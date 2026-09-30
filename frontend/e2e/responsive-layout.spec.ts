import { test, expect } from './fixtures/auth';

test.describe('Subtask 1: Responsive Layout & Mobile Navigation Drawer', () => {
  test.use({ viewport: { width: 375, height: 667 } }); // iPhone SE viewport

  test('debe mostrar barra superior móvil, alternar drawer con botón hamburguesa y cerrar al navegar', async ({ page }) => {
    // 1. Navegar al dashboard (autenticación HSE inyectada previamente por fixture)
    await page.goto('/');

    // 3. Verificar que el header móvil superior es visible
    const mobileHeader = page.locator('header.lg\\:hidden');
    await expect(mobileHeader).toBeVisible();

    // 4. El botón hamburguesa debe estar visible
    const hamburgerBtn = page.getByRole('button', { name: /Abrir menú/i });
    await expect(hamburgerBtn).toBeVisible();

    // 5. Abrir el drawer móvil
    await hamburgerBtn.click();

    // 6. Enlaces de navegación deben ser visibles en el drawer
    const requestsNavLink = page.getByRole('link', { name: /Solicitudes/i });
    await expect(requestsNavLink).toBeVisible();

    // 7. Navegar a solicitudes
    await requestsNavLink.click();
    await expect(page).toHaveURL(/\/requests/);

    // 8. Verificar que no haya desbordamiento horizontal en el viewport móvil
    const isOverflowing = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(isOverflowing).toBe(false);
  });
});
