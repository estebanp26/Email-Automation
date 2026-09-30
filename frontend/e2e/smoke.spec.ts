import { test, expect } from '@playwright/test';

test.describe('Sub-task 1: Setup & Smoke Test', () => {
  test('should load login page and render authentication elements properly', async ({ page }) => {
    await page.goto('/login');

    // Verify Title and Headings
    await expect(page).toHaveTitle(/Riwi/i);
    await expect(page.getByRole('heading', { name: /Inicia sesión en tu cuenta/i })).toBeVisible();

    // Verify Input Fields
    const usernameInput = page.getByPlaceholder(/Usuario, correo o cédula/i);
    const passwordInput = page.getByPlaceholder(/Contraseña o cédula/i);
    const submitButton = page.getByRole('button', { name: /Iniciar sesión/i });

    await expect(usernameInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(submitButton).toBeVisible();

    // Verify Riwi astronaut mascot presence
    const mascotImg = page.getByAltText(/Riwi Fox Astronaut/i);
    await expect(mascotImg).toBeVisible();
  });
});
