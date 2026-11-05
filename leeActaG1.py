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

def leer_acta_individual(cod_acta):
    """Procesa la página individual del acta (el script que ya sabemos que funciona)"""
    url_acta = f"https://www.rfaf.es/pnfg/NPcd/NFG_CmpPartido?cod_primaria=1000120&CodActa={cod_acta}"
    req = urllib.request.Request(url_acta, headers=headers)
    
    try:
        with opener.open(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extraer delegación
            delegacion = "Sin Asignar"
            match_del = re.search(r'DELEGACI[ÓO]N DE\s+([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+)', html, re.IGNORECASE)
            if match_del:
                delegacion = f"Delegación De {match_del.group(1).strip().split()[0].title()}"

            return {
                "acta_id": f"RFAF-{cod_acta}",
                "delegacion": delegacion,
                "html_length": len(html)
            }
    except Exception as e:
        print(f"   ❌ Error leyendo acta {cod_acta}: {e}")
        return None

def procesar_grupo_1():
    print("=" * 65)
    print(" 🚀 RECOLECTANDO ACTAS DEL GRUPO 1 POR ACCESO DIRECTO")
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

    # 2. Leer cada acta individualmente
    print("\nPASO 2: Leyendo actas individuales...")
    procesadas = 0
    for j, lista_actas in mapa_actas.items():
        for cod_acta in lista_actas:
            datos = leer_acta_individual(cod_acta)
            if datos:
                procesadas += 1
                print(f"   ✅ [J{j:02d}] Acta {cod_acta} leída correctamente ({datos['delegacion']})")
            time.sleep(0.1)

    print("\n" + "=" * 65)
    print(f" 🎉 PROCESO CONCLUIDO: {procesadas}/{total_actas} actas leídas con éxito.")
    print("=" * 65)

if __name__ == "__main__":
    procesar_grupo_1()