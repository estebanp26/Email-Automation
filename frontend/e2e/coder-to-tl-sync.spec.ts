import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Integración Bidireccional Coder ↔ Team Leader', () => {
  test('debe reflejar la justificación y evidencia radicada por el Coder en la bandeja de la TL y sincronizar la resolución', async ({ page }) => {
    test.setTimeout(60000);

    // 1. Iniciar sesión como Coder
    await page.goto('/login');
    const coderCedula = '1005556677';
    await page.getByPlaceholder(/Usuario, correo o cédula/i).fill(coderCedula);
    await page.getByPlaceholder(/Contraseña o cédula/i).fill(coderCedula);
    await page.getByRole('button', { name: /Iniciar sesión/i }).click();

    await expect(page).toHaveURL(/\/coder\/new-excuse/);

    // 2. Diligenciar formulario de excusa
    const uniqueDescription = `Ausencia por cita medica especializada de optometria y control visual urgente (${Date.now()}).`;
    await page.getByPlaceholder(/Explica detalladamente la causa/i).fill(uniqueDescription);

    const truthCheckbox = page.locator('input[type="checkbox"]').first();
    await truthCheckbox.check();

    // Avanzar a Paso 2
    await page.getByRole('button', { name: /Continuar con Evidencias/i }).click();
    await expect(page.getByText(/Paso 2: Adjuntar Soportes Probatorios/i)).toBeVisible();

    // Adjuntar archivo PDF
    const fixturePdfPath = path.join(__dirname, 'fixtures', 'test_incapacidad.pdf');
    const fileInput = page.locator('input[type="file"]').last();
    await fileInput.setInputFiles(fixturePdfPath);
    await expect(page.getByText('test_incapacidad.pdf')).toBeVisible();

    // Esperar análisis de dropzone
    await page.waitForTimeout(1000);

    // Enviar formulario
    const submitBtn = page.getByRole('button', { name: /Enviar Justificación/i });
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // Esperar pantalla de confirmación y capturar número de radicado
    await expect(page.getByText(/¡Tu justificación ha sido enviada!/i)).toBeVisible({ timeout: 10000 });
    const radicadoBadge = page.locator('span:has-text("RAD-HSE-")');
    await expect(radicadoBadge).toBeVisible();
    const radicadoText = (await radicadoBadge.textContent()) || '';
    expect(radicadoText).toMatch(/RAD-HSE-\d{4}-\d+/);

    // 3. Cerrar sesión del Coder e iniciar sesión como Team Leader / Admin
    await page.evaluate(() => {
      localStorage.removeItem('hse_token');
      localStorage.removeItem('hse_role');
      localStorage.removeItem('hse_coder_session');
    });
    await page.goto('/login');
    await page.getByPlaceholder(/Usuario, correo o cédula/i).fill('admin@riwi.io');
    await page.getByPlaceholder(/Contraseña o cédula/i).fill('admin123');
    await page.getByRole('button', { name: /Iniciar sesión/i }).click();

    // Ir a la Bandeja de Solicitudes
    await page.goto('/requests');
    await expect(page.getByText(/Bandeja de Entrada/i).first()).toBeVisible();

    // 4. Verificar que la justificación radicada por el Coder aparece en la bandeja y seleccionarla
    const requestCardHeading = page.getByRole('heading', { level: 4, name: new RegExp(radicadoText) });
    await expect(requestCardHeading).toBeVisible({ timeout: 10000 });
    await requestCardHeading.click();

    // 5. Verificar detalle de la justificación en el visor de la TL
    await expect(page.getByRole('heading', { level: 2, name: new RegExp(radicadoText) })).toBeVisible();
    await expect(page.getByText(/test_incapacidad.pdf/i).first()).toBeVisible();
    await expect(page.getByText(/Ver evidencia ↗/i).first()).toBeVisible();

    // 6. Resolver la justificación como Aprobada
    const hseNotes = `Aprobado formalmente por Team Leader Paola. Radicado: ${radicadoText}`;
    const notesInput = page.getByPlaceholder(/Escribe las notas de aprobación/i);
    await notesInput.fill(hseNotes);

    const approveBtn = page.getByRole('button', { name: /Aprobar Excusa/i });
    await approveBtn.click();

    await expect(page.getByText(/Caso aprobado formalmente por el equipo HSE/i)).toBeVisible({ timeout: 10000 });

    // 7. Cerrar sesión de TL y volver como Coder para verificar el historial
    await page.evaluate(() => {
      localStorage.removeItem('hse_token');
      localStorage.removeItem('hse_role');
    });
    await page.goto('/login');
    await page.getByPlaceholder(/Usuario, correo o cédula/i).fill(coderCedula);
    await page.getByPlaceholder(/Contraseña o cédula/i).fill(coderCedula);
    await page.getByRole('button', { name: /Iniciar sesión/i }).click();

    await page.goto('/coder/history');
    await expect(page.getByText(/Historial de Solicitudes HSE/i)).toBeVisible();

    // Verificar que el radicado tiene estado Convalidada / Aprobada y las observaciones de la TL
    await expect(page.getByText(radicadoText).first()).toBeVisible();
    await expect(page.getByText(/Convalidada \/ Aprobada/i).first()).toBeVisible();
    await expect(page.getByText(hseNotes).first()).toBeVisible();
  });
});
