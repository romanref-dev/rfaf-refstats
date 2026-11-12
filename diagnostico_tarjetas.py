import re
from playwright.sync_api import sync_playwright

ACTA_ID = "2734018"

URL = (
    "https://www.rfaf.es/pnfg/NPcd/"
    f"NFG_CmpPartido?cod_primaria=1000120&CodActa={ACTA_ID}&cod_acta={ACTA_ID}"
)

JS_DIAGNOSTICO = """
() => {
    const imagenes = document.querySelectorAll(
        'img[src*="tarj_amar"], img[src*="tarj_roja"]'
    );

    const resultados = [];

    imagenes.forEach(img => {
        const fila = img.closest("tr");
        const details = img.closest("div.details");

        const equipo = details?.querySelector(":scope > .number")
            ?.innerText.trim() || "NO IDENTIFICADO";

        const texto = fila?.innerText.trim() || "";

        const minuto = texto.match(/\\((\\d+\\+?\\d*')\\)/)?.[1]
            || "NO IDENTIFICADO";

        const jugador = texto
            .replace(/\\(\\d+\\+?\\d*'\\)/, "")
            .trim();

        const tipo = img.src.includes("tarj_roja")
            ? "ROJA"
            : "AMARILLA";

        resultados.push({
            equipo,
            tipo,
            minuto,
            jugador
        });
    });

    return resultados;
}
"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"ACTA {ACTA_ID}")
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        tarjetas = page.evaluate(JS_DIAGNOSTICO)

        print(f"Tarjetas encontradas: {len(tarjetas)}")
        print("-" * 65)

        errores = 0

        for tarjeta in tarjetas:
            equipo = tarjeta["equipo"]
            tipo = tarjeta["tipo"]
            minuto = tarjeta["minuto"]
            jugador = tarjeta["jugador"]

            if (
                equipo == "NO IDENTIFICADO"
                or minuto == "NO IDENTIFICADO"
                or not jugador
            ):
                errores += 1

            print(
                f"{equipo} | {tipo} | "
                f"{minuto} | {jugador}"
            )

        print("-" * 65)
        print(f"Errores: {errores}")

        browser.close()


if __name__ == "__main__":
    main()