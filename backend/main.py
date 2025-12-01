from fastapi import FastAPI, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from database import SessionLocal,Base,engine
from models.habilidad import Habilidad
from fastapi.middleware.cors import CORSMiddleware
from mineria import procesar_datos_computrabajo
from models.tiempo import TiempoCarga
from datetime import datetime, timezone, timedelta
import pandas as pd
from pydantic import BaseModel
import shutil
import json
import os
from monitor_recursos import MonitorRecursos
from calcular_energia import calcular_energia_por_consulta

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Habilidades Laborales")

# Configurar CORS desde variable de entorno
allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://habilis-2025.vercel.app").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# crear una sesión por cada solicitud
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

CACHE_DURACION = timedelta(minutes=5)
cache_estadisticas: dict[str, tuple[dict, datetime]] = {}

def _cache_get(key: str):
    item = cache_estadisticas.get(key)
    if not item:
        return None
    data, ts = item
    if datetime.now() - ts > CACHE_DURACION:
        del cache_estadisticas[key]
        return None
    return data

def _cache_set(key: str, data: dict):
    cache_estadisticas[key] = (data, datetime.now())
    _limpiar_cache_viejo()

def _limpiar_cache_viejo():
    now = datetime.now()
    expirados = [k for k, (_, ts) in cache_estadisticas.items() if now - ts > CACHE_DURACION]
    for k in expirados:
        del cache_estadisticas[k]
# ===============================================

@app.get("/estadisticas/habilidades")
def estadisticas_habilidades(carrera: str = Query(..., description="Nombre de la carrera"), db: Session = Depends(get_db)):
    # HIT de caché
    cache_key = f"habilidades:{carrera.strip().lower()}"
    cached = _cache_get(cache_key)
    if cached:
        return {**cached, "cache": True}

    monitor = MonitorRecursos()
    monitor.iniciar_monitoreo()
    
    carrera = carrera.strip()
    registros = db.query(Habilidad).filter(Habilidad.career.ilike(f"%{carrera}%")).all() #consultar
    monitor.capturar_metrica()  # Captura después de la consulta DB

    if not registros:
        return {"message": "No se encontraron resultados para esa carrera."}

    df = pd.DataFrame([r.__dict__ for r in registros])
    df.drop(columns=["_sa_instance_state", "id"], inplace=True)
    monitor.capturar_metrica()  # Captura después de procesar DataFrame

    columnas_tecnicas = [col for col in df.columns if col.startswith("hard_")]
    columnas_blandas = [col for col in df.columns if col.startswith("soft_")]

    tecnicas_sumadas = df[columnas_tecnicas].sum().sort_values(ascending=False)
    blandas_sumadas = df[columnas_blandas].sum().sort_values(ascending=False)
    monitor.capturar_metrica()  # Captura después de calcular habilidades

    habilidades_tecnicas = [
        {"nombre": formatear_nombre(col), "frecuencia": int(tecnicas_sumadas[col])}
        for col in tecnicas_sumadas.index
    ]

    habilidades_blandas = [
        {"nombre": formatear_nombre(col), "frecuencia": int(blandas_sumadas[col])}
        for col in blandas_sumadas.index
    ]

    # Finalizar monitoreo
    metricas = monitor.finalizar_monitoreo()
    
    # Guardar métricas en archivo para análisis
    with open("data/metricas_recursos.json", "a") as f:
        json.dump({
            "endpoint": "/estadisticas/habilidades",
            "carrera": carrera,
            "timestamp": datetime.now().isoformat(),
            **metricas
        }, f)
        f.write("\n")

    resultado = {
        "carrera": carrera,
        "total_ofertas": len(df),
        "habilidades_tecnicas": habilidades_tecnicas,
        "habilidades_blandas": habilidades_blandas,
        "metricas_recursos": metricas  # Incluir en respuesta
    }
    # Guardar en caché
    _cache_set(cache_key, resultado)
    return resultado

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
    # GUARDAR EL CSV PROCESADO
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

# Filtramos por carrera en la consulta y directamente en la base de datos
@app.get("/estadisticas/salarios")
def estadisticas_salarios(carrera: str = Query(..., description="Nombre de la carrera"), db: Session = Depends(get_db)):
    # HIT de caché
    cache_key = f"salarios:{carrera.strip().lower()}"
    cached = _cache_get(cache_key)
    if cached:
        return {**cached, "cache": True}

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

    resultado = {
        "salarios": [
            {"puesto": row["title"], "salario": row["salario_numerico"]}
            for _, row in df.iterrows()
        ]
    }
    # Guardar en caché
    _cache_set(cache_key, resultado)
    return resultado

@app.post("/proceso-csv")
async def proceso_csv_crudo(file: UploadFile = File(...)):
    try:
        # Guardar el archivo temporalmente
        os.makedirs("data", exist_ok=True)
        path_csv = "data/upload.csv"
        
        # Iniciar monitoreo ANTES de guardar
        monitor = MonitorRecursos()
        monitor.iniciar_monitoreo()
        
        with open(path_csv, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Obtener información del archivo
        file_size_bytes = os.path.getsize(path_csv)
        file_size_mb = file_size_bytes / (1024 * 1024)
        file_name = file.filename
        
        print(f"📁 Archivo recibido: {file_name} ({file_size_mb:.2f} MB)")
        
        monitor.capturar_metrica()  # Después de guardar archivo

        # Procesar archivo CSV, reutilizamos la misma función de minería
        try:
            df_final, resumen, columnas_detectadas, preview_antes, preview_despues, preview_no_ingenieria, preview_no_clasificados = procesar_datos_computrabajo(path_csv)
        except ValueError as e:
            return {
                "message": f"❌ Error en contenido del CSV: {str(e)}",
                "error": "Contenido CSV inválido",
                "suggestion": "Verifique que el archivo contenga datos válidos en las columnas requeridas"
            }

        monitor.capturar_metrica()  # Después de procesar

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
        
        # Guardar registros eliminados como archivos .json
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
        
        monitor.capturar_metrica()  # Después de insertar en BD
        
        # Finalizar monitoreo
        metricas = monitor.finalizar_monitoreo()
        
        print(f"📊 Métricas capturadas: {metricas}")
        
        # Guardar métricas del procesamiento CSV
        metricas_csv = {
            "timestamp": datetime.now().isoformat(),
            "nombre_archivo": file_name,
            "peso_mb": round(file_size_mb, 2),
            "registros_originales": resumen["originales"],
            "registros_finales": resumen["finales"],
            "registros_eliminados": resumen["eliminados"],
            **metricas
        }
        
        # Asegurar que la carpeta data existe
        os.makedirs("data", exist_ok=True)
        ruta_metricas = "data/metricas_csv_procesado.json"
        
        with open(ruta_metricas, "w", encoding="utf-8") as f:
            json.dump(metricas_csv, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Métricas guardadas en: {ruta_metricas}")
        print(f"✅ Contenido guardado: {json.dumps(metricas_csv, indent=2, ensure_ascii=False)}")

        return {
            "message": f"{len(df_final)} registros procesados y guardados exitosamente.",
            "resumen": resumen,
            "preview_antes": preview_antes,
            "preview_despues": preview_despues,
            "no_ingenieria": preview_no_ingenieria,
            "no_clasificados": preview_no_clasificados,
            "metricas_procesamiento": metricas_csv  # Incluir métricas en respuesta
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
    inicio: float  
    fin: float 

@app.post("/tiempo-carga/")
def registrar_tiempo_carga(req: TiempoCargaRequest, db: Session = Depends(get_db)):
    inicio_dt = datetime.fromtimestamp(req.inicio)
    fin_dt = datetime.fromtimestamp(req.fin)
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

@app.get("/obtener-metricas/")
def obtener_metricas():
    try:
        with open("data/metricas_recursos.json", "r") as f:
            lineas = f.readlines()
        
        metricas = [json.loads(l) for l in lineas]
        
        # Calcular estadísticas de recursos
        cpu_prom = sum(m['cpu_promedio_percent'] for m in metricas) / len(metricas)
        ram_prom = sum(m['ram_promedio_mb'] for m in metricas) / len(metricas)
        tiempo_prom = sum(m['tiempo_total_seg'] for m in metricas) / len(metricas)
        
        # Calcular energía para cada consulta
        total_energia = 0
        total_co2 = 0
        for m in metricas:
            calculo = calcular_energia_por_consulta(m)
            m['energia_wh'] = calculo['energia_wh']
            m['co2_gramos'] = calculo['co2_gramos']
            total_energia += calculo['energia_wh']
            total_co2 += calculo['co2_gramos']
        
        energia_promedio = total_energia / len(metricas) if len(metricas) > 0 else 0
        
        return {
            "metricas": metricas,
            "estadisticas": {
                "total_consultas": len(metricas),
                "cpu_promedio": round(cpu_prom, 2),
                "ram_promedio": round(ram_prom, 2),
                "tiempo_promedio": round(tiempo_prom, 4),
                "energia_total_wh": round(total_energia, 4),
                "co2_total_gramos": round(total_co2, 2),
                "energia_promedio_wh": round(energia_promedio, 6)
            }
        }
    except FileNotFoundError:
        return {"metricas": [], "estadisticas": {}}

@app.get("/cache/estado")
def estado_cache():
    _limpiar_cache_viejo()
    return {
        "entradas_activas": len(cache_estadisticas),
        "carreras_cacheadas": [key.replace("habilidades:", "").replace("salarios:", "") for key in cache_estadisticas.keys()],
        "duracion_cache_minutos": CACHE_DURACION.total_seconds() / 60
    }

@app.delete("/cache/limpiar")
def limpiar_cache():
    cache_estadisticas.clear()
    return {"message": "Caché limpiado exitosamente"}

@app.get("/metricas-csv-procesado/")
def obtener_metricas_csv():
    """Obtiene las métricas del último CSV procesado"""
    ruta = "data/metricas_csv_procesado.json"
    print(f"🔍 Intentando leer: {ruta}")
    print(f"📁 ¿Existe el archivo?: {os.path.exists(ruta)}")
    
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            metricas = json.load(f)
        
        print(f"✅ Métricas leídas correctamente: {list(metricas.keys())}")
        
        # Agregar flag de éxito
        metricas["existe"] = True
        return metricas
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {ruta}")
        return {
            "mensaje": "No hay métricas de procesamiento disponibles",
            "existe": False
        }
    except Exception as e:
        print(f"❌ Error al leer métricas: {str(e)}")
        return {
            "mensaje": f"Error al leer métricas: {str(e)}",
            "existe": False
        }