import json
from datetime import datetime

def formatear_metricas():
    try:
        with open("data/metricas_recursos.json", "r") as f:
            lineas = f.readlines()
        
        metricas = [json.loads(l) for l in lineas]
        
        print("\n" + "="*80)
        print("REPORTE DE CONSUMO DE RECURSOS")
        print("="*80 + "\n")
        
        for i, m in enumerate(metricas[-10:], 1):  # Últimas 10 consultas
            print(f"Consulta #{i} - {m['carrera']}")
            print(f"  Tiempo: {m['tiempo_total_seg']} segundos")
            print(f"  CPU promedio: {m['cpu_promedio_percent']}%")
            print(f"  RAM promedio: {m['ram_promedio_mb']} MB")
            print(f"  {m['timestamp']}")
            print()
        
        # Promedios generales
        cpu_prom = sum(m['cpu_promedio_percent'] for m in metricas) / len(metricas)
        ram_prom = sum(m['ram_promedio_mb'] for m in metricas) / len(metricas)
        tiempo_prom = sum(m['tiempo_total_seg'] for m in metricas) / len(metricas)
        
        print("="*80)
        print("ESTADÍSTICAS GENERALES")
        print("="*80)
        print(f"Total consultas registradas: {len(metricas)}")
        print(f"CPU promedio: {cpu_prom:.2f}%")
        print(f"RAM promedio: {ram_prom:.2f} MB")
        print(f"Tiempo promedio: {tiempo_prom:.4f} segundos")
        print("="*80 + "\n")
        
    except FileNotFoundError:
        print("No se encontró archivo de métricas. Realiza algunas consultas primero.")

if __name__ == "__main__":
    formatear_metricas()
