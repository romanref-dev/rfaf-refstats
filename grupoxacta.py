import urllib.request
import http.cookiejar
import re
import json
import time
from bs4 import BeautifulSoup
from config import SUPABASE_URL, SUPABASE_KEY, COD_TEMPORADA, COD_COMPETICION_DH

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9"
}

def inicializar_sesion():
    url_landing = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"
    opener.open(urllib.request.Request(url_landing, headers=headers))

def obtener_actas_jornada(cod_grupo, jornada):
    """Extrae únicamente los números de CodActa que existen en esa jornada"""
    url = (
        f"https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada"
        f"?cod_primaria=1000120&CodCompeticion={COD_COMPETICION_DH}"
        f"&CodGrupo={cod_grupo}&CodTemporada={COD_TEMPORADA}&CodJornada={jornada}"
    )
    req = urllib.request.Request(url, headers={**headers, "Referer": "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"})
    
    try:
        with opener.open(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            # Buscar todos los números de CodActa presentes en los enlaces del HTML
            actas = re.findall(r'CodActa=(\d+)', html, re.IGNORECASE)
            return list(set(actas))
    except Exception as e:
        print(f"⚠️ Error al obtener lista de actas de J{jornada}: {e}")
        return []

def leer_acta_individual(cod_acta, jornada):
    """Procesa la página individual del acta extrayendo los datos del partido"""
    url_acta = f"https://www.rfaf.es/pnfg/NPcd/NFG_CmpPartido?cod_primaria=1000120&CodActa={cod_acta}"
    req = urllib.request.Request(url_acta, headers=headers)
    
    try:
        with opener.open(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extraer delegación (tu código original)
            delegacion = "Sin Asignar"
            match_del = re.search(r'DELEGACI[ÓO]N DE\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)', html, re.IGNORECASE)
            if match_del:
                delegacion = f"Delegación De {match_del.group(1).strip().split()[0].title()}"

            # Extraer Equipos
            eq_local, eq_visitante = "Desconocido", "Desconocido"
            enlaces_eq = soup.find_all('a', href=lambda h: h and 'Codigo_Equipo=' in h)
            if len(enlaces_eq) >= 2:
                eq_local = enlaces_eq[0].text.strip()
                eq_visitante = enlaces_eq[1].text.strip()

            # Extraer Resultado (Goles)
            goles_loc, goles_vis = 0, 0
            match_res = re.search(r'(\d+)\s*-\s*(\d+)', soup.text)
            if match_res:
                goles_loc = int(match_res.group(1))
                goles_vis = int(match_res.group(2))

            # Extraer Árbitro
            match_arb = re.search(r'[ÁA]rbitro:\s*([A-Za-zÁÉÍÓÚáéíóúñÑ\s,]+)', soup.text)
            arbitro = match_arb.group(1).strip().title() if match_arb else "Desconocido"
            arbitro = arbitro.split('\n')[0].strip()

            # Extraer Fecha
            match_fecha = re.search(r'(\d{2}-\d{2}-\d{4})', soup.text)
            fecha = match_fecha.group(1) if match_fecha else "2026-01-01"

            return {
                "acta_id": f"RFAF-{cod_acta}",
                "fecha": fecha,
                "categoria": "División de Honor Senior (Grupo 1)",
                "jornada": jornada,
                "equipo_local": eq_local,
                "equipo_visitante": eq_visitante,
                "goles_local": goles_loc,
                "goles_visitante": goles_vis,
                "arbitro": arbitro,
                "delegacion": delegacion
            }
    except Exception as e:
        print(f"   ❌ Error leyendo acta {cod_acta}: {e}")
        return None

def guardar_supabase(partido):
    """Inserta o actualiza el partido en Supabase"""
    endpoint = f"{SUPABASE_URL}/rest/v1/partidos"
    headers_sp = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    data = json.dumps(partido).encode('utf-8')
    req = urllib.request.Request(endpoint, data=data, headers=headers_sp, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception as e:
        print(f"   ❌ Error Supabase: {e}")
        return False

def procesar_grupo_1():
    print("=" * 65)
    print(" 🚀 RECOLECTANDO ACTAS DEL GRUPO 1 Y GUARDANDO EN SUPABASE")
    print("=" * 65)

    inicializar_sesion()
    cod_grupo_g1 = "49641343" # Grupo 1

    # 1. Mapear todas las actas del grupo
    mapa_actas = {}
    print("\nPASO 1: Mapeando IDs de actas por jornada...")
    for j in range(1, 31):
        actas = obtener_actas_jornada(cod_grupo_g1, j)
        mapa_actas[j] = actas
        print(f"   Jornada {j:02d}: {len(actas)} actas localizadas -> {actas[:3]}...")
        time.sleep(0.1)

    total_actas = sum(len(v) for v in mapa_actas.values())
    print(f"\n📊 Total de actas a procesar en el Grupo 1: {total_actas}")

    # 2. Leer cada acta individualmente y guardarla
    print("\nPASO 2: Leyendo actas individuales y guardando en BD...")
    procesadas = 0
    for j, lista_actas in mapa_actas.items():
        for cod_acta in lista_actas:
            datos = leer_acta_individual(cod_acta, j)
            if datos:
                if guardar_supabase(datos):
                    procesadas += 1
                    print(f"   ✅ [J{j:02d}] Acta {cod_acta} guardada: {datos['equipo_local']} vs {datos['equipo_visitante']}")
                else:
                    print(f"   ⚠️ [J{j:02d}] Acta {cod_acta} leída pero falló al guardar en BD")
            time.sleep(0.1)

    print("\n" + "=" * 65)
    print(f" 🎉 PROCESO CONCLUIDO: {procesadas}/{total_actas} actas guardadas en Supabase.")
    print("=" * 65)

if __name__ == "__main__":
    procesar_grupo_1()