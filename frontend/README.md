# Squad Frontend Dashboard

**Integrantes:** Kevin, Camilo  

## Stack:
- Next.js 14+ (App Router) o Vite + React
- Tailwind CSS + shadcn/ui
- Supabase Client (`@supabase/supabase-js`)

## Vistas Requeridas para la Team Leader:
1. **Bandeja de Entrada HSE (Split-View):**
   - Lista lateral con estados: `🟢 Aprobado Auto`, `🔴 Rechazado Auto`, `🟡 Revisión Manual`.
   - Panel de detalle: Datos del coder, correo original, visor embebido del adjunto (PDF / Imagen) y veredicto de la IA.
2. **Acciones 1-Click:**
   - Botón *Aprobar*: Actualiza estado a `APROBADO_MANUAL` y dispara webhook a n8n para enviar correo al coder.
   - Botón *Rechazar*: Abre modal para escribir motivo y dispara correo de rechazo.
3. **Pestaña de Métricas:**
   - Contador de correos procesados hoy, % aprobación y tiempo medio de respuesta.
4. **Pestaña de Configuración (El Salvavidas del Lunes):**
   - Interfaz simple para editar `hse_system_config` y `email_templates` sin tocar código.
