-- =============================================================================
-- SISTEMA DE AUTOMATIZACIÓN DE JUSTIFICACIONES RIWI / HSE
-- Script DDL de Base de Datos PostgreSQL
-- Versión: 2.1 (Modelo con Auditoría Humana y Autenticación Directa HSE)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tablas en orden de dependencia
DROP VIEW IF EXISTS v_justifications_dashboard CASCADE;
DROP TABLE IF EXISTS justifications CASCADE;
DROP TABLE IF EXISTS hse_users CASCADE;
DROP TABLE IF EXISTS coders CASCADE;

-- =============================================================================
-- 1. TABLA coders
-- =============================================================================
CREATE TABLE coders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
-- 2. TABLA hse_users (Con autenticación por contraseña en Frontend)
-- =============================================================================
CREATE TABLE hse_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'HSE',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ,
    CONSTRAINT chk_hse_role CHECK (role IN ('HSE', 'TEAM_LEADER', 'ADMIN'))
);

COMMENT ON TABLE hse_users IS 'Usuarios administrativos de HSE y coordinadores con acceso al panel web';
COMMENT ON COLUMN hse_users.password_hash IS 'Hash seguro de contraseña (bcrypt / argon2) para login directo en frontend';
COMMENT ON COLUMN hse_users.role IS 'Rol administrativo con permisos en el dashboard web';

-- =============================================================================
-- 2.5. TABLA inbound_emails (Registro Transaccional de Ingesta Desacoplada)
-- =============================================================================
CREATE TABLE IF NOT EXISTS inbound_emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id VARCHAR(255) NOT NULL UNIQUE,
    conversation_id VARCHAR(255),
    source_provider VARCHAR(50) NOT NULL DEFAULT 'OUTLOOK',
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(150),
    email_subject TEXT NOT NULL,
    email_body TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING_IDENTIFICATION',
    attachments JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_inbound_status CHECK (
        status IN ('PENDING_IDENTIFICATION', 'IDENTIFIED', 'PROCESSING', 'PROCESSED', 'FAILED', 'DISCARDED')
    )
);

COMMENT ON TABLE inbound_emails IS 'Registro transaccional inmutable para eventos de correo entrante desde Outlook y Gmail';
COMMENT ON COLUMN inbound_emails.message_id IS 'ID inmutable del mensaje en el servidor de correo (Garantía de idempotencia)';
COMMENT ON COLUMN inbound_emails.status IS 'Estado del flujo: PENDING_IDENTIFICATION, IDENTIFIED, etc.';

-- =============================================================================
-- 3. TABLA justifications (Con diferenciador de intervención humana)
-- =============================================================================
CREATE TABLE justifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Relaciones
    coder_id UUID REFERENCES coders(id) ON DELETE SET NULL,
    hse_user_id UUID REFERENCES hse_users(id) ON DELETE SET NULL,
    
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
-- ÍNDICES DE RENDIMIENTO (Performance Tuning)
-- =============================================================================
CREATE INDEX idx_coders_email ON coders(email);
CREATE INDEX idx_coders_cedula ON coders(cedula);
CREATE INDEX idx_coders_active ON coders(is_active);

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

CREATE INDEX IF NOT EXISTS idx_inbound_emails_message_id ON inbound_emails(message_id);
CREATE INDEX IF NOT EXISTS idx_inbound_emails_status ON inbound_emails(status);
CREATE INDEX IF NOT EXISTS idx_inbound_emails_received_at ON inbound_emails(received_at DESC);

-- =============================================================================
-- TRIGGERS PARA AUDITORÍA AUTOMÁTICA (updated_at)
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_coders_updated_at
BEFORE UPDATE ON coders
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_justifications_updated_at
BEFORE UPDATE ON justifications
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_inbound_emails_updated_at
BEFORE UPDATE ON inbound_emails
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VISTA DE CONSULTA OPTIMIZADA PARA EL DASHBOARD HSE
-- =============================================================================
CREATE OR REPLACE VIEW v_justifications_dashboard AS
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
    u.full_name AS hse_reviewer_name,
    u.email AS hse_reviewer_email,
    j.hse_reviewed_at,
    CASE 
        WHEN j.attachments IS NOT NULL AND jsonb_array_length(j.attachments) > 0 THEN TRUE 
        ELSE FALSE 
    END AS has_attachments
FROM justifications j
LEFT JOIN coders c ON j.coder_id = c.id
LEFT JOIN hse_users u ON j.hse_user_id = u.id;

COMMENT ON VIEW v_justifications_dashboard IS 'Vista enriquecida con trazabilidad completa de intervención humana para el Dashboard HSE';


-- 10. USUARIOS ADMINISTRATIVOS DE HSE (Contraseña inicial de prueba: admin123)
INSERT INTO public.hse_users (email, password_hash, full_name, role) VALUES
('laura.hse@riwi.io', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Laura Psicóloga HSE', 'HSE'),
('andres.lead@riwi.io', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Andrés Team Leader', 'TEAM_LEADER'),
('admin.hse@riwi.io', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Administrador General HSE', 'ADMIN')
ON CONFLICT (email) DO NOTHING;

-- 11. SIEMBRA MASIVA DE LOS 297 CODERS REALES DE RIWI (Moodle 132)
INSERT INTO public.coders (cedula, full_name, email, route, is_active)
VALUES
    ('1000000001', 'Jose Luis Acevedo Vargas', 'jose.acevedo@riwi.io', 'Node.js Backend', true),
    ('1000000002', 'Andrea Mariette Ahumada Borja', 'andrea.ahumada@riwi.io', 'Java Spring Boot', true),
    ('1000000003', 'Jhosep Ahumada Navarro', 'jhosep.ahumada@riwi.io', 'BPO / Retiros', true),
    ('1000000004', 'Cristian Ronaldo Albor Parra', 'cristian.albor@riwi.io', 'Java Spring Boot', true),
    ('1000000005', 'Aura Carolina Alean Bolaño', 'aura.alean@riwi.io', 'BPO / Retiros', true),
    ('1000000006', 'Daniel Elias Alvarez Diaz', 'daniel.alvarez@riwi.io', '.NET / C# Backend', true),
    ('1000000007', 'Juan José Álvarez Manjarrez', 'juan.alvarez@riwi.io', '.NET / C# Backend', true),
    ('1000000008', 'Isac David Alvarez Valdes', 'isac.alvarez@riwi.io', 'TypeScript Fullstack', true),
    ('1000000009', 'Daniel Arturo Alzate Zúñiga', 'daniel.alzate@riwi.io', 'Node.js Backend', true),
    ('1000000010', 'Josué Daniel Andrade Najera', 'josue.andrade@riwi.io', 'BPO / Retiros', true),
    ('1000000011', 'Carlos Daniel Aponte Pereira', 'carlos.aponte@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000012', 'Maryuris Aragón Movilla', 'maryuris.aragon@riwi.io', 'TypeScript Fullstack', true),
    ('1000000013', 'Emmanuel De Jesús Archibold Montaño', 'emmanuel.archibold@riwi.io', 'TypeScript Fullstack', true),
    ('1000000014', 'Daniel Alexander Arciniegas Pua', 'daniel.arciniegas@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000015', 'Jorge Areiza', 'jorge.areiza@riwi.io', 'Sin grupo', true),
    ('1000000016', 'Sebastian David Arevalo Barcelo', 'sebastian.arevalo@riwi.io', 'BPO / Retiros', true),
    ('1000000017', 'Harold Ernesto Aristizábal Martinez', 'harold.aristizabal@riwi.io', '.NET / C# Backend', true),
    ('1000000018', 'Javier Ariza', 'javier.ariza@riwi.io', 'Sin grupo', true),
    ('1000000019', 'Julio César Ariza Rivero', 'julio.ariza@riwi.io', 'BPO / Retiros', true),
    ('1000000020', 'Angel David Arnache Cantillo', 'angel.arnache@riwi.io', 'BPO / Retiros', true),
    ('1000000021', 'Alfredo Arteta Tejera', 'alfredo.arteta@riwi.io', 'TypeScript Fullstack', true),
    ('1000000022', 'Sebastian Andres Arzuaga Cormane', 'sebastian.arzuaga@riwi.io', 'BPO / Retiros', true),
    ('1000000023', 'Valentina Atencio Díaz', 'valentina.atencio@riwi.io', 'Java Spring Boot', true),
    ('1000000024', 'Valery Avila Ortega', 'valery.avila@riwi.io', 'Node.js Backend', true),
    ('1000000025', 'Javier Alexander Ávila Rodríguez', 'javier.avila@riwi.io', 'Java Spring Boot', true),
    ('1000000026', 'Leonardo Ivan Ayala Pérez', 'leonardo.ayala@riwi.io', 'Node.js Backend', true),
    ('1000000027', 'Jhonatan Elith Ayala Sanchez', 'jhonatan.ayala@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000028', 'Kerin Enrique Barranco Martínez', 'kerin.barranco@riwi.io', 'Node.js Backend', true),
    ('1000000029', 'Daniel Barrera', 'daniel.barrera@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000030', 'Natalia Barrios', 'natalia.barrios@riwi.io', 'Sin grupo', true),
    ('1000000031', 'Andres Mauricio Barrios Diazgranados', 'andres.barrios@riwi.io', 'Java Spring Boot', true),
    ('1000000032', 'Silvio Luis Barrios Garcia', 'silvio.barrios@riwi.io', 'BPO / Retiros', true),
    ('1000000033', 'Edward Andres Barrios Guerrero', 'edward.barrios@riwi.io', '.NET / C# Backend', true),
    ('1000000034', 'Andrés Barros', 'andres.barros@riwi.io', 'Sin grupo', true),
    ('1000000035', 'Valeria Amelye Bastidas Cancino', 'valeria.bastidas@riwi.io', 'BPO / Retiros', true),
    ('1000000036', 'Eduardo Luis Beleño Forero', 'eduardo.beleno@riwi.io', '.NET / C# Backend', true),
    ('1000000037', 'Kerlys Bello Domecht', 'kerlys.bello@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000038', 'Andres Beltrán', 'andres.beltran@riwi.io', 'Java Spring Boot', true),
    ('1000000039', 'Samuel Esteban Benavides De La Cruz', 'samuel.benavides@riwi.io', 'Automatización con IA', true),
    ('1000000040', 'Andrea Bernal Rueda', 'andrea.bernal@riwi.io', 'BPO / Retiros', true),
    ('1000000041', 'Andres Felipe Blanco Centeno', 'andres.blanco@riwi.io', 'Automatización con IA', true),
    ('1000000042', 'Jaider Yuced Blanco Escobar', 'jaider.blanco@riwi.io', 'BPO / Retiros', true),
    ('1000000043', 'Josué David Blanco Pérez', 'josue.blanco@riwi.io', 'Automatización con IA', true),
    ('1000000044', 'Joseph Bolivar', 'joseph.bolivar@riwi.io', '.NET / C# Backend', true),
    ('1000000045', 'Johana Bolivar González', 'johana.bolivar@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000046', 'Juan Esteban Bolívar Pacheco', 'juan.bolivar@riwi.io', 'TypeScript Fullstack', true),
    ('1000000047', 'Kevin David Bonifacio Trujillo', 'kevin.bonifacio@riwi.io', 'Node.js Backend', true),
    ('1000000048', 'David Alejandro Briceño Nova', 'david.briceno@riwi.io', 'BPO / Retiros', true),
    ('1000000049', 'Valentina Rey Cabas Miranda', 'valentina.cabas@riwi.io', 'Node.js Backend', true),
    ('1000000050', 'Jefferson Lorenzo Cacerez Fernandez', 'jefferson.cacerez@riwi.io', 'BPO / Retiros', true),
    ('1000000051', 'Luis Jose Cala Assia', 'luis.cala@riwi.io', '.NET / C# Backend', true),
    ('1000000052', 'Jefri Miguel Calderin Ortiz', 'jefri.calderin@riwi.io', 'Automatización con IA', true),
    ('1000000053', 'Frank Luis Cañas Bolaño', 'frank.canas@riwi.io', 'Node.js Backend', true),
    ('1000000054', 'Juan Pablo Cañas Jiménez', 'juan.canas@riwi.io', 'Java Spring Boot', true),
    ('1000000055', 'Isaias Cañate Diaz', 'isaias.canate@riwi.io', 'BPO / Retiros', true),
    ('1000000056', 'Moisés Cantillo', 'moises.cantillo@riwi.io', 'Sin grupo', true),
    ('1000000057', 'Joiner Cantillo Camargo', 'joiner.cantillo@riwi.io', 'Node.js Backend', true),
    ('1000000058', 'Jesús David Cantillo Mendoza', 'jesus.cantillo@riwi.io', 'Automatización con IA', true),
    ('1000000059', 'Jorge Luis Carmona Ballestas', 'jorge.carmona@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000060', 'Brandon Jose Carranza Rangel', 'brandon.carranza@riwi.io', 'Automatización con IA', true),
    ('1000000061', 'David Carrascal', 'david.carrascal@riwi.io', 'Java Spring Boot', true),
    ('1000000062', 'Sayder Junior Carreño Ochoa', 'sayder.carreno@riwi.io', 'Automatización con IA', true),
    ('1000000063', 'Hector Mario Carvajal De Los Reyes', 'hector.carvajal@riwi.io', 'Automatización con IA', true),
    ('1000000064', 'Andrés Felipe Cassiani López', 'andres.cassiani@riwi.io', 'BPO / Retiros', true),
    ('1000000065', 'Carlos Dueiner Castaño Rodríguez', 'carlos.castano@riwi.io', 'Sin grupo', true),
    ('1000000066', 'Sebastian Castiblanco Ibañez', 'sebastian.castiblanco@riwi.io', 'Automatización con IA', true),
    ('1000000067', 'Dylan José Castillo Sánchez', 'dylan.castillo@riwi.io', 'BPO / Retiros', true),
    ('1000000068', 'Vanderley Castro Cuadrado', 'vanderley.castro@riwi.io', 'BPO / Retiros', true),
    ('1000000069', 'Ferney Castro Escudero', 'ferney.castro@riwi.io', 'BPO / Retiros', true),
    ('1000000070', 'Carlos Alberto Castro Martínez', 'carlos.castro@riwi.io', 'BPO / Retiros', true),
    ('1000000071', 'Isai David Cataño Diaz', 'isai.catano@riwi.io', 'TypeScript Fullstack', true),
    ('1000000072', 'Elianis Cervantes', 'elianis.cervantes@riwi.io', 'BPO / Retiros', true),
    ('1000000073', 'Joseth Andrés Cervantes Romero', 'joseth.cervantes@riwi.io', 'BPO / Retiros', true),
    ('1000000074', 'Daniel Jesus Chacón De León', 'daniel.chacon@riwi.io', 'BPO / Retiros', true),
    ('1000000075', 'Luisa Fernanda Chamorro Rodríguez', 'luisa.chamorro@riwi.io', 'Sin grupo', true),
    ('1000000076', 'Carlos eduardo charris yepes', 'carlos.charris@riwi.io', 'Node.js Backend', true),
    ('1000000077', 'María José Chavarriaga Rodríguez', 'maria.chavarriaga@riwi.io', 'BPO / Retiros', true),
    ('1000000078', 'Dilan David Chavez Vanegas', 'dilan.chavez@riwi.io', 'Automatización con IA', true),
    ('1000000079', 'Javier Cómbita', 'javier.combita@riwi.io', 'Sin grupo', true),
    ('1000000080', 'Camilo Andrés Coronado Barraza', 'camilo.coronado@riwi.io', 'Automatización con IA', true),
    ('1000000081', 'Jorge Luis Corrales Barraza', 'jorge.corrales@riwi.io', 'TypeScript Fullstack', true),
    ('1000000082', 'Andrés Felipe Cortés Zambrano', 'andres.cortes@riwi.io', '.NET / C# Backend', true),
    ('1000000083', 'Edgar David Corzo Londoño', 'edgar.corzo@riwi.io', 'Automatización con IA', true),
    ('1000000084', 'Oscar Alejandro Corzo Londoño', 'oscar.corzo@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000085', 'Javier Cuenca Meliá', 'javier.cuenca@riwi.io', 'Sin grupo', true),
    ('1000000086', 'Miguel Fernando Daza Hernandez', 'miguel.daza@riwi.io', 'Automatización con IA', true),
    ('1000000087', 'Daniel Santiago De la Hoz Coha', 'daniel.de@riwi.io', '.NET / C# Backend', true),
    ('1000000088', 'Nicholas Andres De La Rosa Rivera', 'nicholas.de@riwi.io', '.NET / C# Backend', true),
    ('1000000089', 'Luisa Fernanda De la Rosa Salgado', 'luisa.de@riwi.io', 'TypeScript Fullstack', true),
    ('1000000090', 'Violy Beatriz De La Rosa Solano', 'violy.de@riwi.io', 'Automatización con IA', true),
    ('1000000091', 'Habith Jose De León Diaz', 'habith.de@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000092', 'Guillermo De León Rojano', 'guillermo.de@riwi.io', 'Java Spring Boot', true),
    ('1000000093', 'Briana De Oro', 'briana.de@riwi.io', 'BPO / Retiros', true),
    ('1000000094', 'Camilo Del Valle', 'camilo.del@riwi.io', 'Sin grupo', true),
    ('1000000095', 'Yulianis Delgado Barros', 'yulianis.delgado@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000096', 'Erik David Demoya', 'erik.demoya@riwi.io', 'BPO / Retiros', true),
    ('1000000097', 'Luis Angel Devia Urueta', 'luis.devia@riwi.io', 'BPO / Retiros', true),
    ('1000000098', 'José del Carmen Díaz Díaz', 'jose.diaz@riwi.io', '.NET / C# Backend', true),
    ('1000000099', 'Arley Diaz Vergara', 'arley.diaz@riwi.io', 'Automatización con IA', true),
    ('1000000100', 'Alejandro Diazgranados', 'alejandro.diazgranados@riwi.io', 'Sin grupo', true),
    ('1000000101', 'Paola Milena Doria Alonso', 'paola.doria@riwi.io', 'Sin grupo', true),
    ('1000000102', 'Danilo Andres Doria Diaz', 'danilo.doria@riwi.io', 'Java Spring Boot', true),
    ('1000000103', 'Nestor Daniel Duran Fuentes', 'nestor.duran@riwi.io', 'Node.js Backend', true),
    ('1000000104', 'Daniel José Echeverría Pardo', 'daniel.echeverria@riwi.io', 'Automatización con IA', true),
    ('1000000105', 'Andrés Camilo Elles Herrera', 'andres.elles@riwi.io', 'TypeScript Fullstack', true),
    ('1000000106', 'Milton Daniel Escamilla Carreño', 'milton.escamilla@riwi.io', 'TypeScript Fullstack', true),
    ('1000000107', 'Ancizar Escobar', 'ancizar.escobar@riwi.io', 'Node.js Backend', true),
    ('1000000108', 'Jonathan Steven Escorcia Salgado', 'jonathan.escorcia@riwi.io', 'TypeScript Fullstack', true),
    ('1000000109', 'Kevin Andres Escorcia Salgado', 'kevin.escorcia@riwi.io', 'Automatización con IA', true),
    ('1000000110', 'Joan Estremor Escalante', 'joan.estremor@riwi.io', 'Node.js Backend', true),
    ('1000000111', 'Vanessa Fontalvo Reniz', 'vanessa.fontalvo@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000112', 'Juan Camilo Gale Muñoz', 'juan.gale@riwi.io', 'Java Spring Boot', true),
    ('1000000113', 'Dylan Gamero', 'dylan.gamero@riwi.io', 'Automatización con IA', true),
    ('1000000114', 'Saeb García Cueto', 'saeb.garcia@riwi.io', 'TypeScript Fullstack', true),
    ('1000000115', 'Yamit Garcia Cueto', 'yamit.garcia@riwi.io', 'Java Spring Boot', true),
    ('1000000116', 'Angela Patricia Garcia Torres', 'angela.garcia@riwi.io', 'BPO / Retiros', true),
    ('1000000117', 'Luigui Garizado Cotes', 'luigui.garizado@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000118', 'Angelo Gaviria', 'angelo.gaviria@riwi.io', 'Sin grupo', true),
    ('1000000119', 'Andrés Felipe Giraldo Acosta', 'andres.giraldo@riwi.io', 'Node.js Backend', true),
    ('1000000120', 'Juan Gomez', 'juan.gomez@riwi.io', 'Node.js Backend', true),
    ('1000000121', 'Luis David Gómez Díaz', 'luis.gomez@riwi.io', 'Automatización con IA', true),
    ('1000000122', 'Alejandro Gonzalez', 'alejandro.gonzalez@riwi.io', 'BPO / Retiros', true),
    ('1000000123', 'Luis Carlos González', 'luis.gonzalez@riwi.io', 'BPO / Retiros', true),
    ('1000000124', 'Joshua Gonzalez Ahumada', 'joshua.gonzalez@riwi.io', 'Automatización con IA', true),
    ('1000000125', 'Diego Alejandro Gonzalez Carvajal', 'diego.gonzalez@riwi.io', 'Node.js Backend', true),
    ('1000000126', 'Adriano de Jesús González Cera', 'adriano.gonzalez@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000127', 'Keyla Thalia Gonzalez Gonzales', 'keyla.gonzalez@riwi.io', 'Java Spring Boot', true),
    ('1000000128', 'Diego Fernando González Henríquez', 'diego.gonzalez2@riwi.io', 'Node.js Backend', true),
    ('1000000129', 'Kevin Andres Gonzalez Visbal', 'kevin.gonzalez@riwi.io', '.NET / C# Backend', true),
    ('1000000130', 'Jose Nicolas Guarin Rodriguez', 'jose.guarin@riwi.io', 'TypeScript Fullstack', true),
    ('1000000131', 'Luis José Guerrero Bruges', 'luis.guerrero@riwi.io', 'Automatización con IA', true),
    ('1000000132', 'Moises Alfredo Gutiérrez Haad', 'moises.gutierrez@riwi.io', 'BPO / Retiros', true),
    ('1000000133', 'Andrés Camilo Gutierrez Ospino', 'andres.gutierrez@riwi.io', 'Node.js Backend', true),
    ('1000000134', 'José David Gutiérrez Retamozo', 'jose.gutierrez@riwi.io', 'TypeScript Fullstack', true),
    ('1000000135', 'Gustavo Andrés Guzmán Mejía', 'gustavo.guzman@riwi.io', 'TypeScript Fullstack', true),
    ('1000000136', 'Isaac Guzman Mora', 'isaac.guzman@riwi.io', 'Java Spring Boot', true),
    ('1000000137', 'Johann Elias Hernandez', 'johann.hernandez@riwi.io', 'BPO / Retiros', true),
    ('1000000138', 'Francisco Hernández López', 'francisco.hernandez@riwi.io', 'Node.js Backend', true),
    ('1000000139', 'Mateo Hernández Mendoza', 'mateo.hernandez@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000140', 'Jorel Yessith Hernandez Muñoz', 'jorel.hernandez@riwi.io', 'Node.js Backend', true),
    ('1000000141', 'Juan David Hernández Viana', 'juan.hernandez@riwi.io', 'BPO / Retiros', true),
    ('1000000142', 'Joseph David Herreño Theran', 'joseph.herreno@riwi.io', 'TypeScript Fullstack', true),
    ('1000000143', 'Brandon Styl Herrera', 'brandon.herrera@riwi.io', 'BPO / Retiros', true),
    ('1000000144', 'Stevens Andres Herrera Hernandez', 'stevens.herrera@riwi.io', '.NET / C# Backend', true),
    ('1000000145', 'Jairo Santiago Ibañez', 'jairo.ibanez@riwi.io', 'BPO / Retiros', true),
    ('1000000146', 'Stevel de Jesus Iglesias Martinez', 'stevel.iglesias@riwi.io', 'Node.js Backend', true),
    ('1000000147', 'Daniel Isaac Jaraba', 'daniel.jaraba@riwi.io', '.NET / C# Backend', true),
    ('1000000148', 'Leonardo David Jiménez Dager', 'leonardo.jimenez@riwi.io', 'Java Spring Boot', true),
    ('1000000149', 'Alejandra Paola Jiménez Dávila', 'alejandra.jimenez@riwi.io', 'TypeScript Fullstack', true),
    ('1000000150', 'Andrea Carolina Jiménez Vargas', 'andrea.jimenez@riwi.io', 'Sin grupo', true),
    ('1000000151', 'Jair Daniel Lastre Arrieta', 'jair.lastre@riwi.io', '.NET / C# Backend', true),
    ('1000000152', 'Jhon Michael Lopera Velasquez', 'jhon.lopera@riwi.io', 'Node.js Backend', true),
    ('1000000153', 'Brayan David Lozada Chaparro', 'brayan.lozada@riwi.io', 'Node.js Backend', true),
    ('1000000154', 'Jesus David Lucena Quintero', 'jesus.lucena@riwi.io', 'Java Spring Boot', true),
    ('1000000155', 'Josue Hernando Lugo Saldarriaga', 'josue.lugo@riwi.io', 'BPO / Retiros', true),
    ('1000000156', 'Juan José Maldonado Navarro', 'juan.maldonado@riwi.io', '.NET / C# Backend', true),
    ('1000000157', 'Breyner De Jesús Manga Arias', 'breyner.manga@riwi.io', 'Automatización con IA', true),
    ('1000000158', 'María Clara Manjarres', 'maria.manjarres@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000159', 'Luis Daniel Manotas Guzman', 'luis.manotas@riwi.io', '.NET / C# Backend', true),
    ('1000000160', 'Emanuel David Manotas Oviedo', 'emanuel.manotas@riwi.io', 'TypeScript Fullstack', true),
    ('1000000161', 'Johan Sebastián Mantilla Jaimes', 'johan.mantilla@riwi.io', 'BPO / Retiros', true),
    ('1000000162', 'Juan Diego Marchena Comas', 'juan.marchena@riwi.io', '.NET / C# Backend', true),
    ('1000000163', 'Camila Isabel Marrugo Tamara', 'camila.marrugo@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000164', 'Deyanis Martelo Hereira', 'deyanis.martelo@riwi.io', 'TypeScript Fullstack', true),
    ('1000000165', 'David Martínez Bolívar', 'david.martinez@riwi.io', 'Sin grupo', true),
    ('1000000166', 'Keiner David Martinez Brochado', 'keiner.martinez@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000167', 'Efrain Hadid Martinez Candanoza', 'efrain.martinez@riwi.io', 'Node.js Backend', true),
    ('1000000168', 'Jayzir Martinez Chamorro', 'jayzir.martinez@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000169', 'Daniel David Martinez González', 'daniel.martinez@riwi.io', 'Automatización con IA', true),
    ('1000000170', 'Valeria Michelle Martinez Sara', 'valeria.martinez@riwi.io', 'BPO / Retiros', true),
    ('1000000171', 'Sebastian Said Maz Vasquez', 'sebastian.maz@riwi.io', 'Node.js Backend', true),
    ('1000000172', 'Luis Alfredo Medrano Caballero', 'luis.medrano@riwi.io', '.NET / C# Backend', true),
    ('1000000173', 'Iván David Mejía Mendez', 'ivan.mejia@riwi.io', '.NET / C# Backend', true),
    ('1000000174', 'Luis Asir Mejía Prada', 'luis.mejia@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000175', 'Laimen Albenis Mejia Prieto', 'laimen.mejia@riwi.io', 'BPO / Retiros', true),
    ('1000000176', 'Alexander Mejia Rodríguez', 'alexander.mejia@riwi.io', 'Node.js Backend', true),
    ('1000000177', 'Roberto Meléndez Ruiz', 'roberto.melendez@riwi.io', '.NET / C# Backend', true),
    ('1000000178', 'Andres David Mena Correa', 'andres.mena@riwi.io', 'TypeScript Fullstack', true),
    ('1000000179', 'Daniel Mendoza', 'daniel.mendoza@riwi.io', 'Node.js Backend', true),
    ('1000000180', 'Sebastian Mendoza Brieva', 'sebastian.mendoza@riwi.io', 'TypeScript Fullstack', true),
    ('1000000181', 'Kevin Alberto Mendoza Rodriguez', 'kevin.mendoza@riwi.io', 'Java Spring Boot', true),
    ('1000000182', 'Sebastián David Mendoza Viloria', 'sebastian.mendoza2@riwi.io', '.NET / C# Backend', true),
    ('1000000183', 'Mateo Mercado', 'mateo.mercado@riwi.io', 'Node.js Backend', true),
    ('1000000184', 'Kevin Junior Mercado Montenegro', 'kevin.mercado@riwi.io', 'Node.js Backend', true),
    ('1000000185', 'Sharon Margarita Meriño Galvis', 'sharon.merino@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000186', 'Camilo Andrés Meza Vásquez', 'camilo.meza@riwi.io', 'Node.js Backend', true),
    ('1000000187', 'Jhonatan Enrique Miranda Bolivar', 'jhonatan.miranda@riwi.io', 'Automatización con IA', true),
    ('1000000188', 'Leonela Isabel Miranda López', 'leonela.miranda@riwi.io', '.NET / C# Backend', true),
    ('1000000189', 'Carlos Daniel Molina Ordóñez', 'carlos.molina@riwi.io', '.NET / C# Backend', true),
    ('1000000190', 'Juan Sebastián Montaño Montilla', 'juan.montano@riwi.io', 'BPO / Retiros', true),
    ('1000000191', 'Cristian Alberto Morales', 'cristian.morales@riwi.io', '.NET / C# Backend', true),
    ('1000000192', 'Mateo Andrés Munera Ospina', 'mateo.munera@riwi.io', 'Java Spring Boot', true),
    ('1000000193', 'Carlos Andrés Muñoz Arrieta', 'carlos.munoz@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000194', 'Jamh Esteban Muñoz Carrasquilla', 'jamh.munoz@riwi.io', 'TypeScript Fullstack', true),
    ('1000000195', 'María Angélica Muñoz López', 'maria.munoz@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000196', 'Dilant Antonio Murillo', 'dilant.murillo@riwi.io', 'Node.js Backend', true),
    ('1000000197', 'Laura Marcela Neira Solano', 'laura.neira@riwi.io', 'Node.js Backend', true),
    ('1000000198', 'Jesús Noguera', 'jesus.noguera@riwi.io', 'Sin grupo', true),
    ('1000000199', 'Mauricio Onofre', 'mauricio.onofre@riwi.io', 'Automatización con IA', true),
    ('1000000200', 'Isaac Camilo Ordoñez', 'isaac.ordonez@riwi.io', 'BPO / Retiros', true),
    ('1000000201', 'Yardelis David Orozco Davis', 'yardelis.orozco@riwi.io', 'BPO / Retiros', true),
    ('1000000202', 'Milton Jesid Ortega Villa', 'milton.ortega@riwi.io', 'TypeScript Fullstack', true),
    ('1000000203', 'Cristian Ortiz', 'cristian.ortiz@riwi.io', 'Automatización con IA', true),
    ('1000000204', 'Sebastian Ulises Ortiz Cruzate', 'sebastian.ortiz@riwi.io', 'Automatización con IA', true),
    ('1000000205', 'Isaac David Ortiz Guzmán', 'isaac.ortiz@riwi.io', 'Java Spring Boot', true),
    ('1000000206', 'Karen Esther Ortiz Martinez', 'karen.ortiz@riwi.io', 'BPO / Retiros', true),
    ('1000000207', 'Carlos Andres Ospina Lizcano', 'carlos.ospina@riwi.io', 'Java Spring Boot', true),
    ('1000000208', 'Diego Andrés Ospino Barrios', 'diego.ospino@riwi.io', 'Automatización con IA', true),
    ('1000000209', 'Santiago Javier Otalora Orozco', 'santiago.otalora@riwi.io', 'Node.js Backend', true),
    ('1000000210', 'Edgardo de Jesús Pacheco Marimon', 'edgardo.pacheco@riwi.io', '.NET / C# Backend', true),
    ('1000000211', 'Valentina Pacheco Ortiz', 'valentina.pacheco@riwi.io', 'Node.js Backend', true),
    ('1000000212', 'Eider Johan Pacheco Suarez', 'eider.pacheco@riwi.io', '.NET / C# Backend', true),
    ('1000000213', 'Esteban Jose Padilla Silva', 'esteban.padilla@riwi.io', 'Automatización con IA', true),
    ('1000000214', 'Lyan Víctor Páez Arévalo', 'lyan.paez@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000215', 'Yesid Palacio', 'yesid.palacio@riwi.io', 'Node.js Backend', true),
    ('1000000216', 'Daniel Pallares', 'daniel.pallares@riwi.io', '.NET / C# Backend', true),
    ('1000000217', 'Lians Dylan Paternina Lopez', 'lians.paternina@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000218', 'Alexandra Peña Orozco', 'alexandra.pena@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000219', 'Jandy José Peña Vásquez', 'jandy.pena@riwi.io', 'TypeScript Fullstack', true),
    ('1000000220', 'Eduardo Perez', 'eduardo.perez@riwi.io', 'Node.js Backend', true),
    ('1000000221', 'Leonardo Jose Perez Chacon', 'leonardo.perez@riwi.io', 'TypeScript Fullstack', true),
    ('1000000222', 'Luis Angel Piñas Meriño', 'luis.pinas@riwi.io', 'Node.js Backend', true),
    ('1000000223', 'Andrés Felipe Quintero Hernandez', 'andres.quintero@riwi.io', 'Java Spring Boot', true),
    ('1000000224', 'Eymi Yurley Quintero Muñoz', 'eymi.quintero@riwi.io', 'Node.js Backend', true),
    ('1000000225', 'Joshua David Quintero Reguillo', 'joshua.quintero@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000226', 'Luz Karime Rabelo', 'luz.rabelo@riwi.io', 'Sin grupo', true),
    ('1000000227', 'William Racine Roa', 'william.racine@riwi.io', 'BPO / Retiros', true),
    ('1000000228', 'Camilo Ramírez', 'camilo.ramirez@riwi.io', 'Java Spring Boot', true),
    ('1000000229', 'Keiner Ramirez', 'keiner.ramirez@riwi.io', 'TypeScript Fullstack', true),
    ('1000000230', 'Neyder Ramirez', 'neyder.ramirez@riwi.io', 'Node.js Backend', true),
    ('1000000231', 'Joyner Ramos Ospino', 'joyner.ramos@riwi.io', 'BPO / Retiros', true),
    ('1000000232', 'Rafael Ramos Rada', 'rafael.ramos@riwi.io', 'BPO / Retiros', true),
    ('1000000233', 'Juan David Rangel Garcia', 'juan.rangel@riwi.io', 'TypeScript Fullstack', true),
    ('1000000234', 'José Mauricio Rangel Nuñez', 'jose.rangel@riwi.io', 'TypeScript Fullstack', true),
    ('1000000235', 'Luis Rafael Reyes Caro', 'luis.reyes@riwi.io', 'Node.js Backend', true),
    ('1000000236', 'Helda Sofía Reyes Ortiz', 'helda.reyes@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000237', 'Valery Nicoll Rhenals Reales', 'valery.rhenals@riwi.io', 'BPO / Retiros', true),
    ('1000000238', 'Manuel David Rincón Clavijo', 'manuel.rincon@riwi.io', '.NET / C# Backend', true),
    ('1000000239', 'Elian David Rivera Guaca', 'elian.rivera@riwi.io', 'Automatización con IA', true),
    ('1000000240', 'Yulianis Paola Rivera Hurtado', 'yulianis.rivera@riwi.io', 'BPO / Retiros', true),
    ('1000000241', 'Diego Andres Rodriguez Arrieta', 'diego.rodriguez@riwi.io', 'Automatización con IA', true),
    ('1000000242', 'Melissa Sofia Rodriguez Buelvas', 'melissa.rodriguez@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000243', 'Jesús David Rodriguez Campo', 'jesus.rodriguez@riwi.io', 'BPO / Retiros', true),
    ('1000000244', 'Ronaldo Rodriguez De Lima', 'ronaldo.rodriguez@riwi.io', 'TypeScript Fullstack', true),
    ('1000000245', 'Jonathan Rodríguez Fernández', 'jonathan.rodriguez@riwi.io', 'TypeScript Fullstack', true),
    ('1000000246', 'Santiago Andres Rodriguez Manzano', 'santiago.rodriguez@riwi.io', 'Java Spring Boot', true),
    ('1000000247', 'Jhonatan Rodriguez Vanegas', 'jhonatan.rodriguez@riwi.io', 'Node.js Backend', true),
    ('1000000248', 'Gabriel Enrique Rodríguez Vasquez', 'gabriel.rodriguez@riwi.io', 'Node.js Backend', true),
    ('1000000249', 'Natalia Isabel Romerin', 'natalia.romerin@riwi.io', 'Node.js Backend', true),
    ('1000000250', 'Joseph Romero', 'joseph.romero@riwi.io', 'Automatización con IA', true),
    ('1000000251', 'Jose David Romero Lara', 'jose.romero@riwi.io', 'TypeScript Fullstack', true),
    ('1000000252', 'Samuel Roncancio Bertel', 'samuel.roncancio@riwi.io', 'Automatización con IA', true),
    ('1000000253', 'Sebastian Enrique Ropain Vasquez', 'sebastian.ropain@riwi.io', 'Automatización con IA', true),
    ('1000000254', 'Kevin Romario Rovira Iglesias', 'kevin.rovira@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000255', 'Jeimar Jesith Rubiano Alcendra', 'jeimar.rubiano@riwi.io', 'Java Spring Boot', true),
    ('1000000256', 'Manuel Alejandro Rueda Consuegra', 'manuel.rueda@riwi.io', 'Node.js Backend', true),
    ('1000000257', 'Axel David Ruiz Polo', 'axel.ruiz@riwi.io', 'Node.js Backend', true),
    ('1000000258', 'John Fredy Salgado', 'john.salgado@riwi.io', 'BPO / Retiros', true),
    ('1000000259', 'Jhonatan David Sanchez Sinning', 'jhonatan.sanchez@riwi.io', 'BPO / Retiros', true),
    ('1000000260', 'Emanuel David Sandoval Jiménez', 'emanuel.sandoval@riwi.io', '.NET / C# Backend', true),
    ('1000000261', 'Fernando Alonso Santos Puentes', 'fernando.santos@riwi.io', '.NET / C# Backend', true),
    ('1000000262', 'Harry Junior Sierra Ospino', 'harry.sierra@riwi.io', 'BPO / Retiros', true),
    ('1000000263', 'Haren Luis Silva Lopez', 'haren.silva@riwi.io', '.NET / C# Backend', true),
    ('1000000264', 'Gianna Solano Cantillo', 'gianna.solano@riwi.io', 'BPO / Retiros', true),
    ('1000000265', 'Oneidy Soto Iriarte', 'oneidy.soto@riwi.io', 'Sin grupo', true),
    ('1000000266', 'Dylan Alberto Suárez Laverde', 'dylan.suarez@riwi.io', 'Node.js Backend', true),
    ('1000000267', 'Luis Mario Suarez Sevilla', 'luis.suarez@riwi.io', 'Node.js Backend', true),
    ('1000000268', 'Sara Tailor Acosta', 'sara.tailor@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000269', 'Santiago Taylor', 'santiago.taylor@riwi.io', 'TypeScript Fullstack', true),
    ('1000000270', 'Andres Felipe Teheran Rodriguez', 'andres.teheran@riwi.io', 'Automatización con IA', true),
    ('1000000271', 'Jafet Miguel Tejada Torres', 'jafet.tejada@riwi.io', 'TypeScript Fullstack', true),
    ('1000000272', 'Sergio David Tobias Viloria', 'sergio.tobias@riwi.io', 'Automatización con IA', true),
    ('1000000273', 'Ricardo José Torres Bermúdez', 'ricardo.torres@riwi.io', 'Node.js Backend', true),
    ('1000000274', 'Beckham Joseth Torres Caceres', 'beckham.torres@riwi.io', 'TypeScript Fullstack', true),
    ('1000000275', 'Saul De Jesús Uribe Hernandez', 'saul.uribe@riwi.io', 'Node.js Backend', true),
    ('1000000276', 'Yaila Ustate Cujia', 'yaila.ustate@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000277', 'Julian Valenzuela Luna', 'julian.valenzuela@riwi.io', 'Node.js Backend', true),
    ('1000000278', 'Julian Vanegas', 'julian.vanegas@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000279', 'Juan José Varela Zorrilla', 'juan.varela@riwi.io', 'Analítica de Datos & BI', true),
    ('1000000280', 'Jose Miguel Vargas Viloria', 'jose.vargas@riwi.io', 'Node.js Backend', true),
    ('1000000281', 'Juan Isaias Vargas Viloria', 'juan.vargas@riwi.io', 'Java Spring Boot', true),
    ('1000000282', 'Manuel Andrés Vásquez Mendoza', 'manuel.vasquez@riwi.io', 'Node.js Backend', true),
    ('1000000283', 'John Sebastian Vasquez Meza', 'john.vasquez@riwi.io', 'BPO / Retiros', true),
    ('1000000284', 'Ramón Alberto Vega Chaparro', 'ramon.vega@riwi.io', 'Java Spring Boot', true),
    ('1000000285', 'Cesar Julio Vega Morales', 'cesar.vega@riwi.io', 'Node.js Backend', true),
    ('1000000286', 'Daniel Viaña Peña', 'daniel.viana@riwi.io', 'Java Spring Boot', true),
    ('1000000287', 'Abrahan Villa', 'abrahan.villa@riwi.io', 'Sin grupo', true),
    ('1000000288', 'Jesús Villa', 'jesus.villa@riwi.io', 'Node.js Backend', true),
    ('1000000289', 'Camilo Andrés Villalobos Ruiz', 'camilo.villalobos@riwi.io', 'Node.js Backend', true),
    ('1000000290', 'Kevin Josué Villalobos Ruiz', 'kevin.villalobos@riwi.io', 'Node.js Backend', true),
    ('1000000291', 'Jaime David Villanova Lamar', 'jaime.villanova@riwi.io', 'Node.js Backend', true),
    ('1000000292', 'Alejandro Israel Villanueva Orozco', 'alejandro.villanueva@riwi.io', 'Node.js Backend', true),
    ('1000000293', 'Jose Visbal', 'jose.visbal@riwi.io', 'BPO / Retiros', true),
    ('1000000294', 'Omar Junior Vizcaino Orozco', 'omar.vizcaino@riwi.io', 'TypeScript Fullstack', true),
    ('1000000295', 'Hillary Sofía Yepes Glen', 'hillary.yepes@riwi.io', 'BPO / Retiros', true),
    ('1000000296', 'Daniela Zapata Jiménez', 'daniela.zapata@riwi.io', 'TypeScript Fullstack', true),
    ('1000000297', 'Andrea Valentina Zárate Rubio', 'andrea.zarate@riwi.io', 'Analítica de Datos & BI', true)
ON CONFLICT (cedula) DO NOTHING;
