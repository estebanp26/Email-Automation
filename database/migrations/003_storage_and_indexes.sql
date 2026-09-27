-- ============================================================
-- Migración 003: Almacenamiento de adjuntos, índices de alto rendimiento y vistas
-- Proyecto: Email-Automation (PostgreSQL 16 auto-hospedado)
-- Descripción:
--   Implementa:
--   1. Tabla justification_attachments con soporte para metadatos,
--      hashes de desduplicación y cajas delimitadoras espaciales
--      (spatial_boxes) emitidas por Strata Core para el visor interactivo (FRONT-03).
--   2. Índices GIN sobre JSONB e índices compuestos para garantizar
--      consultas del Dashboard en menos de 50 milisegundos (DB-04).
--   3. Vistas analíticas optimizadas para los KPIs del Dashboard (vw_dashboard_kpis).
--   4. Triggers automáticos de actualización para updated_at.
-- ============================================================

-- ----------------------------------------------------------
-- 1. Tabla de adjuntos y metadatos de evidencias (DB-02)
--    Soporta integración tanto con volumen local/MinIO
--    como con Supabase Storage (bucket 'justification-attachments').
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS justification_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    justification_id UUID NOT NULL REFERENCES justifications(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,                                  -- Nombre original del archivo (ej. 'incapacidad.pdf')
    file_path_or_url TEXT NOT NULL,                           -- Ruta en el storage local o URL del bucket
    mime_type VARCHAR(100) NOT NULL,                          -- 'application/pdf', 'image/jpeg', 'image/png'
    file_size_bytes BIGINT,                                   -- Tamaño en bytes del archivo
    sha256_hash VARCHAR(64),                                  -- Hash para control de integridad y desduplicación
    spatial_boxes JSONB,                                      -- Coordenadas espaciales (x0, y0, x1, y1) emitidas por Strata Core
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE justification_attachments IS 'Metadatos de evidencias documentales y coordenadas espaciales emitidas por Strata Core.';
COMMENT ON COLUMN justification_attachments.spatial_boxes IS 'Bounding boxes de sellos, firmas, fechas y nombres para auditoría visual en el Frontend.';

-- ----------------------------------------------------------
-- 2. Índices de Alto Rendimiento para el Dashboard (DB-04)
--    Garantiza SLA de consultas < 50ms incluso con > 50.000 registros
-- ----------------------------------------------------------

-- Índice GIN para búsquedas instantáneas dentro del veredicto JSONB de Strata Core
CREATE INDEX IF NOT EXISTS idx_justifications_ai_verdict_gin
    ON justifications USING gin (ai_verdict jsonb_path_ops);

-- Índice compuesto para la bandeja Split-View: filtra por estado y ordena por fecha
CREATE INDEX IF NOT EXISTS idx_justifications_status_created_at
    ON justifications (status, created_at DESC);

-- Índice para acelerar búsquedas por remitente / coder
CREATE INDEX IF NOT EXISTS idx_justifications_sender_email
    ON justifications (sender_email);

-- Índice para agrupamiento por cohorte en vistas analíticas
CREATE INDEX IF NOT EXISTS idx_justifications_cohort
    ON justifications (cohort_group);

-- Índice de clave foránea en attachments
CREATE INDEX IF NOT EXISTS idx_attachments_justification_id
    ON justification_attachments (justification_id);

-- Índice para prevención de adjuntos duplicados por hash
CREATE INDEX IF NOT EXISTS idx_attachments_sha256
    ON justification_attachments (sha256_hash);

-- ----------------------------------------------------------
-- 3. Vistas SQL Optimizadas para el Dashboard (FRONT-06 & KpiCard)
-- ----------------------------------------------------------

-- Vista de KPIs generales: permite al Frontend consultar todos los contadores en una sola lectura
CREATE OR REPLACE VIEW vw_dashboard_kpis AS
SELECT
    COUNT(*) AS total_recibidos,
    COUNT(*) FILTER (WHERE status IN ('APROBADO_AUTO', 'APROBADO_MANUAL')) AS total_aprobados,
    COUNT(*) FILTER (WHERE status IN ('RECHAZADO_AUTO', 'RECHAZADO_MANUAL')) AS total_rechazados,
    COUNT(*) FILTER (WHERE status = 'REVISION_MANUAL') AS total_pendientes,
    COUNT(*) FILTER (WHERE status = 'APROBADO_AUTO') AS auto_aprobados,
    COUNT(*) FILTER (WHERE status = 'RECHAZADO_AUTO') AS auto_rechazados,
    ROUND(
        (COUNT(*) FILTER (WHERE status IN ('APROBADO_AUTO', 'RECHAZADO_AUTO'))::NUMERIC / 
        NULLIF(COUNT(*), 0)::NUMERIC) * 100, 
        1
    ) AS tasa_automatizacion_pct,
    ROUND(
        (COUNT(*) FILTER (WHERE status IN ('APROBADO_AUTO', 'APROBADO_MANUAL'))::NUMERIC / 
        NULLIF(COUNT(*), 0)::NUMERIC) * 100, 
        1
    ) AS tasa_aprobacion_pct,
    ROUND(AVG(processed_in_seconds), 2) AS tiempo_promedio_segundos
FROM justifications;

COMMENT ON VIEW vw_dashboard_kpis IS 'Métricas agregadas consolidadas para las tarjetas KPI del Dashboard.';

-- Vista de justificaciones recientes para la bandeja de entrada
CREATE OR REPLACE VIEW vw_recent_justifications AS
SELECT
    j.id,
    j.sender_name,
    j.sender_email,
    j.cohort_group,
    j.email_subject,
    j.source_provider,
    j.status,
    j.ai_confidence,
    j.processed_in_seconds,
    j.ai_verdict->>'tipo_novedad' AS tipo_novedad,
    j.ai_verdict->>'motivo_decision' AS motivo_decision,
    COALESCE(cardinality(j.attachment_urls), 0) AS total_adjuntos,
    j.created_at
FROM justifications j
ORDER BY j.created_at DESC;

COMMENT ON VIEW vw_recent_justifications IS 'Bandeja formateada de novedades para el visor y split-view del Frontend.';

-- ----------------------------------------------------------
-- 4. Triggers automáticos para mantenimiento de updated_at
-- ----------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_auto_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_update_hse_config_timestamp'
    ) THEN
        CREATE TRIGGER trg_update_hse_config_timestamp
        BEFORE UPDATE ON hse_system_config
        FOR EACH ROW
        EXECUTE FUNCTION fn_auto_update_timestamp();
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_update_email_templates_timestamp'
    ) THEN
        CREATE TRIGGER trg_update_email_templates_timestamp
        BEFORE UPDATE ON email_templates
        FOR EACH ROW
        EXECUTE FUNCTION fn_auto_update_timestamp();
    END IF;
END $$;
