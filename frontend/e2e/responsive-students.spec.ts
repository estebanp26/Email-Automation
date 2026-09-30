import { test, expect } from '@playwright/test';

test.describe('Subtask 5: Responsive Students Directory & Reports', () => {
  test('debe renderizar el directorio de coders y reportes en móvil y tablet sin overflow', async ({ page }) => {
    // 1. Simular autenticación HSE
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/login');
    await page.evaluate(() => {
      localStorage.setItem('hse_token', 'jwt_hse_admin_12345');
      localStorage.setItem('hse_role', 'hse');
    });

    // 2. Navegar a /students en móvil
    await page.goto('/students');
    await expect(page.getByText('Directorio de Coders RIWI')).toBeVisible();

    // Comprobar ausencia de desbordamiento horizontal en móvil
    const isOverflowingStudentsMobile = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingStudentsMobile).toBe(false);

    // Probar búsqueda
    const searchInput = page.getByPlaceholder(/Buscar por nombre/i);
    await expect(searchInput).toBeVisible();
    await searchInput.fill('RIWI');

    // 3. Probar en viewport de tablet (768px)
    await page.setViewportSize({ width: 768, height: 1024 });
    const isOverflowingStudentsTablet = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingStudentsTablet).toBe(false);

    // 4. Navegar a /reports
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/reports');
    await expect(page.getByText('Reportes y Analíticas')).toBeVisible();
    await expect(page.getByText('Tendencia de Solicitudes')).toBeVisible();
    await expect(page.getByText('Resumen Mensual')).toBeVisible();

    const isOverflowingReportsMobile = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingReportsMobile).toBe(false);

    // En tablet
    await page.setViewportSize({ width: 768, height: 1024 });
    const isOverflowingReportsTablet = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingReportsTablet).toBe(false);
  });
});
