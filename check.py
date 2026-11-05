from supabase import create_client

SUPABASE_URL = "https://ztjntikfytksixihylfs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp0am50aWtmeXRrc2l4aWh5bGZzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0MDI4ODE2NSwiZXhwIjoyMDU1ODY4MTY1fQ.vNnO_P09mJgP-OQGkU_1vT9j5dZ_X10aZ6-X6x8423g"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
URL_BASE = "https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Consulta de comprobación
res_total = supabase.table("partidos").select("id", count="exact").execute()
res_arbitros = supabase.table("partidos").select("id", count="exact").neq("arbitro", "No asignado").execute()

print(f"📊 Total partidos registrados en Supabase: {res_total.count}")
print(f"👤 Partidos con árbitro asignado: {res_arbitros.count}")