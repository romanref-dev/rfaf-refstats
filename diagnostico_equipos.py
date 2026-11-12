
import re
import time
from playwright.sync_api import sync_playwright


URL = (
    "https://www.rfaf.es/pnfg/NPcd/"
    "NFG_CmpJornada?cod_primaria=1000120"
)

COMPETICION_ID = "48466530"
GRUPO_ID = "49641343"
JORNADA = "1"


def seleccionar(page, selector, valor):

    page.locator(selector).wait_for(
        state="attached",
        timeout=30000
    )

    resultado = page.evaluate(
        """
        ({selector, valor}) => {
            const select = document.querySelector(selector);

            if (!select) {
                return "SELECT NO ENCONTRADO";
            }

            const opcion = Array.from(select.options).find(
                o => o.value === String(valor)
            );

            if (!opcion) {
                return "OPCION NO ENCONTRADA";
            }

            select.value = opcion.value;

            select.dispatchEvent(
                new Event("input", {bubbles:true})
            );

            select.dispatchEvent(
                new Event("change", {bubbles:true})
            );

            return opcion.textContent.trim();
        }
        """,
        {
            "selector": selector,
            "valor": str(valor)
        }
    )

    if resultado in (
        "SELECT NO ENCONTRADO",
        "OPCION NO ENCONTRADA"
    ):
        raise RuntimeError(resultado)

    print(resultado)
    page.wait_for_timeout(2000)


def obtener_actas(page):

    return page.evaluate(
        """
        () => {
            const enlaces = Array.from(
                document.querySelectorAll('a[href*="CodActa"]')
            );

            return enlaces.map(enlace => {

                const href = enlace.getAttribute("href") || "";
                const match = href.match(/[?&]CodActa=(\\d+)/i);

                if (!match) return null;

                const fila = enlace.closest("tr");

                return {
                    acta: match[1],
                    texto: (fila?.innerText || "")
                        .replace(/\\s+/g, " ")
                        .trim(),
                    href: href
                };

            }).filter(Boolean);
        }
        """
    )


with sync_playwright() as p:

    navegador = p.chromium.launch(headless=True)

    page = navegador.new_page(
        viewport={"width": 1366, "height": 900}
    )

    try:

        print("\nDIAGNOSTICO RFAF - JORNADA 1")
        print("=" * 70)

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(3000)

        print("\nSeleccionando competición:")
        seleccionar(
            page,
            "select#competicion",
            COMPETICION_ID
        )

        print("\nSeleccionando grupo:")
        seleccionar(
            page,
            "select#grupo",
            GRUPO_ID
        )

        print("\nSeleccionando jornada:")
        seleccionar(
            page,
            "select#jornada",
            JORNADA
        )

        print("\nEsperando a que los partidos se estabilicen...")

        ultimo_numero = -1
        repeticiones = 0
        actas = []

        for intento in range(40):

            actas = obtener_actas(page)

            if len(actas) == ultimo_numero:
                repeticiones += 1
            else:
                repeticiones = 0
                ultimo_numero = len(actas)

            if repeticiones >= 5:
                break

            page.wait_for_timeout(500)

        print("\nRESULTADO")
        print("=" * 70)
        print("Partidos detectados:", len(actas))

        for numero, partido in enumerate(actas, start=1):

            print(
                f"{numero}. ACTA {partido['acta']} | "
                f"{partido['texto'] or 'SIN TEXTO EN FILA'}"
            )

        print("\nURL FINAL:")
        print(page.url)

        print("\nDIAGNOSTICO TERMINADO")

    finally:
        navegador.close()
