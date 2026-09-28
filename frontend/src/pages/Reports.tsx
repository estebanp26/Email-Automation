import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { motion } from 'framer-motion';

export default function Reports() {
  const [chartData, setChartData] = useState<any[]>([]);

  useEffect(() => {
    // Reusing the per week data for the area chart
    api.getRequestsPerWeek().then(setChartData);
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Reportes y Analíticas</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100"
          >
            <h2 className="text-lg font-bold text-gray-800 mb-6">Tendencia de Solicitudes</h2>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorSolicitudes" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#5B3FF5" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#5B3FF5" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#888'}} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: '#888'}} />
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
            className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col"
          >
            <h2 className="text-lg font-bold text-gray-800 mb-4">Resumen Mensual</h2>
            <div className="flex-1 space-y-4">
               <div className="p-4 bg-gray-50 rounded-xl">
                 <p className="text-sm text-gray-500 mb-1">Tasa de Aprobación</p>
                 <p className="text-2xl font-bold text-green-600">85%</p>
               </div>
               <div className="p-4 bg-gray-50 rounded-xl">
                 <p className="text-sm text-gray-500 mb-1">Tiempo de Respuesta</p>
                 <p className="text-2xl font-bold text-blue-600">2.4 hrs</p>
               </div>
               <div className="p-4 bg-gray-50 rounded-xl">
                 <p className="text-sm text-gray-500 mb-1">Picos de Solicitudes</p>
                 <p className="text-lg font-bold text-gray-800">Lunes, Jueves</p>
               </div>
            </div>
            <button className="mt-6 w-full bg-[#5B3FF5] text-white py-3 rounded-xl font-medium hover:bg-[#4a31d4] transition-colors">
              Descargar Informe Excel
              

            </button>
          </motion.div>
      </div>
    </div>
  );
}
