import { test, expect } from '@playwright/test';

test.describe('Sub-task 3: Flujo HSE Analista E2E', () => {
  test('debe permitir a la Analista HSE iniciar sesión, ver bandeja, abrir detalle de solicitud y resolverla manualmente', async ({ page }) => {
    // 1. Interceptar solicitudes de API para asegurar un entorno hermético y reproducible
    await page.route('**/api/requests*', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'just-req-101',
              studentId: 'coder-1001',
              emailInfo: {
                senderName: 'Carlos Mendoza',
                senderEmail: 'carlos.mendoza@riwi.io',
                subject: 'Excusa por Inasistencia Medica EPS Sura',
                body: 'Buen dia Team Leader, remito mi incapacidad medica otorgada por la EPS por cuadro respiratorio agudo.',
                date: new Date().toISOString(),
                attachments: [{ name: 'incapacidad_medica.pdf', url: '#' }],
              },
              route: 'Desarrollo Web Fullstack',
              status: 'pending_review',
              decision: {
                source: 'ai',
                confidence: 0.94,
                reasoning: 'Incapacidad expedida por EPS Sura. Rango de reposo coherente con fechas solicitadas.',
              },
            },
          ]),
        });
      } else {
        await route.continue();
      }
    });

    // Interceptar endpoint de resolución
    await page.route('**/api/requests/**/resolve', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          status: 'APPROVED',
          message: 'Decisión registrada exitosamente.',
          details: 'Notificación despachada al estudiante y sincronizada con el portal.',
        }),
      });
    });

    // 2. Login como Analista HSE (admin)
    await page.goto('/login');
    await page.getByPlaceholder(/Usuario, correo o cédula/i).fill('admin@riwi.io');
    await page.getByPlaceholder(/Contraseña o cédula/i).fill('admin123');
    await page.getByRole('button', { name: /Iniciar sesión/i }).click();

    // 3. Verificar navegación al Dashboard principal de HSE
    await expect(page).toHaveURL(/\/(#|\?|$)/);

    // 4. Navegar a Bandeja de Solicitudes (/requests)
    await page.goto('/requests');
    await expect(page.getByText(/Bandeja de Entrada/i).first()).toBeVisible();

    // 5. Verificar que la solicitud aparece en la lista
    const requestCard = page.getByText(/Carlos Mendoza/i).first();
    await expect(requestCard).toBeVisible();
    await requestCard.click();

    // 6. Verificar panel de detalle y visor de justificación
    await expect(page.getByText(/Excusa por Inasistencia Medica EPS Sura/i).first()).toBeVisible();
    await expect(page.getByText(/incapacidad_medica.pdf/i)).toBeVisible();
    await expect(page.getByText(/94% de Certidumbre/i)).toBeVisible();

    // 7. Diligenciar Resolución Manual
    const hseNotesTextarea = page.getByPlaceholder(/Escribe las notas de aprobación/i);
    await expect(hseNotesTextarea).toBeVisible();
    await hseNotesTextarea.fill('Incapacidad médica verificada en portal EPS Sura. Aprobada por Team Leader Paola.');

    // Hacer click en "Aprobar Excusa"
    const approveBtn = page.getByRole('button', { name: /Aprobar Excusa/i });
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // 8. Verificar confirmación visual de la resolución
    await expect(page.getByText(/Caso aprobado formalmente por el equipo HSE/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Decisión persistida en base de datos/i)).toBeVisible();
  });
});
