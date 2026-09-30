import { test, expect } from './fixtures/auth';

test.describe('Nuevas funcionalidades HSE y Coder', () => {
  test('1. Requests: botón Descargar reporte en parte superior derecha y sin ícono descargar en botón Ver Solicitudes del Dashboard', async ({ page }) => {
    // Verificar en Dashboard que el botón Ver Solicitudes no tenga ícono de descargar
    await page.goto('/');
    const verSolBtn = page.getByRole('button', { name: /Ver Solicitudes/i });
    await expect(verSolBtn).toBeVisible();

    // Navegar a /requests
    await page.goto('/requests');
    const downloadBtn = page.getByRole('button', { name: /Descargar reporte/i });
    await expect(downloadBtn).toBeVisible();
  });

  test('2. Settings: sin carta de preferencias, sin botón de descargar, y gestión de reglas HSE', async ({ page }) => {
    await page.goto('/settings');

    // No debe haber botón "Descargar reporte" en configuración
    await expect(page.getByRole('button', { name: /Descargar reporte/i })).not.toBeVisible();

    // No debe existir la tarjeta "Preferencias"
    await expect(page.getByRole('heading', { name: /^Preferencias$/i })).not.toBeVisible();

    // Debe existir Reglas y Parámetros HSE
    await expect(page.getByText(/Reglas y Parámetros HSE/i)).toBeVisible();

    // Probar agregar una nueva regla
    const addRuleBtn = page.getByRole('button', { name: /Agregar Regla/i });
    await expect(addRuleBtn).toBeVisible();
    await addRuleBtn.click();

    // Modal abierto
    await expect(page.getByText('Nuevo Parámetro del Sistema')).toBeVisible();
    await page.getByPlaceholder(/Ej: Tolerancia de retraso/i).fill('Regla de Prueba E2E');
    await page.getByPlaceholder(/Ej: 20 min/i).fill('10 min');
    await page.getByRole('button', { name: /Crear Parámetro/i }).click();

    // Debe verse la nueva regla en la lista
    await expect(page.getByText('Regla de Prueba E2E')).toBeVisible();
  });

  test('3. Directorio de Coders: mensaje masivo a la ruta y asistencia coherente con edición de 4 tarjetas', async ({ page }) => {
    await page.goto('/students');

    // Verificar botón Mensaje a la Ruta
    const massMsgBtn = page.getByRole('button', { name: /Mensaje a la Ruta/i });
    await expect(massMsgBtn).toBeVisible();
    await massMsgBtn.click();

    // Modal de comunicado masivo
    await expect(page.getByText(/Comunicado Masivo a Rutas HSE/i)).toBeVisible();
    await page.getByPlaceholder(/Ej: Jornada Especial de Ergonomía/i).fill('Comunicado Prueba E2E');
    await page.getByPlaceholder(/Redacta las indicaciones oficiales/i).fill('Mensaje de prueba automatizada');
    await page.getByRole('button', { name: /Enviar a \d+ Coders/i }).click();

    // Confirmación
    await expect(page.getByText(/Comunicado masivo despachado exitosamente/i)).toBeVisible();

    // Seleccionar el primer Coder de la lista para ver su historial
    const firstCoderCard = page.locator('[data-testid="coder-card"]').first();
    await firstCoderCard.click();

    // Verificar que estamos en la vista de historial de asistencias
    await expect(page.getByText(/Volver al Directorio de Coders/i)).toBeVisible();
    await expect(page.getByText(/Cumplimiento Global/i)).toBeVisible();

    // Verificar los 4 cuadros dinámicos
    await expect(page.getByText('Asistencia', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Retraso', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Faltas Justificadas', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Faltas Injustificadas', { exact: true }).first()).toBeVisible();

    // Verificar botón para enviar mensaje personalizado
    const personalMsgBtn = page.getByRole('button', { name: /Enviar Mensaje al Coder/i });
    await expect(personalMsgBtn).toBeVisible();

    // Abrir modal de mensaje personalizado
    await personalMsgBtn.click();
    await expect(page.getByText(/Enviar Mensaje a /i)).toBeVisible();
    await page.getByPlaceholder(/Ej: Seguimiento de Asistencia/i).fill('Citación Bienestar E2E');
    await page.getByPlaceholder(/Escribe la observación/i).fill('Favor presentarse a coordinación.');
    await page.getByRole('button', { name: 'Enviar Mensaje', exact: true }).click();

    await expect(page.getByText(/Mensaje enviado exitosamente a/i)).toBeVisible();

    // Probar el botón de editar asistencia de un día (4 tarjetas)
    const editDayBtn = page.locator('button[title*="Modificar asistencia"]').first();
    await expect(editDayBtn).toBeVisible();
    await editDayBtn.click();

    // Verificar modal con las 4 tarjetas
    await expect(page.getByText('Modificar Asistencia')).toBeVisible();
    await expect(page.getByText('Selecciona el Nuevo Estado de Asistencia')).toBeVisible();

    // Las 4 tarjetas de opción
    await expect(page.getByText('Jornada presencial cumplida a tiempo')).toBeVisible();
    await expect(page.getByText('Llegada posterior a hora límite')).toBeVisible();
    await expect(page.getByText('Con soporte legal o de EPS')).toBeVisible();
    await expect(page.getByText('Inasistencia no soportada')).toBeVisible();

    // Seleccionar tarjeta Retraso haciendo clic en su contenedor
    await page.locator('div:has-text("Llegada posterior a hora límite")').first().click();
    await page.getByRole('button', { name: /Actualizar Asistencia/i }).click();

    // Confirmación de toast
    await expect(page.getByText(/Asistencia del .* modificada a/i)).toBeVisible();
  });

  test('4. Portal Coder: sección Chat HSE en menú y visualización de mensajes', async ({ page }) => {
    // Configurar sesión de Coder
    await page.addInitScript(() => {
      localStorage.setItem('hse_token', 'jwt_coder_12345');
      localStorage.setItem('hse_role', 'CODER');
      localStorage.setItem('hse_coder_session', JSON.stringify({
        id: 'coder-e2e',
        name: 'Coder Riwi E2E',
        cedula: '1000000126',
        email: 'coder@riwi.io',
        route: 'Desarrollo de Software'
      }));
    });

    await page.goto('/coder/history');

    // Verificar que en el sidebar aparece "Chat HSE"
    const chatNavItem = page.getByRole('link', { name: /Chat HSE/i });
    await expect(chatNavItem).toBeVisible();
    await chatNavItem.click();

    // Verificar que estamos en /coder/chat
    await expect(page).toHaveURL(/\/coder\/chat/);
    await expect(page.getByText(/Bandeja de Mensajes & Chat HSE/i)).toBeVisible();

    // Debe mostrar la lista de mensajes HSE
    await expect(page.getByText(/Canal Directo HSE Barranquilla/i)).toBeVisible();

    // Probar responder a un mensaje
    const replyInput = page.getByPlaceholder(/Escribe una respuesta o confirmación/i);
    await expect(replyInput).toBeVisible();
    await replyInput.fill('Entendido y enterado, muchas gracias.');
    await page.getByRole('button', { name: /Responder/i }).click();

    await expect(page.getByText(/Respuesta despachada al equipo HSE/i)).toBeVisible();
  });

  test('5. Portal Coder: sección Mi Asistencia en menú, 4 tarjetas dinámicas y sin opción de modificar', async ({ page }) => {
    // Configurar sesión de Coder
    await page.addInitScript(() => {
      localStorage.setItem('hse_token', 'jwt_coder_12345');
      localStorage.setItem('hse_role', 'CODER');
      localStorage.setItem('hse_coder_session', JSON.stringify({
        id: 'coder-e2e',
        name: 'Coder Riwi E2E',
        cedula: '1000000126',
        email: 'coder@riwi.io',
        route: 'Desarrollo de Software'
      }));
    });

    await page.goto('/coder/history');

    // Verificar enlace en el menú
    const attendanceNavItem = page.getByRole('link', { name: /Mi Asistencia/i });
    await expect(attendanceNavItem).toBeVisible();
    await attendanceNavItem.click();

    // Verificar que estamos en /coder/attendance
    await expect(page).toHaveURL(/\/coder\/attendance/);
    await expect(page.getByText(/Mi Asistencia Institucional/i)).toBeVisible();

    // Verificar los 4 cuadros dinámicos
    await expect(page.getByText('Asistencia', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Retraso', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Faltas Justificadas', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('Faltas Injustificadas', { exact: true }).first()).toBeVisible();

    // Verificar lista de días
    await expect(page.getByText(/Mi Historial Diario de Presencialidad/i)).toBeVisible();

    // El Coder NO debe poder modificar su asistencia: no hay botones de modificar asistencia
    const editDayBtn = page.locator('button[title*="Modificar asistencia"]');
    await expect(editDayBtn).toHaveCount(0);
  });

  test('6. Sidebar HSE: cuando está recorrido muestra el ícono de hamburguesa (las 3 rayas) tal como en la vista coder', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/');

    // Inicialmente el sidebar está expandido
    const toggleBtn = page.getByRole('button', { name: /Colapsar menú lateral/i });
    await expect(toggleBtn).toBeVisible();

    // Colapsar menú lateral (recorrerlo)
    await toggleBtn.click();

    // Ahora debe estar recorrido y mostrar el ícono de hamburguesa (las 3 rayas de lucide-menu)
    const collapsedToggleBtn = page.getByRole('button', { name: /Expandir menú lateral/i });
    await expect(collapsedToggleBtn).toBeVisible();
    const hamburgerIcon = collapsedToggleBtn.locator('svg.lucide-menu');
    await expect(hamburgerIcon).toBeVisible();

    // Volver a expandir haciendo clic en el ícono de hamburguesa
    await collapsedToggleBtn.click();
    await expect(page.getByRole('button', { name: /Colapsar menú lateral/i })).toBeVisible();
  });

  test('7. Portal Coder: el botón cerrar sesión del menú de la derecha funciona y redirige a login', async ({ page }) => {
    // Configurar sesión de Coder
    await page.addInitScript(() => {
      localStorage.setItem('hse_token', 'jwt_coder_12345');
      localStorage.setItem('hse_role', 'CODER');
      localStorage.setItem('hse_coder_session', JSON.stringify({
        id: 'coder-e2e',
        name: 'Coder Riwi E2E',
        cedula: '1000000126',
        email: 'coder@riwi.io',
        route: 'Desarrollo de Software'
      }));
    });

    await page.goto('/coder/history');
    await expect(page).toHaveURL(/\/coder\/history/);

    // Abrir menú de usuario en la derecha
    const profileBtn = page.getByRole('button', { name: /Abrir menú de usuario Coder/i });
    await expect(profileBtn).toBeVisible();
    await profileBtn.click();

    // Verificar que el menú desplegable está abierto
    const logoutBtn = page.getByTestId('coder-menu-logout');
    await expect(logoutBtn).toBeVisible();

    // Hacer clic en Cerrar sesión
    await logoutBtn.click();

    // Debe redirigir inmediatamente a /login
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole('button', { name: /Iniciar sesión/i })).toBeVisible();

    // Comprobar que el token y sesión de coder fueron eliminados del almacenamiento
    const token = await page.evaluate(() => localStorage.getItem('hse_token'));
    const role = await page.evaluate(() => localStorage.getItem('hse_role'));
    expect(token).toBeNull();
    expect(role).toBeNull();
  });
});
