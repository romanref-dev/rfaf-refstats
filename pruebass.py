import random
import time
import re

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)


# =========================================================
# CONFIGURACIÓN
# =========================================================

URL = (
    "https://www.rfaf.es/pnfg/NPcd/"
    "NFG_CmpJornada?cod_primaria=1000120"
)

ID_COMPETICION = "48466530"

GRUPOS = {
    "49641343": "Grupo 1",
    "48933162": "Grupo 2"
}

TIMEOUT_ACTAS = 30000


# =========================================================
# PAUSAS
# =========================================================

def pausa(minimo=2.5, maximo=4.5):
    segundos = random.uniform(minimo, maximo)
    time.sleep(segundos)


# =========================================================
# SELECCIÓN DE OPCIONES
# =========================================================

def seleccionar_opcion(page, selector, valor):
    """
    Selecciona una opción y comprueba que el selector
    realmente tenga el valor solicitado.
    """

    try:
        page.locator(selector).select_option(
            value=str(valor),
            timeout=15000
        )

    except PlaywrightTimeoutError:
        # Puede haberse iniciado una navegación.
        try:
            page.wait_for_load_state(
                "domcontentloaded",
                timeout=10000
            )
        except PlaywrightTimeoutError:
            pass

        # Comprobar si la selección llegó a realizarse.
        try:
            valor_actual = page.locator(selector).input_value()

            if valor_actual != str(valor):
                raise RuntimeError(
                    f"No se pudo seleccionar {valor} en {selector}"
                )

        except Exception as error:
            raise RuntimeError(
                f"Error seleccionando {valor} en {selector}: {error}"
            )

    page.wait_for_function(
        """datos => {
            const elemento = document.querySelector(datos.selector);

            return elemento &&
                   elemento.value === datos.valor;
        }""",
        arg={
            "selector": selector,
            "valor": str(valor)
        },
        timeout=15000
    )


# =========================================================
# IDENTIFICADORES DE ACTAS
# =========================================================

def obtener_ids_actas(page):
    """
    Extrae los CodActa presentes en la página.

    Elimina duplicados porque RFAF puede mostrar dos
    enlaces diferentes para un mismo partido.
    """

    return page.locator("a").evaluate_all(
        """elementos => {
            const identificadores = new Set();

            for (const enlace of elementos) {
                const href = enlace.href || "";

                const coincidencia = href.match(
                    /[?&](?:CodActa|cod_acta)=(\\d+)/i
                );

                if (coincidencia) {
                    identificadores.add(coincidencia[1]);
                }
            }

            return Array.from(identificadores).sort();
        }"""
    )


def obtener_actas(page):
    """
    Devuelve las actas únicas con sus URL.
    """

    enlaces = page.locator("a").evaluate_all(
        """elementos => elementos.map(enlace => ({
            href: enlace.href,
            texto: enlace.innerText.trim()
        }))"""
    )

    actas_unicas = {}

    for enlace in enlaces:

        coincidencia = re.search(
            r"[?&](?:CodActa|cod_acta)=(\d+)",
            enlace["href"],
            re.IGNORECASE
        )

        if not coincidencia:
            continue

        id_acta = coincidencia.group(1)

        if id_acta not in actas_unicas:
            actas_unicas[id_acta] = {
                "id": id_acta,
                "href": enlace["href"],
                "texto": enlace["texto"]
            }

    return list(actas_unicas.values())


# =========================================================
# ESPERAR A QUE RFAF ACTUALICE LOS PARTIDOS
# =========================================================

def esperar_actas_actualizadas(
    page,
    ids_anteriores,
    numero_jornada
):
    """
    No se limita a esperar unos segundos.

    Espera hasta que:
      1. La jornada seleccionada sea la solicitada.
      2. Existan identificadores de actas.
      3. Los identificadores sean diferentes de los anteriores.

    Si no se produce el cambio, genera un error.
    """

    ids_anteriores = sorted(set(ids_anteriores))

    print("Esperando actualización real de los partidos...")

    page.wait_for_function(
        """datos => {

            const selector = document.querySelector("#jornada");

            if (!selector) {
                return false;
            }

            if (selector.value !== datos.jornada) {
                return false;
            }

            const identificadores = new Set();

            const enlaces = document.querySelectorAll("a");

            for (const enlace of enlaces) {

                const href = enlace.href || "";

                const coincidencia = href.match(
                    /[?&](?:CodActa|cod_acta)=(\\d+)/i
                );

                if (coincidencia) {
                    identificadores.add(coincidencia[1]);
                }
            }

            const actuales = Array.from(identificadores).sort();

            if (actuales.length === 0) {
                return false;
            }

            return JSON.stringify(actuales) !==
                   JSON.stringify(datos.anteriores);
        }""",
        arg={
            "jornada": str(numero_jornada),
            "anteriores": ids_anteriores
        },
        timeout=TIMEOUT_ACTAS,
        polling=500
    )

    # Pequeña pausa después de confirmar el cambio.
    pausa(1.5, 2.5)

    ids_actuales = obtener_ids_actas(page)

    if not ids_actuales:
        raise RuntimeError(
            f"La jornada {numero_jornada} no contiene actas."
        )

    if ids_actuales == ids_anteriores:
        raise RuntimeError(
            f"RFAF mantiene las mismas actas en la jornada "
            f"{numero_jornada}."
        )

    return ids_actuales


# =========================================================
# LECTURA DE SELECTORES
# =========================================================

def obtener_opciones(page, selector):

    for intento in range(4):

        try:
            return page.locator(selector).evaluate_all(
                """elementos => elementos.flatMap(elemento =>
                    Array.from(elemento.options).map(o => ({
                        texto: o.textContent.trim(),
                        valor: o.value
                    }))
                )"""
            )

        except Exception as error:

            mensaje = str(error).lower()

            if (
                "execution context was destroyed" in mensaje
                or "detached" in mensaje
                or "navigation" in mensaje
            ):

                print(
                    "Esperando a que termine la actualización..."
                )

                pausa(2, 4)
                continue

            raise

    raise RuntimeError(
        f"No se pudo leer el selector {selector}"
    )


# =========================================================
# COMPETICIÓN
# =========================================================

def cargar_competicion(page):

    print("\nSeleccionando División de Honor Sénior...")

    seleccionar_opcion(
        page,
        "select#competicion",
        ID_COMPETICION
    )

    page.wait_for_function(
        """() => {
            const grupo = document.querySelector("#grupo");

            if (!grupo) return false;

            const valores = Array.from(grupo.options)
                .map(o => o.value);

            return valores.includes("49641343")
                && valores.includes("48933162");
        }""",
        timeout=30000
    )

    print("Competición cargada.")
    print("Grupos disponibles correctamente.")


# =========================================================
# GRUPOS
# =========================================================

def cargar_grupo(page, id_grupo, nombre_grupo):

    print(f"\nCargando {nombre_grupo}...")

    # Guardamos las actas que había antes de cambiar de grupo.
    ids_anteriores = obtener_ids_actas(page)

    seleccionar_opcion(
        page,
        "select#grupo",
        id_grupo
    )

    page.wait_for_function(
        """idGrupo => {

            const grupo = document.querySelector("#grupo");
            const jornada = document.querySelector("#jornada");

            if (!grupo || !jornada) return false;

            if (grupo.value !== idGrupo) return false;

            return Array.from(jornada.options)
                .some(o => o.value !== "" && o.value !== "0");
        }""",
        arg=str(id_grupo),
        timeout=30000
    )

    pausa(2, 3)

    jornadas = obtener_opciones(
        page,
        "select#jornada"
    )

    jornadas = [
        jornada
        for jornada in jornadas
        if jornada["valor"] not in ("", "0")
    ]

    print(
        f"{nombre_grupo}: "
        f"{len(jornadas)} jornadas encontradas."
    )

    return jornadas, ids_anteriores


# =========================================================
# JORNADAS
# =========================================================

def procesar_jornada(
    page,
    numero,
    ids_anteriores
):

    seleccionar_opcion(
        page,
        "select#jornada",
        numero
    )

    # Esperar al cambio real de los CodActa.
    ids_actuales = esperar_actas_actualizadas(
        page,
        ids_anteriores,
        numero
    )

    actas = obtener_actas(page)

    # Comprobar que los IDs coinciden con los enlaces extraídos.
    ids_extraidos = sorted(
        acta["id"] for acta in actas
    )

    if ids_extraidos != ids_actuales:
        raise RuntimeError(
            "Los identificadores de los enlaces no coinciden "
            "con los identificadores detectados en la página."
        )

    return actas, ids_actuales


# =========================================================
# PROGRAMA PRINCIPAL
# =========================================================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True
    )

    context = browser.new_context(
        viewport={
            "width": 1366,
            "height": 768
        },
        locale="es-ES"
    )

    page = context.new_page()

    page.set_default_timeout(20000)

    page.on(
        "pageerror",
        lambda error: print(
            "\nERROR JAVASCRIPT:", error
        )
    )

    total_general = 0
    errores_generales = 0

    try:

        print("Cargando RFAF...")

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        pausa(4, 6)

        cargar_competicion(page)

        print("\n" + "=" * 70)
        print("DIVISIÓN DE HONOR SÉNIOR")
        print("=" * 70)

        # Recorrer los dos grupos.
        for id_grupo, nombre_grupo in GRUPOS.items():

            print("\n" + "=" * 70)
            print(nombre_grupo, "|", id_grupo)
            print("=" * 70)

            jornadas, ids_anteriores = cargar_grupo(
                page,
                id_grupo,
                nombre_grupo
            )

            total_grupo = 0
            jornadas_con_actas = 0
            actas_vistas = set()
            errores_grupo = 0

            for jornada in jornadas:

                numero = jornada["valor"]
                fecha = jornada["texto"]

                try:

                    print(
                        f"\nConsultando jornada {numero}..."
                    )

                    actas, ids_actuales = procesar_jornada(
                        page,
                        numero,
                        ids_anteriores
                    )

                    cantidad = len(actas)

                    # Comprobar si hay actas repetidas
                    # respecto a jornadas anteriores.
                    repetidas = (
                        set(ids_actuales) & actas_vistas
                    )

                    if repetidas:
                        print(
                            "AVISO: actas que ya aparecieron "
                            "en jornadas anteriores:",
                            ", ".join(sorted(repetidas))
                        )

                    actas_vistas.update(ids_actuales)

                    total_grupo += cantidad
                    total_general += cantidad

                    if cantidad > 0:
                        jornadas_con_actas += 1

                    print(
                        f"Jornada {numero:>2} | "
                        f"{fecha:<22} | "
                        f"Actas únicas: {cantidad}"
                    )

                    for acta in actas:

                        print(
                            f"    Acta {acta['id']} | "
                            f"{acta['href']}"
                        )

                    # La siguiente jornada deberá compararse
                    # con los identificadores de esta.
                    ids_anteriores = ids_actuales

                except Exception as error:

                    errores_grupo += 1
                    errores_generales += 1

                    print(
                        f"\nERROR en jornada {numero}: "
                        f"{type(error).__name__}: {error}"
                    )

                    print(
                        "No se contabilizan actas de esta jornada "
                        "porque no se ha podido verificar "
                        "la actualización."
                    )

                    pausa(5, 8)

                    # No actualizamos ids_anteriores:
                    # conservamos la última jornada validada.

            print("\nRESUMEN", nombre_grupo)
            print("-" * 50)
            print("Jornadas disponibles:", len(jornadas))
            print("Jornadas con actas:", jornadas_con_actas)
            print("Total de actas procesadas:", total_grupo)
            print("Actas únicas en el grupo:", len(actas_vistas))
            print("Errores:", errores_grupo)

            pausa(5, 9)

        print("\n" + "=" * 70)
        print("RESUMEN GENERAL")
        print("=" * 70)

        print("Competición: División de Honor Sénior")
        print("Grupos analizados:", len(GRUPOS))
        print("Total de actas procesadas:", total_general)
        print("Errores:", errores_generales)

    except Exception as error:

        print("\nERROR GENERAL:")
        print(type(error).__name__, str(error))

    finally:

        browser.close()

        print("\nDIAGNÓSTICO FINALIZADO")