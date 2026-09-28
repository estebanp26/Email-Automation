# Documentación completa del flujo n8n — Automatización de Justificaciones HSE

**Repositorio de referencia:** `estebanp26/Email-Automation`  
**Branch analizada:** `feature/ai-engine`  
**Commit analizado:** `bb4191506be91e04790051faad2a3fac22da3f6b`  
**Motor IA:** Strata Core + Qwen 2.5 (`qwen2.5:1.5b`) vía Ollama  
**Base de Datos Relacional:** PostgreSQL 15+ (Esquema de 3 entidades maestras)  
**Workflow n8n de Producción:** `n8n_workflow_email_hse.json`  

---

## 0. Alcance y estado de esta documentación

Esta documentación reconstruye el flujo integral que orquesta **n8n** a partir del contrato de integración, el código fuente real del motor de IA **Strata Core** y el esquema unificado de base de datos relacional.

**Importante:** La branch analizada contiene el microservicio Strata Core y documentación de integración, pero no incluía los archivos JSON de los workflows n8n funcionales que el `n8n/README.md` mencionaba (`01_ingesta_filtro.json`, `02_evaluacion_ai.json`, `03_despacho_respuestas.json`). En este proyecto se ha materializado el workflow completo y ejecutable en el archivo [`n8n_workflow_email_hse.json`](file:///home/wuisino/Projects/Email-Riwi/n8n_workflow_email_hse.json) (22 nodos, 17 conexiones), completamente alineado con la arquitectura objetivo documentada en este informe.

También se resuelven y estandarizan las inconsistencias identificadas entre la documentación heredada y la implementación real:

- `n8n/README.md` mencionaba Gemini 2.0 Flash y las tablas `hse_system_config` / `email_templates`.
- El AI Engine actual expone una API local con **Qwen 2.5: 1.5B** vía Ollama.
- El endpoint de evaluación acepta reglas dinámicas opcionales, pero dispone de guardrails deterministas en su código.
- La migración SQL obsoleta que creaba tablas de configuración se reemplaza por el **modelo unificado de 3 entidades maestras** (`coders`, `hse_users`, `justifications`).

---

# 1. Arquitectura general

El sistema opera bajo un modelo desacoplado donde n8n actúa como el director de orquesta que conecta los clientes de correo corporativo, la base de datos relacional y el motor local de inferencia.

```mermaid
flowchart TD
    subgraph INBOX["📧 Bandeja de Entrada"]
        MAIL["Outlook / Gmail<br/>Correo entrante del Coder"]
    end

    subgraph N8N_SUB1["⚙️ n8n — Subflujo 1: Ingesta"]
        TRIGGER["Trigger / Webhook Correo"]
        NORM["Normalize Email<br/>Payload Unificado"]
        URL["Build Email URL<br/>Deep Link de Auditoría"]
        TRIGGER --> NORM --> URL
    end

    subgraph DB_SEARCH["🗄️ PostgreSQL — Identificación"]
        FIND["Búsqueda en Cascada<br/>email → cédula → nombre"]
        FOUND{"¿Coder<br/>Encontrado?"}
        NOT_FOUND["CODER_NO_ENCONTRADO<br/>coder_id = NULL"]
        NOT_FOUND_NOTIF["Enviar respuesta pidiendo cédula"]
        FIND --> FOUND
        FOUND -->|NO| NOT_FOUND --> NOT_FOUND_NOTIF
    end

    subgraph AI_ENGINE["🧠 Strata Core API (VPS / Docker)"]
        HTTP_STRATA["POST /api/evaluate-excuse<br/>Timeout ≥ 60s"]
        ENGINE["Extracción OCR (PyMuPDF)<br/>Poda de Contexto ≤ 3500 ch<br/>Inferencia Qwen 2.5: 1.5B (Ollama)"]
        JSON_OUT["Salida JSON Estructurada<br/>valido, tipo_novedad, confianza"]
        HTTP_STRATA --> ENGINE --> JSON_OUT
    end

    subgraph DECISION["⚖️ n8n — Branching de Decisión"]
        GUARD["Validar Schema y Guardrails<br/>(Luto, Fallas, Spam)"]
        SWITCH{"Estado Resultante"}
        APP["APPROVED<br/>Excusa válida con soporte"]
        DIS["DISAPPROVED<br/>Causa injustificada"]
        MAN["MANUAL_INTERACTION<br/>Duda, baja confianza, luto s/soporte"]
        GUARD --> SWITCH
        SWITCH -->|Aprobado| APP
        SWITCH -->|Rechazado| DIS
        SWITCH -->|Revisión| MAN
    end

    subgraph PERSISTENCE["💾 PostgreSQL — Persistencia"]
        JUST_DB[("Tabla: justifications<br/>Registro Único Central")]
    end

    subgraph DISPATCH["📬 Notificación y Visualización"]
        SEND_OK["Correo de Aprobación al Coder"]
        SEND_FAIL["Correo de Rechazo con Motivo"]
        HSE_PANEL["Bandeja de Pendientes<br/>Dashboard Web HSE"]
    end

    MAIL -->|Payload inicial| TRIGGER
    URL --> FIND
    FOUND -->|SÍ| HTTP_STRATA
    JSON_OUT --> GUARD
    APP --> JUST_DB --> SEND_OK
    DIS --> JUST_DB --> SEND_FAIL
    MAN --> JUST_DB --> HSE_PANEL
```

---

# 2. Contrato que entra a n8n

El adaptador de Outlook o Gmail entrega a n8n una estructura homogénea para desacoplar el origen del mensaje:

```json
{
  "source_provider": "OUTLOOK",
  "message_id": "AAMkAGI2...",
  "conversation_id": "AAQkAGI...",
  "sender_email": "coder@example.com",
  "sender_name": "Laura Gómez",
  "email_subject": "Justificación inasistencia 25 Septiembre",
  "email_body": "Buenos días, adjunto comprobante médico...",
  "received_at": "2026-09-25T14:10:00Z",
  "attachments": [
    {
      "filename": "incapacidad_eps.pdf",
      "mime_type": "application/pdf",
      "data_base64": "JVBERi0xLjQK..."
    }
  ]
}
```

**Responsabilidad de n8n:** Conservar este payload intacto, evitar la pérdida de los adjuntos o del cuerpo crudo y enriquecer el objeto con los metadatos necesarios para trazabilidad y auditoría.

---

# 3. Estructura completa de n8n

La implementación se estructura en **tres subflujos lógicos interconectados**:

```mermaid
flowchart LR
    subgraph SF1["SUBFLUJO 1"]
        direction TB
        S1["📥 Ingesta + Normalización"]
        S2["🔍 Identificación en PostgreSQL"]
        S1 --> S2
    end

    subgraph SF2["SUBFLUJO 2"]
        direction TB
        S3["🧠 Invocación Strata Core (IA)"]
        S4["🛡️ Validación de Schema y Guardrails"]
        S3 --> S4
    end

    subgraph SF3["SUBFLUJO 3"]
        direction TB
        S5["💾 Persistencia Unificada en BD"]
        S6["✉️ Despacho de Correo al Coder"]
        S7["👥 Cola Manual en Panel HSE"]
        S5 --> S6
        S5 --> S7
    end

    SF1 -->|Coder Identificado| SF2
    SF2 -->|Veredicto Emitido| SF3
```

Esta división modular conserva la separación funcional recomendada en el repositorio, pero integra directamente **Strata Core / Qwen 2.5** y el esquema definitivo de PostgreSQL.

---

# 4. SUBFLUJO 1 — Ingesta y normalización

## Diagrama n8n del Subflujo 1

```mermaid
flowchart TD
    A["📧 Trigger Outlook / Gmail"] --> B["⚙️ 01 Normalize Email<br/>Homogeneiza encabezados y cuerpo"]
    B --> C{"📎 ¿Contiene Adjuntos?"}
    C -->|SÍ| D1["Extraer Binario / Base64<br/>has_attachments = true"]
    C -->|NO| D2["Continuar solo con Texto<br/>has_attachments = false"]
    D1 --> E["🔗 02 Build Email URL<br/>Construye Deep Link para auditoría"]
    D2 --> E
    E --> F["🗄️ 03 PostgreSQL — Buscar Coder<br/>email → cédula → nombre"]
    F --> G{"04 ¿Coder<br/>Encontrado?"}
    G -->|SÍ| H["➡️ Continuar a Subflujo 2<br/>(07 Preparar Payload Strata Core)"]
    G -->|NO| I["🚫 06A Marcar CODER_NOT_FOUND<br/>validation_status = DISAPPROVED"]
    I --> J["💾 06B Guardar en justifications<br/>coder_id = NULL"]
    J --> K["✉️ 06C Enviar Notificación al Remitente<br/>Solicitando cédula, nombre y ruta"]
```

## Nodo 1 — Trigger de correo
* **Función:** Iniciar la ejecución ante un nuevo mensaje en la bandeja de entrada (Webhook de Outlook Graph API, Gmail Push Notifications o sondeo IMAP).
* **Entrada esperada:** Payload del proveedor de correo.
* **Metadatos esenciales:** `message_id`, `conversation_id`, `sender_email`, `sender_name`, `email_subject`, `email_body`, `received_at` y `attachments`.

## Nodo 2 — Normalize Email
Estandariza los nombres de propiedades para que el resto del workflow sea agnóstico respecto a la plataforma de correo:

| Entrada Outlook / Gmail | Propiedad Unificada n8n | Tipo |
| :--- | :--- | :--- |
| `id` / `messageId` | `message_id` | String |
| `conversationId` / `threadId` | `conversation_id` | String |
| `from.emailAddress.address` / `from` | `sender_email` | String (Lowercase) |
| `from.emailAddress.name` | `sender_name` | String |
| `subject` | `email_subject` | String |
| `body.content` / `snippet` | `email_body` | String |
| `receivedDateTime` / `date` | `received_at` | TIMESTAMPTZ (ISO) |
| `attachments[]` | `attachments[]` | Array de Objetos |

## Nodo 3 — Extract Attachments
Produce la lista de adjuntos con sus metadatos y una bandera booleana operativa:
* `has_attachments = true | false`
* `filename`, `mime_type`, `size_bytes`, `data_base64`.

> [!NOTE]
> **No debe asumirse que todos los correos tienen adjunto.** Strata Core admite la evaluación de correos de texto plano sin archivos anexos.

## Nodo 4 — Build Email URL
Construye automáticamente el hipervínculo directo al correo para el panel web de HSE:
* **Outlook Web:** `https://outlook.office.com/mail/deeplink/read/${encodeURIComponent(message_id)}`
* **Gmail:** `https://mail.google.com/mail/u/0/#search/rfc822msgid%3A${encodeURIComponent(message_id)}`

## Nodo 5 — PostgreSQL: Búsqueda del Coder
La identificación se ejecuta obligatoriamente antes de evaluar la excusa, siguiendo una estrategia de búsqueda en cascada:

```mermaid
flowchart TD
    START(["Remitente del Correo"]) --> STEP1["1. Búsqueda por sender_email<br/>WHERE email = $1"]
    STEP1 --> CHK1{"¿Coincidencia<br/>Exacta?"}
    CHK1 -->|SÍ| FOUND1["✅ Coder Encontrado<br/>Asociar coder_id"]
    CHK1 -->|NO| STEP2["2. Búsqueda por Cédula extraída<br/>WHERE cedula = $2"]
    
    STEP2 --> CHK2{"¿Coincidencia<br/>Única?"}
    CHK2 -->|SÍ| FOUND2["✅ Coder Encontrado<br/>Asociar coder_id"]
    CHK2 -->|NO| STEP3["3. Búsqueda por Nombre extraído<br/>WHERE LOWER(full_name) = LOWER($3)"]
    
    STEP3 --> CHK3{"¿Coincidencia<br/>Única?"}
    CHK3 -->|SÍ| FOUND3["✅ Coder Encontrado<br/>Asociar coder_id"]
    CHK3 -->|NO / Múltiples| NOT_FOUND["❌ CODER NO ENCONTRADO<br/>coder_id = NULL<br/>Derivar a notificación de solicitud"]
```

## Nodo 6 — IF `coder_found`
* **Rama TRUE:** Avanza hacia la evaluación de inteligencia artificial en Strata Core.
* **Rama FALSE:** El sistema no inventa identidad. Se persiste el correo en `justifications` con `coder_id = NULL`, `coder_identification_status = 'CODER_NOT_FOUND'`, `validation_status = 'DISAPPROVED'` y se dispara una respuesta automática al remitente solicitando su cédula y nombre completo.

---

# 5. SUBFLUJO 2 — Evaluación con Strata Core

## Vista del Branch de IA

```mermaid
flowchart TD
    A["07 Prepare Strata Payload<br/>email_subject, email_body, model, file_base64"] --> B["🌐 08 HTTP Request a Strata Core<br/>POST /api/evaluate-excuse (Timeout 60s)"]
    B --> C{"09 ¿Error Técnico<br/>o Timeout?"}
    
    C -->|SÍ (Caída Ollama / Error HTTP)| FAIL["⚠️ Failover de Resiliencia<br/>valido = false, requiere_manual = true<br/>ai_confidence = 0.0"]
    C -->|NO (Respuesta 200 OK)| PARSE["Parsear JSON de IA<br/>valido, tipo, fecha, motivo, score"]
    
    FAIL --> G["🛡️ Guardrails Deterministas<br/>Verificar Luto, Spam, etc."]
    PARSE --> G
    
    G --> D{"10 Decision Switch<br/>validation_status"}
    
    D -->|APPROVED| BRANCH_A["✅ Branch A: Aprobado<br/>valido=true AND manual=false AND score>=0.80"]
    D -->|DISAPPROVED| BRANCH_B["❌ Branch B: Rechazado<br/>valido=false AND manual=false"]
    D -->|MANUAL_INTERACTION| BRANCH_C["⚠️ Branch C: Manual HSE<br/>manual=true OR score<0.80 OR error"]
```

## Nodo 1 — Prepare Strata Payload
Prepara el cuerpo de la petición hacia la API local de Strata Core:

```json
{
  "email_subject": "Incapacidad médica 25 Septiembre",
  "email_body": "Buenos días, adjunto comprobante médico de EPS Sanitas...",
  "model": "qwen2.5:1.5b",
  "file_base64": "JVBERi0xLjQK...",
  "filename": "incapacidad_eps.pdf"
}
```

## Nodo 2 — HTTP Request a Strata Core
* **Endpoint:** `POST http://localhost:8001/api/evaluate-excuse`
* **Timeout configurado:** `60000 ms` (60 segundos).
* **Parámetro clave:** `continueOnFail: true` para habilitar el failover automático ante saturación del modelo.

## Pipeline Interno de Strata Core

```mermaid
flowchart TD
    subgraph INTAKE["📥 Entrada de Datos"]
        F_DOC["Documento Adjunto<br/>(PDF o Imagen)"]
        F_TXT["Texto del Correo<br/>(Asunto y Cuerpo)"]
    end

    subgraph EXTRACT["📄 Extracción de Texto"]
        PDF_ENG["PDFEngineReader"]
        OCR_ENG["FastOCREngine<br/>(Preprocesamiento + Tesseract)"]
        F_DOC --> PDF_ENG
        PDF_ENG -->|Texto digital| CLEAN
        PDF_ENG -->|Escaneado / Imagen| OCR_ENG --> CLEAN
        F_TXT --> CLEAN["Fast Vocabulary Cleaner<br/>Limpieza léxica y normalización"]
    end

    subgraph CONTEXT["✂️ Indexación y Poda de Contexto"]
        SEARCH["Search & Indexing Engine"]
        PRUNING["Smart Context Pruning<br/>Reducción dinámica ≤ 3500 caracteres"]
        CLEAN --> SEARCH --> PRUNING
    end

    subgraph LLM["🤖 Inferencia LLM"]
        PROMPT["evaluator_system_prompt<br/>+ dynamic rules JSON<br/>+ contexto podado"]
        OLLAMA["Ollama /api/generate<br/>Modelo: Qwen 2.5: 1.5B"]
        PRUNING --> PROMPT --> OLLAMA
    end

    subgraph OUTPUT["📤 Salida Estructurada"]
        JSON_RES["JSON Validador y Parser<br/>valido, tipo_novedad, confianza, manual"]
        OLLAMA --> JSON_RES
    end
```

---

# 6. Qué hace Qwen y qué NO hace

### Responsabilidad de Qwen 2.5: 1.5B
* Razona sobre el contexto podado suministrado por Strata Core.
* Produce la salida JSON estructurada con:
  * `valido`: Boolean
  * `tipo_novedad`: Categoría detectada
  * `fecha_afectada`: Fecha extraída
  * `motivo_decision`: Síntesis en lenguaje natural
  * `confianza_score`: Nivel de certidumbre (0.00 a 1.00)
  * `requiere_revision_manual`: Bandera de ambigüedad
  * `detalles_adjunto`: Datos del documento analizado

### Responsabilidad de Strata Core (previo a Qwen)
* Extracción binaria, OCR de imágenes/PDFs, limpieza léxica, detección de firmas/sellos y poda del prompt para no saturar la ventana de contexto.

### Responsabilidad de n8n
* Orquestar la comunicación, identificar al coder en PostgreSQL, aplicar guardrails deterministas, resolver el enrutamiento y ejecutar la persistencia en base de datos.

---

# 7. Respuesta de Strata Core y Branch Principal de Decisión

### Contrato JSON devuelto por Strata Core:

```json
{
  "valido": true,
  "tipo_novedad": "inasistencia_medica",
  "fecha_afectada": "2026-09-25",
  "motivo_decision": "Documento médico oficial válido con fecha y soporte verificable de EPS Sanitas.",
  "confianza_score": 0.95,
  "requiere_revision_manual": false,
  "detalles_adjunto": {
    "es_legible": true,
    "tiene_firma_o_sello": true,
    "institucion_emisora": "EPS Sanitas",
    "paginas_consultadas": [1]
  },
  "tiempo_procesamiento_segundos": 10.65
}
```

## Lógica de Enrutamiento del Decision Switch

```mermaid
flowchart TD
    START(["Resultado de Strata Core"]) --> COND1{"¿requiere_revision_manual?<br/>O confianza < 0.80?"}
    
    COND1 -->|SÍ| MANUAL["🟡 MANUAL_INTERACTION<br/>Derivado a cola de atención humana en Panel HSE"]
    COND1 -->|NO| COND2{"¿valido == true?"}
    
    COND2 -->|SÍ| APPROVED["🟢 APPROVED<br/>Aprobación automática: Persistir y notificar éxito al Coder"]
    COND2 -->|NO| REJECTED["🔴 DISAPPROVED<br/>Rechazo automático: Persistir y notificar motivo al Coder"]

    style MANUAL fill:#fff3cd,stroke:#ffeeba,color:#856404
    style APPROVED fill:#d4edda,stroke:#c3e6cb,color:#155724
    style REJECTED fill:#f8d7da,stroke:#f5c6cb,color:#721c24
```

* **Branch A (APPROVED):** `valido === true` AND `requiere_revision_manual === false` AND `confianza_score >= 0.80`. Guarda en `justifications` y despacha correo de confirmación al coder.
* **Branch B (REJECTED):** `valido === false` AND `requiere_revision_manual === false`. Guarda en `justifications` con el motivo del rechazo y despacha correo informativo.
* **Branch C (MANUAL_INTERACTION):** `requiere_revision_manual === true` OR `confianza_score < 0.80`. Guarda en `justifications` y expone el caso en la bandeja de pendientes del Dashboard HSE.

---

# 8. Failover y Resiliencia cuando Ollama falla

El microservicio Strata Core y el workflow de n8n implementan una contingencia activa para evitar que caídas de infraestructura rechacen injustamente la excusa de un estudiante:

```mermaid
flowchart TD
    REQ["HTTP Request a Strata Core"] --> RESP{"Estado de la Respuesta"}
    RESP -->|200 OK y JSON Válido| NORMAL["Procesamiento Normal de IA<br/>Evaluación con Qwen 2.5"]
    RESP -->|Timeout / 5xx / Ollama Caído| FAILOVER["⚡ Mecanismo de Failover<br/>valido = false<br/>confianza_score = 0.0<br/>requiere_revision_manual = true<br/>tipo_novedad = no_identificado"]
    
    NORMAL --> DECISION["Decisión según reglas"]
    FAILOVER --> MANUAL["🟡 Enrutar a MANUAL_INTERACTION<br/>(Evita rechazos erróneos por caídas del servidor)"]
    
    style FAILOVER fill:#fce5cd,stroke:#e69138,color:#b45f06
```

---

# 9. Guardrails Deterministas de Negocio

Antes de tomar la decisión definitiva, el nodo `09 Validar Schema y Guardrails` en n8n inspecciona el texto del mensaje para aplicar reglas deterministas:

```mermaid
flowchart TD
    IN(["Texto del Correo + Resultado IA"]) --> G1{"¿Contiene palabras de<br/>Luto / Calamidad?"}
    G1 -->|SÍ| G1_ATT{"¿Tiene Adjunto?"}
    G1_ATT -->|NO| F_CAL["Forzar: tipo_novedad = calamidad<br/>valido = false<br/>requiere_manual = true"]
    G1_ATT -->|SÍ| G2
    G1 -->|NO| G2{"¿Contiene palabras<br/>de Spam / Cursos?"}
    
    G2 -->|SÍ| F_SPAM["Forzar: tipo_novedad = no_identificado<br/>valido = false<br/>requiere_manual = true"]
    G2 -->|NO| G3{"¿Contiene ticket / falla<br/>técnica con soporte?"}
    
    G3 -->|SÍ| F_TECH["Forzar: tipo_novedad = falla_tecnica<br/>valido = true, manual = false"]
    G3 -->|NO| G4{"¿Schema de IA válido y<br/>confianza >= 0.80?"}
    
    G4 -->|NO| F_MAN["Forzar: MANUAL_INTERACTION"]
    G4 -->|SÍ| PASS["Aceptar Veredicto de Qwen 2.5"]
    
    F_CAL --> OUT(["Veredicto Final"])
    F_SPAM --> OUT
    F_TECH --> OUT
    F_MAN --> OUT
    PASS --> OUT
```

1. **Calamidad Familiar / Luto:** Términos como *fallecimiento*, *luto*, *funeraria*, *entierro*. Si no hay archivo adjunto, se fuerza `valido = false` y `requiere_revision_manual = true` para que HSE brinde acompañamiento humano sensible.
2. **Spam / Publicidad:** Términos como *descuento*, *cursos de*, *promoción*. Se clasifican como `no_identificado` y se derivan a revisión manual.
3. **Fallas Técnicas:** Términos como *ticket*, *fibra*, *Claro*, *Tigo*, *sin internet*. Con soporte se aprueban; sin soporte se derivan a revisión.

---

# 10. Persistencia en PostgreSQL

El sistema utiliza el **modelo simplificado de 3 entidades maestras**, manteniendo un único registro histórico inmutable para cada correo procesado:

```mermaid
erDiagram
    CODERS ||--o{ JUSTIFICATIONS : "presenta (1:N)"
    HSE_USERS ||--o{ JUSTIFICATIONS : "revisa (0..1:N)"

    CODERS {
        UUID id PK
        VARCHAR cedula UK
        VARCHAR full_name
        VARCHAR email UK
        VARCHAR route
        BOOLEAN is_active
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    HSE_USERS {
        UUID id PK
        VARCHAR email UK
        VARCHAR full_name
        VARCHAR role
        BOOLEAN is_active
        TIMESTAMPTZ created_at
        TIMESTAMPTZ last_login_at
    }

    JUSTIFICATIONS {
        UUID id PK
        UUID coder_id FK "Nullable si CODER_NOT_FOUND"
        UUID hse_user_id FK "Nullable hasta revisión manual"
        VARCHAR sender_email
        VARCHAR sender_name
        TEXT email_subject
        TEXT email_body
        TEXT email_url "Deep link a Outlook/Gmail"
        VARCHAR message_id UK
        VARCHAR intent
        VARCHAR excuse_type
        DATE start_date
        DATE end_date
        NUMERIC ai_confidence
        TEXT ai_reason
        JSONB ai_response "Salida Qwen 2.5"
        VARCHAR validation_status "APPROVED | DISAPPROVED | MANUAL_INTERACTION"
        VARCHAR hse_decision
        TEXT hse_notes
        TIMESTAMPTZ hse_reviewed_at
        JSONB attachments
        TIMESTAMPTZ received_at
        TIMESTAMPTZ created_at
    }
```

**Beneficio Operativo:** Los registros permanecen en la misma tabla `justifications` y nunca se mueven de lugar. El frontend consume la vista enriquecida `v_justifications_dashboard` y filtra por `validation_status` en tiempo real.

---

# 11. SUBFLUJO 3 — Intervención manual HSE y Despacho

## Intervención Manual desde el Panel HSE

Cuando una justificación queda en estado `MANUAL_INTERACTION`, el personal de HSE puede auditar el caso y resolverlo mediante el webhook dedicado:

```mermaid
sequenceDiagram
    autonumber
    actor Coder as 👤 Coder
    actor HSE as 👩‍💼 Funcionario HSE
    participant UI as 💻 Frontend Dashboard HSE
    participant DB as 🗄️ PostgreSQL (justifications)
    participant N8N as ⚙️ Webhook n8n (riwi-hse-dispatch-email)
    participant Mail as 📧 Outlook / Gmail

    Note over UI,DB: Login de HSE verificado con email y password_hash
    HSE->>UI: Abre el panel y selecciona justificación pendiente
    UI->>DB: Consulta datos enriquecidos (v_justifications_dashboard)
    HSE->>UI: Clic en "Abrir correo original" (email_url) para auditar
    HSE->>UI: Corrige datos si aplica (fechas start/end, tipo de excusa o vinculación coder)
    HSE->>UI: Ingresa observaciones y selecciona acción: APPROVE / REJECT / REQUEST_CORRECTION
    UI->>DB: 1. UPDATE directo en PostgreSQL (resolution_mode='MANUAL_HSE', has_human_intervention=TRUE, hse_user_id, correcciones)
    UI->>N8N: 2. POST /webhook/riwi-hse-dispatch-email {justification_id, recipient_email, action, hse_notes, start_date, excuse_type, hse_reviewer_name}
    N8N->>Mail: 3. Despacha correo formal de resolución al coder con notas y nombre del analista
    Mail-->>Coder: Recibe notificación con la decisión final de HSE
    UI-->>HSE: Refleja el estado resuelto en tiempo real con etiqueta de intervención humana
```

## Despacho Automatizado de Correos

```mermaid
flowchart TD
    START(["Persistencia en justifications"]) --> DEC{"validation_status"}
    
    DEC -->|APPROVED| R_OK["12A Despachar Email Aprobación<br/>• Plantilla verde de confirmación<br/>• Fechas autorizadas y tipo de novedad<br/>• Recordatorio de actividades pendientes"]
    
    DEC -->|DISAPPROVED| R_NO["12B Despachar Email Rechazo<br/>• Plantilla formal con ai_reason<br/>• Especifica por qué no cumple el reglamento<br/>• Opción de aportar soporte válido"]
    
    DEC -->|MANUAL_INTERACTION| R_HOLD["12C Encolar para Revisión HSE<br/>• NO se envía rechazo anticipado al coder<br/>• Se genera alerta en el panel administrativo<br/>• Se almacena con deep link para auditoría"]
    
    DEC -->|CODER_NOT_FOUND| R_MISS["06C Despachar Solicitud de Datos<br/>• Informa que el correo no está matriculado<br/>• Pide nombre, cédula y ruta de formación"]

    R_OK --> END_MSG(["📧 Correo enviado al Coder"])
    R_NO --> END_MSG
    R_MISS --> END_MSG
```

---

# 12. Gestión de Errores Técnicos y Resiliencia

El flujo distingue estrictamente entre un **fallo de validación de negocio** y un **fallo técnico de infraestructura**:

```mermaid
flowchart TD
    ERR["Fallo en cualquier nodo del flujo"] --> CLASS{"Tipo de Error"}
    
    CLASS -->|Recuperable<br/>ej. Red transitoria / Rate limit| RETRY["Mecanismo de Reintento<br/>Retry con retroceso exponencial"]
    RETRY -->|Éxito| RESUME["Reanudar Ejecución Normal"]
    RETRY -->|Agotados| CRIT
    
    CLASS -->|Crítico<br/>ej. Timeout IA / DB down| CRIT["Captura por Error Trigger<br/>Registrar log de incidente"]
    CRIT --> AUDIT["Auditoría en Sistema"]
    AUDIT --> FALLBACK["Enrutar caso a MANUAL_INTERACTION<br/>(No emitir resoluciones automáticas en falla técnica)"]
```

---

# 13. Flujo Completo Consolidado

A continuación se presenta el mapa completo de nodos implementados en [`n8n_workflow_email_hse.json`](file:///home/wuisino/Projects/Email-Riwi/n8n_workflow_email_hse.json):

```mermaid
flowchart TD
    E01["01 Webhook Correo Entrante<br/>(Outlook / Gmail)"] --> E02["01 Normalizar Correo<br/>(Campos unificados)"]
    E02 --> E03["02 Extraer Claves e URL<br/>(Cédula regex + Deep Link)"]
    E03 --> E04["03 Buscar Coder en DB<br/>(email / cédula / nombre)"]
    E04 --> E05["04 Evaluar Identificación<br/>(coder_found: true/false)"]
    E05 --> E06{"05 ¿Coder<br/>Encontrado?"}
    
    %% Branch Coder no encontrado
    E06 -->|NO| NF01["06A Preparar Caso No Identificado<br/>(validation_status = DISAPPROVED)"]
    NF01 --> NF02["06B Guardar en DB No Identificado<br/>(coder_id = NULL)"]
    NF02 --> NF03["06C Despachar Email No Identificado<br/>(Pidiendo cédula y nombre)"]
    
    %% Branch Coder encontrado
    E06 -->|SÍ| ST01["07 Preparar Payload Strata Core<br/>(Texto + Adjunto binario/Base64)"]
    ST01 --> ST02["08 HTTP Strata Core Evaluation<br/>(POST /api/evaluate-excuse, 60s)"]
    ST02 --> ST03["09 Validar Schema y Guardrails<br/>(Failover, Luto, Spam, Confianza)"]
    ST03 --> ST04{"10 Decision Switch<br/>(validation_status)"}
    
    %% Salidas de Decisión
    ST04 -->|APPROVED| OK01["11A Guardar Justificación Aprobada<br/>(validation_status = APPROVED)"]
    OK01 --> OK02["12A Despachar Email Aprobación<br/>(Confirmación al coder)"]
    
    ST04 -->|DISAPPROVED| NO01["11B Guardar Justificación Rechazada<br/>(validation_status = DISAPPROVED)"]
    NO01 --> NO02["12B Despachar Email Rechazo<br/>(Notificando motivo)"]
    
    ST04 -->|MANUAL_INTERACTION| MN01["11C Guardar Caso Manual en DB<br/>(validation_status = MANUAL_INTERACTION)"]
    MN01 --> MN02["12C Registrar en Cola Manual HSE<br/>(Disponible en Dashboard)"]
    
    %% Subflujo Despacho Notificación HSE (Disparado desde el Frontend tras UPDATE directo)
    H01["Webhook Despachar Notificación HSE<br/>(POST /riwi-hse-dispatch-email)"] --> H02["14 Despachar Email Notificación HSE<br/>(Correo resolutivo formal al coder)"]

    style E01 fill:#e8f0fe,stroke:#4285f4
    style ST02 fill:#eadcf8,stroke:#8e7cc3
    style OK01 fill:#d4edda,stroke:#28a745
    style NO01 fill:#f8d7da,stroke:#dc3545
    style MN01 fill:#fff3cd,stroke:#ffc107
    style H01 fill:#e8f0fe,stroke:#4285f4
```

---

# 14. Inventario de Nodos del Workflow n8n

| # | Nombre del Nodo | Tipo de Nodo n8n | Responsabilidad Funcional |
| :---: | :--- | :--- | :--- |
| **00** | Webhook Correo Entrante | `n8n-nodes-base.webhook` | Recibir payload de Outlook o Gmail vía Webhook |
| **01** | 01 Normalizar Correo | `n8n-nodes-base.code` | Homogeneizar estructura del mensaje y procesar adjuntos |
| **02** | 02 Extraer Claves e URL | `n8n-nodes-base.code` | Generar `email_url` y extraer posible cédula con regex |
| **03** | 03 Buscar Coder en DB | `n8n-nodes-base.postgres` | Consulta SQL en cascada en la tabla `coders` |
| **04** | 04 Evaluar Identificación | `n8n-nodes-base.code` | Determinar `coder_found` (true/false) y fusionar datos |
| **05** | 05 Coder Encontrado? | `n8n-nodes-base.if` | Bifurcación: continuar evaluación o solicitar datos |
| **06A**| 06A Preparar Caso No Identificado | `n8n-nodes-base.code` | Configurar caso CODER_NOT_FOUND y plantilla HTML |
| **06B**| 06B Guardar en DB No Identificado | `n8n-nodes-base.postgres` | INSERT en `justifications` con `coder_id = NULL` |
| **06C**| 06C Despachar Email No Identificado | `n8n-nodes-base.code` | Enviar correo al remitente solicitando identificación |
| **07** | 07 Preparar Payload Strata Core | `n8n-nodes-base.code` | Empaquetar texto y adjunto Base64 para el motor de IA |
| **08** | 08 HTTP Strata Core Evaluation | `n8n-nodes-base.httpRequest`| POST a `/api/evaluate-excuse` con timeout de 60s |
| **09** | 09 Validar Schema y Guardrails | `n8n-nodes-base.code` | Failover, guardrails deterministas y umbral de score |
| **10** | 10 Decision Switch | `n8n-nodes-base.switch` | Enrutar a APPROVED, DISAPPROVED o MANUAL |
| **11A**| 11A Guardar Justificación Aprobada | `n8n-nodes-base.postgres` | INSERT con `validation_status = 'APPROVED'` |
| **12A**| 12A Despachar Email Aprobación | `n8n-nodes-base.code` | Despachar confirmación positiva al coder |
| **11B**| 11B Guardar Justificación Rechazada | `n8n-nodes-base.postgres` | INSERT con `validation_status = 'DISAPPROVED'` |
| **12B**| 12B Despachar Email Rechazo | `n8n-nodes-base.code` | Despachar notificación de rechazo con motivo |
| **11C**| 11C Guardar Caso Manual en DB | `n8n-nodes-base.postgres` | INSERT con `validation_status = 'MANUAL_INTERACTION'` |
| **12C**| 12C Registrar en Cola Manual HSE | `n8n-nodes-base.code` | Notificar disponibilidad en Dashboard HSE |
| **13** | Webhook Despachar Notificación HSE | `n8n-nodes-base.webhook` | Endpoint de despacho de correo disparado por Frontend tras UPDATE directo |
| **14** | 14 Despachar Email Notificación HSE | `n8n-nodes-base.code` | Construir y enviar correo resolutivo formal al coder con notas del analista |

---

# 15. Secuencia Temporal de una Ejecución Completa

```mermaid
sequenceDiagram
    autonumber
    actor Coder as 👤 Coder
    participant Mail as 📧 Servidor Correo (Outlook/Gmail)
    participant N8N as ⚙️ Orquestador n8n
    participant DB as 🗄️ PostgreSQL
    participant Strata as 🧠 Strata Core API
    participant Ollama as 🦙 Ollama (Qwen 2.5: 1.5B)
    actor HSE as 👩‍💼 Equipo HSE

    Coder->>Mail: Envía correo con justificación y adjunto PDF
    Mail->>N8N: T0: Notifica correo entrante vía Webhook / IMAP
    N8N->>N8N: T1: Normaliza campos y extrae metadatos
    N8N->>DB: T2: Búsqueda del coder en catálogo (email, cédula, nombre)
    DB-->>N8N: Retorna registro del Coder (o no encontrado)
    N8N->>N8N: T3: Construye deep link (email_url) y prepara archivo
    N8N->>Strata: T4: POST /api/evaluate-excuse (payload + doc)
    Strata->>Strata: T5: Extracción con PyMuPDF y OCR
    Strata->>Strata: T6: Limpieza léxica e indexación de términos clave
    Strata->>Strata: T7: Poda inteligente de contexto (≤ 3500 caracteres)
    Strata->>Ollama: T8: Inferencia con evaluator_system_prompt
    Ollama-->>Strata: Retorna respuesta estructurada
    Strata-->>N8N: T9: JSON evaluado (valido, tipo, fechas, confianza)
    N8N->>N8N: T10: Aplica guardrails deterministas de negocio y failover
    N8N->>N8N: T11: Resuelve branch: APPROVED / DISAPPROVED / MANUAL
    N8N->>DB: T12: Persiste registro único en tabla justifications
    alt Caso Aprobado Automáticamente
        N8N->>Mail: T13a: Envía confirmación de aprobación al Coder
        Mail-->>Coder: Recibe notificación de justificación aceptada
    else Caso Rechazado Automáticamente
        N8N->>Mail: T13b: Envía notificación de no aprobación con motivo
        Mail-->>Coder: Recibe notificación de rechazo con soporte de causas
    else Caso Requiere Intervención Manual
        N8N->>HSE: T13c: Encola en Dashboard de Pendientes con deep link
    end
```

---

# 16. Casos de Prueba y Validación Automatizada

La suite automatizada implementada en [`test_workflow_simulation.py`](file:///home/wuisino/Projects/Email-Riwi/test_workflow_simulation.py) valida el comportamiento del sistema ante los siguientes 6 escenarios operativos:

1. **Coder Identificado + Incapacidad Médica Válida:** Coder con correo institucional adjunta certificado EPS Sanitas $\longrightarrow$ `APPROVED`.
2. **Coder No Encontrado:** Remitente envía correo desde buzón externo sin cédula $\longrightarrow$ `CODER_NOT_FOUND` y solicitud de datos.
3. **Calamidad Familiar sin Adjunto:** Coder reporta fallecimiento de familiar sin certificado $\longrightarrow$ Guardrail intercepta y deriva a `MANUAL_INTERACTION`.
4. **Failover Técnico por Caída de Ollama:** Servidor de IA no responde $\longrightarrow$ Contingencia activa `MANUAL_INTERACTION` con confianza 0.0 sin emitir rechazos erróneos.
5. **Causa Injustificada:** Coder explica que no asistió por quedarse dormido $\longrightarrow$ `DISAPPROVED` con notificación explicativa.
6. **Resolución Manual por Webhook HSE:** Analista de bienestar aprueba caso excepcional en el panel web $\longrightarrow$ Actualización en BD y notificación resolutiva.

---

# 17. Resumen Operacional

```mermaid
flowchart LR
    IN["📧 CORREO ENTRANTE<br/>Outlook / Gmail"] --> NORM["⚙️ NORMALIZACIÓN<br/>Extracción de adjuntos y URL"]
    NORM --> IDENT["🗄️ IDENTIFICACIÓN CODER<br/>PostgreSQL (coders)"]
    IDENT --> STRATA["🧠 EVALUACIÓN IA<br/>Strata Core + Qwen 2.5"]
    STRATA --> RULES["⚖️ GUARDRAILS Y BRANCHING<br/>Umbral confianza + Reglas"]
    
    RULES -->|Aprobado| A["🟢 APPROVED"]
    RULES -->|Rechazado| B["🔴 DISAPPROVED"]
    RULES -->|Manual| C["🟡 MANUAL_INTERACTION"]
    
    A --> DB[("💾 POSTGRESQL<br/>Tabla: justifications")]
    B --> DB
    C --> DB
    
    DB --> OUT1["📬 Correo al Coder"]
    DB --> OUT2["💻 Dashboard Web HSE"]
```

La clave fundamental de esta arquitectura es que **n8n no realiza OCR ni inferencia pesada**: los consume como un servicio HTTP especializado en Strata Core. Del mismo modo, Strata Core no administra identidades de coders ni estados relacionales; n8n y PostgreSQL se encargan de toda la orquestación, auditoría y trazabilidad.
