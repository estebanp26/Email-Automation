import { mockStudents, mockEmails, mockRequests, mockStats, mockRequestsPerWeek } from '../data/mock';
import { dispatchHseDecision, type HseDecisionPayload } from './n8n';
import type { Request, Student, KPIStats } from '../types';

const API_BASE = import.meta.env.VITE_API_URL?.replace(/\/$/, '') || '';

export const api = {
  getDashboardStats: async (): Promise<KPIStats & { revisadas?: number; por_revisar?: number; approval_rate?: number }> => {
    try {
      const res = await fetch(`${API_BASE}/api/kpis`);
      if (res.ok) {
        const data = await res.json();
        return data;
      }
    } catch (e) {
      console.warn('Fallo al obtener KPIs del backend, usando respaldo:', e);
    }
    return mockStats;
  },

  getRequestsPerWeek: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/requests/weekly`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return data;
        }
      }
    } catch (e) {
      console.warn('Fallo al obtener datos semanales, usando respaldo:', e);
    }
    return mockRequestsPerWeek;
  },

  getRecentEmails: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/requests/recent?limit=10`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return data;
        }
      }
    } catch (e) {
      console.warn('Fallo al obtener correos recientes, usando respaldo:', e);
    }
    return mockEmails;
  },

  getRequests: async (filters?: any): Promise<Request[]> => {
    try {
      const queryParams = new URLSearchParams();
      if (filters?.status) queryParams.set('status', filters.status);
      queryParams.set('limit', '250');

      const res = await fetch(`${API_BASE}/api/requests?${queryParams.toString()}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return data;
        }
      }
    } catch (e) {
      console.warn('Fallo al obtener solicitudes reales, usando respaldo:', e);
    }
    let filtered = [...mockRequests];
    if (filters?.status) {
      filtered = filtered.filter((r) => r.status === filters.status);
    }
    return filtered;
  },

  getStudents: async (): Promise<Student[]> => {
    try {
      const res = await fetch(`${API_BASE}/api/students`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          return data;
        }
      }
    } catch (e) {
      console.warn('Fallo al obtener estudiantes reales, usando respaldo:', e);
    }
    return mockStudents;
  },

  updateRequestStatus: async (id: string, status: any) => {
    try {
      await fetch(`${API_BASE}/api/requests/${id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: status === 'approved' ? 'APPROVED' : status === 'denied' ? 'DISAPPROVED' : 'REQUEST_CORRECTION',
          notes: 'Actualización rápida desde interfaz'
        })
      });
    } catch (e) {
      console.warn('No se pudo actualizar en DB:', e);
    }
    const req = mockRequests.find((r) => r.id === id);
    if (req) req.status = status;
    return req;
  },

  modifyAiDecision: async (id: string, decision: any) => {
    const req = mockRequests.find((r) => r.id === id);
    if (req) (req as any).decision = decision;
    return req;
  },

  /**
   * Resuelve una justificación manualmente, actualiza la base de datos y dispara el webhook en n8n
   */
  resolveRequestWithN8n: async (
    id: string,
    action: 'APPROVED' | 'DISAPPROVED' | 'REQUEST_CORRECTION',
    notes: string,
    options?: {
      startDate?: string;
      excuseType?: string;
      reviewerName?: string;
      coderName?: string;
      recipientEmail?: string;
      requestObj?: any;
    }
  ) => {
    // 1. Actualizar en base de datos PostgreSQL a través de Strata Core
    try {
      await fetch(`${API_BASE}/api/requests/${id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: action,
          notes: notes,
          reviewer_name: options?.reviewerName || 'Team Leader Paola'
        })
      });
    } catch (dbErr) {
      console.warn('Aviso: no se pudo sincronizar decisión con PostgreSQL:', dbErr);
    }

    // 2. Construir objeto de solicitud actualizado para la interfaz
    const mappedStatus = action === 'APPROVED' ? 'approved' : action === 'DISAPPROVED' ? 'denied' : 'pending_review';
    const baseReq = options?.requestObj || mockRequests.find((r) => r.id === id) || { id };
    const updatedRequest = {
      ...baseReq,
      status: mappedStatus,
      decision: {
        source: 'human',
        confidence: 1.0,
        reasoning: notes,
        modifiedBy: options?.reviewerName || 'Paola Admin (HSE)',
        modifiedAt: new Date().toISOString(),
      },
    };

    // 3. Armar el payload exacto esperado por el nodo 'Webhook Despachar Notificación HSE' de n8n
    const n8nPayload: HseDecisionPayload = {
      justification_id: id,
      action: action,
      coder_name: options?.coderName || baseReq.emailInfo?.senderName || 'Coder',
      recipient_email: options?.recipientEmail || baseReq.emailInfo?.senderEmail || 'coder@riwi.io',
      start_date: options?.startDate || (baseReq.emailInfo?.date ? new Date(baseReq.emailInfo.date).toISOString().split('T')[0] : new Date().toISOString().split('T')[0]),
      excuse_type: options?.excuseType || 'inasistencia_medica',
      hse_notes: notes,
      hse_reviewer_name: options?.reviewerName || 'Equipo HSE RIWI',
    };

    // 4. Despachar a n8n
    const n8nResult = await dispatchHseDecision(n8nPayload);

    return {
      request: updatedRequest,
      n8n: n8nResult,
    };
  },
};
