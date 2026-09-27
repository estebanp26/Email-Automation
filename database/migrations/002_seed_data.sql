-- ============================================================
-- Migración 002: Datos semilla (configuración y plantillas)
-- Proyecto: Email-Automation (PostgreSQL 16 auto-hospedado)
-- Descripción:
--   Inserta los parámetros dinámicos del sistema y las tres
--   plantillas de correo por defecto. Es re-ejecutable gracias
--   a ON CONFLICT (idempotente): si la clave ya existe, se
--   actualiza su valor en lugar de duplicarla.
-- Orden de ejecución:
--   Se ejecuta después de 001_initial_schema.sql (orden
--   alfabético en /docker-entrypoint-initdb.d).
-- ============================================================

-- ----------------------------------------------------------
-- 1. Parámetros de configuración del sistema HSE
-- ----------------------------------------------------------
INSERT INTO hse_system_config (key, value, description)
VALUES
    -- Criterios de evaluación inyectados al prompt de la IA:
    -- max_hours define la ventana válida, min_confidence el umbral
    -- para aprobación automática y allowed_types los motivos válidos.
    ('evaluation_criteria',
     '{"max_hours": 48, "min_confidence": 0.80, "allowed_types": ["medica", "calamidad_domestica", "tramite_legal", "fuerza_mayor", "falla_tecnica"]}'::jsonb,
     'Criterios de evaluación HSE inyectados dinámicamente en el prompt de la IA'),
    -- Palabras clave para el filtro inicial de asunto y cuerpo (n8n).
    ('email_keywords',
     '["justificacion", "inasistencia", "falta", "incapacidad", "tardanza", "salida temprana", "excusa"]'::jsonb,
     'Palabras clave para el filtrado de correos entrantes')
ON CONFLICT (key) DO UPDATE
SET value = EXCLUDED.value,
    description = EXCLUDED.description,
    updated_at = NOW();

-- ----------------------------------------------------------
-- 2. Plantillas de correo por defecto
--    Variables disponibles: {{nombre_coder}}, {{fecha}},
--    {{motivo}}, {{motivo_rechazo}}
-- ----------------------------------------------------------
INSERT INTO email_templates (id, subject, body_html)
VALUES
    -- Respuesta cuando la IA aprueba con confianza alta.
    ('APPROVED',
     'Justificación Aprobada - HSE',
     '<p>Hola {{nombre_coder}},</p><p>Tu solicitud de justificación para la fecha <strong>{{fecha}}</strong> ha sido <strong>APROBADA</strong>.</p><p>Motivo registrado: {{motivo}}.</p><p>Recuerda ponerte al día con las grabaciones y actividades de tu cohorte.</p><p>Atentamente,<br>Equipo HSE</p>'),
    -- Respuesta cuando la IA rechaza con confianza alta.
    ('REJECTED',
     'Justificación No Aprobada - HSE',
     '<p>Hola {{nombre_coder}},</p><p>Tu solicitud de justificación para la fecha <strong>{{fecha}}</strong> no pudo ser aprobada automáticamente.</p><p><strong>Motivo:</strong> {{motivo_rechazo}}</p><p>Tienes 24 horas para reenviar el soporte adecuado si consideras que hubo un error.</p><p>Atentamente,<br>Equipo HSE</p>'),
    -- Respuesta cuando el caso va a revisión manual (Team Leader).
    ('MANUAL_REVIEW',
     'Justificación en Revisión - HSE',
     '<p>Hola {{nombre_coder}},</p><p>Hemos recibido tu justificación. Tu caso requiere validación manual por parte de la Team Leader de HSE.</p><p>Te daremos respuesta a la brevedad posible.</p><p>Atentamente,<br>Equipo HSE</p>')
ON CONFLICT (id) DO UPDATE
SET subject = EXCLUDED.subject,
    body_html = EXCLUDED.body_html,
    updated_at = NOW();
