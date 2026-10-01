import type { Request, Student, KPIStats } from '../types';

export const mockStudents: Student[] = [
  {
    id: 's1',
    name: 'Ana Gomez',
    email: 'ana@ejemplo.com',
    cedula: '1000000101',
    route: 'Frontend',
    status: 'Activo',
    attendance: { present: 40, late: 2, justifiedAbsence: 1, unjustifiedAbsence: 0 }
  },
  {
    id: 's2',
    name: 'Carlos Perez',
    email: 'carlos@ejemplo.com',
    cedula: '1000000102',
    route: 'Backend',
    status: 'Activo',
    attendance: { present: 35, late: 5, justifiedAbsence: 0, unjustifiedAbsence: 3 }
  }
];

export const mockRequests: Request[] = [
  {
    id: 'r1',
    studentId: 's1',
    route: 'Frontend',
    emailInfo: {
      senderName: 'Ana Gomez',
      senderEmail: 'ana@ejemplo.com',
      subject: 'Incapacidad médica por 3 días',
      body: 'Adjunto incapacidad médica debido a una fuerte gripe. Estaré ausente hasta el jueves.',
      date: '2023-10-25T10:00:00Z',
      attachments: [{ 
        name: 'incapacidad_ana.pdf', 
        url: 'data:application/pdf;base64,JVBERi0xLjQKJcOkw7zDtsOfCjEgMCBvYmoKPDwKL1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDIgMCBSCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCj4+CmVuZG9iagozIDAgb2JqCjw8Ci9UeXBlIC9QYWdlCi9QYXJlbnQgMiAwIFIKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KL0NvbnRlbnRzIDQgMCBSCj4+CmVuZG9iago0IDAgb2JqCjw8Ci9MZW5ndGggODAKPj4Kc3RyZWFtCkJUCi9GMSAxMiBUZgoxMDAgNzAwIFREClsoQ2VydGlmaWNhZG8gZGUgSW5jYXBhY2lkYWQgTWVkaWNhIC0gQW5hIEdvbWV6IC0gUml3aSBFZHVjYXRpb24pXSBUSgpFVAplbmRzdHJlYW0KZW5kb2JqCnhyZWYKMCA1CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAxNSAwMDAwMCBuIAowMDAwMDAwMDY4IDAwMDAwIG4gCjAwMDAwMDAxMjUgMDAwMDAgbiAKMDAwMDAwMDIxMyAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMSAwIFIKPj4Kc3RhcnR4cmVmCjM0MgolJUVPRg==',
        mime_type: 'application/pdf'
      }]
    },
    status: 'approved',
    decision: {
      source: 'ai',
      confidence: 0.98,
      reasoning: 'El correo contiene un adjunto PDF válido de incapacidad médica coherente con las fechas.'
    }
  },
  {
    id: 'r2',
    studentId: 's2',
    route: 'Backend',
    emailInfo: {
      senderName: 'Carlos Perez',
      senderEmail: 'carlos@ejemplo.com',
      subject: 'Problemas de internet en el barrio',
      body: 'No podré conectarme hoy porque hay una falla general de internet en mi sector.',
      date: '2023-10-26T08:30:00Z'
    },
    status: 'pending_review',
    decision: {
      source: 'ai',
      confidence: 0.65,
      reasoning: 'Motivo técnico sin adjuntos probatorios. Se sugiere revisión manual.'
    }
  }
];

export const mockStats: KPIStats = {
  total: 156,
  approved: 120,
  denied: 12,
  pending: 24
};

export const mockRequestsPerWeek = [
  { name: 'Lun', solicitudes: 12 },
  { name: 'Mar', solicitudes: 19 },
  { name: 'Mie', solicitudes: 15 },
  { name: 'Jue', solicitudes: 22 },
  { name: 'Vie', solicitudes: 18 },
];

export const mockEmails = [
  { id: '1', subject: 'Incapacidad médica', sender: 'ana@example.com', date: '2023-10-25T10:00:00Z', snippet: 'Adjunto incapacidad por 3 días...' },
];
