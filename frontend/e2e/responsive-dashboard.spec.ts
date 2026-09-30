import { test, expect } from '@playwright/test';

test.describe('Subtask 3: Responsive HSE Dashboard', () => {
  test('debe renderizar KPIs y gráficos responsivos en móvil y tablet sin overflow', async ({ page }) => {
    // 1. Simular autenticación HSE
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/login');
    await page.evaluate(() => {
      localStorage.setItem('hse_token', 'jwt_hse_admin_12345');
      localStorage.setItem('hse_role', 'hse');
    });

    // 2. Ir al dashboard en móvil
    await page.goto('/');

    // 3. Verificar título y KPIs
    await expect(page.getByText(/Resumen del Sistema HSE - Barranquilla/i)).toBeVisible();
    await expect(page.getByText(/¡Bienvenido de nuevo, Paola!/i)).toBeVisible();

    // Las 4 métricas deben ser visibles
    await expect(page.getByText('Total', { exact: true })).toBeVisible();
    await expect(page.getByText('Aprobados').first()).toBeVisible();
    await expect(page.getByText('Denegados').first()).toBeVisible();
    await expect(page.getByText('Por revisar').first()).toBeVisible();

    // 4. Verificar que no haya overflow horizontal en móvil
    const isOverflowingMobile = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingMobile).toBe(false);

    // 5. Verificar en tablet (768px)
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.getByText(/Solicitudes por semana/i)).toBeVisible();
    const isOverflowingTablet = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingTablet).toBe(false);
  });
});
