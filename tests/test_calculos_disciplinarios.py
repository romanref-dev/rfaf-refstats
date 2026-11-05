import pytest

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
