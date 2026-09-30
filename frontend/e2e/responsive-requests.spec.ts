import { test, expect } from '@playwright/test';

test.describe('Subtask 4: Responsive Requests Page (Master-Detail)', () => {
  test('debe permitir navegar maestro-detalle y alternar carpetas en móvil sin overflow', async ({ page }) => {
    // 1. Simular autenticación HSE
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/login');
    await page.evaluate(() => {
      localStorage.setItem('hse_token', 'jwt_hse_admin_12345');
      localStorage.setItem('hse_role', 'hse');
    });

    // 2. Ir a Solicitudes (/requests)
    await page.goto('/requests');

    // 3. Verificar que las píldoras de carpetas móviles sean visibles
    await expect(page.getByRole('button', { name: /Bandeja/i }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Enviados/i }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Redactar/i }).first()).toBeVisible();

    // 4. Verificar ausencia de overflow horizontal en móvil
    const isOverflowingMobile = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingMobile).toBe(false);

    // 5. Probar pulsar el botón Redactar en móvil para abrir el editor y luego volver
    await page.getByRole('button', { name: /Redactar/i }).first().click();
    await expect(page.getByText('Nuevo Mensaje')).toBeVisible();

    // Pulsar botón de volver (ArrowLeft)
    const backBtn = page.getByRole('button', { name: 'Volver a la lista' });
    await expect(backBtn).toBeVisible();
    await backBtn.click();

    // Debe regresar a la lista
    await expect(page.getByText('Nuevo Mensaje')).not.toBeVisible();

    // 6. Probar en viewport de tablet (768px)
    await page.setViewportSize({ width: 768, height: 1024 });
    const isOverflowingTablet = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingTablet).toBe(false);
  });
});
