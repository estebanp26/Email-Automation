# Email-Automation — Sistema de Justificaciones HSE (RIWI)

Automatiza la recepción, evaluación y respuesta de justificaciones de inasistencia/tardanza enviadas por correo al equipo HSE (Habilidades Socioemocionales). Un motor de IA local (**Strata Core** + Qwen 2.5 vía Ollama) lee el correo y sus adjuntos, **n8n** orquesta el flujo, **PostgreSQL** persiste todo y un **dashboard React** permite a HSE resolver los casos dudosos.

---

## Tabla de contenidos

1. [Arquitectura](#arquitectura)
2. [Estructura del repositorio](#estructura-del-repositorio)
3. [Stack](#stack)
4. [Requisitos previos](#requisitos-previos)
5. [Puesta en marcha](#puesta-en-marcha)
6. [Configuración (`.env`)](#configuración-env)
7. [Componentes](#componentes)
8. [Flujo de decisión](#flujo-de-decisión)
9. [Contratos de API](#contratos-de-api)
10. [Pruebas](#pruebas)
11. [Seguridad](#seguridad)
12. [Documentación adicional](#documentación-adicional)
13. [Equipo](#equipo)

---

## Arquitectura

```
 Outlook / Gmail
       │  (conectores Python → payload normalizado)
       ▼
 n8n  ──► PostgreSQL (búsqueda del coder: email → cédula → nombre)
  │
  ├──► Strata Core (FastAPI :8001) ──► PyMuPDF / Tesseract ──► Ollama (qwen2.5:1.5b)
  │
  ├──► Guardrails deterministas + umbral de confianza
  │
  ├──► PostgreSQL (tabla justifications)
  │
  └──► Correo de respuesta al coder  /  cola manual en el Dashboard HSE
```

Principio de diseño: **n8n no hace OCR ni inferencia** (los consume vía HTTP); **Strata Core no conoce identidades ni estados** (eso es de n8n + PostgreSQL).

---

## Estructura del repositorio

```
Email-Automation/
├── strata-core/                      # Motor de extracción + evaluación (FastAPI)
│   ├── server.py                     # API: /health, /api/evaluate-excuse, /api/search
│   ├── engine/  prompts/  schemas/   # Pipeline, prompts y esquemas JSON
│   ├── tests/  test_samples/         # Pruebas y muestras
│   └── requirements.txt
├── frontend/                         # Dashboard HSE (Vite + React + TypeScript)
├── gmail_connector.py                # Ingesta Gmail API + parser Pub/Sub
├── outlook_connector.py              # Ingesta Outlook (IMAP / Microsoft Graph)
├── mail_sender.py                    # Envío multi-proveedor (SMTP / Graph / Gmail)
├── n8n_workflow_email_hse.json       # Workflow n8n importable
├── init_database.sql                 # Esquema PostgreSQL
├── supabase_schema.sql               # Variante del esquema para Supabase
├── docker-compose.yml                # PostgreSQL 16 (Alpine)
├── run.sh                            # Levanta Strata Core + Frontend (+ arranca contenedores existentes)
├── scripts/                          # Scripts auxiliares
├── docs/                             # API_CONTRACTS.md, ROADMAP_NOTION.md
├── *_documentation.md                # Documentación de n8n, base de datos y frontend
├── *.drawio                          # Diagramas ER y del workflow
└── .env.example
```

---

## Stack

| Capa | Tecnología |
| :--- | :--- |
| Orquestación | n8n |
| IA / extracción | FastAPI, PyMuPDF, Tesseract (pytesseract), Ollama + `qwen2.5:1.5b` |
| Base de datos | PostgreSQL 16 (Docker) |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS 4, React Router 7, Recharts, Framer Motion |
| Correo | Microsoft Graph / IMAP (Outlook), Gmail API + Pub/Sub, SMTP |

---

## Requisitos previos

- Docker y Docker Compose
- Python 3.10+ y **binario de Tesseract** instalado en el sistema (requerido por `pytesseract`)
- Node.js 20+ y npm
- [Ollama](https://ollama.com) con el modelo descargado: `ollama pull qwen2.5:1.5b`
- Una instancia de n8n accesible (puerto `5678` por defecto)

---

## Puesta en marcha

### 1. Variables de entorno

```bash
cp .env.example .env
# Edita credenciales (Postgres, Azure/Google, SMTP, Gemini/OpenAI opcionales)
```

### 2. Base de datos

```bash
docker compose up -d
```

> **Ojo:** `docker-compose.yml` monta `./database/migrations` en `docker-entrypoint-initdb.d`, pero esa carpeta **no existe** en esta rama. Aplica el esquema manualmente:
> ```bash
> psql "$DATABASE_URL" -f init_database.sql
> ```

### 3. n8n

1. Levanta tu instancia de n8n.
2. **Workflows → Import from File →** `n8n_workflow_email_hse.json`.
3. Configura las credenciales de PostgreSQL y activa el workflow (o usa *Listen for test event* para depurar).

> `docker-compose.yml` **no** incluye n8n. `run.sh` solo arranca un contenedor ya existente llamado `novasync-n8n`.

### 4. Strata Core

```bash
cd strata-core
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Documentación interactiva: `http://localhost:8001/docs`

### 5. Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Abre `http://localhost:5173`.

### Atajo: todo junto

```bash
./run.sh
```

Arranca (si existen) los contenedores `hse-postgres` y `novasync-n8n`, Strata Core (`:8001`) y el frontend (`:5173`). `Ctrl+C` detiene los procesos y libera los puertos 8001 y 5173.

---

## Configuración (`.env`)

| Grupo | Variables clave |
| :--- | :--- |
| PostgreSQL | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, `DATABASE_URL`, `TZ` |
| n8n | `N8N_HOST`, `N8N_PORT`, `N8N_WEBHOOK_URL`, `N8N_DISPATCH_WEBHOOK_URL`, `N8N_POSTGRES_*` |
| Motor IA | `STRATA_CORE_URL`, `STRATA_CORE_PORT`, `OLLAMA_HOST`, `OLLAMA_MODEL`, `GEMINI_API_KEY`, `OPENAI_API_KEY` |
| Outlook | `OUTLOOK_MAILBOX`, `OUTLOOK_TENANT_ID`, `OUTLOOK_CLIENT_ID`, `OUTLOOK_CLIENT_SECRET` (Graph) · `OUTLOOK_USER`, `OUTLOOK_PASSWORD`, `OUTLOOK_HOST`, `OUTLOOK_PORT` (IMAP) |
| Gmail | `GMAIL_MAILBOX`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GOOGLE_PUBSUB_*` |
| SMTP | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`, `SMTP_DEFAULT_PROVIDER` |

Frontend (`frontend/.env`):

```env
VITE_API_URL=http://localhost:8000
VITE_N8N_URL=http://localhost:5678
VITE_N8N_USE_TEST_WEBHOOK=true
```

---

## Componentes

### Strata Core (`strata-core/`)

Pipeline: triaje PDF (PyMuPDF; si hay texto digital, sin OCR) → visión adaptativa y OCR (Tesseract) → limpieza léxica → poda de contexto (≤ 3500 caracteres) → inferencia con Qwen 2.5 vía Ollama → JSON estructurado.

Ver [`strata-core/README.md`](./strata-core/README.md).

### Conectores de correo

| Archivo | Función |
| :--- | :--- |
| `outlook_connector.py` | Lee correos no leídos por **IMAP4_SSL** (CLI) o **Microsoft Graph** (clase `OutlookGraphClient`). Extrae adjuntos, calcula SHA-256 y reenvía al webhook de n8n con `--forward-n8n`. |
| `gmail_connector.py` | Cliente **Gmail API v1** (OAuth2 con refresh token) y parser de notificaciones **Pub/Sub push**. Normaliza al mismo payload que Outlook (`source_provider='GMAIL'`). |
| `mail_sender.py` | Envía la respuesta HSE por **SMTP**, **Graph** o **Gmail**, preservando el hilo (`In-Reply-To`, `References`, prefijo `Re:`). Incluye plantillas HTML para `APPROVED`, `DISAPPROVED` y `REQUEST_CORRECTION`. |

Uso:

```bash
# Outlook (IMAP), un solo barrido, reenviando a n8n
python outlook_connector.py --mode imap --once --forward-n8n

# Gmail
python gmail_connector.py --forward-n8n

# Enviar una respuesta HSE de prueba
python mail_sender.py --to coder@example.com --action APPROVED --provider SMTP
```

Payload normalizado que entregan los conectores a n8n:

```json
{
  "source_provider": "OUTLOOK",
  "message_id": "…",
  "conversation_id": "…",
  "sender_email": "coder@example.com",
  "sender_name": "Laura Gómez",
  "email_subject": "Justificación inasistencia 25 Septiembre",
  "email_body": "…",
  "received_at": "2026-09-25T14:10:00Z",
  "attachments": [
    { "filename": "incapacidad.pdf", "mime_type": "application/pdf", "size_bytes": 12345, "sha256": "…", "data_base64": "…" }
  ],
  "has_attachments": true
}
```

### Workflow n8n

`n8n_workflow_email_hse.json` — 3 subflujos: **(1)** ingesta e identificación del coder, **(2)** evaluación con Strata Core, **(3)** persistencia, despacho de correo y cola manual. Detalle nodo por nodo en [`n8n_documentation.md`](./n8n_documentation.md).

### Base de datos

Modelo de 3 entidades: `coders`, `hse_users`, `justifications` (registro único por correo procesado, con `validation_status`, respuesta de IA en `JSONB` y datos de la revisión humana). El frontend consume la vista `v_justifications_dashboard`. Ver [`database_documentation.md`](./database_documentation.md) y `riwi_justifications_ER.drawio`.

### Frontend (`frontend/`)

Dashboard para HSE: bandeja de solicitudes, directorio de coders, resolución manual (Aprobar / Rechazar / Pedir soporte) y panel de conexión con n8n (URL base, modo prueba/producción, test de conectividad, simulación de correo entrante).

Archivos clave: `src/services/n8n.ts`, `src/services/api.ts`, `src/pages/Requests.tsx`, `src/pages/Settings.tsx`. Ver [`frontend_architecture_plan.md`](./frontend_architecture_plan.md).

---

## Flujo de decisión

| Estado | Condición | Acción |
| :--- | :--- | :--- |
| `APPROVED` | `valido = true` y `requiere_revision_manual = false` y `confianza_score ≥ 0.80` | Guarda y notifica aprobación al coder |
| `DISAPPROVED` | `valido = false` y `requiere_revision_manual = false` | Guarda y notifica rechazo con motivo |
| `MANUAL_INTERACTION` | `requiere_revision_manual = true` o `confianza_score < 0.80` o fallo técnico | Guarda y encola en el dashboard; **no** se envía rechazo anticipado |
| `CODER_NOT_FOUND` | Sin coincidencia por email, cédula ni nombre | Guarda con `coder_id = NULL` y pide cédula/nombre/ruta al remitente |

**Guardrails deterministas** (nodo `09 Validar Schema y Guardrails`):

- **Luto/calamidad sin adjunto** → revisión manual.
- **Spam/publicidad** (descuentos, cursos…) → `no_identificado`, revisión manual.
- **Falla técnica con soporte** (ticket, proveedor de internet…) → aprobada.
- **Caída de Ollama / timeout** → failover: `valido=false`, `confianza=0.0`, revisión manual (evita rechazos injustos por fallos de infraestructura).

---

## Contratos de API

### Strata Core

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/health` | Estado del servicio y del modelo en Ollama |
| `POST` | `/api/evaluate-excuse` | Multipart: `file`, `email_body`, `email_subject`, `rules_json` (todos opcionales). Devuelve el veredicto |
| `POST` | `/api/search` | Búsqueda espacial: coordenadas `[x0, y0, x1, y1]` de cada coincidencia |

Respuesta de `/api/evaluate-excuse`:

```json
{
  "valido": true,
  "tipo_novedad": "inasistencia_medica",
  "fecha_afectada": "2026-09-25",
  "motivo_decision": "…",
  "confianza_score": 0.95,
  "requiere_revision_manual": false,
  "detalles_adjunto": { "tiene_firma_o_sello": true, "paginas_consultadas": [1] },
  "tiempo_procesamiento_segundos": 8.42
}
```

### Webhooks de n8n

| Ruta | Uso |
| :--- | :--- |
| `POST /webhook/riwi-email-incoming` | Ingesta de correo normalizado (conectores o simulación desde el dashboard) |
| `POST /webhook/riwi-hse-dispatch-email` | Despacho de la decisión manual de HSE |

Variantes de depuración: `/webhook-test/...`.

Payload de despacho HSE:

```json
{
  "justification_id": "c6357532-2555-4a40-a4ff-bd148a8036b2",
  "action": "APPROVED",
  "coder_name": "Valentina Ospina",
  "recipient_email": "valentina.ospina@riwi.io",
  "start_date": "2026-09-27",
  "excuse_type": "calamidad",
  "hse_notes": "Se verificó la situación aportada.",
  "hse_reviewer_name": "Paola Admin (HSE)"
}
```

`action` ∈ `APPROVED` · `DISAPPROVED` · `REQUEST_CORRECTION`. Contratos completos en [`docs/API_CONTRACTS.md`](./docs/API_CONTRACTS.md).

---

## Pruebas

Pruebas offline (no requieren credenciales):

```bash
python outlook_connector.py --test
python gmail_connector.py --test
python mail_sender.py --test
```

Escenarios de flujo completo (coder identificado, coder no encontrado, calamidad sin adjunto, caída de Ollama, causa injustificada, resolución manual por webhook):

```bash
python test_workflow_simulation.py
```

Otros: `test_live_n8n_database.py` (pruebas contra n8n/BD en vivo) y, en `strata-core/`, `test_squad2_evaluator.py` y `generate_test_cases.py`.

---

## Seguridad

- **Nunca** subas `.env` al repositorio.
- `docker-compose.yml` usa contraseñas por defecto de desarrollo si no defines `POSTGRES_PASSWORD`; cámbiala siempre fuera de local.
- Las credenciales de Azure/Google/SMTP en `.env.example` son placeholders.
- Los adjuntos se procesan localmente (Strata Core + Ollama); no se envían a servicios externos de IA en el flujo principal.

---

## Documentación adicional

| Documento | Contenido |
| :--- | :--- |
| [`n8n_documentation.md`](./n8n_documentation.md) | Flujo n8n completo, guardrails, secuencias |
| [`database_documentation.md`](./database_documentation.md) | Esquema y relaciones |
| [`frontend_architecture_plan.md`](./frontend_architecture_plan.md) | Arquitectura del dashboard |
| [`docs/API_CONTRACTS.md`](./docs/API_CONTRACTS.md) | Contratos entre componentes |
| [`docs/ROADMAP_NOTION.md`](./docs/ROADMAP_NOTION.md) | Roadmap |
| [`strata-core/README.md`](./strata-core/README.md) | Motor de IA |

---

## Equipo

| Squad | Foco | Rama |
| :--- | :--- | :--- |
| n8n Core | Orquestación, encolamiento, despacho | `feature/n8n-core` |
| Frontend | Dashboard HSE | `feature/frontend-dashboard` |
| Conexión | Outlook (Graph) y Gmail (Pub/Sub) | `feature/email-connections` |
| Strata Core | Extracción local con Qwen 2.5 y Tesseract | `feature/ai-engine` |
| Database | PostgreSQL / Supabase | `feature/db-supabase` |
