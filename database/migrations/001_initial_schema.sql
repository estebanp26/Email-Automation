-- =============================================================================
-- SISTEMA DE AUTOMATIZACIÓN DE JUSTIFICACIONES RIWI / HSE
-- Script DDL de Base de Datos PostgreSQL — Migración 001
-- Módulo: DB-01 — RBAC, Funciones de Rol, system_users, evidence_files y RLS
-- Versión: 2.2
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- 0. TIPOS ENUM DE ROLES (RBAC)
-- =============================================================================
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM (
        'CODER',
        'HSE_ANALYST',
        'TEAM_LEADER',
        'ADMIN',
        'HSE'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Limpieza previa en orden de dependencia
DROP VIEW IF EXISTS v_justifications_dashboard CASCADE;
DROP TABLE IF EXISTS evidence_files CASCADE;
DROP TABLE IF EXISTS justifications CASCADE;
DROP TABLE IF EXISTS system_users CASCADE;
DROP TABLE IF EXISTS hse_users CASCADE;
DROP TABLE IF EXISTS coders CASCADE;

-- =============================================================================
-- 1. TABLA coders (Catálogo Maestro de Estudiantes)
-- =============================================================================
CREATE TABLE coders (
    id VARCHAR(100) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    cedula VARCHAR(30) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    route VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE coders IS 'Catálogo maestro de estudiantes (coders) activos e inactivos en RIWI';
COMMENT ON COLUMN coders.cedula IS 'Documento nacional de identificación del coder (único)';
COMMENT ON COLUMN coders.email IS 'Correo electrónico institucional o principal registrado';
COMMENT ON COLUMN coders.route IS 'Ruta de formación técnica en la que está asignado';

-- =============================================================================
-- 2. TABLA hse_users (Compatibilidad heredada de autenticación directa HSE)
-- =============================================================================
CREATE TABLE hse_users (
    id VARCHAR(100) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'HSE',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ,
    CONSTRAINT chk_hse_role CHECK (role IN ('HSE', 'HSE_ANALYST', 'TEAM_LEADER', 'ADMIN'))
);

COMMENT ON TABLE hse_users IS 'Usuarios administrativos de HSE y coordinadores con acceso al panel web';
COMMENT ON COLUMN hse_users.password_hash IS 'Hash seguro de contraseña (bcrypt / argon2) para login directo en frontend';
COMMENT ON COLUMN hse_users.role IS 'Rol administrativo con permisos en el dashboard web';

-- =============================================================================
-- 3. TABLA system_users (Núcleo Unificado de Autenticación y RBAC)
-- =============================================================================
CREATE TABLE system_users (
    id VARCHAR(100) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    full_name VARCHAR(150) NOT NULL,
    role user_role NOT NULL DEFAULT 'CODER',
    coder_id VARCHAR(100) REFERENCES coders(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ
);

COMMENT ON TABLE system_users IS 'Tabla unificada de usuarios del sistema y RBAC (Coders, HSE Analysts, TL, Admins)';
COMMENT ON COLUMN system_users.role IS 'Rol asignado: CODER, HSE_ANALYST, TEAM_LEADER, ADMIN';
COMMENT ON COLUMN system_users.coder_id IS 'Vinculación a la entidad coder en caso de usuarios con rol CODER';

-- =============================================================================
-- 4. TABLA justifications (Transaccional de Inasistencias y Evaluaciones)
-- =============================================================================
CREATE TABLE justifications (
    id VARCHAR(100) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    
    -- Relaciones
    coder_id VARCHAR(100) REFERENCES coders(id) ON DELETE SET NULL,
    hse_user_id VARCHAR(100) REFERENCES hse_users(id) ON DELETE SET NULL,
    
    -- Datos del correo entrante
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(150),
    email_subject TEXT NOT NULL,
    email_body TEXT NOT NULL,
    email_url TEXT,
    message_id VARCHAR(255) NOT NULL UNIQUE,
    conversation_id VARCHAR(255),
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Clasificación e Intención (Corregible por HSE)
    intent VARCHAR(100) DEFAULT 'EXCUSA',
    excuse_type VARCHAR(100) NOT NULL DEFAULT 'no_identificado',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    
    -- Inteligencia Artificial (Strata Core / Qwen 2.5)
    ai_confidence NUMERIC(5,4),
    ai_reason TEXT,
    ai_response JSONB,
    ai_model VARCHAR(100) DEFAULT 'qwen2.5:1.5b',
    
    -- Asistencia Analítica Preliminar (Strata Core AI)
    ai_recommendation VARCHAR(30) NOT NULL DEFAULT 'REVISION_MANUAL',
    
    -- Estados del Ciclo de Vida y Diferenciador de Resolución
    coder_identification_status VARCHAR(30) NOT NULL DEFAULT 'IDENTIFIED',
    validation_status VARCHAR(30) NOT NULL DEFAULT 'REVISION_MANUAL',
    validation_notes TEXT,
    
    -- FACTOR DIFERENCIADOR DE INTERVENCIÓN HUMANA
    resolution_mode VARCHAR(20) NOT NULL DEFAULT 'AUTOMATIC_AI',
    has_human_intervention BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Auditoría de Gestión Humana (HSE)
    hse_decision VARCHAR(30),
    hse_notes TEXT,
    hse_reviewed_at TIMESTAMPTZ,
    
    -- Adjuntos y Auditoría
    attachments JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Restricciones de Dominio
    CONSTRAINT chk_coder_ident_status CHECK (
        coder_identification_status IN ('IDENTIFIED', 'CODER_NOT_FOUND')
    ),
    CONSTRAINT chk_ai_recommendation CHECK (
        ai_recommendation IN ('POSIBLEMENTE_VALIDO', 'POSIBLEMENTE_INVALIDO', 'REVISION_MANUAL')
    ),
    CONSTRAINT chk_validation_status CHECK (
        validation_status IN ('POSIBLEMENTE_VALIDO', 'POSIBLEMENTE_INVALIDO', 'REVISION_MANUAL', 'APPROVED', 'DISAPPROVED', 'MANUAL_INTERACTION', 'PENDIENTE_DECISION_TL')
    ),
    CONSTRAINT chk_resolution_mode CHECK (
        resolution_mode IN ('AUTOMATIC_AI', 'MANUAL_HSE')
    ),
    CONSTRAINT chk_hse_decision CHECK (
        hse_decision IS NULL OR hse_decision IN ('APPROVED', 'DISAPPROVED', 'REQUEST_CORRECTION')
    ),
    CONSTRAINT chk_dates_validity CHECK (end_date >= start_date)
);

COMMENT ON TABLE justifications IS 'Historial centralizado de correos y justificaciones de inasistencia';
COMMENT ON COLUMN justifications.coder_id IS 'FK al coder. Modificable/vinculable manualmente por HSE';
COMMENT ON COLUMN justifications.validation_status IS 'Estado del registro: APPROVED, DISAPPROVED o MANUAL_INTERACTION';
COMMENT ON COLUMN justifications.resolution_mode IS 'Diferenciador de origen de resolución: AUTOMATIC_AI o MANUAL_HSE';
COMMENT ON COLUMN justifications.has_human_intervention IS 'Indica si un usuario de HSE realizó modificaciones o validaciones';
COMMENT ON COLUMN justifications.email_url IS 'Enlace directo para visualización del correo en el cliente web';
COMMENT ON COLUMN justifications.ai_response IS 'JSON completo devuelto por Strata Core para auditoría avanzada';

-- =============================================================================
-- 5. TABLA evidence_files (Archivos de Evidencia y Soportes Adjuntos)
-- =============================================================================
CREATE TABLE evidence_files (
    id VARCHAR(100) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    justification_id VARCHAR(100) NOT NULL REFERENCES justifications(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    file_path TEXT,
    mime_type VARCHAR(100),
    file_size_bytes BIGINT,
    extracted_text TEXT,
    spatial_boxes JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE evidence_files IS 'Archivos de soporte/evidencia documental asociados a justificaciones con coordenadas de Strata Core';
COMMENT ON COLUMN evidence_files.justification_id IS 'FK a justifications.id';
COMMENT ON COLUMN evidence_files.spatial_boxes IS 'Coordenadas espaciales (rects) de OCR/PyMuPDF para resaltado en visor web';

-- =============================================================================
-- 6. ÍNDICES DE RENDIMIENTO (Performance Tuning)
-- =============================================================================
CREATE INDEX idx_coders_email ON coders(email);
CREATE INDEX idx_coders_cedula ON coders(cedula);
CREATE INDEX idx_coders_active ON coders(is_active);

CREATE INDEX idx_system_users_email ON system_users(email);
CREATE INDEX idx_system_users_role ON system_users(role);
CREATE INDEX idx_system_users_coder_id ON system_users(coder_id);

CREATE INDEX idx_justifications_status_created ON justifications(validation_status, created_at DESC);
CREATE INDEX idx_justifications_ai_rec ON justifications(ai_recommendation);
CREATE INDEX idx_justifications_resolution_mode ON justifications(resolution_mode);
CREATE INDEX idx_justifications_human_interv ON justifications(has_human_intervention);
CREATE INDEX idx_justifications_coder_id ON justifications(coder_id);
CREATE INDEX idx_justifications_hse_user_id ON justifications(hse_user_id);
CREATE INDEX idx_justifications_sender_email ON justifications(sender_email);
CREATE INDEX idx_justifications_received_at ON justifications(received_at DESC);
CREATE INDEX idx_justifications_message_id ON justifications(message_id);
CREATE INDEX idx_justifications_ai_response ON justifications USING GIN (ai_response);
CREATE INDEX idx_justifications_attachments ON justifications USING GIN (attachments);

CREATE INDEX idx_evidence_files_justification_id ON evidence_files(justification_id);
CREATE INDEX idx_evidence_files_created_at ON evidence_files(created_at DESC);

-- =============================================================================
-- 7. FUNCIONES DE CONVENIENCIA Y GESTIÓN DE ROLES / SESIÓN (RBAC)
-- =============================================================================

-- 7.1. Establecer contexto de autenticación de sesión (Testing y llamadas directas)
CREATE OR REPLACE FUNCTION fn_set_auth_context(
    p_user_id TEXT,
    p_role TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_role TEXT := UPPER(p_role);
BEGIN
    PERFORM set_config('app.current_user_id', p_user_id, false);
    PERFORM set_config('request.jwt.claim.sub', p_user_id, false);
    
    IF v_role IS NOT NULL THEN
        PERFORM set_config('app.current_user_role', v_role, false);
    ELSE
        -- Buscar rol en system_users
        SELECT su.role::text INTO v_role
        FROM system_users su
        WHERE su.id = p_user_id OR su.email = p_user_id
        LIMIT 1;

        IF v_role IS NULL THEN
            IF EXISTS (SELECT 1 FROM coders c WHERE c.id = p_user_id OR c.email = p_user_id) THEN
                v_role := 'CODER';
            ELSE
                SELECT hu.role::text INTO v_role
                FROM hse_users hu
                WHERE hu.id = p_user_id OR hu.email = p_user_id
                LIMIT 1;
            END IF;
        END IF;

        IF v_role IS NOT NULL THEN
            PERFORM set_config('app.current_user_role', UPPER(v_role), false);
        END IF;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 7.2. Obtener el ID del usuario actualmente autenticado
CREATE OR REPLACE FUNCTION fn_get_current_user_id()
RETURNS TEXT AS $$
BEGIN
    -- 1. Variable de sesión app.current_user_id
    IF NULLIF(current_setting('app.current_user_id', true), '') IS NOT NULL THEN
        RETURN current_setting('app.current_user_id', true);
    END IF;

    -- 2. Claim sub de JWT en Supabase
    IF NULLIF(current_setting('request.jwt.claim.sub', true), '') IS NOT NULL THEN
        RETURN current_setting('request.jwt.claim.sub', true);
    END IF;

    -- 3. Parsing de request.jwt.claims si está en formato JSON
    BEGIN
        IF NULLIF(current_setting('request.jwt.claims', true), '') IS NOT NULL THEN
            RETURN (current_setting('request.jwt.claims', true)::jsonb ->> 'sub');
        END IF;
    EXCEPTION WHEN OTHERS THEN
        NULL;
    END;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- 7.3. Obtener el Rol del usuario actualmente autenticado
CREATE OR REPLACE FUNCTION fn_get_current_user_role()
RETURNS TEXT AS $$
DECLARE
    v_role TEXT;
    v_uid TEXT;
BEGIN
    -- 1. Variable explícita de rol en sesión
    v_role := NULLIF(current_setting('app.current_user_role', true), '');
    IF v_role IS NOT NULL THEN
        IF UPPER(v_role) = 'HSE' THEN
            RETURN 'HSE_ANALYST';
        END IF;
        RETURN UPPER(v_role);
    END IF;

    -- 2. Claims de JWT
    BEGIN
        IF NULLIF(current_setting('request.jwt.claims', true), '') IS NOT NULL THEN
            v_role := current_setting('request.jwt.claims', true)::jsonb ->> 'role';
            IF v_role IS NOT NULL AND v_role NOT IN ('authenticated', 'anon') THEN
                RETURN UPPER(v_role);
            END IF;
            v_role := current_setting('request.jwt.claims', true)::jsonb -> 'user_metadata' ->> 'role';
            IF v_role IS NOT NULL THEN
                RETURN UPPER(v_role);
            END IF;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        NULL;
    END;

    -- 3. Búsqueda en system_users por ID de sesión
    v_uid := fn_get_current_user_id();
    IF v_uid IS NOT NULL THEN
        SELECT su.role::text INTO v_role
        FROM system_users su
        WHERE su.id = v_uid OR su.email = v_uid
        LIMIT 1;

        IF v_role IS NOT NULL THEN
            IF UPPER(v_role) = 'HSE' THEN
                RETURN 'HSE_ANALYST';
            END IF;
            RETURN UPPER(v_role);
        END IF;

        -- Fallback a hse_users
        SELECT hu.role::text INTO v_role
        FROM hse_users hu
        WHERE hu.id = v_uid OR hu.email = v_uid
        LIMIT 1;

        IF v_role IS NOT NULL THEN
            IF UPPER(v_role) = 'HSE' THEN
                RETURN 'HSE_ANALYST';
            END IF;
            RETURN UPPER(v_role);
        END IF;

        -- Fallback a coders
        IF EXISTS (SELECT 1 FROM coders c WHERE c.id = v_uid OR c.email = v_uid) THEN
            RETURN 'CODER';
        END IF;
    END IF;

    -- 4. Rol de superusuario o admin de la BD local
    IF CURRENT_USER IN ('postgres', 'hse_admin') THEN
        RETURN 'ADMIN';
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- 7.4. fn_check_user_role: Verificar rol para el usuario de sesión o usuario especificado
CREATE OR REPLACE FUNCTION fn_check_user_role(p_role TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_cur_role TEXT;
    v_target_role TEXT := UPPER(TRIM(p_role));
BEGIN
    v_cur_role := fn_get_current_user_role();
    IF v_cur_role IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Normalizar aliases
    IF v_cur_role = 'HSE' THEN
        v_cur_role := 'HSE_ANALYST';
    END IF;
    IF v_target_role = 'HSE' THEN
        v_target_role := 'HSE_ANALYST';
    END IF;

    -- ADMIN tiene acceso total
    IF v_cur_role = 'ADMIN' THEN
        RETURN TRUE;
    END IF;

    -- Jerarquía: TEAM_LEADER tiene permisos de HSE_ANALYST
    IF v_cur_role = 'TEAM_LEADER' AND v_target_role IN ('HSE_ANALYST', 'TEAM_LEADER') THEN
        RETURN TRUE;
    END IF;

    -- Coincidencia directa
    RETURN (v_cur_role = v_target_role);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Sobrecarga de fn_check_user_role con enum user_role
CREATE OR REPLACE FUNCTION fn_check_user_role(p_role user_role)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN fn_check_user_role(p_role::text);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Sobrecarga de fn_check_user_role por ID de usuario específico
CREATE OR REPLACE FUNCTION fn_check_user_role(p_user_id TEXT, p_role TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_user_role TEXT;
    v_target_role TEXT := UPPER(TRIM(p_role));
BEGIN
    SELECT su.role::text INTO v_user_role
    FROM system_users su
    WHERE su.id = p_user_id OR su.email = p_user_id
    LIMIT 1;

    IF v_user_role IS NULL THEN
        SELECT hu.role::text INTO v_user_role
        FROM hse_users hu
        WHERE hu.id = p_user_id OR hu.email = p_user_id
        LIMIT 1;
    END IF;

    IF v_user_role IS NULL THEN
        IF EXISTS (SELECT 1 FROM coders c WHERE c.id = p_user_id OR c.email = p_user_id) THEN
            v_user_role := 'CODER';
        END IF;
    END IF;

    IF v_user_role IS NULL THEN
        RETURN FALSE;
    END IF;

    IF v_user_role = 'HSE' THEN
        v_user_role := 'HSE_ANALYST';
    END IF;
    IF v_target_role = 'HSE' THEN
        v_target_role := 'HSE_ANALYST';
    END IF;

    IF v_user_role = 'ADMIN' THEN
        RETURN TRUE;
    END IF;
    IF v_user_role = 'TEAM_LEADER' AND v_target_role IN ('HSE_ANALYST', 'TEAM_LEADER') THEN
        RETURN TRUE;
    END IF;

    RETURN (v_user_role = v_target_role);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- =============================================================================
-- 8. TRIGGERS DE INTEGRIDAD Y AUDITORÍA AUTOMÁTICA
-- =============================================================================

-- 8.1. Actualización automática de timestamps updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_coders_updated_at
BEFORE UPDATE ON coders
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_hse_users_updated_at
BEFORE UPDATE ON hse_users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_system_users_updated_at
BEFORE UPDATE ON system_users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_justifications_updated_at
BEFORE UPDATE ON justifications
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_evidence_files_updated_at
BEFORE UPDATE ON evidence_files
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 8.2. Trigger de Integridad para Resolución Humana y Protección RBAC
CREATE OR REPLACE FUNCTION fn_enforce_justification_resolution_integrity()
RETURNS TRIGGER AS $$
DECLARE
    v_role TEXT;
BEGIN
    v_role := fn_get_current_user_role();

    -- Regla de integridad RBAC: Un Coder NO puede cambiar el estado de validación ni la decisión HSE
    IF v_role = 'CODER' THEN
        IF (NEW.validation_status IS DISTINCT FROM OLD.validation_status)
           OR (NEW.hse_decision IS DISTINCT FROM OLD.hse_decision)
           OR (NEW.resolution_mode IS DISTINCT FROM OLD.resolution_mode) THEN
            RAISE EXCEPTION 'Acceso denegado: Usuarios con rol CODER no tienen privilegios para dictaminar o resolver justificaciones.';
        END IF;
    END IF;

    -- Auditoría automática cuando se registra una decisión humana de HSE
    IF (NEW.validation_status IN ('APPROVED', 'DISAPPROVED', 'MANUAL_INTERACTION', 'PENDIENTE_DECISION_TL') AND NEW.validation_status IS DISTINCT FROM OLD.validation_status)
       OR (NEW.hse_decision IS NOT NULL AND NEW.hse_decision IS DISTINCT FROM OLD.hse_decision) THEN
        
        NEW.has_human_intervention := TRUE;
        NEW.resolution_mode := 'MANUAL_HSE';
        NEW.hse_reviewed_at := CURRENT_TIMESTAMP;
        
        IF NEW.hse_user_id IS NULL THEN
            NEW.hse_user_id := fn_get_current_user_id();
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_justifications_resolution_integrity
BEFORE UPDATE ON justifications
FOR EACH ROW
EXECUTE FUNCTION fn_enforce_justification_resolution_integrity();

-- 8.3. Trigger de Integridad de Fechas
CREATE OR REPLACE FUNCTION fn_validate_dates_integrity()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.end_date IS NULL THEN
        NEW.end_date := NEW.start_date;
    END IF;
    IF NEW.end_date < NEW.start_date THEN
        RAISE EXCEPTION 'Restricción de Integridad: La fecha de finalización (end_date: %) no puede ser anterior a la fecha de inicio (start_date: %)', NEW.end_date, NEW.start_date;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_justifications_dates_integrity
BEFORE INSERT OR UPDATE ON justifications
FOR EACH ROW
EXECUTE FUNCTION fn_validate_dates_integrity();

-- 8.4. Trigger para sincronizar evidence_files hacia attachments JSONB
CREATE OR REPLACE FUNCTION fn_sync_evidence_file_to_attachments()
RETURNS TRIGGER AS $$
DECLARE
    v_attachment_obj JSONB;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_attachment_obj := jsonb_build_object(
            'id', NEW.id,
            'file_name', NEW.file_name,
            'file_url', NEW.file_url,
            'mime_type', NEW.mime_type,
            'file_size', NEW.file_size_bytes,
            'spatial_boxes', NEW.spatial_boxes
        );

        UPDATE justifications
        SET attachments = COALESCE(attachments, '[]'::jsonb) || jsonb_build_array(v_attachment_obj)
        WHERE id = NEW.justification_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_evidence_files_sync_attachments
AFTER INSERT ON evidence_files
FOR EACH ROW
EXECUTE FUNCTION fn_sync_evidence_file_to_attachments();

-- =============================================================================
-- 9. CONFIGURACIÓN DE SEGURIDAD POR FILA (Row Level Security - RLS)
-- =============================================================================

ALTER TABLE justifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE justifications FORCE ROW LEVEL SECURITY;

ALTER TABLE evidence_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_files FORCE ROW LEVEL SECURITY;

ALTER TABLE system_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_users FORCE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- 9.1. Políticas RLS para justifications
-- -----------------------------------------------------------------------------

-- SELECT: Coder ve solo sus justificaciones; HSE y ADMIN ven todas las justificaciones
CREATE POLICY p_justifications_select ON justifications
FOR SELECT
USING (
    -- Personal administrativo de HSE o Administrador: visualizan todos los registros
    fn_check_user_role('HSE_ANALYST')
    OR fn_get_current_user_role() IN ('HSE_ANALYST', 'HSE', 'TEAM_LEADER', 'ADMIN')
    OR (CURRENT_USER IN ('postgres', 'hse_admin') AND fn_get_current_user_role() IS NULL)
    -- Coder: Únicamente puede consultar sus propias solicitudes
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
            OR sender_email = fn_get_current_user_id()
            OR sender_email IN (
                SELECT su.email 
                FROM system_users su 
                WHERE su.id = fn_get_current_user_id()
            )
        )
    )
);

-- INSERT: Coder solo puede insertar para sí mismo; HSE y ADMIN pueden registrar
CREATE POLICY p_justifications_insert ON justifications
FOR INSERT
WITH CHECK (
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
            OR sender_email = fn_get_current_user_id()
            OR sender_email IN (
                SELECT su.email 
                FROM system_users su 
                WHERE su.id = fn_get_current_user_id()
            )
        )
    )
);

-- UPDATE: HSE y ADMIN pueden dictaminar y resolver; Coders solo pueden editar antes de resolución
CREATE POLICY p_justifications_update ON justifications
FOR UPDATE
USING (
    fn_check_user_role('HSE_ANALYST')
    OR fn_get_current_user_role() IN ('HSE_ANALYST', 'HSE', 'TEAM_LEADER', 'ADMIN')
    OR (CURRENT_USER IN ('postgres', 'hse_admin') AND fn_get_current_user_role() IS NULL)
    OR (
        fn_get_current_user_role() = 'CODER'
        AND (
            coder_id = fn_get_current_user_id()
            OR sender_email = fn_get_current_user_id()
        )
        AND validation_status = 'REVISION_MANUAL'
    )
);

-- -----------------------------------------------------------------------------
-- 9.2. Políticas RLS para evidence_files
-- -----------------------------------------------------------------------------

CREATE POLICY p_evidence_files_select ON evidence_files
FOR SELECT
USING (
    fn_check_user_role('HSE_ANALYST')
    OR fn_get_current_user_role() IN ('HSE_ANALYST', 'HSE', 'TEAM_LEADER', 'ADMIN')
    OR (CURRENT_USER IN ('postgres', 'hse_admin') AND fn_get_current_user_role() IS NULL)
    OR (
        EXISTS (
            SELECT 1 FROM justifications j
            WHERE j.id = evidence_files.justification_id
              AND (
                  j.coder_id = fn_get_current_user_id()
                  OR j.coder_id IN (
                      SELECT su.coder_id 
                      FROM system_users su 
                      WHERE (su.id = fn_get_current_user_id() OR su.email = fn_get_current_user_id())
                        AND su.coder_id IS NOT NULL
                  )
                  OR j.sender_email = fn_get_current_user_id()
                  OR j.sender_email IN (
                      SELECT su.email 
                      FROM system_users su 
                      WHERE su.id = fn_get_current_user_id()
                  )
              )
        )
    )
);

CREATE POLICY p_evidence_files_insert ON evidence_files
FOR INSERT
WITH CHECK (
    fn_check_user_role('HSE_ANALYST')
    OR fn_get_current_user_role() IN ('HSE_ANALYST', 'HSE', 'TEAM_LEADER', 'ADMIN')
    OR (CURRENT_USER IN ('postgres', 'hse_admin') AND fn_get_current_user_role() IS NULL)
    OR (
        EXISTS (
            SELECT 1 FROM justifications j
            WHERE j.id = evidence_files.justification_id
              AND (
                  j.coder_id = fn_get_current_user_id()
                  OR j.sender_email = fn_get_current_user_id()
              )
        )
    )
);

-- -----------------------------------------------------------------------------
-- 9.3. Políticas RLS para system_users
-- -----------------------------------------------------------------------------
CREATE POLICY p_system_users_select ON system_users
FOR SELECT
USING (
    fn_check_user_role('HSE_ANALYST')
    OR fn_get_current_user_role() IN ('HSE_ANALYST', 'HSE', 'TEAM_LEADER', 'ADMIN')
    OR (CURRENT_USER IN ('postgres', 'hse_admin') AND fn_get_current_user_role() IS NULL)
    OR id = fn_get_current_user_id()
    OR email = fn_get_current_user_id()
);

-- =============================================================================
-- 10. VISTA DE CONSULTA OPTIMIZADA PARA EL DASHBOARD HSE (Con security_invoker)
-- =============================================================================
CREATE OR REPLACE VIEW v_justifications_dashboard
WITH (security_invoker = true) AS
SELECT 
    j.id,
    j.ai_recommendation,
    j.validation_status,
    j.resolution_mode,
    j.has_human_intervention,
    j.coder_identification_status,
    j.coder_id,
    COALESCE(c.full_name, j.sender_name, 'Coder no identificado') AS coder_display_name,
    COALESCE(c.cedula, 'Sin cédula') AS coder_cedula,
    c.route AS coder_route,
    j.sender_email,
    j.email_subject,
    j.email_url,
    j.intent,
    j.excuse_type,
    j.start_date,
    j.end_date,
    (j.end_date - j.start_date + 1) AS total_days,
    j.ai_confidence,
    j.ai_reason,
    j.received_at,
    j.created_at,
    j.hse_decision,
    j.hse_notes,
    j.hse_user_id,
    COALESCE(u.full_name, su.full_name) AS hse_reviewer_name,
    COALESCE(u.email, su.email) AS hse_reviewer_email,
    j.hse_reviewed_at,
    CASE 
        WHEN (j.attachments IS NOT NULL AND jsonb_array_length(j.attachments) > 0)
          OR EXISTS (SELECT 1 FROM evidence_files ef WHERE ef.justification_id = j.id)
        THEN TRUE 
        ELSE FALSE 
    END AS has_attachments
FROM justifications j
LEFT JOIN coders c ON j.coder_id = c.id
LEFT JOIN hse_users u ON j.hse_user_id = u.id
LEFT JOIN system_users su ON j.hse_user_id = su.id;

COMMENT ON VIEW v_justifications_dashboard IS 'Vista enriquecida con trazabilidad completa de intervención humana y RLS invoker para el Dashboard HSE';
