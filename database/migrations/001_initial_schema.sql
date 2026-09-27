-- ============================================================
-- Migración 001: Esquema inicial del sistema HSE
-- Proyecto: Email-Automation (PostgreSQL 16 auto-hospedado)
-- Descripción:
--   Crea la extensión pgcrypto, el tipo ENUM de estados y las
--   tres tablas principales: configuración dinámica, plantillas
--   de correo y registro de justificaciones.
-- Ejecución:
--   Se ejecuta automáticamente al primer arranque del contenedor
--   vía /docker-entrypoint-initdb.d. También es re-ejecutable
--   de forma manual (idempotente).
-- ============================================================

-- ----------------------------------------------------------
-- Extensión necesaria para gen_random_uuid() (IDs de justifications)
-- ----------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ----------------------------------------------------------
-- 1. Tipo ENUM: estados posibles de una justificación
-- ----------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE justification_status AS ENUM (
        'APROBADO_AUTO',
        'RECHAZADO_AUTO',
        'REVISION_MANUAL',
        'APROBADO_MANUAL',
        'RECHAZADO_MANUAL'
    );
EXCEPTION
    -- Si el tipo ya existe (re-ejecución manual), no hacer nada
    WHEN duplicate_object THEN NULL;
END $$;

-- ----------------------------------------------------------
-- 2. Tabla de configuración dinámica del sistema
--    Permite cambiar reglas de negocio sin modificar código
--    (arquitectura config-driven: ajustes sin tocar producción)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS hse_system_config (
    key VARCHAR(50) PRIMARY KEY,               -- Clave única, ej: 'evaluation_criteria'
    value JSONB NOT NULL,                      -- Valor flexible en formato JSON
    description TEXT,                          -- Descripción legible para el equipo HSE
    updated_at TIMESTAMPTZ DEFAULT NOW()       -- Fecha de última actualización
);

COMMENT ON TABLE hse_system_config IS 'Parámetros dinámicos del sistema HSE (criterios, palabras clave).';
COMMENT ON COLUMN hse_system_config.key IS 'Identificador único del parámetro.';
COMMENT ON COLUMN hse_system_config.value IS 'Contenido JSON del parámetro.';

-- ----------------------------------------------------------
-- 3. Tabla de plantillas de correo reutilizables
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_templates (
    id VARCHAR(50) PRIMARY KEY,                -- 'APPROVED', 'REJECTED', 'MANUAL_REVIEW'
    subject TEXT NOT NULL,                     -- Asunto del correo
    body_html TEXT NOT NULL,                   -- Cuerpo HTML con variables {{nombre_coder}}, {{fecha}}, etc.
    updated_at TIMESTAMPTZ DEFAULT NOW()       -- Fecha de última actualización
);

COMMENT ON TABLE email_templates IS 'Plantillas de respuesta editables sin desplegar código.';

-- ----------------------------------------------------------
-- 4. Tabla principal: registro de justificaciones recibidas
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS justifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- Identificador único generado automáticamente
    sender_email VARCHAR(255) NOT NULL,             -- Correo del coder remitente
    sender_name VARCHAR(255),                       -- Nombre del remitente (si se extrae)
    cohort_group VARCHAR(100),                      -- Cohorte o grupo al que pertenece
    email_subject TEXT,                             -- Asunto original del correo
    email_body TEXT,                                -- Cuerpo original del correo
    source_provider VARCHAR(20) NOT NULL            -- Origen: 'OUTLOOK' o 'GMAIL'
        CHECK (source_provider IN ('OUTLOOK', 'GMAIL')),
    status justification_status                    -- Estado del flujo de aprobación
        DEFAULT 'REVISION_MANUAL',
    ai_verdict JSONB,                               -- Veredicto estructurado del motor de IA
    ai_confidence NUMERIC(3,2)                      -- Confianza de la IA (0.00 a 1.00)
        CHECK (ai_confidence IS NULL OR (ai_confidence >= 0 AND ai_confidence <= 1)),
    attachment_urls TEXT[],                         -- Lista de URLs de evidencias adjuntas
    tl_notes TEXT,                                  -- Notas manuales de la Team Leader
    processed_in_seconds NUMERIC(4,2),              -- Tiempo de procesamiento del pipeline
    created_at TIMESTAMPTZ DEFAULT NOW()            -- Fecha de ingreso al sistema
);

COMMENT ON TABLE justifications IS 'Registro central de justificaciones de inasistencia/tardanza.';
COMMENT ON COLUMN justifications.status IS 'Estado actual dentro del flujo HSE.';
COMMENT ON COLUMN justifications.ai_verdict IS 'Resultado JSON del motor Strata Core / IA.';

-- ----------------------------------------------------------
-- 5. Índices para el dashboard y los filtros más usados
-- ----------------------------------------------------------
-- Índice por estado: filtra APROBADO_AUTO, REVISION_MANUAL, etc.
CREATE INDEX IF NOT EXISTS idx_justifications_status
    ON justifications (status);

-- Índice por fecha descendente: ordena lo más reciente primero
CREATE INDEX IF NOT EXISTS idx_justifications_created_at
    ON justifications (created_at DESC);
