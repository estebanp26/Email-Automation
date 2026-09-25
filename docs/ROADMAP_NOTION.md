# 📋 Master Task Tracker (Notion & GitHub Projects Ready)

> **Mecanismo de Trabajo:** El proyecto se rige por **dependencias y bloqueos**, no por fechas fijas.  
> Copia y pega esta tabla directamente en Notion (como vista de Base de Datos / Tabla) o úsala para alimentar tu tablero de GitHub Projects.

---

## 📊 Matriz Maestra de Tareas por Dependencias

| ID | Tarea / Entregable | Squad | Responsable | Prioridad | ¿De quién depende? (Espera a) | Impacto Crítico (A quién desbloquea) | Rama Git | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DB-01** | Crear proyecto Supabase y ejecutar migraciones DDL iniciales | DB | **Eliam** | 🚨 P0 (Bloqueante) | **Ninguna (¡ARRANCAR YA!)** | Desbloquea a **TODO el equipo** (Esteban, Jesus, Kevin y Camilo necesitan DB) | `feature/db-supabase` | 🟡 Por Hacer |
| **DB-02** | Configurar bucket en Storage (`justification-attachments`) y políticas | DB | **Sergio** | 🚨 P0 (Bloqueante) | **Ninguna (¡ARRANCAR YA!)** | Desbloquea a **Esteban** (n8n guarda adjuntos) y **Camilo** (Frontend visor) | `feature/db-supabase` | 🟡 Por Hacer |
| **N8N-01** | Levantar n8n (Docker/Cloud) y variables de entorno seguras | n8n | **Esteban** | 🚨 P0 (Bloqueante) | **Ninguna (¡ARRANCAR YA!)** | Desbloquea a **Samuel** (URL webhook) y **Jesus / Luis** (armar flujos) | `feature/n8n-core` | 🟡 Por Hacer |
| **CONN-01** | Registro en Azure Portal y permisos Microsoft Graph para Outlook | Conexión | **Samuel** | 🚨 P0 (Bloqueante) | **Ninguna (¡ARRANCAR YA!)** | Desbloquea a **Luis** (envío de correos) y **Esteban** (ingesta) | `feature/email-connections` | 🟡 Por Hacer |
| **AI-01** | Calibración del System Prompt multimodal con criterios HSE | AI Engine | **Andres** | 🚨 P0 (Bloqueante) | **Ninguna (¡ARRANCAR YA!)** | Desbloquea a **Sebastian** (conector SDK) y **Jesus** (n8n Subflujo 2) | `feature/ai-engine` | 🟡 Por Hacer |
| **FRONT-01** | Setup Next.js 14 + Tailwind + shadcn/ui y cliente Supabase | Frontend | **Kevin** | P0 | ⏳ Espera a **Eliam** (`DB-01`) por las credenciales | Desbloquea a **Camilo** (layout base para montar el visor de documentos) | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **CONN-04** | Adaptador de normalización de payloads para Outlook y Gmail | Conexión | **Samuel** | P0 | **Ninguna (Hacer de inmediato)** | Desbloquea a **Esteban** (`N8N-02`) para no rehacer la lógica del flujo | `feature/email-connections` | 🟡 Por Hacer |
| **DB-03** | Poblar `hse_system_config` y `email_templates` con datos semilla | DB | **Eliam** | P0 | ⏳ Espera a `DB-01` | Desbloquea a **Esteban** (`N8N-02`) y **Andres** (pruebas de IA dinámicas) | `feature/db-supabase` | 🟡 Por Hacer |
| **AI-02** | Implementar llamada SDK Gemini 2.0 Flash con JSON Schema estricto | AI Engine | **Sebastian** | P0 | ⏳ Espera a **Andres** (`AI-01`) | Desbloquea a **Jesus** (`N8N-03`) para integrar la IA en n8n | `feature/ai-engine` | 🟡 Por Hacer |
| **N8N-02** | Subflujo 1: Ingesta, pre-filtro por keywords y storage de adjuntos | n8n | **Esteban** | P0 | ⏳ Espera a **Samuel** (`CONN-04`), **Eliam** (`DB-01`) y **Sergio** (`DB-02`) | Desbloquea a **Jesus** (`N8N-03`) con el payload procesado | `feature/n8n-core` | 🟡 Por Hacer |
| **FRONT-02** | Maquetación Split-View: Bandeja de entrada con badges de estado | Frontend | **Kevin** | P0 | ⏳ Espera a `FRONT-01` | Desbloquea a **Camilo** (`FRONT-03`) para incrustar el visor a la derecha | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **FRONT-03** | Visor de documentos integrado (Previsualización PDF e imágenes) | Frontend | **Camilo** | P0 | ⏳ Espera a **Kevin** (`FRONT-02`) y **Sergio** (`DB-02`) | Desbloquea las **pruebas visuales** del Dashboard de la Team Leader | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **CONN-02** | Webhook / Suscripción de correo entrante Outlook hacia n8n | Conexión | **Samuel** | P0 | ⏳ Espera a **Esteban** (`N8N-01`) por la URL del webhook | Desbloquea la **ingesta en tiempo real** de correos de Outlook | `feature/email-connections` | 🟡 Por Hacer |
| **CONN-03** | Configurar Google Cloud Pub/Sub y API Gmail hacia n8n | Conexión | **Samuel** | P0 | ⏳ Espera a **Esteban** (`N8N-01`) por la URL del webhook | Desbloquea la **ingesta en tiempo real** de correos de Gmail | `feature/email-connections` | 🟡 Por Hacer |
| **AI-03** | Crear dataset de prueba con 25 casos reales (fotos, recetas, spam) | AI Engine | **Andres** | P0 | **Ninguna (Avanzar en paralelo)** | Desbloquea las **pruebas de precisión** de Sebastian y Jesus | `feature/ai-engine` | 🟡 Por Hacer |
| **N8N-03** | Subflujo 2: Orquestación con Gemini 2.0 Flash y guardado en Supabase | n8n | **Jesus** | P0 | ⏳ Espera a **Sebastian** (`AI-02`) y **Eliam** (`DB-01`) | Desbloquea a **Luis** (`N8N-04`) para la fase de respuesta | `feature/n8n-core` | 🟡 Por Hacer |
| **N8N-04** | Subflujo 3: Despacho de respuesta HTML en el mismo hilo (*Reply-to*) | n8n | **Luis** | P0 | ⏳ Espera a **Eliam** (`DB-03`) y **Samuel** (`CONN-01`) | Desbloquea el **cierre automático del ciclo de correo** al coder | `feature/n8n-core` | 🟡 Por Hacer |
| **N8N-05** | Webhook receptor de acciones manuales desde el Dashboard | n8n | **Jesus** | P1 | ⏳ Espera a **Camilo** (`FRONT-04`) para el contrato JSON | Desbloquea la capacidad de la TL de revertir decisiones con 1-click | `feature/n8n-core` | 🟡 Por Hacer |
| **FRONT-04** | Botones de acción 1-click (*Aprobar*, *Rechazar*) con webhook a n8n | Frontend | **Camilo** | P0 | ⏳ Espera a **Jesus** (`N8N-05`) por la URL del webhook | Desbloquea la **resolución manual interactiva** para la Team Leader | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **FRONT-05** | Pestaña de Configuración: Editor visual de reglas y plantillas | Frontend | **Kevin** | P0 | ⏳ Espera a **Eliam** (`DB-01`, `DB-03`) | **EL SALVAVIDAS:** Permite a la TL cambiar reglas el lunes sin tocar código | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **AI-04** | Benchmark de latencia: Asegurar inferencia multimodal < 2.0 segundos | AI Engine | **Sebastian** | P1 | ⏳ Espera a `AI-02` y **Andres** (`AI-03`) | Desbloquea la **garantía de alta velocidad** requerida para el demo | `feature/ai-engine` | 🟡 Por Hacer |
| **DB-04** | Crear índices y vistas SQL optimizadas para el Dashboard | DB | **Sergio** | P1 | ⏳ Espera a que Kevin y Camilo maqueten la interfaz | Desbloquea tiempos de respuesta **< 50ms** en la carga del Dashboard | `feature/db-supabase` | 🟡 Por Hacer |
| **N8N-06** | Configurar colas de ejecución y reintentos para 200+ correos | n8n | **Luis** | P1 | ⏳ Espera a que los Subflujos 1, 2 y 3 estén enlazados | Desbloquea la **resistencia ante ráfagas masivas** de 60+ correos matutinos | `feature/n8n-core` | 🟡 Por Hacer |
| **AI-05** | Implementar fallback a OpenAI GPT-4o-mini si Gemini falla o satura | AI Engine | **Andres** | P2 | ⏳ Espera a que el flujo principal de Gemini esté estable | Desbloquea la **alta disponibilidad del 99.9%** ante fallos de API | `feature/ai-engine` | 🟡 Por Hacer |
| **FRONT-06** | Pestaña de Métricas: Tiempo medio, tasa de aprobación y volumen | Frontend | **Camilo** | P1 | ⏳ Espera a que haya justificantes de prueba en Supabase | Desbloquea los **gráficos de impacto** para la presentación final | `feature/frontend-dashboard` | 🟡 Por Hacer |
| **DB-05** | Configurar Connection Pooling (PgBouncer) para ráfagas de 200+ | DB | **Eliam** | P1 | ⏳ Espera a las pruebas de carga de **Luis** (`N8N-06`) | Desbloquea la **estabilidad de base de datos** bajo alta concurrencia | `feature/db-supabase` | 🟡 Por Hacer |

---

## 🚨 Foco de Arranque Inmediato: Bloqueadores Clave

```
[Eliam & Sergio - DB]        ──> Desbloquean a: Esteban, Jesus, Kevin, Camilo
[Esteban - n8n Instancia]   ──> Desbloquea a: Samuel, Jesus, Luis
[Samuel - Azure Outlook]     ──> Desbloquea a: Luis (Envío), Esteban (Ingesta)
[Andres - System Prompt]     ──> Desbloquea a: Sebastian (SDK), Jesus (Subflujo 2)
```
