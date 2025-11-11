import psutil  # Librería para acceder a información del sistema operativo
import time    # Para medir tiempo transcurrido
import json    # Para guardar datos en formato JSON
from datetime import datetime  # Para registrar timestamps

class MonitorRecursos:
    """
    Clase que monitorea el consumo de CPU y RAM del proceso de Python
    
    CÓMO FUNCIONA:
    - psutil.Process() obtiene el proceso actual de Python
    - cpu_percent() mide el % de CPU usado por este proceso
    - memory_info().rss obtiene la RAM en bytes (Resident Set Size)
    """
    def __init__(self):
        # Obtiene referencia al proceso actual de Python
        self.proceso = psutil.Process()
        self.inicio = None
        self.metricas = []
    
    def iniciar_monitoreo(self):
        """
        Captura el estado inicial antes de ejecutar la consulta
        
        NOTA: Usamos RSS (Resident Set Size) que mide la memoria física real.
        Task Manager puede mostrar valores ligeramente diferentes porque usa
        'Private Working Set', pero RSS es el estándar para medir consumo real.
        """
        self.inicio = time.time()
        self.metricas = []
        mi = self.proceso.memory_info()
        return {
            "cpu_inicial": self.proceso.cpu_percent(interval=0.1),
            "ram_inicial_mb": mi.rss / 1024 / 1024,  # RSS = memoria física real
            "timestamp": datetime.now().isoformat()
        }
    
    def capturar_metrica(self):
        """
        Toma una 'foto' del estado actual durante la ejecución
        
        SE USA EN:
        - Después de consultar la base de datos
        - Después de procesar el DataFrame
        - Después de calcular estadísticas
        
        Esto permite ver CUÁNDO sube el consumo
        """
        mi = self.proceso.memory_info()
        metrica = {
            "tiempo_transcurrido": time.time() - self.inicio,
            "cpu_percent": self.proceso.cpu_percent(interval=0.1),
            "ram_mb": mi.rss / 1024 / 1024,
            "timestamp": datetime.now().isoformat()
        }
        self.metricas.append(metrica)
        return metrica
    
    def finalizar_monitoreo(self):
        """
        Calcula promedios y resumen final
        
        FÓRMULAS:
        - Tiempo total = tiempo_fin - tiempo_inicio
        - CPU promedio = suma(todas_lecturas_cpu) / cantidad_lecturas
        - RAM promedio = suma(todas_lecturas_ram) / cantidad_lecturas
        """
        tiempo_total = time.time() - self.inicio
        cpu_promedio = sum(m["cpu_percent"] for m in self.metricas) / len(self.metricas) if self.metricas else 0
        ram_promedio = sum(m["ram_mb"] for m in self.metricas) / len(self.metricas) if self.metricas else 0
        
        return {
            "tiempo_total_seg": round(tiempo_total, 4),
            "cpu_promedio_percent": round(cpu_promedio, 2),
            "ram_promedio_mb": round(ram_promedio, 2),
            "num_muestras": len(self.metricas),
            "metricas_detalladas": self.metricas
        }
