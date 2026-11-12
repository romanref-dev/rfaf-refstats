
from playwright.sync_api import sync_playwright
import testacta as rfaf

ACTA_ID = "2733996"


def main():

    print("DIAGNOSTICO DE TARJETAS RFAF")
    print("=" * 80)

    with sync_playwright() as playwright:

        navegador = playwright.chromium.launch(
            headless=True
        )

        page = navegador.new_page()

        try:

            page.goto(
                rfaf.URL_ACTA_BASE.format(id=ACTA_ID),
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(2500)

            tarjetas = page.evaluate(
                """
                () => {

                    const imagenes = Array.from(
                        document.querySelectorAll(
                            'img[src*="tarj_amar"], img[src*="tarj_roja"]'
                        )
                    );

                    return imagenes.map((img, i) => {

                        let nodo = img;
                        const contenedores = [];

                        for (let nivel = 0; nivel < 6 && nodo; nivel++) {

                            const texto = (
                                nodo.innerText || ""
                            ).replace(/\\s+/g, " ").trim();

                            if (
                                texto &&
                                !contenedores.includes(texto)
                            ) {
                                contenedores.push(texto);
                            }

                            nodo = nodo.parentElement;
                        }

                        const src = (
                            img.getAttribute("src") || ""
                        ).toLowerCase();

                        return {
                            numero: i + 1,
                            tipo: src.includes("tarj_amar")
                                ? "AMARILLA"
                                : "ROJA",
                            titulo: img.getAttribute("title") || "",
                            alt: img.getAttribute("alt") || "",
                            contenedores: contenedores
                        };

                    });

                }
                """
            )

            print("Acta:", ACTA_ID)
            print("Tarjetas encontradas:", len(tarjetas))
            print("-" * 80)

            for tarjeta in tarjetas:

                print(
                    f"\nTARJETA {tarjeta['numero']} "
                    f"| {tarjeta['tipo']}"
                )

                if tarjeta["titulo"]:
                    print("Título:", tarjeta["titulo"])

                if tarjeta["alt"]:
                    print("Alt:", tarjeta["alt"])

                for nivel, texto in enumerate(
                    tarjeta["contenedores"],
                    start=1
                ):

                    print(
                        f"Contenedor {nivel}: {texto[:250]}"
                    )

            print("\nDIAGNOSTICO TERMINADO")

        finally:

            navegador.close()


if __name__ == "__main__":
    main()
