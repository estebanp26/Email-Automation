import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Sub-task 2: Flujo Coder E2E', () => {
  test('debe permitir al Coder iniciar sesión, diligenciar formulario, adjuntar PDF de evidencia y obtener radicado', async ({ page }) => {
    // 1. Navegar al Login
    await page.goto('/login');

    // 2. Autenticación con cédula Coder válida (formato fallback numérico >= 6 dígitos)
    const testCedula = '1001234567';
    await page.getByPlaceholder(/Usuario, correo o cédula/i).fill(testCedula);
    await page.getByPlaceholder(/Contraseña o cédula/i).fill(testCedula);
    await page.getByRole('button', { name: /Iniciar sesión/i }).click();

    // 3. Redirección automática al Portal Coder
    await expect(page).toHaveURL(/\/coder\/new-excuse/);
    await expect(page.getByText(/Portal del Coder/i)).toBeVisible();

    // 4. Paso 1: Diligenciamiento de Formulario
    // Seleccionar Novedad (Incapacidad Médica por defecto o click explícito)
    const incapacidadBtn = page.getByRole('button', { name: /Incapacidad Médica/i });
    await expect(incapacidadBtn).toBeVisible();
    await incapacidadBtn.click();

    // Rellenar descripción detallada (mínimo 30 caracteres)
    const validDescription = 'Presento cuadro viral agudo con fiebre alta y reposo médico certificado por EPS Sura por 48 horas.';
    const descTextarea = page.getByPlaceholder(/Explica detalladamente la causa/i);
    await descTextarea.fill(validDescription);

    // Marcar Declaración bajo gravedad de juramento
    const truthCheckbox = page.locator('input[type="checkbox"]').first();
    await truthCheckbox.check();
    await expect(truthCheckbox).toBeChecked();

    // Avanzar a Paso 2: Evidencias
    const continueBtn = page.getByRole('button', { name: /Continuar con Evidencias/i });
    await continueBtn.click();

    // 5. Paso 2: Carga de Evidencia PDF
    await expect(page.getByText(/Paso 2: Adjuntar Soportes Probatorios/i)).toBeVisible();
    await expect(page.getByText(/Paso 2 de 2/i)).toBeVisible();

    // Adjuntar archivo PDF sintético con Magic Bytes válidos (%PDF-1.4)
    const fixturePdfPath = path.join(__dirname, 'fixtures', 'test_incapacidad.pdf');
    const fileInput = page.locator('input[type="file"]').last();
    await fileInput.setInputFiles(fixturePdfPath);

    // Verificar que el archivo aparece listado en la cola de evidencias
    await expect(page.getByText('test_incapacidad.pdf')).toBeVisible();

    // Esperar a que termine la simulación de carga y análisis de legibilidad
    await page.waitForTimeout(1000);

    // 6. Enviar Formulario Final
    const submitBtn = page.getByRole('button', { name: /Enviar Justificación/i });
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // 7. Verificación de Pantalla de Confirmación y Radicado Oficial
    await expect(page.getByText(/¡Tu justificación ha sido enviada!/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Reporte Radicado Exitosamente/i)).toBeVisible();

    // Validar formato del número de radicado RAD-HSE-YYYY-XXXXXX
    const radicadoBadge = page.locator('span:has-text("RAD-HSE-")');
    await expect(radicadoBadge).toBeVisible();
    const radicadoText = await radicadoBadge.textContent();
    expect(radicadoText).toMatch(/RAD-HSE-\d{4}-\d+/);

    // Validar cantidad de evidencias registradas
    await expect(page.getByText(/1 soporte\(s\) registrado\(s\)/i)).toBeVisible();
  });
});
