import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

URL_ACTA = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpPartido?cod_primaria=1000120&CodActa=2734059"

res = requests.get(URL_ACTA, headers=HEADERS)
soup = BeautifulSoup(res.text, 'html.parser')

# Buscar títulos o tablas superiores con los nombres de los clubes
print("=== CONTENIDO DEL ACTA 2734059 (FERNÁNDEZ PISTÓN) ===")
headers = soup.find_all(['h1', 'h2', 'h3', 'th', 'td', 'title'])
for h in headers:
    txt = h.get_text().strip()
    if len(txt) > 3 and not re.search(r'(Jugador|Minuto|Licencia|F.Nac)', txt, re.I):
        if any(kw in txt.upper() for kw in ['VS', '-', 'CLUB', 'C.F.', 'U.D.', 'C.D.', 'REAL', 'ATLETICO', 'SPORTING']):
            print(f" -> {txt}")