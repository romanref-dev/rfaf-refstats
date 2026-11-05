import json
from supabase import create_client

SUPABASE_URL = "https://oagytnryfefqytspetrt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9hZ3l0bnJ5ZmVmcXl0c3BldHJ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIyMzUwMzQsImV4cCI6MjA3NzgxMTAzNH0.HwOfsU64fIsKzL_L5qV0y5hY63GgPTrsW6557R8y3yE"

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = supabase.table("partidos").select("*").execute()
    
    with open("datos.json", "w", encoding="utf-8") as f:
        json.dump(response.data, f, ensure_ascii=False, indent=2)
    print("¡Archivo datos.json creado con éxito con los 18 partidos!")
except Exception as e:
    print(f"Error al conectar con Supabase: {e}")