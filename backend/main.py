from fastapi import FastAPI, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from database import SessionLocal,Base,engine
from models.habilidad import Habilidad
from fastapi.middleware.cors import CORSMiddleware
from mineria import procesar_datos_computrabajo
from sklearn.metrics import accuracy_score
import pandas as pd
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
        # Guardar el archivo cargado
        temp_manual_path = "data/manual.csv"
        with open(temp_manual_path, "wb") as f:
            f.write(await file.read())

        # Leer el CSV manual que contiene las etiquetas verdaderas
        df_real = pd.read_csv(temp_manual_path, sep=';', encoding='utf-8')

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
