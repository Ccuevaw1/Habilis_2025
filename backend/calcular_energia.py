import json
from datetime import datetime

# CONSTANTES BASADAS EN ESPECIFICACIONES TÉCNICAS
TDP_CPU_PROMEDIO = 65  # Watts - TDP típico de CPU servidor Intel Xeon/AMD EPYC
CONSUMO_RAM_POR_GB = 3  # Watts por GB - Valor estándar industria DDR4
RAM_TOTAL_GB = 16  # Ajustar según tu servidor

def calcular_energia_por_consulta(metricas):
    """
    Calcula energía consumida usando física básica: E = P × t
    
    FÓRMULAS EXPLICADAS:
    
    1. POTENCIA CPU:
       P_cpu = (CPU% / 100) × TDP_cpu
       
       RAZÓN: El TDP (Thermal Design Power) es la potencia máxima.
       Si CPU está al 50%, consume 50% del TDP.
       
       EJEMPLO: CPU al 30% con TDP 65W
       P_cpu = (30/100) × 65W = 19.5W
    
    2. POTENCIA RAM:
       P_ram = (RAM_usada_GB) × 3W/GB
       
       RAZÓN: Cada GB de RAM DDR4 consume ~3W en uso activo.
       
       EJEMPLO: 150MB = 0.146GB
       P_ram = 0.146 × 3 = 0.438W
    
    3. ENERGÍA TOTAL:
       E = (P_cpu + P_ram) × tiempo_segundos / 3600
       
       RAZÓN: Energía = Potencia × Tiempo
       Dividimos entre 3600 para convertir de Watt-segundo a Watt-hora (Wh)
       
       EJEMPLO: 19.5W + 0.438W = 19.938W durante 0.5 segundos
       E = 19.938 × 0.5 / 3600 = 0.00277 Wh = 2.77 mWh
    
    4. EMISIONES CO2:
       CO2 = (Energía_kWh) × Factor_emisión
       
       RAZÓN: Factor promedio mundial = 0.5 kg CO2/kWh
       (Varía por país: Perú ~0.4, EE.UU. ~0.4, China ~0.6)
       
       EJEMPLO: 0.00277 Wh = 0.00000277 kWh
       CO2 = 0.00000277 × 0.5 = 0.000001385 kg = 0.001385 g
    """
    
    # Extraer datos de las métricas capturadas
    cpu_percent = metricas["cpu_promedio_percent"]
    ram_mb = metricas["ram_promedio_mb"]
    tiempo_seg = metricas["tiempo_total_seg"]
    
    # PASO 1: Calcular potencia consumida por CPU
    potencia_cpu = (cpu_percent / 100) * TDP_CPU_PROMEDIO
    
    # PASO 2: Calcular potencia consumida por RAM
    ram_gb = ram_mb / 1024  # Convertir MB a GB
    potencia_ram = ram_gb * CONSUMO_RAM_POR_GB
    
    # PASO 3: Potencia total en Watts
    potencia_total_w = potencia_cpu + potencia_ram
    
    # PASO 4: Calcular energía en Watt-hora (Wh)
    # Energía = Potencia × Tiempo
    # 1 hora = 3600 segundos, por eso dividimos
    energia_wh = (potencia_total_w * tiempo_seg) / 3600
    
    # PASO 5: Calcular emisiones de CO2
    # Factor de emisión promedio: 0.5 kg CO2 por kWh
    co2_kg = (energia_wh / 1000) * 0.5  # Convertir Wh a kWh
    
    # PASO 6: Calcular equivalencia comprensible
    # Un LED de 10W en 1 minuto consume: 10W × (1/60)h = 0.167 Wh
    minutos_led = (energia_wh / 10) * 60
    
    return {
        "energia_wh": round(energia_wh, 6),
        "potencia_promedio_w": round(potencia_total_w, 2),
        "co2_gramos": round(co2_kg * 1000, 4),
        "equivalente": f"Encender un LED 10W por {round(minutos_led, 1)} minutos"
    }

def analizar_archivo_metricas():
    """
    Lee todas las métricas guardadas y genera reporte total
    
    PROCESO:
    1. Lee archivo JSON línea por línea
    2. Calcula energía para cada consulta
    3. Suma totales
    4. Calcula promedios
    """
    with open("data/metricas_recursos.json", "r") as f:
        lineas = f.readlines()
    
    metricas_list = [json.loads(l) for l in lineas]
    
    total_energia = 0
    total_co2 = 0
    
    for m in metricas_list:
        calculo = calcular_energia_por_consulta(m)
        total_energia += calculo["energia_wh"]
        total_co2 += calculo["co2_gramos"]
    
    print(f"=== REPORTE CONSUMO ENERGÉTICO ===")
    print(f"Total consultas: {len(metricas_list)}")
    print(f"Energía total: {round(total_energia, 4)} Wh")
    print(f"CO2 total: {round(total_co2, 2)} gramos")
    print(f"Promedio por consulta: {round(total_energia/len(metricas_list), 6)} Wh")

if __name__ == "__main__":
    analizar_archivo_metricas()
