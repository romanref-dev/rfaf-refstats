import urllib.request
import http.cookiejar
import json
import re
import time

from config import SUPABASE_URL, SUPABASE_KEY, COD_TEMPORADA, COD_COMPETICION_DH, GRUPOS_DH

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

headers_base = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9"
}

def obtener_sesion():
    print("📡 Estableciendo cookie de sesión inicial en RFAF...")
    url_landing = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"
    req = urllib.request.Request(url_landing, headers=headers_base)
    for intento in range(1, 4):
        try:
            with opener.open(req, timeout=15) as resp:
                resp.read()
            print("✅ Sesión establecida correctamente.\n")
            return True
        except Exception as e:
            print(f"⚠️ Intento {intento}/3 fallido al iniciar sesión: {e}")
            time.sleep(2)
    return False

def consultar_jornada_html(cod_grupo, cod_jornada):
    url_jornada = (
        f"https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada"
        f"?cod_primaria=1000120"
        f"&CodCompeticion={COD_COMPETICION_DH}"
        f"&CodGrupo={cod_grupo}"
        f"&CodTemporada={COD_TEMPORADA}"
        f"&CodJornada={cod_jornada}"
    )
    headers = headers_base.copy()
    headers["Referer"] = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"
    
    req = urllib.request.Request(url_jornada, headers=headers)
    for intento in range(1, 4):
        try:
            with opener.open(req, timeout=20) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if intento == 3:
                print(f"   ❌ Error al descargar Jornada {cod_jornada}: {e}")
            else:
                time.sleep(1.5)
    return None

def obtener_delegacion(url_acta):
    if not url_acta:
        return "Sin Asignar"
    
    url_completa = f"https://www.rfaf.es{url_acta}" if url_acta.startswith("/") else f"https://www.rfaf.es/pnfg/NPcd/{url_acta}"
    req = urllib.request.Request(url_completa, headers=headers_base)
    try:
        with opener.open(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            match_del = re.search(r'DELEGACI[ÓO]N DE\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)', html, re.IGNORECASE)
            if match_del:
                del_nombre = match_del.group(1).strip().split()[0].title()
                return f"Delegación De {del_nombre}"
    except Exception:
        pass
    return "Sin Asignar"

def guardar_supabase(partido):
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception as e:
        print(f"      ❌ Error Supabase al guardar acta {partido['acta_id']}: {e}")
        return False

def procesar_todo():
    if not obtener_sesion():
        return

    if isinstance(GRUPOS_DH, dict):
        grupos = GRUPOS_DH.items()
    elif isinstance(GRUPOS_DH, list):
        grupos = []
        for g in GRUPOS_DH:
            if isinstance(g, dict):
                grupos.append((g.get('nombre', 'Grupo'), g.get('codigo') or g.get('id')))
            elif isinstance(g, (list, tuple)):
                grupos.append((g[0], g[1]))
            else:
                grupos.append((f"Grupo {g}", g))
    else:
        grupos = [("División de Honor Senior (Grupo 1)", "49641343"), ("División de Honor Senior (Grupo 2)", "49641344")]

    total_guardados = 0

    for nombre_grupo, cod_grupo in grupos:
        print("=" * 70)
        print(f" ⚽ INICIANDO RECORRIDO DE {str(nombre_grupo).upper()}")
        print("=" * 70)

        for jornada in range(1, 31):
            html = consultar_jornada_html(cod_grupo, jornada)
            if not html:
                continue

            # Extraer bloques de partidos dividiendo por las tablas HTML
            bloques_tabla = re.findall(r'<table[^>]*>.*?</table>', html, re.DOTALL | re.IGNORECASE)
            
            partidos_jornada = 0
            actas_procesadas = set()

            for bloque in bloques_tabla:
                # 1. Extraer ID del Acta
                match_acta = re.search(r'href=[\'"]([^\'"]*CodActa=(\d+)[^\'"]*)[\'"]', bloque, re.IGNORECASE)
                if not match_acta:
                    continue

                url_acta = match_acta.group(1)
                cod_acta = match_acta.group(2)

                if cod_acta in actas_procesadas:
                    continue
                actas_procesadas.add(cod_acta)

                # 2. Extraer Nombres de Equipos desde los enlaces VisEquipos
                equipos = re.findall(r'href=[\'"][^\'"]*Codigo_Equipo=[^\'"]*[\'"][^>]*>\s*([^<]+)\s*</a', bloque, re.IGNORECASE)
                if len(equipos) < 2:
                    continue

                local_nombre = equipos[0].strip()
                visitante_nombre = equipos[1].strip()

                # Limpiar texto para extraer datos sencillos
                texto_limpio = re.sub(r'<[^>]+>', ' ', bloque)

                # 3. Extraer Marcador
                goles_loc, goles_vis = 0, 0
                match_res = re.search(r'(\d+)\s*-\s*(\d+)', texto_limpio)
                if match_res:
                    goles_loc, goles_vis = int(match_res.group(1)), int(match_res.group(2))

                # 4. Extraer Fecha
                match_fecha = re.search(r'(\d{2}-\d{2}-\d{4})', texto_limpio)
                fecha_partido = match_fecha.group(1) if match_fecha else "2026-09-13"

                # 5. Extraer Árbitro
                match_arb = re.search(r'[ÁA]rbitro:\s*([A-Za-zÁÉÍÓÚáéíóúñÑ\s,]+)', texto_limpio)
                arbitro_nombre = match_arb.group(1).strip().title() if match_arb else "Desconocido"
                arbitro_nombre = re.split(r'[\r\n\t]', arbitro_nombre)[0].strip()

                # 6. Consultar Delegación
                delegacion = obtener_delegacion(url_acta)

                datos_partido = {
                    "acta_id": f"RFAF-{cod_acta}",
                    "fecha": fecha_partido,
                    "categoria": str(nombre_grupo),
                    "jornada": jornada,
                    "equipo_local": local_nombre,
                    "equipo_visitante": visitante_nombre,
                    "goles_local": goles_loc,
                    "goles_visitante": goles_vis,
                    "arbitro": arbitro_nombre,
                    "delegacion": delegacion,
                    "tarjetas_amarillas": 0,
                    "tarjetas_rojas": 0
                }

                if guardar_supabase(datos_partido):
                    total_guardados += 1
                    partidos_jornada += 1
                    print(f"   ✅ [J{jornada} | Acta {cod_acta}] {local_nombre} {goles_loc}-{goles_vis} {visitante_nombre} | Árb: {arbitro_nombre} ({delegacion})")

            print(f"📊 Jornada {jornada}: {partidos_jornada} partidos extraídos y guardados.")
            time.sleep(0.1)

    print("\n" + "=" * 70)
    print(f" 🎉 RECORRIDO COMPLETO: {total_guardados} partidos guardados en Supabase.")
    print("=" * 70)

if __name__ == "__main__":
    procesar_todo()