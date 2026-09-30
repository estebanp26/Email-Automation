# Email-Automation — Sistema de Justificaciones HSE (RIWI)

Sistema automatizado de ingesta, evaluación y respuesta de justificaciones de inasistencia/tardanza para el equipo HSE. Motor local **Strata Core** (FastAPI + PyMuPDF + Tesseract + Qwen 2.5 vía Ollama), orquestación **n8n**, persistencia **PostgreSQL 16** y **dashboard React + Vite**.

## 1. Arquitectura real

```
Outlook / Gmail (conectores Python / listener IMAP)
        │ payload normalizado
        ▼
n8n (:5678) ──► PostgreSQL (:5432, db hse_email_automation)
   │
   ├──► Strata Core (:8001) ──► PyMuPDF / Tesseract ──► Ollama (qwen2.5:1.5b, con fallback sin IA)
   │
   ├──► Guardrails deterministas + umbral confianza
   │
   ├──► PostgreSQL (tablas coders, justifications)
   │
   └──► Correo respuesta al coder / cola manual en Dashboard HSE (:5173)
```

Principio: **n8n no hace OCR ni inferencia** (la consume por HTTP); **Strata Core no gestiona identidades** (eso es n8n + Postgres).

> `backend/app` (FastAPI `:8000`, `/api/v1/...`) es código legacy/experimental. El sistema en producción que levantan `run.py/run.sh` usa **Strata Core `:8001`** (`/api/kpis`, `/api/requests`, `/api/students`, `/health`, `/api/evaluate-excuse`) como backend de datos del frontend.

## 2. Estructura del repositorio

```
.
├── strata-core/server.py       # Backend real (FastAPI :8001)
├── strata-core/requirements.txt
├── frontend/                   # Dashboard HSE (Vite + React 19 + TS, :5173)
├── backend/app/                # Backend legacy :8000 (no lo levanta run.py)
├── database/migrations/        # 001_*.sql, 002_seed, 003_attendance, 004_indexes
├── docker-compose.yml          # Solo postgres (servicio "postgres", container hse-postgres)
├── run.py / run.sh / run.ps1 / run.bat  # Lanzadores todo-en-uno
├── scripts/gmail_live_listener.py       # Escuchador IMAP en vivo (opcional)
├── gmail_connector.py / outlook_connector.py / mail_sender.py
├── n8n_workflow_email_hse.json
└── .env.example
```

## 3. Requisitos previos

- Docker y Docker Compose
- Python 3.10+ (`python3 --version`)
- Node.js 20+ y npm (`node --version`)
- Binario Tesseract (`which tesseract`)
- Ollama (opcional, solo para inferencia real): `ollama serve` + `ollama pull qwen2.5:1.5b`. Sin Ollama el sistema arranca igual con veredicto fallback.
- Instancia n8n accesible (`:5678`)

Puertos usados: `5432` Postgres, `8001` Strata, `5173` Frontend, `5678` n8n.

## 4. Puesta en marcha paso a paso (manual, recomendado)

### Paso 0 — Clonar y entrar

```bash
cd Email-Riwi
```

### Paso 1 — Variables de entorno raíz

```bash
cp .env.example .env
```

Valores por defecto que ya coinciden con Docker local (`POSTGRES_USER=hse_admin`, `POSTGRES_PASSWORD=hse_segura_123`, `POSTGRES_DB=hse_email_automation`, `STRATA_CORE_URL=http://localhost:8001`). Cámbialos solo para producción. Nunca subas `.env` a Git.

Para el listener de Gmail en vivo agrega en `.env`:

```env
GMAIL_USER=tu_correo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### Paso 2 — Base de datos PostgreSQL

Si es primera vez (sin contenedor previo):

```bash
docker compose up -d
docker compose ps
```

Esto crea `hse-postgres` y ejecuta automáticamente `database/migrations/*.sql` (solo en primer arranque con volumen vacío).

Si ya tienes contenedores corriendo (ej. `riwi-postgres`, `riwi-n8n`), **no** ejecutes `compose up` de nuevo, solo verifícalos:

```bash
docker ps --format "{{.Names}} {{.Status}} {{.Ports}}"
```

> Nota: `docker-compose.yml` solo define Postgres, no n8n. `run.py/run.sh` intentan hacer `docker start hse-postgres` y `novasync-n8n`; si tus contenedores se llaman distinto (`riwi-*`), ese paso solo muestra un aviso y continúa.

### Paso 3 — Strata Core (backend real `:8001`)

```bash
cd strata-core
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt psycopg2-binary python-dotenv
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Verifica:

- Docs: `http://localhost:8001/docs`
- Salud: `http://localhost:8001/health`
- KPIs: `http://localhost:8001/api/kpis` (si devuelve `{"total":...}` hay conexión a Postgres; si devuelve ceros con `"error"`, revisa `.env` de DB)

`psycopg2-binary` no está en `requirements.txt` pero es obligatorio para `/api/kpis`, `/api/requests`, `/api/students`.

### Paso 4 — Frontend (`:5173`)

En otra terminal, desde la raíz:

```bash
cd frontend
echo "VITE_API_URL=http://localhost:8001" > .env
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Abre `http://localhost:5173`.

> `frontend/.env.example` dice `http://localhost:8000`, está desactualizado. El valor correcto es `http://localhost:8001` (Strata). `vite.config.ts` además proxea `/api -> http://localhost:8001`.

### Paso 5 — n8n

1. Abre `http://localhost:5678`.
2. `Workflows → Import from File → n8n_workflow_email_hse.json`.
3. Configura credencial Postgres (`hse_admin / hse_segura_123 / hse_email_automation @ localhost:5432`).
4. `Activate` (producción `/webhook/...`) o `Listen for test event` (depuración `/webhook-test/...`).
5. Desde el frontend en `Configuración → Conexión con n8n` pulsa `Probar Conectividad`, y en `Solicitudes` usa `Aprobar / Rechazar` para validar el despacho (`POST /webhook/riwi-hse-dispatch-email`).

Webhooks:

| Ruta | Uso |
| :--- | :--- |
| `POST /webhook/riwi-email-incoming` | Ingesta correo normalizado |
| `POST /webhook/riwi-hse-dispatch-email` | Decisión manual HSE (`APPROVED` / `DISAPPROVED` / `REQUEST_CORRECTION`) |

### Paso 6 — Listener Gmail en vivo (opcional)

```bash
# desde la raíz, con el venv de strata-core activo
python scripts/gmail_live_listener.py
```

Filtra spam y solo despacha correos con palabras HSE (`justificación`, `incapacidad`, `cita médica`, `calamidad`, etc.). Si no hay `GMAIL_USER/GMAIL_APP_PASSWORD`, omítelo.

## 5. Atajo todo-en-uno

```bash
# Linux/macOS
./run.sh
# o multiplataforma
python run.py
# Windows
run.bat
# o
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Hace, en orden: (1) `docker start hse-postgres/novasync-n8n` si existen, (2) Strata `:8001` con el venv si existe, (3) Frontend `:5173`, (4) listener Gmail. `Ctrl+C` detiene todo y libera `8001/5173`.

URLs al terminar:

- Frontend: `http://localhost:5173` · Solicitudes: `http://localhost:5173/requests` · Coders: `http://localhost:5173/students`
- Strata: `http://localhost:8001/docs`
- n8n: `http://localhost:5678`
- Postgres: `localhost:5432`

## 6. Contratos API (Strata `:8001`)

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/health` | Estado + modelo Ollama |
| `POST` | `/api/evaluate-excuse` | `file` / `email_body` / `email_subject` / `rules_json` → veredicto (`valido`, `categoria_sugerida`, `confianza_score`, `requiere_revision_manual`) |
| `GET` | `/api/kpis` | KPIs dashboard |
| `GET` | `/api/requests?status=&limit=` | Bandeja (`approved`/`denied`/`pending_review`) |
| `GET` | `/api/requests/recent?limit=10` | Carrusel inicio |
| `GET` | `/api/requests/weekly` | Gráfico semanal |
| `GET` | `/api/students` | Coders |
| `POST` | `/api/requests/{id}/resolve` | `{action: APPROVED/DISAPPROVED, notes, reviewer_name}` |

## 7. Pruebas

```bash
python outlook_connector.py --test
python gmail_connector.py --test
python mail_sender.py --test
python test_workflow_simulation.py
```

## 8. Solución de problemas

- `docker compose up` falla por nombre en uso: ya tienes `riwi-postgres` arriba, usa ese y no crees otro.
- `/api/kpis` devuelve ceros con `error`: falta `psycopg2-binary` o `.env` de DB incorrecto.
- Frontend vacío / error CORS: revisa que `frontend/.env` sea `VITE_API_URL=http://localhost:8001`, no `:8000`.
- `ollama list` → `could not connect`: ejecuta `ollama serve &` primero. Sin Ollama igual funciona (fallback).
- Puerto ocupado `8001/5173`: `fuser -k 8001/tcp; fuser -k 5173/tcp`.
- `psql: command not found`: usa `docker exec -it <pg-container> psql -U hse_admin -d hse_email_automation`.
- Listener Gmail se cierra al instante: faltan `GMAIL_USER/GMAIL_APP_PASSWORD` en `.env`.

## 9. Seguridad

- Nunca subas `.env`.
- Cambia `POSTGRES_PASSWORD` fuera de local.
- Adjuntos se procesan en local (Strata + Ollama), no se envían a IA externa en el flujo principal.

## 10. Subir cambios a `develop` (git push)

Ya estás en la rama `develop` con remoto `origin` (`https://github.com/estebanp26/Email-Automation.git`). El `push` lo haces tú; estos son los comandos:

```bash
# 1. Ver qué cambió (deberías ver README.md y strata-core/server.py)
git status --short
git diff --stat

# 2. Revisa el diff antes de subir
git diff README.md strata-core/server.py

# 3. Agrega solo los archivos intencionales (no uses git add . a ciegas)
git add README.md strata-core/server.py .gitignore

# 4. Confirma que no se cuela nada sensible (no debe aparecer .env ni .venv ni node_modules)
git status --short

# 5. Commit (usa el estilo del repo: feat/fix/docs + alcance)
git commit -m "docs: pasos de ejecución verificados y fix ai_recommendation en /api/requests"

# 6. Trae lo último de develop para evitar rechazos
git pull --rebase origin develop

# 7. Sube a develop
git push origin develop
```

Notas:

- `.env`, `frontend/.env`, `.venv/`, `node_modules/`, `dist/` y `temp_processing/` están en `.gitignore` y **no** se suben (verificados: `git check-ignore` los excluye y `git ls-files` confirma que solo `.env.example` está versionado).
- Si `git push` es rechazado por cambios remotos, repite el paso 6 y resuelve el rebase antes de reintentar.
- Si prefieres PR en vez de push directo: `git checkout -b feature/mi-cambio && git push -u origin feature/mi-cambio`, luego abre el PR contra `develop` en GitHub.
