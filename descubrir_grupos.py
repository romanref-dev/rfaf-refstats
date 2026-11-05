import json
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

def descubrir_grupos():
    mapa_completo = {}
    archivo_salida = "mapa_rfaf.json"

    print("🤖 Iniciando navegador para forzar los eventos PostBack de la RFAF...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Cargamos la página base sin forzar variables de competición en la URL
        url_base = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"
        
        for nombre_comp, cod_comp in COMPETICIONES_OBJETIVO.items():
            print(f"📡 Procesando: {nombre_comp} (ID: {cod_comp})...")
            
            try:
                page.goto(url_base, wait_until="domcontentloaded")
                
                # Seleccionamos la competición en el menú desplegable para activar el AJAX/PostBack
                page.locator('select[name="codcompeticion"]').select_option(value=cod_comp)
                
                # Esperamos que el menú de grupos se actualice con los nuevos datos
                page.wait_for_function(
                    "document.querySelector('select[name=\"grupo\"]') && document.querySelector('select[name=\"grupo\"]').options.length > 1", 
                    timeout=8000
                )
                
                grupos = {}
                opciones = page.locator('select[name="grupo"] option').all()
                
                for opt in opciones:
                    val = opt.get_attribute("value")
                    texto = opt.inner_text().strip()
                    if val and val != "0" and "Seleccione" not in texto and "Cargando" not in texto:
                        grupos[texto] = val
                        print(f"   🔹 Grupo encontrado: {texto} -> ID: {val}")

                if not grupos:
                    print("   ⚠️ Sin subgrupos (grupo único).")

                mapa_completo[nombre_comp] = {
                    "id_competicion": cod_comp,
                    "grupos": grupos
                }

            except Exception as e:
                print("   ⚠️ Error al interactuar con el menú (puede no tener grupos asociados o la temporada cambió).")
                mapa_completo[nombre_comp] = {
                    "id_competicion": cod_comp,
                    "grupos": {}
                }

        browser.close()

    with open(archivo_salida, "w", encoding="utf-8") as f:
        json.dump(mapa_completo, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Concluido. Archivo '{archivo_salida}' actualizado con éxito.")

if __name__ == "__main__":
    descubrir_grupos()