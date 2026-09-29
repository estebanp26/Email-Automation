-- =============================================================================
-- MIGRACIÓN DB-04: Índices de Rendimiento y Tuning para Consultas del Dashboard
-- Issue / Tarea: [DB-04] | Sprint 3 | Épica: EPIC-05
-- Responsables: Eliam (eliam-riwi), Sergio (sergio)
-- Dependencias: Bloqueado por [DB-02] (evidence_files y justifications)
-- =============================================================================
-- Objetivo:
-- Configurar índices B-Tree compuestos sobre justifications (coder_id, created_at DESC)
-- y (validation_status, start_date), así como índices especializados GIN sobre los
-- metadatos JSONB de coordenadas espaciales (ocr_spatial_data / spatial_boxes) para
-- asegurar tiempos de respuesta inferiores a 50 ms en las consultas del dashboard HSE
-- con más de 10,000 registros.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. SOPORTE DE COLUMNAS DE COORDENADAS ESPACIALES OCR (Strata Core)
-- -----------------------------------------------------------------------------
-- Garantizar existencia de ocr_spatial_data en evidence_files y justifications
ALTER TABLE public.evidence_files
    ADD COLUMN IF NOT EXISTS ocr_spatial_data JSONB;

COMMENT ON COLUMN public.evidence_files.ocr_spatial_data IS
    'Metadatos y coordenadas espaciales OCR generados por Strata Core / PyMuPDF para análisis de bounding boxes.';

ALTER TABLE public.justifications
    ADD COLUMN IF NOT EXISTS ocr_spatial_data JSONB;

COMMENT ON COLUMN public.justifications.ocr_spatial_data IS
    'Caché consolidado de coordenadas espaciales OCR de los documentos de soporte evaluados.';


-- -----------------------------------------------------------------------------
-- 2. ÍNDICES B-TREE COMPUESTOS REQUERIDOS (Consultas Frecuentes Dashboard HSE)
-- -----------------------------------------------------------------------------

-- 2.1. Consulta de historial por estudiante ordenado cronológicamente
-- Utilizado en la ficha del coder y vista de justificaciones del estudiante
CREATE INDEX IF NOT EXISTS idx_justifications_coder_created_desc
    ON public.justifications (coder_id, created_at DESC);

-- 2.2. Filtro principal de bandeja de entrada por estado y fecha de inasistencia
-- Utilizado en filtros de rango del Dashboard: "Mostrar REVISION_MANUAL del último mes"
CREATE INDEX IF NOT EXISTS idx_justifications_status_start_date
    ON public.justifications (validation_status, start_date DESC);

-- 2.3. Búsqueda y conciliación de solapamiento de fechas por estudiante
-- Optimiza la verificación de inasistencias y vinculación automática con attendance_records
CREATE INDEX IF NOT EXISTS idx_justifications_coder_dates
    ON public.justifications (coder_id, start_date, end_date);

-- 2.4. Filtro analítico por recomendación de IA y estado operativo
-- Optimiza métricas y embudos de triaje (POSIBLEMENTE_VALIDO, POSIBLEMENTE_INVALIDO, etc.)
CREATE INDEX IF NOT EXISTS idx_justifications_ai_rec_status
    ON public.justifications (ai_recommendation, validation_status);


-- -----------------------------------------------------------------------------
-- 3. ÍNDICES ESPECIALIZADOS GIN SOBRE METADATOS JSONB (Coordenadas Espaciales)
-- -----------------------------------------------------------------------------

-- 3.1. Índice GIN sobre ocr_spatial_data en evidence_files (búsquedas por atributo/box)
CREATE INDEX IF NOT EXISTS idx_evidence_files_ocr_spatial_data_gin
    ON public.evidence_files USING GIN (ocr_spatial_data);

-- 3.2. Índice GIN sobre spatial_boxes en evidence_files
CREATE INDEX IF NOT EXISTS idx_evidence_files_spatial_boxes_gin
    ON public.evidence_files USING GIN (spatial_boxes);

-- 3.3. Índice GIN sobre ocr_spatial_data en justifications
CREATE INDEX IF NOT EXISTS idx_justifications_ocr_spatial_data_gin
    ON public.justifications USING GIN (ocr_spatial_data);


-- -----------------------------------------------------------------------------
-- 4. ÍNDICES PARCIALES DE ALTO RENDIMIENTO (Tuning < 50ms para 10,000+ filas)
-- -----------------------------------------------------------------------------

-- 4.1. Cola de triaje activa (Solo registros que requieren acción o decisión HSE)
-- Excluye solicitudes ya resueltas (APPROVED / DISAPPROVED) reduciendo el tamaño del índice en un ~85%
CREATE INDEX IF NOT EXISTS idx_justifications_pending_triage
    ON public.justifications (created_at DESC)
    WHERE validation_status IN (
        'REVISION_MANUAL',
        'POSIBLEMENTE_VALIDO',
        'POSIBLEMENTE_INVALIDO',
        'PENDIENTE_DECISION_TL',
        'MANUAL_INTERACTION'
    );

-- 4.2. Bandeja de entrada sin intervención humana aún (Fila de espera para primer triaje)
CREATE INDEX IF NOT EXISTS idx_justifications_unreviewed
    ON public.justifications (received_at DESC)
    WHERE has_human_intervention = FALSE;

-- 4.3. Índice parcial para la vista v_unjustified_absences en attendance_records
-- Optimiza drásticamente el reporte de ausencias sin justificar
CREATE INDEX IF NOT EXISTS idx_attendance_unjustified_active
    ON public.attendance_records (attendance_date DESC, coder_id)
    WHERE status = 'AUSENTE' AND justification_id IS NULL;


-- -----------------------------------------------------------------------------
-- 5. ACTUALIZACIÓN DEL TRIGGER DE SINCRONIZACIÓN DE EVIDENCIAS
-- -----------------------------------------------------------------------------
-- Asegurar que al insertar en evidence_files, ocr_spatial_data también se copie al JSONB attachments
CREATE OR REPLACE FUNCTION public.fn_sync_evidence_file_to_attachments()
RETURNS TRIGGER AS $$
DECLARE
    v_attachment_obj JSONB;
BEGIN
    v_attachment_obj := jsonb_build_object(
        'id', NEW.id,
        'file_name', NEW.file_name,
        'file_url', NEW.file_url,
        'file_path', NEW.file_path,
        'mime_type', NEW.mime_type,
        'file_size_bytes', NEW.file_size_bytes,
        'extracted_text', NEW.extracted_text,
        'spatial_boxes', NEW.spatial_boxes,
        'ocr_spatial_data', NEW.ocr_spatial_data,
        'created_at', NEW.created_at
    );

    UPDATE public.justifications
    SET attachments = COALESCE(attachments, '[]'::jsonb) || jsonb_build_array(v_attachment_obj),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.justification_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
