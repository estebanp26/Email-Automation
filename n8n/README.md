# Squad n8n Core

**Líder:** Esteban  
**Integrantes:** Jesus, Luis  

## Responsabilidades:
1. **Subflujo 1 (Ingesta & Normalización):**
   - Recibe los eventos de Outlook y Gmail preparados por Samuel (Conexión).
   - Consulta `hse_system_config` en Supabase para obtener las palabras clave.
   - Si no coincide con un correo de justificación, termina silenciosamente.
   - Si coincide, sube los adjuntos al bucket de Supabase Storage y arma el payload normalizado.
2. **Subflujo 2 (Evaluación con IA):**
   - Hace la llamada a la API de Gemini 2.0 Flash con el prompt del sistema y el archivo.
   - Parsea el JSON devuelto.
   - Registra el caso en la tabla `justifications` con el veredicto y tiempo de respuesta.
3. **Subflujo 3 (Despachador de Respuestas):**
   - Obtiene la plantilla desde `email_templates` de Supabase.
   - Reemplaza variables (`{{nombre_coder}}`, `{{motivo}}`, `{{fecha}}`).
   - Envía el correo de respuesta vía el conector respectivo (Outlook o Gmail).

## Archivos de Trabajo:
- `workflows/01_ingesta_filtro.json`
- `workflows/02_evaluacion_ai.json`
- `workflows/03_despacho_respuestas.json`
