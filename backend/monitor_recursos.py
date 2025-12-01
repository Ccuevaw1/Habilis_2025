import psutil  
import time   
import json   
from datetime import datetime  

class MonitorRecursos:

    def __init__(self):
        # Obtiene referencia al proceso actual de Python
        self.proceso = psutil.Process()
        self.inicio = None
        self.metricas = []
    
    def iniciar_monitoreo(self):

        self.inicio = time.time()
        self.metricas = []
        # Primera captura
        self.capturar_metrica()
    
    def capturar_metrica(self):

        tiempo_transcurrido = time.time() - self.inicio
        cpu_percent = self.proceso.cpu_percent(interval=0.1)
        ram_mb = self.proceso.memory_info().rss / (1024 * 1024)
        
        self.metricas.append({
            'tiempo_transcurrido': tiempo_transcurrido,
            'cpu_percent': cpu_percent,
            'ram_mb': ram_mb,
            'timestamp': time.time()
        })
    
    def finalizar_monitoreo(self):

        tiempo_total = time.time() - self.inicio
        
        if not self.metricas:
            return {
                'tiempo_total_seg': round(tiempo_total, 4),
                'cpu_promedio_percent': 0.0,
                'ram_promedio_mb': 0.0,
                'ram_max_mb': 0.0,
                'num_muestras': 0,
                'metricas_detalladas': []
            }
        
        cpu_promedio = sum(m['cpu_percent'] for m in self.metricas) / len(self.metricas)
        ram_promedio = sum(m['ram_mb'] for m in self.metricas) / len(self.metricas)
        ram_max = max(m['ram_mb'] for m in self.metricas)
        
        from datetime import datetime
        metricas_formateadas = [
            {
                'tiempo_transcurrido': m['tiempo_transcurrido'],
                'cpu_percent': m['cpu_percent'],
                'ram_mb': m['ram_mb'],
                'timestamp': datetime.fromtimestamp(m['timestamp']).isoformat()
            }
            for m in self.metricas
        ]
        
        return {
            'tiempo_total_seg': round(tiempo_total, 4),
            'cpu_promedio_percent': round(cpu_promedio, 2),
            'ram_promedio_mb': round(ram_promedio, 2),
            'ram_max_mb': round(ram_max, 2),
            'num_muestras': len(self.metricas),
            'metricas_detalladas': metricas_formateadas
        }
