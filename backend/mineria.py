import pandas as pd
import re
from sklearn.base import BaseEstimator, TransformerMixin

def procesar_datos_computrabajo(csv_path):
    """
    Procesa un archivo CSV crudo de Computrabajo.
    Detecta carrera, habilidades técnicas y blandas,
    y devuelve un DataFrame limpio y estructurado.
    """
    # Leer archivo CSV
    try:
        df_original = pd.read_csv(csv_path, sep=';', encoding='utf-8', on_bad_lines='skip')
    except UnicodeDecodeError:
        df_original = pd.read_csv(csv_path, sep=';', encoding='latin1', on_bad_lines='skip')

    # Hacer una copia para procesar
    df = df_original.copy()
    # LIMPIEZA DE SALARIO
    df['Salario'] = df['Salario'].fillna('').astype(str).str.replace(r"\(.*?\)", "", regex=True).str.strip()
    df[['Salario_Simbolo', 'Salario_Valor']] = df['Salario'].str.extract(r'(\D+)?([\d.,]+)')
    df['Salario'] = df['Salario'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['Salario'] = pd.to_numeric(df['Salario'], errors='coerce')

    df.drop(columns='Salario_Simbolo', inplace=True)
    df.drop(columns='Salario', inplace=True)
    df.rename(columns={'Salario_Valor': 'Salario'}, inplace=True)

    # FILTRADO POR INGENIERÍAS
    keywords_engineering = [
    'engineer', 'ingeniería', 'ingeniero', 'ingeniero agrónomo', 'ing.', 'industrial', 'civil', 'sistemas', 'ambiental',
    'agronomía', 'agrónomo', 'agronoma', 'agronomist', 'minas', 'minería', 'software engineer',
    'network engineer', 'system engineer', 'data engineer', 'devops', 'frontend', 'backend'
    ]

    def contiene_palabra_ingenieria(texto):
        if isinstance(texto, str):
            return any(palabra in texto for palabra in keywords_engineering)
        return False
    df['Título'] = df['Título'].astype(str).str.lower()
    df['Descripción'] = df['Descripción'].astype(str).str.lower()
    filtro = df['Título'].apply(contiene_palabra_ingenieria) | df['Descripción'].apply(contiene_palabra_ingenieria)
    df = df[filtro].copy()

    registros_no_ingenieria = df_original[~filtro].copy()
    registros_no_ingenieria.to_json("data/registros_no_ingenieria.json", orient="records", force_ascii=False)

    # UNIFICAR TEXTO PARA MINERÍA DE HABILIDADES
    df['Descripción'] = df['Descripción'].str.replace(r'[\r\n]+', ' ', regex=True)
    df['Requerimientos'] = df['Requerimientos'].astype(str).str.replace(r'[\r\n]+', ' ', regex=True)
    df['texto_skills'] = df['Descripción'] + " " + df['Requerimientos']

    # DETECCIÓN DE HABILIDADES
    hard_skills = [
        'python', 'java', 'sql', '_net', 'javascript', 'html', 'css', 'django', 'flask', 'react', 'angular',
        'node', 'power bi', 'sap', 'aws', 'azure', 'git', 'github', 'ci/cd', 'linux', 'docker', 'kubernetes',
        'etl', 'big data', 'data lake', 'postgresql', 'mysql', 'nosql', 'mongodb', 'cloud', 'bash', 'jira',
        'excel', 'autocad', 'r', 'office', 'google_workspace', 'matlab', 'project', 'solidworks', 'Manejo_de_datos',
        'seguridad', 'desarrollo_web', 'gestión_proyectos', 'Mejora_procesos'
    ]
    soft_skills = [
        'comunicación', 'trabajo en equipo', 'proactividad', 'compromiso', 'adaptabilidad',
        'liderazgo', 'responsabilidad', 'creatividad', 'resolución de problemas',
        'orientación al cliente', 'pensamiento crítico'
    ]
    for skill in hard_skills:
        col = f"hard_{skill.replace('/', '_').replace(' ', '_')}"
        df[col] = df['texto_skills'].str.contains(rf'\b{re.escape(skill)}\b', regex=True)
    for skill in soft_skills:
        col = f"soft_{skill.replace(' ', '_')}"
        df[col] = df['texto_skills'].str.contains(rf'\b{re.escape(skill)}\b', regex=True)

    # CLASIFICACIÓN DE CARRERA
    df['Subtítulo'] = df['Subtítulo'].astype(str).str.lower()
    carrera_keywords = {
        'Ingeniería de Sistemas': ['network engineer', 'ingeniería de sistemas', 'ing. sistemas', 'sistemas', 'informática', 'ciencia de datos', 'python', 'java', 'sql'],
        'Ingeniería de Minas': ['ingeniería de minas', 'minería', 'voladura', 'mina', 'unidad minera'],
        'Ingeniería Industrial': ['ingeniería industrial', 'procesos', 'gestión de calidad', 'producción', 'logística'],
        'Ingeniería Civil': ['ingeniería civil', 'civil', 'autocad', 'estructuras', 'obra', 'planos'],
        'Ingeniería Ambiental': ['ingeniería ambiental', 'medio ambiente', 'impacto ambiental', 'residuos'],
        'Ingeniería Agrónoma': ['ingeniería agrónoma', 'cultivos', 'agronomía', 'ingeniero agrónomo', 'agroindustria', 'agrícola']
    }

    def detectar_carrera_por_campos(Título, Subtítulo, Descripcion, Requerimientos):
        texto_total = f"{Título} {Subtítulo} {Descripcion} {Requerimientos}".lower()
        
        puntajes = {c: sum(1 for kw in kws if re.search(rf'\b{re.escape(kw)}\b', texto_total)) for c, kws in carrera_keywords.items()}
        
        if any(puntajes.values()):
            return max(puntajes, key=puntajes.get)
        
        if 'ingeniero' in texto_total or 'ing.' in texto_total:
            for carrera, kws in carrera_keywords.items():
                if any(re.search(rf'\b{re.escape(kw)}\b', texto_total) for kw in kws):
                    return carrera
        return 'No clasificado'

    df['Carrera Detectada'] = df.apply(lambda row: detectar_carrera_por_campos(
        row['Título'], row['Subtítulo'], row['Descripción'], row['Requerimientos']), axis=1)

    df_con_carrera = df.copy()
    df = df[df['Carrera Detectada'] != 'No clasificado'].copy()
    registros_no_clasificados = df_con_carrera[df_con_carrera['Carrera Detectada'] == 'No clasificado'].copy()
    columnas_habilidades = [col for col in registros_no_clasificados.columns if col.startswith("hard_") or col.startswith("soft_")]
    registros_no_clasificados = registros_no_clasificados.drop(columns=columnas_habilidades)
    registros_no_clasificados.to_json("data/registros_no_clasificados.json", orient="records", force_ascii=False)

    # LIMPIEZA DE CARACTERES
    columnas_texto = df.select_dtypes(include='object').columns
    def limpiar_y_contar(texto):
        if not isinstance(texto, str):
            return texto
        return re.sub(r'[^\w\s.,:/()-]', '', texto)
    for col in columnas_texto:
        df[col] = df[col].apply(limpiar_y_contar)

    # ELIMINAR COLUMNAS INNECESARIAS
    columnas_a_eliminar = [
        'Subtítulo', 'Calificación', 'URL_Empresa', 'Región',
        'Requerimientos', 'Contrato', 'Descripción', 'texto_skills', 'Acerca_de_Empresa'
    ]
    df.drop(columns=[col for col in columnas_a_eliminar if col in df.columns], inplace=True)

    # RENOMBRAR
    df.rename(columns={
        'Título': 'title',
        'Empresa': 'company',
        'Salario': 'salary',
        'Jornada': 'workday',
        'Tipo_Asistencia': 'modality',
        'Carrera Detectada': 'career'
    }, inplace=True)

    # RELLENAR NULOS
    rellenados = []
    for campo in ['company', 'salary', 'modality']:
        if campo in df.columns:
            cantidad_nulos = df[campo].isna().sum()
            if cantidad_nulos > 0:
                rellenados.append(campo)
            df[campo] = df[campo].fillna('No especificado')

    # SELECCIONAR COLUMNAS FINALES
    columnas_finales = ['career', 'title', 'company', 'workday', 'modality', 'salary'] + \
        [col for col in df.columns if col.startswith("hard_") or col.startswith("soft_")]

    # Guardar para estadísticas
    df_final = df[columnas_finales].copy()
    columnas_detectadas = [col for col in df.columns if col.startswith("hard_") or col.startswith("soft_")]
    
    resumen = {
        "originales": len(df_original),
        "eliminados": len(df_original) - len(df),
        "finales": len(df),
        "transformaciones_salario": df["salary"].notna().sum() if "salary" in df else 0,
        "rellenos": rellenados,
        "columnas_eliminadas": columnas_a_eliminar,
        "caracteres_limpiados": True,
        "habilidades": columnas_detectadas
    }

    # Preparar datos para mostrar
    preview_no_ingenieria = registros_no_ingenieria.fillna('').astype(str).to_dict(orient='records')
    preview_no_clasificados = registros_no_clasificados.fillna('').astype(str).to_dict(orient='records')
    preview_antes = df_original.fillna('').astype(str).to_dict(orient='records')
    preview_despues = df_final.fillna('').to_dict(orient='records')

    return df_final, resumen, columnas_detectadas, preview_antes, preview_despues, preview_no_ingenieria, preview_no_clasificados