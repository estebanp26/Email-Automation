import type { CoderJustification, CoderAttachment } from '../types';

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
    return updatedTarget;
  } catch (e) {
    console.warn('Error actualizando con subsanación:', e);
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
