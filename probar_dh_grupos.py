import os
import re
import time
import datetime
import requests
from bs4 import BeautifulSoup
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
BASE_URL = "https://www.rfaf.es"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9"
}

# Configuración con las IDs REALES obtenidas de la RFAF
GRUPOS_DH_SENIOR = [
    {
        "categoria": "División de Honor Senior",
        "grupo": "Grupo 1",
        "cod_competicion": "48466530",
        "cod_grupo": "49641343"
    },
    {
        "categoria": "División de Honor Senior",
        "grupo": "Grupo 2",
        "cod_competicion": "48466530",
        "cod_grupo": "48933162"  # <-- ID CORREGIDA
    }
]

def obtener_conexion():
    if not DB_URL:
        raise ValueError("DATABASE_URL no está configurada en el archivo .env.")
    return psycopg2.connect(DB_URL)

def limpiar_nombre_y_delegacion(texto_raw):
    if not texto_raw or "Desconocido" in texto_raw:
        return "Desconocido", "Desconocida"

    match_del = re.search(r'DELEGACI[OÓ]N\s+(?:DE\s+)?([A-Za-zÁÉÍÓÚáéíóúÑñ\s]+)', texto_raw, re.I)
    delegacion = match_del.group(1).strip().title() if match_del else "Desconocida"

    corte = re.split(r'\b(?:DELEGACI[OÓ]N|ASISTENTE)\b', texto_raw, flags=re.IGNORECASE)
    nombre = corte[0].strip()
    nombre = re.sub(r'^(?:ÁRBITRO PRINCIPAL|ÁRBITRO|ARBITRO)[:\s]*', '', nombre, flags=re.IGNORECASE).strip().rstrip(',')

    return (nombre if len(nombre) > 2 else "Desconocido"), delegacion

def obtener_html(session, url, max_reintentos=3):
    for _ in range(max_reintentos):
        try:
            res = session.get(url, headers=HEADERS, timeout=12)
            if res.status_code == 200:
                return res.text
        except Exception:
            time.sleep(2)
    return None

def extraer_detalles_acta(session, url_acta):
    html = obtener_html(session, url_acta)
    if not html:
        return {"arbitro": "Desconocido", "delegacion": "Desconocida", "amarillas": 0, "rojas": 0}

    soup = BeautifulSoup(html, 'html.parser')
    texto_pagina = soup.get_text()

    arbitro = "Desconocido"
    delegacion = "Desconocida"

    elem_arbitro = soup.find(string=re.compile(r'^\s*ARBITRO\s*$', re.I))
    if elem_arbitro:
        padre = elem_arbitro.parent
        siguiente = padre.find_next_sibling() or padre.find_next()
        if siguiente:
            arbitro, delegacion = limpiar_nombre_y_delegacion(siguiente.get_text().strip())

    if arbitro == "Desconocido":
        match = re.search(r'ARBITRO\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s,]+?)(?=DELEGACI[OÓ]N|ASISTENTE)', texto_pagina, re.I)
        if match:
            arbitro, delegacion = limpiar_nombre_y_delegacion(match.group(1))

    amarillas = 0
    rojas = 0
    h4s_tarjetas = soup.find_all('h4', string=re.compile(r'Tarjetas', re.I))

    for h4 in h4s_tarjetas:
        siguiente_bloque = h4.find_next(['table', 'div'])
        if siguiente_bloque:
            filas = siguiente_bloque.find_all('tr')
            for f in filas:
                txt_fila = f.get_text().strip()
                if re.search(r'\(\d+\'\)', txt_fila):
                    img = f.find('img')
                    src = img.get('src', '').lower() if img else ''
                    if 'roja' in src or re.search(r'(Expulsi[oó]n|Roja Directa)', txt_fila, re.I):
                        rojas += 1
                    else:
                        amarillas += 1

    if amarillas == 0 and rojas == 0:
        amarillas = len(re.findall(r'\(\d+\'\)', texto_pagina))

    return {
        "arbitro": arbitro,
        "delegacion": delegacion,
        "amarillas": amarillas,
        "rojas": rojas
    }

def procesar_jornada(session, url_jornada, categoria, grupo, jornada):
    html_jornada = obtener_html(session, url_jornada)
    if not html_jornada:
        return []

    soup = BeautifulSoup(html_jornada, 'html.parser')
    filas = soup.find_all('tr')
    partidos_dict = {}

    for fila in filas:
        a_acta = fila.find('a', href=re.compile(r'(NFG_CmpActa|codacta)', re.I))
        if a_acta:
            href = a_acta['href']
            url_acta = BASE_URL + href if href.startswith('/') else href
            cod_match = re.search(r'CodActa=(\d+)', url_acta, re.I) or re.search(r'cod_acta=(\d+)', url_acta, re.I)
            acta_id = f"RFAF-{cod_match.group(1)}" if cod_match else None

            if acta_id and acta_id not in partidos_dict:
                txt_fila = ' '.join(fila.get_text().split())
                match_partido = re.search(r'^(.+?)\s+(\d+)\s*-\s*(\d+)\s+(.+?)(?=\s+\d{2}[-/]\d{2}[-/]\d{4}|\s+\d{2}:\d{2}|$)', txt_fila)
                
                if match_partido:
                    eq_local = match_partido.group(1).strip()[:60]
                    g_local = int(match_partido.group(2))
                    g_visitante = int(match_partido.group(3))
                    eq_visitante_raw = match_partido.group(4).strip()
                    eq_visitante = re.sub(r'\s*\d{2}[-/]\d{2}[-/]\d{4}.*', '', eq_visitante_raw).strip()
                    eq_visitante = re.sub(r'\s*\d{2}:\d{2}.*', '', eq_visitante)[:60].strip()
                else:
                    eq_local = "Equipo Local"
                    eq_visitante = "Equipo Visitante"
                    g_local = 0
                    g_visitante = 0

                partidos_dict[acta_id] = {
                    "url_acta": url_acta,
                    "equipo_local": eq_local,
                    "equipo_visitante": eq_visitante,
                    "goles_local": g_local,
                    "goles_visitante": g_visitante
                }

    total_actas = len(partidos_dict)
    if total_actas == 0:
        return []

    print(f" -> Encontradas {total_actas} actas. Procesando...")

    partidos_batch = []
    for idx, (acta_id, pdata) in enumerate(partidos_dict.items(), start=1):
        print(f"    [{idx}/{total_actas}] Leyendo acta {acta_id}...")
        detalles = extraer_detalles_acta(session, pdata["url_acta"])

        partidos_batch.append((
            acta_id,
            datetime.date.today().strftime('%Y-%m-%d'),
            categoria,
            grupo,
            jornada,
            pdata['equipo_local'],
            pdata['equipo_visitante'],
            pdata['goles_local'],
            pdata['goles_visitante'],
            detalles['arbitro'],
            detalles['delegacion'],
            detalles['amarillas'],
            detalles['rojas']
        ))
        time.sleep(1)

    return partidos_batch

def guardar_partidos(partidos_batch):
    if not partidos_batch:
        return
    conn = None
    try:
        conn = obtener_conexion()
        cur = conn.cursor()

        query = """
            INSERT INTO partidos (
                acta_id, fecha, categoria, grupo, jornada, 
                equipo_local, equipo_visitante, goles_local, goles_visitante, 
                arbitro, delegacion, tarjetas_amarillas, tarjetas_rojas
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (acta_id) DO UPDATE SET
                categoria = EXCLUDED.categoria,
                grupo = EXCLUDED.grupo,
                equipo_local = EXCLUDED.equipo_local,
                equipo_visitante = EXCLUDED.equipo_visitante,
                goles_local = EXCLUDED.goles_local,
                goles_visitante = EXCLUDED.goles_visitante,
                arbitro = EXCLUDED.arbitro,
                delegacion = EXCLUDED.delegacion,
                tarjetas_amarillas = EXCLUDED.tarjetas_amarillas,
                tarjetas_rojas = EXCLUDED.tarjetas_rojas;
        """
        cur.executemany(query, partidos_batch)
        conn.commit()
        cur.close()
    except Exception as db_err:
        print(f"Error en Supabase: {db_err}")
    finally:
        if conn:
            conn.close()

def escanear_jornada_8_ambos_grupos():
    session = requests.Session()
    jornada_objetivo = 8

    for gconf in GRUPOS_DH_SENIOR:
        print(f"\n==========================================")
        print(f" ESCANEANDO JORNADA {jornada_objetivo} - {gconf['grupo'].upper()}")
        print(f"==========================================")

        url = f"https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120&CodCompeticion={gconf['cod_competicion']}&CodGrupo={gconf['cod_grupo']}&CodTemporada=22&CodJornada={jornada_objetivo}"
        
        batch = procesar_jornada(session, url, gconf['categoria'], gconf['grupo'], jornada_objetivo)
        if batch:
            guardar_partidos(batch)
            print(f" -> ¡Éxito! Guardados {len(batch)} partidos del {gconf['grupo']}.")
        else:
            print(f" -> No se encontraron partidos para el {gconf['grupo']}.")

if __name__ == "__main__":
    escanear_jornada_8_ambos_grupos()