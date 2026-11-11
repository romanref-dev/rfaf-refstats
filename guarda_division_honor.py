
import os
import re
import sys
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright
from supabase import create_client

import testacta as rfaf


# ============================================================
# CONFIGURACION
# ============================================================

SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    "https://ijczoeyfgnngocstxgfb.supabase.co"
)

SUPABASE_KEY = os.getenv("SUPABASE_KEY")

COMPETICION = "División Honor Sénior"
COMPETICION_ID = rfaf.COMPETICION_ID

ESPERA_ENTRE_ACTAS = 1

# Se espera encontrar exactamente dos grupos.
NUMERO_GRUPOS_ESPERADO = 2


# ============================================================
# UTILIDADES
# ============================================================

def limpiar(texto):
    return re.sub(r"\s+", " ", texto or "").strip()


def obtener_opciones(page, selector):

    return page.locator(
        selector
    ).evaluate(
        """
        select => Array.from(select.options)
            .map(o => ({
                value: o.value,
                texto: o.textContent.trim()
            }))
            .filter(o => o.value !== "")
        """
    )


def seleccionar_competicion(page):

    page.goto(
        rfaf.URL_BASE,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.locator(
        "select#competicion"
    ).wait_for(
        state="attached",
        timeout=30000
    )

    rfaf.seleccionar_opcion(
        page,
        "select#competicion",
        COMPETICION_ID,
        "Competición"
    )


def cargar_grupo(page, grupo_id):

    seleccionar_competicion(page)

    rfaf.seleccionar_opcion(
        page,
        "select#grupo",
        grupo_id,
        "Grupo"
    )


# ============================================================
# DESCUBRIR LOS DOS GRUPOS
# ============================================================

def descubrir_grupos(page):

    print("\nDESCUBRIENDO GRUPOS")
    print("=" * 90)

    seleccionar_competicion(page)

    grupos = obtener_opciones(
        page,
        "select#grupo"
    )

    if len(grupos) != NUMERO_GRUPOS_ESPERADO:

        raise RuntimeError(
            "Se esperaban exactamente "
            f"{NUMERO_GRUPOS_ESPERADO} grupos, "
            f"pero se han encontrado {len(grupos)}: {grupos}"
        )

    for grupo in grupos:
        print(
            f"Grupo detectado: {grupo['texto']} "
            f"| ID: {grupo['value']}"
        )

    return grupos


# ============================================================
# DESCUBRIR JORNADAS DE UN GRUPO
# ============================================================

def descubrir_jornadas(page, grupo):

    print(
        f"\nDESCUBRIENDO JORNADAS: {grupo['texto']}"
    )

    cargar_grupo(
        page,
        grupo["value"]
    )

    opciones = obtener_opciones(
        page,
        "select#jornada"
    )

    jornadas = {}

    for opcion in opciones:

        valor = str(opcion["value"]).strip()
        texto = str(opcion["texto"]).strip()

        coincidencia = re.search(
            r"\d+",
            valor
        )

        if not coincidencia:
            coincidencia = re.search(
                r"\d+",
                texto
            )

        if not coincidencia:
            continue

        jornada = int(coincidencia.group())

        jornadas[jornada] = {
            "numero": jornada,
            "valor": valor,
            "texto": texto
        }

    resultado = sorted(
        jornadas.values(),
        key=lambda x: x["numero"]
    )

    print(
        f"Jornadas encontradas: {len(resultado)}"
    )

    for jornada in resultado:
        print(
            f"  Jornada {jornada['numero']} "
            f"| {jornada['texto']}"
        )

    return resultado


# ============================================================
# OBTENER FECHA DE JORNADA
# ============================================================

def obtener_fecha(page):

    texto = page.locator(
        "select#jornada option:checked"
    ).inner_text()

    coincidencia = re.search(
        r"(\d{2})-(\d{2})-(\d{4})",
        texto
    )

    if not coincidencia:

        raise RuntimeError(
            "No se pudo obtener la fecha de la jornada: "
            + texto
        )

    dia, mes, anio = coincidencia.groups()

    return f"{anio}-{mes}-{dia}"


# ============================================================
# VALIDAR DATOS
# ============================================================

def validar(datos):

    obligatorios = [
        datos.get("local"),
        datos.get("visitante"),
        datos.get("resultado"),
        datos.get("arbitro"),
        datos.get("delegacion"),
        datos.get("fecha")
    ]

    if not all(obligatorios):

        raise RuntimeError(
            "Faltan datos obligatorios del partido."
        )

    if not re.fullmatch(
        r"\d+-\d+",
        str(datos["resultado"])
    ):

        raise RuntimeError(
            "Marcador no válido."
        )

    tarjetas = datos.get("tarjetas", {})

    campos = [
        "amarillas_local",
        "amarillas_visitante",
        "rojas_local",
        "rojas_visitante"
    ]

    for campo in campos:

        valor = tarjetas.get(campo)

        if not isinstance(valor, int) or valor < 0:

            raise RuntimeError(
                f"Tarjetas sin verificar: {campo}"
            )

    if tarjetas.get("sin_asignar") != 0:

        raise RuntimeError(
            "Hay tarjetas sin asignar."
        )

    suma = sum(
        tarjetas[campo]
        for campo in campos
    )

    if suma != tarjetas.get("total"):

        raise RuntimeError(
            "El total de tarjetas no coincide."
        )

    return True


# ============================================================
# EXTRAER UNA JORNADA
# ============================================================

def extraer_jornada(
    page,
    grupo,
    jornada
):

    numero_jornada = jornada["numero"]

    print("\n" + "=" * 100)
    print(
        f"{grupo['texto'].upper()} | "
        f"JORNADA {numero_jornada}"
    )
    print("=" * 100)

    # Actualizamos el grupo utilizado por testacta.py.
    rfaf.GRUPO_ID = grupo["value"]

    rfaf.cargar_jornada(
        page,
        numero_jornada
    )

    fecha = obtener_fecha(page)

    actas = page.evaluate(
        rfaf.JS_ACTAS
    )

    actas = list(dict.fromkeys(
        str(acta) for acta in actas
    ))

    equipos_calendario = page.evaluate(
        rfaf.JS_CALENDARIO
    )

    print("Fecha:", fecha)
    print("Actas encontradas:", len(actas))

    if not actas:

        print(
            "Jornada sin actas. Se omite."
        )

        return [], 0

    resultados = []
    errores = 0

    for numero, acta_id in enumerate(
        actas,
        start=1
    ):

        print(
            f"\n[{numero}/{len(actas)}] "
            f"ACTA {acta_id}"
        )

        try:

            # Volvemos a cargar el calendario antes de cada acta.
            rfaf.GRUPO_ID = grupo["value"]

            rfaf.cargar_jornada(
                page,
                numero_jornada
            )

            datos = rfaf.procesar_acta(
                page,
                numero_jornada,
                acta_id,
                equipos_calendario
            )

            datos["fecha"] = fecha
            datos["acta_id"] = str(acta_id)
            datos["jornada"] = numero_jornada

            validar(datos)

            datos["grupo"] = grupo["texto"]
            datos["id_grupo"] = grupo["value"]

            resultados.append(datos)

            tarjetas = datos["tarjetas"]

            print(
                "VALIDADO | "
                f"{datos['local']} - "
                f"{datos['visitante']} | "
                f"{datos['resultado']} | "
                f"Árbitro: {datos['arbitro']} | "
                f"AM {tarjetas['amarillas_local']}-"
                f"{tarjetas['amarillas_visitante']} | "
                f"RO {tarjetas['rojas_local']}-"
                f"{tarjetas['rojas_visitante']}"
            )

        except Exception as error:

            errores += 1

            print(
                f"NO GUARDABLE | ACTA {acta_id} | "
                f"{error}"
            )

        time.sleep(ESPERA_ENTRE_ACTAS)

    return resultados, errores


# ============================================================
# CONSTRUIR REGISTRO SUPABASE
# ============================================================

def construir_registro(datos):

    validar(datos)

    acta_id = str(datos["acta_id"])

    goles_local, goles_visitante = map(
        int,
        datos["resultado"].split("-")
    )

    tarjetas = datos["tarjetas"]

    return {
        "id": f"rfaf_{acta_id}",
        "acta_id": acta_id,

        "fecha": datos["fecha"],
        "categoria": COMPETICION,
        "competicion": COMPETICION,

        "grupo": datos["grupo"],
        "id_grupo": datos["id_grupo"],

        "jornada": datos["jornada"],
        "id_jornada": datos["jornada"],

        "equipo_local": datos["local"],
        "equipo_visitante": datos["visitante"],

        "goles_local": goles_local,
        "goles_visitante": goles_visitante,
        "resultado": datos["resultado"],

        "arbitro": datos["arbitro"],
        "arbitro_nombre": datos["arbitro"],

        "delegacion": datos["delegacion"],
        "delegacion_arbitro": datos["delegacion"],

        "tarjetas_amarillas_local":
            tarjetas["amarillas_local"],

        "tarjetas_amarillas_visitante":
            tarjetas["amarillas_visitante"],

        "tarjetas_rojas_local":
            tarjetas["rojas_local"],

        "tarjetas_rojas_visitante":
            tarjetas["rojas_visitante"],

        "estado": "Finalizado",

        "updated_at": datetime.now(
            timezone.utc
        ).isoformat()
    }


# ============================================================
# COMPARAR VALORES
# ============================================================

def valores_coinciden(
    campo,
    esperado,
    obtenido
):

    if campo in ("jornada", "id_jornada"):

        return str(esperado) == str(obtenido)

    return esperado == obtenido


# ============================================================
# GUARDAR Y VERIFICAR PARTIDO
# ============================================================

def guardar_partido(
    supabase,
    datos
):

    registro = construir_registro(datos)

    acta_id = registro["acta_id"]

    print(
        f"Guardando acta {acta_id}..."
    )

    supabase.table(
        "partidos"
    ).upsert(
        registro,
        on_conflict="acta_id"
    ).execute()

    respuesta = (
        supabase
        .table("partidos")
        .select("*")
        .eq("acta_id", acta_id)
        .execute()
    )

    filas = respuesta.data or []

    if len(filas) != 1:

        raise RuntimeError(
            "No se ha encontrado exactamente una fila "
            f"para el acta {acta_id}."
        )

    fila = filas[0]

    campos = [
        "equipo_local",
        "equipo_visitante",
        "goles_local",
        "goles_visitante",
        "resultado",
        "arbitro",
        "arbitro_nombre",
        "delegacion",
        "delegacion_arbitro",
        "tarjetas_amarillas_local",
        "tarjetas_amarillas_visitante",
        "tarjetas_rojas_local",
        "tarjetas_rojas_visitante",
        "fecha",
        "jornada",
        "grupo",
        "id_grupo",
        "competicion",
        "estado"
    ]

    errores = []

    for campo in campos:

        esperado = registro.get(campo)
        obtenido = fila.get(campo)

        if not valores_coinciden(
            campo,
            esperado,
            obtenido
        ):

            errores.append(
                f"{campo}: esperado {esperado!r}, "
                f"obtenido {obtenido!r}"
            )

    if errores:

        print(
            "\nERROR DE VERIFICACIÓN:"
        )

        for error in errores:
            print("-", error)

        raise RuntimeError(
            f"El acta {acta_id} no coincide "
            "con los datos enviados."
        )

    return fila


# ============================================================
# MOSTRAR PARTIDO
# ============================================================

def mostrar_partido(datos):

    tarjetas = datos["tarjetas"]

    print(
        f"{datos['grupo']} | "
        f"J{datos['jornada']} | "
        f"ACTA {datos['acta_id']} | "
        f"{datos['local']} - "
        f"{datos['visitante']} | "
        f"{datos['resultado']} | "
        f"{datos['arbitro']} | "
        f"AM {tarjetas['amarillas_local']}-"
        f"{tarjetas['amarillas_visitante']} | "
        f"RO {tarjetas['rojas_local']}-"
        f"{tarjetas['rojas_visitante']} | "
        "GUARDADO Y VERIFICADO"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not SUPABASE_KEY:

        raise RuntimeError(
            "Falta SUPABASE_KEY en las variables de entorno."
        )

    print("\nRFAF - DIVISIÓN HONOR SÉNIOR")
    print("=" * 100)

    print("Competición:", COMPETICION)
    print("ID competición:", COMPETICION_ID)

    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

    total_jornadas = 0
    total_actas = 0
    total_extraidos = 0
    total_guardados = 0
    total_errores = 0

    with sync_playwright() as playwright:

        navegador = playwright.chromium.launch(
            headless=True
        )

        page = navegador.new_page(
            viewport={
                "width": 1366,
                "height": 900
            }
        )

        try:

            grupos = descubrir_grupos(page)

            for grupo in grupos:

                print("\n\n")
                print("#" * 100)
                print(
                    "PROCESANDO",
                    grupo["texto"].upper(),
                    "| ID:",
                    grupo["value"]
                )
                print("#" * 100)

                jornadas = descubrir_jornadas(
                    page,
                    grupo
                )

                for jornada in jornadas:

                    total_jornadas += 1

                    try:

                        partidos, errores = extraer_jornada(
                            page,
                            grupo,
                            jornada
                        )

                        total_actas += len(partidos) + errores
                        total_extraidos += len(partidos)
                        total_errores += errores

                        for datos in partidos:

                            try:

                                guardar_partido(
                                    supabase,
                                    datos
                                )

                                total_guardados += 1

                                mostrar_partido(datos)

                            except Exception as error:

                                total_errores += 1

                                print(
                                    "ERROR AL GUARDAR | ACTA",
                                    datos["acta_id"],
                                    "|",
                                    str(error)
                                )

                    except Exception as error:

                        total_errores += 1

                        print(
                            f"ERROR EN {grupo['texto']} "
                            f"JORNADA {jornada['numero']}: "
                            f"{error}"
                        )

        finally:

            navegador.close()

    # ========================================================
    # RESUMEN FINAL
    # ========================================================

    print("\n" + "=" * 100)
    print("RESUMEN FINAL")
    print("=" * 100)

    print("Competición:", COMPETICION)
    print("Grupos detectados:", NUMERO_GRUPOS_ESPERADO)
    print("Jornadas examinadas:", total_jornadas)
    print("Actas procesadas:", total_actas)

    print(
        "Partidos extraídos y validados:",
        total_extraidos
    )

    print(
        "Partidos guardados y verificados:",
        total_guardados
    )

    print(
        "Errores:",
        total_errores
    )

    print("\nProceso terminado.")

    if total_errores > 0:

        print(
            "\nATENCIÓN: La ejecución ha terminado "
            "con errores."
        )

        sys.exit(1)


if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print("\nERROR GENERAL:")
        print(error)

        sys.exit(1)
