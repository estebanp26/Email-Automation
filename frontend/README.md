# Dashboard HSE RIWI (Frontend)

Panel web administrativo para el equipo de Habilidades Socioemocionales (HSE) de RIWI, diseñado para auditar, gestionar y resolver justificaciones de inasistencia y contingencias formativas con integración directa al workflow de **n8n**.

---

## ⚡ Tecnologías Principales

- **React 19** + **TypeScript**
- **Vite 8**
- **Tailwind CSS v4**
- **Framer Motion** (Animaciones fluidas y micro-interacciones)
- **Recharts** (Gráficos estadísticos y KPIs)
- **Lucide Icons**

---

## 🔗 Integración con n8n Workflow

El frontend se comunica con n8n mediante endpoints webhook tipo REST:

1. **Webhook de Despacho Manual HSE (`POST /webhook/riwi-hse-dispatch-email` o `/webhook-test/...`):**
   - Disparado al presionar **Aprobar Excusa** (`APPROVED`), **Rechazar Caso** (`DISAPPROVED`) o **Pedir Soporte** (`REQUEST_CORRECTION`).
   - Envía el ID de justificación, la acción, las fechas, tipo de excusa, el nombre del revisor y las observaciones de HSE.
2. **Webhook de Ingesta / Prueba (`POST /webhook/riwi-email-incoming` o `/webhook-test/...`):**
   - Permite simular y probar la ingesta de correos entrantes directamente desde el módulo de configuración.

### Módulos Clave:
- [`src/services/n8n.ts`](./src/services/n8n.ts): Cliente de conexión con n8n, manejo de URLs, modo Test vs Producción y métodos de despacho y diagnóstico.
- [`src/pages/Requests.tsx`](./src/pages/Requests.tsx): Bandeja de entrada con panel de resolución manual y feedback visual en tiempo real.
- [`src/pages/Settings.tsx`](./src/pages/Settings.tsx): Tarjeta de configuración en vivo para cambiar la URL de n8n, probar conectividad o simular correos.

---

## 🚀 Inicio Rápido

### 1. Variables de entorno

Crea o revisa el archivo `.env` en la raíz de `frontend/`:

```env
VITE_API_URL=http://localhost:8000
VITE_N8N_URL=http://localhost:5678
VITE_N8N_USE_TEST_WEBHOOK=true
```

### 2. Instalar dependencias

```bash
npm install
```

### 3. Modo desarrollo

```bash
npm run dev
```

La aplicación quedará disponible en `http://localhost:5173`.

### 4. Compilar para producción

```bash
npm run build
```
