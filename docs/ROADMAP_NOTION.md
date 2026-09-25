# 📋 Master Task Tracker (Por Dependencias y Desbloqueo)

> **Regla de Oro de Ejecución:** No hay fechas fijas; el flujo se mueve por **dependencias**. 
> Si tu tarea dice **"¡HACER YA!"**, tu equipo está detenido esperándote. Si dice **"ESPERA A..."**, avanza en tus tareas secundarias mientras tu compañero te entrega su parte.

---

## 📊 Matriz de Tareas por Dependencia

| ID | Tarea | Squad | Responsable | Condición de Dependencia / Urgencia | Rama Git |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DB-01** | Crear proyecto Supabase y ejecutar migraciones `001_initial_schema.sql` | DB | **Eliam** | 🚨 **¡HACER YA!** Bloquea a TODO el equipo (Esteban, Jesus, Kevin y Camilo necesitan la DB). | `feature/db-supabase` |
| **DB-02** | Crear bucket en Storage (`justification-attachments`) y políticas | DB | **Sergio** | 🚨 **¡HACER YA!** Esteban lo necesita para guardar adjuntos y Camilo para verlos. | `feature/db-supabase` |
| **N8N-01** | Levantar n8n y configurar variables de entorno | n8n | **Esteban** | 🚨 **¡HACER YA!** Samuel necesita la URL del webhook y Jesus/Luis necesitan la instancia. | `feature/n8n-core` |
| **CONN-01** | Registro en Azure Portal y permisos Microsoft Graph para Outlook | Conexión | **Samuel** | 🚨 **¡HACER YA!** Esteban y Luis necesitan las credenciales para recibir y enviar correos. | `feature/email-connections` |
| **AI-01** | Calibración del System Prompt multimodal con criterios HSE | AI Engine | **Andres** | 🚨 **¡HACER YA!** Sebastian lo necesita para codificar el conector y Jesus para n8n. | `feature/ai-engine` |
| **FRONT-01** | Setup Next.js 14 + Tailwind + shadcn/ui y cliente Supabase | Frontend | **Kevin** | ⏳ **Espera a:** Eliam (`DB-01`) para las credenciales de Supabase. **¡Hacer de inmediato tras recibirlas!** Camilo depende de esto. | `feature/frontend-dashboard` |
| **CONN-04** | Adaptador de normalización de payloads para Outlook y Gmail | Conexión | **Samuel** | ⚡ **¡Hacer cuanto antes!** Esteban (`N8N-02`) necesita este formato JSON para no rehacer el flujo. | `feature/email-connections` |
| **DB-03** | Poblar `hse_system_config` y `email_templates` con datos semilla | DB | **Eliam** | ⏳ **Espera a:** `DB-01`. Urgente para que Esteban (`N8N-02`) pruebe la lectura de reglas. | `feature/db-supabase` |
| **AI-02** | Implementar llamada SDK Gemini 2.0 Flash con JSON Schema estricto | AI Engine | **Sebastian** | ⏳ **Espera a:** Andres (`AI-01`). Urgente porque Jesus (`N8N-03`) lo necesita en n8n. | `feature/ai-engine` |
| **N8N-02** | Subflujo 1: Ingesta, pre-filtro por keywords y storage de adjuntos | n8n | **Esteban** | ⏳ **Espera a:** Samuel (`CONN-04`), Eliam (`DB-01`) y Sergio (`DB-02`). | `feature/n8n-core` |
| **FRONT-02** | Maquetación Split-View: Bandeja de entrada con badges de estado | Frontend | **Kevin** | ⏳ **Espera a:** `FRONT-01`. Camilo lo necesita para montar el visor de documentos a la derecha. | `feature/frontend-dashboard` |
| **FRONT-03** | Visor de documentos integrado (Previsualización PDF e imágenes) | Frontend | **Camilo** | ⏳ **Espera a:** Kevin (`FRONT-02`) para el layout y Sergio (`DB-02`) para las URLs del Storage. | `feature/frontend-dashboard` |
| **CONN-02** | Webhook / Suscripción de correo entrante Outlook hacia n8n | Conexión | **Samuel** | ⏳ **Espera a:** Esteban (`N8N-01`) para tener la URL pública del webhook de n8n. | `feature/email-connections` |
| **CONN-03** | Configurar Google Cloud Pub/Sub y API Gmail hacia n8n | Conexión | **Samuel** | ⏳ **Espera a:** Esteban (`N8N-01`) para tener la URL del webhook de n8n. | `feature/email-connections` |
| **AI-03** | Crear dataset de prueba con 25 casos reales (fotos, incapacidades, spam) | AI Engine | **Andres** | ⚡ **¡Hacer cuanto antes!** Sebastian (`AI-04`) y Jesus lo necesitan para probar la IA. | `feature/ai-engine` |
| **N8N-03** | Subflujo 2: Orquestación con Gemini 2.0 Flash y guardado en Supabase | n8n | **Jesus** | ⏳ **Espera a:** Sebastian (`AI-02`) para el nodo de IA y Eliam (`DB-01`) para la tabla `justifications`. | `feature/n8n-core` |
| **N8N-04** | Subflujo 3: Despacho de respuesta HTML en el mismo hilo (*Reply-to*) | n8n | **Luis** | ⏳ **Espera a:** Eliam (`DB-03`) para las plantillas y Samuel (`CONN-01`) para el envío de correo. | `feature/n8n-core` |
| **N8N-05** | Webhook receptor de acciones manuales desde el Dashboard | n8n | **Jesus** | ⏳ **Espera a:** Camilo (`FRONT-04`) para acordar el payload del botón Aprobar/Rechazar. | `feature/n8n-core` |
| **FRONT-04** | Botones de acción 1-click (*Aprobar*, *Rechazar*) conectados a webhook | Frontend | **Camilo** | ⏳ **Espera a:** Jesus (`N8N-05`) para tener el webhook de n8n que procesa la acción. | `feature/frontend-dashboard` |
| **FRONT-05** | Pestaña de Configuración: Editor visual de reglas y plantillas | Frontend | **Kevin** | ⏳ **Espera a:** Eliam (`DB-01`, `DB-03`) para conectar con `hse_system_config`. | `feature/frontend-dashboard` |
| **AI-04** | Benchmark de latencia: Asegurar inferencia multimodal < 2.0 segundos | AI Engine | **Sebastian** | ⏳ **Espera a:** `AI-02` y al dataset de prueba de Andres (`AI-03`). | `feature/ai-engine` |
| **DB-04** | Crear índices y vistas SQL optimizadas para el Dashboard | DB | **Sergio** | ⏳ **Espera a:** Que Kevin y Camilo tengan la vista armada y requieran optimización. | `feature/db-supabase` |
| **N8N-06** | Configurar colas de ejecución y reintentos para 200+ correos | n8n | **Luis** | ⏳ **Espera a:** Que los Subflujos 1, 2 y 3 de Esteban y Jesus estén enlazados. | `feature/n8n-core` |
| **AI-05** | Implementar fallback a OpenAI GPT-4o-mini si Gemini falla o satura | AI Engine | **Andres** | ⏳ **Espera a:** Que el flujo principal con Gemini esté corriendo estable en n8n. | `feature/ai-engine` |
| **FRONT-06** | Pestaña de Métricas: Tiempo medio, tasa de aprobación y volumen | Frontend | **Camilo** | ⏳ **Espera a:** Que haya justificantes de prueba registrados en Supabase. | `feature/frontend-dashboard` |
| **DB-05** | Configurar Connection Pooling (PgBouncer) para ráfagas de 200+ | DB | **Eliam** | ⏳ **Espera a:** Que Luis (`N8N-06`) comience las pruebas de carga y concurrencia. | `feature/db-supabase` |

---

## 🎯 Guía de Acción Inmediata: ¿Quién arranca en este segundo?

### 🚨 GRUPO 1: CERO DEPENDENCIAS (Deben entregar YA porque frenan a otros)
1. **Eliam (`DB-01`):** Entregar la URL de Supabase y las llaves (`anon` y `service_role`). *Tiene frenados a Esteban, Jesus, Kevin y Camilo.*
2. **Sergio (`DB-02`):** Crear el bucket de Storage para adjuntos. *Tiene frenado a Esteban para guardar archivos.*
3. **Esteban (`N8N-01`):** Levantar n8n y pasar la URL pública. *Tiene frenado a Samuel para configurar los webhooks.*
4. **Samuel (`CONN-01`):** Registrar la app en Azure para Outlook. *Tiene frenado a Luis para el envío de correos.*
5. **Andres (`AI-01`):** Escribir el prompt del sistema multimodal. *Tiene frenado a Sebastian para armar el conector con Gemini.*

---

### ⏳ GRUPO 2: PRIMER RELEVO (Arrancan apenas el Grupo 1 les pase sus datos)
* **Kevin (`FRONT-01`):** Espera las llaves de **Eliam**. En cuanto las tenga, inicializa el repo de Next.js. *Camilo lo necesita urgente para no trabajar en el aire.*
* **Sebastian (`AI-02`):** Espera el prompt de **Andres**. En cuanto lo tenga, monta la llamada a Gemini 2.0 Flash con JSON Schema. *Jesus lo necesita para el Subflujo 2.*
* **Samuel (`CONN-04`):** Define el JSON unificado de correos. *Esteban lo necesita para no rehacer el Subflujo 1.*

---

### 🔄 GRUPO 3: INTEGRACIÓN Y CIERRE (Trabajan sobre los módulos de los anteriores)
* **Jesus (`N8N-03`):** Ensambla la IA de Sebastian y guarda en la DB de Eliam.
* **Luis (`N8N-04`):** Ensambla las plantillas de Eliam y el conector de Samuel para responder correos.
* **Camilo (`FRONT-03`, `FRONT-04`):** Monta el visor y los botones sobre la maqueta de Kevin y los webhooks de Jesus.
