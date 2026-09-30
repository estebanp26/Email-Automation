import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { motion } from 'framer-motion';

export default function Reports() {
  const [chartData, setChartData] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({ approval_rate: 0, total: 200, pending: 200 });

  useEffect(() => {
    api.getRequestsPerWeek().then(setChartData);
    api.getDashboardStats().then(setStats);
  }, []);

  return (
    <div className="space-y-4 sm:space-y-6">
      <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">Reportes y Analíticas</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        <div className="lg:col-span-2">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white p-4 sm:p-6 rounded-2xl shadow-sm border border-gray-100 overflow-hidden"
          >
            <h2 className="text-base sm:text-lg font-bold text-gray-800 mb-4 sm:mb-6">Tendencia de Solicitudes</h2>
            <div className="h-64 sm:h-80 w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorSolicitudes" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#5B3FF5" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#5B3FF5" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#888', fontSize: 12}} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: '#888', fontSize: 12}} />
                  <Tooltip />
                  <Area type="monotone" dataKey="solicitudes" stroke="#5B3FF5" strokeWidth={3} fillOpacity={1} fill="url(#colorSolicitudes)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        </div>

        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white p-4 sm:p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col"
          >
            <h2 className="text-base sm:text-lg font-bold text-gray-800 mb-3 sm:mb-4">Resumen Mensual</h2>
            <div className="flex-1 space-y-3 sm:space-y-4">
               <div className="p-3.5 sm:p-4 bg-gray-50 rounded-xl">
                 <p className="text-xs sm:text-sm text-gray-500 mb-0.5 sm:mb-1">Tasa de Aprobación</p>
                 <p className="text-xl sm:text-2xl font-bold text-green-600">{stats.approval_rate || 0}%</p>
               </div>
               <div className="p-3.5 sm:p-4 bg-gray-50 rounded-xl">
                 <p className="text-xs sm:text-sm text-gray-500 mb-0.5 sm:mb-1">Total Radicadas</p>
                 <p className="text-xl sm:text-2xl font-bold text-blue-600">{stats.total || 0}</p>
               </div>
               <div className="p-3.5 sm:p-4 bg-gray-50 rounded-xl">
                 <p className="text-xs sm:text-sm text-gray-500 mb-0.5 sm:mb-1">Casos en Revisión Manual</p>
                 <p className="text-base sm:text-lg font-bold text-amber-600">{stats.por_revisar ?? stats.pending ?? 0} pendientes</p>
               </div>
            </div>
            <div className="mt-4 sm:mt-6 space-y-2">
              <button 
                onClick={() => api.exportHseReport('csv')}
                className="w-full bg-[#5B3FF5] text-white py-2.5 sm:py-3 rounded-xl font-medium hover:bg-[#4a31d4] transition-colors cursor-pointer text-sm sm:text-base flex items-center justify-center gap-2 shadow-sm"
              >
                <span>Descargar Reporte CSV HSE</span>
              </button>
              <button 
                onClick={() => api.exportHseReport('excel')}
                className="w-full bg-white text-[#5B3FF5] border border-[#5B3FF5] py-2 sm:py-2.5 rounded-xl font-medium hover:bg-violet-50 transition-colors cursor-pointer text-xs sm:text-sm flex items-center justify-center gap-2"
              >
                <span>Descargar Informe Excel (.xlsx)</span>
              </button>
            </div>
          </motion.div>
      </div>
    </div>
  );
}
