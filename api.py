import os
import psycopg as psycopg2
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="RFAF RefStats API",
    description="API REST de Inteligencia Arbitral para el fútbol andaluz",
    version="1.0.0"
)

# Permitir peticiones desde el Dashboard Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a la base de datos PostgreSQL (Supabase / Local)
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rfaf_db")

def get_db():
    return psycopg2.connect(DB_URL, row_factory=dict_row)

@app.get("/")
def home():
    return {
        "status": "online",
        "system": "RFAF RefStats API",
        "version": "1.0.0",
        "endpoints": ["/api/arbitros", "/api/informe-tactico/{arbitro_id}"]
    }

@app.get("/api/arbitros")
def get_arbitros():
    """Retorna la lista de árbitros con sus métricas acumuladas de las últimas 3 temporadas"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        query = """
            SELECT 
                a.id, 
                a.nombre, 
                COALESCE(d.nombre, 'Andalucía') as delegacion, 
                COUNT(p.id) as total_partidos,
                COALESCE(SUM(p.amarillas_local + p.amarillas_visitante), 0) as total_amarillas,
                COALESCE(SUM(p.rojas_local + p.rojas_visitante), 0) as total_rojas,
                ROUND(CAST(AVG(COALESCE(p.amarillas_local, 0) + COALESCE(p.amarillas_visitante, 0)) AS numeric), 2) as promedio_amarillas
            FROM arbitros a
            LEFT JOIN delegaciones d ON a.delegacion_id = d.id
            LEFT JOIN partidos p ON a.id = p.arbitro_id
            GROUP BY a.id, d.nombre
            ORDER BY total_partidos DESC;
        """
        
        cur.execute(query)
        arbitros = cur.fetchall()
        conn.close()
        return arbitros

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al conectar a la base de datos: {str(e)}")

@app.get("/api/informe-tactico/{arbitro_id}")
def get_informe_tactico(arbitro_id: int):
    """Genera un informe táctico pre-partido con el perfil de un colegiado concreto"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT a.nombre, COALESCE(d.nombre, 'Andalucía') as delegacion, p.*
            FROM arbitros a
            LEFT JOIN delegaciones d ON a.delegacion_id = d.id
            JOIN partidos p ON a.id = p.arbitro_id
            WHERE a.id = %s
        """, (arbitro_id,))
        
        partidos = cur.fetchall()
        conn.close()

        if not partidos:
            raise HTTPException(status_code=404, detail="Árbitro no encontrado o sin partidos registrados")

        total_partidos = len(partidos)
        total_amarillas = sum((p['amarillas_local'] or 0) + (p['amarillas_visitante'] or 0) for p in partidos)
        total_rojas = sum((p['rojas_local'] or 0) + (p['rojas_visitante'] or 0) for p in partidos)
        
        promedio_tarjetas = round(total_amarillas / total_partidos, 2) if total_partidos > 0 else 0
        nivel_severidad = "ALTO" if promedio_tarjetas >= 5.5 else ("MEDIO" if promedio_tarjetas >= 4.0 else "BAJO")

        return {
            "arbitro_id": arbitro_id,
            "nombre": partidos[0]['nombre'],
            "delegacion": partidos[0]['delegacion'],
            "partidos_analizados": total_partidos,
            "total_amarillas": total_amarillas,
            "total_rojas": total_rojas,
            "promedio_amarillas": promedio_tarjetas,
            "nivel_severidad": nivel_severidad,
            "recomendacion_tactica": (
                "Atención a la primera falta táctica en medio campo. Evitar protestas reiteradas al colegiado."
                if nivel_severidad == "ALTO" else
                "Permite juego fluido. Mantener intensidad en los duelos sin cometer faltas a destiempo."
            )
        }

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar informe: {str(e)}")