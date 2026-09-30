import { test, expect } from '@playwright/test';

test.describe('Sub-task 4: RBAC & Route Protection Guards', () => {
  test('debe redirigir al login si un usuario anónimo intenta acceder a rutas protegidas', async ({ page }) => {
    // 1. Limpiar cualquier token previo
    await page.goto('/login');
    await page.evaluate(() => localStorage.clear());

    // 2. Intentar ingresar a la raíz / (protegida para HSE)
    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);

    // 3. Intentar ingresar a /requests (Bandeja de Analista)
    await page.goto('/requests');
    await expect(page).toHaveURL(/\/login/);

    // 4. Intentar ingresar a /students
    await page.goto('/students');
    await expect(page).toHaveURL(/\/login/);
  });

  test('debe bloquear a un Coder de entrar a rutas HSE y redirigirlo a su portal', async ({ page }) => {
    // Simular sesión activa de Coder en localStorage
    await page.goto('/login');
    await page.evaluate(() => {
      localStorage.setItem('hse_token', 'jwt_coder_1001234567');
      localStorage.setItem('hse_role', 'coder');
      localStorage.setItem(
        'hse_coder_session',
        JSON.stringify({
          id: 'coder-1001234567',
          name: 'Coder 1001234567',
          cedula: '1001234567',
          email: '1001234567@riwi.io',
          route: 'Desarrollo de Software',
        })
      );
    });

    // Intentar acceder al panel HSE de requests
    await page.goto('/requests');

    // Debe ser redirigido forzosamente a /coder/new-excuse
    await expect(page).toHaveURL(/\/coder\/new-excuse/);
  });
});
