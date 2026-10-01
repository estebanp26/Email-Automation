import { test as base, expect } from '@playwright/test';

export const test = base.extend({
  page: async ({ page }, use) => {
    await page.addInitScript(() => {
      localStorage.setItem('hse_token', 'jwt_hse_admin_12345');
      localStorage.setItem('hse_role', 'hse');
    });

    // Interceptar solicitudes API críticas para que los tests E2E no dependan de backend en CI
    await page.route('**/api/students', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'coder-e2e-1',
            name: 'Ana Gomez',
            email: 'ana.gomez@riwi.io',
            cedula: '1000000101',
            route: 'Frontend',
            status: 'Activo',
            attendance: { present: 38, late: 1, justifiedAbsence: 1, unjustifiedAbsence: 0 }
          },
          {
            id: 'coder-e2e-2',
            name: 'Carlos Perez',
            email: 'carlos.perez@riwi.io',
            cedula: '1000000102',
            route: 'Backend',
            status: 'Activo',
            attendance: { present: 35, late: 3, justifiedAbsence: 1, unjustifiedAbsence: 1 }
          }
        ]),
      });
    });

    await use(page);
  },
});

export { expect };
