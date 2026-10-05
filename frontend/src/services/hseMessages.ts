export interface HseMessage {
  id: string;
  sender: string;
  senderRole: string;
  recipientType: 'ROUTE' | 'CODER' | 'ALL';
  recipientTarget: string; // Route name or Coder email
  recipientName?: string;  // Route name or Coder display name
  routes?: string[];       // Target routes when multiple
  subject: string;
  body: string;
  priority: 'NORMAL' | 'URGENT' | 'INFO';
  createdAt: string;
  read?: boolean;
  replies?: Array<{
    id: string;
    sender: string;
    body: string;
    createdAt: string;
  }>;
}

const STORAGE_KEY = 'hse_messages_store';

const INITIAL_MESSAGES: HseMessage[] = [
  {
    id: 'msg-seed-1',
    sender: 'Paola Admin (HSE Barranquilla)',
    senderRole: 'Coordinación HSE & Bienestar',
    recipientType: 'ALL',
    recipientTarget: 'Todas las Rutas',
    recipientName: 'Comunidad RIWI',
    subject: 'Circular Informativa: Protocolos de Ingreso y Registro Biométrico',
    body: 'Estimados Coders, les recordamos que el horario de ingreso presencial inicia a las 07:45 AM. Todo registro posterior a las 08:15 AM computa como retraso en la plataforma de asistencia biométrica. Cuidemos nuestra puntualidad y disciplina profesional.',
    priority: 'INFO',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
    read: false
  },
  {
    id: 'msg-seed-2',
    sender: 'Paola Admin (HSE Barranquilla)',
    senderRole: 'Coordinación HSE & Bienestar',
    recipientType: 'ROUTE',
    recipientTarget: 'Desarrollo de Software',
    recipientName: 'Ruta Desarrollo de Software',
    routes: ['Desarrollo de Software'],
    subject: 'Jornada de Salud Visual y Ergonomía en Sala 3',
    body: 'Hola equipo de Desarrollo de Software. Este jueves a partir de las 10:00 AM tendremos una sesión especial de pausas activas y revisión optométrica preventiva en la sala de entrenamiento. Agradecemos su puntual asistencia.',
    priority: 'NORMAL',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 18).toISOString(),
    read: true
  },
  {
    id: 'msg-seed-3',
    sender: 'Paola Admin (HSE Barranquilla)',
    senderRole: 'Coordinación HSE & Bienestar',
    recipientType: 'CODER',
    recipientTarget: 'coder@riwi.io',
    recipientName: 'Coder Riwi',
    subject: 'Seguimiento de Asistencia y Justificación Médica',
    body: 'Apreciado coder, hemos recibido oportunamente tu soporte de incapacidad médica EPS Sura radicada en el portal. Tu estado ha sido actualizado como justificado en el libro de asistencia. Que sigas mejorando tu salud.',
    priority: 'NORMAL',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
    read: false
  }
];

export function getStoredMessages(): HseMessage[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch (e) {
    console.error('Error leyendo mensajes HSE:', e);
  }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_MESSAGES));
  } catch (e) {}
  return INITIAL_MESSAGES;
}

export function saveStoredMessages(messages: HseMessage[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    window.dispatchEvent(new Event('hse_messages_updated'));
  } catch (e) {
    console.error('Error guardando mensajes HSE:', e);
  }
}

/**
 * Enviar mensaje masivo a una o varias rutas
 */
export function sendMassRouteMessage(params: {
  routes: string[];
  subject: string;
  body: string;
  priority: 'NORMAL' | 'URGENT' | 'INFO';
  sender?: string;
}): HseMessage {
  const messages = getStoredMessages();
  const isAll = params.routes.includes('ALL') || params.routes.length === 0;

  const newMsg: HseMessage = {
    id: `msg-route-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
    sender: params.sender || 'Paola Admin (HSE Barranquilla)',
    senderRole: 'Coordinación HSE & Bienestar',
    recipientType: isAll ? 'ALL' : 'ROUTE',
    recipientTarget: isAll ? 'Todas las Rutas' : params.routes.join(', '),
    recipientName: isAll ? 'Todas las Rutas' : `Rutas: ${params.routes.join(', ')}`,
    routes: isAll ? ['ALL'] : params.routes,
    subject: params.subject.trim(),
    body: params.body.trim(),
    priority: params.priority,
    createdAt: new Date().toISOString(),
    read: false,
    replies: []
  };

  const updated = [newMsg, ...messages];
  saveStoredMessages(updated);
  return newMsg;
}

/**
 * Enviar mensaje personalizado directo a un estudiante / coder
 */
export function sendPersonalizedCoderMessage(params: {
  coder: {
    id?: string;
    name: string;
    email: string;
    cedula?: string;
    route?: string;
  };
  subject: string;
  body: string;
  priority: 'NORMAL' | 'URGENT' | 'INFO';
  sender?: string;
}): HseMessage {
  const messages = getStoredMessages();

  const newMsg: HseMessage = {
    id: `msg-coder-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
    sender: params.sender || 'Paola Admin (HSE Barranquilla)',
    senderRole: 'Coordinación HSE & Bienestar',
    recipientType: 'CODER',
    recipientTarget: params.coder.email.toLowerCase(),
    recipientName: params.coder.name,
    subject: params.subject.trim(),
    body: params.body.trim(),
    priority: params.priority,
    createdAt: new Date().toISOString(),
    read: false,
    replies: []
  };

  const updated = [newMsg, ...messages];
  saveStoredMessages(updated);
  return newMsg;
}

/**
 * Obtener todos los mensajes visibles para un coder específico
 */
export function getMessagesForCoder(coder: {
  email?: string;
  route?: string;
  cedula?: string;
  name?: string;
}): HseMessage[] {
  const allMessages = getStoredMessages();
  const cEmail = coder.email?.toLowerCase().trim() || '';
  const cRoute = coder.route?.trim() || '';
  const cCedula = coder.cedula?.trim() || '';
  const cName = coder.name?.toLowerCase().trim() || '';

  return allMessages.filter(msg => {
    if (msg.recipientType === 'ALL' || msg.recipientTarget === 'Todas las Rutas') {
      return true;
    }

    if (msg.recipientType === 'ROUTE') {
      if (msg.routes && (msg.routes.includes('ALL') || msg.routes.includes(cRoute))) {
        return true;
      }
      if (cRoute && msg.recipientTarget.toLowerCase().includes(cRoute.toLowerCase())) {
        return true;
      }
    }

    if (msg.recipientType === 'CODER') {
      const target = msg.recipientTarget.toLowerCase();
      if (cEmail && target === cEmail) return true;
      if (cCedula && target.includes(cCedula)) return true;
      if (cName && msg.recipientName?.toLowerCase().includes(cName)) return true;
    }

    return false;
  });
}

/**
 * Marcar mensaje como leído
 */
export function markMessageRead(id: string): void {
  const messages = getStoredMessages();
  const updated = messages.map(m => m.id === id ? { ...m, read: true } : m);
  saveStoredMessages(updated);
}

/**
 * Respuesta del Coder a un mensaje HSE
 */
export function addCoderReply(messageId: string, replyText: string, coderName: string): void {
  const messages = getStoredMessages();
  const updated = messages.map(m => {
    if (m.id === messageId) {
      const currentReplies = m.replies || [];
      return {
        ...m,
        replies: [
          ...currentReplies,
          {
            id: `reply-${Date.now()}`,
            sender: coderName,
            body: replyText.trim(),
            createdAt: new Date().toISOString()
          }
        ]
      };
    }
    return m;
  });
  saveStoredMessages(updated);
}
