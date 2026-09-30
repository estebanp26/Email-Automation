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

export type CoderJustificationStatus = 
  | 'APPROVED' 
  | 'DISAPPROVED' 
  | 'REVISION_MANUAL' 
  | 'REQUEST_CORRECTION';

export interface CoderAttachment {
  file_id: string;
  filename: string;
  size_bytes: number;
  mime_type: string;
  preview_url?: string;
  legibility_status?: 'optimal' | 'standard' | 'warning';
  legibility_reason?: string;
  storage_path?: string;
}

export interface CoderJustification {
  id: string;
  radicado: string;
  coder_id?: string;
  coder_cedula: string;
  coder_name: string;
  coder_email: string;
  academic_route: string;
  novelty_type: string;
  novelty_label?: string;
  start_date: string;
  end_date: string;
  description: string;
  truth_declaration: boolean;
  status: CoderJustificationStatus;
  hse_notes?: string;
  hse_reviewer?: string;
  hse_reviewed_at?: string;
  coder_response?: string;
  coder_correction_reply?: string;
  coder_response_at?: string;
  attachments: CoderAttachment[];
  submitted_at: string;
  updated_at?: string;
}
