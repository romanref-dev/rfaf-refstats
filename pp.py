import requests
import re
from bs4 import BeautifulSoup

URL_ACTA = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpPartido?cod_primaria=1000120&CodActa=2733986&cod_acta=2733986"

def test_tarjetas():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.get(URL_ACTA, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    iconos = soup.find_all('img', src=re.compile(r'tarj_(amar|roja)', re.IGNORECASE))
    print(f"🔍 Total iconos de tarjeta encontrados: {len(iconos)}\n")
    
    for i, img in enumerate(iconos):
        texto = img.find_parent('tr').get_text(" ", strip=True) if img.find_parent('tr') else "Sin texto"
        es_roja = "roja" in img.get('src', '').lower()
        tipo = "ROJA" if es_roja else "AMARILLA"
        
        print(f"--- Tarjeta {i+1} ({tipo}) | Texto: {texto[:40]}... ---")
        
        # Analizar la jerarquía de tablas de afuera hacia adentro
        padres_td = img.find_parents('td')
        print(f"  Niveles de TD anidados: {len(padres_td)}")
        
        for j, td in enumerate(reversed(padres_td)):
            tr = td.find_parent('tr')
            tds_hermanos = tr.find_all('td', recursive=False) if tr else []
            indice_mio = tds_hermanos.index(td) if td in tds_hermanos else -1
            print(f"  Nivel {j} (Padre externo): TR con {len(tds_hermanos)} columnas -> La tarjeta está en la columna índice [{indice_mio}]")
        print("\n")

if __name__ == "__main__":
    test_tarjetas()