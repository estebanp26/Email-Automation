-- ============================================================
-- Migración 007: Configuración y justificaciones aprobadas / no aprobadas
-- Proyecto: Email-Automation (PostgreSQL 16)
-- Descripción:
--   1. Restaura la tabla de configuración HSE_SYSTEM_CONFIG.
--   2. Crea justifications_approved (aprobadas).
--   3. Crea justifications_not_approved (no aprobadas).
-- Ejecución:
--   psql -U hse_admin -d hse_email_automation -f 007_justificaciones_aprobadas_y_no_aprobadas.sql
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ----------------------------------------------------------
-- 1. TABLA: HSE_SYSTEM_CONFIG — Configuración dinámica
-- PK: clave | Sin FK (tabla catálogo aislada)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS hse_system_config (
    clave VARCHAR(50) PRIMARY KEY,                -- Clave única, ej: 'criterios_evaluacion'
    valor JSONB NOT NULL,                         -- Valor flexible en formato JSON
    descripcion TEXT,                             -- Descripción legible para el equipo HSE
    actualizado_en TIMESTAMPTZ DEFAULT NOW()      -- Fecha de última actualización
);

COMMENT ON TABLE hse_system_config IS 'Parámetros dinámicos del sistema HSE: reglas editables sin desplegar código.';
COMMENT ON COLUMN hse_system_config.clave IS 'Identificador único del parámetro.';
COMMENT ON COLUMN hse_system_config.valor IS 'Contenido JSON del parámetro (criterios, umbrales, catálogos).';
COMMENT ON COLUMN hse_system_config.descripcion IS 'Descripción funcional para la Team Leader.';
COMMENT ON COLUMN hse_system_config.actualizado_en IS 'Fecha de última actualización del parámetro.';

-- Compatibilidad con esquema anterior (clave/valor/descripcion en inglés):
-- Si la tabla ya existe con columnas "key/value/description/updated_at",
-- se renombran a español de forma idempotente.
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hse_system_config' AND column_name = 'key') THEN
        ALTER TABLE hse_system_config RENAME COLUMN "key" TO clave;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hse_system_config' AND column_name = 'value') THEN
        ALTER TABLE hse_system_config RENAME COLUMN "value" TO valor;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hse_system_config' AND column_name = 'description') THEN
        ALTER TABLE hse_system_config RENAME COLUMN description TO descripcion;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hse_system_config' AND column_name = 'updated_at') THEN
        ALTER TABLE hse_system_config RENAME COLUMN updated_at TO actualizado_en;
    END IF;
END $$;

-- ----------------------------------------------------------
-- 2. TABLA: justifications_approved — Justificaciones aprobadas
-- PK: identificador | FK: justificacion_id -> justifications(id)
-- FK: identificador_coder -> coders(id)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS justifications_approved (
    identificador UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Identificador único interno
    justificacion_id UUID NOT NULL                            -- Vínculo único a la justificación origen
        CONSTRAINT fk_aprobadas_justificacion
        REFERENCES justifications(id) ON DELETE CASCADE,
    identificador_coder UUID                                  -- Vínculo al coder oficial
        CONSTRAINT fk_aprobadas_coder
        REFERENCES coders(id) ON DELETE SET NULL,
    fecha_decision TIMESTAMPTZ DEFAULT NOW(),                 -- Fecha de aprobación
    decidido_por VARCHAR(255),                                -- Responsable: 'SISTEMA' o correo de la Team Leader
    metodo_decision VARCHAR(30) DEFAULT 'APROBADO_AUTO'       -- 'APROBADO_AUTO' o 'APROBADO_MANUAL'
        CONSTRAINT chk_aprobadas_metodo
        CHECK (metodo_decision IN ('APROBADO_AUTO', 'APROBADO_MANUAL')),
    nivel_confianza NUMERIC(3,2)                              -- Confianza de la decisión (0.00 a 1.00)
        CONSTRAINT chk_aprobadas_confianza
        CHECK (nivel_confianza IS NULL OR (nivel_confianza >= 0 AND nivel_confianza <= 1)),
    notas_revision TEXT,                                      -- Notas manuales de la Team Leader
    creado_en TIMESTAMPTZ DEFAULT NOW(),                      -- Fecha de registro
    actualizado_en TIMESTAMPTZ DEFAULT NOW(),                 -- Fecha de última modificación
    CONSTRAINT uq_aprobadas_justificacion UNIQUE (justificacion_id)
);

COMMENT ON TABLE justifications_approved IS 'Justificaciones aprobadas por el sistema o por la Team Leader.';
COMMENT ON COLUMN justifications_approved.identificador IS 'Identificador único interno del registro aprobado.';
COMMENT ON COLUMN justifications_approved.justificacion_id IS 'Vínculo único a la justificación origen; borrado en cascada.';
COMMENT ON COLUMN justifications_approved.identificador_coder IS 'Vínculo al coder oficial; NULL si no fue identificado.';
COMMENT ON COLUMN justifications_approved.fecha_decision IS 'Fecha en que se aprobó la justificación.';
COMMENT ON COLUMN justifications_approved.decidido_por IS 'Responsable de la aprobación: SISTEMA o correo de la Team Leader.';
COMMENT ON COLUMN justifications_approved.metodo_decision IS 'Método de aprobación: APROBADO_AUTO o APROBADO_MANUAL.';
COMMENT ON COLUMN justifications_approved.nivel_confianza IS 'Confianza de la decisión entre 0.00 y 1.00.';
COMMENT ON COLUMN justifications_approved.notas_revision IS 'Notas manuales de revisión de la Team Leader.';
COMMENT ON COLUMN justifications_approved.creado_en IS 'Fecha de registro del fallo aprobado.';
COMMENT ON COLUMN justifications_approved.actualizado_en IS 'Fecha de última modificación del registro.';
COMMENT ON CONSTRAINT uq_aprobadas_justificacion ON justifications_approved IS 'Una justificación solo puede aprobarse una vez.';
COMMENT ON CONSTRAINT fk_aprobadas_justificacion ON justifications_approved IS 'Garantiza que la justificación origen exista.';
COMMENT ON CONSTRAINT fk_aprobadas_coder ON justifications_approved IS 'Mantiene la trazabilidad al coder oficial.';
COMMENT ON CONSTRAINT chk_aprobadas_metodo ON justifications_approved IS 'Solo permite métodos de aprobación válidos.';
COMMENT ON CONSTRAINT chk_aprobadas_confianza ON justifications_approved IS 'Confianza válida entre 0.00 y 1.00.';

-- ----------------------------------------------------------
-- 3. TABLA: justifications_not_approved — Justificaciones no aprobadas
-- PK: identificador | FK: justificacion_id -> justifications(id)
-- FK: identificador_coder -> coders(id)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS justifications_not_approved (
    identificador UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Identificador único interno
    justificacion_id UUID NOT NULL                            -- Vínculo único a la justificación origen
        CONSTRAINT fk_no_aprobadas_justificacion
        REFERENCES justifications(id) ON DELETE CASCADE,
    identificador_coder UUID                                  -- Vínculo al coder oficial
        CONSTRAINT fk_no_aprobadas_coder
        REFERENCES coders(id) ON DELETE SET NULL,
    fecha_decision TIMESTAMPTZ DEFAULT NOW(),                 -- Fecha del rechazo
    decidido_por VARCHAR(255),                                -- Responsable: 'SISTEMA' o correo de la Team Leader
    metodo_decision VARCHAR(30) DEFAULT 'RECHAZADO_AUTO'      -- 'RECHAZADO_AUTO' o 'RECHAZADO_MANUAL'
        CONSTRAINT chk_no_aprobadas_metodo
        CHECK (metodo_decision IN ('RECHAZADO_AUTO', 'RECHAZADO_MANUAL')),
    motivo_rechazo TEXT NOT NULL,                             -- Motivo obligatorio del rechazo
    categoria_rechazo VARCHAR(100),                           -- Categoría: 'soporte_ilegible', 'fuera_de_plazo', etc.
    nivel_confianza NUMERIC(3,2)                              -- Confianza de la decisión (0.00 a 1.00)
        CONSTRAINT chk_no_aprobadas_confianza
        CHECK (nivel_confianza IS NULL OR (nivel_confianza >= 0 AND nivel_confianza <= 1)),
    permite_reenvio BOOLEAN DEFAULT TRUE,                     -- Indica si el coder puede reenviar soporte
    notas_revision TEXT,                                      -- Notas manuales de la Team Leader
    creado_en TIMESTAMPTZ DEFAULT NOW(),                      -- Fecha de registro
    actualizado_en TIMESTAMPTZ DEFAULT NOW(),                 -- Fecha de última modificación
    CONSTRAINT uq_no_aprobadas_justificacion UNIQUE (justificacion_id)
);

COMMENT ON TABLE justifications_not_approved IS 'Justificaciones rechazadas por el sistema o por la Team Leader.';
COMMENT ON COLUMN justifications_not_approved.identificador IS 'Identificador único interno del registro rechazado.';
COMMENT ON COLUMN justifications_not_approved.justificacion_id IS 'Vínculo único a la justificación origen; borrado en cascada.';
COMMENT ON COLUMN justifications_not_approved.identificador_coder IS 'Vínculo al coder oficial; NULL si no fue identificado.';
COMMENT ON COLUMN justifications_not_approved.fecha_decision IS 'Fecha en que se rechazó la justificación.';
COMMENT ON COLUMN justifications_not_approved.decidido_por IS 'Responsable del rechazo: SISTEMA o correo de la Team Leader.';
COMMENT ON COLUMN justifications_not_approved.metodo_decision IS 'Método de rechazo: RECHAZADO_AUTO o RECHAZADO_MANUAL.';
COMMENT ON COLUMN justifications_not_approved.motivo_rechazo IS 'Motivo obligatorio del rechazo enviado al coder.';
COMMENT ON COLUMN justifications_not_approved.categoria_rechazo IS 'Categoría del rechazo para analítica del dashboard.';
COMMENT ON COLUMN justifications_not_approved.nivel_confianza IS 'Confianza de la decisión entre 0.00 y 1.00.';
COMMENT ON COLUMN justifications_not_approved.permite_reenvio IS 'Indica si el coder puede reenviar soporte corregido.';
COMMENT ON COLUMN justifications_not_approved.notas_revision IS 'Notas manuales de revisión de la Team Leader.';
COMMENT ON COLUMN justifications_not_approved.creado_en IS 'Fecha de registro del fallo rechazado.';
COMMENT ON COLUMN justifications_not_approved.actualizado_en IS 'Fecha de última modificación del registro.';
COMMENT ON CONSTRAINT uq_no_aprobadas_justificacion ON justifications_not_approved IS 'Una justificación solo puede rechazarse una vez.';
COMMENT ON CONSTRAINT fk_no_aprobadas_justificacion ON justifications_not_approved IS 'Garantiza que la justificación origen exista.';
COMMENT ON CONSTRAINT fk_no_aprobadas_coder ON justifications_not_approved IS 'Mantiene la trazabilidad al coder oficial.';
COMMENT ON CONSTRAINT chk_no_aprobadas_metodo ON justifications_not_approved IS 'Solo permite métodos de rechazo válidos.';
COMMENT ON CONSTRAINT chk_no_aprobadas_confianza ON justifications_not_approved IS 'Confianza válida entre 0.00 y 1.00.';

-- ----------------------------------------------------------
-- 4. ÍNDICES DE RENDIMIENTO
-- ----------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_aprobadas_justificacion_id ON justifications_approved (justificacion_id);
CREATE INDEX IF NOT EXISTS idx_aprobadas_coder ON justifications_approved (identificador_coder);
CREATE INDEX IF NOT EXISTS idx_aprobadas_fecha ON justifications_approved (fecha_decision DESC);
CREATE INDEX IF NOT EXISTS idx_no_aprobadas_justificacion_id ON justifications_not_approved (justificacion_id);
CREATE INDEX IF NOT EXISTS idx_no_aprobadas_coder ON justifications_not_approved (identificador_coder);
CREATE INDEX IF NOT EXISTS idx_no_aprobadas_fecha ON justifications_not_approved (fecha_decision DESC);
CREATE INDEX IF NOT EXISTS idx_no_aprobadas_categoria ON justifications_not_approved (categoria_rechazo);

-- ----------------------------------------------------------
-- 5. DISPARADORES DE actualizado_en
-- ----------------------------------------------------------
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_actualiza_aprobadas_marca') THEN
        CREATE TRIGGER trg_actualiza_aprobadas_marca
        BEFORE UPDATE ON justifications_approved
        FOR EACH ROW EXECUTE FUNCTION fn_auto_update_timestamp();
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_actualiza_no_aprobadas_marca') THEN
        CREATE TRIGGER trg_actualiza_no_aprobadas_marca
        BEFORE UPDATE ON justifications_not_approved
        FOR EACH ROW EXECUTE FUNCTION fn_auto_update_timestamp();
    END IF;
END $$;

-- Nota: fn_auto_update_timestamp() actualiza la columna "updated_at".
-- Si las tablas nuevas usan "actualizado_en", este disparador alterno la mantiene.
CREATE OR REPLACE FUNCTION fn_actualiza_marca_temporal()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fn_actualiza_marca_temporal IS 'Actualiza automáticamente actualizado_en en cada UPDATE.';

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_aprobadas_actualizado_en') THEN
        CREATE TRIGGER trg_aprobadas_actualizado_en
        BEFORE UPDATE ON justifications_approved
        FOR EACH ROW EXECUTE FUNCTION fn_actualiza_marca_temporal();
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_no_aprobadas_actualizado_en') THEN
        CREATE TRIGGER trg_no_aprobadas_actualizado_en
        BEFORE UPDATE ON justifications_not_approved
        FOR EACH ROW EXECUTE FUNCTION fn_actualiza_marca_temporal();
    END IF;
END $$;

-- ----------------------------------------------------------
-- 6. DATOS SEMILLA DE HSE_SYSTEM_CONFIG (idempotentes)
-- ----------------------------------------------------------
INSERT INTO hse_system_config (clave, valor, descripcion)
VALUES
    ('criterios_evaluacion',
     '{"max_horas": 48, "confianza_minima": 0.80, "tipos_permitidos": ["medica", "calamidad_domestica", "tramite_legal", "fuerza_mayor", "falla_tecnica"]}'::jsonb,
     'Criterios de evaluación HSE inyectados dinámicamente en el prompt de la IA'),
    ('palabras_clave_correo',
     '["justificacion", "inasistencia", "falta", "incapacidad", "tardanza", "salida temprana", "excusa"]'::jsonb,
     'Palabras clave para el filtrado de correos entrantes'),
    ('instituciones_medicas_permitidas',
     '["SURA", "Sanitas", "Compensar", "Famisanar", "Nueva EPS", "Salud Total", "Coosalud", "EPS S.O.S", "Cruz Roja", "Clinica del Country"]'::jsonb,
     'Listado de instituciones de salud y EPS validadas en Colombia'),
    ('umbrales_operativos',
     '{"confianza_minima_aprobacion_auto": 0.85, "confianza_maxima_rechazo_auto": 0.20, "alerta_sla_minutos": 30}'::jsonb,
     'Umbrales de confianza para decisiones automáticas vs revisión manual de la Team Leader'),
    ('rutas_y_grupos_academicos',
     '{"rutas": ["Automatización con IA", "TypeScript Fullstack", "Analítica de Datos & BI", ".NET / C# Backend", "Node.js Backend", "Java Spring Boot", "BPO / Retiros"], "grupos": ["Automatización con IA AM", "TypeScript AM", "Analítica de datos AM", "C# PM", "NodeJS AM", "Java PM", "NodeJS PM", "BPO/Retiros"]}'::jsonb,
     'Listado de rutas técnicas y grupos oficiales de formación activa en Riwi')
ON CONFLICT (clave) DO UPDATE
SET valor = EXCLUDED.valor,
    descripcion = EXCLUDED.descripcion,
    actualizado_en = NOW();
