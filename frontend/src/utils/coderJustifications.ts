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
          data_url: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400"><rect width="100%" height="100%" fill="%23f1f5f9"/><rect x="20" y="20" width="560" height="360" rx="12" fill="%23ffffff" stroke="%23cbd5e1" stroke-width="2"/><text x="300" y="190" font-family="sans-serif" font-size="18" font-weight="bold" fill="%23334155" text-anchor="middle">Soporte Evidencia Fotográfica</text><text x="300" y="225" font-family="sans-serif" font-size="13" fill="%2364748b" text-anchor="middle">Calamidad Doméstica - Barranquilla</text></svg>',
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
          data_url: 'data:application/pdf;base64,JVBERi0xLjQKJcOkw7zDtsOfCjEgMCBvYmoKPDwKL1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDIgMCBSCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCj4+CmVuZG9iagozIDAgb2JqCjw8Ci9UeXBlIC9QYWdlCi9QYXJlbnQgMiAwIFIKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KL0NvbnRlbnRzIDQgMCBSCj4+CmVuZG9iago0IDAgb2JqCjw8Ci9MZW5ndGggODAKPj4Kc3RyZWFtCkJUCi9GMSAxMiBUZgoxMDAgNzAwIFREClsoQ2VydGlmaWNhZG8gZGUgSW5jYXBhY2lkYWQgTWVkaWNhIC0gUml3aSBFZHVjYXRpb24pXSBUSgpFVAplbmRzdHJlYW0KZW5kb2JqCnhyZWYKMCA1CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAxNSAwMDAwMCBuIAowMDAwMDAwMDY4IDAwMDAwIG4gCjAwMDAwMDAxMjUgMDAwMDAgbiAKMDAwMDAwMDIxMyAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMSAwIFIKPj4Kc3RhcnR4cmVmCjM0MgolJUVPRg==',
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
          data_url: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400"><rect width="100%" height="100%" fill="%230f172a"/><rect x="20" y="20" width="560" height="360" rx="12" fill="%231e293b" stroke="%23334155" stroke-width="2"/><text x="300" y="190" font-family="sans-serif" font-size="18" font-weight="bold" fill="%2338bdf8" text-anchor="middle">Reporte de Incidencia de Energía</text><text x="300" y="225" font-family="sans-serif" font-size="13" fill="%2394a3b8" text-anchor="middle">Air-e - Circuito Barranquilla Norte</text></svg>',
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

  // Evaluador determinista de IA para radicados directos vía portal
  const attachments = item.attachments || [];
  const hasAttachments = attachments.length > 0;
  const desc = (item.description || '').toLowerCase();
  const novelty = (item.novelty_type || '').toLowerCase();
  const fullText = `${desc} ${novelty}`.toLowerCase();
  const isExtemporaneous = fullText.includes('vencid') || fullText.includes('extemporan') || fullText.includes('semana pasada');
  const epsKeywords = ["sura", "sanitas", "salud total", "nueva eps", "compensar", "famisanar", "coosalud", "mutual ser", "eps", "ips", "clinica", "clínica", "hospital", "cita", "ortodoncia", "odontol"];
  const mentionsEpsOrMedical = epsKeywords.some(w => fullText.includes(w)) || novelty.includes('incapacidad') || novelty.includes('cita');

  const isAutoApproved = hasAttachments && mentionsEpsOrMedical && !isExtemporaneous;
  const status: CoderJustificationStatus = isAutoApproved ? 'APPROVED' : 'REVISION_MANUAL';

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
    status,
    hse_notes: isAutoApproved 
      ? 'Resolución 100% automática del Sistema HSE: Justificación médica validada con soporte reglamentario EPS adjunto sin intervención humana.'
      : hasAttachments
        ? 'Reporte radicado vía portal con soporte. Requiere verificación manual de tolerancia HSE.'
        : 'Reporte radicado vía portal sin soporte adjunto. Requiere validación y criterio del Team Leader HSE.',
    hse_reviewer: isAutoApproved ? 'Sistema IA HSE' : undefined,
    hse_reviewed_at: isAutoApproved ? new Date().toISOString() : undefined,
    attachments,
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
  const attachmentsList = (j.attachments || []).map((att) => ({
    name: att.filename || 'Evidencia.pdf',
    url: att.data_url || att.preview_url || att.storage_path || '#',
    mime_type: att.mime_type,
    data_base64: att.data_base64,
  }));

  const hasAttachments = attachmentsList.length > 0;
  const desc = (j.description || '').toLowerCase();
  const novelty = (j.novelty_type || '').toLowerCase();
  const fullText = `${desc} ${novelty}`.toLowerCase();
  const isExtemporaneous = fullText.includes('vencid') || fullText.includes('extemporan') || fullText.includes('semana pasada');
  const epsKeywords = ["sura", "sanitas", "salud total", "nueva eps", "compensar", "famisanar", "coosalud", "mutual ser", "eps", "ips", "clinica", "clínica", "hospital", "cita", "ortodoncia", "odontol"];
  const mentionsEpsOrMedical = epsKeywords.some(w => fullText.includes(w)) || novelty.includes('incapacidad') || novelty.includes('cita');

  const isHumanReviewed = Boolean(j.hse_reviewer && j.hse_reviewer !== 'Sistema IA HSE');
  const qualifiesAuto = !isHumanReviewed && hasAttachments && mentionsEpsOrMedical && !isExtemporaneous;

  const isApproved = j.status === 'APPROVED' || qualifiesAuto;
  const isDisapproved = j.status === 'DISAPPROVED';
  const isCorrection = j.status === 'REQUEST_CORRECTION';
  const hasDecision = isApproved || isDisapproved || isCorrection;
  const isAutomatic = qualifiesAuto || (isApproved && (!j.hse_reviewer || j.hse_reviewer === 'Sistema IA HSE'));

  const mappedStatus = isApproved ? 'approved' : isDisapproved ? 'denied' : 'pending_review';
  const mappedCategory = isApproved ? 'POSIBLEMENTE_VALIDO' : isDisapproved ? 'POSIBLEMENTE_INVALIDO' : 'REVISION_MANUAL';

  const structuredBody = [
    `Radicado Oficial: ${j.radicado}`,
    `Coder: ${j.coder_name} (Documento: CC ${j.coder_cedula})`,
    `Ruta Académica: ${j.academic_route || 'Desarrollo de Software'}`,
    `Tipo de Novedad: ${j.novelty_label || NOVELTY_LABELS[j.novelty_type] || j.novelty_type}`,
    `Período de Ausencia: ${j.start_date} al ${j.end_date}`,
    `\nMotivo Declarado por el Coder:\n${j.description}`,
    j.coder_correction_reply ? `\n\nRespuesta de Subsanación del Coder:\n${j.coder_correction_reply}` : '',
  ].filter(Boolean).join('\n');

  const aiNote = isAutomatic
    ? 'Resolución 100% automática del Sistema HSE: Justificación médica validada con soporte reglamentario EPS adjunto sin intervención humana.'
    : (j.hse_notes || 'Radicado directo vía Portal del Coder. Documentación de soporte y declaración juramentada adjuntas.');

  return {
    id: j.id || j.radicado,
    studentId: j.coder_id || `coder-${j.coder_cedula}`,
    route: j.academic_route || 'Desarrollo de Software',
    status: mappedStatus,
    category: mappedCategory,
    recommendation: mappedCategory,
    noveltyType: j.novelty_type,
    noveltyLabel: j.novelty_label || NOVELTY_LABELS[j.novelty_type] || j.novelty_type,
    hasAttachment: attachmentsList.length > 0,
    attachmentsCount: attachmentsList.length,
    hasHumanIntervention: hasDecision && !isAutomatic,
    isAutomatic,
    aiReason: aiNote,
    hseDecision: hasDecision ? (isApproved ? 'APPROVED' : j.status) : null,
    hseNotes: j.hse_notes || null,
    hseReviewedAt: j.hse_reviewed_at || (isAutomatic ? j.submitted_at : null),
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
      source: isAutomatic ? 'ai' : hasDecision ? 'human' : 'ai',
      confidence: isAutomatic ? 0.95 : 0.85,
      reasoning: aiNote,
      modifiedBy: isAutomatic ? 'Sistema IA HSE' : j.hse_reviewer,
      modifiedAt: j.hse_reviewed_at || (isAutomatic ? j.submitted_at : undefined),
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
        let changed = false;
        const normalized = parsed.map((j: CoderJustification) => {
          const hasAttachments = (j.attachments || []).length > 0;
          const desc = (j.description || '').toLowerCase();
          const novelty = (j.novelty_type || '').toLowerCase();
          const fullText = `${desc} ${novelty}`.toLowerCase();
          const isExtemporaneous = fullText.includes('vencid') || fullText.includes('extemporan') || fullText.includes('semana pasada');
          const epsKeywords = ["sura", "sanitas", "salud total", "nueva eps", "compensar", "famisanar", "coosalud", "mutual ser", "eps", "ips", "clinica", "clínica", "hospital", "cita", "ortodoncia", "odontol"];
          const mentionsEpsOrMedical = epsKeywords.some(w => fullText.includes(w)) || novelty.includes('incapacidad') || novelty.includes('cita');

          const isHumanReviewed = Boolean(j.hse_reviewer && j.hse_reviewer !== 'Sistema IA HSE');
          if (!isHumanReviewed && j.status === 'REVISION_MANUAL' && hasAttachments && mentionsEpsOrMedical && !isExtemporaneous) {
            changed = true;
            return {
              ...j,
              status: 'APPROVED' as CoderJustificationStatus,
              hse_reviewer: 'Sistema IA HSE',
              hse_reviewed_at: j.submitted_at || new Date().toISOString(),
              hse_notes: 'Resolución 100% automática del Sistema HSE: Justificación médica validada con soporte reglamentario EPS adjunto sin intervención humana.',
            };
          }
          return j;
        });

        if (changed) {
          try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
          } catch (e) {
            // ignore
          }
        }
        return normalized;
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
