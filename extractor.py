import os
import json
import time
import random
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from supabase import create_client, Client

DEFAULT_URL = "https://ijczoeyfgnngocstxgfb.supabase.co"
DEFAULT_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlqY3pvZXlmZ25uZ29jc3R4Z2ZiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzExMzQyMiwiZXhwIjoyMTA4Njg5NDIyfQ.yPTDZIgGoRlpYUVHQSXTJ0INABGGZRxAP0leLfBDpYM"

SUPABASE_URL = os.getenv("SUPABASE_URL") or DEFAULT_URL
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or DEFAULT_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
URL_BASE = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"

def parsear_resultado(res_raw):
    """Extrae goles local/visitante y el estado del partido."""
    res_limpio = res_raw.strip()
    match_goles = re.match(r'^(\d+)\s*-\s*(\d+)', res_limpio)
    
    if match_goles:
        g_loc = int(match_goles.group(1))
        g_vis = int(match_goles.group(2))
        return f"{g_loc} - {g_vis}", g_loc, g_vis, "Finalizado"
    elif "Descansa" in res_limpio:
        return "Descansa", None, None, "Descansa"
    else:
        return "-", None, None, "Pendiente"

def sincronizar_supabase(partidos, reintentos=3):
    """Upsert masivo en Supabase con política de reintentos."""
    for intento in range(1, reintentos + 1):
        try:
            supabase.table("partidos").upsert(partidos).execute()
            return True
        except Exception as e:
            if intento == reintentos:
                print(f"         ⚠️ Error al sincronizar batch: {e}")
                return False
            time.sleep(2)

def extractor_barrido_total():
    if not os.path.exists("mapa_rfaf.json"):
        print("❌ Error: No se encuentra 'mapa_rfaf.json'")
        return

    with open("mapa_rfaf.json", "r", encoding="utf-8") as f:
        mapa_rfaf = json.load(f)

    print("🚀 Iniciando barrido completo para BBDD de Dashboard...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        for nombre_comp, datos_comp in mapa_rfaf.items():
            id_comp = datos_comp["id_competicion"]
            grupos = datos_comp["grupos"]

            for nombre_grupo, id_grupo in grupos.items():
                print(f"\n⚽ Competición: {nombre_comp} | Grupo: {nombre_grupo}")
                
                jornadas = []
                try:
                    page.goto(URL_BASE, wait_until="networkidle", timeout=35000)
                    page.locator('select#competicion').select_option(value=id_comp, force=True)
                    time.sleep(1.5)
                    page.locator('select#grupo').select_option(value=id_grupo, force=True)
                    time.sleep(2.0)

                    opciones = page.locator('select#jornada option').all()
                    for opt in opciones:
                        val = opt.get_attribute("value")
                        txt = opt.inner_text().strip()
                        if val and val != "0" and "Seleccione" not in txt:
                            jornadas.append((txt, val))

                    print(f"   📅 Total de Jornadas en la temporada: {len(jornadas)}")
                except Exception as e:
                    print(f"   ⚠️ Error cargando grupo {nombre_grupo}: {e}")
                    continue

                for txt_jornada, id_jornada in jornadas:
                    time.sleep(random.uniform(1.8, 3.0))

                    for intento in range(1, 4):
                        try:
                            page.locator('select#jornada').select_option(value=id_jornada, force=True)
                            time.sleep(2.0)
                            page.wait_for_load_state("networkidle", timeout=5000)

                            soup = BeautifulSoup(page.content(), 'html.parser')
                            filas = soup.find_all('tr')

                            partidos_jornada = []
                            partido_actual = {}

                            for fila in filas:
                                texto_fila = fila.get_text(separator=" ", strip=True)
                                if not texto_fila or any(k in texto_fila for k in ["Jornada", "Equipos", "Fecha"]):
                                    continue

                                celdas = fila.find_all('td')
                                if len(celdas) >= 3:
                                    local = celdas[0].get_text(strip=True)
                                    res_raw = celdas[1].get_text(strip=True)
                                    visitante = celdas[2].get_text(strip=True)

                                    if local and visitante:
                                        if partido_actual and "equipo_local" in partido_actual:
                                            partidos_jornada.append(partido_actual)
                                            partido_actual = {}

                                        res_fmt, g_loc, g_vis, estado = parsear_resultado(res_raw)
                                        partido_id = f"{id_grupo}_{id_jornada}_{local}_{visitante}".replace(" ", "_").replace(".", "")

                                        partido_actual = {
                                            "id": partido_id,
                                            "competicion": nombre_comp,
                                            "grupo": nombre_grupo,
                                            "id_grupo": str(id_grupo),
                                            "jornada": txt_jornada,
                                            "id_jornada": str(id_jornada),
                                            "equipo_local": local,
                                            "equipo_visitante": visitante,
                                            "resultado": res_fmt,
                                            "goles_local": g_loc,
                                            "goles_visitante": g_vis,
                                            "estado": estado,
                                            "arbitro": "No asignado",
                                            "updated_at": datetime.utcnow().isoformat()
                                        }

                                if "Árbitro:" in texto_fila or "Arbitro:" in texto_fila:
                                    match_arb = re.search(r'(?:Árbitro|Arbitro):\s*\|?\s*([A-ZÁÉÍÓÚÑ\s,]+)', texto_fila)
                                    if match_arb and partido_actual:
                                        partido_actual["arbitro"] = match_arb.group(1).strip()

                            if partido_actual and "equipo_local" in partido_actual:
                                partidos_jornada.append(partido_actual)

                            if partidos_jornada:
                                ok = sincronizar_supabase(partidos_jornada)
                                if ok:
                                    print(f"      ✅ {txt_jornada}: {len(partidos_jornada)} partidos procesados.")
                                break

                        except Exception as err:
                            if intento == 3:
                                print(f"      ❌ Fallo en {txt_jornada}: {err}")
                            time.sleep(1.5)

        browser.close()

    print("\n🎉 Extracción completa finalizada. Base de datos lista para el Dashboard.")

if __name__ == "__main__":
    extractor_barrido_total()