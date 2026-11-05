import requests
from bs4 import BeautifulSoup
import re

URL_INICIAL = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"
URL_EXEC = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada_Exec"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://www.rfaf.es/'
}

def descubrir_y_guardar():
    print("🔍 Conectando con la RFAF para extraer todas las competiciones disponibles...")
    
    session = requests.Session()
    res = session.get(URL_INICIAL, headers=HEADERS)
    
    if res.status_code != 200:
        print(f"❌ Error al conectar con RFAF (Código HTTP {res.status_code})")
        return

    soup = BeautifulSoup(res.text, 'html.parser')
    select_comp = soup.find('select', {'id': 'competicion'}) or soup.find('select', {'name': 'competicion'})
    
    if not select_comp:
        print("⚠️ No se encontró el desplegable de competiciones en el HTML.")
        return

    # Lista para almacenar las líneas que guardaremos en el archivo
    lineas_fichero = []
    lineas_fichero.append("# LISTADO OFICIAL DE COMPETICIONES RFAF\n")
    lineas_fichero.append("| Categoría / Grupo | Nombre de la Competición | ID Competición |")
    lineas_fichero.append("|-------------------|--------------------------|----------------|")

    categoria_actual = "GENERAL"
    total_encontradas = 0

    for elem in select_comp.children:
        # Si es un grupo de opciones (e.g. SENIOR, JUVENILES, CADETES...)
        if elem.name == 'optgroup':
            categoria_actual = elem.get('label', 'GENERAL').strip()
            for opt in elem.find_all('option'):
                val = opt.get('value', '').strip()
                texto = opt.get_text(strip=True)
                if val and val != "0":
                    lineas_fichero.append(f"| {categoria_actual} | {texto} | `{val}` |")
                    total_encontradas += 1

        # Si es una opción suelta fuera de optgroup
        elif elem.name == 'option':
            val = elem.get('value', '').strip()
            texto = elem.get_text(strip=True)
            if val and val != "0":
                lineas_fichero.append(f"| {categoria_actual} | {texto} | `{val}` |")
                total_encontradas += 1

    # Guardar en un archivo de texto / markdown
    nombre_archivo = "competiciones_rfaf.md"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas_fichero))

    print(f"\n✅ ¡Proceso completado con éxito!")
    print(f"📄 Se han guardado {total_encontradas} competiciones en el archivo: '{nombre_archivo}'")

if __name__ == "__main__":
    descubrir_y_guardar()