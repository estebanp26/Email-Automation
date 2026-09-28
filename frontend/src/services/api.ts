import { mockStudents, mockEmails, mockRequests, mockStats, mockRequestsPerWeek } from '../data/mock';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const api = {
  getDashboardStats: async () => {
    await delay(500);
    return mockStats;
  },
  getRequestsPerWeek: async () => {
    await delay(500);
    return mockRequestsPerWeek;
  },
  getRecentEmails: async () => {
    await delay(500);
    return mockEmails;
  },
  getRequests: async (filters?: any) => {
    await delay(800);
    let filtered = [...mockRequests];
    if (filters?.status) {
      filtered = filtered.filter((r) => r.status === filters.status);
    }
    return filtered;
  },
  getStudents: async () => {
    await delay(500);
    return mockStudents;
  },
  updateRequestStatus: async (id: string, status: any) => {
    await delay(500);
    const req = mockRequests.find((r) => r.id === id);
    if (req) req.status = status;
    return req;
  },
  modifyAiDecision: async (id: string, decision: any) => {
    await delay(500);
    const req = mockRequests.find((r) => r.id === id);
    if (req) (req as any).decision = decision;
    return req;
  }
};
