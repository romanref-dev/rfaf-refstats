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

def obtener_conexion():
    if not DB_URL:
        raise ValueError("DATABASE_URL no está configurada en el archivo .env.")
    return psycopg2.connect(DB_URL)

def limpiar_nombre_arbitro(texto_raw):
    if not texto_raw or "Desconocido" in texto_raw:
        return "Desconocido"
    
    corte = re.split(r'\b(?:DELEGACI[OÓ]N|ASISTENTE)\b', texto_raw, flags=re.IGNORECASE)
    nombre = corte[0].strip()
    nombre = re.sub(r'^(?:ÁRBITRO PRINCIPAL|ÁRBITRO|ARBITRO)[:\s]*', '', nombre, flags=re.IGNORECASE).strip()
    nombre = nombre.rstrip(',').strip()

    return nombre if len(nombre) > 2 else "Desconocido"

def obtener_html(session, url, max_reintentos=3):
    for _ in range(max_reintentos):
        try:
            res = session.get(url, headers=HEADERS, timeout=12)
            if res.status_code == 200:
                return res.text
        except Exception:
            time.sleep(2)
    return None

def extraer_sanciones_acta(session, url_acta):
    """
    Lee las tarjetas y el árbitro del acta individual.
    """
    html = obtener_html(session, url_acta)
    if not html:
        return {"arbitro": "Desconocido", "amarillas": 0, "rojas": 0}

    soup = BeautifulSoup(html, 'html.parser')
    texto_pagina = soup.get_text()

    # 1. Extraer Árbitro Principal
    arbitro = "Desconocido"
    elem_arbitro = soup.find(string=re.compile(r'^\s*ARBITRO\s*$', re.I))
    
    if elem_arbitro:
        padre = elem_arbitro.parent
        siguiente = padre.find_next_sibling() or padre.find_next()
        if siguiente:
            arbitro = limpiar_nombre_arbitro(siguiente.get_text().strip())

    if arbitro == "Desconocido":
        match = re.search(r'ARBITRO\s+([A-Za-zÁÉÍÓÚáéíóúÑñ\s,]+?)(?=DELEGACI[OÓ]N|ASISTENTE)', texto_pagina, re.I)
        if match:
            arbitro = limpiar_nombre_arbitro(match.group(1))

    # 2. Conteo de Tarjetas
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
        "amarillas": amarillas,
        "rojas": rojas
    }

def escanear_y_actualizar_jornada(url_jornada, categoria="División de Honor Senior", jornada=8):
    print(f"[{datetime.datetime.now()}] Sincronizando datos de la RFAF (Jornada {jornada})...")

    session = requests.Session()
    html_jornada = obtener_html(session, url_jornada)
    if not html_jornada:
        print("Error descargando la página de la jornada.")
        return

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
                
                # Extraer equipos y goles de forma limpia
                match_partido = re.search(r'^(.+?)\s+(\d+)\s*-\s*(\d+)\s+(.+?)(?=\s+\d{2}[-/]\d{2}[-/]\d{4}|\s+\d{2}:\d{2}|$)', txt_fila)
                
                if match_partido:
                    eq_local = match_partido.group(1).strip()
                    g_local = int(match_partido.group(2))
                    g_visitante = int(match_partido.group(3))
                    
                    eq_visitante_raw = match_partido.group(4).strip()
                    eq_visitante = re.sub(r'\s*\d{2}[-/]\d{2}[-/]\d{4}.*', '', eq_visitante_raw).strip()
                    eq_visitante = re.sub(r'\s*\d{2}:\d{2}.*', '', eq_visitante).strip()
                    
                    eq_local = eq_local[:60]
                    eq_visitante = eq_visitante[:60]
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

    print(f"Detectadas {len(partidos_dict)} actas únicas en la jornada. Procesando...")

    partidos_batch = []
    for idx, (acta_id, pdata) in enumerate(partidos_dict.items(), start=1):
        sanciones = extraer_sanciones_acta(session, pdata["url_acta"])

        print(f" -> [{idx}/{len(partidos_dict)}] {acta_id} | {pdata['equipo_local']} ({pdata['goles_local']}) vs ({pdata['goles_visitante']}) {pdata['equipo_visitante']} | Árbitro: {sanciones['arbitro']} | Amarillas: {sanciones['amarillas']} | Rojas: {sanciones['rojas']}")

        partidos_batch.append((
            acta_id,
            datetime.date.today().strftime('%Y-%m-%d'),
            categoria,
            jornada,
            pdata['equipo_local'],
            pdata['equipo_visitante'],
            pdata['goles_local'],
            pdata['goles_visitante'],
            sanciones['arbitro'],
            sanciones['amarillas'],
            sanciones['rojas']
        ))

        time.sleep(1.5)

    if partidos_batch:
        conn = None
        try:
            conn = obtener_conexion()
            cur = conn.cursor()

            query = """
                INSERT INTO partidos (
                    acta_id, fecha, categoria, jornada, 
                    equipo_local, equipo_visitante, goles_local, goles_visitante, 
                    arbitro, tarjetas_amarillas, tarjetas_rojas
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (acta_id) DO UPDATE SET
                    equipo_local = EXCLUDED.equipo_local,
                    equipo_visitante = EXCLUDED.equipo_visitante,
                    goles_local = EXCLUDED.goles_local,
                    goles_visitante = EXCLUDED.goles_visitante,
                    tarjetas_amarillas = EXCLUDED.tarjetas_amarillas,
                    tarjetas_rojas = EXCLUDED.tarjetas_rojas,
                    arbitro = EXCLUDED.arbitro;
            """
            cur.executemany(query, partidos_batch)
            conn.commit()
            cur.close()
            print(f"\n¡Éxito! Se han guardado/actualizado {len(partidos_batch)} partidos con datos limpios en Supabase.")
        except Exception as db_err:
            print(f"Error al guardar en Supabase: {db_err}")
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    URL_JORNADA_8 = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120&CodCompeticion=48466530&CodGrupo=49641343&CodTemporada=22&cod_agrupacion=&CodJornada=8&Sch_Codigo_Delegacion=&Sch_Tipo_Juego="
    escanear_y_actualizar_jornada(URL_JORNADA_8, categoria="División de Honor Senior", jornada=8)