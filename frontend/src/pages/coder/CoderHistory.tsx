import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertTriangle, 
  Search, 
  PlusCircle, 
  Calendar, 
  ChevronDown, 
  Paperclip, 
  MessageSquare,
  FileText,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';
import type { CoderJustification, CoderJustificationStatus } from '../../types';
import { getCoderSession } from '../../utils/coderSession';
import { 
  getCoderJustifications, 
  calculateCoderStats,
  NOVELTY_LABELS 
} from '../../utils/coderJustifications';
import { RequestCorrectionModal } from '../../components/coder/RequestCorrectionModal';
import { matchesNormalized } from '../../utils/textUtils';
import { useAuth } from '../../context/AuthContext';
import { CoderProfileMenu } from '../../components/coder/CoderProfileMenu';

export default function CoderHistory() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const session = useMemo(() => {
    if (user && user.role === 'CODER') {
      return {
        name: user.name,
        cedula: user.cedula || '',
        email: user.email,
        route: user.route || 'Desarrollo de Software',
      };
    }
    return getCoderSession();
  }, [user]);

  const [justifications, setJustifications] = useState<CoderJustification[]>([]);
  const [activeFilter, setActiveFilter] = useState<'ALL' | CoderJustificationStatus>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedForCorrection, setSelectedForCorrection] = useState<CoderJustification | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Cargar justificaciones del coder desde almacenamiento persistente
  const loadData = () => {
    const list = getCoderJustifications(
      session.cedula,
      session.name,
      session.email,
      session.route
    );
    setJustifications(list);
  };

  useEffect(() => {
    loadData();
  }, [session]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Manejo de subsanación exitosa desde el modal
  const handleCorrectionSuccess = (updated: CoderJustification) => {
    loadData();
    showToast(`Subsanación enviada para el radicado ${updated.radicado}. Ahora está En Revisión HSE.`);
  };

  // Estadísticas KPI calculadas
  const stats = useMemo(() => calculateCoderStats(justifications), [justifications]);

  // 4 Tarjetas KPI que replican exactamente la estructura y diseño del Dashboard HSE
  const kpiCards = [
    {
      label: 'Convalidadas',
      value: String(stats.approved),
      growth: `${stats.approvalRate}%`,
      text: 'tasa de convalidación',
      icon: CheckCircle,
      color: 'text-[#20B486]',
      bg: 'bg-[#20B486]',
      wave: 'from-[#20B486]/5 to-transparent',
      statusKey: 'APPROVED' as const,
    },
    {
      label: 'No Aprobadas',
      value: String(stats.disapproved),
      growth: stats.total > 0 ? `${Math.round((stats.disapproved / stats.total) * 100)}%` : '0%',
      text: 'sin convalidar por criterio',
      icon: XCircle,
      color: 'text-[#FF5C67]',
      bg: 'bg-[#FF5C67]',
      wave: 'from-[#FF5C67]/5 to-transparent',
      statusKey: 'DISAPPROVED' as const,
    },
    {
      label: 'En Revisión HSE',
      value: String(stats.revision),
      growth: stats.total > 0 ? `${Math.round((stats.revision / stats.total) * 100)}%` : '0%',
      text: 'en auditoría del analista',
      icon: Clock,
      color: 'text-[#F5B83D]',
      bg: 'bg-[#F5B83D]',
      wave: 'from-[#F5B83D]/5 to-transparent',
      statusKey: 'REVISION_MANUAL' as const,
    },
    {
      label: 'Requiere Corrección',
      value: String(stats.requestCorrection),
      growth: `${stats.requestCorrection} pendientes`,
      text: 'por adjuntar nuevo soporte',
      icon: AlertTriangle,
      color: 'text-[#F97316]',
      bg: 'bg-[#F97316]',
      wave: 'from-[#F97316]/5 to-transparent',
      statusKey: 'REQUEST_CORRECTION' as const,
    },
  ];

  // Filtrar justificaciones por búsqueda y estado (tolerante a tildes / acentos)
  const filteredJustifications = useMemo(() => {
    return justifications.filter((j) => {
      const matchesFilter = activeFilter === 'ALL' || j.status === activeFilter;
      const q = searchQuery.trim();
      const matchesSearch = 
        !q ||
        matchesNormalized(j.radicado, q) ||
        matchesNormalized(j.novelty_label || j.novelty_type, q) ||
        matchesNormalized(j.description, q) ||
        matchesNormalized(j.status, q) ||
        matchesNormalized(j.start_date, q) ||
        matchesNormalized(j.end_date, q);

      return matchesFilter && matchesSearch;
    });
  }, [justifications, activeFilter, searchQuery]);

  // Renderizador de Badge de Estado Unificado
  const renderStatusBadge = (status: CoderJustificationStatus) => {
    switch (status) {
      case 'APPROVED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#20B486]/10 text-[#136c50] border border-[#20B486]/30 shadow-sm">
            <span className="size-2 rounded-full bg-[#20B486]" />
            🟢 Convalidada / Aprobada
          </span>
        );
      case 'DISAPPROVED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#FF5C67]/10 text-[#9c242c] border border-[#FF5C67]/30 shadow-sm">
            <span className="size-2 rounded-full bg-[#FF5C67]" />
            🔴 No Aprobada
          </span>
        );
      case 'REVISION_MANUAL':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#F5B83D]/15 text-[#855e09] border border-[#F5B83D]/40 shadow-sm">
            <span className="size-2 rounded-full bg-[#F5B83D] animate-pulse" />
            🟡 En Revisión HSE
          </span>
        );
      case 'REQUEST_CORRECTION':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#F97316]/15 text-[#9a3412] border border-[#F97316]/40 shadow-sm animate-pulse">
            <span className="size-2 rounded-full bg-[#F97316]" />
            🟠 Requiere Corrección
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Toast Notification flotante */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-6 left-1/2 -translate-x-1/2 z-50 bg-[#11132C] text-white px-6 py-3 rounded-full font-bold shadow-2xl flex items-center gap-2 border border-white/10 text-xs sm:text-sm"
          >
            <CheckCircle2 size={18} className="text-[#20B486]" />
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* HEADER PRINCIPAL (idéntico al del Dashboard HSE) */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-[28px] font-bold text-[#11132C] mb-1">
            Historial de Solicitudes HSE - Barranquilla
          </h1>
          <h2 className="text-xl font-bold text-[#11132C] mt-2 mb-1">
            ¡Bienvenido de nuevo, {session.name.split(' ')[0]}!
          </h2>
          <p className="text-[#7C8499] text-sm">
            Aquí tienes el seguimiento en tiempo real de tus justificaciones radicadas y convalidaciones.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Botón de acción rápida: Radicar Justificación */}
          <button
            type="button"
            onClick={() => navigate('/coder/new-excuse')}
            className="flex items-center gap-2 bg-[#5B3FF5] hover:bg-[#4a32cc] px-5 py-2.5 rounded-full shadow-lg shadow-[#5B3FF5]/30 text-sm font-semibold text-white transition-all cursor-pointer hover:scale-[1.02]"
          >
            <PlusCircle size={16} />
            <span>Radicar Justificación</span>
          </button>

          {/* Avatar del Coder con menú desplegable */}
          <CoderProfileMenu />
        </div>
      </div>

      {/* 4 CUADROS DEL PANEL PRINCIPAL (REPLICADOS EXACTAMENTE DE LAS FOTOS HSE) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 pt-2">
        {kpiCards.map((kpi, i) => (
          <div
            key={i}
            onClick={() => setActiveFilter(activeFilter === kpi.statusKey ? 'ALL' : kpi.statusKey)}
            className={`bg-white rounded-3xl p-6 relative overflow-hidden shadow-[0_4px_20px_-10px_rgba(0,0,0,0.05)] border border-gray-50 flex flex-col justify-between h-[160px] cursor-pointer transition-all hover:scale-[1.02] hover:shadow-md ${
              activeFilter === kpi.statusKey ? 'ring-2 ring-[#5B3FF5]' : ''
            }`}
          >
            <div className={`absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t ${kpi.wave} pointer-events-none rounded-b-3xl`} />

            <div className="flex justify-between items-start z-10 relative">
              <div className="flex items-center gap-3">
                <div className={`size-10 rounded-full ${kpi.bg} flex items-center justify-center text-white shadow-md shadow-${kpi.color}/20`}>
                  <kpi.icon size={20} strokeWidth={2.5} />
                </div>
                <span className="font-semibold text-[#11132C] text-sm">{kpi.label}</span>
              </div>
              <ChevronDown size={16} className="text-gray-300 -rotate-90" />
            </div>

            <div className="text-center z-10 relative mt-2">
              <h3 className="text-[40px] font-bold text-[#11132C] leading-none mb-3">{kpi.value}</h3>
              <p className="text-xs text-[#7C8499] flex items-center justify-center gap-1">
                <span className={kpi.color}>↗ {kpi.growth}</span> {kpi.text}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* BARRA DE HERRAMIENTAS: FILTROS Y BÚSQUEDA */}
      <div className="bg-white rounded-2xl p-4 border border-[#E2E8F0] shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Pills de Filtrado por Estado */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => setActiveFilter('ALL')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeFilter === 'ALL'
                ? 'bg-[#5B3FF5] text-white shadow-md shadow-[#5B3FF5]/25'
                : 'bg-gray-100 text-[#7C8499] hover:text-[#11132C] hover:bg-gray-200'
            }`}
          >
            Todas ({justifications.length})
          </button>

          <button
            type="button"
            onClick={() => setActiveFilter('APPROVED')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeFilter === 'APPROVED'
                ? 'bg-[#20B486] text-white shadow-md shadow-[#20B486]/25'
                : 'bg-emerald-50 text-[#136c50] hover:bg-emerald-100 border border-emerald-200/60'
            }`}
          >
            <span className="size-1.5 rounded-full bg-[#20B486]" />
            Aprobadas ({stats.approved})
          </button>

          <button
            type="button"
            onClick={() => setActiveFilter('REVISION_MANUAL')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeFilter === 'REVISION_MANUAL'
                ? 'bg-[#F5B83D] text-white shadow-md shadow-[#F5B83D]/25'
                : 'bg-amber-50 text-[#855e09] hover:bg-amber-100 border border-amber-200/60'
            }`}
          >
            <span className="size-1.5 rounded-full bg-[#F5B83D]" />
            En Revisión ({stats.revision})
          </button>

          <button
            type="button"
            onClick={() => setActiveFilter('REQUEST_CORRECTION')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeFilter === 'REQUEST_CORRECTION'
                ? 'bg-[#F97316] text-white shadow-md shadow-[#F97316]/25'
                : 'bg-orange-50 text-[#9a3412] hover:bg-orange-100 border border-orange-200/60'
            }`}
          >
            <span className="size-1.5 rounded-full bg-[#F97316]" />
            Requiere Corrección ({stats.requestCorrection})
          </button>

          <button
            type="button"
            onClick={() => setActiveFilter('DISAPPROVED')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              activeFilter === 'DISAPPROVED'
                ? 'bg-[#FF5C67] text-white shadow-md shadow-[#FF5C67]/25'
                : 'bg-rose-50 text-[#9c242c] hover:bg-rose-100 border border-rose-200/60'
            }`}
          >
            <span className="size-1.5 rounded-full bg-[#FF5C67]" />
            No Aprobadas ({stats.disapproved})
          </button>
        </div>

        {/* Buscador */}
        <div className="relative min-w-[260px]">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#7C8499]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar por radicado, motivo..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-gray-50 border border-[#E2E8F0] text-xs text-[#111827] placeholder:text-[#A3AAC2] focus:outline-none focus:border-[#5B3FF5] focus:bg-white transition-all"
          />
        </div>
      </div>

      {/* LISTADO DE JUSTIFICACIONES RADICADAS */}
      <div className="space-y-4">
        {filteredJustifications.length === 0 ? (
          <div className="p-12 text-center rounded-3xl bg-white border border-[#E2E8F0] shadow-sm space-y-3">
            <div className="size-14 rounded-2xl bg-gray-100 text-[#7C8499] flex items-center justify-center mx-auto">
              <FileText className="size-7" />
            </div>
            <h3 className="text-base font-bold text-[#111827]">No se encontraron solicitudes</h3>
            <p className="text-xs text-[#7C8499] max-w-sm mx-auto">
              {searchQuery
                ? 'No hay registros que coincidan con los criterios de búsqueda aplicados.'
                : 'Aún no has radicado solicitudes bajo este filtro.'}
            </p>
            <button
              type="button"
              onClick={() => navigate('/coder/new-excuse')}
              className="mt-2 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#5B3FF5] text-white text-xs font-bold hover:bg-[#4a32cc] transition-colors cursor-pointer shadow-md shadow-[#5B3FF5]/20"
            >
              <PlusCircle size={15} />
              <span>Radicar Nueva Justificación</span>
            </button>
          </div>
        ) : (
          filteredJustifications.map((item) => {
            const isCorrectionNeeded = item.status === 'REQUEST_CORRECTION';

            return (
              <motion.div
                key={item.id}
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-6 rounded-3xl bg-white border transition-all shadow-sm space-y-4 ${
                  isCorrectionNeeded
                    ? 'border-[#F97316]/50 shadow-md shadow-[#F97316]/5 hover:border-[#F97316]'
                    : 'border-[#E2E8F0] hover:border-slate-300'
                }`}
              >
                {/* Cabecera de la Tarjeta */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#E2E8F0]/70">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-bold text-[#5B3FF5] bg-[#F2F0FF] px-3 py-1 rounded-xl border border-[#5B3FF5]/30 shadow-xs">
                      {item.radicado}
                    </span>
                    <span className="text-xs text-[#7C8499] font-mono">
                      Radicado: {new Date(item.submitted_at).toLocaleDateString('es-CO', { dateStyle: 'medium' })}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 self-start sm:self-auto">
                    {renderStatusBadge(item.status)}
                  </div>
                </div>

                {/* Contenido Principal */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                  {/* Tipo de novedad y periodo */}
                  <div className="space-y-1">
                    <span className="text-[#7C8499] uppercase tracking-wider font-semibold text-[10px] block">
                      Novedad y Periodo
                    </span>
                    <p className="font-bold text-sm text-[#111827]">
                      {item.novelty_label || NOVELTY_LABELS[item.novelty_type] || item.novelty_type}
                    </p>
                    <p className="text-[#7C8499] flex items-center gap-1.5 font-medium">
                      <Calendar size={13} className="text-[#5B3FF5]" />
                      <span>{item.start_date} al {item.end_date}</span>
                    </p>
                  </div>

                  {/* Descripción detallada */}
                  <div className="md:col-span-2 space-y-1">
                    <span className="text-[#7C8499] uppercase tracking-wider font-semibold text-[10px] block">
                      Motivo Declarado
                    </span>
                    <p className="text-slate-700 leading-relaxed line-clamp-2">
                      {item.description}
                    </p>
                  </div>
                </div>

                {/* Soportes Probatorios Adjuntos */}
                {item.attachments && item.attachments.length > 0 && (
                  <div className="pt-2 flex flex-wrap items-center gap-2 text-xs">
                    <span className="text-[#7C8499] font-semibold text-[11px] flex items-center gap-1">
                      <Paperclip size={12} className="text-[#5B3FF5]" /> Evidencias adjuntas ({item.attachments.length}):
                    </span>
                    {item.attachments.map((att, aIdx) => (
                      <span
                        key={aIdx}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-gray-50 border border-[#E2E8F0] text-[#111827] text-xs"
                      >
                        <FileText size={12} className="text-[#5B3FF5]" />
                        <span className="truncate max-w-[220px] font-mono text-[11px]">{att.filename}</span>
                      </span>
                    ))}
                  </div>
                )}

                {/* CALLOUT DE FEEDBACK HSE (Notas del Analista) */}
                {item.hse_notes && (
                  <div
                    className={`p-4 rounded-2xl border text-xs space-y-1 ${
                      isCorrectionNeeded
                        ? 'bg-[#F97316]/10 border-[#F97316]/30 text-[#7c2d12]'
                        : item.status === 'APPROVED'
                        ? 'bg-[#20B486]/10 border-[#20B486]/30 text-[#136c50]'
                        : item.status === 'DISAPPROVED'
                        ? 'bg-[#FF5C67]/10 border-[#FF5C67]/30 text-[#9c242c]'
                        : 'bg-gray-50 border-[#E2E8F0] text-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between font-bold text-[11px]">
                      <span className="flex items-center gap-1.5 uppercase tracking-wide">
                        {isCorrectionNeeded ? (
                          <AlertTriangle size={14} className="text-[#F97316]" />
                        ) : (
                          <MessageSquare size={14} />
                        )}
                        Dictamen del Equipo HSE
                      </span>
                      {item.hse_reviewer && (
                        <span className="font-normal opacity-80">{item.hse_reviewer}</span>
                      )}
                    </div>
                    <p className="leading-relaxed font-medium">{item.hse_notes}</p>
                  </div>
                )}

                {/* Respuesta previa del coder si ya subsanó */}
                {item.coder_response && (
                  <div className="p-3.5 rounded-2xl bg-[#F2F0FF] border border-[#5B3FF5]/20 text-xs space-y-1">
                    <span className="font-bold text-[#5B3FF5] uppercase tracking-wide text-[10px] block">
                      Aclaración enviada por ti:
                    </span>
                    <p className="text-slate-700 italic leading-relaxed">
                      "{item.coder_response}"
                    </p>
                  </div>
                )}

                {/* ACCIÓN INTERACTIVA PARA REQUEST_CORRECTION */}
                {isCorrectionNeeded && (
                  <div className="pt-2 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-t border-[#F97316]/20">
                    <span className="text-xs font-semibold text-[#9a3412]">
                      ⚠️ Tu justificación requiere corrección o soporte adicional para ser aprobada.
                    </span>

                    <button
                      type="button"
                      onClick={() => setSelectedForCorrection(item)}
                      className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#F97316] to-[#EA580C] hover:opacity-95 text-white font-bold text-xs flex items-center gap-2 shadow-md shadow-[#F97316]/30 cursor-pointer transition-all"
                    >
                      <RefreshCw size={14} />
                      <span>Subsanar Solicitud / Adjuntar Soporte</span>
                    </button>
                  </div>
                )}
              </motion.div>
            );
          })
        )}
      </div>

      {/* MODAL INTERACTIVO DE SUBSANACIÓN */}
      <RequestCorrectionModal
        justification={selectedForCorrection}
        isOpen={Boolean(selectedForCorrection)}
        onClose={() => setSelectedForCorrection(null)}
        onSuccess={handleCorrectionSuccess}
      />
    </div>
  );
}
