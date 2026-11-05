import time
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL_BASE = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"
ID_COMP = "48466530"  # División Honor Sénior
ID_GRUPO = "49641343" # Grupo 1
ID_JORNADA = "1"

def extraer_partidos_y_arbitros():
    print("🔬 Extrayendo partidos y árbitros (Parseo nativo Python/BeautifulSoup)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        # 1. Cargar la vista base e interactuar con los desplegables
        page.goto(URL_BASE, wait_until="networkidle")

        page.locator('select#competicion').select_option(value=ID_COMP, force=True)
        time.sleep(1.5)
        page.locator('select#grupo').select_option(value=ID_GRUPO, force=True)
        time.sleep(1.5)
        
        print(f"⏳ Seleccionando Jornada {ID_JORNADA}...")
        page.locator('select#jornada').select_option(value=ID_JORNADA, force=True)
        
        # Pausa fija para asegurar que el JS de Novanet recargue la tabla
        time.sleep(3.5)

        # 2. Obtener el HTML renderizado y parsearlo con BeautifulSoup
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        filas = soup.find_all('tr')
        partidos = []
        partido_actual = {}

        for fila in filas:
            texto_fila = fila.get_text(separator=" ", strip=True)
            
            if not texto_fila or any(k in texto_fila for k in ["Jornada", "Equipos", "Fecha"]):
                continue

            # Detectar fila principal de resultado (contiene " - ")
            celdas = fila.find_all('td')
            if len(celdas) >= 3:
                local = celdas[0].get_text(strip=True)
                res = celdas[1].get_text(strip=True)
                visitante = celdas[2].get_text(strip=True)

                if local and visitante and ("-" in res or res == "" or res.isdigit()):
                    if partido_actual and "local" in partido_actual:
                        partidos.append(partido_actual)
                        partido_actual = {}

                    partido_actual = {
                        "local": local,
                        "resultado": res,
                        "visitante": visitante,
                        "arbitro": "No asignado"
                    }

            # Detectar fila secundaria de detalles donde figura el árbitro
            if "Árbitro:" in texto_fila or "Arbitro:" in texto_fila:
                match = re.search(r'(?:Árbitro|Arbitro):\s*\|?\s*([A-ZÁÉÍÓÚÑ\s,]+)', texto_fila)
                if match and partido_actual:
                    partido_actual["arbitro"] = match.group(1).strip()

        if partido_actual and "local" in partido_actual:
            partidos.append(partido_actual)

        print(f"\n✅ Total encuentros parseados: {len(partidos)}\n")
        
        if len(partidos) == 0:
            print("⚠️ No se extrajeron encuentros. Guardando captura de pantalla para diagnóstico...")
            page.screenshot(path="diagnostico_jornada.png")
            print("📸 Captura guardada en 'diagnostico_jornada.png'")
        else:
            for idx, p_data in enumerate(partidos, 1):
                print(f" Partido [{idx}]: {p_data.get('local')} [{p_data.get('resultado')}] {p_data.get('visitante')}")
                print(f"   👤 Árbitro: {p_data.get('arbitro')}\n")

        browser.close()

if __name__ == "__main__":
    extraer_partidos_y_arbitros()