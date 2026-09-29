-- =============================================================================
-- MIGRACIÓN DB-03: Sincronización de Asistencias Externas y Ausencias Injustificadas
-- Tabla: attendance_records | Vista: v_unjustified_absences
-- Issue / Tarea: [DB-03] | Sprint 2 | Épica: EPIC-05
-- Responsables: Sergio, Eliam
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 0. TIPO ENUM: attendance_status
-- Estados de asistencia provenientes de la plataforma externa
-- -----------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE attendance_status AS ENUM (
        'PRESENT',
        'ABSENT',
        'LATE',
        'EARLY_LEAVE',
        'EXCUSED'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- -----------------------------------------------------------------------------
-- 1. TABLA: attendance_records
-- Almacena los registros sincronizados de asistencia desde la plataforma hermana
-- (Moodle, LMS, control biométrico o API externa).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance_records (
    id VARCHAR(100) PRIMARY KEY DEFAULT gen_random_uuid()::text,

    -- Llaves foráneas obligatorias del negocio
    coder_id VARCHAR(100) NOT NULL REFERENCES coders(id) ON DELETE CASCADE,
    justification_id VARCHAR(100) REFERENCES justifications(id) ON DELETE SET NULL,

    -- Datos de la asistencia externa
    external_attendance_id VARCHAR(255),
    attendance_date DATE NOT NULL,
    session_name VARCHAR(150) NOT NULL DEFAULT 'Jornada Principal',
    status attendance_status NOT NULL DEFAULT 'ABSENT',
    
    -- Indicador y trazabilidad de justificación
    is_justified BOOLEAN NOT NULL DEFAULT FALSE,
    source_platform VARCHAR(100) NOT NULL DEFAULT 'PLATAFORMA_HERMANA',
    synced_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadatos y payload crudo del proveedor externo
    raw_data JSONB,
    
    -- Auditoría temporal
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Restricción para evitar duplicados del mismo coder, fecha y sesión
    CONSTRAINT uq_coder_attendance_session UNIQUE (coder_id, attendance_date, session_name),
    CONSTRAINT chk_attendance_date CHECK (attendance_date <= CURRENT_DATE + INTERVAL '1 day')
);

COMMENT ON TABLE attendance_records IS 'Registros de asistencia sincronizados desde la plataforma hermana (Moodle/LMS) con enlace a coders y justificaciones.';
COMMENT ON COLUMN attendance_records.coder_id IS 'FK a coders.id. Identifica al estudiante al que pertenece la asistencia.';
COMMENT ON COLUMN attendance_records.justification_id IS 'FK a justifications.id. NULL si la inasistencia no ha sido justificada; referenciado cuando existe excusa.';
COMMENT ON COLUMN attendance_records.is_justified IS 'Bandera booleana rápida que indica si la inasistencia o tardanza cuenta con soporte justificado.';
COMMENT ON COLUMN attendance_records.status IS 'Estado de asistencia: PRESENT, ABSENT, LATE, EARLY_LEAVE, EXCUSED.';
COMMENT ON COLUMN attendance_records.source_platform IS 'Nombre o identificador del sistema origen (ej: MOODLE, PLATAFORMA_HERMANA, BIOMETRICO).';

-- Índices de rendimiento
CREATE INDEX IF NOT EXISTS idx_attendance_records_coder_id ON attendance_records(coder_id);
CREATE INDEX IF NOT EXISTS idx_attendance_records_justification_id ON attendance_records(justification_id);
CREATE INDEX IF NOT EXISTS idx_attendance_records_date ON attendance_records(attendance_date DESC);
CREATE INDEX IF NOT EXISTS idx_attendance_records_status ON attendance_records(status);
CREATE INDEX IF NOT EXISTS idx_attendance_records_is_justified ON attendance_records(is_justified);
CREATE INDEX IF NOT EXISTS idx_attendance_records_coder_date ON attendance_records(coder_id, attendance_date);
CREATE INDEX IF NOT EXISTS idx_attendance_records_raw_data ON attendance_records USING GIN (raw_data);

-- -----------------------------------------------------------------------------
-- 2. TRIGGER: Actualización automática de updated_at
-- -----------------------------------------------------------------------------
CREATE TRIGGER trg_attendance_records_updated_at
BEFORE UPDATE ON attendance_records
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- -----------------------------------------------------------------------------
-- 3. TRIGGER: Sincronización Automática entre Inasistencias y Justificaciones
-- Cuando una inasistencia se inserta o actualiza, busca automáticamente si existe
-- una justificación APROBADA para ese coder en esa fecha.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_auto_link_attendance_to_justification()
RETURNS TRIGGER AS $$
DECLARE
    v_just_id VARCHAR(100);
BEGIN
    -- Si ya tiene justificación asignada y aprobada, marcar is_justified
    IF NEW.justification_id IS NOT NULL THEN
        NEW.is_justified := TRUE;
        IF NEW.status = 'ABSENT' THEN
            NEW.status := 'EXCUSED';
        END IF;
        RETURN NEW;
    END IF;

    -- Si es una inasistencia o tardanza sin justificación explícita, buscar en justifications
    IF NEW.status IN ('ABSENT', 'LATE', 'EARLY_LEAVE') THEN
        SELECT j.id INTO v_just_id
        FROM justifications j
        WHERE j.coder_id = NEW.coder_id
          AND j.validation_status = 'APPROVED'
          AND NEW.attendance_date BETWEEN j.start_date AND j.end_date
        LIMIT 1;

        IF v_just_id IS NOT NULL THEN
            NEW.justification_id := v_just_id;
            NEW.is_justified := TRUE;
            IF NEW.status = 'ABSENT' THEN
                NEW.status := 'EXCUSED';
            END IF;
        ELSE
            NEW.is_justified := FALSE;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_attendance_records_auto_link ON attendance_records;
CREATE TRIGGER trg_attendance_records_auto_link
BEFORE INSERT OR UPDATE ON attendance_records
FOR EACH ROW
EXECUTE FUNCTION fn_auto_link_attendance_to_justification();

-- -----------------------------------------------------------------------------
-- 4. TRIGGER RECÍPROCO: Cuando una justificación pasa a APPROVED
-- Actualiza automáticamente las inasistencias del coder cubiertas por esa fecha.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_sync_approved_justification_to_attendance()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.validation_status = 'APPROVED' AND (OLD.validation_status IS DISTINCT FROM 'APPROVED') THEN
        UPDATE attendance_records
        SET 
            justification_id = NEW.id,
            is_justified = TRUE,
            status = CASE WHEN status = 'ABSENT' THEN 'EXCUSED'::attendance_status ELSE status END,
            updated_at = CURRENT_TIMESTAMP
        WHERE coder_id = NEW.coder_id
          AND attendance_date BETWEEN NEW.start_date AND NEW.end_date
          AND (justification_id IS NULL OR justification_id = NEW.id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_justification_approved_sync_attendance ON justifications;
CREATE TRIGGER trg_justification_approved_sync_attendance
AFTER UPDATE OF validation_status ON justifications
FOR EACH ROW
EXECUTE FUNCTION fn_sync_approved_justification_to_attendance();

-- -----------------------------------------------------------------------------
-- 5. VISTA UNIFICADA: v_unjustified_absences
-- Identifica todas las inasistencias de coders que aún NO cuentan con
-- una justificación radicada y aprobada en el sistema.
-- Incluye detección de si existe alguna solicitud de justificación en trámite
-- (MANUAL_INTERACTION, REVISION_MANUAL, POSIBLEMENTE_VALIDO, etc.).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_unjustified_absences
WITH (security_invoker = true) AS
SELECT 
    ar.id AS attendance_id,
    ar.coder_id,
    c.full_name AS coder_name,
    c.cedula AS coder_cedula,
    c.email AS coder_email,
    c.route AS coder_route,
    ar.attendance_date,
    ar.session_name,
    ar.status AS attendance_status,
    ar.source_platform,
    (CURRENT_DATE - ar.attendance_date) AS days_unjustified,
    
    -- Detección de justificaciones en trámite (no aprobadas aún)
    CASE 
        WHEN pj.id IS NOT NULL THEN TRUE 
        ELSE FALSE 
    END AS has_pending_justification,
    pj.id AS pending_justification_id,
    pj.validation_status AS pending_validation_status,
    pj.email_subject AS pending_justification_subject,
    pj.ai_reason AS pending_justification_reason,
    
    ar.synced_at,
    ar.created_at
FROM attendance_records ar
INNER JOIN coders c ON ar.coder_id = c.id
-- Subconsulta para ubicar justificaciones pendientes en trámite
LEFT JOIN LATERAL (
    SELECT j.id, j.validation_status, j.email_subject, j.ai_reason
    FROM justifications j
    WHERE j.coder_id = ar.coder_id
      AND j.validation_status NOT IN ('APPROVED', 'DISAPPROVED')
      AND ar.attendance_date BETWEEN j.start_date AND j.end_date
    ORDER BY j.created_at DESC
    LIMIT 1
) pj ON true
WHERE ar.is_justified = FALSE
  AND ar.status IN ('ABSENT', 'LATE', 'EARLY_LEAVE')
  -- Garantizar que no exista ninguna justificación aprobada vigente
  AND NOT EXISTS (
      SELECT 1 
      FROM justifications j 
      WHERE j.coder_id = ar.coder_id 
        AND j.validation_status = 'APPROVED'
        AND ar.attendance_date BETWEEN j.start_date AND j.end_date
  );

COMMENT ON VIEW v_unjustified_absences IS 'Vista unificada de inasistencias y tardanzas sin justificación radicada, con alerta de solicitudes en trámite.';

-- -----------------------------------------------------------------------------
-- 6. POLÍTICAS RLS (Row Level Security) para attendance_records
-- Consistente con el modelo RBAC de DB-01
-- -----------------------------------------------------------------------------
ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_records FORCE ROW LEVEL SECURITY;

-- SELECT: Staff HSE y Admin ven todas; Coders solo ven sus propios registros
CREATE POLICY p_attendance_records_select ON attendance_records
FOR SELECT
USING (
    fn_check_user_role('HSE_ANALYST')
    OR fn_get_current_user_role() IN ('HSE_ANALYST', 'HSE', 'TEAM_LEADER', 'ADMIN')
    OR (CURRENT_USER IN ('postgres', 'hse_admin') AND fn_get_current_user_role() IS NULL)
    OR (
        (fn_get_current_user_role() = 'CODER' OR fn_get_current_user_role() IS NULL)
        AND (
            coder_id = fn_get_current_user_id()
            OR coder_id IN (
                SELECT su.coder_id 
                FROM system_users su 
                WHERE (su.id = fn_get_current_user_id() OR su.email = fn_get_current_user_id())
                  AND su.coder_id IS NOT NULL
            )
        )
    )
);

-- INSERT / UPDATE: Solo personal administrativo o servicios backend autorizados
CREATE POLICY p_attendance_records_insert ON attendance_records
FOR INSERT
WITH CHECK (
    fn_check_user_role('HSE_ANALYST')
    OR fn_get_current_user_role() IN ('HSE_ANALYST', 'HSE', 'TEAM_LEADER', 'ADMIN')
    OR (CURRENT_USER IN ('postgres', 'hse_admin') AND fn_get_current_user_role() IS NULL)
);

CREATE POLICY p_attendance_records_update ON attendance_records
FOR UPDATE
USING (
    fn_check_user_role('HSE_ANALYST')
    OR fn_get_current_user_role() IN ('HSE_ANALYST', 'HSE', 'TEAM_LEADER', 'ADMIN')
    OR (CURRENT_USER IN ('postgres', 'hse_admin') AND fn_get_current_user_role() IS NULL)
);
