-- ============================================================
-- Migración 004: Directorio de Coders Riwi y Resolución de Identidad Multivariable
-- Proyecto: Email-Automation con Strata Core (Riwi Moodle ID: 132)
-- Descripción:
--   1. Crea la tabla 'coders' para albergar el maestro de ~310 estudiantes
--      registrados en Moodle (https://moodle.riwi.io/user/index.php?id=132).
--   2. Modifica 'justifications' para asociar el coder oficial (coder_id),
--      su cédula de ciudadanía (cc_coder) y el método de identificación.
--   3. Implementa la función SQL 'fn_resolve_coder_identity' para emparejar
--      por triplete [EMAIL, CÉDULA EPS, NOMBRE] sin fricción para el estudiante.
--   4. Inserta la plantilla 'UNIDENTIFIED_CODER' en email_templates para el 15%
--      de correos atípicos que requieran intervención de Paola (TL HSE).
--   5. Actualiza la vista 'vw_recent_justifications' con los nuevos campos.
-- ============================================================

-- ----------------------------------------------------------
-- 1. Tabla de Directorio Institucional de Coders de Riwi
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS coders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    moodle_id VARCHAR(50),                         -- ID de usuario en moodle.riwi.io (ej: '132_405')
    name_coder VARCHAR(255) NOT NULL,               -- Nombre completo oficial
    cc_coder VARCHAR(20) UNIQUE,                   -- Cédula de Ciudadanía / Documento de identidad
    email_coder VARCHAR(255) UNIQUE NOT NULL,      -- Correo institucional @riwi.io o personal registrado
    academic_route VARCHAR(100),                   -- Ruta: 'Node.js Backend', 'Java Spring Boot', 'Python AI', etc.
    cohort_group VARCHAR(100),                     -- Grupo/Salón: 'Sputnik Mañana', 'Artemis Tarde', etc.
    status VARCHAR(50) DEFAULT 'ACTIVO',           -- 'ACTIVO', 'GRADUADO', 'INACTIVO'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE coders IS 'Directorio institucional oficial de coders activos en Riwi (Moodle).';
COMMENT ON COLUMN coders.cc_coder IS 'Cédula de ciudadanía, clave para cruce con certificados médicos de EPS.';
COMMENT ON COLUMN coders.academic_route IS 'Ruta de especialización técnica del coder.';

-- Índices de búsqueda para resolución instantánea (< 2ms)
CREATE INDEX IF NOT EXISTS idx_coders_cc ON coders (cc_coder);
CREATE INDEX IF NOT EXISTS idx_coders_email ON coders (email_coder);
CREATE INDEX IF NOT EXISTS idx_coders_name ON coders (name_coder);
CREATE INDEX IF NOT EXISTS idx_coders_route ON coders (academic_route);

-- Trigger para updated_at en coders
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_update_coders_timestamp'
    ) THEN
        CREATE TRIGGER trg_update_coders_timestamp
        BEFORE UPDATE ON coders
        FOR EACH ROW
        EXECUTE FUNCTION fn_auto_update_timestamp();
    END IF;
END $$;

-- ----------------------------------------------------------
-- 2. Evolución de la Tabla 'justifications'
-- ----------------------------------------------------------
ALTER TABLE justifications 
    ADD COLUMN IF NOT EXISTS coder_id UUID REFERENCES coders(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS cc_coder VARCHAR(20),
    ADD COLUMN IF NOT EXISTS identification_method VARCHAR(30) DEFAULT 'UNIDENTIFIED';

-- Índices en justifications para auditoría y búsqueda por cédula
CREATE INDEX IF NOT EXISTS idx_justifications_coder_id ON justifications (coder_id);
CREATE INDEX IF NOT EXISTS idx_justifications_cc_coder ON justifications (cc_coder);

-- ----------------------------------------------------------
-- 3. Función SQL de Resolución de Identidad Multivariable
--    Intenta resolver por: 1) EMAIL -> 2) CÉDULA -> 3) NOMBRE
-- ----------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_resolve_coder_identity(
    p_email TEXT,
    p_cc TEXT DEFAULT NULL,
    p_name TEXT DEFAULT NULL
)
RETURNS TABLE (
    coder_id UUID,
    matched_name VARCHAR(255),
    matched_cc VARCHAR(20),
    matched_cohort VARCHAR(100),
    matched_route VARCHAR(100),
    method VARCHAR(30)
) AS $$
DECLARE
    clean_cc TEXT;
BEGIN
    -- Limpieza básica de la cédula (solo dígitos)
    IF p_cc IS NOT NULL THEN
        clean_cc := regexp_replace(p_cc, '\D', '', 'g');
    END IF;

    -- Intento 1: Coincidencia por correo electrónico exacto
    IF p_email IS NOT NULL AND trim(p_email) <> '' THEN
        RETURN QUERY
        SELECT c.id, c.name_coder, c.cc_coder, c.cohort_group, c.academic_route, 'EMAIL_EXACT'::VARCHAR(30)
        FROM coders c
        WHERE lower(trim(c.email_coder)) = lower(trim(p_email))
        LIMIT 1;
        IF FOUND THEN RETURN; END IF;
    END IF;

    -- Intento 2: Coincidencia por Cédula de Ciudadanía (extraída de la EPS o texto)
    IF clean_cc IS NOT NULL AND length(clean_cc) >= 6 THEN
        RETURN QUERY
        SELECT c.id, c.name_coder, c.cc_coder, c.cohort_group, c.academic_route, 'CC_EPS_MATCH'::VARCHAR(30)
        FROM coders c
        WHERE regexp_replace(c.cc_coder, '\D', '', 'g') = clean_cc
        LIMIT 1;
        IF FOUND THEN RETURN; END IF;
    END IF;

    -- Intento 3: Coincidencia parcial / ILIKE por nombre si se suministra
    IF p_name IS NOT NULL AND length(trim(p_name)) >= 5 THEN
        RETURN QUERY
        SELECT c.id, c.name_coder, c.cc_coder, c.cohort_group, c.academic_route, 'NAME_FUZZY'::VARCHAR(30)
        FROM coders c
        WHERE c.name_coder ILIKE '%' || trim(p_name) || '%'
        LIMIT 1;
        IF FOUND THEN RETURN; END IF;
    END IF;

    -- Intento 4: No identificado
    RETURN QUERY
    SELECT NULL::UUID, NULL::VARCHAR(255), clean_cc::VARCHAR(20), NULL::VARCHAR(100), NULL::VARCHAR(100), 'UNIDENTIFIED'::VARCHAR(30);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fn_resolve_coder_identity IS 'Resuelve la identidad del coder usando la triple llave [EMAIL, CÉDULA, NOMBRE].';

-- ----------------------------------------------------------
-- 4. Plantilla de Correo para el 15% No Identificado
-- ----------------------------------------------------------
INSERT INTO email_templates (id, subject, body_html)
VALUES
    ('UNIDENTIFIED_CODER',
     'Solicitud de Información Adicional - HSE Riwi',
     '<p>Hola,</p><p>Hemos recibido tu solicitud de justificación, pero no logramos identificar tu registro en nuestro directorio de coders activos de Riwi.</p><p>Para que <strong>Paola (Team Leader HSE)</strong> pueda procesar y validar tu novedad, por favor responde a este correo indicando:</p><ul><li><strong>Nombre completo:</strong></li><li><strong>Número de cédula (CC):</strong></li><li><strong>Ruta o grupo de formación:</strong></li></ul><p>Atentamente,<br>Equipo HSE Riwi</p>')
ON CONFLICT (id) DO UPDATE
SET subject = EXCLUDED.subject,
    body_html = EXCLUDED.body_html,
    updated_at = NOW();

-- ----------------------------------------------------------
-- 5. Semillas de Coders Reales de Riwi (Muestra para Pruebas)
-- ----------------------------------------------------------
INSERT INTO coders (id, moodle_id, name_coder, cc_coder, email_coder, academic_route, cohort_group)
VALUES
    ('c1111111-1111-1111-1111-111111111111', '132_101', 'Carlos Mendoza', '1098765432', 'carlos.mendoza@riwi.io', 'Node.js Backend', 'Grupo Sputnik Mañana'),
    ('c2222222-2222-2222-2222-222222222222', '132_102', 'Mariana Torres', '1098765433', 'mariana.torres@riwi.io', 'Frontend React', 'Grupo Artemis Mañana'),
    ('c3333333-3333-3333-3333-333333333333', '132_103', 'Diego Ramírez', '1098765434', 'diego.ramirez@riwi.io', 'Fullstack Python', 'Grupo Apolo Tarde'),
    ('c4444444-4444-4444-4444-444444444444', '132_104', 'Laura Gómez', '1098765435', 'laura.gomez@riwi.io', 'Mobile Flutter', 'Grupo Sputnik Tarde'),
    ('c5555555-5555-5555-5555-555555555555', '132_105', 'Andrés Felipe Castro', '1098765436', 'andres.felipe@riwi.io', 'Java Spring Boot', 'Grupo Artemis Mañana'),
    ('c6666666-6666-6666-6666-666666666666', '132_106', 'Valentina Ruiz', '1098765437', 'valentina.ruiz@riwi.io', 'Node.js Backend', 'Grupo Sputnik Mañana'),
    ('c7777777-7777-7777-7777-777777777777', '132_107', 'Mateo Herrera', '1098765438', 'mateo.herrera@riwi.io', 'Python AI & Data', 'Grupo Apolo Mañana'),
    ('c8888888-8888-8888-8888-888888888888', '132_108', 'Camila Osorio', '1098765439', 'camila.osorio@riwi.io', 'Frontend React', 'Grupo Artemis Tarde'),
    ('c9999999-9999-9999-9999-999999999999', '132_109', 'Santiago Morales', '1098765440', 'santiago.morales@riwi.io', 'Java Spring Boot', 'Grupo Sputnik Tarde'),
    ('caaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '132_110', 'Daniela Pineda', '1098765441', 'daniela.pineda@riwi.io', 'Python AI & Data', 'Grupo Apolo Tarde')
ON CONFLICT (email_coder) DO UPDATE
SET name_coder = EXCLUDED.name_coder,
    cc_coder = EXCLUDED.cc_coder,
    academic_route = EXCLUDED.academic_route,
    cohort_group = EXCLUDED.cohort_group,
    updated_at = NOW();

-- Actualizar las justificaciones existentes para vincularlas a los coders de prueba
UPDATE justifications j
SET coder_id = c.id,
    cc_coder = c.cc_coder,
    identification_method = 'EMAIL_EXACT'
FROM coders c
WHERE lower(j.sender_email) = lower(c.email_coder)
   OR lower(j.sender_name) = lower(c.name_coder);

-- ----------------------------------------------------------
-- 6. Actualización de la Vista 'vw_recent_justifications'
-- ----------------------------------------------------------
CREATE OR REPLACE VIEW vw_recent_justifications AS
SELECT
    j.id,
    COALESCE(c.name_coder, j.sender_name, 'No identificado') AS sender_name,
    j.sender_email,
    COALESCE(c.cc_coder, j.cc_coder, 'Sin CC') AS cc_coder,
    COALESCE(c.cohort_group, j.cohort_group, 'Sin cohorte') AS cohort_group,
    COALESCE(c.academic_route, 'No asignada') AS academic_route,
    j.identification_method,
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
LEFT JOIN coders c ON j.coder_id = c.id
ORDER BY j.created_at DESC;

COMMENT ON VIEW vw_recent_justifications IS 'Bandeja enriquecida con datos del coder Riwi, cédula, ruta y método de identificación.';
