-- =============================================================================
-- MIGRACIÓN 005: Vista Analítica de Resumen Semanal para Comité HSE
-- Issue / Tarea: [DB-EXT-01] | Sprint 4 | Épica: EPIC-05
-- Responsable: Eliam (@aZian10)
-- Dependencias: [DB-01] (justifications, coders) y [DB-04] (performance indexes)
-- =============================================================================
-- Objetivo:
-- Proporcionar una vista analítica consolidada (v_hse_weekly_summary) que agrupa
-- novedades, inasistencias y solicitudes por ruta formativa (ej. Node.js Backend,
-- Java Spring Boot, Desarrollo Web, TypeScript Fullstack) y semana epidemiológica/académica
-- para el Comité Semanal de Permanencia y Seguimiento de HSE.
-- =============================================================================

CREATE OR REPLACE VIEW public.v_hse_weekly_summary
WITH (security_invoker = true) AS
SELECT 
    -- 1. Agrupador principal de ruta formativa
    COALESCE(c.route, 'Sin Ruta Asignada')                                              AS route,
    COALESCE(c.route, 'Sin Ruta Asignada')                                              AS ruta_formativa,

    -- 2. Periodo temporal (Semana académica y año)
    DATE_TRUNC('week', j.start_date)::DATE                                             AS week_start,
    DATE_TRUNC('week', j.start_date)::DATE                                             AS semana_inicio,
    EXTRACT(WEEK FROM j.start_date)::INTEGER                                            AS week_number,
    EXTRACT(WEEK FROM j.start_date)::INTEGER                                            AS numero_semana,
    EXTRACT(YEAR FROM j.start_date)::INTEGER                                            AS year,
    EXTRACT(YEAR FROM j.start_date)::INTEGER                                            AS anio,

    -- 3. Volumetría consolidada de solicitudes
    COUNT(j.id)                                                                         AS total_requests,
    COUNT(j.id)                                                                         AS total_solicitudes,

    -- 4. Desglose de estados de validación HSE
    COUNT(CASE 
        WHEN j.validation_status = 'APPROVED' OR j.hse_decision = 'APPROVED' 
        THEN 1 
    END)                                                                                AS total_approved,
    COUNT(CASE 
        WHEN j.validation_status = 'APPROVED' OR j.hse_decision = 'APPROVED' 
        THEN 1 
    END)                                                                                AS total_aprobadas,

    COUNT(CASE 
        WHEN j.validation_status = 'DISAPPROVED' OR j.hse_decision = 'DISAPPROVED' 
        THEN 1 
    END)                                                                                AS total_disapproved,
    COUNT(CASE 
        WHEN j.validation_status = 'DISAPPROVED' OR j.hse_decision = 'DISAPPROVED' 
        THEN 1 
    END)                                                                                AS total_rechazadas,

    COUNT(CASE 
        WHEN (j.validation_status NOT IN ('APPROVED', 'DISAPPROVED') OR j.validation_status IS NULL)
         AND (j.hse_decision IS NULL OR j.hse_decision NOT IN ('APPROVED', 'DISAPPROVED'))
        THEN 1 
    END)                                                                                AS total_pending,
    COUNT(CASE 
        WHEN (j.validation_status NOT IN ('APPROVED', 'DISAPPROVED') OR j.validation_status IS NULL)
         AND (j.hse_decision IS NULL OR j.hse_decision NOT IN ('APPROVED', 'DISAPPROVED'))
        THEN 1 
    END)                                                                                AS total_pendientes,

    -- 5. Impacto en días totales de inasistencia acumulada
    COALESCE(SUM(j.end_date - j.start_date + 1), 0)::INTEGER                            AS total_absence_days,
    COALESCE(SUM(j.end_date - j.start_date + 1), 0)::INTEGER                            AS total_dias_ausente,

    -- 6. Métricas de alcance de estudiantes (Coders únicos afectados)
    COUNT(DISTINCT j.coder_id)                                                          AS unique_coders_count,
    COUNT(DISTINCT j.coder_id)                                                          AS total_coders

FROM public.justifications j
LEFT JOIN public.coders c ON j.coder_id = c.id
GROUP BY 
    COALESCE(c.route, 'Sin Ruta Asignada'),
    DATE_TRUNC('week', j.start_date)::DATE,
    EXTRACT(WEEK FROM j.start_date)::INTEGER,
    EXTRACT(YEAR FROM j.start_date)::INTEGER
ORDER BY 
    year DESC,
    week_number DESC,
    route ASC;

COMMENT ON VIEW public.v_hse_weekly_summary IS 
'Vista analítica consolidada de novedades e inasistencias agrupadas por ruta formativa y semana académica para el Comité Semanal de HSE y Permanencia [DB-EXT-01].';

-- Índice complementario de soporte para acelerar la agregación semanal
CREATE INDEX IF NOT EXISTS idx_justifications_start_date_coder
    ON public.justifications (start_date, coder_id);
