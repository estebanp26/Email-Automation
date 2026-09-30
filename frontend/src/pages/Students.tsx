import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Search, Mail, ChevronRight, Users, BookOpen } from 'lucide-react';
import { api } from '../services/api';
import { matchesNormalized } from '../utils/textUtils';
import { CoderAttendanceHistory } from '../components/students/CoderAttendanceHistory';

export default function Students() {
  const [students, setStudents] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeRouteName, setActiveRouteName] = useState<string>('');
  const [selectedCoder, setSelectedCoder] = useState<any | null>(null);

  useEffect(() => {
    api.getStudents().then((data: any) => {
      if (Array.isArray(data) && data.length > 0) {
        setStudents(data);
      }
    });
  }, []);

  // Agrupar rutas dinámicamente desde los coders reales
  const routes = useMemo(() => {
    const counts: Record<string, number> = {};
    students.forEach((s) => {
      const r = s.route || 'Sin ruta';
      counts[r] = (counts[r] || 0) + 1;
    });

    const list = Object.entries(counts)
      .map(([name, count]) => ({
        id: name,
        name,
        count
      }))
      .sort((a, b) => b.count - a.count);

    return list;
  }, [students]);

  // Si no hay ruta seleccionada o la actual no existe, seleccionar la primera
  useEffect(() => {
    if (routes.length > 0 && (!activeRouteName || !routes.some(r => r.name === activeRouteName))) {
      setActiveRouteName(routes[0].name);
    }
  }, [routes, activeRouteName]);

  const activeRoute = routes.find(r => r.name === activeRouteName) || {
    id: 'default',
    name: 'Cargando rutas...',
    count: students.length
  };

  // Filtrar coders por ruta activa y búsqueda (tolerante a tildes / acentos)
  const filteredCoders = useMemo(() => {
    return students.filter(s => {
      const matchesRoute = (s.route || 'Sin ruta') === activeRouteName;
      const q = searchQuery.trim();
      const matchesSearch = !q || 
        matchesNormalized(s.name, q) ||
        matchesNormalized(s.email, q) ||
        matchesNormalized(s.route, q) ||
        (s.cedula && s.cedula.includes(q));
      return matchesRoute && matchesSearch;
    });
  }, [students, activeRouteName, searchQuery]);

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
    <div className="h-[calc(100vh-6rem)] flex flex-col gap-6">
      
      {/* PAGE HEADER */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 flex-shrink-0">
        <div>
          <h1 className="text-[28px] font-bold text-[#111827]">Directorio de Coders RIWI</h1>
          <p className="text-[#7C8499] mt-1 text-sm">Gestiona y visualiza los {students.length} estudiantes reales por ruta de entrenamiento.</p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#7C8499]" size={18} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar por nombre, correo o cédula..."
            className="pl-10 pr-4 py-2.5 w-full sm:w-[320px] bg-white border border-[#E2E8F0] rounded-xl text-sm focus:outline-none focus:border-[#5B3FF5] focus:ring-4 focus:ring-[#5B3FF5]/10 transition-all text-[#111827] placeholder:text-[#A3AAC2]"
          />
        </div>
      </div>

      {/* MAIN CONTENT LAYOUT */}
      <div className="flex-1 flex flex-col lg:flex-row gap-6 overflow-hidden min-h-0">
        
        {/* SIDEBAR: LISTA DE RUTAS */}
        <div className="w-full lg:w-[320px] bg-white rounded-[24px] border border-[#E2E8F0] shadow-sm flex flex-col flex-shrink-0 overflow-hidden">
          <div className="p-5 border-b border-[#E2E8F0] bg-gray-50/50">
            <h2 className="text-xs font-bold text-[#7C8499] uppercase tracking-widest flex items-center gap-2">
              <BookOpen size={14} />
              Rutas Institucionales ({routes.length})
            </h2>
          </div>
          
          <div className="flex-1 p-3 overflow-y-auto custom-scrollbar space-y-1">
            {routes.map(route => {
              const isActive = route.name === activeRouteName;
              return (
                <button
                  key={route.id}
                  onClick={() => setActiveRouteName(route.name)}
                  className={`w-full flex items-center justify-between p-3.5 rounded-[16px] transition-all duration-200 group cursor-pointer ${
                    isActive 
                      ? 'bg-gradient-to-r from-[#5636F5] to-[#633BFF] shadow-md' 
                      : 'bg-transparent hover:bg-[#F6F7FB]'
                  }`}
                >
                  <span className={`font-semibold text-[14px] text-left leading-tight ${isActive ? 'text-white' : 'text-[#17203A] group-hover:text-[#5B3FF5]'}`}>
                    {route.name}
                  </span>
                  <span className={`text-[11px] px-2.5 py-1 rounded-full font-bold flex-shrink-0 ml-3 transition-colors ${
                    isActive 
                      ? 'bg-white/20 text-white' 
                      : 'bg-[#F2F0FF] text-[#5B3FF5]'
                  }`}>
                    {route.count}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* LISTA DE CODERS */}
        <div className="flex-1 bg-white rounded-[24px] border border-[#E2E8F0] shadow-sm flex flex-col overflow-hidden min-w-0">
          
          {/* HEADER DE LA RUTA SELECCIONADA */}
          <div className="p-6 lg:px-8 border-b border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gray-50/30">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <div className="w-8 h-8 rounded-lg bg-[#F2F0FF] text-[#5B3FF5] flex items-center justify-center">
                  <Users size={16} strokeWidth={2.5} />
                </div>
                <h2 className="text-[20px] font-bold text-[#111827]">{activeRoute.name}</h2>
              </div>
              <p className="text-sm text-[#7C8499] font-medium ml-11">
                Total de {filteredCoders.length} coders en esta vista
              </p>
            </div>
            
            <button className="flex items-center justify-center gap-2 text-sm text-[#5B3FF5] font-bold bg-[#F2F0FF] px-5 py-2.5 rounded-[12px] hover:bg-[#EDEBFF] transition-colors cursor-pointer">
              <Mail size={16} strokeWidth={2.5} /> 
              Mensaje a la Ruta
            </button>
          </div>
          
          {/* CONTENEDOR DE RECTANGULOS HORIZONTALES */}
          <div className="flex-1 p-6 lg:p-8 overflow-y-auto custom-scrollbar bg-[#F6F7FB]/50 space-y-3">
            {filteredCoders.length === 0 ? (
              <div className="text-center py-12 text-[#7C8499]">
                <p>No se encontraron coders con los criterios actuales.</p>
              </div>
            ) : (
              filteredCoders.map((coder, index) => {
                const initials = coder.name
                  ? coder.name.split(' ').map((n: string) => n[0]).slice(0, 2).join('')
                  : 'C';
                const attendancePct = coder.attendance?.present 
                  ? Math.round((coder.attendance.present / 40) * 100) 
                  : 95;

                return (
                  <motion.div
                    key={coder.id}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25, delay: Math.min(index * 0.02, 0.3) }}
                    onClick={() => setSelectedCoder(coder)}
                    className="bg-white border border-[#E2E8F0] p-4 lg:px-6 lg:py-5 rounded-[20px] flex items-center justify-between hover:shadow-[0_8px_30px_rgba(0,0,0,0.04)] hover:border-[#5B3FF5]/30 transition-all group cursor-pointer"
                  >
                    {/* INFO IZQUIERDA: AVATAR Y NOMBRE */}
                    <div className="flex items-center gap-5 min-w-0">
                      <div className="w-[46px] h-[46px] rounded-[14px] bg-gradient-to-tr from-[#5B3FF5] to-[#7B61FF] flex items-center justify-center text-white font-bold shadow-[0_4px_12px_rgba(91,63,245,0.2)] flex-shrink-0 text-sm">
                        {initials}
                      </div>
                      <div className="truncate">
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-[#111827] text-[15px] group-hover:text-[#5B3FF5] transition-colors truncate">
                            {coder.name}
                          </h3>
                          {coder.cedula && (
                            <span className="text-[11px] font-mono text-[#A3AAC2] bg-gray-100 px-1.5 py-0.5 rounded">
                              CC: {coder.cedula}
                            </span>
                          )}
                        </div>
                        <p className="text-[13px] text-[#7C8499] truncate mt-0.5">{coder.email}</p>
                      </div>
                    </div>
                    
                    {/* INFO DERECHA: ESTADISTICAS Y ACCIONES */}
                    <div className="flex items-center gap-8 ml-4 flex-shrink-0">
                      
                      {/* ASISTENCIA */}
                      <div className="hidden md:flex flex-col items-end">
                        <span className="text-[11px] text-[#A3AAC2] font-bold uppercase tracking-wide mb-1">Asistencia</span>
                        <span className={`text-[14px] font-bold flex items-center gap-1.5 ${attendancePct >= 90 ? 'text-[#20B486]' : 'text-[#F5B83D]'}`}>
                          <div className={`w-2 h-2 rounded-full ${attendancePct >= 90 ? 'bg-[#20B486]' : 'bg-[#F5B83D]'}`}></div>
                          {attendancePct}%
                        </span>
                      </div>

                      {/* ESTADO */}
                      <div className="hidden sm:flex min-w-[90px] justify-end">
                        <span className={`px-3 py-1.5 rounded-full text-[12px] font-bold ${
                          coder.status === 'Activo' 
                            ? 'bg-[#20B486]/10 text-[#20B486]' 
                            : 'bg-[#FF5C67]/10 text-[#FF5C67]'
                        }`}>
                          {coder.status}
                        </span>
                      </div>

                      {/* FLECHA DE NAVEGACION */}
                      <button className="w-8 h-8 flex items-center justify-center rounded-full text-[#A3AAC2] group-hover:bg-[#F2F0FF] group-hover:text-[#5B3FF5] transition-all">
                        <ChevronRight size={18} strokeWidth={2.5} />
                      </button>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
