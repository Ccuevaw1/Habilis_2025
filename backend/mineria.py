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
    keywords_engineering = ['ingeniería', 'ingeniero', 'industrial', 'sistemas', 'civil', 'ambiental', 'agrónoma', 'minas']
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
    # df['Subtítulo'] = df['Subtítulo'].astype(str).str.lower()
    # carrera_keywords = {
    #     'Ingeniería de Sistemas': ['ingeniería de sistemas', 'ing. sistemas', 'sistemas', 'informática', 'python', 'java', 'sql'],
    #     'Ingeniería de Minas': ['ingeniería de minas', 'minería', 'voladura', 'mina', 'unidad minera'],
    #     'Ingeniería Industrial': ['ingeniería industrial', 'procesos', 'gestión de calidad', 'producción', 'logística'],
    #     'Ingeniería Civil': ['ingeniería civil', 'autocad', 'estructuras', 'obra', 'planos'],
    #     'Ingeniería Ambiental': ['ingeniería ambiental', 'medio ambiente', 'impacto ambiental', 'residuos'],
    #     'Ingeniería Agrónoma': ['ingeniería agrónoma', 'cultivos', 'agronomía', 'agroindustria', 'agrícola']
    # }
    # def detectar_carrera_por_campos(titulo, subtitulo, descripcion, requerimientos):
    #     texto_total = f"{titulo} {subtitulo} {descripcion} {requerimientos}"
    #     puntajes = {c: sum(1 for kw in kws if kw in texto_total) for c, kws in carrera_keywords.items()}
    #     return max(puntajes, key=puntajes.get) if any(puntajes.values()) else 'No clasificado'
    # df['Carrera Detectada'] = df.apply(lambda row: detectar_carrera_por_campos(
    #     row['Título'], row['Subtítulo'], row['Descripción'], row['Requerimientos']), axis=1)
    # df = df[df['Carrera Detectada'] != 'No clasificado'].copy()

    # === CLASIFICACIÓN DE CARRERA (ANTES DE FILTRAR) ===
    df_original['Título'] = df_original['Título'].astype(str).str.lower()
    df_original['Descripción'] = df_original['Descripción'].astype(str).str.lower()
    df_original['Subtítulo'] = df_original['Subtítulo'].astype(str).str.lower()
    df_original['Requerimientos'] = df_original['Requerimientos'].astype(str).str.lower()

    carrera_keywords = {
        'Ingeniería de Sistemas': ['ingeniería de sistemas', 'ing. sistemas', 'sistemas', 'informática', 'python', 'java', 'sql'],
        'Ingeniería de Minas': ['ingeniería de minas', 'minería', 'voladura', 'mina', 'unidad minera'],
        'Ingeniería Industrial': ['ingeniería industrial', 'procesos', 'gestión de calidad', 'producción', 'logística'],
        'Ingeniería Civil': ['ingeniería civil', 'autocad', 'estructuras', 'obra', 'planos'],
        'Ingeniería Ambiental': ['ingeniería ambiental', 'medio ambiente', 'impacto ambiental', 'residuos'],
        'Ingeniería Agrónoma': ['ingeniería agrónoma', 'cultivos', 'agronomía', 'agroindustria', 'agrícola']
    }

    def detectar_carrera_por_campos(titulo, subtitulo, descripcion, requerimientos):
        texto_total = f"{titulo} {subtitulo} {descripcion} {requerimientos}"
        puntajes = {c: sum(1 for kw in kws if kw in texto_total) for c, kws in carrera_keywords.items()}
        return max(puntajes, key=puntajes.get) if any(puntajes.values()) else 'No clasificado'

    df_original['Carrera Detectada'] = df_original.apply(lambda row: detectar_carrera_por_campos(
        row['Título'], row['Subtítulo'], row['Descripción'], row['Requerimientos']), axis=1)

    # Guardar registros no clasificados
    registros_no_clasificados = df_original[df_original['Carrera Detectada'] == 'No clasificado'].copy()
    registros_no_clasificados.to_json("data/registros_no_clasificados.json", orient="records", force_ascii=False)

    # === Filtrar por carreras de ingeniería (después de clasificar) ===
    keywords_engineering = ['ingeniería', 'ingeniero', 'industrial', 'sistemas', 'civil', 'ambiental', 'agrónoma', 'minas']
    def contiene_palabra_ingenieria(texto):
        if isinstance(texto, str):
            return any(palabra in texto for palabra in keywords_engineering)
        return False

    filtro = df_original['Título'].apply(contiene_palabra_ingenieria) | df_original['Descripción'].apply(contiene_palabra_ingenieria)
    df = df_original[filtro].copy()

    registros_no_ingenieria = df_original[~filtro].copy()
    registros_no_ingenieria.to_json("data/registros_no_ingenieria.json", orient="records", force_ascii=False)

    df_con_carrera = df.copy()
    registros_no_clasificados = df_con_carrera[df_con_carrera['Carrera Detectada'] == 'No clasificado'].copy()
    registros_no_clasificados.to_json("data/registros_no_clasificados.json", orient="records", force_ascii=False)
    df = df[df['Carrera Detectada'] != 'No clasificado'].copy()
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
    
    return (
        df_final, resumen, columnas_detectadas, preview_antes,
        preview_despues, preview_no_ingenieria,
        preview_no_clasificados
    )

class HabilidadesExtractor(BaseEstimator, TransformerMixin):
    """
    Clase para extracción de habilidades compatible con scikit-learn
    """
    def __init__(self):
        # Definición de habilidades (las mismas que usas actualmente)
        self.hard_skills = [
            'python', 'java', 'sql', '_net', 'javascript', 'html', 'css', 'django', 'flask', 'react', 'angular',
            'node', 'power bi', 'sap', 'aws', 'azure', 'git', 'github', 'ci/cd', 'linux', 'docker', 'kubernetes',
            'etl', 'big data', 'data lake', 'postgresql', 'mysql', 'nosql', 'mongodb', 'cloud', 'bash', 'jira',
            'excel', 'autocad', 'r', 'office', 'google_workspace', 'matlab', 'project', 'solidworks', 'Manejo_de_datos',
            'seguridad', 'desarrollo_web', 'gestión_proyectos', 'Mejora_procesos'
        ]
        self.soft_skills = [
            'comunicación', 'trabajo en equipo', 'proactividad', 'compromiso', 'adaptabilidad',
            'liderazgo', 'responsabilidad', 'creatividad', 'resolución de problemas',
            'orientación al cliente', 'pensamiento crítico'
        ]
        
        # Precompilar expresiones regulares para mejor performance
        self.regex_cache = {}
        for skill in self.hard_skills + self.soft_skills:
            self.regex_cache[skill] = re.compile(rf'\b{re.escape(skill)}\b', re.IGNORECASE)

    def fit(self, X, y=None):
        return self
    
    def transform(self, X):
        """
        Transforma texto en características de habilidades
        X: DataFrame con columna 'texto_skills' o similar
        """
        if isinstance(X, pd.DataFrame):
            textos = X['texto_skills'] if 'texto_skills' in X.columns else X.iloc[:, 0]
        else:
            textos = X
            
        resultados = []
        for texto in textos:
            fila = {}
            # Procesar hard skills
            for skill in self.hard_skills:
                col_name = f"hard_{skill.replace('/', '_').replace(' ', '_')}"
                fila[col_name] = int(self.regex_cache[skill].search(str(texto)) is not None)
            # Procesar soft skills
            for skill in self.soft_skills:
                col_name = f"soft_{skill.replace(' ', '_')}"
                fila[col_name] = int(self.regex_cache[skill].search(str(texto)) is not None)
            resultados.append(fila)
        
        return pd.DataFrame(resultados)