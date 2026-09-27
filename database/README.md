# 🗄️ Squad Database (PostgreSQL & Storage)

**Responsables:** Eliam (`Lead DB`) & Sergio (`Storage & Optimization`)  
**Tecnología Base:** PostgreSQL 16 (Alpine auto-hospedado) con compatibilidad nativa para Supabase  
**Misión:** Garantizar la persistencia inmutable, el cumplimiento estricto de la **Ley 1581 de Habeas Data (soberanía médica on-premise)**, consultas al Dashboard con SLA inferior a **50ms** y el soporte de almacenamiento para evidencias probatorias.

---

## 🏗️ 1. Diagrama Entidad-Relación (ER)

```mermaid
erDiagram
    hse_system_config {
        varchar(50) key PK "Clave del parámetro"
        jsonb value "Configuración flexible en JSON"
        text description "Descripción funcional"
        timestamptz updated_at "Última modificación"
    }

    email_templates {
        varchar(50) id PK "APPROVED, REJECTED, MANUAL_REVIEW"
        text subject "Asunto con variables"
        text body_html "Cuerpo con {{variables}}"
        timestamptz updated_at "Última modificación"
    }

    justifications {
        uuid id PK "Identificador único (gen_random_uuid)"
        varchar(255) sender_email "Correo del coder"
        varchar(255) sender_name "Nombre completo"
        varchar(100) cohort_group "Cohorte académica"
        text email_subject "Asunto del correo"
        text email_body "Cuerpo del correo"
        varchar(20) source_provider "OUTLOOK o GMAIL"
        justification_status status "Estado del dictamen"
        jsonb ai_verdict "Salida estructurada Strata Core"
        numeric(3,2) ai_confidence "Confianza (0.00 a 1.00)"
        text[] attachment_urls "URLs de las evidencias"
        text tl_notes "Notas de la Team Leader"
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

    justifications ||--o{ justification_attachments : "contiene"
```

---

## 📂 2. Estructura de Migraciones Idempotentes

Las migraciones se ubican en `database/migrations/` y se ejecutan automáticamente en orden alfabético al iniciar el contenedor de Docker:

| Archivo | Propósito | Responsable |
| :--- | :--- | :--- |
| **`001_initial_schema.sql`** | Creación de extensión `pgcrypto`, ENUM `justification_status`, tablas principales (`hse_system_config`, `email_templates`, `justifications`) e índices base. | Eliam (`DB-01`) |
| **`002_seed_data.sql`** | Datos semilla de reglas dinámicas, instituciones médicas reconocidas (EPS), plantillas HTML y 5 casos reales precargados de prueba. | Eliam (`DB-03`) |
| **`003_storage_and_indexes.sql`** | Tabla `justification_attachments`, índices GIN sobre JSONB, índices compuestos para el Split-View, vistas SQL (`vw_dashboard_kpis`, `vw_recent_justifications`) y triggers. | Sergio (`DB-02` / `DB-04`) |

---

## ⚡ 3. Optimización y Rendimiento (SLA < 50ms)

Para soportar ráfagas matutinas de más de **200 correos diarios** y visualización instantánea en el Frontend:

1. **Índice GIN sobre `ai_verdict`:**
   ```sql
   CREATE INDEX idx_justifications_ai_verdict_gin 
       ON justifications USING gin (ai_verdict jsonb_path_ops);
   ```
   Permite filtrar en < 5ms por cualquier propiedad interna de la IA, por ejemplo:
   ```sql
   SELECT * FROM justifications 
   WHERE ai_verdict @> '{"tipo_novedad": "inasistencia_medica", "valido": true}';
   ```

2. **Índice Compuesto `(status, created_at DESC)`:**
   Acelera la bandeja dividida (*Split-View*) del Frontend (`FRONT-02`), permitiendo paginar y filtrar por estado sin escaneo secuencial de la tabla.

3. **Vistas Pre-calculadas:**
   * **`vw_dashboard_kpis`**: Agrega en una única consulta todos los contadores necesarios para las tarjetas KPI de la cabecera:
     ```sql
     SELECT * FROM vw_dashboard_kpis;
     ```
   * **`vw_recent_justifications`**: Devuelve los registros formateados con el tipo de novedad y total de adjuntos desglosado.

---

## 🚀 4. Guía de Ejecución Local con Docker

### Iniciar la base de datos:
```powershell
docker compose up -d
```

### Verificar el estado y salud del contenedor:
```powershell
docker compose ps
```

### Conectarse a través de `psql` (dentro del contenedor):
```powershell
docker compose exec postgres psql -U hse_admin -d hse_email_automation
```

### Detener el servicio conservando los datos:
```powershell
docker compose down
```

### Reiniciar y aplicar migraciones desde cero (recrear volumen):
```powershell
docker compose down -v
docker compose up -d
```

---

## 🔗 5. Variables de Conexión (`.env`)

```ini
# Configuración local de PostgreSQL
POSTGRES_USER=hse_admin
POSTGRES_PASSWORD=hse_segura_123
POSTGRES_DB=hse_email_automation
POSTGRES_PORT=5432
DATABASE_URL=postgresql://hse_admin:hse_segura_123@localhost:5432/hse_email_automation
```

---

## ☁️ 6. Compatibilidad con Supabase Cloud / Self-Hosted

Si el equipo decide desplegar sobre un proyecto de Supabase:
1. Copiar y pegar secuencialmente los archivos `001`, `002` y `003` en el **SQL Editor** del dashboard de Supabase.
2. Todas las sentencias son 100% compatibles con la sintaxis de PostgreSQL de Supabase.
3. Para el almacenamiento de adjuntos en Supabase Storage, crear el bucket `justification-attachments` con política pública de lectura o acceso autenticado.
