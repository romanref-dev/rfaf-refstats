
import re
from playwright.sync_api import sync_playwright
import testacta as rfaf

GRUPOS = {
    "Grupo 1": "49641343",
    "Grupo 2": "48933162"
}

def seleccionar(page, selector, valor):
    resultado = page.evaluate(
        """
        ({selector, valor}) => {
            const select = document.querySelector(selector);
            if (!select) return "SELECT NO ENCONTRADO";

            const opcion = Array.from(select.options).find(
                o => o.value === String(valor)
            );

            if (!opcion) return "OPCION NO ENCONTRADA";

            select.value = opcion.value;
            select.dispatchEvent(new Event("change", {bubbles:true}));

            return opcion.textContent.trim();
        }
        """,
        {"selector": selector, "valor": str(valor)}
    )

    if resultado in ("SELECT NO ENCONTRADO", "OPCION NO ENCONTRADA"):
        raise RuntimeError(resultado)

    page.wait_for_timeout(1500)
    return resultado


with sync_playwright() as p:
    navegador = p.chromium.launch(headless=True)
    page = navegador.new_page()

    try:
        for nombre, grupo_id in GRUPOS.items():

            print("\n" + "=" * 70)
            print(nombre)
            print("=" * 70)

            page.goto(
                rfaf.URL_BASE,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(2000)

            print(
                "Competición:",
                seleccionar(
                    page,
                    "select#competicion",
                    rfaf.COMPETICION_ID
                )
            )

            print(
                "Grupo:",
                seleccionar(
                    page,
                    "select#grupo",
                    grupo_id
                )
            )

            opciones = page.locator(
                "select#jornada"
            ).evaluate(
                """select => Array.from(select.options).map(o => ({
                    value: o.value,
                    texto: o.textContent.trim()
                }))"""
            )

            print("\nOPCIONES DEL DESPLEGABLE:")

            for opcion in opciones:
                print(
                    f"Texto: {opcion['texto']} | "
                    f"VALUE: {opcion['value']!r}"
                )

    finally:
        navegador.close()
