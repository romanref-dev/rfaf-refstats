from bs4 import BeautifulSoup
import re

with open("jornada1_get.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
tablas = soup.find_all('table')

print("=" * 70)
print(f" 🔬 INSPECCIONANDO LAS {len(tablas)} TABLAS DE 'jornada1_get.html'")
print("=" * 70)

for idx, tabla in enumerate(tablas):
    filas = tabla.find_all('tr')
    # Buscar si la tabla contiene texto de partidos o resultados
    texto_tabla = tabla.text.strip()
    
    # Imprimir un resumen de cada tabla
    print(f"\n📋 TABLA #{idx + 1} ({len(filas)} filas):")
    
    # Imprimir las primeras 3 filas de la tabla para identificar la que tiene los partidos
    for f_idx, fila in enumerate(filas[:4]):
        celdas = [c.text.strip() for c in fila.find_all(['td', 'th']) if c.text.strip()]
        if celdas:
            print(f"   Fila {f_idx + 1}: {' | '.join(celdas)}")
            
    # Buscar enlaces dentro de esta tabla específica
    enlaces = tabla.find_all('a', href=True)
    if enlaces:
        print(f"   🔗 Enlaces en Tabla #{idx + 1}:")
        for a in enlaces[:3]:
            print(f"      -> {a.text.strip()} [href='{a['href']}']")

print("\n" + "=" * 70)