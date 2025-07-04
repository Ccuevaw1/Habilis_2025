from fastapi import FastAPI, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from database import SessionLocal,Base,engine
from models.habilidad import Habilidad
from fastapi.middleware.cors import CORSMiddleware
from mineria import procesar_datos_computrabajo
from sklearn.metrics import accuracy_score
from models.tiempo import TiempoCarga
from datetime import datetime, timezone
from difflib import SequenceMatcher
from io import BytesIO
import pandas as pd
import unicodedata
from pydantic import BaseModel
from unidecode import unidecode
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

@app.get("/estado-csv-procesado")
def obtener_estado_csv():
    import os, json
    ruta = "data/resultado_procesado.json"
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"mensaje": "No hay datos cargados"}

@app.post("/subir-csv-crudo/")
async def subir_csv_crudo(file: UploadFile = File(...)):
    
    # Asegurar carpeta temporal
    os.makedirs("data", exist_ok=True)
    temp_path = "data/datos_crudos.csv"

    # Guardar archivo en la carpeta data/
    contents = await file.read()
    with open(temp_path, "wb") as f:
        f.write(contents)

    # Procesar el archivo con la función del módulo mineria.py
    df = procesar_datos_computrabajo(temp_path)

    df.to_csv("data/datos_procesados.csv", index=False)

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

        # Procesar archivo CSV (mineria.py)
        try:
            df_final, resumen, columnas_detectadas, preview_antes, preview_despues, preview_no_ingenieria, preview_no_clasificados = procesar_datos_computrabajo(path_csv)
        except ValueError as e:
            return {
                "message": f"❌ Error en contenido del CSV: {str(e)}",
                "error": "Contenido CSV inválido",
                "suggestion": "Verifique que el archivo contenga datos válidos en las columnas requeridas"
            }

       # Asegurar que ambos previews sean listas válidas (ya vienen como dicts)
        if not isinstance(preview_antes, list):
            preview_antes = []
        else:
            preview_antes = preview_antes

        if not isinstance(preview_despues, list):
            preview_despues = []
        else:
            preview_despues = preview_despues
        # Verificar si df_final está vacío (importante validación)
        if df_final.empty:
            return {"message": "No se generaron registros válidos tras procesar el CSV.", "error": "DataFrame vacío."}

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
        
        # Guardar registros eliminados como archivos .jsonAdd commentMore actions
        with open("data/registros_no_ingenieria.json", "w", encoding="utf-8") as f1:
            json.dump(preview_no_ingenieria, f1, ensure_ascii=False, indent=2)

        with open("data/registros_no_clasificados.json", "w", encoding="utf-8") as f2:
            json.dump(preview_no_clasificados, f2, ensure_ascii=False, indent=2)

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
            "preview_antes": preview_antes,
            "preview_despues": preview_despues,
            "no_ingenieria": preview_no_ingenieria,
            "no_clasificados": preview_no_clasificados
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("❌ ERROR DETALLADO:", error_trace)
        return {
            "message": "❌ Error al procesar el archivo. Formato Incorrecto o datos inválidos.",
            "error": str(e),
            "detalle": error_trace 
        }

class TiempoCargaRequest(BaseModel):
    carrera: str
    inicio: float  # timestamp UNIX en segundos
    fin: float     # timestamp UNIX en segundos

@app.post("/tiempo-carga/")
def registrar_tiempo_carga(req: TiempoCargaRequest, db: Session = Depends(get_db)):
    inicio_dt = datetime.fromtimestamp(req.inicio, timezone.utc)
    fin_dt = datetime.fromtimestamp(req.fin, timezone.utc)
    duracion = round((fin_dt - inicio_dt).total_seconds(), 4)

    nuevo_log = TiempoCarga(
        carrera=req.carrera,
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

@app.get("/registros-eliminados")
def obtener_registros_eliminados():
    try:
        with open("data/registros_no_ingenieria.json", "r", encoding="utf-8") as f1:
            no_ingenieria = json.load(f1)
    except:
        no_ingenieria = []

    try:
        with open("data/registros_no_clasificados.json", "r", encoding="utf-8") as f2:
            no_clasificados = json.load(f2)
    except:
        no_clasificados = []

    return {
        "no_ingenieria": no_ingenieria,
        "no_clasificados": no_clasificados
    }