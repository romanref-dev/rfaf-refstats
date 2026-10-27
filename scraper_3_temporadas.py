import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup
import psycopg2
from tqdm import tqdm

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rfaf_db")

TEMPORADAS = {
    "2023-2024": "23/24",
    "2024-2025": "24/25",
    "2025-2026": "25/26"
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/123.0.0.0 Safari/537.36"
]

def get_db():
    return psycopg2.connect(DB_URL)

def procesar_acta(acta_id, temporada_tag):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM partidos WHERE acta_id = %s", (str(acta_id),))
    if cur.fetchone():
        conn.close()
        return False

    url = f"https://www.rfaf.es/pnfg/NPfd-Partido?cod_primaria=3000856&cod_partido={acta_id}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            conn.close()
            return False

        soup = BeautifulSoup(response.text, 'html.parser')

        elem_arbitro = soup.find(text=re.compile(r'ÁRBITRO|Árbitro principal', re.IGNORECASE))
        if not elem_arbitro:
            conn.close()
            return False

        nombre_arbitro = "DESCONOCIDO"
        delegacion = "Andalucía"

        if elem_arbitro.parent:
            texto_raw = elem_arbitro.parent.text.replace("Árbitro principal:", "").strip().upper()
            del_match = re.search(r'\((.*?)\)', texto_raw)
            if del_match:
                delegacion = del_match.group(1).strip().title()
                nombre_arbitro = re.sub(r'\(.*?\)', '', texto_raw).strip()
            else:
                nombre_arbitro = texto_raw

        cur.execute("INSERT INTO delegaciones (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (delegacion,))
        cur.execute("SELECT id FROM delegaciones WHERE nombre = %s", (delegacion,))
        delegacion_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO arbitros (nombre, delegacion_id, partidos_totales) 
            VALUES (%s, %s, 1)
            ON CONFLICT (nombre, delegacion_id) 
            DO UPDATE SET partidos_totales = arbitros.partidos_totales + 1
            RETURNING id;
        """, (nombre_arbitro, delegacion_id))
        arbitro_id = cur.fetchone()[0]

        amarillas_loc = len(soup.select(".tarjeta-amarilla-local, img[src*='amarilla']"))
        amarillas_vis = len(soup.select(".tarjeta-amarilla-visitante"))
        rojas_loc = len(soup.select(".tarjeta-roja-local, img[src*='roja']"))
        rojas_vis = len(soup.select(".tarjeta-roja-visitante"))
        
        categoria_elem = soup.find('div', class_='nombre-competicion')
        categoria = categoria_elem.text.strip() if categoria_elem else "1ª Andaluza"

        cur.execute("""
            INSERT INTO partidos 
            (acta_id, temporada, categoria, equipo_local, equipo_visitante, arbitro_id, amarillas_local, amarillas_visitante, rojas_local, rojas_visitante)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (str(acta_id), temporada_tag, categoria, "Local", "Visitante", arbitro_id, amarillas_loc, amarillas_vis, rojas_loc, rojas_vis))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        conn.close()
        return False

def ejecutar_barrido_3_temporadas(rangos_por_temporada):
    for temp_nombre, config in rangos_por_temporada.items():
        tag = TEMPORADAS[temp_nombre]
        inicio, fin = config["inicio"], config["fin"]
        print(f"\n🚀 Iniciando extracción Temporada {temp_nombre} ({tag}) | Rango IDs: {inicio} -> {fin}")

        n_procesados = 0
        for acta_id in tqdm(range(inicio, fin + 1)):
            guardado = procesar_acta(acta_id, tag)
            if guardado:
                n_procesados += 1
                time.sleep(random.uniform(1.5, 2.5))
            else:
                time.sleep(0.1)

        print(f"✅ Temporada {temp_nombre} completada. {n_procesados} nuevos partidos registrados.")

if __name__ == "__main__":
    RANGOS_RFAF = {
        "2023-2024": {"inicio": 180000, "fin": 180050},
        "2024-2025": {"inicio": 210000, "fin": 210050},
        "2025-2026": {"inicio": 240000, "fin": 240050}
    }
    ejecutar_barrido_3_temporadas(RANGOS_RFAF)