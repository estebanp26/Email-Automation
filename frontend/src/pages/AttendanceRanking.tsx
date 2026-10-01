import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { 
  Search, 
  AlertTriangle, 
  AlertCircle, 
  CheckCircle2, 
  ShieldAlert, 
  ChevronRight, 
  MessageSquare, 
  Users, 
  Filter,
  ArrowUpDown,
  BookOpen
} from 'lucide-react';
import { api } from '../services/api';
import { matchesNormalized } from '../utils/textUtils';
import { CoderAttendanceHistory } from '../components/students/CoderAttendanceHistory';
import type { Student } from '../types';

export type RiskLevel = 'CRITICAL' | 'RISK' | 'GOOD';

export interface CoderWithRisk extends Student {
  riskLevel: RiskLevel;
  unjustifiedCount: number;
  justifiedCount: number;
  lateCount: number;
  totalAbsences: number;
  attendancePct: number;
  rank: number;
}

export default function AttendanceRanking() {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRoute, setSelectedRoute] = useState<string>('ALL');
  const [riskFilter, setRiskFilter] = useState<'ALL' | RiskLevel>('ALL');
  const [sortBy, setSortBy] = useState<'UNJUSTIFIED' | 'TOTAL' | 'PCT'>('UNJUSTIFIED');
  const [selectedCoder, setSelectedCoder] = useState<Student | null>(null);

  useEffect(() => {
    setLoading(true);
    api.getStudents()
      .then((data: Student[]) => {
        if (Array.isArray(data) && data.length > 0) {
          setStudents(data);
        }
      })
      .catch((err) => console.error('Error cargando estudiantes para ranking:', err))
      .finally(() => setLoading(false));
  }, []);

  // Calcular métricas, nivel de riesgo y ranking para todos los coders
  const rankedCoders: CoderWithRisk[] = useMemo(() => {
    const list = students.map((s) => {
      const unjustified = s.attendance?.unjustifiedAbsence ?? 0;
      const justified = s.attendance?.justifiedAbsence ?? 0;
      const late = s.attendance?.late ?? 0;
      const present = s.attendance?.present ?? Math.max(10, 40 - unjustified - justified - late);
      const totalAbsences = unjustified + justified;
      const totalSessions = present + late + totalAbsences;
      const attendancePct = totalSessions > 0 ? Math.round((present / totalSessions) * 100) : 95;

      // Criterio de semaforización:
      // Rojo: 3 o más injustificadas (límite legal superado/alcanzado) o 4+ faltas totales
      // Amarillo: 2 injustificadas (a 1 falta del límite) o 2-3 faltas totales
      // Verde: 0 a 1 injustificada y buen estado
      let riskLevel: RiskLevel = 'GOOD';
      if (unjustified >= 3 || totalAbsences >= 4) {
        riskLevel = 'CRITICAL';
      } else if (unjustified === 2 || totalAbsences >= 2) {
        riskLevel = 'RISK';
      }

      return {
        ...s,
        riskLevel,
        unjustifiedCount: unjustified,
        justifiedCount: justified,
        lateCount: late,
        totalAbsences,
        attendancePct,
        rank: 0 // se asigna tras ordenar
      };
    });

    // Ordenar por severidad (priorizar injustificadas, luego total faltas, luego menor %)
    list.sort((a, b) => {
      if (sortBy === 'UNJUSTIFIED') {
        if (b.unjustifiedCount !== a.unjustifiedCount) {
          return b.unjustifiedCount - a.unjustifiedCount;
        }
        return b.totalAbsences - a.totalAbsences;
      }
      if (sortBy === 'TOTAL') {
        return b.totalAbsences - a.totalAbsences;
      }
      return a.attendancePct - b.attendancePct;
    });

    // Asignar posición de ranking general
    return list.map((item, idx) => ({
      ...item,
      rank: idx + 1
    }));
  }, [students, sortBy]);

  // Rutas disponibles
  const availableRoutes = useMemo(() => {
    const map: Record<string, number> = {};
    students.forEach((s) => {
      const r = s.route || 'Sin ruta';
      map[r] = (map[r] || 0) + 1;
    });
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  }, [students]);

  // Contadores de KPIs
  const counts = useMemo(() => {
    let critical = 0;
    let risk = 0;
    let good = 0;
    rankedCoders.forEach((c) => {
      if (c.riskLevel === 'CRITICAL') critical++;
      else if (c.riskLevel === 'RISK') risk++;
      else good++;
    });
    return {
      total: rankedCoders.length,
      critical,
      risk,
      good
    };
  }, [rankedCoders]);

  // Filtrado reactivo por búsqueda, ruta y pestaña de riesgo
  const filteredCoders = useMemo(() => {
    return rankedCoders.filter((c) => {
      // Filtro de riesgo
      if (riskFilter !== 'ALL' && c.riskLevel !== riskFilter) {
        return false;
      }
      // Filtro de ruta
      if (selectedRoute !== 'ALL' && (c.route || 'Sin ruta') !== selectedRoute) {
        return false;
      }
      // Filtro de búsqueda
      const q = searchQuery.trim();
      if (!q) return true;
      return (
        matchesNormalized(c.name, q) ||
        matchesNormalized(c.email, q) ||
        matchesNormalized(c.route, q) ||
        (c.cedula && c.cedula.includes(q))
      );
    });
  }, [rankedCoders, riskFilter, selectedRoute, searchQuery]);

  // Si hay un coder seleccionado, renderizamos su perfil completo
  if (selectedCoder) {
    return (
      <div className="h-[calc(100vh-6rem)] overflow-y-auto custom-scrollbar pr-1 pb-10">
        <CoderAttendanceHistory
          coder={selectedCoder}
          onBack={() => setSelectedCoder(null)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* HEADER PRINCIPAL */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[#FF5C67]/10 text-[#FF5C67] flex items-center justify-center shadow-xs">
              <ShieldAlert size={22} />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl lg:text-[28px] font-bold text-[#11132C] leading-tight">
                Ranking y Control de Inasistencias
              </h1>
              <p className="text-xs sm:text-sm text-[#7C8499] mt-0.5">
                Top de coders ordenados por faltas con semaforización de riesgo y acceso directo a mensajería oficial.
              </p>
            </div>
          </div>
        </div>

        {/* Buscador Superior */}
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#7C8499]" size={17} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar por coder, email o cédula..."
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-[#E2E8F0] rounded-2xl text-xs sm:text-sm focus:outline-none focus:border-[#5B3FF5] focus:ring-4 focus:ring-[#5B3FF5]/10 transition-all text-[#11132C] placeholder:text-[#A3AAC2] shadow-xs"
          />
        </div>
      </div>

      {/* TARJETAS KPI DE RESUMEN CROMÁTICO */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Coders */}
        <div className="bg-white rounded-3xl p-5 border border-gray-100 shadow-[0_4px_20px_-10px_rgba(0,0,0,0.05)] relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#7C8499] uppercase tracking-wider">Total Coders</span>
            <div className="w-8 h-8 rounded-full bg-[#5B3FF5]/10 text-[#5B3FF5] flex items-center justify-center">
              <Users size={16} />
            </div>
          </div>
          <div className="mt-3">
            <h3 className="text-3xl font-black text-[#11132C]">{counts.total}</h3>
            <p className="text-xs text-[#7C8499] mt-0.5">Auditados en el sistema HSE</p>
          </div>
        </div>

        {/* 🔴 Casos Críticos (Límite Superado) */}
        <button
          onClick={() => setRiskFilter(riskFilter === 'CRITICAL' ? 'ALL' : 'CRITICAL')}
          className={`text-left rounded-3xl p-5 border transition-all cursor-pointer relative overflow-hidden flex flex-col justify-between ${
            riskFilter === 'CRITICAL' 
              ? 'bg-[#FF5C67] text-white border-[#FF5C67] shadow-lg shadow-[#FF5C67]/25' 
              : 'bg-white hover:bg-red-50/50 border-red-100 shadow-[0_4px_20px_-10px_rgba(255,92,103,0.1)]'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className={`text-xs font-bold uppercase tracking-wider ${riskFilter === 'CRITICAL' ? 'text-white/80' : 'text-[#FF5C67]'}`}>
              🔴 Casos Críticos
            </span>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${riskFilter === 'CRITICAL' ? 'bg-white/20 text-white' : 'bg-[#FF5C67]/10 text-[#FF5C67]'}`}>
              <AlertCircle size={16} />
            </div>
          </div>
          <div className="mt-3">
            <h3 className={`text-3xl font-black ${riskFilter === 'CRITICAL' ? 'text-white' : 'text-[#FF5C67]'}`}>
              {counts.critical}
            </h3>
            <p className={`text-xs mt-0.5 ${riskFilter === 'CRITICAL' ? 'text-white/80' : 'text-[#7C8499]'}`}>
              {counts.critical > 0 ? 'Con 3+ faltas (límite superado)' : 'Sin casos críticos'}
            </p>
          </div>
        </button>

        {/* 🟡 En Riesgo (Alerta Preventiva) */}
        <button
          onClick={() => setRiskFilter(riskFilter === 'RISK' ? 'ALL' : 'RISK')}
          className={`text-left rounded-3xl p-5 border transition-all cursor-pointer relative overflow-hidden flex flex-col justify-between ${
            riskFilter === 'RISK' 
              ? 'bg-[#F5B83D] text-white border-[#F5B83D] shadow-lg shadow-[#F5B83D]/25' 
              : 'bg-white hover:bg-amber-50/50 border-amber-100 shadow-[0_4px_20px_-10px_rgba(245,184,61,0.1)]'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className={`text-xs font-bold uppercase tracking-wider ${riskFilter === 'RISK' ? 'text-white/80' : 'text-[#D9961A]'}`}>
              🟡 En Riesgo
            </span>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${riskFilter === 'RISK' ? 'bg-white/20 text-white' : 'bg-[#F5B83D]/15 text-[#D9961A]'}`}>
              <AlertTriangle size={16} />
            </div>
          </div>
          <div className="mt-3">
            <h3 className={`text-3xl font-black ${riskFilter === 'RISK' ? 'text-white' : 'text-[#D9961A]'}`}>
              {counts.risk}
            </h3>
            <p className={`text-xs mt-0.5 ${riskFilter === 'RISK' ? 'text-white/80' : 'text-[#7C8499]'}`}>
              2 inasistencias (a 1 del límite)
            </p>
          </div>
        </button>

        {/* 🟢 Al Día / Asistencia Óptima */}
        <button
          onClick={() => setRiskFilter(riskFilter === 'GOOD' ? 'ALL' : 'GOOD')}
          className={`text-left rounded-3xl p-5 border transition-all cursor-pointer relative overflow-hidden flex flex-col justify-between ${
            riskFilter === 'GOOD' 
              ? 'bg-[#20B486] text-white border-[#20B486] shadow-lg shadow-[#20B486]/25' 
              : 'bg-white hover:bg-emerald-50/50 border-emerald-100 shadow-[0_4px_20px_-10px_rgba(32,180,134,0.1)]'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className={`text-xs font-bold uppercase tracking-wider ${riskFilter === 'GOOD' ? 'text-white/80' : 'text-[#20B486]'}`}>
              🟢 Al Día
            </span>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${riskFilter === 'GOOD' ? 'bg-white/20 text-white' : 'bg-[#20B486]/10 text-[#20B486]'}`}>
              <CheckCircle2 size={16} />
            </div>
          </div>
          <div className="mt-3">
            <h3 className={`text-3xl font-black ${riskFilter === 'GOOD' ? 'text-white' : 'text-[#20B486]'}`}>
              {counts.good}
            </h3>
            <p className={`text-xs mt-0.5 ${riskFilter === 'GOOD' ? 'text-white/80' : 'text-[#7C8499]'}`}>
              Asistencia normal y regular
            </p>
          </div>
        </button>
      </div>

      {/* BARRA DE FILTROS, RUTAS Y ORDENAMIENTO */}
      <div className="bg-white p-4 sm:p-5 rounded-3xl border border-gray-100 shadow-[0_4px_20px_-10px_rgba(0,0,0,0.05)] flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
        {/* Pestañas de Severidad */}
        <div className="flex items-center gap-1.5 p-1 bg-gray-100/70 rounded-2xl overflow-x-auto shrink-0">
          <button
            onClick={() => setRiskFilter('ALL')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              riskFilter === 'ALL'
                ? 'bg-white text-[#11132C] shadow-xs'
                : 'text-[#7C8499] hover:text-[#11132C]'
            }`}
          >
            Todos ({counts.total})
          </button>
          <button
            onClick={() => setRiskFilter('CRITICAL')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              riskFilter === 'CRITICAL'
                ? 'bg-[#FF5C67] text-white shadow-xs'
                : 'text-[#FF5C67] hover:bg-red-50'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-[#FF5C67] inline-block" />
            Críticos ({counts.critical})
          </button>
          <button
            onClick={() => setRiskFilter('RISK')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              riskFilter === 'RISK'
                ? 'bg-[#F5B83D] text-white shadow-xs'
                : 'text-[#D9961A] hover:bg-amber-50'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-[#F5B83D] inline-block" />
            En Riesgo ({counts.risk})
          </button>
          <button
            onClick={() => setRiskFilter('GOOD')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              riskFilter === 'GOOD'
                ? 'bg-[#20B486] text-white shadow-xs'
                : 'text-[#20B486] hover:bg-emerald-50'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-[#20B486] inline-block" />
            Al Día ({counts.good})
          </button>
        </div>

        {/* Filtros secundarios: Ruta y Criterio de Orden */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Selector de Ruta */}
          <div className="flex items-center gap-2">
            <BookOpen size={15} className="text-[#7C8499]" />
            <select
              value={selectedRoute}
              onChange={(e) => setSelectedRoute(e.target.value)}
              className="bg-gray-50 border border-gray-200 text-xs font-bold text-[#11132C] rounded-xl px-3 py-2 focus:outline-none focus:border-[#5B3FF5] cursor-pointer"
            >
              <option value="ALL">Todas las rutas ({students.length})</option>
              {availableRoutes.map(([name, count]) => (
                <option key={name} value={name}>
                  {name} ({count})
                </option>
              ))}
            </select>
          </div>

          {/* Selector de Orden */}
          <div className="flex items-center gap-2">
            <ArrowUpDown size={15} className="text-[#7C8499]" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-gray-50 border border-gray-200 text-xs font-bold text-[#11132C] rounded-xl px-3 py-2 focus:outline-none focus:border-[#5B3FF5] cursor-pointer"
            >
              <option value="UNJUSTIFIED">Mayor a menor faltas sin soporte</option>
              <option value="TOTAL">Total de inasistencias acumuladas</option>
              <option value="PCT">Menor % de asistencia general</option>
            </select>
          </div>
        </div>
      </div>

      {/* LISTADO DE CODERS EN RANKING */}
      <div className="space-y-3">
        {loading ? (
          <div className="bg-white rounded-3xl p-12 text-center border border-gray-100">
            <div className="inline-block w-8 h-8 border-4 border-[#5B3FF5] border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-sm font-semibold text-[#7C8499]">Calculando ranking de inasistencias...</p>
          </div>
        ) : filteredCoders.length === 0 ? (
          <div className="bg-white rounded-3xl p-12 text-center border border-gray-100 text-[#7C8499]">
            <Filter size={36} className="mx-auto mb-3 opacity-30" />
            <h3 className="font-bold text-[#11132C] text-base">No hay coders en este criterio</h3>
            <p className="text-xs mt-1">Prueba cambiando la severidad, la ruta o limpiando el buscador.</p>
          </div>
        ) : (
          filteredCoders.map((coder) => {
            const initials = coder.name
              ? coder.name.split(' ').map((n) => n[0]).slice(0, 2).join('')
              : 'C';

            // Estilos cromáticos según riesgo
            const isCritical = coder.riskLevel === 'CRITICAL';
            const isRisk = coder.riskLevel === 'RISK';
            const isGood = coder.riskLevel === 'GOOD';

            const cardBorder = isCritical
              ? 'border-l-4 border-l-[#FF5C67] border-gray-200 hover:border-[#FF5C67]'
              : isRisk
              ? 'border-l-4 border-l-[#F5B83D] border-gray-200 hover:border-[#F5B83D]'
              : 'border-l-4 border-l-[#20B486] border-gray-200 hover:border-[#20B486]';

            const badgeBg = isCritical
              ? 'bg-red-50 text-[#FF5C67] border-red-200'
              : isRisk
              ? 'bg-amber-50 text-[#D9961A] border-amber-200'
              : 'bg-emerald-50 text-[#20B486] border-emerald-200';

            const avatarBg = isCritical
              ? 'bg-gradient-to-tr from-[#FF5C67] to-[#ff8c95] text-white'
              : isRisk
              ? 'bg-gradient-to-tr from-[#F5B83D] to-[#ffd27a] text-white'
              : 'bg-gradient-to-tr from-[#20B486] to-[#5cdbaf] text-white';

            return (
              <motion.div
                key={coder.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                onClick={() => setSelectedCoder(coder)}
                className={`bg-white rounded-2xl sm:rounded-3xl p-4 sm:p-5 border transition-all hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)] cursor-pointer flex flex-col md:flex-row items-start md:items-center justify-between gap-4 group ${cardBorder}`}
              >
                {/* LADO IZQUIERDO: RANKING + AVATAR + DATOS */}
                <div className="flex items-center gap-3.5 sm:gap-5 min-w-0">
                  {/* Badge de Posición en el Ranking */}
                  <div className={`w-9 h-9 sm:w-11 sm:h-11 rounded-2xl flex items-center justify-center font-black text-xs sm:text-sm shrink-0 ${
                    coder.rank === 1 ? 'bg-[#FF5C67] text-white shadow-md shadow-[#FF5C67]/30' :
                    coder.rank === 2 ? 'bg-[#FF5C67]/80 text-white' :
                    coder.rank === 3 ? 'bg-[#F5B83D] text-white' :
                    'bg-gray-100 text-[#7C8499]'
                  }`}>
                    #{coder.rank}
                  </div>

                  {/* Avatar con Iniciales */}
                  <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-2xl flex items-center justify-center font-bold text-sm sm:text-base shrink-0 shadow-xs ${avatarBg}`}>
                    {initials}
                  </div>

                  {/* Información Coder */}
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-bold text-[#11132C] text-sm sm:text-base group-hover:text-[#5B3FF5] transition-colors truncate">
                        {coder.name}
                      </h3>
                      {coder.cedula && (
                        <span className="text-[10px] font-mono text-[#7C8499] bg-gray-100 px-2 py-0.5 rounded-md">
                          CC: {coder.cedula}
                        </span>
                      )}
                      <span className="text-[10px] font-medium text-[#5B3FF5] bg-[#5B3FF5]/10 px-2 py-0.5 rounded-md truncate max-w-[180px]">
                        {coder.route || 'Ruta General'}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-[#7C8499]">
                      <span className="truncate">{coder.email}</span>
                      <span className="hidden sm:inline">•</span>
                      <span className={`inline-flex items-center gap-1 font-bold text-[11px] px-2 py-0.5 rounded-full border ${badgeBg}`}>
                        {isCritical && <AlertCircle size={12} />}
                        {isRisk && <AlertTriangle size={12} />}
                        {isGood && <CheckCircle2 size={12} />}
                        {isCritical ? 'Crítico - Límite Superado' : isRisk ? 'En Riesgo de Sanción' : 'Asistencia Regular'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* LADO DERECHO: DESGLOSE DE MÉTRICAS + BOTÓN ACCIÓN */}
                <div className="flex items-center justify-between md:justify-end gap-3 sm:gap-6 w-full md:w-auto pt-3 md:pt-0 border-t md:border-t-0 border-gray-100">
                  {/* Faltas Injustificadas (Métrica Clave) */}
                  <div className="text-left md:text-right">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C8499] block">
                      Sin Justificar
                    </span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className={`text-base sm:text-lg font-black ${
                        isCritical ? 'text-[#FF5C67]' : isRisk ? 'text-[#D9961A]' : 'text-[#20B486]'
                      }`}>
                        {coder.unjustifiedCount}
                      </span>
                      <span className="text-[11px] font-bold text-[#7C8499]">/ 3 máx</span>
                    </div>
                  </div>

                  {/* Faltas Justificadas */}
                  <div className="text-left md:text-right hidden sm:block">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C8499] block">
                      Con Soporte
                    </span>
                    <span className="text-sm sm:text-base font-bold text-[#11132C] mt-0.5 block">
                      {coder.justifiedCount}
                    </span>
                  </div>

                  {/* % Asistencia */}
                  <div className="text-left md:text-right">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C8499] block">
                      Asistencia
                    </span>
                    <span className={`text-sm sm:text-base font-bold mt-0.5 block ${
                      coder.attendancePct >= 90 ? 'text-[#20B486]' :
                      coder.attendancePct >= 80 ? 'text-[#D9961A]' : 'text-[#FF5C67]'
                    }`}>
                      {coder.attendancePct}%
                    </span>
                  </div>

                  {/* Botón de Entrada al Perfil y Mensajes */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedCoder(coder);
                    }}
                    className="flex items-center gap-2 bg-[#5B3FF5]/10 hover:bg-[#5B3FF5] text-[#5B3FF5] hover:text-white px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer shrink-0 shadow-2xs group-hover:bg-[#5B3FF5] group-hover:text-white"
                  >
                    <MessageSquare size={14} />
                    <span className="hidden sm:inline">Perfil & Mensaje</span>
                    <ChevronRight size={14} />
                  </button>
                </div>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}
