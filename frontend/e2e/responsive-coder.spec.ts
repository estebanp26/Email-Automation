import { test, expect } from '@playwright/test';

test.describe('Subtask 6: Responsive Coder Excuse Submission Form', () => {
  test('debe permitir interactuar con el formulario y stepper en móvil y tablet sin overflow', async ({ page }) => {
    // 1. Simular autenticación Coder
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/login');
    await page.evaluate(() => {
      localStorage.setItem('hse_token', 'jwt_coder_test_12345');
      localStorage.setItem('hse_role', 'coder');
      localStorage.setItem('hse_coder_session', JSON.stringify({
        id: 'coder_camilo_1',
        name: 'Camilo Coder Real',
        cedula: '1000123456',
        email: 'camilo@riwi.io',
        route: 'Ruta 1 Node.js'
      }));
    });

    // 2. Navegar a /coder/new-excuse en móvil
    await page.goto('/coder/new-excuse');

    // 3. Verificar header y bienvenida
    await expect(page.getByText('Portal del Coder')).toBeVisible();
    await expect(page.getByText(/Hola, Camilo/i)).toBeVisible();

    // 4. Verificar stepper
    await expect(page.getByRole('button', { name: /1. Motivo/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /2. Evidencias/i })).toBeVisible();

    // 5. Verificar ausencia de overflow horizontal en móvil
    const isOverflowingCoderMobile = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingCoderMobile).toBe(false);

    // 6. Seleccionar un tipo de novedad táctil
    await page.getByText(/Calamidad Doméstica/i).first().click();

    // 7. Llenar campos requeridos para avanzar a Paso 2
    const descriptionTextarea = page.getByPlaceholder(/Explica detalladamente la causa/i);
    await descriptionTextarea.fill('Presenté una situación de calamidad médica urgente justificada debidamente.');
    
    // Marcar declaración bajo gravedad de juramento
    await page.getByRole('checkbox').check();

    // Avanzar a Paso 2
    await page.getByRole('button', { name: /Continuar con Evidencias/i }).click();

    // 8. Verificar que el Paso 2 esté visible y la dropzone esté lista
    await expect(page.getByText('Paso 2: Adjuntar Soportes Probatorios')).toBeVisible();
    await expect(page.getByText(/Arrastra y suelta tus evidencias/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Volver al Paso 1/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Enviar Justificación/i })).toBeVisible();

    // Comprobar que en Paso 2 tampoco haya overflow en móvil
    const isOverflowingStep2 = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingStep2).toBe(false);

    // 9. Verificar en tablet (768px)
    await page.setViewportSize({ width: 768, height: 1024 });
    const isOverflowingTablet = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingTablet).toBe(false);
  });
});
