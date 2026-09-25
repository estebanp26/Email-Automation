# Squad Conexión (Email Providers)

**Responsable:** Samuel  

## Responsabilidades:
1. **Microsoft Graph API (Outlook / Office 365):**
   - Configuración de Azure App Registration (Permisos: `Mail.ReadWrite`, `Mail.Send`).
   - Setup del Webhook / Subscription de notificaciones entrantes de Graph API hacia n8n.
   - Creación de plantilla/nodo para enviar respuesta en el mismo hilo de conversación (*Reply-To*).
2. **Google Workspace API (Gmail):**
   - Configuración de Google Cloud Console (OAuth Client / Service Account con delegación de dominio o Pub/Sub).
   - Setup de suscripción Pub/Sub para notificaciones push en tiempo real hacia n8n.
3. **Adaptador de Normalización:**
   - Garantizar que sin importar si el correo viene de Outlook o Gmail, el payload enviado al subflujo de n8n tenga la misma estructura (remitente, asunto, cuerpo HTML/texto, y lista de adjuntos en base64 o buffer).
