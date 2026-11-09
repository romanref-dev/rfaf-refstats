from curl_cffi import requests
from bs4 import BeautifulSoup
import re

URL_ACTA = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpPartido?cod_primaria=1000120&CodActa=2733986&cod_acta=2733986"

r = requests.get(URL_ACTA, impersonate="chrome110")
html_raw = r.text.replace('&nbsp;', ' ')
soup = BeautifulSoup(html_raw, 'html.parser')

# La frontera real de tarjetas es la 2ª etiqueta "Tarjetas" del HTML
tarjetas_headers = [m.start() for m in re.finditer(r'Tarjetas', html_raw, re.I)]
pos_corte_tarjetas = tarjetas_headers[1] if len(tarjetas_headers) >= 2 else len(html_raw)

print(f"📍 Posición de corte de Tarjetas Visitante: {pos_corte_tarjetas}\n")

# Extraer tarjetas y buscar su posición en HTML usando rfind o contexto
iconos = soup.find_all('img', src=re.compile(r'tarj_(amar|roja)', re.I))

for img in iconos:
    contenedor = img.find_parent('tr') or img.parent
    texto = contenedor.get_text(" ", strip=True)
    
    match = re.search(r'([A-ZÁÉÍÓÚÑ\s,\.\-]+)', texto, re.I)
    if match:
        nombre = match.group(1).strip()
        # Buscamos el nombre desde la 2ª mitad del HTML si es posible, o usamos la ocurrencia exacta
        # Si el bloque del contenedor en texto aparece después del corte de Tarjetas
        pos_html = html_raw.rfind(nombre) if "PINTO" in nombre or "ROMERO" in nombre else html_raw.find(nombre)
        
        equipo = "VISITANTE" if pos_html >= pos_corte_tarjetas else "LOCAL"
        print(f"Pos HTML: {pos_html} | {nombre} -> {equipo}")