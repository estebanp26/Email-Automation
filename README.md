# Email-Automation (HSE Attendance Justification System con Strata Core)

Sistema automatizado de ingesta, filtración, análisis y resolución de justificaciones de inasistencia/tardanza para el equipo de HSE (Habilidades para la Vida), impulsado por el motor local **Strata Core**.

## 🚀 Arquitectura del Proyecto (Monorepo)

```
Email-Automation/
├── n8n/                # Workflows modulares de orquestación (Squad: Esteban, Jesus, Luis)
├── frontend/           # Dashboard para la Team Leader HSE (Squad: Kevin, Camilo)
├── connection/         # Webhooks y adaptadores Outlook/Gmail (Squad: Samuel)
├── strata-core/        # Motor universal de extracción y evidencia (Squad: Andres, Sebastian)
├── database/           # Schemas PostgreSQL / Supabase y Seeds (Squad: Eliam, Sergio)
├── docs/               # Contratos de API, guías de arquitectura y roadmap
└── .env.example        # Variables de entorno unificadas
```

## 👥 Organización de Squads & Responsables

| Squad | Integrantes | Foco Principal | Rama de Trabajo |
| :--- | :--- | :--- | :--- |
| **n8n Core** | **Esteban (Leader)**, Jesus, Luis | Orquestación, encolamiento y despacho de correos | `feature/n8n-core` |
| **Frontend** | **Kevin**, Camilo | Dashboard Next.js con visor de evidencias espaciales | `feature/frontend-dashboard` |
| **Conexión** | **Samuel** | Webhooks Outlook (Graph API) & Gmail (PubSub) | `feature/email-connections` |
| **Strata Core**| **Andres**, Sebastian | Motor universal de extracción local con Qwen 2.5 y Tesseract | `feature/ai-engine` |
| **Database** | **Eliam**, Sergio | Supabase PostgreSQL, Storage S3 y reglas dinámicas | `feature/db-supabase` |

## 🛠️ Regla de Oro: Config-Driven Architecture
Ninguna regla de negocio o plantilla de correo está quemada en código. Todo se lee dinámicamente de la base de datos para permitir ajustes el lunes sin tocar producción.

---

## 🐳 Despliegue y Ejecución con Docker

Puedes levantar todo el ecosistema (PostgreSQL, Strata Core, Backend API, Frontend y n8n) con un solo comando:

```bash
# 1. Configurar variables de entorno (usa .env.docker como base)
cp .env.docker .env

# 2. Levantar todos los servicios principales
docker compose up -d --build

# 3. (Opcional) Levantar también el escuchador en vivo de Gmail
docker compose --profile worker up -d
```

### URLs de Acceso Local
- **🖥️ Tablero Frontend:** [http://localhost:5173](http://localhost:5173)
- **⚡ Backend API (FastAPI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **🧠 Strata Core API (OCR/IA):** [http://localhost:8001/docs](http://localhost:8001/docs)
- **🔄 Orquestador n8n:** [http://localhost:5678](http://localhost:5678)
- **🗄️ PostgreSQL:** `localhost:5432` (`hse_email_automation`)

Comandos útiles de Docker Compose:
```bash
docker compose ps               # Ver estado de los contenedores
docker compose logs -f backend  # Ver logs en vivo del backend
docker compose down             # Detener todos los servicios conservando datos
docker compose down -v          # Detener y reiniciar base de datos limpia
```

---

## 🔗 Integración Frontend (Dashboard HSE) con Workflow n8n

El frontend se conecta de manera desacoplada con el flujo de automatización orquestado en **n8n** ([`n8n_workflow_email_hse.json`](./n8n_workflow_email_hse.json)) mediante webhooks REST.

### 1. Puntos de Conexión (Webhooks) Enlazados

#### A. Webhook de Despacho Manual HSE (`POST /webhook/riwi-hse-dispatch-email` o `/webhook-test/...`)
- **Nodo destino en n8n:** `node-webhook-hse-dispatch` $\rightarrow$ `14 Despachar Email Notificación HSE`.
- **Propósito:** Disparado inmediatamente cuando el analista de HSE toma una decisión sobre una justificación (Aprobar, Rechazar o Pedir Corrección) desde la interfaz web.
- **Contrato del Payload:**
  ```json
  {
    "justification_id": "c6357532-2555-4a40-a4ff-bd148a8036b2",
    "action": "APPROVED",
    "coder_name": "Valentina Ospina",
    "recipient_email": "valentina.ospina@riwi.io",
    "start_date": "2026-09-27",
    "excuse_type": "calamidad",
    "hse_notes": "Se verificó la situación familiar aportada. Convalidado por 2 días.",
    "hse_reviewer_name": "Paola Admin (HSE)"
  }
  ```
  *Valores de `action`:* `'APPROVED'`, `'DISAPPROVED'`, `'REQUEST_CORRECTION'`.

#### B. Webhook de Ingesta / Prueba de Correo Entrante (`POST /webhook/riwi-email-incoming` o `/webhook-test/...`)
- **Nodo destino en n8n:** `Webhook Correo Entrante`.
- **Propósito:** Permite la ingesta en vivo desde adaptadores de correo (Outlook Graph / Gmail) o desde el botón de simulación del dashboard para validar el pipeline de IA y persistencia.

---

### 2. Estructura y Servicios en el Frontend (`/frontend`)

- **[`src/services/n8n.ts`](./frontend/src/services/n8n.ts):**
  - Manejo de endpoints dinámicos de n8n (por defecto `http://localhost:5678`).
  - Alternador entre modo **Prueba** (`/webhook-test/`) y modo **Producción** (`/webhook/`).
  - Persistencia de configuración en `localStorage` (configurable desde la UI sin reiniciar el servidor).
  - Métodos:
    - `dispatchHseDecision(payload)`: Envía la resolución humana al webhook resolutivo.
    - `sendIncomingEmailSimulation(payload)`: Simula la recepción de correos de prueba.
    - `testN8nConnection()`: Verifica la salud y conectividad con la instancia de n8n.
- **[`src/services/api.ts`](./frontend/src/services/api.ts):**
  - Método `resolveRequestWithN8n`: Actualiza el estado local y simultáneamente despacha la resolución al webhook de n8n.
- **[`src/pages/Requests.tsx`](./frontend/src/pages/Requests.tsx):**
  - Panel integrado **"Resolución Manual HSE & Despacho a n8n"** en la vista de detalle:
    - 🟢 **Aprobar Excusa** (`APPROVED`)
    - 🔴 **Rechazar Caso** (`DISAPPROVED`)
    - 🟡 **Pedir Soporte** (`REQUEST_CORRECTION`)
    - Campos editables para fechas afectadas (`start_date`), tipo de excusa (`excuse_type`) y observaciones obligatorias (`hse_notes`).
    - Alertas visuales con feedback en tiempo real según la respuesta de n8n.
- **[`src/pages/Settings.tsx`](./frontend/src/pages/Settings.tsx):**
  - Tarjeta destacada **"Conexión con n8n Workflow"**:
    - Edición de la URL base de n8n.
    - Selector interactivo entre modo *Prueba* y *Producción*.
    - Botón **"Probar Conectividad con n8n"** para diagnóstico en vivo.
    - Botón **"Simular Envío de Correo Entrante"** para pruebas end-to-end.
    - Visualización de URLs calculadas de los webhooks.
- **Variables de Entorno ([`frontend/.env.example`](./frontend/.env.example)):**
  ```env
  VITE_API_URL=http://localhost:8000
  VITE_N8N_URL=http://localhost:5678
  VITE_N8N_USE_TEST_WEBHOOK=true
  ```

---

### 3. Puesta en Marcha y Pruebas Paso a Paso

1. **Importar el Workflow en n8n:**
   - Accede a tu instancia de n8n (ej. `http://localhost:5678`).
   - Ve a **Workflows** $\rightarrow$ **Import from File** y carga [`n8n_workflow_email_hse.json`](./n8n_workflow_email_hse.json).
   - Haz clic en **Publish / Activate** (para modo producción) o haz clic en **"Listen for test event"** sobre el nodo *Webhook Despachar Notificación HSE* (para depuración en modo prueba).

2. **Ejecutar el Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Abre `http://localhost:5173` en el navegador.

3. **Validar la Conexión:**
   - Dirígete a **Configuración** $\rightarrow$ tarjeta **"Conexión con n8n Workflow"** y pulsa **"Probar Conectividad con n8n"**.
   - En **Bandeja de Entrada / Solicitudes**, selecciona una justificación y pulsa **"Aprobar Excusa"** o **"Rechazar Caso"** para comprobar el disparo y recepción en n8n.

