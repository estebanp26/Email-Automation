import { z } from 'zod';

export const NOVELTY_TYPES = [
  {
    id: 'incapacidad_medica',
    label: 'Incapacidad Médica',
    hint: 'Afecciones de salud, hospitalizaciones o consultas médicas prioritarias.',
    alert: 'Requiere soporte emitido por EPS o entidad de salud oficial donde consten los días exactos de incapacidad y firma/registro del profesional médico.',
  },
  {
    id: 'calamidad_domestica',
    label: 'Calamidad Doméstica',
    hint: 'Situaciones graves e imprevistas que afecten el núcleo familiar o vivienda.',
    alert: 'Aplica para sucesos graves familiares o de fuerza mayor comprobables. Detalla la relación de parentesco o la eventualidad en la descripción.',
  },
  {
    id: 'tramite_legal',
    label: 'Trámite Legal / Judicial',
    hint: 'Diligencias judiciales, notariales, cédula o citaciones de entes públicos.',
    alert: 'Se debe adjuntar la citación oficial, constancia de comparecencia o radicado con fecha y hora correspondiente al horario formativo.',
  },
  {
    id: 'falla_tecnica',
    label: 'Falla Técnica / Conectividad',
    hint: 'Interrupción del fluido eléctrico, caída masiva de internet o daño en equipo.',
    alert: 'Acompaña con capturas de pantalla con fecha/hora, número de reporte ante el operador (ISP) o comunicado de la empresa prestadora de servicios.',
  },
  {
    id: 'permiso_academico_otro',
    label: 'Permiso Académico / Otro',
    hint: 'Grados, sustentaciones universitarias u otros eventos justificados.',
    alert: 'Los permisos académicos o de fuerza mayor deben presentarse idealmente con antelación o con constancia formal de la institución educativa.',
  },
] as const;

export type NoveltyTypeId = (typeof NOVELTY_TYPES)[number]['id'];

export const excuseFormSchema = z
  .object({
    novelty_type: z.enum([
      'incapacidad_medica',
      'calamidad_domestica',
      'tramite_legal',
      'falla_tecnica',
      'permiso_academico_otro',
    ], {
      error: 'Debes seleccionar un tipo de novedad válido.',
    }),
    start_date: z
      .string()
      .min(1, 'La fecha de inicio es obligatoria.')
      .refine((val) => !isNaN(Date.parse(val)), {
        message: 'Fecha de inicio no válida.',
      }),
    end_date: z
      .string()
      .min(1, 'La fecha de finalización es obligatoria.')
      .refine((val) => !isNaN(Date.parse(val)), {
        message: 'Fecha de finalización no válida.',
      }),
    description: z
      .string()
      .trim()
      .min(30, 'La descripción debe tener al menos 30 caracteres para brindar suficiente contexto.')
      .max(1500, 'La descripción no puede exceder los 1500 caracteres.'),
    truth_declaration: z
      .boolean()
      .refine((val) => val === true, {
        message: 'Debes aceptar la declaración de veracidad bajo juramento para continuar.',
      }),
  })
  .refine(
    (data) => {
      if (!data.start_date || !data.end_date) return true;
      const start = new Date(data.start_date).getTime();
      const end = new Date(data.end_date).getTime();
      return end >= start;
    },
    {
      message: 'La fecha de fin no puede ser anterior a la fecha de inicio.',
      path: ['end_date'],
    }
  );

export type ExcuseFormData = z.infer<typeof excuseFormSchema>;

