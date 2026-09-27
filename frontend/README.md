# Squad Frontend Dashboard — Email Automation HSE

**Integrantes:** Kevin, Camilo

## Stack
- Vite + React 19
- Tailwind CSS 4 (`@tailwindcss/vite`)
- lucide-react (iconos) + Recharts (gráfico de ingesta)
- Supabase Client (`@supabase/supabase-js`) — pendiente de integrar

## Estructura
```
src/
├── App.jsx                  # Layout: Sidebar + Header + KPIs + grid
├── main.jsx
├── index.css                # Tailwind + tema (sidebar #1E2235, brand #5b36f5)
└── components/
    ├── Sidebar.jsx          # Navegación oscura + tarjeta Plan de Control HSE
    ├── Header.jsx           # Título + acciones de perfil + notificaciones + avatar AD
    ├── KpiCard.jsx          # Tarjetas Respondidos / Pendientes / En Revisión
    ├── ChartCard.jsx        # Flujo de Ingesta Mensual (Recharts)
    └── RecentMessages.jsx   # Gestión de Mensajes Recientes + contadores por tipo
```

> Toda la UI visible está en español según el mockup.

## Desarrollo
```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # salida en dist/
```

## Vistas Requeridas para la Team Leader (roadmap)
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
