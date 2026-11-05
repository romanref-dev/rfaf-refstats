import time
from playwright.sync_api import sync_playwright

URL_PRUEBA = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120&codcompeticion=48466530&codgrupo=49641343&codjornada=1"

def inspeccionar_tabla_asincrona():
    print("🔬 Esperando a la renderización completa de la tabla de resultados...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        page.goto(URL_PRUEBA, wait_until="domcontentloaded")

        # 1. Esperamos a que la tabla de partidos aparezca en el DOM
        try:
            page.wait_for_selector('table.tabla_resultados, table.grid, table[class*="tabla"]', timeout=10000)
            print("✅ Tabla de partidos localizada en pantalla.")
        except Exception as e:
            print(f"⚠️ La tabla tardó en cargar. Guardando captura de estado...")
            page.screenshot(path="poc_error_tabla.png")

        time.sleep(2)  # Margen de seguridad para bindings de JS

        # 2. Buscamos todas las filas o celdas de la tabla para ver sus atributos
        filas = page.locator('table tr').all()
        print(f"📊 Filas encontradas en la tabla: {len(filas)}")

        partidos_detectados = 0
        for idx, fila in enumerate(filas):
            texto = fila.inner_text().strip().replace("\n", " | ")
            onclick_attr = fila.get_attribute("onclick") or ""
            
            # Buscar también en las celdas o botones dentro de la fila
            hijos_onclick = fila.locator('*[onclick]').all()
            eventos_hijos = [h.get_attribute("onclick") for h in hijos_onclick if h.get_attribute("onclick")]

            if texto and not any(k in texto for k in ["Jornada", "Local", "Equipo"]):
                partidos_detectados += 1
                print(f"\n⚽ Partido [{partidos_detectados}]: {texto}")
                if onclick_attr:
                    print(f"   👉 onClick en fila: '{onclick_attr}'")
                if eventos_hijos:
                    print(f"   👉 onClick en elementos internos: {eventos_hijos}")

        page.screenshot(path="poc_actas_tabla_cargada.png")
        browser.close()

if __name__ == "__main__":
    inspeccionar_tabla_asincrona()