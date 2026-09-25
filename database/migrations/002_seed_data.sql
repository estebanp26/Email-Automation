-- 002_seed_data.sql
-- Datos iniciales y reglas por defecto

-- Reglas por defecto configurables
INSERT INTO hse_system_config (key, value, description) 
VALUES
('evaluation_criteria', '{
    "max_hours_allowed": 48,
    "valid_reasons": ["medica", "calamidad_domestica", "tramite_legal", "fuerza_mayor", "falla_tecnica"],
    "requires_attachment": true,
    "min_confidence_score": 0.80
}'::jsonb, 'Criterios de evaluación HSE inyectados dinámicamente en el prompt'),
('email_keywords', '["justificacion", "inasistencia", "falta", "incapacidad", "tardanza", "salida temprana", "excusa"]'::jsonb, 'Palabras clave para filtro de asunto y cuerpo')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Plantillas de correo por defecto
INSERT INTO email_templates (id, subject, html_body)
VALUES
('APPROVED', 'Justificación Aprobada - HSE', '<p>Hola {{nombre_coder}},</p><p>Tu solicitud de justificación para la fecha <strong>{{fecha}}</strong> ha sido <strong>APROBADA</strong>.</p><p>Motivo registrado: {{motivo}}.</p><p>Recuerda ponerte al día con las grabaciones y actividades de tu cohorte.</p><p>Atentamente,<br>Equipo HSE</p>'),
('REJECTED', 'Justificación No Aprobada - HSE', '<p>Hola {{nombre_coder}},</p><p>Tu solicitud de justificación para la fecha <strong>{{fecha}}</strong> no pudo ser aprobada automáticamente.</p><p><strong>Motivo:</strong> {{motivo_rechazo}}</p><p>Tienes 24 horas para reenviar el soporte adecuado si consideras que hubo un error.</p><p>Atentamente,<br>Equipo HSE</p>'),
('MANUAL_REVIEW', 'Justificación en Revisión - HSE', '<p>Hola {{nombre_coder}},</p><p>Hemos recibido tu justificación. Tu caso requiere validación manual por parte de la Team Leader de HSE.</p><p>Te daremos respuesta a la brevedad posible.</p><p>Atentamente,<br>Equipo HSE</p>')
ON CONFLICT (id) DO UPDATE SET subject = EXCLUDED.subject, html_body = EXCLUDED.html_body;
