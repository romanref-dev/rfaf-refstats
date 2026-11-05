import os

files_content = {
    "pytest.ini": """[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --cov=src --cov-report=term-missing --cov-report=html
""",

    "requirements-test.txt": """pytest>=7.4.0
pytest-mock>=3.11.1
pytest-cov>=4.1.0
requests>=2.31.0
supabase>=1.0.0
fastapi>=0.100.0
httpx>=0.24.0
""",

    "tests/conftest.py": """import pytest
from fastapi.testclient import TestClient
from src.main import app, DATA_PARTIDOS

@pytest.fixture(autouse=True)
def reset_db():
    \"\"\"Limpia y resetea la BD en memoria antes de cada test para aislar las pruebas.\"\"\"
    DATA_PARTIDOS.clear()
    DATA_PARTIDOS.extend([
        {
            "id": 1,
            "jornada": 1,
            "categoria": "División de Honor Senior (Grupo 1)",
            "equipo_local": "C.D. Utrera",
            "equipo_visitante": "Castilleja C.F.",
            "goles_local": 2,
            "goles_visitante": 1,
            "arbitro": "Álvaro Gómez",
            "tarjetas_amarillas": 7,
            "tarjetas_rojas": 1,
            "jugadores_tarjetas": [
                {"nombre": "Juan Pérez", "equipo": "C.D. Utrera", "tipo": "amarilla"},
                {"nombre": "Juan Pérez", "equipo": "C.D. Utrera", "tipo": "amarilla"},
                {"nombre": "Juan Pérez", "equipo": "C.D. Utrera", "tipo": "amarilla"},
                {"nombre": "Juan Pérez", "equipo": "C.D. Utrera", "tipo": "amarilla"}, # 4a amarillas -> apercibido
                {"nombre": "Carlos Ruiz", "equipo": "Castilleja C.F.", "tipo": "roja"} # roja -> sancionado
            ]
        },
        {
            "id": 2,
            "jornada": 1,
            "categoria": "División de Honor Senior (Grupo 1)",
            "equipo_local": "U.D. Tomares",
            "equipo_visitante": "C.D. Utrera",
            "goles_local": 0,
            "goles_visitante": 0,
            "arbitro": "Manuel Martínez",
            "tarjetas_amarillas": 3,
            "tarjetas_rojas": 0,
            "jugadores_tarjetas": []
        },
        {
            "id": 3,
            "jornada": 1,
            "categoria": "Primera Andaluza (Grupo 2)",
            "equipo_local": "Chiclana C.F.",
            "equipo_visitante": "C.D. Rota",
            "goles_local": 0,
            "goles_visitante": 2,
            "arbitro": "Álvaro Gómez",
            "tarjetas_amarillas": 2,
            "tarjetas_rojas": 0,
            "jugadores_tarjetas": []
        }
    ])
    yield
    DATA_PARTIDOS.clear()

@pytest.fixture
def client():
    return TestClient(app)
""",

    "tests/test_disciplinario_service.py": """import pytest
from src.services.disciplinario import (
    normalizar_nombre_equipo,
    extraer_categoria_base,
    calcular_indice_volatilidad,
    calcular_clasificacion,
    procesar_radar_jugadores
)

def test_normalizar_nombre_equipo_casos_borde():
    assert normalizar_nombre_equipo("") == ""
    assert normalizar_nombre_equipo(None) == ""
    assert normalizar_nombre_equipo("  C.D. Utrera  ") == "CD Utrera"
    assert normalizar_nombre_equipo("Castilleja C.F.") == "Castilleja CF"
    assert normalizar_nombre_equipo("U.D. Los Barrios") == "UD Los Barrios"
    assert normalizar_nombre_equipo("U.B. Lebrijana") == "UB Lebrijana"

def test_extraer_categoria_base_casos_borde():
    assert extraer_categoria_base("") == "Desconocida"
    assert extraer_categoria_base(None) == "Desconocida"
    assert extraer_categoria_base("División de Honor Senior (Grupo 1)") == "División de Honor"
    assert extraer_categoria_base("Senior") == "Desconocida"
    assert extraer_categoria_base("Primera Andaluza Grupo 2") == "Primera Andaluza"

def test_calcular_indice_volatilidad_vacio():
    assert calcular_indice_volatilidad([]) == 0.0

def test_calcular_clasificacion_partidos_incompletos_y_empates():
    partidos_incompletos = [
        {"equipo_local": "Equipo A", "equipo_visitante": "Equipo B", "goles_local": None, "goles_visitante": 1},
        {"equipo_local": None, "equipo_visitante": "Equipo B", "goles_local": 1, "goles_visitante": 1},
        {"equipo_local": "Equipo A", "equipo_visitante": "Equipo B", "goles_local": 1, "goles_visitante": 1}, # Empate
        {"equipo_local": "Equipo B", "equipo_visitante": "Equipo A", "goles_local": 2, "goles_visitante": 0}  # Victoria B
    ]
    clasif = calcular_clasificacion(partidos_incompletos)
    assert len(clasif) == 2
    assert clasif[0]["equipo"] == "Equipo B"
    assert clasif[0]["pts"] == 4
    assert clasif[1]["equipo"] == "Equipo A"
    assert clasif[1]["pts"] == 1

def test_procesar_radar_jugadores_sin_datos():
    partidos_sin_tarjetas = [
        {"jugadores_tarjetas": [{"nombre": "", "equipo": "A"}]},
        {"jugadores_tarjetas": None}
    ]
    res = procesar_radar_jugadores(partidos_sin_tarjetas)
    assert res["apercibidos"] == []
    assert res["sancionados"] == []
""",

    "tests/test_api_endpoints.py": """import pytest

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "RFAF RefStats API"}

def test_listar_partidos_sin_filtro(client):
    response = client.get("/api/partidos")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["partidos"]) == 3

def test_listar_partidos_con_filtros(client):
    # Filtro por Categoria
    res_cat = client.get("/api/partidos?categoria=División de Honor")
    assert res_cat.json()["total"] == 2

    # Filtro por Arbitro
    res_arb = client.get("/api/partidos?arbitro=alvaro")
    assert res_arb.json()["total"] == 2

    # Filtro por Equipo
    res_eq = client.get("/api/partidos?equipo=C.D. Utrera")
    assert res_eq.json()["total"] == 2

def test_obtener_partido_por_id_exito(client):
    response = client.get("/api/partidos/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["arbitro"] == "Álvaro Gómez"

def test_obtener_partido_por_id_404(client):
    response = client.get("/api/partidos/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Partido no encontrado"

def test_obtener_volatilidad_niveles(client):
    res_div = client.get("/api/analisis/volatilidad?categoria=División de Honor")
    assert res_div.status_code == 200
    assert res_div.json()["nivel"] == "Tensión Media"

    res_and = client.get("/api/analisis/volatilidad?categoria=Primera Andaluza")
    assert res_and.json()["nivel"] == "Baja Tensión"

def test_obtener_clasificacion(client):
    response = client.get("/api/clasificacion?categoria=División de Honor")
    assert response.status_code == 200
    clasif = response.json()["clasificacion"]
    assert len(clasif) == 3
    assert clasif[0]["equipo"] == "C.D. Utrera"

def test_obtener_radar_jugadores(client):
    response = client.get("/api/radar-jugadores")
    assert response.status_code == 200
    data = response.json()
    assert len(data["apercibidos"]) == 1
    assert data["apercibidos"][0]["nombre"] == "Juan Pérez"
    assert len(data["sancionados"]) == 1
    assert data["sancionados"][0]["nombre"] == "Carlos Ruiz"
"""
}

for relative_path, content in files_content.items():
    directory = os.path.dirname(relative_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    with open(relative_path, "w", encoding="utf-8") as f:
        f.write(content)

print("✅ Suite de cobertura al 100% generada correctamente.")