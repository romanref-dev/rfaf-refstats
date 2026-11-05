import json
import time
from playwright.sync_api import sync_playwright

COMPETICIONES_OBJETIVO = {
    "División Honor Sénior": "48466530",
    "3ª Federación": "48465908",
    "1ª Andaluza Sénior (Sevilla)": "48466124",
    "1ª Andaluza Sénior (Málaga)": "48465920",
    "1ª Andaluza SENIOR (CADIZ)": "48680130",
    "1ª Andaluza Sénior (Granada)": "48466157",
    "1ª Andaluza Senior (Cordoba)": "48466090",
    "1ª Andaluza Senior (Huelva)": "48466521",
    "1ª Andaluza Sénior (Jaén)": "48466094",
    "1ª Andaluza Sénior (Almería)": "48786377"
}

def generar_mapa():
    mapa_completo = {}
    archivo_salida = "mapa_rfaf.json"

    print("🚀 Construyendo mapa completo con recarga limpia de DOM...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        url_base = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"

        for nombre_comp, cod_comp in COMPETICIONES_OBJETIVO.items():
            print(f"📡 Procesando: {nombre_comp} (ID: {cod_comp})...")
            
            try:
                # 1. Carga limpia por cada competición para reiniciar los scripts de Novanet
                page.goto(url_base, wait_until="networkidle")

                # 2. Localizar selector nativo y forzar visibilidad por si Novanet lo enmascara
                select_comp = page.locator('select#competicion, select[name="competicion"]')
                select_comp.wait_for(state="attached", timeout=5000)
                
                # 3. Seleccionar valor
                select_comp.select_option(value=cod_comp, force=True)

                # 4. Dar margen para la llamada AJAX de los grupos
                time.sleep(3)

                grupos = {}
                opciones = page.locator('select#grupo option, select[name="grupo"] option').all()

                for opt in opciones:
                    val = opt.get_attribute("value")
                    txt = opt.inner_text().strip()
                    if val and val != "0" and not any(k in txt.lower() for k in ["seleccione", "cargando"]):
                        grupos[txt] = val
                        print(f"   🔹 {txt} -> ID: {val}")

                mapa_completo[nombre_comp] = {
                    "id_competicion": cod_comp,
                    "grupos": grupos
                }

            except Exception as e:
                print(f"   ⚠️ Fallo procesando {nombre_comp}: {e}")

        browser.close()

    with open(archivo_salida, "w", encoding="utf-8") as f:
        json.dump(mapa_completo, f, ensure_ascii=False, indent=4)

    print(f"\n✅ ¡Mapa generado con éxito en '{archivo_salida}'!")

if __name__ == "__main__":
    generar_mapa()