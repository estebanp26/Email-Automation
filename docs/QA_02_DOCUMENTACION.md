# 📋 Documentación Técnica: Suite Automatizada E2E con Playwright [QA-02]

> **Módulo:** Quality Assurance & Testing Automatizado  
> **Épica:** `EPIC-07: QA, Seguridad Integral y Testing`  
> **Task ID:** `[QA-02]`  
> **Squad:** QA & Seguridad / Frontend  
> **Responsables:** Andres, Dev FE 3  
> **Estimación:** 8 Story Points  
> **Estado:** ✅ Completado y Verificado (DoD Satisfecho)  
> **Fecha:** 2026-09-30  

---

## 1. Resumen Ejecutivo y Alcance

La tarea **`[QA-02]`** implementa la suite oficial de pruebas automatizadas **End-to-End (E2E)** sobre el ecosistema web de Riwi HSE Justifications (Release 3.0). El objetivo primordial es garantizar la integridad operativa de los dos flujos más críticos de la plataforma:

1. **Flujo de Autoservicio del Coder:** Ingreso autenticado por documento de identidad, diligenciamiento estructurado de novedades con validación Zod, carga asistida de evidencias probatorias digitales (PDF/PNG/JPG) con validación de magic bytes y radicación oficial del caso.
2. **Flujo de Gestión y Triaje HSE:** Acceso del equipo administrativo (`admin@riwi.io`), inspección de la bandeja de entrada `/requests`, consulta de recomendaciones emitidas por Strata Core (IA Engine), resolución manual asistida y despacho formal de notificaciones.
3. **Guardrails de Seguridad RBAC:** Blindaje de rutas frontend contra accesos no autorizados y segregación de privilegios entre perfiles (Coder vs Analista HSE).

---

## 2. Arquitectura de Archivos y Componentes

```
Email-Automation/
├── .github/
│   └── workflows/
│       └── e2e-playwright.yml             # Pipeline CI/CD automatizado (< 4 min budget)
└── frontend/
    ├── playwright.config.ts               # Configuración central (Chromium, timeouts, webServer)
    ├── package.json                       # Scripts npm: test:e2e, test:e2e:ui
    └── e2e/
        ├── fixtures/
        │   └── test_incapacidad.pdf       # Soporte sintético válido (%PDF-1.4)
        ├── smoke.spec.ts                  # Verificación base de entorno y renderizado
        ├── coder-flow.spec.ts             # Flujo Coder (Login -> Form -> Drag&Drop -> Radicado)
        ├── hse-flow.spec.ts               # Flujo HSE (Bandeja -> Detalle -> Resolución manual)
        └── rbac-guard.spec.ts             # Seguridad y protección de rutas con ProtectedRoute
```

### 2.1 Configuración del Runner (`frontend/playwright.config.ts`)
* **Navegador:** Chromium Headless Shell (v1243).
* **Vite WebServer Integrado:** Automatizado mediante `npm run dev -- --host 127.0.0.1 --port 5173`. Playwright espera el levantamiento del dev server antes de iniciar la suite.
* **Política de Trazabilidad y Forense:**
  * `screenshot: 'only-on-failure'`: Captura automática del viewport ante cualquier fallo.
  * `trace: 'retain-on-failure'`: Generación de traza interactiva `.zip` para inspección con `npx playwright show-trace`.
  * `video: 'retain-on-failure'`: Grabación de video de la sesión en fallos.
* **Tiempo Límite por Test:** 30,000 ms (timeout de aserción: 5,000 ms).
* **Paralelismo:** `fullyParallel: true` (5 workers en concurrencia).

---

## 3. Detalle de Suites y Casos de Prueba

| Suite | Archivo | Casos Probados | Tiempo Promedio |
|---|---|---|---|
| **Smoke Test** | `e2e/smoke.spec.ts` | Renderizado de login, títulos, inputs, botón de acceso y mascota institucional. | **~4.5s** |
| **Flujo Coder** | `e2e/coder-flow.spec.ts` | Login con cédula $\rightarrow$ Redirección a `/coder/new-excuse` $\rightarrow$ Paso 1 Formulario $\rightarrow$ Paso 2 Drag-and-drop de PDF $\rightarrow$ Envío y verificación de número de radicado oficial (`RAD-HSE-YYYY-XXXXXX`). | **~5.5s** |
| **Flujo HSE** | `e2e/hse-flow.spec.ts` | Login `admin@riwi.io` $\rightarrow$ Bandeja `/requests` $\rightarrow$ Apertura de detalle y recomendación de Strata Core $\rightarrow$ Diligenciamiento de notas de resolución $\rightarrow$ Aprobación formal y confirmación en pantalla. | **~8.1s** |
| **Guardrails RBAC** | `e2e/rbac-guard.spec.ts` | Bloqueo de usuarios anónimos (redirección a `/login`) y bloqueo de usuarios Coder intentando acceder a vistas de analista (redirección a `/coder/new-excuse`). | **~4.5s** |

---

## 4. Métricas de Rendimiento y Cumplimiento del DoD

* **Criterio de Aceptación:** La suite debe ejecutarse en el pipeline headless en $< 4$ minutos ($240$ s).
* **Resultado Real:** **18.2 segundos** (13 veces más rápido que el umbral estipulado).
* **Fiabilidad:** 5 de 5 pruebas pasando (100% de efectividad).
* **Frontend Build:** `npm run build` en 1.27s (0 errores TypeScript).
* **Backend Pytest:** 161 pruebas pasando en 0.93s (`.venv/bin/pytest backend/tests`).

---

## 5. Guía de Ejecución Rápida de Comandos

```bash
# Ejecutar toda la suite E2E en modo headless
cd frontend
npm run test:e2e

# Ejecutar con el explorador interactivo de Playwright UI
npm run test:e2e:ui

# Ejecutar un test en particular
npx playwright test e2e/coder-flow.spec.ts

# Ver reporte visual detallado tras la ejecución
npx playwright show-report
```

---

## 6. Configuración del Pipeline CI/CD (`.github/workflows/e2e-playwright.yml`)

```yaml
name: E2E Automated Tests (QA-02)

on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'
      - '.github/workflows/e2e-playwright.yml'
  pull_request:
    branches: [main, develop]
    paths:
      - 'frontend/**'
      - '.github/workflows/e2e-playwright.yml'

jobs:
  playwright-e2e:
    name: Playwright E2E Test Suite
    runs-on: ubuntu-latest
    timeout-minutes: 8

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Setup Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install Frontend Dependencies
        working-directory: ./frontend
        run: npm ci || npm install

      - name: Install Playwright Browsers & OS Dependencies
        working-directory: ./frontend
        run: npx playwright install --with-deps chromium

      - name: Run Playwright E2E Suite (< 4 min budget)
        working-directory: ./frontend
        run: npm run test:e2e

      - name: Upload Test Artifacts (Screenshots & Traces on Failure)
        uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: playwright-report
          path: |
            frontend/playwright-report/
            frontend/test-results/
          retention-days: 14
```
