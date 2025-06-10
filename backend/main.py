from fastapi import FastAPI, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from models.habilidad import Habilidad
from fastapi.middleware.cors import CORSMiddleware
from mineria import procesar_datos_computrabajo
from sklearn.metrics import accuracy_score
import pandas as pd
import shutil
import json
import os

# Inicializar la app
app = FastAPI(title="API Habilidades Laborales")

# ✅ CORS configurado justo después de crear `app`
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://habilis-2025.vercel.app"],  # o ["*"] en modo desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear tablas
Base.metadata.create_all(bind=engine)

# Conexión a BD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Backend is ready"}

@app.get("/habilidades/")
def obtener_habilidades(carrera: str = Query(...), db: Session = Depends(get_db)):
    return db.query(Habilidad).filter(Habilidad.career.ilike(f"%{carrera.strip()}%")).all()

def formatear_nombre(nombre: str) -> str:
    partes = nombre.split('_')[1:]
    return ' '.join(partes).capitalize()

@app.get("/estadisticas/habilidades")
def estadisticas_habilidades(carrera: str, db: Session = Depends(get_db)):
    registros = db.query(Habilidad).filter(Habilidad.career.ilike(f"%{carrera.strip()}%")).all()
    if not registros:
        return {"message": "No se encontraron resultados para esa carrera."}

    df = pd.DataFrame([r.__dict__ for r in registros]).drop(columns=["_sa_instance_state", "id"])
    cols_tec = [col for col in df.columns if col.startswith("hard_")]
    cols_soft = [col for col in df.columns if col.startswith("soft_")]

    tec = df[cols_tec].sum().sort_values(ascending=False)
    soft = df[cols_soft].sum().sort_values(ascending=False)

    return {
        "carrera": carrera,
        "total_ofertas": len(df),
        "habilidades_tecnicas": [{"nombre": formatear_nombre(k), "frecuencia": int(v)} for k, v in tec.items()],
        "habilidades_blandas": [{"nombre": formatear_nombre(k), "frecuencia": int(v)} for k, v in soft.items()]
    }

@app.post("/subir-csv-crudo/")
async def subir_csv_crudo(file: UploadFile = File(...)):
    path = "data/datos_crudos.csv"
    os.makedirs("data", exist_ok=True)
    with open(path, "wb") as f:
        f.write(await file.read())

    df, _, _ = procesar_datos_computrabajo(path)
    db = SessionLocal()
    db.query(Habilidad).delete()
    db.commit()
    for _, row in df.iterrows():
        h = Habilidad(
            career=row.get("career"),
            title=row.get("title"),
            company=row.get("company"),
            workday=row.get("workday"),
            modality=row.get("modality"),
            salary=row.get("salary"),
            **{c: int(row[c]) for c in df.columns if c.startswith("hard_") or c.startswith("soft_")}
        )
        db.add(h)
    db.commit()
    db.close()
    return {"message": f"{len(df)} registros guardados."}

@app.post("/proceso-csv")
async def proceso_csv_crudo(file: UploadFile = File(...)):
    try:
        path_csv = "data/upload.csv"
        os.makedirs("data", exist_ok=True)
        with open(path_csv, "wb") as f:
            shutil.copyfileobj(file.file, f)

        df_final, resumen, columnas_detectadas = procesar_datos_computrabajo(path_csv)

        db = SessionLocal()
        db.query(Habilidad).delete()
        db.commit()
        for _, row in df_final.iterrows():
            h = Habilidad(
                career=row.get("career"),
                title=row.get("title"),
                company=row.get("company"),
                workday=row.get("workday"),
                modality=row.get("modality"),
                salary=row.get("salary"),
                **{col: int(row[col]) for col in columnas_detectadas}
            )
            db.add(h)
        db.commit()
        db.close()

        return {
            "message": f"{len(df_final)} registros procesados y guardados exitosamente.",
            "resumen": resumen
        }
    except Exception as e:
        import traceback
        print("❌ ERROR en /proceso-csv:", traceback.format_exc())
        return {"message": "❌ Error al procesar el archivo.", "error": str(e)}

@app.get("/estadisticas/salarios")
def estadisticas_salarios(carrera: str, db: Session = Depends(get_db)):
    registros = db.query(Habilidad).filter(Habilidad.career.ilike(f"%{carrera.strip()}%")).all()
    if not registros:
        return {"message": "No se encontraron resultados para esa carrera."}

    df = pd.DataFrame([r.__dict__ for r in registros]).drop(columns=["_sa_instance_state", "id"])
    df = df[df["salary"].notnull() & (df["salary"] != "No especificado")].copy()

    def limpiar(s):
        try:
            s = str(s).replace("s/", "").replace(".", "").replace(",", ".").strip().lower()
            return float(s)
        except:
            return None

    df["salario_numerico"] = df["salary"].apply(limpiar)
    df = df.dropna(subset=["salario_numerico"])
    df = df[df["salario_numerico"] > 1500]
    df = df.sort_values(by="salario_numerico", ascending=False).drop_duplicates(subset=["title"])
    df = df.sort_values(by="salario_numerico")

    return {"salarios": [{"puesto": row["title"], "salario": row["salario_numerico"]} for _, row in df.iterrows()]}

@app.post("/verificar-modelo/")
async def verificar_modelo(file: UploadFile = File(...)):
    try:
        path = "data/manual.csv"
        with open(path, "wb") as f:
            f.write(await file.read())

        try:
            df_real = pd.read_csv(path, sep=';', encoding='utf-8')
        except UnicodeDecodeError:
            df_real = pd.read_csv(path, sep=';', encoding='latin1')

        df_pred = procesar_datos_computrabajo(path)[0]
        cols = [col for col in df_real.columns if col.startswith("hard_") or col.startswith("soft_")]
        y_true = df_real[cols].astype(int)
        y_pred = df_pred[cols].astype(int)

        precision = accuracy_score(y_true.values.flatten(), y_pred.values.flatten())

        resultado = {
            "precision": round(precision, 4),
            "mensaje": f"Precisión del modelo de minería: {precision * 100:.2f}%"
        }

        with open("data/precision_guardada.json", "w") as f:
            json.dump(resultado, f, indent=2)

        return resultado
    except Exception as e:
        return {"error": str(e)}

@app.get("/precision-mineria/")
def obtener_precision_modelo():
    try:
        with open("data/precision_guardada.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"precision": None, "mensaje": "⚠️ Aún no se ha verificado el modelo."}