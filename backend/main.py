from fastapi import FastAPI, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from database import SessionLocal,Base,engine
from models.habilidad import Habilidad
from fastapi.middleware.cors import CORSMiddleware
from mineria import procesar_datos_computrabajo
from sklearn.metrics import accuracy_score
from models.tiempo import TiempoCarga
import time
from datetime import datetime, timezone
import pandas as pd
import shutil
import json
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Habilidades Laborales")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://habilis-2025.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware: crear una sesión por cada solicitud
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Backend is ready"}

# Endpoint para filtrar por carrera
@app.get("/habilidades/")
def obtener_habilidades(carrera: str = Query(..., description="Nombre de la carrera"), db: Session = Depends(get_db)):
    resultados = db.query(Habilidad).filter(Habilidad.career.ilike(f"%{carrera.strip()}%")).all()
    return resultados

# Función para limpiar nombre de habilidad
def formatear_nombre(nombre: str) -> str:
    partes = nombre.split('_')[1:]  # elimina el prefijo 'hard_' o 'soft_'
    return ' '.join(partes).capitalize()  # puedes usar .title() si quieres Todo En Mayúscula Inicial

@app.get("/estadisticas/habilidades")
def estadisticas_habilidades(carrera: str = Query(..., description="Nombre de la carrera"), db: Session = Depends(get_db)):
    carrera = carrera.strip()
    registros = db.query(Habilidad).filter(Habilidad.career.ilike(f"%{carrera}%")).all()

    if not registros:
        return {"message": "No se encontraron resultados para esa carrera."}

    df = pd.DataFrame([r.__dict__ for r in registros])
    df.drop(columns=["_sa_instance_state", "id"], inplace=True)

    columnas_tecnicas = [col for col in df.columns if col.startswith("hard_")]
    columnas_blandas = [col for col in df.columns if col.startswith("soft_")]

    tecnicas_sumadas = df[columnas_tecnicas].sum().sort_values(ascending=False)
    blandas_sumadas = df[columnas_blandas].sum().sort_values(ascending=False)

    habilidades_tecnicas = [
        {"nombre": formatear_nombre(col), "frecuencia": int(tecnicas_sumadas[col])}
        for col in tecnicas_sumadas.index
    ]

    habilidades_blandas = [
        {"nombre": formatear_nombre(col), "frecuencia": int(blandas_sumadas[col])}
        for col in blandas_sumadas.index
    ]

    return {
        "carrera": carrera,
        "total_ofertas": len(df),
        "habilidades_tecnicas": habilidades_tecnicas,
        "habilidades_blandas": habilidades_blandas
    }

@app.post("/subir-csv-crudo/")
async def subir_csv_crudo(file: UploadFile = File(...)):
    """
    Endpoint para subir y procesar un archivo CSV crudo extraído de Computrabajo.
    El sistema detecta habilidades técnicas y blandas, y guarda los datos en la base de datos.
    """
    # Asegurar carpeta temporal
    os.makedirs("data", exist_ok=True)
    temp_path = "data/datos_crudos.csv"

    # Guardar archivo en la carpeta data/
    contents = await file.read()
    with open(temp_path, "wb") as f:
        f.write(contents)

    # Procesar el archivo con la función del módulo mineria.py
    df = procesar_datos_computrabajo(temp_path)

    # Insertar los datos en la base de datos
    db = SessionLocal()
    db.query(Habilidad).delete()
    db.commit()
    for _, row in df.iterrows():
        habilidad = Habilidad(
            career=row.get("career"),
            title=row.get("title"),
            company=row.get("company"),
            workday=row.get("workday"),
            modality=row.get("modality"),
            salary=row.get("salary"),
            **{col: int(row[col]) for col in df.columns if col.startswith("hard_") or col.startswith("soft_")}
        )
        db.add(habilidad)

    db.commit()
    db.close()

    return {"message": f"{len(df)} registros procesados y guardados exitosamente."}

@app.post("/verificar-modelo/")
async def verificar_modelo(file: UploadFile = File(...)):
    try:
        import json

        # Guardar el archivo cargado
        temp_manual_path = "data/manual.csv"
        with open(temp_manual_path, "wb") as f:
            f.write(await file.read())

        # Leer el CSV manual que contiene las etiquetas verdaderas
        try:
            df_real = pd.read_csv(temp_manual_path, sep=';', encoding='utf-8')
        except UnicodeDecodeError:
            df_real = pd.read_csv(temp_manual_path, sep=';', encoding='latin1')

        # Generar predicciones usando la función de minería
        df_predicho = procesar_datos_computrabajo(temp_manual_path)

        # Extraer columnas de habilidades para comparar
        columnas_habilidades = [col for col in df_real.columns if col.startswith("hard_") or col.startswith("soft_")]

        y_true = df_real[columnas_habilidades].applymap(lambda x: int(str(x).lower() in ["1", "true", "t"])).reset_index(drop=True)
        y_pred = df_predicho[columnas_habilidades].applymap(lambda x: int(str(x).lower() in ["1", "true", "t"])).reset_index(drop=True)


        # Calcular precisión y recall
        precision = accuracy_score(y_true.values.flatten(), y_pred.values.flatten())
        recall = (y_pred & y_true).sum().sum() / y_true.sum().sum()

        # Cobertura media por carrera
        if "career" in df_real.columns:
            carreras = df_real["career"].unique()
            cobertura = {}
            for carrera in carreras:
                subset = df_real[df_real["career"] == carrera]
                if len(subset) > 0:
                    sub_pred = df_predicho[df_real["career"] == carrera]
                    sub_cols = sub_pred[columnas_habilidades]
                    cobertura[carrera] = sub_cols.sum(axis=1).mean()
            cobertura_media = round(sum(cobertura.values()) / len(cobertura), 2)
        else:
            cobertura_media = None

        # Habilidades más ruidosas
        errores = abs(y_true - y_pred)
        errores_por_habilidad = errores.sum().sort_values(ascending=False)
        habilidades_ruidosas = errores_por_habilidad.head(5).to_dict()

        # Preparar resultado
        resultado = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "cobertura_media": cobertura_media,
            "habilidades_ruidosas": habilidades_ruidosas,
            "mensaje": f"Precisión del modelo de minería: {precision * 100:.2f}%"
        }

        os.makedirs("data", exist_ok=True)
        with open("data/evaluacion_modelo.json", "w") as f:
            json.dump(resultado, f, indent=2)

        return resultado

    except Exception as e:
        return {"error": str(e)}

# @app.get("/precision-mineria/")
# def obtener_precision_modelo():
#     try:
#         with open("data/precision_guardada.json", "r") as f:
#             precision_data = json.load(f)
#         return precision_data
#     except FileNotFoundError:
#         return {
#             "precision": None,
#             "mensaje": "⚠️ Aún no se ha verificado el modelo."
#         }

@app.get("/estadisticas/salarios")
def estadisticas_salarios(carrera: str = Query(..., description="Nombre de la carrera"), db: Session = Depends(get_db)):
    registros = db.query(Habilidad).filter(Habilidad.career.ilike(f"%{carrera.strip()}%")).all()

    if not registros:
        return {"message": "No se encontraron resultados para esa carrera."}

    df = pd.DataFrame([r.__dict__ for r in registros])
    df.drop(columns=["_sa_instance_state", "id"], inplace=True)

    # Filtrar salarios válidos
    df = df[df["salary"].notnull() & (df["salary"] != "No especificado")].copy()

    def limpiar_salario(s):
        try:
            s = str(s).strip().lower()
            s = s.replace("s/", "").replace(".", "").replace(",", ".")
            return float(s)
        except:
            return None

    df["salario_numerico"] = df["salary"].apply(limpiar_salario)
    df = df.dropna(subset=["salario_numerico"])
    
    # Filtrar solo salarios > 1500
    df = df[df["salario_numerico"] > 1500]

    # Eliminar títulos duplicados (quedarse con el mayor salario por título)
    df = df.sort_values(by="salario_numerico", ascending=False).drop_duplicates(subset=["title"])

    # Ordenar de menor a mayor para la gráfica
    df = df.sort_values(by="salario_numerico", ascending=True)

    return {
        "salarios": [
            {"puesto": row["title"], "salario": row["salario_numerico"]}
            for _, row in df.iterrows()
        ]
    }

@app.post("/proceso-csv")
async def proceso_csv_crudo(file: UploadFile = File(...)):
    try:
        # Guardar el archivo temporalmente
        os.makedirs("data", exist_ok=True)
        path_csv = "data/upload.csv"
        with open(path_csv, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Leer CSV original con manejo robusto de encoding
        try:
            df_original = pd.read_csv(path_csv, encoding="utf-8", sep=";", on_bad_lines='skip')
        except UnicodeDecodeError:
            df_original = pd.read_csv(path_csv, encoding="latin1", sep=";", on_bad_lines='skip')

        # Procesar archivo CSV (mineria.py)
        df_final, resumen, columnas_detectadas, preview_antes, preview_despues = procesar_datos_computrabajo(path_csv)

       # Asegurar que ambos previews sean listas válidas (ya vienen como dicts)
        if not isinstance(preview_antes, list):
            preview_antes_list = []
        else:
            preview_antes_list = preview_antes

        if not isinstance(preview_despues, list):
            preview_despues_list = []
        else:
            preview_despues_list = preview_despues
        # Verificar si df_final está vacío (importante validación)
        if df_final.empty:
            return {"message": "❌ No se generaron registros válidos tras procesar el CSV.", "error": "DataFrame vacío."}

        # Asegurar tipos correctos para el frontend
        resumen = {
            "originales": int(resumen["originales"]),
            "eliminados": int(resumen["eliminados"]),
            "finales": int(resumen["finales"]),
            "transformaciones_salario": int(resumen["transformaciones_salario"]),
            "rellenos": resumen["rellenos"],
            "columnas_eliminadas": resumen["columnas_eliminadas"],
            "caracteres_limpiados": resumen["caracteres_limpiados"],
            "habilidades": resumen["habilidades"]
        }

        # Insertar datos procesados en BD
        db = SessionLocal()
        db.query(Habilidad).delete()
        db.commit()
        for _, row in df_final.iterrows():
            habilidad = Habilidad(
                career=row.get("career"),
                title=row.get("title"),
                company=row.get("company"),
                workday=row.get("workday"),
                modality=row.get("modality"),
                salary=row.get("salary"),
                **{col: int(row[col]) for col in columnas_detectadas}
            )
            db.add(habilidad)
        db.commit()
        db.close()

        return {
            "message": f"{len(df_final)} registros procesados y guardados exitosamente.",
            "resumen": resumen,
            "preview_antes": preview_antes_list,
            "preview_despues": preview_despues_list
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("❌ ERROR DETALLADO:", error_trace)
        return {
            "message": "❌ Error al procesar el archivo.",
            "error": str(e),
            "detalle": error_trace  # Opcional para debug
        }

@app.get("/evaluacion-modelo/")
def obtener_evaluacion_modelo():
    try:
        with open("data/evaluacion_modelo.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "precision": None,
            "recall": None,
            "cobertura_media": None,
            "habilidades_ruidosas": {},
            "mensaje": "Aún no se ha calculado la evaluación del modelo."
        }

@app.post("/tiempo-carga/")
def registrar_tiempo_carga(
    carrera: str = Query(...),
    inicio: float = Query(...),  # viene del frontend como UNIX timestamp
    db: Session = Depends(get_db)
):
    # Convertir inicio recibido desde frontend
    inicio_dt = datetime.fromtimestamp(inicio, tz=timezone.utc)
    fin_dt = datetime.now(timezone.utc)

    duracion = round((fin_dt - inicio_dt).total_seconds(), 4)
    if duracion < 0:
        duracion = 0.001  # evitar valores negativos

    nuevo_log = TiempoCarga(
        carrera=carrera,
        inicio=inicio_dt,
        fin=fin_dt,
        tiempo_segundos=duracion
    )

    db.add(nuevo_log)
    db.commit()

    return {
        "mensaje": f"Tiempo registrado: {duracion} segundos",
        "inicio": inicio_dt.isoformat(),
        "fin": fin_dt.isoformat()
    }
