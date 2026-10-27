import os
import psycopg2
from datetime import datetime

# Conexión a Supabase usando variables de entorno de producción
DB_URL = os.getenv("DATABASE_URL")

def obtener_conexion():
    if not DB_URL:
        raise ValueError("DATABASE_URL no está configurada en las variables de entorno.")
    return psycopg2.connect(DB_URL)

def ejecutar_actualizacion_semanal():
    print(f"[{datetime.now()}] Iniciando actualización semanal de partidos RFAF...")
    
    conn = obtener_conexion()
    cur = conn.cursor()
    
    # 1. Obtener la última fecha registrada en la base de datos
    cur.execute("SELECT MAX(fecha) FROM partidos;")
    ultima_fecha = cur.fetchone()[0]
    print(f"Último partido registrado en BD: {ultima_fecha}")

    # Lógica de raspado para traer solo jornadas posteriores a 'ultima_fecha'
    # ... (Aquí va la llamada a la función de scraping que ya usas en scraper_3_temporadas) ...
    
    conn.close()
    print(f"[{datetime.now()}] Actualización semanal completada con éxito.")

if __name__ == "__main__":
    ejecutar_actualizacion_semanal()