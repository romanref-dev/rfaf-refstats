CREATE TABLE IF NOT EXISTS delegaciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS arbitros (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    delegacion_id INT REFERENCES delegaciones(id),
    partidos_totales INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_arbitro_delegacion UNIQUE (nombre, delegacion_id)
);

CREATE TABLE IF NOT EXISTS partidos (
    id SERIAL PRIMARY KEY,
    acta_id VARCHAR(100) UNIQUE NOT NULL,
    temporada VARCHAR(20) NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    equipo_local VARCHAR(100) NOT NULL,
    equipo_visitante VARCHAR(100) NOT NULL,
    goles_local INT DEFAULT 0,
    goles_visitante INT DEFAULT 0,
    arbitro_id INT REFERENCES arbitros(id),
    amarillas_local INT DEFAULT 0,
    amarillas_visitante INT DEFAULT 0,
    rojas_local INT DEFAULT 0,
    rojas_visitante INT DEFAULT 0,
    fecha_partido DATE
);

CREATE INDEX IF NOT EXISTS idx_partidos_arbitro ON partidos(arbitro_id);
CREATE INDEX IF NOT EXISTS idx_partidos_temporada ON partidos(temporada);