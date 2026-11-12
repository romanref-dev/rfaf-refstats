
import os
import re
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

JORNADAS = [1, 2, 3]

COMPETICION = "División Honor Sénior"
GRUPO = "Grupo 1"

COMPETICION_ID = "48466530"
GRUPO_ID = "49641343"


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
        raise RuntimeError("Marcador no válido.")

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

    suma = sum(tarjetas[c] for c in campos)

    if suma != tarjetas.get("total"):
        raise RuntimeError(
            "El total de tarjetas no coincide."
        )

    return True


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
            "No se pudo obtener la fecha de la jornada."
        )

    dia, mes, anio = coincidencia.groups()

    return f"{anio}-{mes}-{dia}"


# ============================================================
# EXTRAER UNA JORNADA
# ============================================================

def extraer_jornada(page, jornada):

    print("\n" + "=" * 90)
    print(f"EXTRAYENDO JORNADA {jornada}")
    print("=" * 90)

    rfaf.cargar_jornada(page, jornada)

    fecha = obtener_fecha(page)

    actas = page.evaluate(rfaf.JS_ACTAS)

    actas = list(dict.fromkeys(
        str(acta) for acta in actas
    ))

    equipos_calendario = page.evaluate(
        rfaf.JS_CALENDARIO
    )

    print("Fecha:", fecha)
    print("Partidos encontrados:", len(actas))

    resultados = []

    for numero, acta_id in enumerate(actas, start=1):

        print(
            f"\n[{numero}/{len(actas)}] "
            f"Procesando acta {acta_id}..."
        )

        try:

            rfaf.cargar_jornada(page, jornada)

            datos = rfaf.procesar_acta(
                page,
                jornada,
                acta_id,
                equipos_calendario
            )

            datos["fecha"] = fecha
            datos["acta_id"] = str(acta_id)
            datos["jornada"] = jornada

            validar(datos)

            resultados.append(datos)

            print(
                "OK |",
                datos["local"],
                "-",
                datos["visitante"],
                "|",
                datos["resultado"]
            )

        except Exception as error:

            print(
                "NO GUARDABLE | ACTA",
                acta_id,
                "|",
                str(error)
            )

    return resultados


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

    registro = {
        "id": f"rfaf_{acta_id}",
        "acta_id": acta_id,

        "fecha": datos["fecha"],
        "categoria": COMPETICION,
        "competicion": COMPETICION,

        "grupo": GRUPO,
        "id_grupo": GRUPO_ID,

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

    return registro


# ============================================================
# COMPARAR VALORES
# ============================================================

def valores_coinciden(campo, esperado, obtenido):

    # Supabase devuelve la columna jornada como texto.
    if campo == "jornada":
        return str(esperado) == str(obtenido)

    return esperado == obtenido


# ============================================================
# GUARDAR Y VERIFICAR UN PARTIDO
# ============================================================

def guardar_partido(supabase, datos):

    registro = construir_registro(datos)

    acta_id = registro["acta_id"]

    print(f"Guardando acta {acta_id}...")

    supabase.table("partidos").upsert(
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
        "jornada"
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

        print("\nERROR DE VERIFICACIÓN:")

        for error in errores:
            print("-", error)

        raise RuntimeError(
            f"El acta {acta_id} no coincide con los datos enviados."
        )

    return fila


# ============================================================
# MOSTRAR RESULTADO
# ============================================================

def mostrar_partido(datos):

    tarjetas = datos["tarjetas"]

    print(
        f"J{datos['jornada']} | "
        f"ACTA {datos['acta_id']} | "
        f"{datos['local']} - {datos['visitante']} | "
        f"{datos['resultado']} | "
        f"{datos['arbitro']} | "
        f"AM {tarjetas['amarillas_local']}-"
        f"{tarjetas['amarillas_visitante']} | "
        f"RO {tarjetas['rojas_local']}-"
        f"{tarjetas['rojas_visitante']} | "
        f"GUARDADO Y VERIFICADO"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not SUPABASE_KEY:
        raise RuntimeError(
            "Falta SUPABASE_KEY en las variables de entorno."
        )

    print("\nRFAF - GUARDADO DE JORNADAS")
    print("=" * 90)

    print("Competición:", COMPETICION)
    print("Grupo:", GRUPO)
    print("Jornadas:", JORNADAS)

    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

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

        for jornada in JORNADAS:

            try:

                partidos = extraer_jornada(
                    page,
                    jornada
                )

                total_extraidos += len(partidos)

                print(
                    f"\nGUARDANDO JORNADA {jornada}"
                )

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
                    f"ERROR EN JORNADA {jornada}:",
                    str(error)
                )

        navegador.close()

    print("\n" + "=" * 90)
    print("RESUMEN FINAL")
    print("=" * 90)

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


if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print("\nERROR GENERAL:")
        print(error)
