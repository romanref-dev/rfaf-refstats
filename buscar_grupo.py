import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# URL de la competición general (División de Honor Senior)
URL_COMPETITION = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120&CodCompeticion=48466530&CodTemporada=22"

res = requests.get(URL_COMPETITION, headers=HEADERS)
soup = BeautifulSoup(res.text, 'html.parser')

print("=== BUSCANDO CÓDIGOS DE GRUPO EN LA RFAF ===\n")

# Buscar los desplegables o enlaces de grupos en la página
opciones_grupo = soup.find_all('option', string=re.compile(r'Grupo', re.I))

if opciones_grupo:
    for opt in opciones_grupo:
        print(f"Grupo: {opt.get_text().strip()} | Value (CodGrupo): {opt.get('value')}")
else:
    # Si no hay select, buscamos enlaces que contengan CodGrupo
    enlaces = soup.find_all('a', href=re.compile(r'CodGrupo=\d+', re.I))
    for a in enlaces:
        match = re.search(r'CodGrupo=(\d+)', a['href'])
        if match:
            print(f"Texto: {a.get_text().strip()} | CodGrupo: {match.group(1)}")