"""Sincronizador de 3.ª Federación RFAF (Grupos 9 y 10) con actas extendidas (asistentes, goles y alineaciones)."""
import sys

import config
from guarda_division_honor import (
    SUPABASE_URL,
    SUPABASE_KEY,
    ESPERA_ENTRE_ACTAS,
    NUMERO_GRUPOS_ESPERADO,
    limpiar,
    normalizar,
    normalizar_equipo,
    fecha_actual_espana,
    obtener_opciones,
    seleccionar_competicion as _seleccionar_competicion_base,
    cargar_grupo as _cargar_grupo_base,
    descubrir_grupos as _descubrir_grupos_base,
    descubrir_jornadas as _descubrir_jornadas_base,
    obtener_fecha,
    validar_tarjetas_individuales,
    validar,
    extraer_jornada as _extraer_jornada_base,
    construir_registro as _construir_registro_base,
    valores_coinciden,
    guardar_partido as _guardar_partido_base,
    construir_registros_tarjetas as _construir_registros_tarjetas_base,
    guardar_tarjetas_individuales as _guardar_tarjetas_individuales_base,
    sincronizar_arbitros_desde_partidos,
    mostrar_partido,
    ejecutar_sincronizacion,
)

COMPETICION = config.COMPETICION_TERCERA
COMPETICION_ID = config.COD_COMPETICION_TERCERA
TEMPORADA_ID = config.COD_TEMPORADA
GRUPOS_ESPERADOS = config.GRUPOS_ESPERADOS_TERCERA


def seleccionar_competicion(page):
    return _seleccionar_competicion_base(page, competicion_id=COMPETICION_ID)


def cargar_grupo(page, grupo_id):
    return _cargar_grupo_base(
        page, grupo_id, competicion_id=COMPETICION_ID
    )


def descubrir_grupos(page):
    return _descubrir_grupos_base(
        page,
        competicion_id=COMPETICION_ID,
        grupos_esperados=GRUPOS_ESPERADOS,
        nombre_competicion=COMPETICION,
    )


def descubrir_jornadas(page, grupo):
    return _descubrir_jornadas_base(
        page, grupo, competicion_id=COMPETICION_ID
    )


def extraer_jornada(page, grupo, jornada):
    return _extraer_jornada_base(
        page,
        grupo,
        jornada,
        competicion_id=COMPETICION_ID,
        omitir_sin_marcador=True,
    )


def construir_registro(datos):
    return _construir_registro_base(
        datos,
        competicion=COMPETICION,
        incluir_jugadores_tarjetas=True,
    )


def guardar_partido(supabase, datos):
    return _guardar_partido_base(
        supabase,
        datos,
        competicion=COMPETICION,
        incluir_jugadores_tarjetas=True,
    )


def construir_registros_tarjetas(datos):
    return _construir_registros_tarjetas_base(
        datos, competicion=COMPETICION
    )


def guardar_tarjetas_individuales(supabase, datos):
    return _guardar_tarjetas_individuales_base(
        supabase, datos, competicion=COMPETICION
    )


def main():
    ejecutar_sincronizacion(
        competicion=COMPETICION,
        competicion_id=COMPETICION_ID,
        grupos_esperados=GRUPOS_ESPERADOS,
        incluir_jugadores_tarjetas=True,
        omitir_sin_marcador=True,
        titulo="RFAF - 3.ª FEDERACIÓN",
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("\nERROR GENERAL:")
        print(error)
        sys.exit(1)
