import socket
import sys
from supabase import create_client

SUPABASE_URL = "https://ijczoeyfgnngocstxgfb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlqY3pvZXlmZ25uZ29jc3R4Z2ZiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzExMzQyMiwiZXhwIjoyMTA4Njg5NDIyfQ.yPTDZIgGoRlpYUVHQSXTJ0INABGGZRxAP0leLfBDpYM"

def probar_red_y_supabase():
    host = SUPABASE_URL.replace("https://", "").replace("http://", "").split("/")[0]
    print(f"1. Verificando resolución DNS para: {host}...")
    
    try:
        ip = socket.gethostbyname(host)
        print(f"   ✅ DNS resuelto correctamente -> IP: {ip}")
    except socket.gaierror:
        print(f"   ❌ ERROR FATAL: No se puede resolver la IP de '{host}'.")
        sys.exit(1)

    print("\n2. Probando conexión con el cliente de Supabase...")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = supabase.table("partidos").select("id", count="exact").limit(1).execute()
        print(f"   ✅ Conexión a Supabase EXITOSA. Tabla 'partidos' accesible.")
        print(f"   📊 Registros actuales en la base de datos: {res.count}\n")
    except Exception as e:
        print(f"   ⚠️ Respuesta de Supabase: {e}")

if __name__ == "__main__":
    probar_red_y_supabase()