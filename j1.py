import urllib.request
import http.cookiejar
import re
import time
from config import COD_TEMPORADA, COD_COMPETICION_DH

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
    url = (
        f"https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada"
        f"?cod_primaria=1000120&CodCompeticion={COD_COMPETICION_DH}"
        f"&CodGrupo={cod_grupo}&CodTemporada={COD_TEMPORADA}&CodJornada={jornada}"
    )
    req = urllib.request.Request(url, headers={**headers, "Referer": "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"})
    
    try:
        with opener.open(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            actas = re.findall(r'CodActa=(\d+)', html, re.IGNORECASE)
            return list(set(actas))
    except Exception as e:
        print(f"⚠️ Error al obtener lista de actas de J{jornada}: {e}")
        return []

def probar_grupo_1():
    print("=" * 65)
    print(" 🚀 RECOLECTANDO ACTAS DEL GRUPO 1 POR ACCESO DIRECTO")
    print("=" * 65)

    inicializar_sesion()
    cod_grupo_g1 = "49641343"

    mapa_actas = {}
    print("\nMapeando IDs de actas por jornada...")
    for j in range(1, 31):
        actas = obtener_actas_jornada(cod_grupo_g1, j)
        mapa_actas[j] = actas
        print(f"   Jornada {j:02d}: {len(actas)} actas localizadas -> {actas[:3]}...")
        time.sleep(0.1)

    total_actas = sum(len(v) for v in mapa_actas.values())
    print("\n" + "=" * 65)
    print(f" 📊 Total de actas en Grupo 1: {total_actas}")
    print("=" * 65)

if __name__ == "__main__":
    probar_grupo_1()