export type Status = 'approved' | 'denied' | 'pending_review';

export interface Decision {
  source: 'ai' | 'human';
  confidence?: number;
  reasoning?: string;
  modifiedBy?: string;
  modifiedAt?: string;
}

export interface Attendance {
  present: number;
  late: number;
  justifiedAbsence: number;
  unjustifiedAbsence: number;
}

export interface Student {
  id: string;
  name: string;
  email: string;
  cedula?: string;
  route: string;
  attendance?: Attendance;
}

export interface EmailInfo {
  senderName: string;
  senderEmail: string;
  subject: string;
  body: string;
  date: string;
  attachments?: { name: string; url: string }[];
  images?: string[];
}

export interface Request {
  id: string;
  studentId: string;
  emailInfo: EmailInfo;
  route: Student['route'];
  status: Status;
  decision: Decision;
}

export interface KPIStats {
  total: number;
  approved: number;
  denied: number;
  pending: number;
}

