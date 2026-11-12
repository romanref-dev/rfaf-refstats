from playwright.sync_api import sync_playwright
import testacta as rfaf

ACTA_ID = "2733996"


def main():

    print("DIAGNOSTICO DE ESTRUCTURA DE EQUIPOS")
    print("=" * 75)

    with sync_playwright() as playwright:

        navegador = playwright.chromium.launch(headless=True)
        page = navegador.new_page()

        try:

            page.goto(
                rfaf.URL_ACTA_BASE.format(id=ACTA_ID),
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(2000)

            bloques = page.evaluate("""
                () => {

                    const imagenes = Array.from(
                        document.querySelectorAll(
                            'img[src*="tarj_amar"], img[src*="tarj_roja"]'
                        )
                    );

                    const grupos = new Map();

                    imagenes.forEach(img => {

                        let nodo = img.parentElement;
                        let bloqueTarjeta = "";

                        for (let i = 0; i < 5 && nodo; i++) {

                            const texto = (nodo.innerText || "")
                                .replace(/\\\\s+/g, " ")
                                .trim();

                            if (texto.includes("Titulares")) {
                                bloqueTarjeta = texto;
                                break;
                            }

                            nodo = nodo.parentElement;
                        }

                        if (!grupos.has(bloqueTarjeta)) {
                            grupos.set(bloqueTarjeta, img);
                        }

                    });

                    return Array.from(grupos.entries()).map(
                        ([texto, img], indice) => {

                            const niveles = [];
                            let nodo = img;

                            for (let i = 1; i <= 9 && nodo; i++) {

                                const textoNodo = (
                                    nodo.innerText || ""
                                ).replace(/\\\\s+/g, " ").trim();

                                const anterior = nodo.previousElementSibling;
                                const siguiente = nodo.nextElementSibling;

                                niveles.push({
                                    nivel: i,
                                    etiqueta: nodo.tagName,
                                    clase: nodo.className?.toString() || "",
                                    id: nodo.id || "",
                                    texto: textoNodo.substring(0, 160),
                                    anterior: (
                                        anterior?.innerText || ""
                                    ).replace(/\\\\s+/g, " ").trim().substring(0, 100),
                                    siguiente: (
                                        siguiente?.innerText || ""
                                    ).replace(/\\\\s+/g, " ").trim().substring(0, 100)
                                });

                                nodo = nodo.parentElement;
                            }

                            return {
                                grupo: indice + 1,
                                jugador: (
                                    img.parentElement?.innerText || ""
                                ).replace(/\\\\s+/g, " ").trim(),
                                niveles: niveles
                            };

                        }
                    );

                }
            """)

            for grupo in bloques:

                print(f"\\nBLOQUE {grupo['grupo']}")
                print("-" * 75)

                print("Tarjeta de referencia:", grupo["jugador"])

                for nivel in grupo["niveles"]:

                    print(
                        f"Nivel {nivel['nivel']} | "
                        f"{nivel['etiqueta']} | "
                        f"class={nivel['clase']} | "
                        f"id={nivel['id']}"
                    )

                    if nivel["texto"]:
                        print("  Texto:", nivel["texto"])

                    if nivel["anterior"]:
                        print("  Anterior:", nivel["anterior"])

                    if nivel["siguiente"]:
                        print("  Siguiente:", nivel["siguiente"])

            print("\\nDIAGNOSTICO TERMINADO")

        finally:
            navegador.close()


if __name__ == "__main__":
    main()