import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="RFAF RefStats API",
    description="API para consultar métricas de tarjetas e inteligencia arbitral de la RFAF",
    version="1.0.0"
)

# Permitir solicitudes desde cualquier origen (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(
            status_code=500, 
            detail="DATABASE_URL no está configurada en las variables de entorno."
        )
    try:
        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al conectar a la base de datos: {str(e)}"
        )

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Bienvenido a RFAF RefStats API",
        "endpoints": ["/api/stats", "/api/kpis", "/api/arbitros/search"]
    }

@app.get("/api/kpis")
def obtener_kpis_globales():
    """Retorna los indicadores globales principales de la competición."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT 
                COUNT(DISTINCT arbitro) as total_arbitros,
                COUNT(id) as total_partidos,
                COALESCE(SUM(tarjetas_amarillas), 0) as total_amarillas,
                COALESCE(SUM(tarjetas_rojas), 0) as total_rojas,
                ROUND(AVG(tarjetas_amarillas)::numeric, 2) as media_amarillas_partido,
                ROUND(AVG(tarjetas_rojas)::numeric, 2) as media_rojas_partido
            FROM partidos
            WHERE arbitro IS NOT NULL AND arbitro != '';
        """
        cur.execute(query)
        kpis = cur.fetchone()
        cur.close()
        conn.close()
        return kpis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
def obtener_estadisticas_arbitros():
    """Retorna las estadísticas acumuladas y promedios agrupados por árbitro."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT 
                arbitro,
                COUNT(id) as partidos,
                SUM(tarjetas_amarillas) as total_amarillas,
                SUM(tarjetas_rojas) as total_rojas,
                ROUND(AVG(tarjetas_amarillas)::numeric, 2) as media_amarillas,
                ROUND(AVG(tarjetas_rojas)::numeric, 2) as media_rojas
            FROM partidos
            WHERE arbitro IS NOT NULL AND arbitro != ''
            GROUP BY arbitro
            ORDER BY partidos DESC, media_amarillas DESC;
        """
        cur.execute(query)
        stats = cur.fetchall()
        cur.close()
        conn.close()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/arbitros/search")
def buscar_arbitro(nombre: str = Query(..., description="Nombre parcial o completo del árbitro")):
    """Busca los partidos pitados por un árbitro concreto."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT 
                id,
                fecha,
                categoria,
                jornada,
                equipo_local,
                equipo_visitante,
                goles_local,
                goles_visitante,
                tarjetas_amarillas,
                tarjetas_rojas
            FROM partidos
            WHERE arbitro ILIKE %s
            ORDER BY fecha DESC;
        """
        cur.execute(query, (f"%{nombre}%",))
        partidos = cur.fetchall()
        cur.close()
        conn.close()
        return {
            "arbitro": nombre,
            "total_encontrados": len(partidos),
            "partidos": partidos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))