-- ============================================================
-- Migración 002: Datos semilla (configuración, plantillas y casos de prueba)
-- Proyecto: Email-Automation (PostgreSQL 16 auto-hospedado)
-- Descripción:
--   Inserta los parámetros dinámicos del sistema, las tres
--   plantillas de correo por defecto y justificaciones semilla
--   realistas calibradas con las salidas oficiales de Strata Core.
--   Es re-ejecutable gracias a ON CONFLICT (idempotente).
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
     'Palabras clave para el filtrado de correos entrantes'),
    -- Entidades de salud reconocidas por el radar léxico espacial (Strata Core FastVocabCleaner)
    ('allowed_medical_institutions',
     '["SURA", "Sanitas", "Compensar", "Famisanar", "Nueva EPS", "Salud Total", "Coosalud", "EPS S.O.S", "Cruz Roja", "Clinica del Country"]'::jsonb,
     'Listado de instituciones de salud y EPS validadas en Colombia'),
    -- Umbrales operativos del sistema (SLA y enrutamiento a revisión manual)
    ('operational_thresholds',
     '{"auto_approve_min_confidence": 0.85, "auto_reject_max_confidence": 0.20, "alert_sla_minutes": 30}'::jsonb,
     'Umbrales de confianza para decisiones automáticas vs revisión manual de la Team Leader')
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

-- ----------------------------------------------------------
-- 3. Casos Semilla de Justificaciones para el Dashboard
--    Permite al Frontend y a la Team Leader visualizar
--    métricas y la bandeja interactiva inmediatamente.
-- ----------------------------------------------------------
INSERT INTO justifications (
    id,
    sender_email,
    sender_name,
    cohort_group,
    email_subject,
    email_body,
    source_provider,
    status,
    ai_verdict,
    ai_confidence,
    attachment_urls,
    tl_notes,
    processed_in_seconds,
    created_at
)
VALUES
    -- Caso 1: Incapacidad médica oficial EPS SURA (Aprobada automática)
    (
        'a1b2c3d4-e5f6-7890-abcd-111111111111',
        'carlos.mendoza@campuslands.net',
        'Carlos Mendoza',
        'Cohorte C-12 Backend',
        'Justificación inasistencia 25 Septiembre - Carlos Mendoza',
        'Estimado equipo HSE, adjunto certificado de incapacidad médica por cuadro viral emitido por EPS SURA.',
        'OUTLOOK',
        'APROBADO_AUTO',
        '{"valido": true, "tipo_novedad": "inasistencia_medica", "fecha_afectada": "2026-09-25", "motivo_decision": "Incapacidad médica oficial emitida por EPS SURA con firma digital válida y fecha dentro de plazo.", "confianza_score": 0.98, "requiere_revision_manual": false, "detalles_adjunto": {"es_legible": true, "tiene_firma_o_sello": true, "institucion_emisora": "EPS SURA", "paginas_consultadas": 1}}'::jsonb,
        0.98,
        ARRAY['https://storage.institucion.edu/justifications/incapacidad_sura_cmendoza.pdf'],
        'Aprobado automáticamente por motor Strata Core con alta confianza.',
        9.24,
        NOW() - INTERVAL '2 hours'
    ),
    -- Caso 2: Falla técnica de Internet con Radicado ISP Tigo (Aprobada automática)
    (
        'a1b2c3d4-e5f6-7890-abcd-222222222222',
        'mariana.torres@campuslands.net',
        'Mariana Torres',
        'Cohorte C-14 Frontend',
        'Excusa por corte de energía y fibra óptica - Mariana Torres',
        'Buenos días equipo, el día de hoy tuvimos corte general de fibra óptica en el sector. Adjunto radicado de falla técnica de Tigo UNE.',
        'GMAIL',
        'APROBADO_AUTO',
        '{"valido": true, "tipo_novedad": "falla_tecnica", "fecha_afectada": "2026-09-26", "motivo_decision": "Reporte de incidencia técnica con número de radicado y afectación domiciliaria comprobable.", "confianza_score": 0.92, "requiere_revision_manual": false, "detalles_adjunto": {"es_legible": true, "tiene_firma_o_sello": false, "institucion_emisora": "Tigo Colombia", "paginas_consultadas": 1}}'::jsonb,
        0.92,
        ARRAY['https://storage.institucion.edu/justifications/ticket_tigo_mtorres.png'],
        NULL,
        8.65,
        NOW() - INTERVAL '4 hours'
    ),
    -- Caso 3: Calamidad doméstica (En Revisión Manual por la TL)
    (
        'a1b2c3d4-e5f6-7890-abcd-333333333333',
        'diego.ramirez@campuslands.net',
        'Diego Ramírez',
        'Cohorte C-10 Fullstack',
        'Inasistencia por urgencia familiar grave',
        'Estimada profe, no pude conectarme a la sesión de la mañana debido a una emergencia médica con mi madre en clínica.',
        'OUTLOOK',
        'REVISION_MANUAL',
        '{"valido": false, "tipo_novedad": "calamidad_domestica", "fecha_afectada": "2026-09-27", "motivo_decision": "Relato creíble en texto plano pero carece de soporte clínico adjunto. Requiere validación de la Team Leader.", "confianza_score": 0.65, "requiere_revision_manual": true, "detalles_adjunto": {"es_legible": false, "tiene_firma_o_sello": false, "institucion_emisora": null, "paginas_consultadas": 0}}'::jsonb,
        0.65,
        ARRAY[]::text[],
        'Pendiente llamada de bienestar para constatar situación personal del coder.',
        6.12,
        NOW() - INTERVAL '1 hour'
    ),
    -- Caso 4: Foto borrosa e ilegible (Rechazo automático con opción de reenvío)
    (
        'a1b2c3d4-e5f6-7890-abcd-444444444444',
        'laura.gomez@campuslands.net',
        'Laura Gómez',
        'Cohorte C-11 Mobile',
        'Justificante cita médica Laura',
        'Adjunto foto de la orden que me dieron.',
        'GMAIL',
        'RECHAZADO_AUTO',
        '{"valido": false, "tipo_novedad": "inasistencia_medica", "fecha_afectada": null, "motivo_decision": "Imagen con desenfoque severo, resolución inferior a umbral mínimo, no se aprecian firmas ni fechas de atención.", "confianza_score": 0.15, "requiere_revision_manual": false, "detalles_adjunto": {"es_legible": false, "tiene_firma_o_sello": false, "institucion_emisora": null, "paginas_consultadas": 1}}'::jsonb,
        0.15,
        ARRAY['https://storage.institucion.edu/justifications/foto_ilegible_lgomez.jpg'],
        'Notificado por correo para reenvío de imagen nítida en 24h.',
        11.40,
        NOW() - INTERVAL '5 hours'
    ),
    -- Caso 5: Salida temprana con comprobante odontológico (Aprobado Manualmente por la TL)
    (
        'a1b2c3d4-e5f6-7890-abcd-555555555555',
        'andres.felipe@campuslands.net',
        'Andrés Felipe Castro',
        'Cohorte C-12 Backend',
        'Permiso salida anticipada 3:00 PM por cita odontológica',
        'Buenas tardes, el día de hoy debo retirarme a las 3:00 PM para procedimiento dental. Adjunto comprobante de agendamiento.',
        'OUTLOOK',
        'APROBADO_MANUAL',
        '{"valido": true, "tipo_novedad": "salida_temprana", "fecha_afectada": "2026-09-24", "motivo_decision": "Cita programada con soporte de consultorio dental particular.", "confianza_score": 0.88, "requiere_revision_manual": true, "detalles_adjunto": {"es_legible": true, "tiene_firma_o_sello": true, "institucion_emisora": "Dentisalud", "paginas_consultadas": 1}}'::jsonb,
        0.88,
        ARRAY['https://storage.institucion.edu/justifications/cita_dentisalud_acastro.pdf'],
        'Aprobado manualmente por Team Leader tras validar reposición de horario.',
        7.80,
        NOW() - INTERVAL '1 day'
    )
ON CONFLICT (id) DO NOTHING;
