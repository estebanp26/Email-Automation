import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ArrowLeft, 
  CheckCircle2, 
  Clock, 
  ShieldCheck, 
  XCircle, 
  Calendar, 
  BookOpen, 
  AlertTriangle,
  Edit3,
  Mail,
  Send,
  X,
  MessageSquare
} from 'lucide-react';
import type { Student } from '../../types';
import { 
  sendPersonalizedCoderMessage
} from '../../services/hseMessages';

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
export function generateInitialRecords(coder: any): DailyAttendanceRecord[] {
  const attendance = coder.attendance || {
    present: 34,
    late: 3,
    justifiedAbsence: 2,
    unjustifiedAbsence: 1,
  };

  const justifiedCount = Math.max(0, attendance.justifiedAbsence ?? 2);
  const lateCount = Math.max(0, attendance.late ?? 3);
  const unjustifiedCount = Math.max(0, attendance.unjustifiedAbsence ?? 1);
  const presentCount = Math.max(10, attendance.present ?? 34);

  const totalDays = justifiedCount + lateCount + unjustifiedCount + presentCount;
  
  const typesQueue: AttendanceRecordType[] = [];
  for (let i = 0; i < justifiedCount; i++) typesQueue.push('JUSTIFIED_ABSENCE');
  for (let i = 0; i < lateCount; i++) typesQueue.push('LATE');
  for (let i = 0; i < unjustifiedCount; i++) typesQueue.push('UNJUSTIFIED_ABSENCE');
  for (let i = 0; i < presentCount; i++) typesQueue.push('PRESENT');

  const seedStr = coder.id + (coder.cedula || '100');
  let seed = 0;
  for (let i = 0; i < seedStr.length; i++) {
    seed = (seed * 31 + seedStr.charCodeAt(i)) & 0xffffffff;
  }

  const seededRandom = () => {
    seed = (seed * 1664525 + 1013904223) & 0xffffffff;
    return (seed >>> 0) / 4294967296;
  };

  for (let i = typesQueue.length - 1; i > 0; i--) {
    const j = Math.floor(seededRandom() * (i + 1));
    [typesQueue[i], typesQueue[j]] = [typesQueue[j], typesQueue[i]];
  }

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

    const dayOfWeek = d.getDay();
    if (dayOfWeek === 0 || dayOfWeek === 6) continue;

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

  // Registros en estado local con persistencia en localStorage por coder
  const storageKey = `hse_coder_records_${coder.id || coder.cedula}`;
  const [records, setRecords] = useState<DailyAttendanceRecord[]>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {}
    return generateInitialRecords(coder);
  });

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(records));
    } catch (e) {}
  }, [records, storageKey]);

  // Modal para Modificar Asistencia del Día
  const [editingRecord, setEditingRecord] = useState<DailyAttendanceRecord | null>(null);
  const [selectedType, setSelectedType] = useState<AttendanceRecordType>('PRESENT');
  const [editReason, setEditReason] = useState('');
  const [editArrivalTime, setEditArrivalTime] = useState('');

  // Modal para Enviar Mensaje Personalizado
  const [showMessageModal, setShowMessageModal] = useState(false);
  const [messageForm, setMessageForm] = useState({
    subject: '',
    body: '',
    priority: 'NORMAL' as 'NORMAL' | 'URGENT' | 'INFO'
  });
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Cálculo de estadísticas rigurosas y coherentes:
  // Un estudiante NO puede tener 100% si ha tenido retrasos o faltas.
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
    
    // Ponderación de presencialidad efectiva:
    // Presente a tiempo: 100%
    // Retraso: 75% de cumplimiento
    // Justificada: 40% (no cuenta como jornada presencial completa)
    // Injustificada: 0%
    const weightedPoints = (present * 1.0) + (late * 0.75) + (justified * 0.40);
    let attendancePct = total > 0 ? Math.round((weightedPoints / total) * 100) : 100;

    // Si ha tenido retrasos o faltas, la asistencia NO puede ser 100%
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

  const initials = coder.name
    ? coder.name
        .split(' ')
        .map((n) => n[0])
        .slice(0, 2)
        .join('')
    : 'CO';

  // 4 Cuadros Dinámicos (KPI Cards)
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
      subtitle: 'con soporte médico o legal',
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
      subtitle: 'sin justificación radicada',
      icon: AlertTriangle,
      color: 'text-[#FF5C67]',
      bg: 'bg-[#FF5C67]/10',
      badge: 'Alerta HSE',
      badgeBg: 'bg-[#FF5C67]/15 text-[#FF5C67]',
    },
  ];

  // Handler para abrir modal de modificación de asistencia
  const handleOpenEdit = (record: DailyAttendanceRecord) => {
    setEditingRecord(record);
    setSelectedType(record.type);
    setEditReason(record.reason || '');
    setEditArrivalTime(record.arrivalTime || (record.type === 'LATE' ? '08:20 AM' : '07:55 AM'));
  };

  // Handler para guardar cambio de asistencia
  const handleSaveAttendanceEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRecord) return;

    let finalArrivalTime = editArrivalTime;
    let finalReason = editReason.trim();
    let finalRef = editingRecord.referenceDoc;

    if (selectedType === 'PRESENT') {
      finalArrivalTime = finalArrivalTime || '07:55 AM';
      finalReason = finalReason || 'Jornada presencial completa · Asistencia registrada';
      finalRef = undefined;
    } else if (selectedType === 'LATE') {
      finalArrivalTime = finalArrivalTime || '08:22 AM';
      finalReason = finalReason || 'Ingreso posterior a hora límite · Retraso registrado';
      finalRef = undefined;
    } else if (selectedType === 'JUSTIFIED_ABSENCE') {
      finalArrivalTime = undefined as any;
      finalReason = finalReason || 'Incapacidad médica validada por Team Leader';
      finalRef = finalRef || `RAD-HSE-2026-${Math.floor(10000 + Math.random() * 90000)}`;
    } else if (selectedType === 'UNJUSTIFIED_ABSENCE') {
      finalArrivalTime = undefined as any;
      finalReason = finalReason || 'Inasistencia sin soporte documental radicado';
      finalRef = undefined;
    }

    setRecords(prev => prev.map(r => r.id === editingRecord.id ? {
      ...r,
      type: selectedType,
      arrivalTime: finalArrivalTime,
      reason: finalReason,
      referenceDoc: finalRef
    } : r));

    showToast(`Asistencia del ${editingRecord.dayName} modificada a ${
      selectedType === 'PRESENT' ? 'Asistencia' :
      selectedType === 'LATE' ? 'Retraso' :
      selectedType === 'JUSTIFIED_ABSENCE' ? 'Falta Justificada' : 'Falta Injustificada'
    }`);
    setEditingRecord(null);
  };

  // Handler para enviar mensaje personalizado al estudiante
  const handleSendPersonalMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!messageForm.subject.trim() || !messageForm.body.trim()) return;

    sendPersonalizedCoderMessage({
      coder: {
        id: coder.id,
        name: coder.name,
        email: coder.email,
        cedula: coder.cedula,
        route: coder.route
      },
      subject: messageForm.subject,
      body: messageForm.body,
      priority: messageForm.priority,
      sender: 'Paola Admin (HSE Barranquilla)'
    });

    showToast(`Mensaje enviado exitosamente a ${coder.name}`);
    setShowMessageModal(false);
    setMessageForm({ subject: '', body: '', priority: 'NORMAL' });
  };

  return (
    <div className="space-y-6 relative">
      
      {/* Toast Flotante */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-8 right-8 z-50 bg-[#11132C] text-white px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-3 border border-white/10 text-sm font-semibold"
          >
            <CheckCircle2 size={18} className="text-[#20B486]" />
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

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
          Portal HSE · Historial & Novedades
        </span>
      </div>

      {/* 2. CARD DE IDENTIDAD DEL CODER CON ACCIONES */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-[24px] border border-[#E2E8F0] p-6 shadow-sm flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6"
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

        {/* Acciones del Estudiante: Enviar Mensaje + Cumplimiento Global */}
        <div className="flex items-center gap-5 w-full lg:w-auto justify-between lg:justify-end pt-4 lg:pt-0 border-t lg:border-t-0 border-[#E2E8F0]">
          {/* Botón de Enviar Mensaje Personalizado */}
          <button
            type="button"
            onClick={() => setShowMessageModal(true)}
            className="flex items-center gap-2 bg-[#5B3FF5] hover:bg-[#4a32cc] text-white px-4 py-2.5 rounded-xl text-xs sm:text-sm font-bold shadow-md shadow-[#5B3FF5]/20 transition-all cursor-pointer"
          >
            <Mail size={16} />
            <span>Enviar Mensaje al Coder</span>
          </button>

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

      {/* 4. SECCIÓN PRINCIPAL: LISTA DETALLADA POR DÍA CON BOTÓN PARA MODIFICAR */}
      <div className="bg-white rounded-[24px] border border-[#E2E8F0] shadow-sm overflow-hidden flex flex-col">
        
        {/* Encabezado y Filtros de la Lista */}
        <div className="p-5 sm:p-6 border-b border-[#E2E8F0] bg-gray-50/40 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-[#111827] flex items-center gap-2">
              <Calendar size={18} className="text-[#5B3FF5]" />
              Registro Diario de Asistencia y Novedades
            </h3>
            <p className="text-xs text-[#7C8499] mt-0.5">
              Auditoría cronológica. Haz clic en el ícono de lápiz de cualquier día para modificar el estado.
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

        {/* Lista de Registros Diarios */}
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
                  className="p-4 sm:px-6 hover:bg-[#F8F9FE] transition-colors flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 group"
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

                  {/* Horario + Botón Pequeño de Modificar Asistencia */}
                  <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                    <div className="text-right text-xs">
                      <span className="text-[#A3AAC2] block font-mono">
                        {item.arrivalTime ? `Ingreso: ${item.arrivalTime}` : 'Jornada ausente'}
                      </span>
                    </div>

                    {/* Botón con ícono pequeño para modificar la asistencia de dicho día */}
                    <button
                      type="button"
                      onClick={() => handleOpenEdit(item)}
                      className="p-2 text-[#7C8499] hover:text-[#5B3FF5] hover:bg-white rounded-xl border border-transparent hover:border-[#E2E8F0] shadow-2xs transition-all cursor-pointer group-hover:border-gray-200"
                      title={`Modificar asistencia del ${item.dayName} (${item.formattedDate})`}
                    >
                      <Edit3 size={15} />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* MODAL PARA MODIFICAR LA ASISTENCIA DE DICHO DÍA (4 TARJETAS CON OPCIONES) */}
      <AnimatePresence>
        {editingRecord && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl border border-gray-100"
            >
              <div className="flex justify-between items-start mb-5">
                <div>
                  <h3 className="text-lg font-bold text-[#11132C]">
                    Modificar Asistencia
                  </h3>
                  <p className="text-xs text-[#7C8499] mt-0.5">
                    {editingRecord.dayName}, {editingRecord.formattedDate} · {coder.name}
                  </p>
                </div>
                <button
                  onClick={() => setEditingRecord(null)}
                  className="p-1 text-gray-400 hover:text-gray-700 transition-colors cursor-pointer"
                >
                  <X size={20} />
                </button>
              </div>

              <form onSubmit={handleSaveAttendanceEdit} className="space-y-5">
                {/* 4 Tarjetas de Opción */}
                <div>
                  <label className="block text-xs font-bold text-[#7B8195] uppercase mb-2">
                    Selecciona el Nuevo Estado de Asistencia
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    
                    {/* Tarjeta 1: Asistencia */}
                    <div
                      onClick={() => {
                        setSelectedType('PRESENT');
                        setEditArrivalTime('07:55 AM');
                        setEditReason('Jornada presencial completa · Asistencia verificada');
                      }}
                      className={`p-3.5 rounded-2xl border-2 cursor-pointer transition-all flex items-start gap-3 select-none ${
                        selectedType === 'PRESENT'
                          ? 'border-[#20B486] bg-[#20B486]/10 ring-2 ring-[#20B486]/20'
                          : 'border-[#E8EAF2] hover:border-[#20B486]/40 bg-white'
                      }`}
                    >
                      <div className="w-8 h-8 rounded-lg bg-[#20B486]/15 text-[#20B486] flex items-center justify-center shrink-0 mt-0.5">
                        <CheckCircle2 size={18} strokeWidth={2.5} />
                      </div>
                      <div className="min-w-0">
                        <p className="font-bold text-sm text-[#11132C]">Asistencia</p>
                        <p className="text-[11px] text-[#7C8499] leading-tight mt-0.5">
                          Jornada presencial cumplida a tiempo
                        </p>
                      </div>
                    </div>

                    {/* Tarjeta 2: Retraso */}
                    <div
                      onClick={() => {
                        setSelectedType('LATE');
                        setEditArrivalTime('08:20 AM');
                        setEditReason('Retraso por transporte reportado');
                      }}
                      className={`p-3.5 rounded-2xl border-2 cursor-pointer transition-all flex items-start gap-3 select-none ${
                        selectedType === 'LATE'
                          ? 'border-[#F5B83D] bg-[#F5B83D]/10 ring-2 ring-[#F5B83D]/20'
                          : 'border-[#E8EAF2] hover:border-[#F5B83D]/40 bg-white'
                      }`}
                    >
                      <div className="w-8 h-8 rounded-lg bg-[#F5B83D]/15 text-[#B87A00] flex items-center justify-center shrink-0 mt-0.5">
                        <Clock size={18} strokeWidth={2.5} />
                      </div>
                      <div className="min-w-0">
                        <p className="font-bold text-sm text-[#11132C]">Retraso</p>
                        <p className="text-[11px] text-[#7C8499] leading-tight mt-0.5">
                          Llegada posterior a hora límite
                        </p>
                      </div>
                    </div>

                    {/* Tarjeta 3: Falta Justificada */}
                    <div
                      onClick={() => {
                        setSelectedType('JUSTIFIED_ABSENCE');
                        setEditArrivalTime('');
                        setEditReason('Incapacidad médica EPS radicada');
                      }}
                      className={`p-3.5 rounded-2xl border-2 cursor-pointer transition-all flex items-start gap-3 select-none ${
                        selectedType === 'JUSTIFIED_ABSENCE'
                          ? 'border-[#5B3FF5] bg-[#5B3FF5]/10 ring-2 ring-[#5B3FF5]/20'
                          : 'border-[#E8EAF2] hover:border-[#5B3FF5]/40 bg-white'
                      }`}
                    >
                      <div className="w-8 h-8 rounded-lg bg-[#5B3FF5]/15 text-[#5B3FF5] flex items-center justify-center shrink-0 mt-0.5">
                        <ShieldCheck size={18} strokeWidth={2.5} />
                      </div>
                      <div className="min-w-0">
                        <p className="font-bold text-sm text-[#11132C]">Falta Justificada</p>
                        <p className="text-[11px] text-[#7C8499] leading-tight mt-0.5">
                          Con soporte legal o de EPS
                        </p>
                      </div>
                    </div>

                    {/* Tarjeta 4: Falta Injustificada */}
                    <div
                      onClick={() => {
                        setSelectedType('UNJUSTIFIED_ABSENCE');
                        setEditArrivalTime('');
                        setEditReason('Ausencia sin justificación documental');
                      }}
                      className={`p-3.5 rounded-2xl border-2 cursor-pointer transition-all flex items-start gap-3 select-none ${
                        selectedType === 'UNJUSTIFIED_ABSENCE'
                          ? 'border-[#FF5C67] bg-[#FF5C67]/10 ring-2 ring-[#FF5C67]/20'
                          : 'border-[#E8EAF2] hover:border-[#FF5C67]/40 bg-white'
                      }`}
                    >
                      <div className="w-8 h-8 rounded-lg bg-[#FF5C67]/15 text-[#FF5C67] flex items-center justify-center shrink-0 mt-0.5">
                        <XCircle size={18} strokeWidth={2.5} />
                      </div>
                      <div className="min-w-0">
                        <p className="font-bold text-sm text-[#11132C]">Falta Injustificada</p>
                        <p className="text-[11px] text-[#7C8499] leading-tight mt-0.5">
                          Inasistencia no soportada
                        </p>
                      </div>
                    </div>

                  </div>
                </div>

                {/* Campos de Detalle */}
                <div className="space-y-3">
                  {(selectedType === 'PRESENT' || selectedType === 'LATE') && (
                    <div>
                      <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">
                        Hora de Llegada
                      </label>
                      <input
                        type="text"
                        value={editArrivalTime}
                        onChange={e => setEditArrivalTime(e.target.value)}
                        placeholder="Ej: 08:15 AM"
                        className="w-full px-3.5 py-2 border border-[#E8EAF2] rounded-xl text-sm font-mono font-medium focus:border-[#5B3DF5] focus:outline-none"
                      />
                    </div>
                  )}

                  <div>
                    <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">
                      Motivo / Referencia
                    </label>
                    <input
                      type="text"
                      value={editReason}
                      onChange={e => setEditReason(e.target.value)}
                      placeholder="Describe la novedad o soporte..."
                      className="w-full px-3.5 py-2 border border-[#E8EAF2] rounded-xl text-sm font-medium focus:border-[#5B3DF5] focus:outline-none"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={() => setEditingRecord(null)}
                    className="px-4 py-2 text-sm font-semibold text-gray-500 hover:text-gray-800 cursor-pointer"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 bg-[#5B3FF5] hover:bg-[#4a32cc] text-white rounded-xl text-sm font-bold shadow-md shadow-[#5B3FF5]/20 cursor-pointer"
                  >
                    Actualizar Asistencia
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL PARA ENVIAR MENSAJE PERSONALIZADO AL CODER */}
      <AnimatePresence>
        {showMessageModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl border border-gray-100"
            >
              <div className="flex justify-between items-start mb-5">
                <div>
                  <h3 className="text-lg font-bold text-[#11132C] flex items-center gap-2">
                    <MessageSquare size={18} className="text-[#5B3FF5]" />
                    Enviar Mensaje a {coder.name}
                  </h3>
                  <p className="text-xs text-[#7C8499] mt-0.5">
                    Este comunicado aparecerá directamente en el Chat HSE del portal del estudiante.
                  </p>
                </div>
                <button
                  onClick={() => setShowMessageModal(false)}
                  className="p-1 text-gray-400 hover:text-gray-700 transition-colors cursor-pointer"
                >
                  <X size={20} />
                </button>
              </div>

              <form onSubmit={handleSendPersonalMessage} className="space-y-4">
                <div className="p-3 rounded-xl bg-[#F8F9FE] border border-[#E8EAF2] text-xs space-y-1">
                  <p className="font-semibold text-[#11132C]">
                    Destinatario: <span className="text-[#5B3FF5]">{coder.name}</span>
                  </p>
                  <p className="text-[#7C8499]">
                    Correo: {coder.email} · Ruta: {coder.route || 'General'}
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">
                      Asunto
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="Ej: Seguimiento de Asistencia"
                      value={messageForm.subject}
                      onChange={e => setMessageForm({ ...messageForm, subject: e.target.value })}
                      className="w-full px-3.5 py-2 border border-[#E8EAF2] rounded-xl text-sm font-medium focus:border-[#5B3DF5] focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">
                      Prioridad
                    </label>
                    <select
                      value={messageForm.priority}
                      onChange={e => setMessageForm({ ...messageForm, priority: e.target.value as any })}
                      className="w-full px-3 py-2 border border-[#E8EAF2] rounded-xl text-sm font-medium bg-white focus:border-[#5B3DF5] focus:outline-none"
                    >
                      <option value="NORMAL">Normal</option>
                      <option value="URGENT">Urgente</option>
                      <option value="INFO">Informativo</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">
                    Mensaje Personalizado
                  </label>
                  <textarea
                    rows={4}
                    required
                    placeholder="Escribe la observación, recomendación o citación para el estudiante..."
                    value={messageForm.body}
                    onChange={e => setMessageForm({ ...messageForm, body: e.target.value })}
                    className="w-full px-3.5 py-2.5 border border-[#E8EAF2] rounded-xl text-sm font-normal focus:border-[#5B3DF5] focus:outline-none resize-none"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={() => setShowMessageModal(false)}
                    className="px-4 py-2 text-sm font-semibold text-gray-500 hover:text-gray-800 cursor-pointer"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 bg-[#5B3FF5] hover:bg-[#4a32cc] text-white rounded-xl text-sm font-bold shadow-md shadow-[#5B3FF5]/20 flex items-center gap-1.5 cursor-pointer"
                  >
                    <Send size={14} />
                    <span>Enviar Mensaje</span>
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}

export default CoderAttendanceHistory;
