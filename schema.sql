-- Esquema actualizado de RFAF RefStats (Supabase / PostgreSQL)

CREATE TABLE IF NOT EXISTS competiciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    grupo VARCHAR(100) NOT NULL,
    temporada VARCHAR(20) NOT NULL DEFAULT '2026/2027',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_competicion_grupo_temporada UNIQUE (nombre, grupo, temporada)
);

CREATE TABLE IF NOT EXISTS arbitros (
    id VARCHAR(100) PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE NOT NULL,
    delegacion VARCHAR(100),
    partidos_dirigidos INT DEFAULT 0,
    total_amarillas INT DEFAULT 0,
    total_rojas INT DEFAULT 0,
    promedio_amarillas NUMERIC(5,2) DEFAULT 0,
    promedio_rojas NUMERIC(5,2) DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS partidos (
    id VARCHAR(100) PRIMARY KEY,
    acta_id VARCHAR(100) UNIQUE NOT NULL,
    fecha DATE NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    competicion VARCHAR(100) NOT NULL,
    grupo VARCHAR(100) NOT NULL,
    id_grupo VARCHAR(50) NOT NULL,
    jornada INT NOT NULL,
    id_jornada INT NOT NULL,
    equipo_local VARCHAR(150) NOT NULL,
    equipo_visitante VARCHAR(150) NOT NULL,
    goles_local INT DEFAULT 0,
    goles_visitante INT DEFAULT 0,
    resultado VARCHAR(20),
    arbitro VARCHAR(150) DEFAULT '',
    arbitro_nombre VARCHAR(150) DEFAULT '',
    arbitro_id VARCHAR(100),
    delegacion VARCHAR(100),
    delegacion_arbitro VARCHAR(100),
    hora VARCHAR(20),
    estadio VARCHAR(200),
    ciudad VARCHAR(150),
    tarjetas_amarillas INT DEFAULT 0,
    tarjetas_rojas INT DEFAULT 0,
    tarjetas_amarillas_local INT DEFAULT 0,
    tarjetas_amarillas_visitante INT DEFAULT 0,
    tarjetas_rojas_local INT DEFAULT 0,
    tarjetas_rojas_visitante INT DEFAULT 0,
    jugadores_tarjetas JSONB DEFAULT '[]'::jsonb,
    detalles_acta JSONB DEFAULT '{}'::jsonb,
    estado VARCHAR(50) DEFAULT 'Finalizado',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS actas_tarjetas (
    id SERIAL PRIMARY KEY,
    partido_id VARCHAR(100) REFERENCES partidos(id) ON DELETE CASCADE,
    acta_id VARCHAR(100) NOT NULL,
    numero_tarjeta INT NOT NULL,
    competicion VARCHAR(100) NOT NULL,
    grupo VARCHAR(100) NOT NULL,
    jornada INT NOT NULL,
    fecha DATE NOT NULL,
    equipo VARCHAR(150) NOT NULL,
    jugador VARCHAR(150) NOT NULL,
    minuto VARCHAR(20) NOT NULL,
    tipo_persona VARCHAR(50) DEFAULT 'jugador',
    tipo_tarjeta VARCHAR(20) NOT NULL CHECK (tipo_tarjeta IN ('amarilla', 'roja')),
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_acta_numero_tarjeta UNIQUE (acta_id, numero_tarjeta)
);

CREATE INDEX IF NOT EXISTS idx_partidos_arbitro ON partidos(arbitro);
CREATE INDEX IF NOT EXISTS idx_partidos_competicion_grupo ON partidos(competicion, grupo, jornada);
CREATE INDEX IF NOT EXISTS idx_partidos_fecha ON partidos(fecha DESC);
CREATE INDEX IF NOT EXISTS idx_actas_tarjetas_acta_id ON actas_tarjetas(acta_id);
CREATE INDEX IF NOT EXISTS idx_actas_tarjetas_jugador ON actas_tarjetas(jugador);
CREATE INDEX IF NOT EXISTS idx_arbitros_nombre ON arbitros(nombre);
