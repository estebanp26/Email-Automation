-- 001_initial_schema.sql
-- Ejecutar en Supabase SQL Editor

-- 1. ENUMS
DO $$ BEGIN
    CREATE TYPE justification_status AS ENUM (
        'APROBADO_AUTO',
        'RECHAZADO_AUTO',
        'REVISION_MANUAL',
        'APROBADO_MANUAL',
        'RECHAZADO_MANUAL'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. TABLA DE CONFIGURACIÓN DINÁMICA (Permite cambios el lunes sin tocar código)
CREATE TABLE IF NOT EXISTS hse_system_config (
    key VARCHAR(50) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. PLANTILLAS DE CORREO DINÁMICAS
CREATE TABLE IF NOT EXISTS email_templates (
    id VARCHAR(50) PRIMARY KEY, -- 'APPROVED', 'REJECTED', 'MANUAL_REVIEW'
    subject VARCHAR(255) NOT NULL,
    html_body TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. REGISTRO PRINCIPAL DE JUSTIFICACIONES
CREATE TABLE IF NOT EXISTS justifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),
    cohort_group VARCHAR(100),
    email_subject TEXT,
    email_body TEXT,
    source_provider VARCHAR(20) NOT NULL, -- 'OUTLOOK' o 'GMAIL'
    status justification_status DEFAULT 'REVISION_MANUAL',
    ai_verdict JSONB,
    ai_confidence NUMERIC(3,2),
    attachment_urls TEXT[],
    tl_notes TEXT,
    processed_in_seconds NUMERIC(4,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para búsqueda rápida en Dashboard
CREATE INDEX IF NOT EXISTS idx_justifications_status ON justifications(status);
CREATE INDEX IF NOT EXISTS idx_justifications_created_at ON justifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_justifications_sender ON justifications(sender_email);
