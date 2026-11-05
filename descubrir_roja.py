import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

URL_VELEZ = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpPartido?cod_primaria=1000120&CodActa=2734064"

res = requests.get(URL_VELEZ, headers=HEADERS)
soup = BeautifulSoup(res.text, 'html.parser')

h4s = soup.find_all('h4', string=re.compile(r'Tarjetas', re.I))

for idx, h4 in enumerate(h4s, 1):
    siguiente = h4.find_next(['table', 'div'])
    if siguiente:
        filas = siguiente.find_all('tr')
        for f in filas:
            if "ARIAS SANCHEZ" in f.get_text() or "(89')" in f.get_text():
                print("=== FILA DE LA EXPULSIÓN (RAW HTML) ===")
                print(f)
                print("\n=== IMÁGENES DENTRO DE ESTA FILA ===")
                print(f.find_all('img'))
                print("\n=== ATRIBUTOS Y CLASES DE LA FILA ===")
                print(f.attrs)