import random
import re
import time
from bs4 import BeautifulSoup
from curl_cffi import requests

URLS_ACTAS = [
    (
        "https://www.rfaf.es/pnfg/NPcd/NFG_CmpPartido?cod_primaria=1000120&CodActa=2733986&cod_acta=2733986"
    ),
]


def extraer_datos_html(url):
    print(f"🔍 Descargando HTML directo de RFAF (anti-bot bypass): {url}")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, impersonate="chrome110")
    response.raise_for_status()

    html_raw = response.text.replace("&nbsp;", " ")
    soup = BeautifulSoup(html_raw, "html.parser")

    datos = {
        "arbitros": [],
        "cuerpo_tecnico": {"local": [], "visitante": []},
        "goles": [],
        "tarjetas": {
            "local": {
                "amarillas_jugadores": [],
                "rojas_jugadores": [],
                "amarillas_ct": [],
                "rojas_ct": [],
            },
            "visitante": {
                "amarillas_jugadores": [],
                "rojas_jugadores": [],
                "amarillas_ct": [],
                "rojas_ct": [],
            },
        },
    }

    # ==========================================
    # FRONTERAS POSICIONALES EN HTML
    # ==========================================
    matches_ct = [
        m.start() for m in re.finditer(r"Cuerpo\s+T[ée]cnico", html_raw, re.I)
    ]
    pos_corte_ct = matches_ct[1] if len(matches_ct) >= 2 else len(html_raw)

    matches_tarjetas = [
        m.start() for m in re.finditer(r"Tarjetas", html_raw, re.I)
    ]
    pos_corte_tarjetas = (
        matches_tarjetas[1] if len(matches_tarjetas) >= 2 else len(html_raw)
    )

    # ==========================================
    # 1. ÁRBITROS Y DELEGACIONES
    # ==========================================
    texto_plano = soup.get_text(" | ", strip=True)
    patron_arb = re.compile(
        r"(ARBITRO|ASISTENTE\s*\d*|CUARTO ÁRBITRO)\s*\|\s*([A-ZÁÉÍÓÚÑ\s,]+?)\s*\|\s*(DELEGACI[ÓO]N\s+DE\s+[A-ZÁÉÍÓÚÑ\s]+)",
        re.I,
    )
    for match in patron_arb.finditer(texto_plano):
        cargo = match.group(1).strip().upper()
        nombre = match.group(2).strip()
        delegacion = match.group(3).strip().title()
        registro = {"cargo": cargo, "nombre": nombre, "delegacion": delegacion}
        if registro not in datos["arbitros"]:
            datos["arbitros"].append(registro)

    # ==========================================
    # 2. CUERPO TÉCNICO
    # ==========================================
    # Expresión regular flexible para roles
    patron_ct = re.compile(
        r"(DEL\.\s*(?:Campo|Equipo)|Entrenador|2º\s*Entrenador|FISIOTERAPEUTA|ENCARGADO DE MATERIAL|PREPARADOR FISICO|DELEGADO|MEDICO)\s*:\s*([A-ZÁÉÍÓÚÑ\s,]+)",
        re.I,
    )

    for match in patron_ct.finditer(texto_plano):
        rol_limpio = match.group(1).strip().upper()
        nombre_cand = match.group(2).strip()

        # Cortar en caso de topar con licencias o marcadores
        nombre = re.split(
            r"(Licencia|DEL\.|Entrenador|FISIOTERAPEUTA|ENCARGADO|Titulares|Suplentes)",
            nombre_cand,
            flags=re.I,
        )[0].strip()
        nombre = re.sub(r"\s{2,}.*", "", nombre).strip()

        if nombre and 3 < len(nombre) < 60:
            pos_nodo = html_raw.find(nombre)
            equipo = "visitante" if pos_nodo >= pos_corte_ct else "local"
            registro = {"rol": rol_limpio, "nombre": nombre}
            if registro not in datos["cuerpo_tecnico"][equipo]:
                datos["cuerpo_tecnico"][equipo].append(registro)

    # ==========================================
    # 3. GOLES (MARCADORES CORREGIDOS)
    # ==========================================
    etiquetas_goles = soup.find_all(
        lambda tag: tag.name in ["img", "a"]
        and tag.has_attr("title")
        and "gol" in tag.get("title", "").lower()
    )

    for tag in etiquetas_goles:
        fila = tag.find_parent("tr") or tag.parent
        texto = fila.get_text(" ", strip=True)

        match_jugador = re.search(
            r"\(\s*(\d+)\s*\'?\s*\)\s*([A-ZÁÉÍÓÚÑ\s,\.\-]+)", texto, re.I
        )

        if match_jugador:
            minuto = int(match_jugador.group(1))
            jugador = match_jugador.group(2).strip()
            jugador = re.split(r"\s{2,}", jugador)[0]

            # Buscar patrón de resultado dentro de las celdas de la fila
            resultado = "?"
            for celda in fila.find_all(["td", "div", "span", "b"]):
                txt_c = celda.get_text(strip=True)
                m_marcador = re.search(r"(\d+)\s*-\s*(\d+)", txt_c)
                if m_marcador:
                    # Garantizamos que no coincide con el minuto del gol
                    g1, g2 = m_marcador.group(1), m_marcador.group(2)
                    if int(g1) < 30 and int(g2) < 30:  # Marcador de fútbol real
                        resultado = f"{g1} - {g2}"
                        break

            registro = {
                "minuto": minuto,
                "jugador": jugador,
                "resultado": resultado,
            }
            if registro not in datos["goles"]:
                datos["goles"].append(registro)

    # ==========================================
    # 4. TARJETAS
    # ==========================================
    iconos_tarjetas = soup.find_all(
        "img", src=re.compile(r"tarj_(amar|roja)", re.I)
    )

    for img in iconos_tarjetas:
        es_roja = "roja" in img.get("src", "").lower()
        contenedor = img.find_parent("tr") or img.parent
        if not contenedor:
            continue

        texto = contenedor.get_text(" ", strip=True)
        match = re.search(
            r"\(\s*(\d+)\s*\'?\s*\)\s*([A-ZÁÉÍÓÚÑ\s,\.\-]+)", texto, re.I
        )

        if match:
            minuto = int(match.group(1))
            nombre = match.group(2).strip()
            nombre = re.split(r"\s{2,}", nombre)[0]
            nombre_limpio = re.sub(
                r"\([A-Z\.]+\)", "", nombre, flags=re.I
            ).strip()

            pos_nombre = html_raw.rfind(nombre_limpio)
            equipo = (
                "visitante" if pos_nombre >= pos_corte_tarjetas else "local"
            )

            es_ct = any(
                nombre_limpio in ct["nombre"] or ct["nombre"] in nombre_limpio
                for ct in datos["cuerpo_tecnico"][equipo]
            )

            item = {"minuto": minuto, "nombre": nombre_limpio}
            tipo_tarjeta = "rojas" if es_roja else "amarillas"
            tipo_persona = "ct" if es_ct else "jugadores"
            clave = f"{tipo_tarjeta}_{tipo_persona}"

            if item not in datos["tarjetas"][equipo][clave]:
                datos["tarjetas"][equipo][clave].append(item)

    return datos


if __name__ == "__main__":
    try:
        total_actas = len(URLS_ACTAS)

        for idx, url in enumerate(URLS_ACTAS, start=1):
            datos = extraer_datos_html(url)

            print("\n🏁 --- ÁRBITROS Y DELEGACIONES ---")
            for arb in datos["arbitros"]:
                print(f"[{arb['cargo']}] {arb['nombre']} - ({arb['delegacion']})")

            print("\n👔 --- CUERPO TÉCNICO LOCAL ---")
            for ct in datos["cuerpo_tecnico"]["local"]:
                print(f"[{ct['rol']}] {ct['nombre']}")

            print("\n👔 --- CUERPO TÉCNICO VISITANTE ---")
            for ct in datos["cuerpo_tecnico"]["visitante"]:
                print(f"[{ct['rol']}] {ct['nombre']}")

            print("\n⚽ --- GOLES ---")
            for gol in datos["goles"]:
                print(
                    f"Min {gol['minuto']}' | {gol['jugador']} |"
                    f" {gol['resultado']}"
                )

            def printear_tarjetas(equipo, tipo_persona, titulo):
                amarillas = datos["tarjetas"][equipo][
                    f"amarillas_{tipo_persona}"
                ]
                rojas = datos["tarjetas"][equipo][f"rojas_{tipo_persona}"]
                print(f"\n🟨 🟥 --- TARJETAS {titulo} ---")
                print(f"Amarillas detectadas: {len(amarillas)}")
                for t in amarillas:
                    print(f"  - Min {t['minuto']}' {t['nombre']}")
                print(f"Rojas detectadas: {len(rojas)}")
                for t in rojas:
                    print(f"  - Min {t['minuto']}' {t['nombre']}")

            printear_tarjetas("local", "jugadores", "LOCAL (JUGADORES)")
            printear_tarjetas("local", "ct", "LOCAL (CUERPO TÉCNICO)")
            printear_tarjetas("visitante", "jugadores", "VISITANTE (JUGADORES)")
            printear_tarjetas("visitante", "ct", "VISITANTE (CUERPO TÉCNICO)")

            print("\n✅ Extracción completa.")

            if idx < total_actas:
                t_espera = random.uniform(2.5, 4.5)
                print(f"\n⏳ Pausa anti-bloqueo: {t_espera:.2f}s...")
                time.sleep(t_espera)

    except Exception as e:
        print(f"Error procesando el acta: {e}")