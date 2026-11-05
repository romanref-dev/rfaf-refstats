import requests
from bs4 import BeautifulSoup
import json

# Configuración de tu proyecto Supabase
SUPABASE_URL = "https://ijczoeyfgnngocstxgfb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlqY3pvZXlmZ25uZ29jc3R4Z2ZiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMxMTM0MjIsImV4cCI6MjEwODY4OTQyMn0.ygZNfFCaXQy4EK8h8uXj1in676gxSc6oxI1-4JNtU74"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates" # Evita duplicar si el acta ya existe
}

def extraer_datos_acta(url_acta):
    """
    Función para parsear el HTML de un acta de la RFAF.
    Ajusta los selectores según la estructura de la web de la RFAF.
    """
    response = requests.get(url_acta)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Ejemplo de extracción de datos del acta:
    # 1. Nombre del Árbitro
    arbitro_elem = soup.find('span', id='lblArbitro') or soup.find('td', class_='arbitro')
    nombre_arbitro = arbitro_elem.text.strip() if arbitro_elem else "Desconocido"

    # 2. Delegación / Comité del Árbitro (Dato oficial RFAF)
    delegacion_elem = soup.find('span', id='lblDelegacion') or soup.find('td', class_='delegacion')
    delegacion_real = delegacion_elem.text.strip() if delegacion_elem else "Sevilla"  # Valor por defecto si no figura

    # 3. Equipos, Resultado y Tarjetas
    partido_data = {
        "acta_id": "ACTA-" + url_acta.split('/')[-1],
        "fecha": "2026-10-28",
        "categoria": "División de Honor",
        "jornada": 1,
        "equipo_local": "Equipo Local",
        "equipo_visitante": "Equipo Visitante",
        "goles_local": 2,
        "goles_visitante": 1,
        "arbitro": nombre_arbitro,
        "delegacion": delegacion_real,  # <-- DELEGACIÓN EXTRAÍDA
        "tarjetas_amarillas": 4,
        "tarjetas_rojas": 0
    }
    
    return partido_data

def subir_a_supabase(partido_data):
    """
    Envía el registro con la delegación correcta directamente a Supabase.
    """
    endpoint = f"{SUPABASE_URL}/rest/v1/partidos"
    res = requests.post(endpoint, headers=HEADERS, data=json.dumps(partido_data))
    
    if res.status_code in [200, 201]:
        print(f"✅ Partido {partido_data['acta_id']} guardado con Árbitro: {partido_data['arbitro']} ({partido_data['delegacion']})")
    else:
        print(f"❌ Error al guardar partido: {res.status_code} - {res.text}")

if __name__ == "__main__":
    # Ejemplo de actualización cargando las URL de las actas
    urls_actas = [
        "https://www.rfaf.es/acta/12345",
        "https://www.rfaf.es/acta/12346"
    ]
    
    for url in urls_actas:
        partido = extraer_datos_acta(url)
        subir_a_supabase(partido)