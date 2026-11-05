import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

URL_VELEZ = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpPartido?cod_primaria=1000120&CodActa=2734064"

res = requests.get(URL_VELEZ, headers=HEADERS)
soup = BeautifulSoup(res.text, 'html.parser')

# Buscar los bloques que van justo debajo de los <h4>Tarjetas</h4>
h4s = soup.find_all('h4', string=re.compile(r'Tarjetas', re.I))

print(f"Se han encontrado {len(h4s)} cabeceras 'Tarjetas'.\n")

for idx, h4 in enumerate(h4s, 1):
    print(f"--- BLOQUE DE TARJETAS #{idx} ---")
    # Buscar la primera tabla o div hermano justo después del h4
    siguiente = h4.find_next(['table', 'div'])
    if siguiente:
        # Imprimir las filas tr de la tabla para ver el motivo/tipo de cada tarjeta
        filas = siguiente.find_all('tr')
        for f in filas:
            txt_fila = f.get_text().strip()
            if re.search(r'\(\d+\'\)', txt_fila):
                print(f"  Row -> {txt_fila}")