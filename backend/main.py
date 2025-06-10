from fastapi import FastAPI, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from database import SessionLocal,Base,engine
from models.habilidad import Habilidad
from fastapi.middleware.cors import CORSMiddleware
from mineria import procesar_datos_computrabajo
from sklearn.metrics import accuracy_score
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

# def obtener_resumen_procesamiento(df_original, df_filtrado, columnas_detectadas):
    
#     return {
#           "originales": len(df_original),
#           "eliminados": len(df_original) - len(df_filtrado),
#           "finales": len(df_filtrado),
#           "transformaciones_salario": 0,  
#           "rellenos": [],                
#           "columnas_eliminadas": [],       
#           "caracteres_limpiados": True,
#           "habilidades": columnas_detectadas
#     }

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

        y_true = df_real[columnas_habilidades].astype(int)
        y_pred = df_predicho[columnas_habilidades].astype(int)

        # Calcular precisión
        precision = accuracy_score(y_true.values.flatten(), y_pred.values.flatten())

        # Preparar y guardar el resultado en un archivo JSON
        resultado = {
            "precision": round(precision, 4),
            "mensaje": f"Precisión del modelo de minería: {precision * 100:.2f}%"
        }

        os.makedirs("data", exist_ok=True)
        with open("data/precision_guardada.json", "w") as f:
            import json
            json.dump(resultado, f, indent=2)

        return resultado

    except Exception as e:
        return {"error": str(e)}

@app.get("/precision-mineria/")
def obtener_precision_modelo():
    try:
        with open("data/precision_guardada.json", "r") as f:
            precision_data = json.load(f)
        return precision_data
    except FileNotFoundError:
        return {
            "precision": None,
            "mensaje": "⚠️ Aún no se ha verificado el modelo."
        }

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
        # Guardar archivo temporal
        os.makedirs("data", exist_ok=True)
        path_csv = "data/upload.csv"
        with open(path_csv, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Leer CSV original
        try:
            df_original = pd.read_csv(path_csv, encoding="utf-8", sep=";", on_bad_lines='skip')
        except UnicodeDecodeError:
            df_original = pd.read_csv(path_csv, encoding="latin1", sep=";", on_bad_lines='skip')

        # Procesar archivo (solo devuelve df procesado)
        df_final, resumen, columnas_detectadas = procesar_datos_computrabajo(path_csv)

        # Detectar columnas de habilidades
        columnas_habilidades = [col for col in df_final.columns if col.startswith("hard_") or col.startswith("soft_")]

        # Generar resumen manual
        # resumen = obtener_resumen_procesamiento(df_original, df_final, columnas_habilidades)

        # Insertar en base de datos (borrando lo anterior)
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
                **{col: int(row[col]) for col in columnas_habilidades}
            )
            db.add(habilidad)
        db.commit()
        db.close()

        return {
            "message": f"{len(df_final)} registros procesados y guardados exitosamente.",
            "resumen": resumen
        }

    except Exception as e:
        import traceback
        print("❌ ERROR en /proceso-csv:", traceback.format_exc())
        return {
            "message": "❌ Error al procesar el archivo.",
            "error": str(e)
        }

