import { mockStudents, mockEmails, mockRequests, mockStats, mockRequestsPerWeek } from '../data/mock';
import { dispatchHseDecision, type HseDecisionPayload } from './n8n';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const api = {
  getDashboardStats: async () => {
    await delay(300);
    return mockStats;
  },
  getRequestsPerWeek: async () => {
    await delay(300);
    return mockRequestsPerWeek;
  },
  getRecentEmails: async () => {
    await delay(300);
    return mockEmails;
  },
  getRequests: async (filters?: any) => {
    await delay(400);
    let filtered = [...mockRequests];
    if (filters?.status) {
      filtered = filtered.filter((r) => r.status === filters.status);
    }
    return filtered;
  },
  getStudents: async () => {
    await delay(300);
    return mockStudents;
  },
  updateRequestStatus: async (id: string, status: any) => {
    await delay(300);
    const req = mockRequests.find((r) => r.id === id);
    if (req) req.status = status;
    return req;
  },
  modifyAiDecision: async (id: string, decision: any) => {
    await delay(300);
    const req = mockRequests.find((r) => r.id === id);
    if (req) (req as any).decision = decision;
    return req;
  },

  /**
   * Resuelve una justificación manualmente y dispara el webhook en n8n
   */
  resolveRequestWithN8n: async (
    id: string,
    action: 'APPROVED' | 'DISAPPROVED' | 'REQUEST_CORRECTION',
    notes: string,
    options?: {
      startDate?: string;
      excuseType?: string;
      reviewerName?: string;
    }
  ) => {
    const req = mockRequests.find((r) => r.id === id);
    if (!req) {
      throw new Error(`No se encontró la solicitud con ID ${id}`);
    }

    // Actualizar estado local
    const mappedStatus = action === 'APPROVED' ? 'approved' : action === 'DISAPPROVED' ? 'denied' : 'pending_review';
    req.status = mappedStatus;
    req.decision = {
      source: 'human',
      confidence: 1.0,
      reasoning: notes,
      modifiedBy: options?.reviewerName || 'Analista HSE',
      modifiedAt: new Date().toISOString(),
    };

    // Armar el payload exacto esperado por el nodo 'Webhook Despachar Notificación HSE' de n8n
    const n8nPayload: HseDecisionPayload = {
      justification_id: req.id,
      action: action,
      coder_name: req.emailInfo?.senderName || 'Coder',
      recipient_email: req.emailInfo?.senderEmail || 'coder@riwi.io',
      start_date: options?.startDate || new Date(req.emailInfo.date).toISOString().split('T')[0],
      excuse_type: options?.excuseType || 'inasistencia_medica',
      hse_notes: notes,
      hse_reviewer_name: options?.reviewerName || 'Equipo HSE RIWI',
    };

    // Despachar a n8n
    const n8nResult = await dispatchHseDecision(n8nPayload);

    return {
      request: req,
      n8n: n8nResult,
    };
  },
};
