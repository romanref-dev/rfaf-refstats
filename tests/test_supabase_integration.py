import pytest

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
