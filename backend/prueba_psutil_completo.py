import psutil
import time

proceso = psutil.Process()

def mb(x): return x / 1024 / 1024

def leer_memorias():
    mi = proceso.memory_info()
    rss = mb(mi.rss)  # Working Set (memoria física asignada al proceso)
    try:
        full = proceso.memory_full_info()
        wset = mb(getattr(full, "wset", mi.rss))        # Working Set total
        private = mb(getattr(full, "private", mi.rss))  # Private Working Set (exclusiva)
        uss = mb(getattr(full, "uss", mi.rss))          # Unique Set Size (exclusiva real)
    except Exception:
        wset = rss
        private = rss
        uss = rss
    return rss, wset, private, uss

print("\n=== MEMORIA (Windows) ===")
print(f"PID: {proceso.pid}")

input("Presiona ENTER para ver valores actuales...")

rss, wset, private, uss = leer_memorias()
print(f"\nValores actuales:")
print(f"  RSS / Working Set:       {rss:.2f} MB")
print(f"  Working Set (total):     {wset:.2f} MB")
print(f"  Private Working Set:     {private:.2f} MB")
print(f"  USS (Unique Set Size):   {uss:.2f} MB")

print(f"\nSugerencia de comparación:")
print(f"  - Pestaña 'Procesos' → columna Memory ≈ USS ≈ {uss:.2f} MB")
print(f"  - Pestaña 'Detalles' → columna Memory (Working Set) ≈ RSS/WSet ≈ {rss:.2f}/{wset:.2f} MB")

input("\nENTER para iniciar demostración de aumento de memoria...")

# DEMOSTRACIÓN:
# Cada iteración reserva ~10 MB en bytearray.
# Objetivo: mostrar relación directa entre asignación explícita y aumento inmediato en:
# - RSS / WSet (páginas residentes totales)
# - Private / USS (memoria exclusiva)
# Esto valida que los números varían por acción real y son adecuados para justificar medición de recursos en tu informe.
bloques = []
for i in range(1, 6):
    bloques.append(bytearray(10_000_000))  # ~10 MB cada paso
    time.sleep(0.5)
    rss, wset, private, uss = leer_memorias()
    print(f"Paso {i}: RSS={rss:.2f} MB | WSet={wset:.2f} MB | Private={private:.2f} MB | USS={uss:.2f} MB (≈ Procesos)")

input("\nENTER para liberar memoria...")
# # Al limpiar la lista se liberan las referencias → el GC y el allocator devuelven páginas.
# bloques.clear()
# time.sleep(1.0)
# rss, wset, private, uss = leer_memorias()
# print(f"Tras liberar: RSS={rss:.2f} MB | WSet={wset:.2f} MB | Private={private:.2f} MB | USS={uss:.2f} MB (≈ Procesos)")

# print("""
# Conclusión:
# - El aumento controlado demuestra causalidad: asignas → sube; liberas → baja.
# - Para tu presentación: justifica que las métricas de psutil provienen de interacción real con memoria física.
# - Usa RSS (o USS si quieres alinearte con lo que ve tu profesor en 'Procesos') para tu cálculo energético.
# """)
