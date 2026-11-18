import pytest

import testacta
import guarda_division_honor
import guarda_tercera_federacion


def extraer_categoria_base(categoria_str):
    if not categoria_str:
        return "Desconocida"
    limpia = categoria_str.split("(")[0].strip()
    return (
        limpia.replace("Senior", "").replace("Grupo", "").strip()
        or "Desconocida"
    )


def calcular_indice_volatilidad(partidos):
    if not partidos:
        return 0.0
    total_tarjetas = sum(
        (p.get("tarjetas_amarillas") or 0) + (p.get("tarjetas_rojas") or 0)
        for p in partidos
    )
    media = total_tarjetas / len(partidos)
    return round(min(10.0, media * 1.2), 1)


def test_extraer_categoria_base():
    assert (
        extraer_categoria_base("División de Honor Senior (Grupo 1)")
        == "División de Honor"
    )
    assert extraer_categoria_base("") == "Desconocida"


def test_calcular_indice_volatilidad(lista_partidos_simulada):
    score = calcular_indice_volatilidad(lista_partidos_simulada)
    assert score == 7.2
    assert isinstance(score, float)


def test_normalizar_equipo_elimina_marcador_y_acentos():
    assert testacta.normalizar_equipo("  La Palma C.F. 3 ") == "LA PALMA C.F."
    assert testacta.normalizar_equipo("Atlético Central 12") == "ATLETICO CENTRAL"


def test_validar_tarjetas_individuales_con_tiempo_anadido():
    datos = {
        "local": "CD Utrera",
        "visitante": "Castilleja CF",
        "tarjetas": {
            "amarillas_local": 1,
            "amarillas_visitante": 1,
            "rojas_local": 0,
            "rojas_visitante": 1,
            "sin_asignar": 0,
            "total": 3,
        },
        "tarjetas_individuales": [
            {
                "tipo": "amarilla",
                "minuto": "44",
                "jugador": "Juan Pérez",
                "equipo": "CD Utrera",
            },
            {
                "tipo": "amarilla",
                "minuto": "90+3",
                "jugador": "Pedro Gómez",
                "equipo": "Castilleja CF",
            },
            {
                "tipo": "roja",
                "minuto": "90+5",
                "jugador": "Carlos Ruiz",
                "equipo": "Castilleja CF",
            },
        ],
        "errores_individuales": [],
    }

    assert guarda_division_honor.validar_tarjetas_individuales(datos) is True
    assert guarda_tercera_federacion.validar_tarjetas_individuales(datos) is True


def test_limpiar_normaliza_espacios_antes_de_coma():
    assert (
        guarda_division_honor.limpiar("  MUNUERA SANCHEZ , ALVARO ")
        == "MUNUERA SANCHEZ, ALVARO"
    )


def test_construir_partido_pendiente_y_registro_futuro():
    pendiente = guarda_division_honor.construir_partido_pendiente_calendario(
        {
            "orden": 1,
            "acta_id": "2639475",
            "local": "UNION DEPORTIVA MELILLA",
            "visitante": "C.D. CHURRIANA DE LA VEGA C.F.",
            "fecha": "2026-11-22",
            "hora": "12:00",
            "estadio": "ALVAREZ CLARO",
            "arbitro": "GARCIA CALVO , ALVARO",
        },
        fecha_jornada="2026-11-22",
        numero_jornada=12,
        grupo={"texto": "Grupo 9", "value": "48710553"},
        competicion_id="48465908",
    )
    registro = guarda_division_honor.construir_registro(
        pendiente,
        competicion="3.ª Federación",
    )
    assert registro["estado"] == "Pendiente"
    assert registro["goles_local"] is None
    assert registro["goles_visitante"] is None
    assert registro["arbitro"] == "GARCIA CALVO, ALVARO"
    assert registro["jugadores_tarjetas"] == []


def test_catalogo_aficionados_completo():
    import config
    assert len(config.COMPETICIONES_AFICIONADOS) == 43


