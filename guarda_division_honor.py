import os
import re
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright
from supabase import create_client

import config
import testacta as rfaf


# ============================================================
# CONFIGURACION
# ============================================================

SUPABASE_URL = config.SUPABASE_URL
SUPABASE_KEY = config.SUPABASE_KEY

COMPETICION = config.COMPETICION_DH
COMPETICION_ID = config.COD_COMPETICION_DH

ESPERA_ENTRE_ACTAS = config.ESPERA_ENTRE_ACTAS
NUMERO_GRUPOS_ESPERADO = 2
GRUPOS_ESPERADOS = config.GRUPOS_ESPERADOS_DH


# ============================================================
# UTILIDADES
# ============================================================

def limpiar(texto):
    return re.sub(r"\s+,", ",", re.sub(r"\s+", " ", texto or "")).strip()


def normalizar(texto):
    return limpiar(texto).casefold()


def normalizar_equipo(texto):
    return rfaf.normalizar_equipo(texto)


def fecha_actual_espana():
    return datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()


def obtener_opciones(page, selector):
    opciones = page.locator(selector).evaluate(
        """
        select => Array.from(select.options).map(o => ({
            value: o.value.trim(),
            texto: o.textContent.trim()
        }))
        """
    )

    opciones_validas = []

    for opcion in opciones:
        valor = str(opcion["value"]).strip()
        texto = limpiar(opcion["texto"])
        texto_normalizado = texto.lower()

        if not valor or valor == "0":
            continue

        if "seleccione" in texto_normalizado:
            continue

        if texto_normalizado in ("--", "-", "seleccionar"):
            continue

        opciones_validas.append({
            "value": valor,
            "texto": texto
        })

    return opciones_validas


def seleccionar_competicion(page, competicion_id=None):
    comp_id = competicion_id or COMPETICION_ID

    page.goto(
        rfaf.URL_BASE,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.locator("select#competicion").wait_for(
        state="attached",
        timeout=30000
    )

    rfaf.seleccionar_opcion(
        page,
        "select#competicion",
        comp_id,
        "Competición"
    )


def cargar_grupo(page, grupo_id, competicion_id=None):
    seleccionar_competicion(page, competicion_id=competicion_id)

    rfaf.seleccionar_opcion(
        page,
        "select#grupo",
        grupo_id,
        "Grupo"
    )


# ============================================================
# DESCUBRIR GRUPOS
# ============================================================

def descubrir_grupos(
    page,
    competicion_id=None,
    grupos_esperados=None,
    nombre_competicion=None,
    numero_grupos_esperado=None
):
    print("\nDESCUBRIENDO GRUPOS")
    print("=" * 90)

    seleccionar_competicion(page, competicion_id=competicion_id)

    grupos = obtener_opciones(page, "select#grupo")

    if not grupos:
        raise RuntimeError(
            f"No se ha detectado ningún grupo para la competición {nombre_competicion or competicion_id}."
        )

    if numero_grupos_esperado is not None and len(grupos) != numero_grupos_esperado:
        raise RuntimeError(
            "Se esperaban exactamente "
            f"{numero_grupos_esperado} grupos reales, "
            f"pero se han encontrado {len(grupos)}: {grupos}"
        )

    if grupos_esperados:
        ids_detectados = {str(grupo["value"]) for grupo in grupos}
        if ids_detectados != set(grupos_esperados):
            etiqueta = nombre_competicion or COMPETICION
            raise RuntimeError(
                "Los grupos detectados no coinciden con los IDs configurados "
                f"para {etiqueta}. Esperados: {sorted(grupos_esperados)}; "
                f"detectados: {sorted(ids_detectados)}. Se cancela para evitar "
                "guardar datos en una competición o grupo incorrecto."
            )

    for grupo in grupos:
        print(
            f"Grupo detectado: {grupo['texto']} "
            f"| ID: {grupo['value']}"
        )

    return grupos


# ============================================================
# DESCUBRIR JORNADAS
# ============================================================

def descubrir_jornadas(page, grupo, competicion_id=None):
    print(f"\nDESCUBRIENDO JORNADAS: {grupo['texto']}")

    cargar_grupo(page, grupo["value"], competicion_id=competicion_id)

    opciones = obtener_opciones(page, "select#jornada")

    jornadas = {}

    for opcion in opciones:
        valor = str(opcion["value"]).strip()
        texto = str(opcion["texto"]).strip()

        coincidencia = re.fullmatch(r"\s*(\d+)\s*", valor)

        if not coincidencia:
            coincidencia = re.match(r"\s*(\d+)", texto)

        if not coincidencia:
            continue

        numero = int(coincidencia.group(1))

        if numero <= 0:
            continue

        jornadas[numero] = {
            "numero": numero,
            "valor": valor,
            "texto": texto
        }

    resultado = sorted(
        jornadas.values(),
        key=lambda x: x["numero"]
    )

    print(f"Jornadas encontradas: {len(resultado)}")

    for jornada in resultado:
        print(
            f"  Jornada {jornada['numero']} "
            f"| {jornada['texto']}"
        )

    return resultado


# ============================================================
# OBTENER FECHA DE JORNADA
# ============================================================

def obtener_fecha(page, jornada):
    texto = limpiar(jornada.get("texto", ""))

    coincidencia = re.search(
        r"(\d{1,2})-(\d{1,2})-(\d{4})",
        texto
    )

    if not coincidencia:
        texto = page.locator("select#jornada").evaluate(
            """
            select => select.selectedOptions.length
                ? select.selectedOptions[0].textContent.trim()
                : ""
            """
        )

        coincidencia = re.search(
            r"(\d{1,2})-(\d{1,2})-(\d{4})",
            texto
        )

    if not coincidencia:
        raise RuntimeError(
            "No se pudo obtener la fecha de la jornada: " + texto
        )

    dia, mes, anio = coincidencia.groups()

    return f"{anio}-{int(mes):02d}-{int(dia):02d}"


# ============================================================
# VALIDAR TARJETAS INDIVIDUALES
# ============================================================

def validar_tarjetas_individuales(datos):
    tarjetas = datos.get("tarjetas", {})
    individuales = datos.get("tarjetas_individuales")

    if not isinstance(individuales, list):
        raise RuntimeError(
            "No se ha obtenido la lista de tarjetas individuales."
        )

    errores_individuales = datos.get("errores_individuales")

    if errores_individuales:
        raise RuntimeError(
            "La extracción individual contiene errores: "
            f"{errores_individuales}"
        )

    for numero, tarjeta in enumerate(individuales, start=1):
        if not isinstance(tarjeta, dict):
            raise RuntimeError(
                f"La tarjeta {numero} no tiene formato válido."
            )

        campos = ["tipo", "minuto", "jugador", "equipo"]

        for campo in campos:
            if not limpiar(str(tarjeta.get(campo) or "")):
                raise RuntimeError(
                    f"Tarjeta {numero}: falta el campo {campo}."
                )

        tipo = str(tarjeta["tipo"]).lower().strip()

        if tipo not in ("amarilla", "roja"):
            raise RuntimeError(
                f"Tarjeta {numero}: tipo desconocido: {tipo}"
            )

        if not re.fullmatch(
            r"\d+(?:\+\d+)?",
            str(tarjeta["minuto"]).strip()
        ):
            raise RuntimeError(
                f"Tarjeta {numero}: minuto no válido: "
                f"{tarjeta['minuto']}"
            )

    total_esperado = sum([
        tarjetas.get("amarillas_local", 0),
        tarjetas.get("amarillas_visitante", 0),
        tarjetas.get("rojas_local", 0),
        tarjetas.get("rojas_visitante", 0)
    ])

    if len(individuales) != total_esperado:
        raise RuntimeError(
            "No coinciden las tarjetas individuales con "
            f"el total del acta: {len(individuales)} "
            f"individuales frente a {total_esperado} totales."
        )

    equipos = {
        normalizar_equipo(datos["local"]): {
            "amarilla": tarjetas["amarillas_local"],
            "roja": tarjetas["rojas_local"]
        },
        normalizar_equipo(datos["visitante"]): {
            "amarilla": tarjetas["amarillas_visitante"],
            "roja": tarjetas["rojas_visitante"]
        }
    }

    recuento = {
        equipo: {
            "amarilla": 0,
            "roja": 0
        }
        for equipo in equipos
    }

    for tarjeta in individuales:
        equipo = normalizar_equipo(tarjeta["equipo"])

        if equipo not in recuento:
            raise RuntimeError(
                "Equipo de tarjeta no coincide con los equipos "
                f"del partido: {tarjeta['equipo']}"
            )

        tipo = str(tarjeta["tipo"]).lower().strip()
        recuento[equipo][tipo] += 1

    for equipo, esperados in equipos.items():
        obtenidos = recuento[equipo]

        for tipo in ("amarilla", "roja"):
            if obtenidos[tipo] != esperados[tipo]:
                raise RuntimeError(
                    f"Descuadre de {tipo} para {equipo}: "
                    f"esperadas {esperados[tipo]}, "
                    f"extraídas {obtenidos[tipo]}."
                )

    return True


# ============================================================
# VALIDAR DATOS DEL PARTIDO
# ============================================================

def validar(datos):
    if datos.get("estado") != "OK":
        raise RuntimeError(
            "El extractor no ha marcado el acta como OK: "
            f"{datos.get('estado')!r}"
        )

    errores_tarjetas = datos.get("errores_tarjetas") or []

    if errores_tarjetas:
        raise RuntimeError(
            "La extracción de totales de tarjetas contiene errores: "
            f"{errores_tarjetas}"
        )

    obligatorios = [
        datos.get("local"),
        datos.get("visitante"),
        datos.get("resultado"),
        datos.get("arbitro"),
        datos.get("fecha")
    ]

    if not all(obligatorios):
        raise RuntimeError(
            "Faltan datos obligatorios del partido "
            "(local, visitante, resultado, árbitro o fecha)."
        )

    if not re.fullmatch(r"\d+-\d+", str(datos["resultado"])):
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

        if type(valor) is not int or valor < 0:
            raise RuntimeError(f"Tarjetas sin verificar: {campo}")

    if (
        type(tarjetas.get("sin_asignar")) is not int
        or tarjetas.get("sin_asignar") != 0
    ):
        raise RuntimeError(
            "Hay tarjetas sin asignar o el contador no está verificado."
        )

    if (
        type(tarjetas.get("total")) is not int
        or tarjetas.get("total") < 0
    ):
        raise RuntimeError(
            "El total de imágenes de tarjetas no está verificado."
        )

    suma = sum(tarjetas[campo] for campo in campos)

    if suma != tarjetas.get("total"):
        raise RuntimeError("El total de tarjetas no coincide.")

    individuales = datos.get("tarjetas_individuales")

    if (
        not isinstance(individuales, list)
        or len(individuales) != tarjetas["total"]
    ):
        raise RuntimeError(
            "El número de tarjetas individuales no coincide con "
            "las imágenes detectadas en el acta."
        )

    validar_tarjetas_individuales(datos)

    return True


# ============================================================
# EXTRAER UNA JORNADA (SOPORTA DISPUTADAS Y CALENDARIO FUTURO)
# ============================================================

def construir_partido_pendiente_calendario(
    item,
    fecha_jornada,
    numero_jornada,
    grupo,
    competicion_id
):
    acta_id = item.get("acta_id")
    if not acta_id:
        acta_id = f"fut_{competicion_id}_{grupo['value']}_{numero_jornada}_{item.get('orden', 1)}"

    return {
        "es_pendiente": True,
        "acta_id": str(acta_id),
        "fecha": item.get("fecha") or fecha_jornada,
        "hora": item.get("hora"),
        "estadio": item.get("estadio"),
        "jornada": numero_jornada,
        "grupo": grupo["texto"],
        "id_grupo": grupo["value"],
        "local": limpiar(item.get("local") or ""),
        "visitante": limpiar(item.get("visitante") or ""),
        "resultado": None,
        "arbitro": limpiar(item.get("arbitro") or ""),
        "delegacion": None,
        "tarjetas": {
            "amarillas_local": 0,
            "amarillas_visitante": 0,
            "rojas_local": 0,
            "rojas_visitante": 0,
            "sin_asignar": 0,
            "total": 0,
        },
        "tarjetas_individuales": [],
        "detalles_acta": {
            "hora": item.get("hora"),
            "estadio": item.get("estadio"),
        },
        "estado": "PENDIENTE",
    }


def extraer_jornada(
    page,
    grupo,
    jornada,
    competicion_id=None,
    omitir_sin_marcador=True,
    guardar_jornadas_futuras=True
):
    comp_id = competicion_id or COMPETICION_ID
    numero_jornada = jornada["numero"]

    print("\n" + "=" * 100)
    print(
        f"{grupo['texto'].upper()} | "
        f"JORNADA {numero_jornada}"
    )
    print("=" * 100)

    fecha = obtener_fecha(page, jornada)
    hoy = fecha_actual_espana()

    print("Fecha de la jornada:", fecha)
    print("Fecha actual en España:", hoy)

    # --------------------------------------------------------
    # SI LA JORNADA ES FUTURA (fecha > hoy):
    # NO SE ABRE NINGUNA ACTA INDIVIDUAL.
    # Si guardar_jornadas_futuras=True, se lee solo la tabla
    # del calendario para registrar los encuentros como 'Pendiente'.
    # --------------------------------------------------------

    if fecha > hoy:
        print()
        print("JORNADA FUTURA / PENDIENTE (No se abren actas individuales)")

        if not guardar_jornadas_futuras:
            print(f"Jornada {numero_jornada} omitida correctamente.")
            return [], 0, 1

        rfaf.COMPETICION_ID = comp_id
        rfaf.GRUPO_ID = grupo["value"]

        try:
            rfaf.cargar_jornada(
                page,
                numero_jornada,
                competicion_id=comp_id,
                grupo_id=grupo["value"],
                permitir_sin_actas=True
            )
            partidos_cal = page.evaluate(rfaf.JS_PARTIDOS_CALENDARIO_COMPLETO) or []
        except Exception as exc_cal:
            print(f"No se pudo leer calendario futuro de jornada {numero_jornada}: {exc_cal}")
            return [], 0, 1

        pendientes = []
        for item in partidos_cal:
            if item.get("local") and item.get("visitante"):
                pendientes.append(
                    construir_partido_pendiente_calendario(
                        item,
                        fecha_jornada=fecha,
                        numero_jornada=numero_jornada,
                        grupo=grupo,
                        competicion_id=comp_id
                    )
                )

        print(f"Partidos futuros extraídos del calendario (sin abrir actas): {len(pendientes)}")
        return pendientes, 0, len(pendientes)

    # --------------------------------------------------------
    # SI NO ES FUTURA, CARGARLA UNA SOLA VEZ POR JORNADA
    # --------------------------------------------------------

    rfaf.COMPETICION_ID = comp_id
    rfaf.GRUPO_ID = grupo["value"]

    rfaf.cargar_jornada(
        page,
        numero_jornada,
        competicion_id=comp_id,
        grupo_id=grupo["value"],
        permitir_sin_actas=True
    )

    actas = page.evaluate(rfaf.JS_ACTAS)

    actas = list(dict.fromkeys(
        str(acta) for acta in actas
    ))

    equipos_calendario = page.evaluate(rfaf.JS_CALENDARIO)
    partidos_cal_lista = page.evaluate(rfaf.JS_PARTIDOS_CALENDARIO_COMPLETO) or []
    mapa_cal_por_acta = {
        str(it["acta_id"]): it
        for it in partidos_cal_lista
        if it.get("acta_id")
    }

    print("Actas encontradas:", len(actas))

    if not actas:
        if guardar_jornadas_futuras and partidos_cal_lista:
            pendientes = [
                construir_partido_pendiente_calendario(
                    item,
                    fecha_jornada=fecha,
                    numero_jornada=numero_jornada,
                    grupo=grupo,
                    competicion_id=comp_id
                )
                for item in partidos_cal_lista
                if item.get("local") and item.get("visitante")
            ]
            print(f"Jornada sin enlaces de acta pero con {len(pendientes)} partidos en calendario.")
            return pendientes, 0, len(pendientes)

        if omitir_sin_marcador:
            print("Jornada sin enlaces de acta. Se omite.")
            return [], 0, 0
        raise RuntimeError(
            "RFAF no ha cargado ningún enlace de acta "
            "en una jornada que no es futura."
        )

    # --------------------------------------------------------
    # PROCESAMIENTO DE CADA ACTA (SIN RECARGAR EL CALENDARIO)
    # --------------------------------------------------------

    resultados = []
    errores = 0
    omitidos = 0

    for numero, acta_id in enumerate(actas, start=1):
        print(
            f"\n[{numero}/{len(actas)}] "
            f"ACTA {acta_id}"
        )

        try:
            datos = rfaf.procesar_acta(
                page,
                numero_jornada,
                acta_id,
                equipos_calendario
            )

            if omitir_sin_marcador and not datos.get("resultado"):
                estado = str(datos.get("estado") or "")
                if estado.startswith("ERROR:"):
                    raise RuntimeError(estado)

                omitidos += 1
                if guardar_jornadas_futuras:
                    info_cal = mapa_cal_por_acta.get(str(acta_id), {})
                    pendiente = construir_partido_pendiente_calendario(
                        {
                            "acta_id": str(acta_id),
                            "local": datos.get("local") or info_cal.get("local"),
                            "visitante": datos.get("visitante") or info_cal.get("visitante"),
                            "fecha": info_cal.get("fecha") or fecha,
                            "hora": info_cal.get("hora"),
                            "estadio": info_cal.get("estadio"),
                            "arbitro": datos.get("arbitro") or info_cal.get("arbitro"),
                        },
                        fecha_jornada=fecha,
                        numero_jornada=numero_jornada,
                        grupo=grupo,
                        competicion_id=comp_id
                    )
                    pendiente["delegacion"] = datos.get("delegacion")
                    if pendiente["local"] and pendiente["visitante"]:
                        resultados.append(pendiente)
                        print(
                            "PARTIDO PENDIENTE / APLAZADO | "
                            f"ACTA {acta_id} | Registrado como 'Pendiente' sin tarjetas."
                        )
                else:
                    print(
                        "PARTIDO PENDIENTE / NO DISPUTADO | "
                        f"ACTA {acta_id} | Sin marcador. Se omite."
                    )
                time.sleep(ESPERA_ENTRE_ACTAS)
                continue

            datos["fecha"] = fecha
            datos["acta_id"] = str(acta_id)
            datos["jornada"] = numero_jornada
            datos["grupo"] = grupo["texto"]
            datos["id_grupo"] = grupo["value"]

            validar(datos)

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
                f"{tarjetas['rojas_visitante']} | "
                f"Tarjetas individuales: "
                f"{len(datos['tarjetas_individuales'])}"
            )

        except Exception as error:
            errores += 1

            print(
                f"NO GUARDABLE | ACTA {acta_id} | "
                f"{error}"
            )

        time.sleep(ESPERA_ENTRE_ACTAS)

    return resultados, errores, omitidos


# ============================================================
# CONSTRUIR REGISTRO SUPABASE: PARTIDO
# ============================================================

def construir_registro(
    datos,
    competicion=None,
    incluir_jugadores_tarjetas=True
):
    nombre_comp = competicion or COMPETICION
    acta_id = str(datos["acta_id"])

    if datos.get("es_pendiente"):
        arb = limpiar(datos.get("arbitro") or "")
        detalles = datos.get("detalles_acta") or {}
        meta_pendiente = []
        if any(detalles.values()):
            meta_pendiente.append({"tipo": "metadata_acta", "detalles_acta": detalles})
        return {
            "id": f"rfaf_{acta_id}",
            "acta_id": acta_id,
            "fecha": datos["fecha"],
            "categoria": nombre_comp,
            "competicion": nombre_comp,
            "grupo": datos["grupo"],
            "id_grupo": datos["id_grupo"],
            "jornada": datos["jornada"],
            "id_jornada": datos["jornada"],
            "equipo_local": datos["local"],
            "equipo_visitante": datos["visitante"],
            "goles_local": None,
            "goles_visitante": None,
            "resultado": None,
            "arbitro": arb,
            "arbitro_nombre": arb,
            "delegacion": datos.get("delegacion"),
            "delegacion_arbitro": datos.get("delegacion"),
            "tarjetas_amarillas": 0,
            "tarjetas_rojas": 0,
            "tarjetas_amarillas_local": 0,
            "tarjetas_amarillas_visitante": 0,
            "tarjetas_rojas_local": 0,
            "tarjetas_rojas_visitante": 0,
            "jugadores_tarjetas": meta_pendiente,
            "estado": "Pendiente",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    validar(datos)

    goles_local, goles_visitante = map(
        int,
        datos["resultado"].split("-")
    )

    tarjetas = datos["tarjetas"]

    total_amarillas = (
        tarjetas["amarillas_local"]
        + tarjetas["amarillas_visitante"]
    )

    total_rojas = (
        tarjetas["rojas_local"]
        + tarjetas["rojas_visitante"]
    )

    registro = {
        "id": f"rfaf_{acta_id}",
        "acta_id": acta_id,
        "fecha": datos["fecha"],
        "categoria": nombre_comp,
        "competicion": nombre_comp,
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
        "tarjetas_amarillas": total_amarillas,
        "tarjetas_rojas": total_rojas,
        "tarjetas_amarillas_local": tarjetas["amarillas_local"],
        "tarjetas_amarillas_visitante": tarjetas["amarillas_visitante"],
        "tarjetas_rojas_local": tarjetas["rojas_local"],
        "tarjetas_rojas_visitante": tarjetas["rojas_visitante"],
        "estado": "Finalizado",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    if incluir_jugadores_tarjetas:
        lista_json = list(datos.get("tarjetas_individuales") or [])
        detalles = datos.get("detalles_acta") or {}
        if any(detalles.values()):
            lista_json.append({"tipo": "metadata_acta", "detalles_acta": detalles})
        registro["jugadores_tarjetas"] = lista_json

    return registro


# ============================================================
# COMPARAR VALORES
# ============================================================

def valores_coinciden(campo, esperado, obtenido):
    if campo in ("jornada", "id_jornada"):
        return str(esperado) == str(obtenido)

    return esperado == obtenido


# ============================================================
# GUARDAR Y VERIFICAR PARTIDO
# ============================================================

def guardar_partido(
    supabase,
    datos,
    competicion=None,
    incluir_jugadores_tarjetas=True
):
    registro = construir_registro(
        datos,
        competicion=competicion,
        incluir_jugadores_tarjetas=incluir_jugadores_tarjetas
    )
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
        "tarjetas_amarillas",
        "tarjetas_rojas",
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

    if incluir_jugadores_tarjetas:
        campos.append("jugadores_tarjetas")

    errores = []

    for campo in campos:
        esperado = registro.get(campo)
        obtenido = fila.get(campo)

        if not valores_coinciden(campo, esperado, obtenido):
            errores.append(
                f"{campo}: esperado {esperado!r}, "
                f"obtenido {obtenido!r}"
            )

    if errores:
        print("\nERROR DE VERIFICACIÓN:")

        for error in errores:
            print("-", error)

        raise RuntimeError(
            f"El acta {acta_id} no coincide "
            "con los datos enviados."
        )

    return fila


# ============================================================
# CONSTRUIR REGISTROS DE TARJETAS INDIVIDUALES
# ============================================================

def construir_registros_tarjetas(datos, competicion=None):
    validar_tarjetas_individuales(datos)

    nombre_comp = competicion or COMPETICION
    acta_id = str(datos["acta_id"])
    partido_id = f"rfaf_{acta_id}"

    ahora = datetime.now(timezone.utc).isoformat()

    registros = []

    for numero, tarjeta in enumerate(
        datos["tarjetas_individuales"],
        start=1
    ):
        registros.append({
            "partido_id": partido_id,
            "acta_id": acta_id,
            "numero_tarjeta": numero,
            "competicion": nombre_comp,
            "grupo": datos["grupo"],
            "jornada": datos["jornada"],
            "fecha": datos["fecha"],
            "equipo": limpiar(tarjeta["equipo"]),
            "jugador": limpiar(tarjeta["jugador"]),
            "minuto": str(tarjeta["minuto"]).strip(),
            "tipo_persona": tarjeta.get("tipo_persona") or "jugador",
            "tipo_tarjeta": str(
                tarjeta["tipo"]
            ).lower().strip(),
            "updated_at": ahora
        })

    return registros


# ============================================================
# GUARDAR TARJETAS INDIVIDUALES
# ============================================================

def guardar_tarjetas_individuales(supabase, datos, competicion=None):
    acta_id = str(datos["acta_id"])

    registros = construir_registros_tarjetas(datos, competicion=competicion)

    print(
        f"Guardando {len(registros)} tarjetas "
        f"individuales del acta {acta_id}..."
    )

    if registros:
        supabase.table("actas_tarjetas").upsert(
            registros,
            on_conflict="acta_id,numero_tarjeta"
        ).execute()

    consulta = (
        supabase
        .table("actas_tarjetas")
        .delete()
        .eq("acta_id", acta_id)
    )

    if registros:
        consulta = consulta.gt(
            "numero_tarjeta",
            len(registros)
        )

    consulta.execute()

    respuesta = (
        supabase
        .table("actas_tarjetas")
        .select(
            "acta_id,numero_tarjeta,equipo,jugador,"
            "minuto,tipo_tarjeta"
        )
        .eq("acta_id", acta_id)
        .order("numero_tarjeta")
        .execute()
    )

    filas = respuesta.data or []

    if len(filas) != len(registros):
        raise RuntimeError(
            f"Acta {acta_id}: se esperaban "
            f"{len(registros)} tarjetas guardadas, "
            f"pero se encontraron {len(filas)}."
        )

    for esperado, obtenido in zip(registros, filas):
        campos = [
            "acta_id",
            "numero_tarjeta",
            "equipo",
            "jugador",
            "minuto",
            "tipo_tarjeta"
        ]

        for campo in campos:
            if str(esperado[campo]) != str(obtenido[campo]):
                raise RuntimeError(
                    f"Acta {acta_id}: discrepancia en "
                    f"tarjeta {esperado['numero_tarjeta']}, "
                    f"campo {campo}. "
                    f"Esperado: {esperado[campo]!r}; "
                    f"obtenido: {obtenido[campo]!r}"
                )

    return len(filas)


# ============================================================
# SINCRONIZAR TABLA DE ÁRBITROS DESDE PARTIDOS
# ============================================================

def sincronizar_arbitros_desde_partidos(supabase):
    """Recalcula y sincroniza las estadísticas acumuladas de la tabla `arbitros` a partir de `partidos`."""
    print("\nSincronizando tabla 'arbitros' a partir de 'partidos'...")

    respuesta_partidos = (
        supabase
        .table("partidos")
        .select("arbitro,arbitro_nombre,delegacion,delegacion_arbitro,tarjetas_amarillas,tarjetas_rojas,estado")
        .execute()
    )
    partidos_db = respuesta_partidos.data or []

    respuesta_arbitros = (
        supabase
        .table("arbitros")
        .select("id,nombre,delegacion")
        .execute()
    )
    arbitros_db = respuesta_arbitros.data or []

    id_por_nombre = {}
    delegacion_previa = {}
    max_id_numerico = 0

    for arb in arbitros_db:
        nombre_limpio = limpiar(arb.get("nombre") or "")
        if not nombre_limpio:
            continue
        arb_id = str(arb.get("id") or "").strip()
        id_por_nombre[nombre_limpio] = arb_id
        if arb.get("delegacion"):
            delegacion_previa[nombre_limpio] = limpiar(arb["delegacion"])
        if arb_id.isdigit():
            max_id_numerico = max(max_id_numerico, int(arb_id))

    agregados = {}

    for p in partidos_db:
        if str(p.get("estado") or "").strip().lower() == "pendiente":
            continue
        nombre = limpiar(p.get("arbitro") or p.get("arbitro_nombre") or "")
        if not nombre:
            continue

        deleg = limpiar(p.get("delegacion") or p.get("delegacion_arbitro") or "")
        am = int(p.get("tarjetas_amarillas") or 0)
        ro = int(p.get("tarjetas_rojas") or 0)

        if nombre not in agregados:
            agregados[nombre] = {
                "delegacion": deleg or delegacion_previa.get(nombre),
                "partidos": 0,
                "amarillas": 0,
                "rojas": 0,
            }

        item = agregados[nombre]
        if deleg and not item["delegacion"]:
            item["delegacion"] = deleg
        item["partidos"] += 1
        item["amarillas"] += am
        item["rojas"] += ro

    ahora = datetime.now(timezone.utc).isoformat()
    registros_arbitros = []

    for nombre in sorted(agregados.keys()):
        datos_arb = agregados[nombre]
        arb_id = id_por_nombre.get(nombre)
        if not arb_id:
            max_id_numerico += 1
            arb_id = str(max_id_numerico)

        partidos_dir = datos_arb["partidos"]
        tot_am = datos_arb["amarillas"]
        tot_ro = datos_arb["rojas"]

        registros_arbitros.append({
            "id": arb_id,
            "nombre": nombre,
            "delegacion": datos_arb["delegacion"],
            "partidos_dirigidos": partidos_dir,
            "total_amarillas": tot_am,
            "total_rojas": tot_ro,
            "promedio_amarillas": round(tot_am / partidos_dir, 2) if partidos_dir > 0 else 0.0,
            "promedio_rojas": round(tot_ro / partidos_dir, 2) if partidos_dir > 0 else 0.0,
            "updated_at": ahora,
        })

    if registros_arbitros:
        supabase.table("arbitros").upsert(
            registros_arbitros,
            on_conflict="id"
        ).execute()

    print(f"Tabla 'arbitros' sincronizada: {len(registros_arbitros)} árbitros actualizados.")
    return len(registros_arbitros)


# ============================================================
# MOSTRAR PARTIDO
# ============================================================

def mostrar_partido(datos):
    if datos.get("es_pendiente"):
        print(
            f"{datos['grupo']} | "
            f"J{datos['jornada']} | "
            f"ACTA {datos['acta_id']} | "
            f"{datos['local']} - "
            f"{datos['visitante']} | "
            f"PENDIENTE ({datos.get('fecha')} {datos.get('hora') or ''}) | "
            f"Árbitro: {datos.get('arbitro') or 'Por designar'} | "
            "GUARDADO EN CALENDARIO"
        )
        return

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


def sincronizar_competiciones_desde_partidos(supabase):
    """Asegura que todos los pares (competicion, grupo) de `partidos` existan en la tabla `competiciones`."""
    print("\nSincronizando tabla 'competiciones' a partir de 'partidos'...")
    resp_partidos = (
        supabase
        .table("partidos")
        .select("competicion,grupo")
        .execute()
    )
    pares_partidos = {
        (limpiar(p.get("competicion") or ""), limpiar(p.get("grupo") or ""))
        for p in (resp_partidos.data or [])
        if limpiar(p.get("competicion") or "") and limpiar(p.get("grupo") or "")
    }

    resp_comp = (
        supabase
        .table("competiciones")
        .select("id,nombre,grupo,temporada")
        .execute()
    )
    existentes = {
        (limpiar(c.get("nombre") or ""), limpiar(c.get("grupo") or ""))
        for c in (resp_comp.data or [])
    }

    nuevos = []
    for nombre, grupo in sorted(pares_partidos - existentes):
        nuevos.append({
            "nombre": nombre,
            "grupo": grupo,
            "temporada": "2026/2027",
        })

    if nuevos:
        supabase.table("competiciones").insert(nuevos).execute()

    print(
        f"Tabla 'competiciones' verificada: {len(existentes) + len(nuevos)} grupos activos "
        f"({len(nuevos)} nuevos añadidos)."
    )
    return len(nuevos)


# ============================================================
# EJECUCIÓN DE SINCRONIZACIÓN
# ============================================================

def ejecutar_sincronizacion(
    competicion=COMPETICION,
    competicion_id=COMPETICION_ID,
    grupos_esperados=None,
    incluir_jugadores_tarjetas=True,
    omitir_sin_marcador=True,
    guardar_jornadas_futuras=True,
    sincronizar_tablas_resumen=True,
    titulo="RFAF - DIVISIÓN HONOR SÉNIOR"
):
    supabase_url = os.getenv("SUPABASE_URL", SUPABASE_URL)
    supabase_key = os.getenv("SUPABASE_KEY", SUPABASE_KEY)

    if not supabase_key:
        raise RuntimeError(
            "Falta SUPABASE_KEY en las variables de entorno."
        )

    if not supabase_url:
        raise RuntimeError(
            "Falta SUPABASE_URL en las variables de entorno."
        )

    print(f"\n{titulo}")
    print("=" * 100)
    print("Competición:", competicion)
    print("ID competición:", competicion_id)
    print("Fecha actual en España:", fecha_actual_espana())
    if grupos_esperados:
        print("Grupos esperados:", ", ".join(sorted(grupos_esperados)))

    supabase = create_client(
        supabase_url,
        supabase_key
    )

    total_jornadas = 0
    total_actas = 0
    total_extraidos = 0
    total_guardados = 0
    total_tarjetas_guardadas = 0
    total_errores = 0
    total_omitidos = 0

    grupos = []

    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(headless=True)

        page = navegador.new_page(
            viewport={
                "width": 1366,
                "height": 900
            }
        )

        try:
            grupos = descubrir_grupos(
                page,
                competicion_id=competicion_id,
                grupos_esperados=grupos_esperados,
                nombre_competicion=competicion
            )

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
                    grupo,
                    competicion_id=competicion_id
                )

                for jornada in jornadas:
                    total_jornadas += 1

                    try:
                        partidos, errores, omitidos = extraer_jornada(
                            page,
                            grupo,
                            jornada,
                            competicion_id=competicion_id,
                            omitir_sin_marcador=omitir_sin_marcador,
                            guardar_jornadas_futuras=guardar_jornadas_futuras
                        )

                        total_actas += len(partidos) + errores
                        total_extraidos += len(partidos)
                        total_errores += errores
                        total_omitidos += omitidos

                        for datos in partidos:
                            try:
                                guardar_partido(
                                    supabase,
                                    datos,
                                    competicion=competicion,
                                    incluir_jugadores_tarjetas=incluir_jugadores_tarjetas
                                )

                                total_guardados += 1

                                mostrar_partido(datos)

                                if datos.get("es_pendiente"):
                                    continue

                                try:
                                    cantidad = guardar_tarjetas_individuales(
                                        supabase,
                                        datos,
                                        competicion=competicion
                                    )

                                    total_tarjetas_guardadas += cantidad

                                    print(
                                        "TARJETAS GUARDADAS Y "
                                        f"VERIFICADAS: {cantidad}"
                                    )
                                except Exception as error_tarjetas:
                                    print(
                                        "AVISO actas_tarjetas (ya persistido en partidos.jugadores_tarjetas) | ACTA",
                                        datos["acta_id"],
                                        "|",
                                        str(error_tarjetas)
                                    )

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

    if sincronizar_tablas_resumen:
        try:
            sincronizar_arbitros_desde_partidos(supabase)
        except Exception as error:
            print("AVISO: No se pudo sincronizar la tabla 'arbitros':", error)

        try:
            sincronizar_competiciones_desde_partidos(supabase)
        except Exception as error:
            print("AVISO: No se pudo sincronizar la tabla 'competiciones':", error)

    # RESUMEN FINAL

    print("\n" + "=" * 100)
    print("RESUMEN FINAL")
    print("=" * 100)

    print("Competición:", competicion)
    print("Grupos detectados:", len(grupos))
    print("Jornadas examinadas:", total_jornadas)
    print("Actas procesadas:", total_actas)
    print("Jornadas futuras / partidos pendientes omitidos:", total_omitidos)
    print("Partidos extraídos y validados:", total_extraidos)
    print("Partidos guardados y verificados:", total_guardados)

    print(
        "Tarjetas individuales guardadas y verificadas:",
        total_tarjetas_guardadas
    )

    print("Errores:", total_errores)
    print("\nProceso terminado.")

    if total_errores > 0:
        print(
            "\nATENCIÓN: La ejecución ha terminado "
            "con errores."
        )

        sys.exit(1)


def main():
    ejecutar_sincronizacion(
        competicion=COMPETICION,
        competicion_id=COMPETICION_ID,
        grupos_esperados=GRUPOS_ESPERADOS,
        incluir_jugadores_tarjetas=True,
        omitir_sin_marcador=True,
        titulo="RFAF - DIVISIÓN HONOR SÉNIOR"
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print("\nERROR GENERAL:")
        print(error)
        sys.exit(1)
