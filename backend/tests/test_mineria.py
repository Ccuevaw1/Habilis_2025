# backend/tests/test_mineria.py

import os, sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mineria import procesar_datos_computrabajo

def test_procesar_datos_computrabajo():
    # Ruta del archivo de prueba
    csv_path = os.path.join(os.path.dirname(__file__), "data", "sample.csv")

    # Ejecutar función
    df_final, resumen, columnas_detectadas, preview_antes, preview_despues, preview_no_ingenieria, preview_no_clasificados = procesar_datos_computrabajo(csv_path)

    # Verificaciones básicas
    assert isinstance(df_final, pd.DataFrame)
    assert isinstance(resumen, dict)
    assert isinstance(columnas_detectadas, list)
    assert isinstance(preview_antes, list)
    assert isinstance(preview_despues, list)
    assert isinstance(preview_no_ingenieria, list)
    assert isinstance(preview_no_clasificados, list)

    # Verificar que al menos una habilidad técnica se detectó
    habilidades_tecnicas = [col for col in columnas_detectadas if col.startswith("hard_")]
    assert any(h in df_final.columns for h in habilidades_tecnicas)

    # Verificar que las columnas claves están en el DataFrame
    for col in ["career", "title", "company", "workday", "modality", "salary"]:
        assert col in df_final.columns

    # Verificar que los valores en `preview_despues` tengan 'Sí' o 'No'
    for registro in preview_despues:
        for col in columnas_detectadas:
            assert registro[col] in ["Sí", "No"]
