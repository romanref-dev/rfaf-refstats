import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

URL_JORNADA = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120&CodCompeticion=48466530&CodGrupo=49641343&CodTemporada=22&cod_agrupacion=&CodJornada=8&Sch_Codigo_Delegacion=&Sch_Tipo_Juego="

res = requests.get(URL_JORNADA, headers=HEADERS)
soup = BeautifulSoup(res.text, 'html.parser')

print("=== PARTIDOS ENCONTRADOS EN LA TABLA PRINCIPAL DE LA JORNADA 8 ===\n")

# Buscar todas las filas tr que contienen enlaces a actas
filas_partidos = soup.find_all('tr')

for idx, fila in enumerate(filas_partidos, 1):
    enlace_acta = fila.find('a', href=re.compile(r'(NFG_CmpActa|codacta)', re.I))
    if enlace_acta:
        texto_fila = ' '.join(fila.get_text().split())
        print(f"Partido {idx}: {texto_fila}")
        print(f" -> Enlace Acta: {enlace_acta['href']}\n")