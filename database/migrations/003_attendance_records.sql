-- =============================================================================
-- MIGRACIÓN DB-03: Tabla y Vistas de Sincronización de Asistencias Externas
-- Issue: #20 | Sprint 2 | Épica: EPIC-05
-- Responsables: Sergio, Eliam
-- Dependencias: Bloqueado por DB-01 (coders, justifications deben existir)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLA: attendance_records
-- Almacena los registros de asistencia sincronizados desde la plataforma hermana.
-- Vinculada a coders y opcionalmente a justifications cuando existe excusa radicada.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.attendance_records (
    id                  VARCHAR(100) PRIMARY KEY DEFAULT gen_random_uuid()::text,

    -- Relación con el coder (obligatoria)
    coder_id            VARCHAR(100) NOT NULL
        REFERENCES public.coders(id) ON DELETE CASCADE,

    -- Relación opcional con justificación radicada
    justification_id    VARCHAR(100)
        REFERENCES public.justifications(id) ON DELETE SET NULL,

    -- Datos del registro de asistencia
    attendance_date     DATE          NOT NULL,
    session_type        VARCHAR(50)   NOT NULL DEFAULT 'CLASE',   -- CLASE, TALLER, EVALUACION, etc.
    status              VARCHAR(30)   NOT NULL DEFAULT 'AUSENTE', -- PRESENTE, AUSENTE, TARDANZA, EXCUSADO

    -- Origen del registro (plataforma hermana / sincronización externa)
    source_platform     VARCHAR(100),
    external_record_id  VARCHAR(255),                             -- ID en la plataforma de origen

    -- Auditoría
    synced_at           TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Evitar duplicados: un coder no puede tener dos registros el mismo día para la misma sesión
    CONSTRAINT uq_attendance_coder_date_session UNIQUE (coder_id, attendance_date, session_type),

    -- Restricciones de dominio
    CONSTRAINT chk_attendance_status CHECK (
        status IN ('PRESENTE', 'AUSENTE', 'TARDANZA', 'EXCUSADO')
    ),
    CONSTRAINT chk_session_type CHECK (
        session_type IN ('CLASE', 'TALLER', 'EVALUACION', 'OTRO')
    )
);

COMMENT ON TABLE public.attendance_records IS
    'Registros de asistencia sincronizados desde la plataforma hermana. Vincula coders con sus inasistencias y excusas radicadas.';
COMMENT ON COLUMN public.attendance_records.coder_id IS
    'FK obligatoria al coder. Al eliminar un coder se eliminan sus registros en cascada.';
COMMENT ON COLUMN public.attendance_records.justification_id IS
    'FK opcional a justifications. Se asigna cuando existe una excusa radicada para esta inasistencia.';
COMMENT ON COLUMN public.attendance_records.status IS
    'Estado del registro: PRESENTE, AUSENTE, TARDANZA o EXCUSADO (cuando justification_id está asignado).';
COMMENT ON COLUMN public.attendance_records.source_platform IS
    'Nombre de la plataforma de origen desde donde se sincronizó el registro (ej: Moodle, SIA).';
COMMENT ON COLUMN public.attendance_records.external_record_id IS
    'Identificador del registro en la plataforma externa para trazabilidad y evitar duplicados en re-sincronización.';

-- Trigger para actualizar updated_at automáticamente
CREATE TRIGGER trg_attendance_records_updated_at
BEFORE UPDATE ON public.attendance_records
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();

-- Triggers de sincronización automática bidireccional
CREATE OR REPLACE FUNCTION public.fn_auto_link_attendance_to_justification()
RETURNS TRIGGER AS $$
DECLARE
    v_just_id VARCHAR(100);
BEGIN
    IF NEW.justification_id IS NOT NULL THEN
        IF NEW.status = 'AUSENTE' THEN
            NEW.status := 'EXCUSADO';
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.status = 'AUSENTE' THEN
        SELECT j.id INTO v_just_id
        FROM public.justifications j
        WHERE j.coder_id = NEW.coder_id
          AND NEW.attendance_date BETWEEN j.start_date AND j.end_date
          AND j.validation_status = 'APPROVED'
        ORDER BY j.created_at DESC
        LIMIT 1;

        IF v_just_id IS NOT NULL THEN
            NEW.justification_id := v_just_id;
            NEW.status := 'EXCUSADO';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_attendance_records_auto_link ON public.attendance_records;
CREATE TRIGGER trg_attendance_records_auto_link
BEFORE INSERT OR UPDATE OF coder_id, attendance_date, status ON public.attendance_records
FOR EACH ROW
EXECUTE FUNCTION public.fn_auto_link_attendance_to_justification();

CREATE OR REPLACE FUNCTION public.fn_sync_approved_justification_to_attendance()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.validation_status = 'APPROVED' AND (OLD.validation_status IS NULL OR OLD.validation_status != 'APPROVED') THEN
        UPDATE public.attendance_records
        SET justification_id = NEW.id,
            status = 'EXCUSADO',
            updated_at = CURRENT_TIMESTAMP
        WHERE coder_id = NEW.coder_id
          AND attendance_date BETWEEN NEW.start_date AND NEW.end_date
          AND status = 'AUSENTE';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_justification_approved_attendance ON public.justifications;
CREATE TRIGGER trg_sync_justification_approved_attendance
AFTER UPDATE OF validation_status ON public.justifications
FOR EACH ROW
EXECUTE FUNCTION public.fn_sync_approved_justification_to_attendance();

-- Índices de rendimiento
CREATE INDEX IF NOT EXISTS idx_attendance_coder_id
    ON public.attendance_records(coder_id);

CREATE INDEX IF NOT EXISTS idx_attendance_date
    ON public.attendance_records(attendance_date DESC);

CREATE INDEX IF NOT EXISTS idx_attendance_status
    ON public.attendance_records(status);

CREATE INDEX IF NOT EXISTS idx_attendance_justification_id
    ON public.attendance_records(justification_id);

CREATE INDEX IF NOT EXISTS idx_attendance_synced_at
    ON public.attendance_records(synced_at DESC);


-- -----------------------------------------------------------------------------
-- VISTA: v_unjustified_absences
-- Identifica inasistencias (status = AUSENTE) que aún no cuentan con una
-- justificación radicada (justification_id IS NULL).
-- Útil para el dashboard HSE y reportes de seguimiento.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.v_unjustified_absences
WITH (security_invoker = true) AS
SELECT
    ar.id                                               AS record_id,
    ar.attendance_date,
    ar.session_type,
    ar.status,
    ar.source_platform,
    ar.external_record_id,
    ar.synced_at,

    -- Datos del coder
    c.id                                                AS coder_id,
    c.full_name                                         AS coder_name,
    c.email                                             AS coder_email,
    c.cedula                                            AS coder_cedula,
    c.route                                             AS coder_route,
    c.is_active                                         AS coder_is_active,

    -- Días transcurridos sin justificación
    CURRENT_DATE - ar.attendance_date                   AS days_without_justification,

    -- Alerta si existe una justificación en trámite (revisión manual o pendiente)
    CASE 
        WHEN pj.id IS NOT NULL THEN TRUE 
        ELSE FALSE 
    END                                                 AS has_pending_justification,
    pj.id                                               AS pending_justification_id,
    pj.validation_status                                AS pending_justification_status

FROM public.attendance_records ar
INNER JOIN public.coders c ON ar.coder_id = c.id
LEFT JOIN LATERAL (
    SELECT j.id, j.validation_status
    FROM public.justifications j
    WHERE j.coder_id = ar.coder_id
      AND ar.attendance_date BETWEEN j.start_date AND j.end_date
      AND j.validation_status NOT IN ('APPROVED', 'DISAPPROVED')
    ORDER BY j.created_at DESC
    LIMIT 1
) pj ON TRUE
WHERE
    ar.status = 'AUSENTE'
    AND ar.justification_id IS NULL
    AND c.is_active = TRUE
ORDER BY
    ar.attendance_date DESC,
    c.full_name ASC;

COMMENT ON VIEW public.v_unjustified_absences IS
    'Vista unificada de inasistencias sin justificación radicada. Filtra registros AUSENTE sin justification_id asignado para coders activos.';


-- -----------------------------------------------------------------------------
-- RLS (Row Level Security) — coherente con políticas existentes
-- -----------------------------------------------------------------------------
ALTER TABLE public.attendance_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Permitir lectura de attendance_records a usuarios autenticados"
ON public.attendance_records FOR SELECT TO authenticated USING (true);

CREATE POLICY "Permitir insertar attendance_records a usuarios autenticados"
ON public.attendance_records FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Permitir actualizar attendance_records a usuarios autenticados"
ON public.attendance_records FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Permitir eliminar attendance_records a usuarios autenticados"
ON public.attendance_records FOR DELETE TO authenticated USING (true);

