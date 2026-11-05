import requests
from bs4 import BeautifulSoup
import re

URL_ACTA = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpPartido?cod_primaria=1000120&CodActa=2734056&cod_acta=2734056"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9"
}

res = requests.get(URL_ACTA, headers=headers)
soup = BeautifulSoup(res.text, 'html.parser')

print("--- 1. BÚSQUEDA DE IMÁGENES / ICONOS DE TARJETAS ---")
tarjetas_img = []
for img in soup.find_all('img'):
    src = img.get('src', '')
    title = img.get('title', '')
    alt = img.get('alt', '')
    if any(k in (src + title + alt).lower() for k in ['tarjeta', 'amarilla', 'roja', 'amonestacion', 'tar_']):
        tarjetas_img.append((src, title, alt))

print(f"Total imágenes de tarjetas detectadas: {len(tarjetas_img)}")
for src, title, alt in tarjetas_img:
    print(f" -> SRC: {src} | TITLE: {title} | ALT: {alt}")

print("\n--- 2. BÚSQUEDA DE TABLAS Y FILAS CON SANCIONES ---")
filas_amarillas = 0
filas_rojas = 0

for tr in soup.find_all('tr'):
    texto_fila = tr.get_text().strip()
    if re.search(r'amarilla|amonestaci[oó]n', texto_fila, re.I):
        filas_amarillas += 1
    if re.search(r'roja|expulsi[oó]n', texto_fila, re.I):
        filas_rojas += 1

print(f"Filas detectadas con amarillas/amonestaciones: {filas_amarillas}")
print(f"Filas detectadas con rojas/expulsiones: {filas_rojas}")

print("\n--- 3. BÚSQUEDA DEL ÁRBITRO PRINCIPAL ---")
for elem in soup.find_all(string=re.compile(r'ÁRBITRO|ARBITRO', re.I)):
    print(f"Coincidencia: '{elem.strip()}' -> Padre: '{elem.parent.get_text().strip()}'")