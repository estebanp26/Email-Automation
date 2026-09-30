import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, 
  CheckCircle2, 
  Clock, 
  ShieldCheck, 
  XCircle, 
  Calendar, 
  BookOpen, 
  AlertTriangle
} from 'lucide-react';
import type { Student } from '../../types';

interface CoderAttendanceHistoryProps {
  coder: Student & { status?: string };
  onBack: () => void;
}

export type AttendanceRecordType = 'PRESENT' | 'LATE' | 'JUSTIFIED_ABSENCE' | 'UNJUSTIFIED_ABSENCE';

export interface DailyAttendanceRecord {
  id: string;
  dateStr: string;
  dayName: string;
  formattedDate: string;
  type: AttendanceRecordType;
  arrivalTime?: string | undefined;
  reason?: string | undefined;
  referenceDoc?: string | undefined;
}

/**
 * Genera un historial diario determinista y consistente basado en los datos del Coder.
 */
function generateAttendanceRecords(coder: Student): DailyAttendanceRecord[] {
  const attendance = coder.attendance || {
    present: 36,
    late: 2,
    justifiedAbsence: 2,
    unjustifiedAbsence: 1,
  };

  const justifiedCount = Math.max(0, attendance.justifiedAbsence ?? 1);
  const lateCount = Math.max(0, attendance.late ?? 1);
  const unjustifiedCount = Math.max(0, attendance.unjustifiedAbsence ?? 0);
  const presentCount = Math.max(10, attendance.present ?? 35);

  const totalDays = justifiedCount + lateCount + unjustifiedCount + presentCount;
  
  // Lista de tipos a asignar
  const typesQueue: AttendanceRecordType[] = [];
  for (let i = 0; i < justifiedCount; i++) typesQueue.push('JUSTIFIED_ABSENCE');
  for (let i = 0; i < lateCount; i++) typesQueue.push('LATE');
  for (let i = 0; i < unjustifiedCount; i++) typesQueue.push('UNJUSTIFIED_ABSENCE');
  for (let i = 0; i < presentCount; i++) typesQueue.push('PRESENT');

  // Mezclar determinísticamente según el id o cédula del coder
  const seedStr = coder.id + (coder.cedula || '100');
  let seed = 0;
  for (let i = 0; i < seedStr.length; i++) {
    seed = (seed * 31 + seedStr.charCodeAt(i)) & 0xffffffff;
  }

  const seededRandom = () => {
    seed = (seed * 1664525 + 1013904223) & 0xffffffff;
    return (seed >>> 0) / 4294967296;
  };

  // Fisher-Yates shuffle con seed
  for (let i = typesQueue.length - 1; i > 0; i--) {
    const j = Math.floor(seededRandom() * (i + 1));
    [typesQueue[i], typesQueue[j]] = [typesQueue[j], typesQueue[i]];
  }

  // Generar días laborables (Lunes a Viernes) hacia atrás desde el 30 de Septiembre 2026
  const records: DailyAttendanceRecord[] = [];
  const currentDate = new Date(2026, 8, 30); // 30 Septiembre 2026

  const justifiedReasons = [
    'Incapacidad médica EPS expedida por médico general (Reposo 48h)',
    'Cita médica prioritaria especialista con soporte EPS validado',
    'Calamidad doméstica de primer grado notificada oportunamente al Team Leader',
    'Incapacidad por cuadro respiratorio agudo certificada por EPS Sura',
  ];

  const unjustifiedReasons = [
    'Inasistencia sin notificación previa ni radicación de soporte en plazo',
    'Ausencia en sesión práctica sin justificación aportada ante Team Leader',
    'Plazo reglamentario de 48h vencido sin entrega de documentos probatorios',
  ];

  const lateReasons = [
    'Retraso de 22 min - Trancón vehicular por contingencia en Vía 40',
    'Retraso de 18 min - Demora técnica en servicio de transporte masivo',
    'Retraso de 25 min - Falla mecánica de transporte reportada a Team Leader',
  ];

  let dayOffset = 0;
  let assignedIndex = 0;

  const dayNames = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
  const monthNames = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  while (records.length < totalDays && dayOffset < 120) {
    const d = new Date(currentDate);
    d.setDate(currentDate.getDate() - dayOffset);
    dayOffset++;

    // Omitir fines de semana
    const dayOfWeek = d.getDay();
    if (dayOfWeek === 0 || dayOfWeek === 6) {
      continue;
    }

    const type = typesQueue[assignedIndex] || 'PRESENT';
    assignedIndex++;

    const dayName = dayNames[dayOfWeek];
    const formattedDate = `${d.getDate()} de ${monthNames[d.getMonth()]}, ${d.getFullYear()}`;
    const dateStr = d.toISOString().split('T')[0];

    let reason = 'Jornada presencial completa · Registro biométrico verificado';
    let arrivalTime: string | undefined = '07:55 AM';
    let referenceDoc: string | undefined = undefined;

    if (type === 'JUSTIFIED_ABSENCE') {
      const rIndex = Math.floor(seededRandom() * justifiedReasons.length);
      reason = justifiedReasons[rIndex];
      const radNum = Math.floor(10000 + seededRandom() * 90000);
      referenceDoc = `RAD-HSE-2026-${radNum}`;
      arrivalTime = undefined;
    } else if (type === 'UNJUSTIFIED_ABSENCE') {
      const rIndex = Math.floor(seededRandom() * unjustifiedReasons.length);
      reason = unjustifiedReasons[rIndex];
      arrivalTime = undefined;
    } else if (type === 'LATE') {
      const rIndex = Math.floor(seededRandom() * lateReasons.length);
      reason = lateReasons[rIndex];
      const minute = Math.floor(12 + seededRandom() * 25);
      arrivalTime = `08:${minute < 10 ? '0' + minute : minute} AM`;
    } else {
      const min = Math.floor(50 + seededRandom() * 9);
      arrivalTime = `07:${min} AM`;
    }

    records.push({
      id: `att-${coder.id}-${dateStr}`,
      dateStr,
      dayName,
      formattedDate,
      type,
      arrivalTime,
      reason,
      referenceDoc,
    });
  }

  return records;
}

export function CoderAttendanceHistory({ coder, onBack }: CoderAttendanceHistoryProps) {
  const [activeFilter, setActiveFilter] = useState<'ALL' | AttendanceRecordType>('ALL');

  const records = useMemo(() => generateAttendanceRecords(coder), [coder]);

  // Contadores dinámicos calculados directamente de los registros generados
  const stats = useMemo(() => {
    let present = 0;
    let late = 0;
    let justified = 0;
    let unjustified = 0;

    records.forEach((r) => {
      if (r.type === 'PRESENT') present++;
      else if (r.type === 'LATE') late++;
      else if (r.type === 'JUSTIFIED_ABSENCE') justified++;
      else if (r.type === 'UNJUSTIFIED_ABSENCE') unjustified++;
    });

    const total = records.length;
    const effectivePresent = present + late;
    const attendancePct = total > 0 ? Math.round((effectivePresent / total) * 100) : 100;

    return {
      present,
      late,
      justified,
      unjustified,
      total,
      attendancePct,
    };
  }, [records]);

  const filteredRecords = useMemo(() => {
    if (activeFilter === 'ALL') return records;
    return records.filter((r) => r.type === activeFilter);
  }, [records, activeFilter]);

  const initials = coder.name
    ? coder.name
        .split(' ')
        .map((n) => n[0])
        .slice(0, 2)
        .join('')
    : 'CO';

  // 4 Cuadros Dinámicos (KPI Cards) con el diseño estandarizado
  const dynamicKpiCards = [
    {
      label: 'Asistencia',
      value: `${stats.present} días`,
      rate: `${stats.attendancePct}%`,
      subtitle: 'jornadas presenciales cumplidas',
      icon: CheckCircle2,
      color: 'text-[#20B486]',
      bg: 'bg-[#20B486]/10',
      border: 'border-[#20B486]/30',
      badge: 'Normal',
      badgeBg: 'bg-[#20B486]/15 text-[#20B486]',
    },
    {
      label: 'Retraso',
      value: `${stats.late} sesiones`,
      rate: `${Math.round((stats.late / stats.total) * 100)}%`,
      subtitle: 'ingresos posteriores a la hora límite',
      icon: Clock,
      color: 'text-[#F5B83D]',
      bg: 'bg-[#F5B83D]/10',
      border: 'border-[#F5B83D]/30',
      badge: 'Tardanza',
      badgeBg: 'bg-[#F5B83D]/15 text-[#B87A00]',
    },
    {
      label: 'Faltas Justificadas',
      value: `${stats.justified} días`,
      rate: `${Math.round((stats.justified / stats.total) * 100)}%`,
      subtitle: 'con soporte médico o legal aprobado',
      icon: ShieldCheck,
      color: 'text-[#5B3FF5]',
      bg: 'bg-[#5B3FF5]/10',
      border: 'border-[#5B3FF5]/30',
      badge: 'Excusa Válida',
      badgeBg: 'bg-[#5B3FF5]/15 text-[#5B3FF5]',
    },
    {
      label: 'Faltas Injustificadas',
      value: `${stats.unjustified} días`,
      rate: `${Math.round((stats.unjustified / stats.total) * 100)}%`,
      subtitle: 'sin justificación radicada ante TL',
      icon: AlertTriangle,
      color: 'text-[#FF5C67]',
      bg: 'bg-[#FF5C67]/10',
      border: 'border-[#FF5C67]/30',
      badge: 'Alerta HSE',
      badgeBg: 'bg-[#FF5C67]/15 text-[#FF5C67]',
    },
  ];

  return (
    <div className="space-y-6">
      
      {/* 1. BARRA SUPERIOR CON BOTÓN DE REGRESAR */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-2.5 text-sm font-bold text-[#5B3FF5] hover:text-[#4A32D6] bg-white border border-[#E2E8F0] hover:border-[#5B3FF5]/40 px-4 py-2.5 rounded-2xl shadow-xs transition-all cursor-pointer group"
        >
          <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
          <span>Volver al Directorio de Coders</span>
        </button>

        <span className="text-xs text-[#7C8499] font-medium bg-gray-100 px-3 py-1.5 rounded-full">
          Portal HSE · Gestión de Estudiantes
        </span>
      </div>

      {/* 2. CARD DE IDENTIDAD DEL CODER */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-[24px] border border-[#E2E8F0] p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6"
      >
        <div className="flex items-center gap-5 min-w-0">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#5B3FF5] to-[#7B61FF] text-white flex items-center justify-center font-bold text-xl shadow-lg shadow-[#5B3FF5]/25 shrink-0">
            {initials}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <h2 className="text-xl sm:text-2xl font-bold text-[#111827] truncate">
                {coder.name}
              </h2>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                coder.status === 'Inactivo' ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'
              }`}>
                {coder.status || 'Activo'}
              </span>
            </div>
            
            <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm text-[#7C8499]">
              {coder.cedula && (
                <span className="font-mono bg-gray-100 text-[#111827] font-semibold px-2 py-0.5 rounded">
                  CC: {coder.cedula}
                </span>
              )}
              <span>{coder.email}</span>
              <span className="hidden sm:inline text-gray-300">•</span>
              <span className="flex items-center gap-1.5 font-medium text-[#5B3FF5]">
                <BookOpen size={14} />
                {coder.route || 'Ruta de Entrenamiento'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 w-full md:w-auto justify-between md:justify-end pt-4 md:pt-0 border-t md:border-t-0 border-[#E2E8F0]">
          <div className="text-right">
            <span className="text-[11px] text-[#7C8499] uppercase font-bold tracking-wider block">
              Cumplimiento Global
            </span>
            <span className="text-2xl font-black text-[#20B486]">
              {stats.attendancePct}%
            </span>
          </div>
        </div>
      </motion.div>

      {/* 3. CUADROS DINÁMICOS: Asistencia, Retraso, Faltas Justificadas, Faltas Injustificadas */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {dynamicKpiCards.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <motion.div
              key={kpi.label}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="bg-white rounded-[22px] border border-[#E2E8F0] p-5 shadow-xs hover:shadow-md transition-all flex flex-col justify-between relative overflow-hidden"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className={`w-10 h-10 rounded-xl ${kpi.bg} ${kpi.color} flex items-center justify-center`}>
                    <Icon size={20} strokeWidth={2.5} />
                  </div>
                  <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${kpi.badgeBg}`}>
                    {kpi.badge}
                  </span>
                </div>
                <span className="text-xs font-bold text-[#7C8499] uppercase tracking-wider block">
                  {kpi.label}
                </span>
                <div className="flex items-baseline gap-2 mt-1">
                  <h3 className="text-2xl font-black text-[#111827]">{kpi.value}</h3>
                  <span className={`text-xs font-bold ${kpi.color}`}>{kpi.rate}</span>
                </div>
              </div>
              <p className="text-xs text-[#A3AAC2] mt-3 pt-3 border-t border-[#F1F3F9]">
                {kpi.subtitle}
              </p>
            </motion.div>
          );
        })}
      </div>

      {/* 4. SECCIÓN PRINCIPAL: LISTA DETALLADA POR DÍA */}
      <div className="bg-white rounded-[24px] border border-[#E2E8F0] shadow-sm overflow-hidden flex flex-col">
        
        {/* Encabezado y Filtros de la Lista */}
        <div className="p-5 sm:p-6 border-b border-[#E2E8F0] bg-gray-50/40 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-[#111827] flex items-center gap-2">
              <Calendar size={18} className="text-[#5B3FF5]" />
              Registro Diario de Asistencia y Novedades
            </h3>
            <p className="text-xs text-[#7C8499] mt-0.5">
              Auditoría cronológica de cada jornada con registro de retardos y motivos de inasistencia.
            </p>
          </div>

          {/* Filtros de estado */}
          <div className="flex flex-wrap items-center gap-1.5 bg-white p-1 rounded-xl border border-[#E2E8F0]">
            <button
              type="button"
              onClick={() => setActiveFilter('ALL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeFilter === 'ALL'
                  ? 'bg-[#5B3FF5] text-white shadow-xs'
                  : 'text-[#7C8499] hover:text-[#111827]'
              }`}
            >
              Todos ({records.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveFilter('PRESENT')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeFilter === 'PRESENT'
                  ? 'bg-[#20B486] text-white shadow-xs'
                  : 'text-[#7C8499] hover:text-[#20B486]'
              }`}
            >
              Asistencias ({stats.present})
            </button>
            <button
              type="button"
              onClick={() => setActiveFilter('LATE')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeFilter === 'LATE'
                  ? 'bg-[#F5B83D] text-white shadow-xs'
                  : 'text-[#7C8499] hover:text-[#B87A00]'
              }`}
            >
              Retrasos ({stats.late})
            </button>
            <button
              type="button"
              onClick={() => setActiveFilter('JUSTIFIED_ABSENCE')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeFilter === 'JUSTIFIED_ABSENCE'
                  ? 'bg-[#5B3FF5] text-white shadow-xs'
                  : 'text-[#7C8499] hover:text-[#5B3FF5]'
              }`}
            >
              F. Justificadas ({stats.justified})
            </button>
            <button
              type="button"
              onClick={() => setActiveFilter('UNJUSTIFIED_ABSENCE')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeFilter === 'UNJUSTIFIED_ABSENCE'
                  ? 'bg-[#FF5C67] text-white shadow-xs'
                  : 'text-[#7C8499] hover:text-[#FF5C67]'
              }`}
            >
              F. Injustificadas ({stats.unjustified})
            </button>
          </div>
        </div>

        {/* Lista de Registros */}
        <div className="divide-y divide-[#E2E8F0] max-h-[600px] overflow-y-auto custom-scrollbar">
          {filteredRecords.length === 0 ? (
            <div className="text-center py-12 text-[#7C8499]">
              <p className="text-sm">No existen registros en esta categoría de filtro.</p>
            </div>
          ) : (
            filteredRecords.map((item) => {
              // Configuración visual según el tipo de registro
              const isPresent = item.type === 'PRESENT';
              const isLate = item.type === 'LATE';
              const isJustified = item.type === 'JUSTIFIED_ABSENCE';
              const isUnjustified = item.type === 'UNJUSTIFIED_ABSENCE';

              return (
                <div
                  key={item.id}
                  className="p-4 sm:px-6 hover:bg-[#F8F9FE] transition-colors flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
                >
                  {/* Ícono de Estado + Día y Fecha */}
                  <div className="flex items-center gap-4 min-w-[240px]">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                      isPresent ? 'bg-[#20B486]/10 text-[#20B486]' :
                      isLate ? 'bg-[#F5B83D]/10 text-[#F5B83D]' :
                      isJustified ? 'bg-[#5B3FF5]/10 text-[#5B3FF5]' :
                      'bg-[#FF5C67]/10 text-[#FF5C67]'
                    }`}>
                      {isPresent && <CheckCircle2 size={20} strokeWidth={2.5} />}
                      {isLate && <Clock size={20} strokeWidth={2.5} />}
                      {isJustified && <ShieldCheck size={20} strokeWidth={2.5} />}
                      {isUnjustified && <XCircle size={20} strokeWidth={2.5} />}
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-[#111827]">
                          {item.dayName}
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          isPresent ? 'bg-[#20B486]/10 text-[#20B486]' :
                          isLate ? 'bg-[#F5B83D]/15 text-[#B87A00]' :
                          isJustified ? 'bg-[#5B3FF5]/10 text-[#5B3FF5]' :
                          'bg-[#FF5C67]/10 text-[#FF5C67]'
                        }`}>
                          {isPresent ? 'Asistió' :
                           isLate ? `Retraso (${item.arrivalTime})` :
                           isJustified ? 'Falta Justificada' :
                           'Falta Injustificada'}
                        </span>
                      </div>
                      <span className="text-xs text-[#7C8499]">
                        {item.formattedDate}
                      </span>
                    </div>
                  </div>

                  {/* Espacio Pequeño de Referencia / Motivo de Falta o Novedad */}
                  <div className="flex-1 w-full sm:w-auto sm:px-4">
                    <div className={`p-2.5 rounded-xl border text-xs flex items-start gap-2 ${
                      isJustified
                        ? 'bg-[#5B3FF5]/5 border-[#5B3FF5]/20 text-[#171B3A]'
                        : isUnjustified
                        ? 'bg-[#FF5C67]/5 border-[#FF5C67]/20 text-[#9E1B26]'
                        : isLate
                        ? 'bg-[#F5B83D]/10 border-[#F5B83D]/25 text-[#7A5000]'
                        : 'bg-gray-50 border-gray-100 text-[#7C8499]'
                    }`}>
                      <span className="font-bold shrink-0">
                        {isJustified ? 'Motivo Justificado:' :
                         isUnjustified ? 'Referencia Falta:' :
                         isLate ? 'Novedad de Llegada:' :
                         'Sesión:'}
                      </span>
                      <span className="truncate">
                        {item.reason}
                      </span>
                      {item.referenceDoc && (
                        <span className="ml-auto font-mono text-[10px] font-bold bg-[#5B3FF5]/10 text-[#5B3FF5] px-1.5 py-0.5 rounded shrink-0">
                          {item.referenceDoc}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Horario / Hora de Entrada */}
                  <div className="text-right text-xs shrink-0 self-end sm:self-center">
                    <span className="text-[#A3AAC2] block font-mono">
                      {item.arrivalTime ? `Ingreso: ${item.arrivalTime}` : 'Jornada ausente'}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

    </div>
  );
}

export default CoderAttendanceHistory;
