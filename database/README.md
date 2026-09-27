# 🗄️ Squad Database (PostgreSQL, Storage & Riwi Coders Directory)

**Responsables:** Eliam (`Lead DB`) & Sergio (`Storage & Optimization`)  
**Tecnología Base:** PostgreSQL 16 (Alpine auto-hospedado) con compatibilidad nativa para Supabase  
**Entorno Operativo:** Riwi (Habilidades para la Vida - HSE | Moodle ID: 132 | Team Leader: Paola)  
**Misión:** Garantizar la persistencia inmutable, el cumplimiento estricto de la **Ley 1581 de Habeas Data (soberanía médica on-premise)**, consultas al Dashboard con SLA inferior a **50ms**, soporte de almacenamiento para evidencias probatorias y la resolución automática de identidad de los ~310 coders.

---

## 🏗️ 1. Diagrama Entidad-Relación (ER)

```mermaid
erDiagram
    coders {
        uuid id PK "Identificador único"
        varchar(50) moodle_id "ID en moodle.riwi.io"
        varchar(255) name_coder "Nombre completo oficial"
        varchar(20) cc_coder UK "Cédula de ciudadanía"
        varchar(255) email_coder UK "Correo institucional @riwi.io"
        varchar(100) academic_route "Ruta (Node, Java, Python AI...)"
        varchar(100) cohort_group "Grupo/Salón (Sputnik, Artemis...)"
        varchar(50) status "ACTIVO, GRADUADO, INACTIVO"
        timestamptz created_at
        timestamptz updated_at
    }

    hse_system_config {
        varchar(50) key PK "Clave del parámetro"
        jsonb value "Configuración flexible en JSON"
        text description "Descripción funcional"
        timestamptz updated_at "Última modificación"
    }

    email_templates {
        varchar(50) id PK "APPROVED, REJECTED, MANUAL_REVIEW, UNIDENTIFIED_CODER"
        text subject "Asunto con variables"
        text body_html "Cuerpo con {{variables}}"
        timestamptz updated_at "Última modificación"
    }

    justifications {
        uuid id PK "Identificador único (gen_random_uuid)"
        uuid coder_id FK "Vínculo al coder de Riwi"
        varchar(20) cc_coder "Cédula extraída de la EPS o vinculada"
        varchar(30) identification_method "EMAIL_EXACT, CC_EPS_MATCH, NAME_FUZZY, UNIDENTIFIED"
        varchar(255) sender_email "Correo del remitente"
        varchar(255) sender_name "Nombre del remitente"
        varchar(100) cohort_group "Cohorte / Grupo"
        text email_subject "Asunto del correo"
        text email_body "Cuerpo del correo"
        varchar(20) source_provider "OUTLOOK o GMAIL"
        justification_status status "Estado del dictamen"
        jsonb ai_verdict "Salida estructurada Strata Core"
        numeric(3,2) ai_confidence "Confianza (0.00 a 1.00)"
        text[] attachment_urls "URLs de las evidencias"
        text tl_notes "Notas de Paola (Team Leader)"
        numeric(4,2) processed_in_seconds "Latencia total del pipeline"
        timestamptz created_at "Fecha y hora de recepción"
    }

    justification_attachments {
        uuid id PK "Identificador único"
        uuid justification_id FK "Relación con justifications"
        text file_name "Nombre del archivo"
        text file_path_or_url "Ruta local o URL S3"
        varchar(100) mime_type "application/pdf, image/png..."
        bigint file_size_bytes "Peso en bytes"
        varchar(64) sha256_hash "Hash para desduplicación"
        jsonb spatial_boxes "Bounding boxes para el visor"
        timestamptz created_at "Fecha de subida"
    }

    coders ||--o{ justifications : "presenta"
    justifications ||--o{ justification_attachments : "contiene"
```

---

## 🔍 2. Resolución de Identidad Multivariable [NOMBRE, CC, EMAIL]

Ante la realidad operativa de que un **~15% de coders** no estructuran sus correos formalmente (olvidan su ruta o escriben desde un correo personal alternativo), el sistema implementa la función SQL:
```sql
SELECT * FROM fn_resolve_coder_identity('correo@ejemplo.com', '1098765432', 'Carlos Mendoza');
```

### Algoritmo de Emparejamiento en Cascada:
1. **Intento 1 (`EMAIL_EXACT`):** Busca coincidencia directa del `sender_email` en `coders.email_coder`.
2. **Intento 2 (`CC_EPS_MATCH`):** Si el correo es personal o desconocido, Strata Core extrae la Cédula de Ciudadanía del certificado médico de la EPS (sello o encabezado clínico). La función busca coincidencia numérica exacta contra `coders.cc_coder`.
3. **Intento 3 (`NAME_FUZZY`):** Búsqueda por aproximación de nombres si el coder firma su correo.
4. **Contingencia 15% (`UNIDENTIFIED`):** Si no hay coincidencia, el caso se asigna con `status = 'REVISION_MANUAL'` para **Paola (Team Leader HSE)** y se despacha la plantilla `UNIDENTIFIED_CODER` solicitando amablemente al coder que envíe su Cédula y Nombre Completo.

---

## 📂 3. Estructura de Migraciones Idempotentes

Las migraciones se ubican en `database/migrations/` y se ejecutan automáticamente en orden alfabético al iniciar el contenedor de Docker:

| Archivo | Propósito | Responsable |
| :--- | :--- | :--- |
| **`001_initial_schema.sql`** | Creación de extensión `pgcrypto`, ENUM `justification_status`, tablas principales (`hse_system_config`, `email_templates`, `justifications`) e índices base. | Eliam (`DB-01`) |
| **`002_seed_data.sql`** | Datos semilla de reglas dinámicas, instituciones médicas reconocidas (EPS), plantillas HTML y 5 casos reales precargados de prueba. | Eliam (`DB-03`) |
| **`003_storage_and_indexes.sql`** | Tabla `justification_attachments`, índices GIN sobre JSONB, índices compuestos para el Split-View, vistas SQL (`vw_dashboard_kpis`, `vw_recent_justifications`) y triggers. | Sergio (`DB-02` / `DB-04`) |
| **`004_riwi_coders_directory.sql`** | Estructura base de tabla `coders`, campos `cc_coder` en `justifications`, función `fn_resolve_coder_identity` y plantilla `UNIDENTIFIED_CODER`. | Eliam & Sergio |
| **`005_real_riwi_coders.sql`** | Inserción masiva de los **297 coders reales** extraídos de Moodle ID=132 con sus rutas oficiales (IA, TypeScript, NodeJS, Java, C#, Analítica) y correos `@riwi.io`. | Importador Automatizado |

---

## ⚡ 4. Optimización y Rendimiento (SLA < 50ms)

* **Índice GIN sobre `ai_verdict`:** Permite filtrar por tipo de novedad o validez en `< 5ms`.
* **Índice Compuesto `(status, created_at DESC)`:** Paginación y filtrado instantáneo en la bandeja de entrada del Frontend.
* **Índices en `coders`:** Búsquedas por `cc_coder` y `email_coder` en tiempo O(1) con índice B-Tree.

---

## 🚀 5. Guía de Ejecución Local con Docker

```powershell
# Iniciar base de datos
docker compose up -d

# Validar integridad y consistencia de todas las migraciones
python database/verify_schema.py

# Conectarse a psql en el contenedor
docker compose exec postgres psql -U hse_admin -d hse_email_automation
```
