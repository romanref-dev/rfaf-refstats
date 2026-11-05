import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import json
import re
import sys
import time
from bs4 import BeautifulSoup

from config import SUPABASE_URL, SUPABASE_KEY, COD_TEMPORADA, COD_COMPETICION_DH, GRUPOS_DH

# Instanciar gestor de cookies para emular la navegación real
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
opener.addheaders = [
    ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
    ("Accept-Language", "es-ES,es;q=0.9")
]

def obtener_html(url):
    try:
        req = urllib.request.Request(url, method='GET')
        with opener.open(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"   ⚠️ Error de red al acceder a {url}: {e}")
        return None

def parsear_y_auditar_acta(cod_partido, jornada_num, categoria_nombre):
    url_partido = f"https://www.rfaf.es/pnfg/NFG_CmpPartido?cod_primaria=1000120&CodPartido={cod_partido}"
    html = obtener_html(url_partido)
    if not html:
        return None, "ERROR_RED"

    soup = BeautifulSoup(html, 'html.parser')

    # 1. Extracción de Equipos
    local_nombre = "Desconocido"
    visitante_nombre = "Desconocido"
    elem_local = soup.find('div', class_='font_widgetL')
    elem_vis = soup.find('div', class_='font_widgetV')

    if elem_local: local_nombre = elem_local.text.strip()
    if elem_vis: visitante_nombre = elem_vis.text.strip()

    # 2. Extracción de Marcador
    goles_loc, goles_vis = 0, 0
    m = re.search(r'(\d+)\s*-\s*(\d+)', soup.text)
    if m:
        goles_loc, goles_vis = int(m.group(1)), int(m.group(2))

    # 3. Extracción de Árbitro y Delegación Oficial
    arbitro_nombre = "Desconocido"
    delegacion_nombre = "Sin Asignar"

    seccion_arbitros = soup.find('div', class_='desc') or soup
    spans_responsive = seccion_arbitros.find_all('span', class_='font_responsive')

    for span in spans_responsive:
        texto_span = span.text.strip()
        span_cursiva = span.find('span', class_='txtcursiva')
        
        if span_cursiva:
            delegacion_nombre = span_cursiva.text.strip()
            texto_limpio = texto_span.replace(delegacion_nombre, '').strip()
            if texto_limpio and len(texto_limpio) > 3:
                arbitro_nombre = texto_limpio
                break

    if delegacion_nombre == "Sin Asignar":
        match_del = re.search(r'DELEGACI[ÓO]N DE\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)', soup.text, re.IGNORECASE)
        if match_del:
            delegacion_nombre = f"Delegación de {match_del.group(1).strip().split()[0]}"

    arbitro_nombre = re.sub(r'\s+', ' ', arbitro_nombre).title()
    delegacion_nombre = re.sub(r'\s+', ' ', delegacion_nombre).title()

    amarillas = len(soup.find_all('img', src=lambda x: x and 'amarilla' in str(x).lower()))
    rojas = len(soup.find_all('img', src=lambda x: x and 'roja' in str(x).lower()))

    datos_partido = {
        "acta_id": f"RFAF-{cod_partido}",
        "fecha": "2026-10-28",
        "categoria": categoria_nombre,
        "jornada": jornada_num,
        "equipo_local": local_nombre,
        "equipo_visitante": visitante_nombre,
        "goles_local": goles_loc,
        "goles_visitante": goles_vis,
        "arbitro": arbitro_nombre,
        "delegacion": delegacion_nombre,
        "tarjetas_amarillas": amarillas,
        "tarjetas_rojas": rojas
    }

    # AUDITORÍA ESTRICTA
    campos_incompletos = []
    if local_nombre == "Desconocido" or visitante_nombre == "Desconocido":
        campos_incompletos.append("Equipos")
    if arbitro_nombre == "Desconocido":
        campos_incompletos.append("Árbitro")
    if delegacion_nombre == "Sin Asignar":
        campos_incompletos.append("Delegación")

    if campos_incompletos:
        info_debug = {
            "cod_partido": cod_partido,
            "campos_fallidos": campos_incompletos,
            "url": url_partido
        }
        return datos_partido, info_debug

    return datos_partido, None

def guardar_en_supabase(partido):
    if not partido:
        return False

    endpoint = f"{SUPABASE_URL}/rest/v1/partidos"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    data = json.dumps(partido).encode('utf-8')
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            return True
    except urllib.error.HTTPError as e:
        print(f"   ❌ Error Supabase HTTP {e.code} al guardar acta {partido.get('acta_id')}")
        return False

def ejecucion():
    print("=" * 75)
    print(" ⚽  RFAF REFSTATS - EXTRACCIÓN Y RECORRIDO OFICIAL POR JORNADAS  ⚽")
    print("=" * 75)

    # Handshake inicial para activar las cookies del servidor Novanet
    print("🔑 Inicializando sesión Novanet...")
    obtener_html("https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120&cod_agrupacion=1")

    total_guardados = 0

    for grp in GRUPOS_DH:
        print(f"\n===========================================================================")
        print(f"📂 COMPROBANDO Y EXTRAIENDO: {grp['nombre']}")
        print(f"===========================================================================")

        jornadas_vacias_seguidas = 0

        for jornada in range(1, grp["total_jornadas"] + 1):
            # URL idéntica a la que genera la función IrA(jornada) en la web oficial
            url_jornada = (
                f"https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?"
                f"cod_primaria=1000120&CodCompeticion={COD_COMPETICION_DH}"
                f"&CodGrupo={grp['cod_grupo']}&CodTemporada={COD_TEMPORADA}"
                f"&CodJornada={jornada}&Sch_Codigo_Delegacion=1&Sch_Tipo_Juego=1"
            )
            
            html_jornada = obtener_html(url_jornada)
            if not html_jornada:
                print(f"⚠️ Jornada {jornada}: Sin respuesta del servidor.")
                continue

            codigos_partido = list(set(re.findall(r'CodPartido=(\d+)', html_jornada, re.IGNORECASE)))

            if not codigos_partido:
                jornadas_vacias_seguidas += 1
                if jornadas_vacias_seguidas >= 3:
                    print(f"\nℹ️ Fin de partidos disputados en {grp['nombre']} (Jornada {jornada}).")
                    break
                continue

            jornadas_vacias_seguidas = 0
            print(f"\n--- Jornada {jornada} ({len(codigos_partido)} partidos encontrados) ---")

            for cod in codigos_partido:
                partido, error_debug = parsear_y_auditar_acta(cod, jornada, grp['nombre'])

                if error_debug and error_debug != "ERROR_RED":
                    print(f"\n🚨 [ALERTA DE AUDITORÍA] Datos incompletos detectados en Partido ID: {cod}")
                    print(f"   Campos afectados: {error_debug['campos_fallidos']}")
                    print(f"   URL del acta: {error_debug['url']}")
                    print(f"   Local: {partido['equipo_local']} | Visitante: {partido['equipo_visitante']}")
                    print(f"   Árbitro: {partido['arbitro']} | Delegación: {partido['delegacion']}")
                    print("\n🛑 Proceso pausado automáticamente para evitar guardar datos corruptos/Sin Asignar.")
                    sys.exit(1)

                if partido:
                    if guardar_en_supabase(partido):
                        total_guardados += 1
                        print(f"  ✅ J{jornada} | {partido['equipo_local']} vs {partido['equipo_visitante']} | Árb: {partido['arbitro']} ({partido['delegacion']})")
                    else:
                        print(f"  ❌ Fallo de almacenamiento en Supabase para el partido ID {cod}")

                time.sleep(0.08)

    print("\n" + "=" * 75)
    print(" 🎉 PROCESO DE EXTRACCIÓN COMPLETADO CON ÉXITO")
    print(f" 📊 Partidos guardados/actualizados en Supabase: {total_guardados}")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    ejecucion()