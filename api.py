from contextlib import contextmanager
import logging
import os
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("rfaf_api")

app = FastAPI(
    title="RFAF RefStats API",
    description="API para consultar métricas de tarjetas e inteligencia arbitral de la RFAF",
    version="1.1.0",
)

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
            detail="DATABASE_URL no está configurada en las variables de entorno.",
        )
    try:
        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    except Exception as exc:
        logger.error("Error al conectar a la base de datos: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="No se pudo establecer conexión con la base de datos.",
        ) from exc


@contextmanager
def get_db_cursor():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        yield cur
    finally:
        cur.close()
        conn.close()


@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Bienvenido a RFAF RefStats API",
        "endpoints": ["/api/stats", "/api/kpis", "/api/arbitros/search"],
    }


@app.get("/api/kpis")
def obtener_kpis_globales(
    categoria: Optional[str] = Query(None, description="Filtrar por categoría/competición"),
    grupo: Optional[str] = Query(None, description="Filtrar por grupo"),
):
    """Retorna los indicadores globales principales de la competición."""
    try:
        condiciones = ["arbitro IS NOT NULL", "arbitro != ''"]
        parametros = []

        if categoria:
            condiciones.append("categoria = %s")
            parametros.append(categoria)
        if grupo:
            condiciones.append("grupo = %s")
            parametros.append(grupo)

        where_sql = " AND ".join(condiciones)
        query = f"""
            SELECT 
                COUNT(DISTINCT arbitro) as total_arbitros,
                COUNT(id) as total_partidos,
                COALESCE(SUM(tarjetas_amarillas), 0) as total_amarillas,
                COALESCE(SUM(tarjetas_rojas), 0) as total_rojas,
                COALESCE(ROUND(AVG(tarjetas_amarillas)::numeric, 2), 0) as media_amarillas_partido,
                COALESCE(ROUND(AVG(tarjetas_rojas)::numeric, 2), 0) as media_rojas_partido
            FROM partidos
            WHERE {where_sql};
        """
        with get_db_cursor() as cur:
            cur.execute(query, tuple(parametros))
            return cur.fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error consultando KPIs globales: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Error interno al consultar los indicadores globales.",
        ) from exc


@app.get("/api/stats")
def obtener_estadisticas_arbitros(
    categoria: Optional[str] = Query(None, description="Filtrar por categoría/competición"),
    grupo: Optional[str] = Query(None, description="Filtrar por grupo"),
):
    """Retorna las estadísticas acumuladas y promedios agrupados por árbitro."""
    try:
        condiciones = ["arbitro IS NOT NULL", "arbitro != ''"]
        parametros = []

        if categoria:
            condiciones.append("categoria = %s")
            parametros.append(categoria)
        if grupo:
            condiciones.append("grupo = %s")
            parametros.append(grupo)

        where_sql = " AND ".join(condiciones)
        query = f"""
            SELECT 
                arbitro,
                COUNT(id) as partidos,
                SUM(tarjetas_amarillas) as total_amarillas,
                SUM(tarjetas_rojas) as total_rojas,
                ROUND(AVG(tarjetas_amarillas)::numeric, 2) as media_amarillas,
                ROUND(AVG(tarjetas_rojas)::numeric, 2) as media_rojas
            FROM partidos
            WHERE {where_sql}
            GROUP BY arbitro
            ORDER BY partidos DESC, media_amarillas DESC;
        """
        with get_db_cursor() as cur:
            cur.execute(query, tuple(parametros))
            return cur.fetchall()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error consultando estadísticas de árbitros: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Error interno al consultar las estadísticas arbitrales.",
        ) from exc


@app.get("/api/arbitros/search")
def buscar_arbitro(
    nombre: str = Query(..., min_length=2, description="Nombre parcial o completo del árbitro")
):
    """Busca los partidos pitados por un árbitro concreto."""
    try:
        query = """
            SELECT 
                id,
                fecha,
                categoria,
                grupo,
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
        with get_db_cursor() as cur:
            cur.execute(query, (f"%{nombre}%",))
            partidos = cur.fetchall()
        return {
            "arbitro": nombre,
            "total_encontrados": len(partidos),
            "partidos": partidos,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error buscando árbitro '%s': %s", nombre, exc)
        raise HTTPException(
            status_code=500,
            detail="Error interno al buscar partidos del árbitro.",
        ) from exc
