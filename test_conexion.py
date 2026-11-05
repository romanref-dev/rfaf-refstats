import urllib.request
import urllib.error
import json

SUPABASE_URL = "https://ijczoeyfgnngocstxgfb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlqY3pvZXlmZ25uZ29jc3R4Z2ZiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMxMTM0MjIsImV4cCI6MjEwODY4OTQyMn0.ygZNfFCaXQy4EK8h8uXj1in676gxSc6oxI1-4JNtU74"

endpoint = f"{SUPABASE_URL}/rest/v1/partidos?select=*"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Accept": "application/json"
}

try:
    req = urllib.request.Request(endpoint, headers=headers)
    with urllib.request.urlopen(req) as response:
        print("¡CONEXIÓN EXITOSA! Estado:", response.status)
        data = json.loads(response.read().decode('utf-8'))
        print(f"Total partidos recuperados: {len(data)}")
        if data:
            print("Muestra del primer registro:", data[0])
except urllib.error.HTTPError as e:
    print(f"Error HTTP {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Error en la petición: {e}")