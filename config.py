# config.py - Configuración centralizada de RFAF RefStats
import os

SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    "https://ijczoeyfgnngocstxgfb.supabase.co"
)
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

URL_BASE = (
    "https://www.rfaf.es/pnfg/NPcd/"
    "NFG_CmpJornada?cod_primaria=1000120"
)

URL_ACTA_BASE = (
    "https://www.rfaf.es/pnfg/NPcd/"
    "NFG_CmpPartido?cod_primaria=1000120&CodActa={id}&cod_acta={id}"
)

COD_TEMPORADA = "22"

# División de Honor Sénior
COMPETICION_DH = "División Honor Sénior"
COD_COMPETICION_DH = "48466530"
GRUPOS_DH = [
    {
        "nombre": "División de Honor Senior (Grupo 1)",
        "cod_grupo": "49641343",
        "total_jornadas": 30,
    },
    {
        "nombre": "División de Honor Senior (Grupo 2)",
        "cod_grupo": "49641344",
        "total_jornadas": 30,
    },
]
GRUPOS_ESPERADOS_DH = {g["cod_grupo"] for g in GRUPOS_DH}

# 3.ª Federación
COMPETICION_TERCERA = "3.ª Federación"
COD_COMPETICION_TERCERA = "48465908"
GRUPOS_ESPERADOS_TERCERA = {"48710553", "48710554"}

# Tiempos de espera de scraping (ms / s)
ESPERA_MS = 1500
ESPERA_ENTRE_ACTAS = 1
ESPERA_ESTABILIDAD_MS = 500
REPETICIONES_ESTABLES = 5
INTENTOS_ESTABILIDAD = 40
