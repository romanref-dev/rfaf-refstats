import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ijczoeyfgnngocstxgfb.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlqY3pvZXlmZ25uZ29jc3R4Z2ZiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzExMzQyMiwiZXhwIjoyMTA4Njg5NDIyfQ.yPTDZIgGoRlpYUVHQSXTJ0INABGGZRxAP0leLfBDpYM")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    res = supabase.table("partidos").select("id", count="exact").execute()
    print(f"📊 Registros actuales en Supabase: {res.count}")
except Exception as e:
    print(f"❌ Error al consultar la base de datos: {e}")