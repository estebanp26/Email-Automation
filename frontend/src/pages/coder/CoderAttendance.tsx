import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  CheckCircle2, 
  Clock, 
  ShieldCheck, 
  XCircle, 
  Calendar, 
  BookOpen, 
  AlertTriangle,
  FilePlus,
  ArrowRight,
  ShieldAlert
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getCoderSession } from '../../utils/coderSession';
import { 
  generateInitialRecords, 
  type DailyAttendanceRecord, 
  type AttendanceRecordType 
} from '../../components/students/CoderAttendanceHistory';
import { CoderProfileMenu } from '../../components/coder/CoderProfileMenu';

export default function CoderAttendance() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const session = useMemo(() => {
    if (user && user.role === 'CODER') {
      return {
        id: user.id || 'coder-100',
        name: user.name,
        cedula: user.cedula || '1000000126',
        email: user.email,
        route: user.route || 'Desarrollo de Software',
      };
    }
    return getCoderSession();
  }, [user]);

  const [activeFilter, setActiveFilter] = useState<'ALL' | AttendanceRecordType>('ALL');

  // Cargar registros vinculados al coder (si HSE modificó algo en su panel, se refleja aquí)
  const storageKey = `hse_coder_records_${session.id || session.cedula}`;
  const [records, setRecords] = useState<DailyAttendanceRecord[]>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {}
    return generateInitialRecords({
      id: session.id || 'coder-100',
      cedula: session.cedula || '1000000126',
      name: session.name,
      email: session.email,
      route: session.route,
    });
  });

  // Sincronización si cambian en otra pestaña o en HSE
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === storageKey && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue);
          if (Array.isArray(parsed)) setRecords(parsed);
        } catch (err) {}
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, [storageKey]);

  // Cálculo de estadísticas coherentes y rigurosas:
  // Si hay retrasos o faltas, la asistencia nunca es 100%
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
    const weightedPoints = (present * 1.0) + (late * 0.75) + (justified * 0.40);
    let attendancePct = total > 0 ? Math.round((weightedPoints / total) * 100) : 100;

    if ((late > 0 || justified > 0 || unjustified > 0) && attendancePct >= 100) {
      attendancePct = 99;
    }

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

  const initials = session.name
    ? session.name
        .split(' ')
        .map((n) => n[0])
        .slice(0, 2)
        .join('')
    : 'CO';

  // 4 Cuadros Dinámicos (KPI Cards) idénticos a la vista HSE
  const dynamicKpiCards = [
    {
      label: 'Asistencia',
      value: `${stats.present} días`,
      rate: `${stats.total > 0 ? Math.round((stats.present / stats.total) * 100) : 0}%`,
      subtitle: 'jornadas a tiempo y completas',
      icon: CheckCircle2,
      color: 'text-[#20B486]',
      bg: 'bg-[#20B486]/10',
      badge: 'Normal',
      badgeBg: 'bg-[#20B486]/15 text-[#20B486]',
    },
    {
      label: 'Retraso',
      value: `${stats.late} sesiones`,
      rate: `${stats.total > 0 ? Math.round((stats.late / stats.total) * 100) : 0}%`,
      subtitle: 'ingresos con tardanza penalizada',
      icon: Clock,
      color: 'text-[#F5B83D]',
      bg: 'bg-[#F5B83D]/10',
      badge: 'Tardanza',
      badgeBg: 'bg-[#F5B83D]/15 text-[#B87A00]',
    },
    {
      label: 'Faltas Justificadas',
      value: `${stats.justified} días`,
      rate: `${stats.total > 0 ? Math.round((stats.justified / stats.total) * 100) : 0}%`,
      subtitle: 'con soporte médico o legal aprobado',
      icon: ShieldCheck,
      color: 'text-[#5B3FF5]',
      bg: 'bg-[#5B3FF5]/10',
      badge: 'Excusa Válida',
      badgeBg: 'bg-[#5B3FF5]/15 text-[#5B3FF5]',
    },
    {
      label: 'Faltas Injustificadas',
      value: `${stats.unjustified} días`,
      rate: `${stats.total > 0 ? Math.round((stats.unjustified / stats.total) * 100) : 0}%`,
      subtitle: 'sin justificación radicada ante HSE',
      icon: AlertTriangle,
      color: 'text-[#FF5C67]',
      bg: 'bg-[#FF5C67]/10',
      badge: 'Alerta HSE',
      badgeBg: 'bg-[#FF5C67]/15 text-[#FF5C67]',
    },
  ];

  return (
    <div className="space-y-6 pb-12 font-sans">
      
      {/* 1. TOP HEADER DEL PORTAL CODER */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-[#111827] flex items-center gap-2">
            <Calendar className="text-[#5B3FF5]" size={24} />
            Mi Asistencia Institucional
          </h1>
          <p className="text-xs sm:text-sm text-[#7C8499] mt-0.5">
            Registro biométrico oficial, seguimiento de presencialidad y estado ante el equipo HSE.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto">
          <div className="flex items-center gap-2 text-xs bg-white px-3.5 py-1.5 rounded-full border border-[#E2E8F0] text-[#7C8499] font-medium shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-[#20B486]" />
            <span className="hidden sm:inline">Sede RIWI Barranquilla · Presencial</span>
            <span className="sm:hidden">RIWI Barranquilla</span>
          </div>
          <CoderProfileMenu />
        </div>
      </div>

      {/* 2. CARD DE IDENTIDAD DEL ESTUDIANTE */}
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
                {session.name}
              </h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-600 border border-emerald-200">
                Coder Activo
              </span>
            </div>
            
            <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm text-[#7C8499]">
              {session.cedula && (
                <span className="font-mono bg-gray-100 text-[#111827] font-semibold px-2 py-0.5 rounded">
                  CC: {session.cedula}
                </span>
              )}
              <span>{session.email}</span>
              <span className="hidden sm:inline text-gray-300">•</span>
              <span className="flex items-center gap-1.5 font-medium text-[#5B3FF5]">
                <BookOpen size={14} />
                {session.route}
              </span>
            </div>
          </div>
        </div>

        {/* Cumplimiento Global y Acceso a Radicar Justificación */}
        <div className="flex items-center gap-6 w-full md:w-auto justify-between md:justify-end pt-4 md:pt-0 border-t md:border-t-0 border-[#E2E8F0]">
          {stats.unjustified > 0 && (
            <button
              onClick={() => navigate('/coder/new-excuse')}
              className="flex items-center gap-2 bg-[#5B3FF5] hover:bg-[#4a32cc] text-white px-4 py-2 rounded-xl text-xs font-bold shadow-md shadow-[#5B3FF5]/20 transition-all cursor-pointer shrink-0"
            >
              <FilePlus size={15} />
              <span>Radicar Justificación</span>
            </button>
          )}

          <div className="text-right shrink-0">
            <span className="text-[11px] text-[#7C8499] uppercase font-bold tracking-wider block">
              Cumplimiento Global
            </span>
            <span className={`text-2xl font-black ${
              stats.attendancePct >= 90 ? 'text-[#20B486]' :
              stats.attendancePct >= 75 ? 'text-[#F5B83D]' : 'text-[#FF5C67]'
            }`}>
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

      {/* AVISO INFORMATIVO DE RADICACIÓN O JUSTIFICACIONES PENDIENTES */}
      {stats.unjustified > 0 && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-amber-900">
          <div className="flex items-center gap-3">
            <ShieldAlert size={20} className="text-amber-600 shrink-0" />
            <div>
              <p className="font-bold">Tienes {stats.unjustified} {stats.unjustified === 1 ? 'inasistencia sin justificar' : 'inasistencias sin justificar'}.</p>
              <p className="text-amber-700">Recuerda que dispones de hasta 3 días hábiles para radicar soporte médico EPS o calamidad demostrable.</p>
            </div>
          </div>
          <button
            onClick={() => navigate('/coder/new-excuse')}
            className="flex items-center gap-1.5 font-bold text-[#5B3FF5] hover:underline self-end sm:self-auto cursor-pointer"
          >
            <span>Radicar ahora</span>
            <ArrowRight size={14} />
          </button>
        </div>
      )}

      {/* 4. SECCIÓN PRINCIPAL: LISTA DETALLADA POR DÍA (SOLO LECTURA, SIN MODIFICAR) */}
      <div className="bg-white rounded-[24px] border border-[#E2E8F0] shadow-sm overflow-hidden flex flex-col">
        
        {/* Encabezado y Filtros de la Lista */}
        <div className="p-5 sm:p-6 border-b border-[#E2E8F0] bg-gray-50/40 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-[#111827] flex items-center gap-2">
              <Calendar size={18} className="text-[#5B3FF5]" />
              Mi Historial Diario de Presencialidad
            </h3>
            <p className="text-xs text-[#7C8499] mt-0.5">
              Auditoría sincronizada con los lectores biométricos y la coordinación de Bienestar HSE.
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

        {/* Lista de Registros Diarios (Vista Coder: Solo Lectura, no modificable) */}
        <div className="divide-y divide-[#E2E8F0] max-h-[600px] overflow-y-auto custom-scrollbar">
          {filteredRecords.length === 0 ? (
            <div className="text-center py-12 text-[#7C8499]">
              <p className="text-sm">No existen registros en esta categoría de filtro.</p>
            </div>
          ) : (
            filteredRecords.map((item) => {
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

                  {/* Horario de Ingreso (Solo lectura) */}
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
