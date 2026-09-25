# 📋 Master Task Tracker (Notion / GitHub Projects Ready)

Copia y pega esta tabla directamente en Notion (como Base de Datos) o úsala para crear los Issues de GitHub Projects.

## 📊 Tabla Maestra de Tareas

| ID | Tarea | Squad | Responsable | Prioridad | Día Límite | Rama Git | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **N8N-01** | Levantar n8n (Docker/Cloud) y variables de entorno seguras | n8n | **Esteban** | P0 (Bloqueante) | Viernes | `feature/n8n-core` | 🟡 Por Hacer |
| **N8N-02** | Subflujo 1: Ingesta, pre-filtro por keywords y storage de adjuntos | n8n | **Esteban** | P0 | Sábado | `feature/n8n-core` | 🟡 Por Hacer |
| **N8N-03** | Subflujo 2: Orquestación con Gemini 2.0 Flash y guardado en Supabase | n8n | **Jesus** | P0 | Sábado | `feature/n8n-core` | 🟡 Por Hacer |
| **N8N-04** | Subflujo 3: Despacho de respuesta HTML en el mismo hilo (*Reply-to*) | n8n | **Luis** | P0 | Sábado | `feature/n8n-core` | 🟡 Por Hacer |
| **N8N-05** | Webhook receptor de acciones manuales desde el Dashboard | n8n | **Jesus** | P1 | Domingo | `feature/n8n-core` | 🟡 Por Hacer |
| **N8N-06** | Configurar colas de ejecución y reintentos para 200+ correos | n8n | **Luis** | P1 | Domingo | `feature/n8n-core` | 🟡 Por Hacer |
| **FRONT-01** | Setup Next.js 14 + Tailwind + shadcn/ui y cliente Supabase | Frontend | **Kevin** | P0 | Viernes | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **FRONT-02** | Maquetación Split-View: Bandeja de entrada con badges de estado | Frontend | **Kevin** | P0 | Sábado | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **FRONT-03** | Visor de documentos integrado (Previsualización PDF e imágenes) | Frontend | **Camilo** | P0 | Sábado | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **FRONT-04** | Botones de acción 1-click (*Aprobar*, *Rechazar*) conectados a webhook | Frontend | **Camilo** | P0 | Domingo | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **FRONT-05** | Pestaña de Configuración: Editor visual de reglas y plantillas | Frontend | **Kevin** | P0 | Domingo | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **FRONT-06** | Pestaña de Métricas: Tiempo medio, tasa de aprobación y volumen | Frontend | **Camilo** | P1 | Lunes | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **CONN-01** | Registro en Azure Portal y permisos Microsoft Graph para Outlook | Conexión | **Samuel** | P0 | Viernes | `feature/email-connections` | 🟡 Por Hacer |
| **CONN-02** | Webhook / Suscripción de correo entrante Outlook hacia n8n | Conexión | **Samuel** | P0 | Sábado | `feature/email-connections` | 🟡 Por Hacer |
| **CONN-03** | Configurar Google Cloud Pub/Sub y API Gmail hacia n8n | Conexión | **Samuel** | P0 | Sábado | `feature/email-connections` | 🟡 Por Hacer |
| **CONN-04** | Adaptador de normalización de payloads para Outlook y Gmail | Conexión | **Samuel** | P0 | Domingo | `feature/email-connections` | 🟡 Por Hacer |
| **AI-01** | Calibración del System Prompt multimodal con criterios HSE | AI Engine | **Andres** | P0 | Viernes | `feature/ai-engine` | 🟡 Por Hacer |
| **AI-02** | Implementar llamada SDK Gemini 2.0 Flash con JSON Schema estricto | AI Engine | **Sebastian** | P0 | Sábado | `feature/ai-engine` | 🟡 Por Hacer |
| **AI-03** | Crear dataset de prueba con 25 casos reales (fotos, incapacidades, spam) | AI Engine | **Andres** | P0 | Sábado | `feature/ai-engine` | 🟡 Por Hacer |
| **AI-04** | Benchmark de latencia: Asegurar inferencia multimodal < 2.0 segundos | AI Engine | **Sebastian** | P1 | Domingo | `feature/ai-engine` | 🟡 Por Hacer |
| **AI-05** | Implementar fallback a OpenAI GPT-4o-mini si Gemini falla o satura | AI Engine | **Andres** | P2 | Lunes | `feature/ai-engine` | 🟡 Por Hacer |
| **DB-01** | Crear proyecto Supabase y correr migraciones `001_initial_schema.sql` | DB | **Eliam** | P0 | Viernes | `feature/db-supabase` | 🟡 Por Hacer |
| **DB-02** | Configurar bucket en Storage (`justification-attachments`) y políticas | DB | **Sergio** | P0 | Viernes | `feature/db-supabase` | 🟡 Por Hacer |
| **DB-03** | Ejecutar script semilla `002_seed_data.sql` (reglas y plantillas) | DB | **Eliam** | P0 | Sábado | `feature/db-supabase` | 🟡 Por Hacer |
| **DB-04** | Crear índices y vistas SQL optimizadas para el Dashboard | DB | **Sergio** | P1 | Domingo | `feature/db-supabase` | 🟡 Por Hacer |
| **DB-05** | Configurar Connection Pooling (PgBouncer) para ráfagas de 200+ | DB | **Eliam** | P1 | Lunes | `feature/db-supabase` | 🟡 Por Hacer |

---

## 🎯 Ficha de Misiones Específicas por Persona

### 🔴 Squad n8n (Rama: `feature/n8n-core`)
* **Esteban (Líder del Squad):**
  * **Misión:** Levantar la infraestructura n8n y asegurar la ingesta.
  * **Entregable:** Instancia operativa de n8n con variables de entorno listas + **Subflujo 1** que recibe el webhook de Samuel, valida las palabras clave de `hse_system_config` y sube los archivos a Supabase Storage.
* **Jesus:**
  * **Misión:** Orquestación de IA y acciones del Dashboard.
  * **Entregable:** **Subflujo 2** que toma el texto y la imagen, invoca el nodo de Gemini Flash de Andres/Sebastian, valida el schema JSON e inserta el resultado en la tabla `justifications`.
  * **Entregable Domingo:** Endpoint webhook que escucha cuando Kevin o Camilo dan clic en *Aprobar* o *Rechazar* desde el frontend.
* **Luis:**
  * **Misión:** Despachador de correos y resiliencia ante picos de 200+.
  * **Entregable:** **Subflujo 3** que toma la plantilla HTML de Supabase, reemplaza variables (`{{nombre_coder}}`, `{{motivo}}`) y responde al coder en el mismo hilo de Outlook/Gmail. Configurar la cola con reintentos en n8n.

---

### 🔵 Squad Frontend (Rama: `feature/frontend-dashboard`)
* **Kevin:**
  * **Misión:** Estructura base, Bandeja de Entrada y Pestaña de Configuración.
  * **Entregable:** Proyecto Next.js 14 corriendo en Vercel. Vista dividida con tarjetas de coders ordenadas cronológicamente con estados de colores (`🟢 Aprobado`, `🔴 Rechazado`, `🟡 Revisión`).
  * **Entregable Domingo:** **Pestaña de Configuración de Reglas** (el salvavidas del lunes para que la TL o el equipo cambien horas límite o palabras clave desde la interfaz sin tocar código).
* **Camilo:**
  * **Misión:** Visor de Evidencias, Acciones 1-Click y Métricas.
  * **Entregable:** Componente interactivo que renderiza el PDF o la foto del certificado médico al seleccionar un caso, mostrando al lado la explicación de la IA.
  * **Entregable Domingo:** Botones *Aprobar* y *Rechazar con Nota* que disparan el webhook a n8n y actualizan el estado en vivo.
  * **Entregable Lunes:** Tarjetas de métricas: tiempo medio en segundos, porcentaje de auto-aprobación y contador de correos hoy.

---

### 🟢 Squad Conexión (Rama: `feature/email-connections`)
* **Samuel:**
  * **Misión:** Conectar los buzones reales y normalizar los datos.
  * **Entregable:** Registro de Azure con permisos Graph API + Suscripción a Webhook de correos entrantes de Outlook.
  * **Entregable Sábado:** Configuración de Google Cloud Pub/Sub para notificaciones push de Gmail.
  * **Entregable Domingo:** Un script/nodo adaptador que garantice que sin importar si el correo vino de Gmail o de Outlook, a Esteban (n8n) le llegue exactamente la misma estructura de JSON (ver `docs/API_CONTRACTS.md`).

---

### 🟣 Squad AI Engine (Rama: `feature/ai-engine`)
* **Andres:**
  * **Misión:** Calibración del Prompt Multimodal, Casos Borde y Fallback.
  * **Entregable:** El System Prompt maestro en `ai-engine/prompts/evaluator_system_prompt.md` que acepta reglas dinámicas.
  * **Entregable Sábado:** Banco de pruebas de 25 correos y documentos simulados (fotos de recetas médicas borrosas, incapacidades oficiales, excusas sin soporte, correos de spam).
  * **Entregable Lunes:** Lógica de fallback a GPT-4o-mini si la cuota de Gemini experimenta lentitud.
* **Sebastian:**
  * **Misión:** Implementación SDK de Gemini y optimización de latencia.
  * **Entregable:** Módulo de llamada a **Gemini 2.0 Flash** con validación estricta de JSON Schema (`ai-engine/schemas/evaluation_schema.json`).
  * **Entregable Domingo:** Benchmark que garantice que el procesamiento de imagen + texto se complete en **menos de 2 segundos**.

---

### 🟠 Squad Database (Rama: `feature/db-supabase`)
* **Eliam:**
  * **Misión:** Arquitectura de datos, seguridad y alta concurrencia.
  * **Entregable:** Proyecto Supabase activo con las tablas `justifications`, `hse_system_config` y `email_templates` creadas a partir de `database/migrations/001_initial_schema.sql` y pobladas con `002_seed_data.sql`.
  * **Entregable Lunes:** Configuración del Connection Pooling (puerto 6543) para que una ráfaga de 60 o 200 correos simultáneos no agote las conexiones de PostgreSQL.
* **Sergio:**
  * **Misión:** Storage S3 para adjuntos y optimización de lectura.
  * **Entregable:** Bucket de Supabase Storage configurado para recibir PDFs e imágenes, con URLs de acceso seguras para el Dashboard de Camilo y Kevin.
  * **Entregable Domingo:** Índices en base de datos para que la carga de justificantes en el Dashboard responda en menos de 50 milisegundos.

---

## ⚡ Cadena de Desbloqueo (Quién desbloquea a quién)
1. **Eliam y Sergio (DB)** deben compartir la URL y las llaves de Supabase **hoy mismo**. Esto desbloquea a **Esteban (n8n)** y a **Kevin (Frontend)**.
2. **Samuel (Conexión)** configura los webhooks de prueba. Mientras tanto, Esteban puede usar un webhook con datos simulados usando el JSON de `docs/API_CONTRACTS.md`.
3. **Andres y Sebastian (AI)** prueban el prompt de Gemini de forma aislada. Cuando el JSON esté listo, se lo entregan a **Jesus (n8n)** para ensamblarlo en el Subflujo 2.
