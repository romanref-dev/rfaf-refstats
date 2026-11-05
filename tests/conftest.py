import pytest

@pytest.fixture
def partido_ejemplo():
    """Fixture con la estructura exacta de un partido en la BD Supabase."""
    return {
        "id": 101,
        "jornada": 5,
        "categoria": "División de Honor Senior (Grupo 1)",
        "equipo_local": "CD Utrera",
        "equipo_visitante": "Castilleja CF",
        "goles_local": 2,
        "goles_visitante": 1,
        "arbitro": "Álvaro Gómez",
        "tarjetas_amarillas": 7,
        "tarjetas_rojas": 1,
        "jugadores_tarjetas": [
            {"nombre": "Juan Pérez", "equipo": "CD Utrera", "tipo": "amarilla"},
            {"nombre": "Carlos Ruiz", "equipo": "Castilleja CF", "tipo": "roja"}
        ]
    }

@pytest.fixture
def lista_partidos_simulada(partido_ejemplo):
    return [
        partido_ejemplo,
        {
            "id": 102,
            "jornada": 5,
            "categoria": "División de Honor Senior (Grupo 1)",
            "equipo_local": "UP Viso",
            "equipo_visitante": "PD Rociera",
            "goles_local": 0,
            "goles_visitante": 0,
            "arbitro": "Álvaro Gómez",
            "tarjetas_amarillas": 4,
            "tarjetas_rojas": 0,
            "jugadores_tarjetas": []
        }
    ]
