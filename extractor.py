import json
import os
import random
import re
import time
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from curl_cffi import requests
from playwright.sync_api import sync_playwright
from supabase import Client, create_client

# Configuración Supabase
DEFAULT_URL = "https://ijczoeyfgnngocstxgfb.supabase.co"
DEFAULT_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlqY3pvZXlmZ25uZ29jc3R4Z2ZiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzExMzQyMiwiZXhwIjoyMTA4Njg5NDIyfQ.yPTDZIgGoRlpYUVHQSXTJ0INABGGZRxAP0leLfBDpYM"
)

SUPABASE_URL = os.getenv("SUPABASE_URL") or DEFAULT_URL
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or DEFAULT_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
URL_BASE = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101"
        " Firefox/119.0"
    ),
]


def parsear_acta_detallada(url_acta, partido_id):
    datos_acta = {
        "arbitros": [],
        "delegacion_principal": "Sin Delegación",
        "am_local": 0,
        "am_visitante": 0,
        "roj_local": 0,
        "roj_visitante": 0,
        "incidencias_tarjetas": [],
        "goles": [],
    }

    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        response = requests.get(
            url_acta, headers=headers, impersonate="chrome110", timeout=15
        )

        if response.status_code != 200:
            print(
                f"         ⚠️ Error HTTP {response.status_code} al acceder a"
                f" {url_acta}"
            )
            return datos_acta

        html_raw = response.text.replace("&nbsp;", " ")
        soup = BeautifulSoup(html_raw, "html.parser")

        # ==========================================
        # FRONTERAS POSICIONALES EN HTML
        # ==========================================
        matches_ct = [
            m.start()
            for m in re.finditer(r"Cuerpo\s+T[ée]cnico", html_raw, re.I)
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
            registro = {
                "cargo": cargo,
                "nombre": nombre,
                "delegacion": delegacion,
            }
            if registro not in datos_acta["arbitros"]:
                datos_acta["arbitros"].append(registro)
                if cargo == "ARBITRO":
                    datos_acta["delegacion_principal"] = delegacion

        # ==========================================
        # 2. CUERPO TÉCNICO
        # ==========================================
        cuerpo_tecnico = {"local": [], "visitante": []}
        patron_ct = re.compile(
            r"(DEL\.\s*(?:Campo|Equipo)|Entrenador|2º\s*Entrenador|FISIOTERAPEUTA|ENCARGADO DE MATERIAL|PREPARADOR FISICO|DELEGADO|MEDICO)\s*:\s*([A-ZÁÉÍÓÚÑ\s,]+)",
            re.I,
        )

        for match in patron_ct.finditer(texto_plano):
            rol_limpio = match.group(1).strip().upper()
            nombre_cand = match.group(2).strip()
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
                if registro not in cuerpo_tecnico[equipo]:
                    cuerpo_tecnico[equipo].append(registro)

        # ==========================================
        # 3. GOLES
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

                resultado = "?"
                for celda in fila.find_all(["td", "div", "span", "b"]):
                    txt_c = celda.get_text(strip=True)
                    m_marcador = re.search(r"(\d+)\s*-\s*(\d+)", txt_c)
                    if m_marcador:
                        g1, g2 = m_marcador.group(1), m_marcador.group(2)
                        if int(g1) < 30 and int(g2) < 30:
                            resultado = f"{g1} - {g2}"
                            break

                datos_acta["goles"].append(
                    {
                        "minuto": minuto,
                        "jugador": jugador,
                        "resultado": resultado,
                    }
                )

        # ==========================================
        # 4. TARJETAS (POSICIONAL)
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
                equipo_str = (
                    "visitante" if pos_nombre >= pos_corte_tarjetas else "local"
                )

                es_ct = any(
                    nombre_limpio in ct["nombre"]
                    or ct["nombre"] in nombre_limpio
                    for ct in cuerpo_tecnico[equipo_str]
                )

                tipo_tarjeta = "ROJA" if es_roja else "AMARILLA"

                if equipo_str == "local":
                    if es_roja:
                        datos_acta["roj_local"] += 1
                    else:
                        datos_acta["am_local"] += 1
                else:
                    if es_roja:
                        datos_acta["roj_visitante"] += 1
                    else:
                        datos_acta["am_visitante"] += 1

                datos_acta["incidencias_tarjetas"].append(
                    {
                        "partido_id": partido_id,
                        "equipo": equipo_str,
                        "jugador": nombre_limpio,
                        "minuto": minuto,
                        "tipo_persona": "CUERPO_TECNICO"
                        if es_ct
                        else "JUGADOR",
                        "tipo_tarjeta": tipo_tarjeta,
                    }
                )

    except Exception as e:
        print(f"         ⚠️ Error procesando el acta ({url_acta}): {e}")

    return datos_acta


def extractor_profundo_rfaf():
    if not os.path.exists("mapa_rfaf.json"):
        print("❌ Error: No se encuentra 'mapa_rfaf.json'")
        return

    with open("mapa_rfaf.json", "r", encoding="utf-8") as f:
        mapa_rfaf = json.load(f)

    print("🚀 Iniciando extracción profunda RFAF (Playwright + curl_cffi)...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        for nombre_comp, datos_comp in mapa_rfaf.items():
            id_comp = datos_comp["id_competicion"]
            for nombre_grupo, id_grupo in datos_comp["grupos"].items():
                print(
                    f"\n======================================================\n⚽"
                    f" Competición: {nombre_comp} | Grupo: {nombre_grupo}\n======================================================"
                )

                try:
                    page.goto(URL_BASE, wait_until="networkidle", timeout=35000)
                    page.locator("select#competicion").select_option(
                        value=id_comp, force=True
                    )
                    time.sleep(1.5)
                    page.locator("select#grupo").select_option(
                        value=id_grupo, force=True
                    )
                    time.sleep(1.5)

                    opciones_jornada = []
                    for opt in page.locator("select#jornada option").all():
                        val = opt.get_attribute("value")
                        txt = opt.inner_text().strip()
                        if val and val != "0" and "Seleccione" not in txt:
                            num_j = re.search(r"\d+", txt)
                            opciones_jornada.append(
                                (
                                    txt,
                                    val,
                                    int(num_j.group()) if num_j else 1,
                                )
                            )

                except Exception as e:
                    print(
                        f"   ⚠️ Error de navegación inicial en grupo"
                        f" {nombre_grupo}: {e}"
                    )
                    continue

                for txt_jornada, id_jornada, num_jornada in opciones_jornada:
                    print(f"\n📅 --- {txt_jornada} ---")

                    time.sleep(random.uniform(1.8, 3.2))

                    try:
                        page.locator("select#jornada").select_option(
                            value=id_jornada, force=True
                        )
                        time.sleep(1.5)
                        soup = BeautifulSoup(page.content(), "html.parser")

                        partidos_batch = []
                        tarjetas_batch = []
                        arbitros_map = {}

                        filas = soup.find_all("tr")
                        for fila in filas:
                            celdas = fila.find_all("td")
                            if len(celdas) >= 3:
                                loc = celdas[0].get_text(strip=True)
                                res_celda = celdas[1].get_text(strip=True)
                                vis = celdas[2].get_text(strip=True)

                                # Extraer SOLO el número del marcador limpio (ej. 5 - 4)
                                match_goles = re.search(
                                    r"(\d+)\s*-\s*(\d+)", res_celda
                                )

                                if loc and vis and (match_goles or "Descansa" in res_celda):
                                    g_loc = (
                                        int(match_goles.group(1))
                                        if match_goles
                                        else None
                                    )
                                    g_vis = (
                                        int(match_goles.group(2))
                                        if match_goles
                                        else None
                                    )
                                    res_limpio = f"{g_loc} - {g_vis}" if match_goles else "Descansa"
                                    estado = (
                                        "Finalizado"
                                        if match_goles
                                        else (
                                            "Descansa"
                                            if "Descansa" in res_celda
                                            else "Pendiente"
                                        )
                                    )

                                    p_id = (
                                        f"{id_grupo}_{num_jornada}_{loc}_{vis}"
                                        .replace(" ", "_")
                                        .replace(".", "")
                                    )

                                    # ====================================================
                                    # EXTRACCIÓN EXACTA DE LA URL DEL ACTA (CodActa)
                                    # ====================================================
                                    url_acta = None
                                    link_acta = fila.find(
                                        "a", href=re.compile(r"CodActa=(\d+)", re.I)
                                    )
                                    
                                    if link_acta and "href" in link_acta.attrs:
                                        match_cod = re.search(r"CodActa=(\d+)", link_acta["href"], re.I)
                                        if match_cod:
                                            cod_acta = match_cod.group(1)
                                            # Construir URL canónica exacta comprobada
                                            url_acta = f"https://www.rfaf.es/pnfg/NPcd/NFG_CmpPartido?cod_primaria=1000120&CodActa={cod_acta}&cod_acta={cod_acta}"

                                    datos_acta = {
                                        "arbitros": [],
                                        "delegacion_principal": (
                                            "Sin Delegación"
                                        ),
                                        "am_local": 0,
                                        "am_visitante": 0,
                                        "roj_local": 0,
                                        "roj_visitante": 0,
                                        "incidencias_tarjetas": [],
                                        "goles": [],
                                    }

                                    if url_acta and estado == "Finalizado":
                                        print(
                                            f"   🔎 Analizando Acta:"
                                            f" {loc} vs {vis} ({res_limpio}) -> {url_acta}"
                                        )
                                        datos_acta = parsear_acta_detallada(
                                            url_acta, p_id
                                        )

                                        arb_str = ", ".join(
                                            f"{a['nombre']} ({a['delegacion']})"
                                            for a in datos_acta["arbitros"]
                                        )
                                        print(
                                            f"      🏁 Árbitros:"
                                            f" {arb_str if arb_str else 'No asignado'}"
                                        )
                                        print(
                                            f"      🟨 Tarjetas Amarillas:"
                                            f" Local {datos_acta['am_local']} |"
                                            " Visitante"
                                            f" {datos_acta['am_visitante']}"
                                        )
                                        print(
                                            f"      🟥 Tarjetas Rojas: Local"
                                            f" {datos_acta['roj_local']} |"
                                            " Visitante"
                                            f" {datos_acta['roj_visitante']}"
                                        )

                                        time.sleep(random.uniform(2.0, 4.0))

                                    arb_nombre = "No asignado"
                                    if datos_acta["arbitros"]:
                                        arb_nombre = datos_acta["arbitros"][0][
                                            "nombre"
                                        ]

                                    arb_id = (
                                        arb_nombre.lower()
                                        .replace(" ", "_")
                                        .replace(",", "")
                                    )
                                    if arb_nombre != "No asignado":
                                        arbitros_map[arb_id] = {
                                            "id": arb_id,
                                            "nombre": arb_nombre,
                                            "delegacion": datos_acta[
                                                "delegacion_principal"
                                            ],
                                            "updated_at": (
                                                datetime.now(timezone.utc).isoformat()
                                            ),
                                        }

                                    tot_am = (
                                        datos_acta["am_local"]
                                        + datos_acta["am_visitante"]
                                    )
                                    tot_roj = (
                                        datos_acta["roj_local"]
                                        + datos_acta["roj_visitante"]
                                    )

                                    partido_obj = {
                                        "id": p_id,
                                        "competicion": nombre_comp,
                                        "categoria": (
                                            f"{nombre_comp} ({nombre_grupo})"
                                        ),
                                        "grupo": nombre_grupo,
                                        "id_grupo": str(id_grupo),
                                        "jornada": num_jornada,
                                        "id_jornada": str(id_jornada),
                                        "equipo_local": loc,
                                        "equipo_visitante": vis,
                                        "resultado": res_limpio,
                                        "goles_local": g_loc,
                                        "goles_visitante": g_vis,
                                        "estado": estado,
                                        "arbitro_id": arb_id,
                                        "arbitro_nombre": arb_nombre,
                                        "delegacion_arbitro": datos_acta[
                                            "delegacion_principal"
                                        ],
                                        "tarjetas_amarillas_local": datos_acta[
                                            "am_local"
                                        ],
                                        "tarjetas_amarillas_visitante": (
                                            datos_acta["am_visitante"]
                                        ),
                                        "tarjetas_rojas_local": datos_acta[
                                            "roj_local"
                                        ],
                                        "tarjetas_rojas_visitante": datos_acta[
                                            "roj_visitante"
                                        ],
                                        "tarjetas_amarillas": tot_am,
                                        "tarjetas_rojas": tot_roj,
                                        "updated_at": datetime.now(timezone.utc).isoformat(),
                                    }
                                    partidos_batch.append(partido_obj)

                                    if datos_acta["incidencias_tarjetas"]:
                                        tarjetas_batch.extend(
                                            datos_acta["incidencias_tarjetas"]
                                        )

                        if partidos_batch:
                            if arbitros_map:
                                supabase.table("arbitros").upsert(
                                    list(arbitros_map.values())
                                ).execute()
                            supabase.table("partidos").upsert(
                                partidos_batch
                            ).execute()
                            if tarjetas_batch:
                                supabase.table("actas_tarjetas").upsert(
                                    tarjetas_batch
                                ).execute()

                            print(
                                f"\n   ✅ Jornada {num_jornada} guardada en"
                                f" Supabase: {len(partidos_batch)} partidos |"
                                f" {len(tarjetas_batch)} incidencias"
                                " registradas."
                            )

                    except Exception as err:
                        print(
                            f"   ❌ Error procesando jornada {txt_jornada}:"
                            f" {err}"
                        )

        browser.close()

    print("\n🎉 Extracción completa finalizada. Datos 100% listos en Supabase.")


if __name__ == "__main__":
    extractor_profundo_rfaf()