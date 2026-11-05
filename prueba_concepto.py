import time
from playwright.sync_api import sync_playwright

ID_DIVISION_HONOR = "48466530"  # ID de la División Honor Sénior

def prueba_focalizada():
    print("🧪 Lanzando prueba de concepto (PoC) en modo visible...")

    with sync_playwright() as p:
        # headless=False para que veas la ventana emergente en tu escritorio
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        url = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"
        print(f"1️⃣ Navegando a la portada: {url}")
        page.goto(url, wait_until="networkidle")
        page.screenshot(path="poc_01_portada.png")

        # Localizamos el selector de competición
        select_comp = page.locator('select#competicion, select[name="competicion"]')
        print("2️⃣ Esperando selector de competición...")
        select_comp.wait_for(state="visible", timeout=10000)

        print(f"3️⃣ Seleccionando 'División Honor Sénior' (ID: {ID_DIVISION_HONOR})...")
        select_comp.select_option(value=ID_DIVISION_HONOR)

        # Esperamos 4 segundos para observar la respuesta del servidor en pantalla
        print("⏳ Esperando respuesta del servidor PNFG...")
        time.sleep(4)
        page.screenshot(path="poc_02_tras_seleccion.png")

        # Inspeccionamos los selectores que se han generado en el DOM
        html_grupo = page.locator('select#grupo, select[name="grupo"]').inner_html()
        print("\n=== CONTENIDO HTML DEL SELECTOR DE GRUPO ===")
        print(html_grupo)
        print("============================================\n")

        # Evaluamos el número de opciones de grupo
        opciones = page.locator('select#grupo option, select[name="grupo"] option').all()
        print(f"📊 Opciones totales encontradas en el selector 'grupo': {len(opciones)}")
        
        for opt in opciones:
            val = opt.get_attribute("value")
            txt = opt.inner_text().strip()
            print(f"   👉 Opción: '{txt}' | Valor (ID): '{val}'")

        browser.close()
        print("\n✅ Prueba finalizada. Capturas guardadas: 'poc_01_portada.png' y 'poc_02_tras_seleccion.png'")

if __name__ == "__main__":
    prueba_focalizada()