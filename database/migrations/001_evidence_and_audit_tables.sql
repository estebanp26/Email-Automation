-- =============================================================================
-- MIGRACIÓN DB-02: Normalización del Modelo E-R
-- Tablas de Evidencias y Auditoría de Estados
-- Issue: #13 | Sprint 1 | Épica: EPIC-05
-- Responsables: Sergio, Eliam
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLA: evidence_files
-- Extrae el campo desnormalizado attachments JSONB de justifications
-- hacia una tabla relacional dedicada con integridad referencial.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.evidence_files (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relación con la justificación (ON DELETE CASCADE según criterio de aceptación)
    justification_id UUID NOT NULL
        REFERENCES public.justifications(id) ON DELETE CASCADE,

    -- Metadatos del archivo adjunto
    file_name     VARCHAR(255) NOT NULL,
    file_url      TEXT         NOT NULL,
    mime_type     VARCHAR(100),
    file_size_kb  INTEGER,

    -- Auditoría
    uploaded_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.evidence_files IS
    'Archivos de evidencia adjuntos a una justificación. Normaliza el campo JSONB attachments de justifications.';
COMMENT ON COLUMN public.evidence_files.justification_id IS
    'FK a justifications. Al eliminar la justificación se eliminan en cascada todos sus archivos.';
COMMENT ON COLUMN public.evidence_files.file_url IS
    'URL de acceso al archivo almacenado (Supabase Storage u otro proveedor).';
COMMENT ON COLUMN public.evidence_files.mime_type IS
    'Tipo MIME del archivo (ej: image/jpeg, application/pdf).';
COMMENT ON COLUMN public.evidence_files.file_size_kb IS
    'Tamaño del archivo en kilobytes.';

-- Índices de rendimiento para evidence_files
CREATE INDEX IF NOT EXISTS idx_evidence_files_justification_id
    ON public.evidence_files(justification_id);

CREATE INDEX IF NOT EXISTS idx_evidence_files_uploaded_at
    ON public.evidence_files(uploaded_at DESC);


-- -----------------------------------------------------------------------------
-- TABLA: justification_status_audit
-- Registra cada transición de estado en el ciclo de vida de una justificación.
-- Poblada automáticamente por el trigger trg_justification_status_audit.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.justification_status_audit (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Referencia a la justificación auditada
    justification_id  UUID NOT NULL
        REFERENCES public.justifications(id) ON DELETE CASCADE,

    -- Transición de estado
    previous_status   VARCHAR(30),
    new_status        VARCHAR(30) NOT NULL,

    -- Contexto del cambio
    changed_by_hse_id UUID
        REFERENCES public.hse_users(id) ON DELETE SET NULL,
    change_reason     TEXT,

    -- Auditoría temporal
    changed_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.justification_status_audit IS
    'Historial inmutable de cada transición de validation_status en justifications. Insertado automáticamente por trigger.';
COMMENT ON COLUMN public.justification_status_audit.previous_status IS
    'Estado anterior antes del cambio (NULL si es la primera asignación de estado).';
COMMENT ON COLUMN public.justification_status_audit.new_status IS
    'Nuevo estado tras el cambio (APPROVED, DISAPPROVED o MANUAL_INTERACTION).';
COMMENT ON COLUMN public.justification_status_audit.changed_by_hse_id IS
    'FK al usuario HSE que realizó el cambio. NULL si fue una transición automática por IA.';
COMMENT ON COLUMN public.justification_status_audit.change_reason IS
    'Texto libre opcional para describir el motivo del cambio de estado.';

-- Índices de rendimiento para justification_status_audit
CREATE INDEX IF NOT EXISTS idx_status_audit_justification_id
    ON public.justification_status_audit(justification_id);

CREATE INDEX IF NOT EXISTS idx_status_audit_changed_at
    ON public.justification_status_audit(changed_at DESC);

CREATE INDEX IF NOT EXISTS idx_status_audit_new_status
    ON public.justification_status_audit(new_status);


-- -----------------------------------------------------------------------------
-- TRIGGER: trg_justification_status_audit
-- Se dispara automáticamente en cada UPDATE de validation_status en justifications,
-- insertando un registro en justification_status_audit.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.fn_audit_justification_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo registrar si el campo validation_status cambió efectivamente
    IF OLD.validation_status IS DISTINCT FROM NEW.validation_status THEN
        INSERT INTO public.justification_status_audit (
            justification_id,
            previous_status,
            new_status,
            changed_by_hse_id,
            change_reason,
            changed_at
        ) VALUES (
            NEW.id,
            OLD.validation_status,
            NEW.validation_status,
            NEW.hse_user_id,       -- FK al HSE que actualizó la fila
            NEW.validation_notes,  -- Reutiliza validation_notes como razón del cambio
            CURRENT_TIMESTAMP
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear el trigger sobre justifications
DROP TRIGGER IF EXISTS trg_justification_status_audit ON public.justifications;

CREATE TRIGGER trg_justification_status_audit
AFTER UPDATE OF validation_status ON public.justifications
FOR EACH ROW
EXECUTE FUNCTION public.fn_audit_justification_status();

COMMENT ON FUNCTION public.fn_audit_justification_status() IS
    'Función de trigger que registra en justification_status_audit cada cambio de validation_status en justifications.';


-- -----------------------------------------------------------------------------
-- RLS (Row Level Security) para las nuevas tablas
-- Coherente con la política existente en justifications y hse_users
-- -----------------------------------------------------------------------------
ALTER TABLE public.evidence_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.justification_status_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Permitir lectura de evidence_files a usuarios autenticados"
ON public.evidence_files FOR SELECT TO authenticated USING (true);

CREATE POLICY "Permitir insertar evidence_files a usuarios autenticados"
ON public.evidence_files FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Permitir eliminar evidence_files a usuarios autenticados"
ON public.evidence_files FOR DELETE TO authenticated USING (true);

CREATE POLICY "Permitir lectura de justification_status_audit a usuarios autenticados"
ON public.justification_status_audit FOR SELECT TO authenticated USING (true);
