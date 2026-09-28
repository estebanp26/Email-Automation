# Plan de Arquitectura y Documentación del Frontend — Dashboard HSE RIWI

**Proyecto:** Panel Administrativo de Habilidades Socioemocionales (HSE) para Gestión de Justificaciones  
**Audiencia Principal:** Equipo de Habilidades Socioemocionales (psicólogos, coordinadores de bienestar, directores de ruta)  
**Integración:** PostgreSQL 15+ (Vista `v_justifications_dashboard`) y Webhook de n8n (`riwi-hse-manual-decision`)  
**Fecha de Publicación:** 2026-09-27  

---

## 1. Visión del Producto y Arquetipo de Usuario

El **Frontend de HSE** es una aplicación web diseñada específicamente para personal no técnico del área de acompañamiento humano de RIWI. Su objetivo es convertir un flujo masivo de correos electrónicos en una experiencia operativa clara, visual y de alta eficiencia.

### Arquetipo de Usuario:
* **Rol:** Profesional de Habilidades Socioemocionales / Team Leader.
* **Objetivo:** Auditar decisiones automáticas de la IA, resolver casos dudosos o excepcionales (luto, calamidades, falta de documentos) y mantener la trazabilidad de los coders en sus rutas formativas.
* **Puntos de Dolor Históricos:**
  * Tener que buscar correos perdidos en una bandeja compartida.
  * No saber si un coder ya adjuntó la constancia médica o si es un documento antiguo.
  * Inconsistencias en fechas o tipos de excusa cuando la IA tiene baja certidumbre.
  * Falta de trazabilidad sobre qué analista de HSE atendió cada caso.
* **Solución del Frontend:**
  * **Autenticación Directa de HSE:** Login por correo y contraseña contra `hse_users` (validando `password_hash`), registrando la autoría estricta de cada acción.
  * **Edición y Corrección en Pantalla:** Capacidad del analista para corregir fechas (`start_date`, `end_date`), reclasificar la excusa (`excuse_type`) y vincular manualmente el Coder (`coder_id`) si no fue identificado.
  * **Actualización Inmediata en Base de Datos:** El frontend ejecuta el `UPDATE` directo en PostgreSQL marcando `resolution_mode = 'MANUAL_HSE'` y `has_human_intervention = TRUE`.
  * **Despacho Desacoplado de Correos:** Tras guardar en BD, invoca el webhook ligero de n8n para enviar la respuesta formal al coder sin bloquear la UI.

---

## 2. Stack Tecnológico Recomendado

```
┌────────────────────────────────────────────────────────┐
│                   CAPA DE PRESENTACIÓN                  │
│   Next.js 14+ (App Router) + TypeScript + Tailwind CSS  │
│   Componentes UI: Shadcn UI + Radix UI + Lucide Icons  │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│               CAPA DE DATOS Y TIEMPO REAL              │
│   TanStack Query v5 (React Query)                      │
│   Server-Sent Events (SSE) o WebSocket / Polling       │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│     PostgreSQL / API      │ │    Webhook n8n Decisión   │
│  v_justifications_dash    │ │  POST /riwi-hse-decision  │
└───────────────────────────┘ └───────────────────────────┘
```

* **Framework:** Next.js (App Router) con TypeScript para renderizado híbrido (SSR para carga inicial veloz y Client Components para reactividad).
* **Estilos:** Tailwind CSS con la librería de componentes **Shadcn UI** (diseño sobrio, accesible y personalizable con paleta corporativa de RIWI).
* **Gestión de Estado y Servidor:** **TanStack Query (React Query)** con revalidación en segundo plano y mutaciones optimistas.
* **Iconografía:** Lucide React (`CheckCircle`, `XCircle`, `AlertCircle`, `ExternalLink`, `FileText`, `Clock`).

---

## 3. Arquitectura de Navegación y Vistas

El panel se compone de una vista principal en formato Dashboard con cuatro secciones fundamentales:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Logo RIWI]  Panel de Justificaciones HSE               (User: Laura G) │
├─────────────────────────────────────────────────────────────────────────┤
│  [ Total Hoy: 28 ]  [ Aprobadas: 20 ]  [ Rechazadas: 5 ]  [ ⚠️ Manual: 3 ] │
├─────────────────────────────────────────────────────────────────────────┤
│  🔍 Buscar por Coder, Cédula o Asunto...         [ Filtro Ruta: Todas ▾ ]│
├─────────────────────────────────────────────────────────────────────────┤
│  [ Todas (28) ] | [ 🔴 Pendientes HSE (3) ] | [ Aprobadas (20) ] | [ Rechazadas (5) ] │
├─────────────────────────────────────────────────────────────────────────┤
│  TABLA DE JUSTIFICACIONES                                               │
│  ┌──────────┬─────────────┬──────────────┬───────────────┬────────────┐ │
│  │ Estado   │ Fecha Nov.  │ Coder / Ruta │ Tipo / Motivo │ Acciones   │ │
│  ├──────────┼─────────────┼──────────────┼───────────────┼────────────┤ │
│  │ 🟡 PEND. │ 27-Sep-2026 │ Valentina O. │ Calamidad     │ [Revisar]  │ │
│  │ 🟢 APROB │ 25-Sep-2026 │ Santiago M.  │ Médica EPS    │ [Ver]      │ │
│  │ 🔴 RECH. │ 24-Sep-2026 │ Desconocido  │ No Coder      │ [Ver]      │ │
│  └──────────┴─────────────┴──────────────┴───────────────┴────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.1. Tarjetas Métricas Superiores (KPIs)
* **Total Recibidas (Hoy):** Contador de correos procesados en las últimas 24 horas.
* **Aprobadas Automáticas:** Porcentaje de automatización exitosa por Qwen 2.5 sin intervención humana.
* **Rechazadas Automáticas:** Casos no válidos o sin identificación.
* **Requieren Atención HSE:** Contador en color ámbar/rojo con badge pulsante que indica cuántos casos están bloqueados en `MANUAL_INTERACTION`.

### 3.2. Pestañas de Filtrado Rápido
1. **Pendientes de Revisión HSE (Prioridad 1):** Filtra estrictamente `validation_status = 'MANUAL_INTERACTION'`. Muestra los casos que requieren juicio humano (ej. calamidades, fallos de IA, documentos dudosos).
2. **Todas:** Historial cronológico unificado ordenado por `created_at DESC`.
3. **Válidas (Aprobadas):** Registros con `validation_status = 'APPROVED'`.
4. **No Válidas (Rechazadas):** Registros con `validation_status = 'DISAPPROVED'`.

---

## 4. Modal / Drawer de Detalle y Resolución Manual

Al hacer clic en cualquier fila o en el botón **[Revisar]**, se despliega un Drawer lateral o Modal enriquecido con la información completa del caso:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ DETALLE DE JUSTIFICACIÓN #c6357532-2555                                 │
├─────────────────────────────────────────────────────────────────────────┤
│ 👤 INFORMACIÓN DEL CODER                                                │
│ Nombre: Valentina Ospina         Cédula: 1098765432                     │
│ Correo: valentina.ospina@riwi.io  Ruta: Python AI Specialist            │
│                                                                         │
│ ✉️ METADATOS DEL CORREO ORIGINAL                                         │
│ Asunto: Urgente: Calamidad familiar                                     │
│ Fecha Recepción: 27/09/2026 08:31 AM                                    │
│ [ 🔗 Abrir Correo Original en Outlook / Gmail ]  <-- Botón Deep Link     │
│                                                                         │
│ 🤖 ANÁLISIS DE INTELIGENCIA ARTIFICIAL (Qwen 2.5)                       │
│ Confianza: [██████████████░░░░] 90%                                     │
│ Tipo detectado: Calamidad Familiar                                      │
│ Razón IA: Reporte de fallecimiento de familiar sin soporte adjunto.     │
│ Fechas: 27/09/2026 a 28/09/2026 (2 días calculados)                     │
│                                                                         │
│ 📎 ADJUNTOS Y DOCUMENTOS                                                │
│ Estado: Sin archivos adjuntos detectados en el correo.                  │
│                                                                         │
│ ✍️ INTERVENCIÓN Y DECISIÓN DE HSE                                        │
│ Observaciones / Justificación de la decisión:*                          │
│ [ Se contactó a la coder vía telefónica y se verificó el caso...      ] │
│                                                                         │
│   [ ✅ Aprobar Excusa ]   [ ❌ Rechazar ]   [ ⚠️ Pedir Soporte ]         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Capacidades de Edición y Acciones del Modal:
1. **Auditoría con Deep Link al Correo (`email_url`):** Botón de acceso inmediato al mensaje original en Outlook/Gmail.
2. **Corrección de Datos Extraídos:**
   * **Buscador/Selector de Coder:** Si el caso ingresó como `CODER_NOT_FOUND`, el analista puede buscar al coder por nombre o cédula en un dropdown y asociar su `coder_id`.
   * **Selectores de Fechas (`start_date` / `end_date`):** Permite corregir los días reales de la inasistencia si la IA se equivocó.
   * **Reclasificador de Novedad (`excuse_type`):** Selector para cambiar la categoría (ej. de `no_identificado` a `inasistencia_medica`, `calamidad`, etc.).
3. **Formulario de Resolución y Trazabilidad Humana:**
   * Campo obligatorio: `hse_notes` (comentarios y soporte de la decisión).
   * Botón Verde: `APPROVE` $\rightarrow$ Guarda en BD con `validation_status = 'APPROVED'`, `resolution_mode = 'MANUAL_HSE'`, `has_human_intervention = TRUE`, `hse_user_id = user.id`.
   * Botón Rojo: `DISAPPROVE` $\rightarrow$ Guarda en BD con `validation_status = 'DISAPPROVED'`, `resolution_mode = 'MANUAL_HSE'`, `has_human_intervention = TRUE`.
   * Botón Ámbar: `REQUEST_CORRECTION` $\rightarrow$ Guarda notas y solicita soporte adicional.
   * **Despacho Automático:** Inmediatamente tras el éxito del `UPDATE` en BD, el frontend dispara una petición asíncrona a n8n (`POST /riwi-hse-dispatch-email`) para enviar el correo formal al coder con las notas y el nombre del analista.

---

## 5. Contratos de API entre Frontend, Base de Datos y n8n

### 5.1. Consulta de Justificaciones (Lectura desde BD / API Backend)
* **Endpoint:** `GET /api/justifications`
* **Query Params:**
  * `status`: `ALL` | `APPROVED` | `DISAPPROVED` | `MANUAL_INTERACTION`
  * `route`: `Node.js` | `Java` | `Python` | etc.
  * `search`: Texto para buscar por nombre, cédula o asunto.
  * `page`: Número de página (default 1).
  * `limit`: Cantidad por página (default 25).
* **Respuesta Exitosa (`200 OK`):**
```json
{
  "total": 142,
  "page": 1,
  "limit": 25,
  "data": [
    {
      "id": "c6357532-2555-4a40-a4ff-bd148a8036b2",
      "validation_status": "MANUAL_INTERACTION",
      "coder_display_name": "Valentina Ospina",
      "coder_cedula": "1098765432",
      "coder_route": "Python AI Specialist",
      "sender_email": "valentina.ospina@riwi.io",
      "email_subject": "Urgente: Calamidad familiar",
      "email_url": "https://outlook.office.com/mail/deeplink/read/AAMkAGI...",
      "excuse_type": "calamidad",
      "start_date": "2026-09-27",
      "end_date": "2026-09-28",
      "total_days": 2,
      "ai_confidence": 0.90,
      "ai_reason": "Reporte de fallecimiento de familiar sin soporte adjunto. Requiere validación manual de HSE.",
      "has_attachments": false,
      "created_at": "2026-09-27T13:31:00Z"
    }
  ]
}
```

---

### 5.2. Autenticación y Mutación Directa en Base de Datos

#### A. Autenticación de Personal HSE (`POST /api/auth/login`)
* **Payload:** `{ "email": "laura.gomez@riwi.io", "password": "mipasswordseguro" }`
* **Mecanismo:** El endpoint consulta `hse_users WHERE email = $1`, verifica el hash con `bcrypt.compare(password, user.password_hash)` y retorna un token JWT que incluye `{ id, email, full_name, role }`.

#### B. Actualización y Validación del Caso (`PUT /api/justifications/:id`)
El frontend envía las correcciones y la decisión tomada por el usuario autenticado:
* **Endpoint:** `PUT /api/justifications/:id`
* **Headers:** `Authorization: Bearer <JWT_HSE_USER>`
* **Payload:**
```json
{
  "action": "APPROVED",
  "hse_notes": "Se verificó incapacidad médica aportada. Se convalida excusa por 2 días.",
  "start_date": "2026-09-25",
  "end_date": "2026-09-26",
  "excuse_type": "inasistencia_medica",
  "coder_id": "c001-uuid-si-fue-corregido"
}
```
* **Acción en Base de Datos:**
```sql
UPDATE justifications 
SET 
    validation_status = $1,
    resolution_mode = 'MANUAL_HSE',
    has_human_intervention = TRUE,
    hse_user_id = $2, -- ID extraído del token JWT del login
    hse_decision = $1,
    hse_notes = $3,
    start_date = $4,
    end_date = $5,
    excuse_type = $6,
    coder_id = COALESCE($7, coder_id),
    hse_reviewed_at = CURRENT_TIMESTAMP
WHERE id = $8;
```

#### C. Disparo del Despacho de Correo vía n8n (`POST /riwi-hse-dispatch-email`)
Una vez completado el `UPDATE` en PostgreSQL de forma instantánea, el backend/frontend invoca el webhook ligero de n8n para que construya el HTML y envíe el correo al estudiante:
* **Endpoint:** `POST https://n8n.riwi.io/webhook/riwi-hse-dispatch-email`
* **Payload:**
```json
{
  "justification_id": "c6357532-2555-4a40-a4ff-bd148a8036b2",
  "action": "APPROVED",
  "coder_name": "Valentina Ospina",
  "recipient_email": "valentina.ospina@riwi.io",
  "start_date": "2026-09-25",
  "excuse_type": "inasistencia_medica",
  "hse_notes": "Se verificó incapacidad médica aportada. Se convalida excusa por 2 días.",
  "hse_reviewer_name": "Laura Gómez (HSE)"
}
```

---

## 6. Jerarquía de Componentes en React / Next.js

```text
src/
├── app/
│   ├── layout.tsx                # Layout principal, Providers (React Query, Toaster)
│   ├── page.tsx                  # Dashboard principal
│   └── login/page.tsx            # Autenticación de personal HSE
├── components/
│   ├── dashboard/
│   │   ├── MetricCards.tsx       # Tarjetas de contadores (Aprobadas, Rechazadas, Manuales)
│   │   ├── StatusTabs.tsx        # Selector de pestañas de estado
│   │   ├── SearchAndFilters.tsx  # Barra de búsqueda y selector de ruta
│   │   └── JustificationsTable.tsx # Tabla principal con Badges y acciones
│   ├── detail/
│   │   ├── JustificationDrawer.tsx # Drawer lateral con el detalle completo
│   │   ├── CoderProfileCard.tsx  # Ficha del coder (nombre, cédula, ruta)
│   │   ├── AiAnalysisSection.tsx # Indicadores de Qwen 2.5 (confianza, razón)
│   │   ├── EmailDeepLinkButton.tsx # Botón con enlace al correo original
│   │   └── ManualDecisionForm.tsx # Formulario con botones de Aprobar/Rechazar
│   └── ui/                       # Componentes base Shadcn (Button, Dialog, Badge, Input)
├── hooks/
│   ├── useJustifications.ts      # Query hook para listar y filtrar
│   └── useSubmitDecision.ts      # Mutation hook hacia n8n con Toasts y revalidación
└── lib/
    ├── api.ts                    # Cliente HTTP (fetch / axios)
    └── types.ts                  # Definiciones de TypeScript
```

---

## 7. Estrategia de Actualización en Tiempo Real

Para que el personal de HSE vea nuevos correos en la bandeja de entrada inmediatamente sin tener que recargar la página:
1. **Fase 1 (Inmediata / MVP):** **Polling Inteligente con TanStack Query**.
   * Se configura `refetchInterval: 12000` (cada 12 segundos) únicamente mientras la ventana del navegador esté activa (`refetchOnWindowFocus: true`).
2. **Fase 2 (Tiempo Real Nativo):** **Server-Sent Events (SSE)**.
   * La base de datos emite un trigger `NOTIFY new_justification` en cada `INSERT` de la tabla `justifications`.
   * Una ruta en Next.js (`/api/realtime`) escucha la notificación de PostgreSQL y envía un evento al navegador, provocando que React Query invalide la caché instantáneamente y muestre una notificación Toast en pantalla: *"Nuevo correo recibido de Santiago Morales"*.

---

## 8. Cronograma de Implementación y Fases

| Fase | Alcance | Entregable |
| :---: | :--- | :--- |
| **Fase 1: Setup y UI Base** | Configuración de Next.js 14, Tailwind, Shadcn UI y componentes de estructura. | Maquetación estática del Dashboard y Tabla. |
| **Fase 2: Conexión con PostgreSQL** | Creación de endpoints API internos consumiendo `v_justifications_dashboard`. | Listado dinámico con filtros por estado y buscador funcional. |
| **Fase 3: Modal de Detalle y Enlaces** | Implementación del Drawer de detalle, visualización de `ai_reason` y deep link a correo. | Inspección completa de un caso con apertura en Outlook. |
| **Fase 4: Integración con n8n** | Conexión del formulario de resolución manual con el Webhook de n8n. | Flujo de resolución humana funcional de extremo a extremo. |
| **Fase 5: Notificaciones y Despliegue** | Feedback con Toasts (Sonner), validaciones de roles y despliegue en VPS/Docker. | Panel en producción disponible para el equipo HSE de RIWI. |
