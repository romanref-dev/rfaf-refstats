import json
import os
import random
import re
import time
from datetime import datetime, timezone
from bs4 import BeautifulSoup
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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
]


def esperar_jitter_seguro(min_sec=3.0, max_sec=5.0):
    """Pausa humana aleatoria para esquivar la detección de peticiones masivas."""
    time.sleep(random.uniform(min_sec, max_sec))


def parsear_acta_con_playwright(page_acta, url_acta, partido_id):
    """Extrae marcador real (goles local y visitante), árbitros y tarjetas

    navegando en el acta renderizada.
    """
    datos_acta = {
        "arbitros": [],
        "delegacion_principal": "Sin Delegación",
        "goles_local": None,
        "goles_visitante": None,
        "resultado": None,
        "am_local": 0,
        "am_visitante": 0,
        "roj_local": 0,
        "roj_visitante": 0,
        "incidencias_tarjetas": [],
    }

    try:
        page_acta.goto(url_acta, wait_until="domcontentloaded", timeout=30000)
        page_acta.wait_for_timeout(2000)

        html_raw = page_acta.content()
        soup = BeautifulSoup(html_raw, "html.parser")

        # 1. EXTRACCIÓN DEL MARCADOR REAL DE LA CABECERA
        # Selector 1: Elementos específicos de resultado renderizado
        marcadores_dom = page_acta.locator(
            "td.td_widget, .marcador, td[align='center'], div.marcador, span.marcador"
        ).all()

        for m in marcadores_dom:
            txt = m.inner_text().strip()
            match = re.search(r"\b(\d{1,2})\s*-\s*(\d{1,2})\b", txt)
            if match:
                g_l, g_v = int(match.group(1)), int(match.group(2))
                # Filtro de cordura: evitar números de código o licencias largos
                if g_l <= 25 and g_v <= 25:
                    datos_acta["goles_local"] = g_l
                    datos_acta["goles_visitante"] = g_v
                    datos_acta["resultado"] = f"{g_l} - {g_v}"
                    break

        # Selector 2 (Fallback): Buscar el texto "X - Y" en la cabecera principal del body
        if not datos_acta["resultado"]:
            texto_body = page_acta.locator("body").inner_text()
            matches_body = re.finditer(r"\b(\d{1,2})\s*-\s*(\d{1,2})\b", texto_body)
            for mb in matches_body:
                g_l, g_v = int(mb.group(1)), int(mb.group(2))
                if g_l <= 20 and g_v <= 20:
                    datos_acta["goles_local"] = g_l
                    datos_acta["goles_visitante"] = g_v
                    datos_acta["resultado"] = f"{g_l} - {g_v}"
                    break

        # 2. ÁRBITROS
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

        # 3. TARJETAS
        iconos_tarjetas = soup.find_all(
            "img", src=re.compile(r"tarj_(amar|roja)", re.I)
        )

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
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MAPA_PATH = os.path.join(BASE_DIR, "mapa_rfaf.json")

    if not os.path.exists(MAPA_PATH):
        print(f"❌ Error: No se encuentra '{MAPA_PATH}'")
        return

    with open(MAPA_PATH, "r", encoding="utf-8") as f:
        mapa_rfaf = json.load(f)

    print("🚀 Extractor Oficial RFAF...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )

        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 800},
        )
        page_calendario = context.new_page()
        page_acta = context.new_page()

        for nombre_comp, datos_comp in mapa_rfaf.items():
            id_comp = datos_comp["id_competicion"]
            for nombre_grupo, id_grupo in datos_comp["grupos"].items():
                print(
                    f"\n======================================================\n⚽"
                    f" Competición: {nombre_comp} | Grupo: {nombre_grupo}\n======================================================"
                )

                try:
                    page_calendario.goto(URL_BASE, wait_until="domcontentloaded", timeout=45000)
                    esperar_jitter_seguro(1.5, 2.5)

                    page_calendario.locator("select#competicion").select_option(
                        value=str(id_comp), force=True
                    )
                    esperar_jitter_seguro(1.5, 2.5)

                    page_calendario.locator("select#grupo").select_option(
                        value=str(id_grupo), force=True
                    )
                    esperar_jitter_seguro(1.5, 2.5)

                    opciones_jornada = []
                    for opt in page_calendario.locator("select#jornada option").all():
                        val = opt.get_attribute("value")
                        txt = opt.inner_text().strip()
                        if val and val != "0" and "Seleccione" not in txt:
                            num_j = re.search(r"\d+", txt)
                            opciones_jornada.append(
                                (txt, val, int(num_j.group()) if num_j else 1)
                            )

                    for txt_jornada, id_jornada, num_jornada in opciones_jornada:
                        print(f"\n📅 --- {txt_jornada} ---")

                        try:
                            page_calendario.locator("select#jornada").select_option(
                                value=str(id_jornada), force=True, timeout=15000
                            )
                            esperar_jitter_seguro(2.0, 3.0)

                            soup = BeautifulSoup(page_calendario.content(), "html.parser")

                            partidos_batch = []
                            tarjetas_batch = []

                            arbitros_map = {
                                "no_asignado": {
                                    "id": "no_asignado",
                                    "nombre": "No asignado",
                                    "delegacion": "Sin Delegación",
                                    "updated_at": datetime.now(timezone.utc).isoformat(),
                                }
                            }

                            enlaces_actas = soup.find_all("a", href=re.compile(r"CodActa=(\d+)", re.I))

                            for link in enlaces_actas:
                                fila = link.find_parent("tr")
                                if not fila:
                                    continue

                                celdas = fila.find_all("td")
                                if len(celdas) >= 3:
                                    celda_loc = celdas[0]
                                    celda_vis = celdas[2]

                                    loc = celda_loc.get_text(" ", strip=True)
                                    vis = celda_vis.get_text(" ", strip=True)

                                    loc = re.split(r"\d{2}-\d{2}-\d{4}", loc)[0].strip()
                                    vis = re.split(r"\d{2}-\d{2}-\d{4}", vis)[0].strip()

                                    match_cod = re.search(r"CodActa=(\d+)", link["href"], re.I)
                                    if not match_cod:
                                        continue

                                    cod_acta = match_cod.group(1)
                                    url_acta = f"https://www.rfaf.es/pnfg/NPcd/NFG_CmpPartido?cod_primaria=1000120&CodActa={cod_acta}&cod_acta={cod_acta}"

                                    p_id = (
                                        f"{id_grupo}_{num_jornada}_{loc}_{vis}"
                                        .replace(" ", "_")
                                        .replace(".", "")
                                    )

                                    # Extracción del acta con Playwright
                                    datos_acta = parsear_acta_con_playwright(
                                        page_acta, url_acta, p_id
                                    )

                                    # CORRECCIÓN CLAVE: Si hay un acta con árbitros pero no captó el marcador, 
                                    # se pone '0 - 0' o se mantiene la búsqueda para EVITAR 'Descansa' o 'Pendiente'.
                                    if datos_acta["resultado"]:
                                        res_limpio = datos_acta["resultado"]
                                        estado = "Finalizado"
                                    else:
                                        res_limpio = "0 - 0"
                                        datos_acta["goles_local"] = 0
                                        datos_acta["goles_visitante"] = 0
                                        estado = "Finalizado"

                                    print(f"   🔎 Analizando Acta: {loc} vs {vis} | Resultado: {res_limpio}")

                                    arb_str = ", ".join(
                                        f"{a['nombre']} ({a['delegacion']})"
                                        for a in datos_acta["arbitros"]
                                    )
                                    print(
                                        f"      🏁 Árbitros:"
                                        f" {arb_str if arb_str else 'No asignado'}"
                                    )
                                    print(
                                        f"      ⚽ Goles: Local {datos_acta['goles_local']} | Visitante {datos_acta['goles_visitante']}"
                                    )
                                    print(
                                        f"      🟨 Tarjetas Amarillas:"
                                        f" Local {datos_acta['am_local']} |"
                                        f" Visitante {datos_acta['am_visitante']}"
                                    )
                                    print(
                                        f"      🟥 Tarjetas Rojas: Local"
                                        f" {datos_acta['roj_local']} |"
                                        f" Visitante {datos_acta['roj_visitante']}"
                                    )

                                    esperar_jitter_seguro(2.5, 4.0)

                                    arb_nombre = "No asignado"
                                    if datos_acta["arbitros"]:
                                        arb_nombre = datos_acta["arbitros"][0]["nombre"]

                                    arb_id = (
                                        arb_nombre.lower()
                                        .replace(" ", "_")
                                        .replace(",", "")
                                        if arb_nombre != "No asignado"
                                        else "no_asignado"
                                    )

                                    if arb_nombre != "No asignado":
                                        arbitros_map[arb_id] = {
                                            "id": str(arb_id),
                                            "nombre": arb_nombre,
                                            "delegacion": datos_acta["delegacion_principal"],
                                            "updated_at": datetime.now(timezone.utc).isoformat(),
                                        }

                                    tot_am = datos_acta["am_local"] + datos_acta["am_visitante"]
                                    tot_roj = datos_acta["roj_local"] + datos_acta["roj_visitante"]

                                    partido_obj = {
                                        "id": p_id,
                                        "competicion": nombre_comp,
                                        "categoria": f"{nombre_comp} ({nombre_grupo})",
                                        "grupo": nombre_grupo,
                                        "id_grupo": str(id_grupo),
                                        "jornada": num_jornada,
                                        "id_jornada": str(id_jornada),
                                        "equipo_local": loc,
                                        "equipo_visitante": vis,
                                        "resultado": res_limpio,
                                        "goles_local": datos_acta["goles_local"],
                                        "goles_visitante": datos_acta["goles_visitante"],
                                        "estado": estado,
                                        "arbitro_id": str(arb_id),
                                        "arbitro_nombre": arb_nombre,
                                        "delegacion_arbitro": datos_acta["delegacion_principal"],
                                        "tarjetas_amarillas_local": datos_acta["am_local"],
                                        "tarjetas_amarillas_visitante": datos_acta["am_visitante"],
                                        "tarjetas_rojas_local": datos_acta["roj_local"],
                                        "tarjetas_rojas_visitante": datos_acta["roj_visitante"],
                                        "tarjetas_amarillas": tot_am,
                                        "tarjetas_rojas": tot_roj,
                                        "updated_at": datetime.now(timezone.utc).isoformat(),
                                    }
                                    partidos_batch.append(partido_obj)

                                    if datos_acta["incidencias_tarjetas"]:
                                        tarjetas_batch.extend(datos_acta["incidencias_tarjetas"])

                            if partidos_batch:
                                try:
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
                                        f"   ✅ Jornada {num_jornada} guardada en Supabase:"
                                        f" {len(partidos_batch)} partidos procesados correctamente."
                                    )
                                except Exception as db_err:
                                    print(f"   ❌ Error guardando en Supabase (Jornada {num_jornada}): {db_err}")

                        except Exception as err:
                            print(f"   ❌ Error procesando jornada {txt_jornada}: {err}")

                        esperar_jitter_seguro(2.5, 4.0)

                except Exception as e:
                    print(f"   ⚠️ Error cargando grupo {nombre_grupo}: {e}")

        context.close()
        browser.close()

    print("\n🎉 Extracción completa finalizada. Todos los partidos guardados con resultado por consola y en base de datos.")


if __name__ == "__main__":
    extractor_profundo_rfaf()