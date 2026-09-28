/**
 * Servicio de Integración con n8n Workflow — HSE RIWI
 * Conecta las acciones manuales del Frontend con los Webhooks de n8n:
 *  - Webhook Despacho HSE: /webhook/riwi-hse-dispatch-email (o /webhook-test/...)
 *  - Webhook Correo Entrante: /webhook/riwi-email-incoming (o /webhook-test/...)
 */

export interface N8nConfig {
  baseUrl: string;
  useTestWebhook: boolean;
  dispatchWebhookPath: string;
  incomingWebhookPath: string;
}

export interface HseDecisionPayload {
  justification_id: string;
  action: 'APPROVED' | 'DISAPPROVED' | 'REQUEST_CORRECTION';
  coder_name: string;
  recipient_email: string;
  start_date?: string;
  excuse_type?: string;
  hse_notes: string;
  hse_reviewer_name: string;
}

export interface IncomingEmailPayload {
  source_provider?: 'OUTLOOK' | 'GMAIL';
  sender_name: string;
  sender_email: string;
  email_subject: string;
  email_body: string;
  attachments?: Array<{
    filename: string;
    mime_type: string;
    data_base64?: string;
  }>;
}

const STORAGE_KEY = 'riwi_hse_n8n_config';

export function getN8nConfig(): N8nConfig {
  const envBaseUrl = import.meta.env.VITE_N8N_URL || 'http://localhost:5678';
  const envUseTest = import.meta.env.VITE_N8N_USE_TEST_WEBHOOK === 'true' || import.meta.env.DEV;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        baseUrl: parsed.baseUrl || envBaseUrl,
        useTestWebhook: typeof parsed.useTestWebhook === 'boolean' ? parsed.useTestWebhook : envUseTest,
        dispatchWebhookPath: parsed.dispatchWebhookPath || 'riwi-hse-dispatch-email',
        incomingWebhookPath: parsed.incomingWebhookPath || 'riwi-email-incoming',
      };
    }
  } catch (e) {
    console.warn('No se pudo cargar la configuración de n8n desde localStorage:', e);
  }

  return {
    baseUrl: envBaseUrl,
    useTestWebhook: envUseTest,
    dispatchWebhookPath: 'riwi-hse-dispatch-email',
    incomingWebhookPath: 'riwi-email-incoming',
  };
}

export function saveN8nConfig(config: Partial<N8nConfig>): N8nConfig {
  const current = getN8nConfig();
  const updated: N8nConfig = { ...current, ...config };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (e) {
    console.error('Error guardando configuración de n8n:', e);
  }
  return updated;
}

export function buildWebhookUrl(path: string, useTest?: boolean): string {
  const cfg = getN8nConfig();
  const base = cfg.baseUrl.replace(/\/+$/, '');
  const cleanPath = path.replace(/^\/+/, '');
  const isTest = typeof useTest === 'boolean' ? useTest : cfg.useTestWebhook;
  const prefix = isTest ? 'webhook-test' : 'webhook';
  return `${base}/${prefix}/${cleanPath}`;
}

export function getDispatchWebhookUrl(): string {
  const cfg = getN8nConfig();
  return buildWebhookUrl(cfg.dispatchWebhookPath, cfg.useTestWebhook);
}

export function getIncomingWebhookUrl(): string {
  const cfg = getN8nConfig();
  return buildWebhookUrl(cfg.incomingWebhookPath, cfg.useTestWebhook);
}

/**
 * Despacha la resolución de un caso de HSE directamente al Webhook de n8n.
 */
export async function dispatchHseDecision(payload: HseDecisionPayload): Promise<{ success: boolean; data?: any; error?: string }> {
  const url = getDispatchWebhookUrl();

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      return {
        success: false,
        error: `n8n respondió con HTTP ${response.status}: ${errorText || response.statusText}`,
      };
    }

    const data = await response.json().catch(() => ({ status: 'received' }));
    return {
      success: true,
      data,
    };
  } catch (err: any) {
    console.error('Error al conectar con Webhook de n8n:', err);
    return {
      success: false,
      error: err.message || 'No se pudo conectar con el servidor n8n. Revisa si n8n está activo y si la URL es correcta.',
    };
  }
}

/**
 * Envía un correo simulado al webhook de entrada de n8n para probar el flujo completo.
 */
export async function sendIncomingEmailSimulation(payload: IncomingEmailPayload): Promise<{ success: boolean; data?: any; error?: string }> {
  const url = getIncomingWebhookUrl();

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        source_provider: payload.source_provider || 'OUTLOOK',
        message_id: `sim_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
        sender_name: payload.sender_name,
        sender_email: payload.sender_email,
        email_subject: payload.email_subject,
        email_body: payload.email_body,
        received_at: new Date().toISOString(),
        attachments: payload.attachments || [],
      }),
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      return {
        success: false,
        error: `n8n respondió con HTTP ${response.status}: ${errorText || response.statusText}`,
      };
    }

    const data = await response.json().catch(() => ({ status: 'received' }));
    return {
      success: true,
      data,
    };
  } catch (err: any) {
    console.error('Error al simular correo en n8n:', err);
    return {
      success: false,
      error: err.message || 'No se pudo conectar con el webhook de entrada de n8n.',
    };
  }
}

/**
 * Prueba la conectividad básica con n8n
 */
export async function testN8nConnection(): Promise<{ success: boolean; message: string; url: string }> {
  const url = getDispatchWebhookUrl();
  try {
    // n8n webhooks suelen responder a OPTIONS o a POST vacío / HEAD
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ping: true, test: true }),
    });

    if (res.status === 404) {
      return {
        success: false,
        url,
        message: `El webhook respondió 404. Si usas modo Test ('webhook-test'), recuerda hacer clic en 'Listen for test event' en n8n. Si usas Producción ('webhook'), asegúrate de activar el workflow.`,
      };
    }

    if (res.ok) {
      return {
        success: true,
        url,
        message: `¡Conexión exitosa con n8n! (HTTP ${res.status})`,
      };
    }

    return {
      success: false,
      url,
      message: `El webhook respondió con código ${res.status}: ${res.statusText}`,
    };
  } catch (err: any) {
    return {
      success: false,
      url,
      message: `No se pudo alcanzar la URL: ${err.message}. Verifica que n8n esté corriendo en esa dirección.`,
    };
  }
}
