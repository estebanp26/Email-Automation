import { test as base, expect } from '@playwright/test';

export const test = base.extend({
  page: async ({ page }, use) => {
    await page.addInitScript(() => {
      localStorage.setItem('hse_token', 'jwt_hse_admin_12345');
      localStorage.setItem('hse_role', 'hse');
    });

    await use(page);
  },
});

export { expect };
