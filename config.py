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
        "cod_grupo": "48933162",
        "total_jornadas": 30,
    },
]
GRUPOS_ESPERADOS_DH = {g["cod_grupo"] for g in GRUPOS_DH}

# 3.ª Federación
COMPETICION_TERCERA = "3.ª Federación"
COD_COMPETICION_TERCERA = "48465908"
GRUPOS_ESPERADOS_TERCERA = {"48710553", "48710554"}

# 1.ª Andaluza Sénior (8 Provincias)
COMPETICIONES_PRIMERA_ANDALUZA = [
    {"id": "48786377", "nombre": "1ª Andaluza Sénior (Almería)"},
    {"id": "48680130", "nombre": "1ª Andaluza Sénior (Cádiz)"},
    {"id": "48466090", "nombre": "1ª Andaluza Sénior (Córdoba)"},
    {"id": "48466157", "nombre": "1ª Andaluza Sénior (Granada)"},
    {"id": "48466521", "nombre": "1ª Andaluza Sénior (Huelva)"},
    {"id": "48466094", "nombre": "1ª Andaluza Sénior (Jaén)"},
    {"id": "48465920", "nombre": "1ª Andaluza Sénior (Málaga)"},
    {"id": "48466124", "nombre": "1ª Andaluza Sénior (Sevilla)"},
]

# 2.ª Andaluza Sénior (8 Provincias)
COMPETICIONES_SEGUNDA_ANDALUZA = [
    {"id": "49951770", "nombre": "2ª Andaluza Sénior (Almería)"},
    {"id": "48680489", "nombre": "2ª Andaluza Sénior (Cádiz)"},
    {"id": "48466092", "nombre": "2ª Andaluza Sénior (Córdoba)"},
    {"id": "48466167", "nombre": "2ª Andaluza Sénior (Granada)"},
    {"id": "48466523", "nombre": "2ª Andaluza Sénior (Huelva)"},
    {"id": "48466104", "nombre": "2ª Andaluza Sénior (Jaén)"},
    {"id": "48465922", "nombre": "2ª Andaluza Sénior (Málaga)"},
    {"id": "48466126", "nombre": "2ª Andaluza Sénior (Sevilla)"},
]

# 3.ª Andaluza Sénior
COMPETICIONES_TERCERA_ANDALUZA = [
    {"id": "48780558", "nombre": "3ª Andaluza Sénior (Cádiz)"},
    {"id": "49097854", "nombre": "3ª Andaluza Sénior (Córdoba)"},
    {"id": "48466195", "nombre": "3ª Andaluza Sénior (Granada)"},
    {"id": "48465924", "nombre": "3ª Andaluza Sénior (Málaga)"},
    {"id": "48466186", "nombre": "3ª Andaluza Sénior (Sevilla)"},
]

# Copas Sénior y Torneos RFAF (Aficionados)
COMPETICIONES_COPAS_AFICIONADOS = [
    {"id": "48773606", "nombre": "Copa Andalucía Senior"},
    {"id": "48772387", "nombre": "Copa RFAF"},
    {"id": "49349675", "nombre": "Copa Federación Sénior"},
    {"id": "48786998", "nombre": "Copa de Andalucía - Fase Provincial - 1ª Andaluza Senior (Almería)"},
    {"id": "48789706", "nombre": "Copa Provincial 1ª Andaluza Sénior (Córdoba)"},
    {"id": "48678442", "nombre": "Copa Andalucía 1ª Andaluza Sénior (Granada)"},
    {"id": "48466528", "nombre": "Copa Andalucía Fase Provincial 1ª Andaluza Senior (Huelva)"},
    {"id": "48769610", "nombre": "Copa Andalucía - Fase Provincial - 1ª Andaluza Sénior (Jaén)"},
    {"id": "48768306", "nombre": "Copa Andalucía - Fase Provincial - 1ª Andaluza Sénior (Málaga)"},
    {"id": "48674715", "nombre": "Copa 1ª Andaluza Sénior (Sevilla)"},
    {"id": "48829832", "nombre": "Trofeo Copa Presidente Diputación (Jaén)"},
]

# Otras ligas del bloque Aficionados
COMPETICIONES_OTRAS_AFICIONADOS = [
    {"id": "50651827", "nombre": "Liga Veteranos Alto Guadalquivir (Córdoba)"},
    {"id": "48466286", "nombre": "Liga de Peñas Costa Tropical"},
    {"id": "50231134", "nombre": "Interfútbol Torneo Félix Esquinas RFAF (Córdoba)"},
    {"id": "51201850", "nombre": "Fútbol Andando"},
    {"id": "48466508", "nombre": "Liga Andaluza Inclusiva (Granada)"},
    {"id": "51093916", "nombre": "Copa Provincial Inclusiva"},
    {"id": "48466608", "nombre": "Liga Andaluza Inclusiva (Cádiz)"},
    {"id": "51196770", "nombre": "I Concentración Inclusiva (Jaén)"},
    {"id": "49750007", "nombre": "Liga Provincial Inclusiva (Huelva)"},
]

# Catálogo completo de las 43 competiciones del bloque AFICIONADOS
COMPETICIONES_AFICIONADOS = [
    {"id": COD_COMPETICION_DH, "nombre": COMPETICION_DH},
    {"id": COD_COMPETICION_TERCERA, "nombre": COMPETICION_TERCERA},
    *COMPETICIONES_PRIMERA_ANDALUZA,
    *COMPETICIONES_SEGUNDA_ANDALUZA,
    *COMPETICIONES_TERCERA_ANDALUZA,
    *COMPETICIONES_COPAS_AFICIONADOS,
    *COMPETICIONES_OTRAS_AFICIONADOS,
]

# Tiempos de espera de scraping (ms / s)
ESPERA_MS = 1500
ESPERA_ENTRE_ACTAS = 1
ESPERA_ESTABILIDAD_MS = 500
REPETICIONES_ESTABLES = 5
INTENTOS_ESTABILIDAD = 40
