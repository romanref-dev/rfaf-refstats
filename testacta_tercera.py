import config
from testacta import (
    URL_BASE,
    URL_ACTA_BASE,
    JORNADAS,
    ESPERA,
    ESPERA_ENTRE_ACTAS,
    ESPERA_ESTABILIDAD,
    REPETICIONES_ESTABLES,
    INTENTOS_ESTABILIDAD,
    JS_ACTAS,
    JS_CALENDARIO,
    JS_MARCADOR,
    JS_ARBITRO,
    JS_TARJETAS,
    JS_TARJETAS_INDIVIDUALES,
    limpiar,
    normalizar,
    normalizar_equipo,
    seleccionar_opcion,
    esperar_actas_estables,
    cargar_jornada as _cargar_jornada_base,
    validar_totales_tarjetas,
    procesar_acta,
    mostrar_linea,
    mostrar_tarjetas_individuales,
    ejecutar_prueba,
)

COMPETICION_ID = config.COD_COMPETICION_TERCERA
GRUPO_ID = "48710553"


def cargar_jornada(page, jornada, competicion_id=None, grupo_id=None):
    return _cargar_jornada_base(
        page,
        jornada,
        competicion_id=competicion_id or COMPETICION_ID,
        grupo_id=grupo_id or GRUPO_ID,
    )


def main():
    ejecutar_prueba(
        competicion_id=COMPETICION_ID,
        grupo_id=GRUPO_ID,
        jornadas=JORNADAS,
        archivo_salida="resultados_tercera_j1_j2_j3.txt",
        titulo="RFAF - 3.ª FEDERACIÓN (JORNADAS 1, 2 Y 3)",
    )


if __name__ == "__main__":
    main()
