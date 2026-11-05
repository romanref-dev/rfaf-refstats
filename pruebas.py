import urllib.request
import urllib.parse
import http.cookiejar

URL_BASE = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
opener.addheaders = [
    ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
    ("Accept-Language", "es-ES,es;q=0.9")
]

# 1. Handshake inicial para capturar cookies de Novanet
req_init = urllib.request.Request("https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120&cod_agrupacion=1")
with opener.open(req_init) as resp:
    resp.read()

# 2. Petición a la Jornada 1 del Grupo 1
url_jornada = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120&CodCompeticion=48466530&CodGrupo=49641343&CodTemporada=22&CodJornada=1"
req_jornada = urllib.request.Request(url_jornada)

with opener.open(req_jornada) as resp:
    html = resp.read().decode('utf-8', errors='ignore')
    print("=== TAMAÑO DEL HTML RECIBIDO ===")
    print(f"Bytes: {len(html)}")
    print("\n=== BÚSQUEDA DE 'CodPartido' EN EL HTML ===")
    import re
    partidos = re.findall(r'CodPartido=(\d+)', html, re.IGNORECASE)
    print(f"Coincidencias encontradas: {partidos}")
    
    if not partidos:
        print("\n=== FRAGMENTO DEL HTML DEVUELTO (primeros 1000 caracteres) ===")
        print(html[:1000])