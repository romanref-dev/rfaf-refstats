
from playwright.sync_api import sync_playwright
import testacta as rfaf
import re


ACTA_ID = "2733997"


def extraer_tarjetas(page):

    return page.evaluate("""
        () => {

            const imagenes = Array.from(
                document.querySelectorAll(
                    'img[src*="tarj_amar"], img[src*="tarj_roja"]'
                )
            );

            return imagenes.map(img => {

                const src = (
                    img.getAttribute("src") || ""
                ).toLowerCase();

                const fila = img.closest("tr");
                const celda = img.closest("td");
                const equipoContenedor = img.closest("div.details");

                const textoFila = (
                    fila?.innerText || ""
                ).replace(/\\\\s+/g, " ").trim();

                const textoEquipo = (
                    equipoContenedor?.innerText || ""
                ).replace(/\\\\s+/g, " ").trim();

                const nombreEquipo = textoEquipo
                    .split(/Titulares/i)[0]
                    .trim();

                const coincidencia = textoFila.match(
                    /\\((\\d+\\+?\\d*)'\\)\\s*(.+)/
                );

                return {

                    tipo: src.includes("tarj_amar")
                        ? "AMARILLA"
                        : "ROJA",

                    minuto: coincidencia
                        ? coincidencia[1]
                        : "",

                    jugador: coincidencia
                        ? coincidencia[2].trim()
                        : "",

                    equipo: nombreEquipo,

                    fila: textoFila,

                    encontrado_equipo: !!equipoContenedor

                };

            });

        }
    """)


def main():

    print("DIAGNOSTICO DE TARJETAS INDIVIDUALES RFAF")
    print("=" * 80)

    with sync_playwright() as playwright:

        navegador = playwright.chromium.launch(headless=True)
        page = navegador.new_page()

        try:

            page.goto(
                rfaf.URL_ACTA_BASE.format(id=ACTA_ID),
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(2500)

            tarjetas = extraer_tarjetas(page)

            print("Acta:", ACTA_ID)
            print("Tarjetas encontradas:", len(tarjetas))
            print("-" * 80)

            resumen = {}

            for numero, tarjeta in enumerate(tarjetas, start=1):

                equipo = tarjeta["equipo"] or "EQUIPO NO IDENTIFICADO"

                resumen.setdefault(
                    equipo,
                    {"AMARILLA": 0, "ROJA": 0}
                )

                resumen[equipo][tarjeta["tipo"]] += 1

                estado = (
                    "OK"
                    if tarjeta["jugador"]
                    and tarjeta["minuto"]
                    and tarjeta["encontrado_equipo"]
                    else "REVISAR"
                )

                print(
                    f"{numero:02d}. [{estado}] "
                    f"{tarjeta['tipo']} | "
                    f"{tarjeta['minuto']}' | "
                    f"{tarjeta['jugador'] or 'JUGADOR NO IDENTIFICADO'}"
                )

                print(
                    f"    Equipo: {equipo or 'NO IDENTIFICADO'}"
                )

            print("\\nRESUMEN POR EQUIPO")
            print("-" * 80)

            for equipo, datos in resumen.items():

                print(
                    f"{equipo}: "
                    f"{datos['AMARILLA']} amarillas | "
                    f"{datos['ROJA']} rojas"
                )

            errores = sum(
                1 for tarjeta in tarjetas
                if (
                    not tarjeta["jugador"]
                    or not tarjeta["minuto"]
                    or not tarjeta["encontrado_equipo"]
                )
            )

            print("\\nRESULTADO")
            print("-" * 80)
            print("Tarjetas:", len(tarjetas))
            print("Errores:", errores)

            if tarjetas and errores == 0:
                print("EXTRACCION INDIVIDUAL CORRECTA")
            else:
                print("EXTRACCION PENDIENTE DE REVISION")

        finally:

            navegador.close()


if __name__ == "__main__":
    main()
