
import re
import time
import unicodedata
from playwright.sync_api import sync_playwright


# ============================================================
# CONFIGURACION
# ============================================================

URL_BASE = (
    "https://www.rfaf.es/pnfg/NPcd/"
    "NFG_CmpJornada?cod_primaria=1000120"
)

URL_ACTA_BASE = (
    "https://www.rfaf.es/pnfg/NPcd/"
    "NFG_CmpPartido?cod_primaria=1000120&CodActa={id}&cod_acta={id}"
)

COMPETICION_ID = "48466530"
GRUPO_ID = "49641343"
JORNADAS = [1, 2, 3]

ESPERA = 1500
ESPERA_ENTRE_ACTAS = 1

# Espera de carga de partidos
ESPERA_ESTABILIDAD = 500
REPETICIONES_ESTABLES = 5
INTENTOS_ESTABILIDAD = 40


# ============================================================
# UTILIDADES
# ============================================================

def limpiar(texto):
    return re.sub(r"\s+", " ", texto or "").strip()


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto or "")
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )
    return limpiar(texto).upper()


# ============================================================
# SELECCIONAR COMPETICION, GRUPO Y JORNADA
# ============================================================

def seleccionar_opcion(page, selector, valor, descripcion):

    page.locator(selector).wait_for(
        state="attached",
        timeout=30000
    )

    page.wait_for_function(
        """
        ({selector, valor}) => {
            const select = document.querySelector(selector);

            return select &&
                Array.from(select.options).some(
                    o => o.value === String(valor)
                );
        }
        """,
        arg={
            "selector": selector,
            "valor": str(valor)
        },
        timeout=30000
    )

    resultado = page.evaluate(
        """
        ({selector, valor}) => {
            const select = document.querySelector(selector);

            if (!select) {
                return {ok:false, error:"Select no encontrado"};
            }

            const opcion = Array.from(select.options).find(
                o => o.value === String(valor)
            );

            if (!opcion) {
                return {ok:false, error:"Opción no encontrada"};
            }

            select.value = opcion.value;

            select.dispatchEvent(
                new Event("input", {bubbles:true})
            );

            select.dispatchEvent(
                new Event("change", {bubbles:true})
            );

            return {
                ok:true,
                texto:opcion.textContent.trim()
            };
        }
        """,
        {
            "selector": selector,
            "valor": str(valor)
        }
    )

    if not resultado["ok"]:
        raise RuntimeError(
            f"{descripcion}: {resultado}"
        )

    print(f"{descripcion}: {resultado['texto']}")
    page.wait_for_timeout(ESPERA)


# ============================================================
# EXTRAER ACTAS
# ============================================================

JS_ACTAS = r"""
() => {
    const enlaces = Array.from(
        document.querySelectorAll('a[href*="CodActa"]')
    );

    const ids = [];

    for (const enlace of enlaces) {
        const href = enlace.getAttribute("href") || "";
        const m = href.match(/[?&]CodActa=(\d+)/i);

        if (m && !ids.includes(m[1])) {
            ids.push(m[1]);
        }
    }

    return ids;
}
"""


def esperar_actas_estables(page):

    ultimo_numero = -1
    repeticiones = 0
    actas = []

    for _ in range(INTENTOS_ESTABILIDAD):

        actas = page.evaluate(JS_ACTAS)
        numero_actual = len(actas)

        if numero_actual == ultimo_numero:
            repeticiones += 1
        else:
            repeticiones = 0
            ultimo_numero = numero_actual

        if (
            numero_actual > 0
            and repeticiones >= REPETICIONES_ESTABLES
        ):
            return actas

        page.wait_for_timeout(ESPERA_ESTABILIDAD)

    if not actas:
        raise RuntimeError(
            "RFAF no ha cargado ningún enlace de acta."
        )

    print(
        "AVISO: No se confirmó la estabilidad completa "
        "de los partidos."
    )

    return actas


def cargar_jornada(page, jornada):

    page.goto(
        URL_BASE,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(2000)

    seleccionar_opcion(
        page,
        "select#competicion",
        COMPETICION_ID,
        "Competición"
    )

    seleccionar_opcion(
        page,
        "select#grupo",
        GRUPO_ID,
        "Grupo"
    )

    page.wait_for_timeout(2000)

    seleccionar_opcion(
        page,
        "select#jornada",
        str(jornada),
        f"Jornada {jornada}"
    )

    seleccionada = page.locator(
        "select#jornada"
    ).input_value()

    if seleccionada != str(jornada):
        raise RuntimeError(
            f"Jornada incorrecta. Esperada: {jornada}. "
            f"Seleccionada: {seleccionada}"
        )

    print("Esperando a que se carguen todos los partidos...")

    actas = esperar_actas_estables(page)

    print(
        f"Partidos cargados y estabilizados: {len(actas)}"
    )

    return actas


# ============================================================
# EXTRAER EQUIPOS DESDE EL CALENDARIO
# ============================================================

JS_CALENDARIO = r"""
() => {

    const limpiar = t =>
        (t || "").replace(/\s+/g, " ").trim();

    const enlaces = Array.from(
        document.querySelectorAll('a[href*="CodActa"]')
    );

    const partidos = {};

    for (const enlace of enlaces) {

        const href = enlace.getAttribute("href") || "";
        const match = href.match(/[?&]CodActa=(\d+)/i);

        if (!match) continue;

        const acta = match[1];
        const fila = enlace.closest("tr");

        if (!fila) continue;

        const textoFila = limpiar(fila.innerText);

        /*
         * Formato habitual:
         *
         * EQUIPO LOCAL - FECHA HORA EQUIPO VISITANTE
         *
         * También puede aparecer un marcador antes
         * de la fecha:
         *
         * EQUIPO LOCAL - 1 FECHA HORA EQUIPO VISITANTE
         */

        const fecha = textoFila.match(
            /(\d{2}-\d{2}-\d{4}\s+\d{1,2}:\d{2})/
        );

        let local = null;
        let visitante = null;

        if (fecha) {

            const posicion = fecha.index;

            const parteLocal = limpiar(
                textoFila.substring(0, posicion)
            );

            const parteVisitante = limpiar(
                textoFila.substring(
                    posicion + fecha[0].length
                )
            );

            /*
             * Eliminamos el separador y el posible
             * marcador que aparece antes de la fecha.
             */

            const localMatch = parteLocal.match(
                /^(.*?)\s+-\s*(?:\d+\s*)?$/
            );

            if (localMatch) {
                local = limpiar(localMatch[1]);
            }

            visitante = parteVisitante;

        }

        /*
         * Alternativa para filas con otra estructura.
         * Solo se utiliza si no se ha podido identificar
         * correctamente alguno de los dos equipos.
         */

        if (!local || !visitante) {

            const celdas = Array.from(
                fila.querySelectorAll("td")
            );

            const textos = celdas.map(
                celda => limpiar(celda.innerText)
            ).filter(Boolean);

            const candidatos = textos.filter(
                texto =>
                    !/^\d{1,2}-\d{1,2}-\d{4}/.test(texto) &&
                    !/^\d+$/.test(texto)
            );

            if (!local && candidatos.length >= 2) {
                local = candidatos[0];
            }

            if (!visitante && candidatos.length >= 2) {
                visitante = candidatos[candidatos.length - 1];
            }
        }

        if (local && visitante) {

            partidos[acta] = {
                local: local,
                visitante: visitante
            };

        }
    }

    return partidos;
}
"""


# ============================================================
# EXTRAER MARCADOR VALIDADO
# ============================================================

JS_MARCADOR = r"""
() => {
    const strong = document.querySelector("h2.ntype strong");

    if (!strong) return null;

    const elementos = Array.from(strong.children).filter(el =>
        el.tagName === "I" &&
        el.classList.contains("fa-solid")
    );

    if (elementos.length !== 2) return null;

    function visible(el) {
        const s = getComputedStyle(el);
        return s.display !== "none" &&
               s.visibility !== "hidden";
    }

    function pseudo(el) {
        const nodos = [el, ...el.querySelectorAll("*")];

        for (const nodo of nodos) {
            for (const tipo of ["::before", "::after"]) {

                const s = getComputedStyle(nodo, tipo);

                if (
                    s.display === "none" ||
                    s.visibility === "hidden"
                ) continue;

                let c = s.content;

                if (
                    !c ||
                    c === "none" ||
                    c === "normal" ||
                    c === '""'
                ) continue;

                c = c.replace(/^["']|["']$/g, "");

                const hex = c.match(
                    /^\\([0-9a-fA-F]{1,6})\s*$/
                );

                if (hex) {
                    c = String.fromCodePoint(
                        parseInt(hex[1], 16)
                    );
                }

                const m = c.match(/[0-9]/);

                if (m) return m[0];
            }
        }

        return null;
    }

    function clase(el) {
        const nodos = [el, ...el.querySelectorAll("*")];

        for (const nodo of nodos) {
            for (const c of nodo.classList) {
                const m = c.match(/^fa-([0-9])$/);

                if (m) return m[1];
            }
        }

        return null;
    }

    function texto(el) {

        function recorrer(nodo) {

            if (nodo.nodeType === Node.TEXT_NODE) {
                return nodo.nodeValue || "";
            }

            if (nodo.nodeType !== Node.ELEMENT_NODE) {
                return "";
            }

            if (
                ["script", "style"].includes(
                    nodo.tagName.toLowerCase()
                ) ||
                !visible(nodo)
            ) return "";

            return Array.from(nodo.childNodes)
                .map(recorrer)
                .join("");
        }

        return recorrer(el).replace(/\s+/g, "");
    }

    function extraer(el) {
        return (
            pseudo(el) ||
            clase(el) ||
            (texto(el).match(/[0-9]/) || [])[0] ||
            null
        );
    }

    const local = extraer(elementos[0]);
    const visitante = extraer(elementos[1]);

    if (local === null || visitante === null) {
        return null;
    }

    return local + "-" + visitante;
}
"""


# ============================================================
# EXTRAER ARBITRO Y DELEGACION
# ============================================================

JS_ARBITRO = r"""
() => {
    const normalizar = t =>
        (t || "").replace(/\s+/g, " ").trim();

    const elementos = Array.from(
        document.querySelectorAll("tr, li, div, p, span, td")
    );

    let texto = null;

    for (const el of elementos) {

        const t = normalizar(el.innerText);

        if (
            t.toUpperCase() !== "ARBITRO" &&
            t.toUpperCase() !== "ÁRBITRO"
        ) continue;

        let siguiente = el.nextElementSibling;

        while (siguiente) {

            const contenido = normalizar(
                siguiente.innerText
            );

            if (
                contenido &&
                !["ARBITRO", "ÁRBITRO"].includes(
                    contenido.toUpperCase()
                )
            ) {
                texto = contenido;
                break;
            }

            siguiente = siguiente.nextElementSibling;
        }

        if (!texto) {
            const fila = el.closest("tr");

            if (fila && fila.nextElementSibling) {
                texto = normalizar(
                    fila.nextElementSibling.innerText
                );
            }
        }

        if (texto) break;
    }

    if (!texto) {
        return {
            arbitro:null,
            delegacion:null
        };
    }

    const patron =
        /\s+DELEGACI[ÓO]N\s+DE\s+(.+)$/i;

    const m = texto.match(patron);

    return {
        arbitro: m
            ? texto.substring(0, m.index).trim()
            : texto,

        delegacion: m
            ? m[1].trim()
            : null
    };
}
"""


# ============================================================
# EXTRAER TOTALES DE TARJETAS POR EQUIPO
# ============================================================

JS_TARJETAS = r"""
({local, visitante}) => {

    const normalizar = t =>
        (t || "").replace(/\s+/g, " ").trim().toUpperCase();

    const equipos = {
        local: normalizar(local),
        visitante: normalizar(visitante)
    };

    const imagenes = Array.from(
        document.querySelectorAll(
            'img[src*="tarj_amar"], img[src*="tarj_roja"]'
        )
    );

    const resultado = {
        amarillas_local: 0,
        amarillas_visitante: 0,
        rojas_local: 0,
        rojas_visitante: 0,
        sin_asignar: 0,
        total: imagenes.length
    };

    for (const img of imagenes) {

        const src = (
            img.getAttribute("src") || ""
        ).toLowerCase();

        let tipo = null;

        if (src.includes("tarj_amar")) {
            tipo = "amarillas";
        }

        if (src.includes("tarj_roja")) {
            tipo = "rojas";
        }

        if (!tipo) continue;

        let nodo = img;
        let asignado = null;

        for (let i = 0; i < 7 && nodo; i++) {

            const texto = normalizar(nodo.innerText);

            const contieneLocal =
                equipos.local &&
                texto.includes(equipos.local);

            const contieneVisitante =
                equipos.visitante &&
                texto.includes(equipos.visitante);

            if (contieneLocal && !contieneVisitante) {
                asignado = "local";
                break;
            }

            if (contieneVisitante && !contieneLocal) {
                asignado = "visitante";
                break;
            }

            nodo = nodo.parentElement;
        }

        if (!asignado) {
            resultado.sin_asignar++;
            continue;
        }

        resultado[tipo + "_" + asignado]++;
    }

    return resultado;
}
"""


# ============================================================
# EXTRAER TARJETAS INDIVIDUALES
# ============================================================

JS_TARJETAS_INDIVIDUALES = r"""
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

        let tipo = null;

        if (src.includes("tarj_amar")) {
            tipo = "amarilla";
        } else if (src.includes("tarj_roja")) {
            tipo = "roja";
        }

        const fila = img.closest("tr");
        const equipoContenedor = img.closest("div.details");

        const textoFila = (
            fila?.innerText || ""
        ).replace(/\s+/g, " ").trim();

        const textoEquipo = (
            equipoContenedor?.innerText || ""
        ).replace(/\s+/g, " ").trim();

        const nombreEquipo = textoEquipo
            .split(/Titulares/i)[0]
            .trim();

        const coincidencia = textoFila.match(
            /\((\d+(?:\+\d+)?)'\)\s*(.+)/
        );

        return {

            tipo: tipo,

            minuto: coincidencia
                ? coincidencia[1]
                : null,

            jugador: coincidencia
                ? coincidencia[2].trim()
                : null,

            equipo: nombreEquipo || null

        };

    });

}
"""


# ============================================================
# PROCESAR ACTA
# ============================================================

def procesar_acta(page, jornada, acta_id, equipos_calendario):

    equipos = equipos_calendario.get(acta_id, {})

    try:

        page.goto(
            URL_ACTA_BASE.format(id=acta_id),
            wait_until="domcontentloaded",
            timeout=45000
        )

        page.wait_for_timeout(ESPERA)

        resultado = page.evaluate(JS_MARCADOR)
        arbitro = page.evaluate(JS_ARBITRO)

        # ----------------------------------------------------
        # TOTALES DE TARJETAS
        # ----------------------------------------------------

        local = equipos.get("local")
        visitante = equipos.get("visitante")

        if local and visitante:

            tarjetas = page.evaluate(
                JS_TARJETAS,
                {
                    "local": local,
                    "visitante": visitante
                }
            )

            if tarjetas["sin_asignar"] > 0:

                for campo in (
                    "amarillas_local",
                    "amarillas_visitante",
                    "rojas_local",
                    "rojas_visitante"
                ):
                    tarjetas[campo] = "?"

        else:

            tarjetas = {
                "amarillas_local": "?",
                "amarillas_visitante": "?",
                "rojas_local": "?",
                "rojas_visitante": "?",
                "sin_asignar": "?",
                "total": "?"
            }

        # ----------------------------------------------------
        # TARJETAS INDIVIDUALES
        # ----------------------------------------------------

        tarjetas_individuales = page.evaluate(
            JS_TARJETAS_INDIVIDUALES
        )

        errores_individuales = []

        for numero, tarjeta in enumerate(
            tarjetas_individuales,
            start=1
        ):

            if not tarjeta.get("jugador"):
                errores_individuales.append(
                    f"Tarjeta {numero}: jugador no identificado"
                )

            if not tarjeta.get("minuto"):
                errores_individuales.append(
                    f"Tarjeta {numero}: minuto no identificado"
                )

            if not tarjeta.get("equipo"):
                errores_individuales.append(
                    f"Tarjeta {numero}: equipo no identificado"
                )

            if not tarjeta.get("tipo"):
                errores_individuales.append(
                    f"Tarjeta {numero}: tipo no identificado"
                )

        correcto = all([
            local,
            visitante,
            resultado,
            arbitro.get("arbitro")
        ])

        return {
            "jornada": jornada,
            "acta": acta_id,
            "local": local,
            "visitante": visitante,
            "resultado": resultado,
            "arbitro": arbitro.get("arbitro"),
            "delegacion": arbitro.get("delegacion"),
            "tarjetas": tarjetas,
            "tarjetas_individuales": tarjetas_individuales,
            "errores_individuales": errores_individuales,
            "estado": "OK" if correcto else "REVISAR"
        }

    except Exception as e:

        return {
            "jornada": jornada,
            "acta": acta_id,
            "local": equipos.get("local"),
            "visitante": equipos.get("visitante"),
            "resultado": None,
            "arbitro": None,
            "delegacion": None,
            "tarjetas": {
                "amarillas_local": "?",
                "amarillas_visitante": "?",
                "rojas_local": "?",
                "rojas_visitante": "?",
                "sin_asignar": "?",
                "total": "?"
            },
            "tarjetas_individuales": [],
            "errores_individuales": [
                "Error procesando acta: " + str(e)
            ],
            "estado": "ERROR: " + str(e)
        }


# ============================================================
# MOSTRAR RESULTADO
# ============================================================

def mostrar_linea(r):

    t = r["tarjetas"]

    return (
        f"J{r['jornada']} | "
        f"ACTA {r['acta']} | "
        f"{r['local'] or 'LOCAL NO IDENTIFICADO'} - "
        f"{r['visitante'] or 'VISITANTE NO IDENTIFICADO'} | "
        f"{r['resultado'] or 'SIN RESULTADO'} | "
        f"{r['arbitro'] or 'SIN ARBITRO'} | "
        f"AM {t['amarillas_local']}-{t['amarillas_visitante']} | "
        f"RO {t['rojas_local']}-{t['rojas_visitante']} | "
        f"{r['estado']}"
    )


def mostrar_tarjetas_individuales(r):

    tarjetas = r.get("tarjetas_individuales", [])

    if not tarjetas:
        print("    Sin tarjetas individuales encontradas.")
        return

    for tarjeta in tarjetas:

        jugador = tarjeta.get("jugador") or "JUGADOR NO IDENTIFICADO"
        equipo = tarjeta.get("equipo") or "EQUIPO NO IDENTIFICADO"
        minuto = tarjeta.get("minuto") or "?"
        tipo = (tarjeta.get("tipo") or "DESCONOCIDA").upper()

        estado = (
            "OK"
            if (
                tarjeta.get("jugador")
                and tarjeta.get("equipo")
                and tarjeta.get("minuto")
                and tarjeta.get("tipo")
            )
            else "REVISAR"
        )

        print(
            f"    [{estado}] {tipo} | "
            f"{minuto}' | {jugador} | {equipo}"
        )

    errores = r.get("errores_individuales", [])

    if errores:
        for error in errores:
            print(f"    ERROR: {error}")


# ============================================================
# MAIN
# ============================================================

def main():

    resultados = []

    print("\nRFAF - JORNADAS 1, 2 Y 3")
    print("=" * 140)

    with sync_playwright() as playwright:

        navegador = playwright.chromium.launch(
            headless=True
        )

        page = navegador.new_page(
            viewport={"width": 1366, "height": 900}
        )

        try:

            for jornada in JORNADAS:

                print(f"\nJORNADA {jornada}")
                print("-" * 140)

                actas = cargar_jornada(page, jornada)

                equipos_calendario = page.evaluate(
                    JS_CALENDARIO
                )

                print(
                    f"Partidos con equipos identificados: "
                    f"{len(equipos_calendario)}"
                )

                for acta_id in actas:

                    datos = procesar_acta(
                        page,
                        jornada,
                        acta_id,
                        equipos_calendario
                    )

                    resultados.append(datos)

                    print(mostrar_linea(datos))

                    print("  TARJETAS INDIVIDUALES:")
                    mostrar_tarjetas_individuales(datos)

                    time.sleep(ESPERA_ENTRE_ACTAS)

        finally:
            navegador.close()

    # ========================================================
    # RESUMEN
    # ========================================================

    print("\n" + "=" * 140)
    print("RESUMEN")

    for jornada in JORNADAS:

        partidos = [
            r for r in resultados
            if r["jornada"] == jornada
        ]

        correctos = sum(
            1 for r in partidos
            if r["estado"] == "OK"
        )

        tarjetas_individuales = sum(
            len(r["tarjetas_individuales"])
            for r in partidos
        )

        errores_individuales = sum(
            len(r["errores_individuales"])
            for r in partidos
        )

        print(
            f"JORNADA {jornada}: "
            f"{correctos}/{len(partidos)} partidos con datos básicos | "
            f"{tarjetas_individuales} tarjetas individuales | "
            f"{errores_individuales} errores individuales"
        )

    print("-" * 80)
    print(f"TOTAL PARTIDOS: {len(resultados)}")

    total_tarjetas = sum(
        len(r["tarjetas_individuales"])
        for r in resultados
    )

    total_errores = sum(
        len(r["errores_individuales"])
        for r in resultados
    )

    print(f"TOTAL TARJETAS INDIVIDUALES: {total_tarjetas}")
    print(f"ERRORES DE EXTRACCION INDIVIDUAL: {total_errores}")

    with open(
        "resultados_j1_j2_j3.txt",
        "w",
        encoding="utf-8"
    ) as archivo:

        for r in resultados:

            archivo.write(
                mostrar_linea(r) + "\n"
            )

            archivo.write("  TARJETAS INDIVIDUALES:\n")

            for tarjeta in r["tarjetas_individuales"]:

                archivo.write(
                    "    "
                    + str(tarjeta.get("tipo"))
                    + " | "
                    + str(tarjeta.get("minuto"))
                    + "' | "
                    + str(tarjeta.get("jugador"))
                    + " | "
                    + str(tarjeta.get("equipo"))
                    + "\n"
                )

            for error in r["errores_individuales"]:
                archivo.write("    ERROR: " + error + "\n")

    print("Archivo generado: resultados_j1_j2_j3.txt")
    print("No se ha conectado ni escrito nada en Supabase.")


if __name__ == "__main__":
    main()
