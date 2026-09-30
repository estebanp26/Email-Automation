import { test, expect } from '@playwright/test';

test.describe('Subtask 2: Responsive Login Page', () => {
  test('debe renderizar el login perfectamente en viewport móvil sin desbordamiento horizontal', async ({ page }) => {
    // 1. Simular viewport móvil estándar (iPhone SE / Android)
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/login');

    // 2. Verificar que los elementos esenciales están visibles y centrados
    const loginCard = page.locator('form');
    await expect(loginCard).toBeVisible();

    const userInput = page.getByPlaceholder(/Usuario, correo o cédula/i);
    const passInput = page.getByPlaceholder(/Contraseña o cédula/i);
    const submitBtn = page.getByRole('button', { name: /Iniciar sesión/i });

    await expect(userInput).toBeVisible();
    await expect(passInput).toBeVisible();
    await expect(submitBtn).toBeVisible();

    // 3. Verificar que no exista scroll horizontal indeseado
    const isOverflowing = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowing).toBe(false);

    // 4. Probar en viewport de tablet (iPad Mini 768px)
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(userInput).toBeVisible();
    const isOverflowingTablet = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowingTablet).toBe(false);
  });
});
