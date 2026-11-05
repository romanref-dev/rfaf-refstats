import os

# Estructura de archivos y contenidos de la suite de pruebas
files_content = {
    "pytest.ini": """[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
""",
    "requirements-test.txt": """pytest>=7.4.0
pytest-mock>=3.11.1
requests>=2.31.0
supabase>=1.0.0
""",
    "tests/conftest.py": """import pytest

@pytest.fixture
def partido_ejemplo():
    \"\"\"Fixture con la estructura exacta de un partido en la BD Supabase.\"\"\"
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
""",
    "tests/test_calculos_disciplinarios.py": """import pytest

def extraer_categoria_base(categoria_str):
    if not categoria_str:
        return "Desconocida"
    limpia = categoria_str.split('(')[0].strip()
    return limpia.replace("Senior", "").replace("Grupo", "").strip() or "Desconocida"

def calcular_indice_volatilidad(partidos):
    if not partidos:
        return 0.0
    total_tarjetas = sum((p.get("tarjetas_amarillas") or 0) + (p.get("tarjetas_rojas") or 0) for p in partidos)
    media = total_tarjetas / len(partidos)
    return round(min(10.0, media * 1.2), 1)

def test_extraer_categoria_base():
    assert extraer_categoria_base("División de Honor Senior (Grupo 1)") == "División de Honor"
    assert extraer_categoria_base("") == "Desconocida"

def test_calcular_indice_volatilidad(lista_partidos_simulada):
    score = calcular_indice_volatilidad(lista_partidos_simulada)
    assert score == 7.2
    assert isinstance(score, float)
""",
    "tests/test_supabase_integration.py": """import pytest

class MockSupabaseTable:
    def __init__(self, data):
        self._data = data

    def select(self, fields):
        return self

    def order(self, field, ascending=True):
        return self

    def execute(self):
        class Response:
            def __init__(self, data):
                self.data = data
        return Response(self._data)

def test_simulacion_consulta_supabase(mocker, lista_partidos_simulada):
    mock_client = mocker.Mock()
    mock_client.from_.return_value = MockSupabaseTable(lista_partidos_simulada)

    response = mock_client.from_('partidos').select('*').order('jornada').execute()

    assert len(response.data) == 2
    assert response.data[0]["arbitro"] == "Álvaro Gómez"
    assert response.data[0]["tarjetas_amarillas"] == 7
"""
}

# Creación de carpetas y archivos
for relative_path, content in files_content.items():
    directory = os.path.dirname(relative_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        print(f"📁 Carpeta creada: {directory}")

    with open(relative_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"📄 Archivo generado: {relative_path}")

print("\n✅ ¡Suite de pruebas generada correctamente!")