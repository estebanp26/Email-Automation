# 📋 Master Task Tracker — Email Automation con Strata Core

> **Nombre Oficial del Motor:** **`Strata Core`**  
> Motor universal de procesamiento de datos desestructurados (texto plano, fotos, escaneos, documentos) con indexación léxica espacial y extracción de evidencia con IA local (Qwen 2.5).
>
> **Mecanismo de Trabajo:** El proyecto se rige por **dependencias y bloqueos**, no por fechas fijas.

---

## 📊 Matriz Maestra de Tareas con Integración de Strata Core

| ID | Tarea / Entregable | Squad | Responsable | Prioridad | ¿De quién depende? (Espera a) | Impacto Crítico (A quién desbloquea) | Rama Git | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DB-01** | Crear proyecto Supabase y ejecutar migraciones DDL iniciales | DB | **Eliam** | 🚨 P0 (Bloqueante) | **Ninguna (¡ARRANCAR YA!)** | Desbloquea a **TODO el equipo** (Esteban, Jesus, Kevin y Camilo necesitan DB) | `feature/db-supabase` | 🟡 Por Hacer |
| **DB-02** | Configurar bucket en Storage (`justification-attachments`) y políticas | DB | **Sergio** | 🚨 P0 (Bloqueante) | **Ninguna (¡ARRANCAR YA!)** | Desbloquea a **Esteban** (guardar adjuntos) y a **Camilo** (visor de evidencias) | `feature/db-supabase` | 🟡 Por Hacer |
| **N8N-01** | Levantar n8n (Docker/Cloud) y variables de entorno | n8n | **Esteban** | 🚨 P0 (Bloqueante) | **Ninguna (¡ARRANCAR YA!)** | Desbloquea a **Samuel** (URL webhook) y **Jesus / Luis** (armar flujos) | `feature/n8n-core` | 🟡 Por Hacer |
| **CONN-01** | Registro en Azure Portal y permisos Microsoft Graph para Outlook | Conexión | **Samuel** | 🚨 P0 (Bloqueante) | **Ninguna (¡ARRANCAR YA!)** | Desbloquea a **Luis** (envío de correos) y **Esteban** (ingesta) | `feature/email-connections` | 🟡 Por Hacer |
| **STRATA-01**| Calibrar prompts y schema de salida HSE en **Strata Core** | Strata Core | **Andres** | 🚨 P0 (Bloqueante) | **Ninguna (¡ARRANCAR YA!)** | Desbloquea a **Sebastian** (ajuste del microservicio) y **Jesus** (n8n Subflujo 2) | `feature/ai-engine` | 🟡 Por Hacer |
| **STRATA-02**| Exponer API HTTP de **Strata Core** (`/api/evaluate-excuse`) para n8n | Strata Core | **Sebastian** | 🚨 P0 (Bloqueante) | ⏳ Espera a **Andres** (`STRATA-01`) | Desbloquea a **Jesus** (`N8N-03`) para enviar texto plano y adjuntos a evaluar | `feature/ai-engine` | 🟡 Por Hacer |
| **FRONT-01** | Setup Next.js 14 + Tailwind + shadcn/ui y cliente Supabase | Frontend | **Kevin** | P0 | ⏳ Espera a **Eliam** (`DB-01`) por las credenciales | Desbloquea a **Camilo** (layout base para montar el visor) | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **CONN-04** | Normalizar payloads para Outlook/Gmail (cuerpo texto + adjuntos) | Conexión | **Samuel** | P0 | **Ninguna (Hacer de inmediato)** | Desbloquea a **Esteban** (`N8N-02`) para pasar datos limpios a Strata Core | `feature/email-connections` | 🟡 Por Hacer |
| **DB-03** | Poblar `hse_system_config` y `email_templates` con datos semilla | DB | **Eliam** | P0 | ⏳ Espera a `DB-01` | Desbloquea a **Esteban** (`N8N-02`) y a **Andres** (reglas dinámicas) | `feature/db-supabase` | 🟡 Por Hacer |
| **N8N-02** | Subflujo 1: Ingesta, pre-filtro y despacho hacia **Strata Core** | n8n | **Esteban** | P0 | ⏳ Espera a **Samuel** (`CONN-04`), **Eliam** (`DB-01`) y **Sergio** (`DB-02`) | Desbloquea a **Jesus** (`N8N-03`) con el payload procesado | `feature/n8n-core` | 🟡 Por Hacer |
| **FRONT-02** | Maquetación Split-View: Bandeja de entrada con badges de estado | Frontend | **Kevin** | P0 | ⏳ Espera a `FRONT-01` | Desbloquea a **Camilo** (`FRONT-03`) para incrustar el visor a la derecha | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **FRONT-03** | Visor de documentos con resaltado de cajas espaciales de **Strata** | Frontend | **Camilo** | P0 | ⏳ Espera a **Kevin** (`FRONT-02`) y **Sergio** (`DB-02`) | Desbloquea la **auditoría visual con coordenadas** para la Team Leader | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **CONN-02** | Webhook / Suscripción de correo entrante Outlook hacia n8n | Conexión | **Samuel** | P0 | ⏳ Espera a **Esteban** (`N8N-01`) por la URL del webhook | Desbloquea la **ingesta en tiempo real** de Outlook | `feature/email-connections` | 🟡 Por Hacer |
| **CONN-03** | Configurar Google Cloud Pub/Sub y API Gmail hacia n8n | Conexión | **Samuel** | P0 | ⏳ Espera a **Esteban** (`N8N-01`) por la URL del webhook | Desbloquea la **ingesta en tiempo real** de Gmail | `feature/email-connections` | 🟡 Por Hacer |
| **STRATA-03**| Dataset de 25 casos reales para calibrar el `FastVocabCleaner` | Strata Core | **Andres** | P0 | **Ninguna (Avanzar en paralelo)** | Desbloquea las **pruebas de precisión léxica y médica** en Strata Core | `feature/ai-engine` | 🟡 Por Hacer |
| **N8N-03** | Subflujo 2: Enlazar **Strata Core** con Supabase (Guardar veredicto) | n8n | **Jesus** | P0 | ⏳ Espera a **Sebastian** (`STRATA-02`) y **Eliam** (`DB-01`) | Desbloquea a **Luis** (`N8N-04`) para la fase de respuesta | `feature/n8n-core` | 🟡 Por Hacer |
| **N8N-04** | Subflujo 3: Despacho de respuesta HTML en el mismo hilo (*Reply-to*) | n8n | **Luis** | P0 | ⏳ Espera a **Eliam** (`DB-03`) y **Samuel** (`CONN-01`) | Desbloquea el **cierre automático del ciclo de correo** al coder | `feature/n8n-core` | 🟡 Por Hacer |
| **N8N-05** | Webhook receptor de acciones manuales desde el Dashboard | n8n | **Jesus** | P1 | ⏳ Espera a **Camilo** (`FRONT-04`) para el contrato JSON | Desbloquea la capacidad de la TL de revertir decisiones con 1-click | `feature/n8n-core` | 🟡 Por Hacer |
| **FRONT-04** | Botones de acción 1-click (*Aprobar*, *Rechazar*) con webhook a n8n | Frontend | **Camilo** | P0 | ⏳ Espera a **Jesus** (`N8N-05`) por la URL del webhook | Desbloquea la **resolución manual interactiva** para la Team Leader | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **FRONT-05** | Pestaña de Configuración: Editor visual de reglas y plantillas | Frontend | **Kevin** | P0 | ⏳ Espera a **Eliam** (`DB-01`, `DB-03`) | **EL SALVAVIDAS:** Permite a la TL cambiar reglas el lunes sin tocar código | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **STRATA-04**| Benchmark y optimización de latencia en **Strata Core** (< 10s) | Strata Core | **Sebastian** | P1 | ⏳ Espera a `STRATA-02` y **Andres** (`STRATA-03`) | Garantiza la **velocidad de procesamiento local** | `feature/ai-engine` | 🟡 Por Hacer |
| **DB-04** | Crear índices y vistas SQL optimizadas para el Dashboard | DB | **Sergio** | P1 | ⏳ Espera a que Kevin y Camilo maqueten la interfaz | Desbloquea tiempos de respuesta **< 50ms** en la carga del Dashboard | `feature/db-supabase` | 🟡 Por Hacer |
| **N8N-06** | Configurar cola secuencial en n8n para no saturar Strata Core | n8n | **Luis** | P1 | ⏳ Espera a que los Subflujos 1, 2 y 3 estén enlazados | Desbloquea la **estabilidad de CPU** ante ráfagas concurrentes de correos | `feature/n8n-core` | 🟡 Por Hacer |
| **STRATA-05**| Configurar fallback híbrido a Gemini Flash si Strata se satura | Strata Core | **Andres** | P2 | ⏳ Espera a que el flujo local principal esté estable | Respaldo de **alta disponibilidad** para el pitch del martes | `feature/ai-engine` | 🟡 Por Hacer |
| **FRONT-06** | Pestaña de Métricas: Tiempo medio, tasa de aprobación y volumen | Frontend | **Camilo** | P1 | ⏳ Espera a que haya justificantes de prueba en Supabase | Desbloquea los **gráficos de impacto** para la presentación final | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **DB-05** | Configurar Connection Pooling (PgBouncer) para concurrencia | DB | **Eliam** | P1 | ⏳ Espera a las pruebas de carga de **Luis** (`N8N-06`) | Desbloquea la **estabilidad de base de datos** bajo alta demanda | `feature/db-supabase` | 🟡 Por Hacer |

---

## 🎯 Reasignación Operativa de Squads con Strata Core

### 🟣 Squad Strata Core (Andres & Sebastian) — *Rama: `feature/ai-engine`*
* **Misión:** Convertir el motor existente en el servicio central de evaluación multimodal y de texto plano del sistema.
* **Andres:** Adapta el vocabulario (`FastVocabCleaner`), la detección de términos de salud/HSE y calibra las instrucciones de Qwen 2.5 para que devuelva siempre el JSON de validación estructurada.
* **Sebastian:** Levanta el microservicio de **Strata Core** (FastAPI/Uvicorn en puerto 8001), creando el endpoint que recibe: o bien el texto plano del correo, o bien el archivo PDF/imagen adjunta, y devuelve el diagnóstico en < 10 segundos.

### 🔴 Squad n8n (Esteban, Jesus, Luis) — *Rama: `feature/n8n-core`*
* **Esteban:** Orquesta la entrada. En lugar de procesar archivos en nodos lentos, se los envía directo como un payload HTTP multipart a **Strata Core**.
* **Jesus:** Conecta la respuesta de **Strata Core** con la base de datos de Supabase y escucha los webhooks del Dashboard.
* **Luis:** Administra la cola de n8n para que las peticiones a **Strata Core** entren de forma controlada sin ahogar la CPU, y despacha las respuestas automáticas a los coders.

### 🔵 Squad Frontend (Kevin & Camilo) — *Rama: `feature/frontend-dashboard`*
* **Kevin:** Construye la bandeja de entrada y el panel de configuración dinámica de reglas.
* **Camilo:** Aprovecha una de las mejores características de **Strata Core**: **las coordenadas espaciales (`rects`)**, renderizando el visor de documentos donde las fechas, sellos y nombres aparecen resaltados visualmente en cajas de color para la Team Leader.

### 🟢 Squad Conexión (Samuel) — *Rama: `feature/email-connections`*
* **Samuel:** Asegura que los correos de Outlook y Gmail extraigan tanto el cuerpo en texto plano como los archivos adjuntos (PDFs, fotos JPG/PNG) y los entregue listos para Strata Core.

### 🟠 Squad Database (Eliam & Sergio) — *Rama: `feature/db-supabase`*
* **Eliam & Sergio:** Mantienen la persistencia de los veredictos emitidos por Strata Core, las evidencias citadas y el almacenamiento de los archivos adjuntos.
