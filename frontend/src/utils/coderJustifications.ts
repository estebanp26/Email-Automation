import type { CoderJustification, CoderAttachment, Request, CoderJustificationStatus } from '../types';

const STORAGE_KEY = 'hse_coder_justifications';

/**
 * Mapeo de labels amigables para tipos de novedad
 */
export const NOVELTY_LABELS: Record<string, string> = {
  incapacidad_medica: 'Incapacidad Médica',
  calamidad_domestica: 'Calamidad Doméstica',
  tramite_legal: 'Trámite Legal / Judicial',
  falla_tecnica: 'Falla Técnica / Conectividad',
  permiso_academico_otro: 'Permiso Académico / Otro',
  inasistencia_medica: 'Incapacidad Médica',
  fuerza_mayor: 'Calamidad Doméstica / Fuerza Mayor',
};

/**
 * Datos semilla con cobertura completa de los 4 estados para pruebas inmediatas del Coder
 */
function getInitialSeedData(coderName: string, coderCedula: string, coderEmail: string, route: string): CoderJustification[] {
  return [
    {
      id: 'just-001',
      radicado: 'RAD-HSE-2026-849102',
      coder_cedula: coderCedula,
      coder_name: coderName,
      coder_email: coderEmail,
      academic_route: route,
      novelty_type: 'calamidad_domestica',
      novelty_label: 'Calamidad Doméstica',
      start_date: '2026-09-27',
      end_date: '2026-09-28',
      description: 'Inundación parcial en mi domicilio por fuertes lluvias en Barranquilla, lo que me impidió asistir a la sesión formativa en el horario matutino.',
      truth_declaration: true,
      status: 'REQUEST_CORRECTION',
      hse_notes: 'El certificado o soporte fotográfico adjunto no permite verificar la fecha ni la dirección de la novedad. Por favor adjunta un comprobante de servicio público o reporte de atención de emergencia barrial con fecha visible para convalidar la inasistencia.',
      hse_reviewer: 'Paola Admin (HSE Barranquilla)',
      hse_reviewed_at: '2026-09-29T14:30:00.000Z',
      attachments: [
        {
          file_id: 'att-101',
          filename: 'foto_evidencia_inicial.jpg',
          size_bytes: 1420500,
          mime_type: 'image/jpeg',
          legibility_status: 'warning',
          legibility_reason: 'Baja resolución. El texto y metadatos no son completamente legibles.',
        }
      ],
      submitted_at: '2026-09-28T09:15:00.000Z',
      updated_at: '2026-09-29T14:30:00.000Z',
    },
    {
      id: 'just-002',
      radicado: 'RAD-HSE-2026-712495',
      coder_cedula: coderCedula,
      coder_name: coderName,
      coder_email: coderEmail,
      academic_route: route,
      novelty_type: 'incapacidad_medica',
      novelty_label: 'Incapacidad Médica',
      start_date: '2026-09-20',
      end_date: '2026-09-22',
      description: 'Cuadro de gastroenteritis aguda con orden de reposo e incapacidad emitida por IPS Sura.',
      truth_declaration: true,
      status: 'APPROVED',
      hse_notes: 'Convalidada satisfactoriamente. Soporte con código de habilitación y registro médico verificado.',
      hse_reviewer: 'Paola Admin (HSE Barranquilla)',
      hse_reviewed_at: '2026-09-23T11:00:00.000Z',
      attachments: [
        {
          file_id: 'att-102',
          filename: 'incapacidad_eps_sura.pdf',
          size_bytes: 524288,
          mime_type: 'application/pdf',
          legibility_status: 'optimal',
          legibility_reason: 'Documento vectorial digital legible.',
        }
      ],
      submitted_at: '2026-09-22T16:00:00.000Z',
      updated_at: '2026-09-23T11:00:00.000Z',
    },
    {
      id: 'just-003',
      radicado: 'RAD-HSE-2026-591034',
      coder_cedula: coderCedula,
      coder_name: coderName,
      coder_email: coderEmail,
      academic_route: route,
      novelty_type: 'falla_tecnica',
      novelty_label: 'Falla Técnica / Conectividad',
      start_date: '2026-09-29',
      end_date: '2026-09-29',
      description: 'Corte masivo de energía eléctrica reportado por Air-e en el sector norte de Barranquilla durante 5 horas.',
      truth_declaration: true,
      status: 'REVISION_MANUAL',
      hse_notes: 'En revisión por el analista HSE. Verificando reporte de incidencia técnica.',
      attachments: [
        {
          file_id: 'att-103',
          filename: 'reporte_incidencia_aire.png',
          size_bytes: 840100,
          mime_type: 'image/png',
          legibility_status: 'standard',
          legibility_reason: 'Captura con resolución estándar.',
        }
      ],
      submitted_at: '2026-09-29T18:20:00.000Z',
    },
    {
      id: 'just-004',
      radicado: 'RAD-HSE-2026-402911',
      coder_cedula: coderCedula,
      coder_name: coderName,
      coder_email: coderEmail,
      academic_route: route,
      novelty_type: 'permiso_academico_otro',
      novelty_label: 'Permiso Académico / Otro',
      start_date: '2026-09-15',
      end_date: '2026-09-15',
      description: 'Asistencia a evento personal sin soporte oficial ni radicación oportuna.',
      truth_declaration: true,
      status: 'DISAPPROVED',
      hse_notes: 'No cumple con las causales de justificación contempladas en el reglamento de convivencia ni se aportó soporte oficial.',
      hse_reviewer: 'Paola Admin (HSE Barranquilla)',
      hse_reviewed_at: '2026-09-16T10:15:00.000Z',
      attachments: [],
      submitted_at: '2026-09-15T20:00:00.000Z',
      updated_at: '2026-09-16T10:15:00.000Z',
    }
  ];
}

/**
 * Obtener lista de justificaciones persistida o inicializada
 */
export function getCoderJustifications(coderCedula: string, coderName: string, coderEmail: string, route: string): CoderJustification[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed: CoderJustification[] = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch (e) {
    console.warn('Error leyendo justificaciones de localStorage:', e);
  }

  // Si no hay datos, inicializar con las semillas y persistir
  const initial = getInitialSeedData(coderName, coderCedula, coderEmail, route);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(initial));
  } catch (e) {
    console.warn('Error guardando semillas iniciales:', e);
  }
  return initial;
}

/**
 * Guardar una nueva justificación radicada desde el formulario Coder
 */
export function saveNewCoderJustification(item: Partial<CoderJustification>): CoderJustification {
  const current = getCoderJustifications(
    item.coder_cedula || '',
    item.coder_name || '',
    item.coder_email || '',
    item.academic_route || ''
  );

  const radicadoId = item.radicado || `RAD-HSE-2026-${Math.floor(100000 + Math.random() * 900000)}`;

  const newItem: CoderJustification = {
    id: `just-${Date.now()}`,
    radicado: radicadoId,
    coder_cedula: item.coder_cedula || '',
    coder_name: item.coder_name || '',
    coder_email: item.coder_email || '',
    academic_route: item.academic_route || 'Desarrollo de Software',
    novelty_type: item.novelty_type || 'incapacidad_medica',
    novelty_label: NOVELTY_LABELS[item.novelty_type || ''] || 'Novedad Justificada',
    start_date: item.start_date || new Date().toISOString().split('T')[0],
    end_date: item.end_date || new Date().toISOString().split('T')[0],
    description: item.description || '',
    truth_declaration: Boolean(item.truth_declaration),
    status: 'REVISION_MANUAL',
    attachments: item.attachments || [],
    submitted_at: new Date().toISOString(),
  };

  const updated = [newItem, ...current];
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('hse_justification_created', { detail: { justification: newItem } }));
    }
  } catch (e) {
    console.warn('Error guardando nueva justificación:', e);
  }

  return newItem;
}

/**
 * Responder y subsanar un caso con estado REQUEST_CORRECTION
 */
export function updateCoderJustificationWithCorrection(
  radicado: string,
  data: {
    newFiles: CoderAttachment[];
    coderReply?: string;
  }
): CoderJustification | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const list: CoderJustification[] = JSON.parse(raw);

    const index = list.findIndex(j => j.radicado === radicado);
    if (index === -1) return null;

    const target = list[index];
    const updatedTarget: CoderJustification = {
      ...target,
      status: 'REVISION_MANUAL',
      attachments: [...target.attachments, ...data.newFiles],
      coder_correction_reply: data.coderReply || 'Nueva evidencia adjuntada por el coder para subsanación.',
      updated_at: new Date().toISOString(),
    };

    list[index] = updatedTarget;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));

    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('hse_justifications_updated', { detail: { justification: updatedTarget } }));
    }

    return updatedTarget;
  } catch (e) {
    console.warn('Error actualizando con subsanación:', e);
    return null;
  }
}

/**
 * Convierte una Justificación del Coder al modelo canónico Request consumido por la TL (Requests.tsx y Dashboard)
 */
export function convertCoderJustificationToRequest(j: CoderJustification): Request {
  const isApproved = j.status === 'APPROVED';
  const isDisapproved = j.status === 'DISAPPROVED';
  const isCorrection = j.status === 'REQUEST_CORRECTION';
  const hasDecision = isApproved || isDisapproved || isCorrection;

  const mappedStatus = isApproved ? 'approved' : isDisapproved ? 'denied' : 'pending_review';
  const mappedCategory = isApproved ? 'POSIBLEMENTE_VALIDO' : isDisapproved ? 'POSIBLEMENTE_INVALIDO' : 'REVISION_MANUAL';

  const attachmentsList = (j.attachments || []).map((att) => ({
    name: att.filename || 'Evidencia.pdf',
    url: att.preview_url || att.storage_path || '#',
  }));

  const structuredBody = [
    `Radicado Oficial: ${j.radicado}`,
    `Coder: ${j.coder_name} (Documento: CC ${j.coder_cedula})`,
    `Ruta Académica: ${j.academic_route || 'Desarrollo de Software'}`,
    `Tipo de Novedad: ${j.novelty_label || NOVELTY_LABELS[j.novelty_type] || j.novelty_type}`,
    `Período de Ausencia: ${j.start_date} al ${j.end_date}`,
    `\nMotivo Declarado por el Coder:\n${j.description}`,
    j.coder_correction_reply ? `\n\nRespuesta de Subsanación del Coder:\n${j.coder_correction_reply}` : '',
  ].filter(Boolean).join('\n');

  return {
    id: j.id || j.radicado,
    studentId: j.coder_id || `coder-${j.coder_cedula}`,
    route: j.academic_route || 'Desarrollo de Software',
    status: mappedStatus,
    category: mappedCategory,
    recommendation: mappedCategory,
    hasHumanIntervention: hasDecision,
    hseDecision: hasDecision ? j.status : null,
    hseNotes: j.hse_notes || null,
    hseReviewedAt: j.hse_reviewed_at || null,
    isResponded: hasDecision,
    emailInfo: {
      senderName: j.coder_name || 'Coder Estudiante',
      senderEmail: j.coder_email || `${j.coder_cedula}@riwi.io`,
      subject: `[Radicado ${j.radicado}] ${j.novelty_label || NOVELTY_LABELS[j.novelty_type] || 'Justificación de Inasistencia'} - ${j.coder_name}`,
      body: structuredBody,
      date: j.submitted_at || new Date().toISOString(),
      attachments: attachmentsList,
    },
    decision: {
      source: hasDecision ? 'human' : 'ai',
      confidence: 0.95,
      reasoning: j.hse_notes || 'Radicado directo vía Portal del Coder. Documentación de soporte y declaración juramentada adjuntas.',
      modifiedBy: j.hse_reviewer,
      modifiedAt: j.hse_reviewed_at,
    },
  } as any;
}

/**
 * Obtiene todas las justificaciones de Coders persistidas en el cliente
 */
export function getAllCoderJustifications(): CoderJustification[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed;
      }
    }
  } catch (e) {
    console.warn('Error al leer justificaciones de Coder:', e);
  }
  return [];
}

/**
 * Obtiene todas las justificaciones de Coders adaptadas como Requests para la bandeja TL
 */
export function getAllCoderJustificationsAsRequests(): Request[] {
  const justifications = getAllCoderJustifications();
  return justifications.map(convertCoderJustificationToRequest);
}

/**
 * Actualiza el estado y observaciones de una justificación por parte de la Team Leader / HSE
 */
export function updateCoderJustificationStatus(
  idOrRadicado: string,
  newStatus: 'APPROVED' | 'DISAPPROVED' | 'REQUEST_CORRECTION' | 'REVISION_MANUAL',
  notes?: string,
  reviewerName?: string
): CoderJustification | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const list: CoderJustification[] = JSON.parse(raw);

    const index = list.findIndex(
      (j) => j.id === idOrRadicado || j.radicado === idOrRadicado
    );
    if (index === -1) return null;

    const target = list[index];
    const updatedTarget: CoderJustification = {
      ...target,
      status: newStatus as CoderJustificationStatus,
      hse_notes: notes !== undefined ? notes : target.hse_notes,
      hse_reviewer: reviewerName || target.hse_reviewer || 'Paola Admin (HSE)',
      hse_reviewed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    list[index] = updatedTarget;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));

    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('hse_justifications_updated', {
          detail: { justification: updatedTarget },
        })
      );
    }

    return updatedTarget;
  } catch (e) {
    console.warn('Error al actualizar estado de justificación de Coder:', e);
    return null;
  }
}

/**
 * Cálculo de estadísticas KPI para el panel Coder
 */
export function calculateCoderStats(justifications: CoderJustification[]) {
  const total = justifications.length;
  const approved = justifications.filter(j => j.status === 'APPROVED').length;
  const disapproved = justifications.filter(j => j.status === 'DISAPPROVED').length;
  const revision = justifications.filter(j => j.status === 'REVISION_MANUAL' || (j.status as any) === 'MANUAL_INTERACTION').length;
  const requestCorrection = justifications.filter(j => j.status === 'REQUEST_CORRECTION').length;

  const approvalRate = total > 0 ? Math.round((approved / total) * 100) : 0;

  return {
    total,
    approved,
    disapproved,
    revision,
    requestCorrection,
    approvalRate,
  };
}
