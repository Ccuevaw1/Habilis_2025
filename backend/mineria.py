import pandas as pd
import re

def procesar_datos_computrabajo(csv_path):
    # Paso 1: Leer CSV original (con manejo robusto de codificación y fallback)
    try:
        df_original = pd.read_csv(csv_path, sep=';', encoding='utf-8', on_bad_lines='skip')
    except UnicodeDecodeError:
        try:
            df_original = pd.read_csv(csv_path, sep=';', encoding='latin1', on_bad_lines='skip')
        except Exception as e:
            raise ValueError(f"❌ Error al leer el archivo CSV: {e}")

    if df_original.empty:
        raise ValueError("❌ El CSV está vacío o no tiene datos válidos.")

    # Paso 2: Guardar vista previa cruda
    preview_antes = df_original.head(5).to_dict(orient='records')

    # Paso 3: Copiar el DataFrame para procesamiento
    df = df_original.copy()

    # Verificación mínima de columnas requeridas
    columnas_requeridas = ['Título', 'Descripción', 'Requerimientos', 'Empresa', 'Salario']
    for col in columnas_requeridas:
        if col not in df.columns:
            raise ValueError(f"❌ El CSV no contiene la columna requerida: '{col}'")

    # Limpieza de salario
    df['Salario'] = df['Salario'].fillna('').astype(str).str.replace(r"\(.*?\)", "", regex=True).str.strip()
    df[['Salario_Simbolo', 'Salario_Valor']] = df['Salario'].str.extract(r'(\D+)?([\d.,]+)')
    df['Salario'] = df['Salario'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['Salario'] = pd.to_numeric(df['Salario'], errors='coerce')
    df.drop(columns='Salario_Simbolo', inplace=True)
    df.drop(columns='Salario', inplace=True)
    df.rename(columns={'Salario_Valor': 'Salario'}, inplace=True)

    # Filtrado por palabras clave
    keywords_engineering = ['ingeniería', 'ingeniero', 'industrial', 'sistemas', 'civil', 'ambiental', 'agrónoma', 'minas']
    df['Título'] = df['Título'].astype(str).str.lower()
    df['Descripción'] = df['Descripción'].astype(str).str.lower()
    df = df[
        df['Título'].apply(lambda x: any(k in x for k in keywords_engineering)) |
        df['Descripción'].apply(lambda x: any(k in x for k in keywords_engineering))
    ].copy()

    if df.empty:
        raise ValueError("❌ No se encontraron registros que coincidan con ingenierías.")

    # Unificación de texto para minería
    df['Descripción'] = df['Descripción'].str.replace(r'[\r\n]+', ' ', regex=True)
    df['Requerimientos'] = df['Requerimientos'].astype(str).str.replace(r'[\r\n]+', ' ', regex=True)
    df['texto_skills'] = df['Descripción'] + " " + df['Requerimientos']

    # Detección de habilidades
    hard_skills = ['python', 'java', 'sql', '_net', 'javascript', 'html', 'css']
    soft_skills = ['comunicación', 'trabajo en equipo', 'proactividad']
    for skill in hard_skills:
        col = f"hard_{skill.replace('/', '_').replace(' ', '_')}"
        df[col] = df['texto_skills'].str.contains(rf'\b{re.escape(skill)}\b', regex=True)
    for skill in soft_skills:
        col = f"soft_{skill.replace(' ', '_')}"
        df[col] = df['texto_skills'].str.contains(rf'\b{re.escape(skill)}\b', regex=True)

    # Clasificación de carrera
    carrera_keywords = {
        'Ingeniería de Sistemas': ['sistemas', 'informática', 'python'],
        'Ingeniería Industrial': ['procesos', 'logística'],
    }
    def detectar_carrera(row):
        texto = f"{row.get('Título', '')} {row.get('Subtítulo', '')} {row.get('Descripción', '')} {row.get('Requerimientos', '')}"
        for carrera, kws in carrera_keywords.items():
            if any(k in texto for k in kws):
                return carrera
        return 'No clasificado'

    df['Carrera Detectada'] = df.apply(detectar_carrera, axis=1)
    df = df[df['Carrera Detectada'] != 'No clasificado'].copy()

    # Limpieza de caracteres
    columnas_texto = df.select_dtypes(include='object').columns
    def limpiar_texto(txt):
        return re.sub(r'[^\w\s.,:/()-]', '', txt) if isinstance(txt, str) else txt
    for col in columnas_texto:
        df[col] = df[col].apply(limpiar_texto)

    # Eliminar columnas innecesarias
    columnas_a_eliminar = ['Subtítulo', 'Calificación', 'URL_Empresa', 'Región',
                           'Requerimientos', 'Contrato', 'Descripción', 'texto_skills', 'Acerca_de_Empresa']
    df.drop(columns=[c for c in columnas_a_eliminar if c in df.columns], inplace=True)

    # Renombrado
    df.rename(columns={
        'Título': 'title',
        'Empresa': 'company',
        'Salario': 'salary',
        'Jornada': 'workday',
        'Tipo_Asistencia': 'modality',
        'Carrera Detectada': 'career'
    }, inplace=True)

    # Relleno de nulos
    rellenados = []
    for campo in ['company', 'salary', 'modality']:
        if campo in df.columns and df[campo].isna().sum() > 0:
            rellenados.append(campo)
            df[campo] = df[campo].fillna('No especificado')

    # Selección final
    columnas_finales = ['career', 'title', 'company', 'workday', 'modality', 'salary'] + \
                       [col for col in df.columns if col.startswith('hard_') or col.startswith('soft_')]
    df_final = df[columnas_finales].copy()
    columnas_detectadas = [col for col in df.columns if col.startswith("hard_") or col.startswith("soft_")]

    # Generar resumen
    resumen = {
        "originales": len(df_original),
        "eliminados": len(df_original) - len(df),
        "finales": len(df),
        "transformaciones_salario": df["salary"].notna().sum(),
        "rellenos": rellenados,
        "columnas_eliminadas": columnas_a_eliminar,
        "caracteres_limpiados": True,
        "habilidades": columnas_detectadas
    }

    preview_despues = df_final.head(5).to_dict(orient='records')
    return df_final, resumen, columnas_detectadas, preview_antes, preview_despues
