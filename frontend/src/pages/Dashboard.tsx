import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, CheckCircle, XCircle, Clock, ChevronDown, Maximize2, BarChart2, PieChart as PieChartIcon, Download, Settings as SettingsIcon, Bell, LogOut } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { api } from '../services/api';

export default function Dashboard() {
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const navigate = useNavigate();

  const [stats, setStats] = useState({
    total: 200,
    approved: 0,
    denied: 0,
    pending: 200,
    revisadas: 0,
    por_revisar: 200,
    approval_rate: 0
  });

  const [weeklyData, setWeeklyData] = useState<any[]>([
    { name: 'Lun', Total: 200, Aprobados: 0, Denegados: 0 },
    { name: 'Mar', Total: 0, Aprobados: 0, Denegados: 0 },
    { name: 'Mié', Total: 0, Aprobados: 0, Denegados: 0 },
    { name: 'Jue', Total: 0, Aprobados: 0, Denegados: 0 },
    { name: 'Vie', Total: 0, Aprobados: 0, Denegados: 0 },
  ]);

  const [recentEmails, setRecentEmails] = useState<any[]>([]);

  useEffect(() => {
    // 1. Obtener KPIs agregados desde la base de datos
    api.getDashboardStats().then((data: any) => {
      if (data && typeof data.total === 'number') {
        setStats(data);
      }
    });

    // 2. Obtener tendencia semanal real
    api.getRequestsPerWeek().then((data: any) => {
      if (Array.isArray(data) && data.length > 0) {
        setWeeklyData(data);
      }
    });

    // 3. Obtener correos recientes reales
    api.getRecentEmails().then((data: any) => {
      if (Array.isArray(data) && data.length > 0) {
        setRecentEmails(data);
      }
    });
  }, []);

  const totalEvaluated = stats.revisadas ?? (stats.approved + stats.denied);
  const percentReviewed = stats.total > 0 ? Math.round((totalEvaluated / stats.total) * 100) : 0;

  const pieData = [
    { name: 'Revisadas', value: totalEvaluated },
    { name: 'Pendientes', value: stats.por_revisar ?? stats.pending },
  ];

  const kpiCards = [
    { 
      label: 'Total recibidos', 
      value: String(stats.total), 
      growth: '+100%', 
      text: 'radicados en el sistema', 
      icon: Mail, 
      color: 'text-[#20B486]', 
      bg: 'bg-[#20B486]', 
      wave: 'from-[#20B486]/5 to-transparent' 
    },
    { 
      label: 'Aprobados', 
      value: String(stats.approved), 
      growth: `${stats.approval_rate || 0}%`, 
      text: 'tasa de aprobación', 
      icon: CheckCircle, 
      color: 'text-[#5B3FF5]', 
      bg: 'bg-[#5B3FF5]', 
      wave: 'from-[#5B3FF5]/5 to-transparent' 
    },
    { 
      label: 'Denegados', 
      value: String(stats.denied), 
      growth: '0%', 
      text: 'rechazados por criterio', 
      icon: XCircle, 
      color: 'text-[#FF5C67]', 
      bg: 'bg-[#FF5C67]', 
      wave: 'from-[#FF5C67]/5 to-transparent' 
    },
    { 
      label: 'Por revisar', 
      value: String(stats.pending), 
      growth: `${100 - (stats.approval_rate || 0)}%`, 
      text: 'requieren decisión TL', 
      icon: Clock, 
      color: 'text-[#F5B83D]', 
      bg: 'bg-[#F5B83D]', 
      wave: 'from-[#F5B83D]/5 to-transparent' 
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-[28px] font-bold text-[#11132C] mb-1">Resumen del Sistema HSE - Barranquilla</h1>
          <h2 className="text-xl font-bold text-[#11132C] mt-4 mb-1">¡Bienvenido de nuevo, Paola!</h2>
          <p className="text-[#7C8499] text-sm">Aquí tienes un resumen en tiempo real de las solicitudes del sistema.</p>
        </div>
        
        <div className="flex items-center gap-4 mt-2 relative">
          <button 
            onClick={() => navigate('/requests')}
            className="flex items-center gap-2 bg-[#5B3FF5] hover:bg-[#4a32cc] px-4 py-2 rounded-full shadow-lg shadow-[#5B3FF5]/30 text-sm font-semibold text-white transition-colors cursor-pointer"
          >
            <Download size={16} /> Ver Solicitudes ({stats.total})
          </button>

          <div 
            className="w-10 h-10 rounded-full bg-[#11132C] flex items-center justify-center text-white font-bold text-sm cursor-pointer select-none"
            onClick={() => setShowProfileMenu(!showProfileMenu)}
          >
            PA
          </div>
          {showProfileMenu && (
            <div className="absolute top-12 right-0 w-48 bg-white rounded-xl shadow-lg border border-gray-100 py-2 z-50">
              <button onClick={() => navigate('/requests')} className="w-full text-left px-4 py-2 text-sm text-[#11132C] hover:bg-gray-50 flex items-center gap-3 transition-colors cursor-pointer">
                <Bell size={16} className="text-[#7C8499]" />
                Bandeja de Solicitudes
              </button>
              <button onClick={() => navigate('/settings')} className="w-full text-left px-4 py-2 text-sm text-[#11132C] hover:bg-gray-50 flex items-center gap-3 transition-colors cursor-pointer">
                <SettingsIcon size={16} className="text-[#7C8499]" />
                Configuración
              </button>
              <button onClick={() => { localStorage.removeItem('hse_token'); window.location.href = '/login'; }} className="w-full text-left px-4 py-2 text-sm text-[#FF5C67] hover:bg-red-50 flex items-center gap-3 transition-colors cursor-pointer">
                <LogOut size={16} className="text-[#FF5C67]" />
                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-6 pt-4">
        {kpiCards.map((kpi, i) => (
          <div key={i} className="bg-white rounded-3xl p-6 relative overflow-hidden shadow-[0_4px_20px_-10px_rgba(0,0,0,0.05)] border border-gray-50 flex flex-col justify-between h-[160px]">
            <div className={`absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t ${kpi.wave} pointer-events-none rounded-b-3xl`} />
            
            <div className="flex justify-between items-start z-10 relative">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-full ${kpi.bg} flex items-center justify-center text-white shadow-md shadow-${kpi.color}/20`}>
                  <kpi.icon size={20} strokeWidth={2.5} />
                </div>
                <span className="font-semibold text-[#11132C]">{kpi.label}</span>
              </div>
              <ChevronDown size={16} className="text-gray-300 -rotate-90 cursor-pointer" />
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

      {/* Charts Row */}
      <div className="grid grid-cols-[2fr_1fr] gap-6">
        {/* Bar Chart */}
        <div className="bg-white rounded-3xl p-6 shadow-[0_4px_20px_-10px_rgba(0,0,0,0.05)] border border-gray-50">
          <div className="flex justify-between items-start mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#5B3FF5]/10 flex items-center justify-center text-[#5B3FF5]">
                <BarChart2 size={20} />
              </div>
              <div>
                <h3 className="font-bold text-[#11132C]">Solicitudes por semana</h3>
                <p className="text-xs text-[#7C8499]">Total, aprobadas y denegadas</p>
              </div>
            </div>
          </div>
          
          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weeklyData} margin={{ top: 20, right: 0, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#7C8499', fontSize: 12 }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#7C8499', fontSize: 12 }} />
                <Tooltip cursor={{ fill: 'transparent' }} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 15px rgba(0,0,0,0.1)' }} />
                <Legend iconType="circle" wrapperStyle={{ top: -45, right: 20, width: 'auto' }} />
                <Bar dataKey="Total" fill="#7B61FF" radius={[4, 4, 4, 4]} barSize={12} />
                <Bar dataKey="Aprobados" fill="#20B486" radius={[4, 4, 4, 4]} barSize={12} />
                <Bar dataKey="Denegados" fill="#FF5C67" radius={[4, 4, 4, 4]} barSize={12} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Donut Chart */}
        <div className="bg-white rounded-3xl p-6 shadow-[0_4px_20px_-10px_rgba(0,0,0,0.05)] border border-gray-50 flex flex-col">
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#5B3FF5]/10 flex items-center justify-center text-[#5B3FF5]">
                <PieChartIcon size={20} />
              </div>
              <div>
                <h3 className="font-bold text-[#11132C]">Solicitudes por revisar</h3>
                <p className="text-xs text-[#7C8499]">Porcentaje de solicitudes auditadas</p>
              </div>
            </div>
            <ChevronDown size={16} className="text-gray-300 -rotate-90 cursor-pointer" />
          </div>

          <div className="flex-1 relative flex flex-col items-center justify-center">
            <div className="h-[200px] w-full relative">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="65%"
                    startAngle={180}
                    endAngle={0}
                    innerRadius={75}
                    outerRadius={95}
                    paddingAngle={5}
                    dataKey="value"
                    stroke="none"
                    cornerRadius={10}
                  >
                    <Cell fill="#5B3FF5" />
                    <Cell fill="#E2E8F0" />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              
              <div className="absolute inset-0 flex flex-col items-center justify-end pb-8 pointer-events-none">
                <span className="text-[40px] font-black text-[#11132C] leading-none">{percentReviewed}%</span>
                <span className="text-sm text-[#7C8499] font-medium mt-1">Revisadas</span>
              </div>
            </div>

            <div className="flex w-full justify-around mt-2">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#5B3FF5]" />
                  <span className="font-bold text-[#11132C] text-sm">Revisadas</span>
                </div>
                <span className="text-xs text-[#7C8499] pl-5">{percentReviewed}% ({totalEvaluated})</span>
              </div>
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#E2E8F0]" />
                  <span className="font-bold text-[#11132C] text-sm">Pendientes</span>
                </div>
                <span className="text-xs text-[#7C8499] pl-5">{100 - percentReviewed}% ({stats.por_revisar ?? stats.pending})</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Emails */}
      <div className="bg-white rounded-3xl p-6 shadow-[0_4px_20px_-10px_rgba(0,0,0,0.05)] border border-gray-50">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#5B3FF5]/10 flex items-center justify-center text-[#5B3FF5]">
              <Mail size={20} />
            </div>
            <h3 className="font-bold text-[#11132C] text-lg">Correos recientes recibidos ({recentEmails.length})</h3>
          </div>
          <button 
            onClick={() => navigate('/requests')}
            className="bg-[#5B3FF5] text-white px-5 py-2.5 rounded-full text-sm font-semibold flex items-center gap-2 hover:bg-[#4a32cc] transition-colors shadow-lg shadow-[#5B3FF5]/30 cursor-pointer"
          >
            <Maximize2 size={16} /> Ver en pantalla completa
          </button>
        </div>

        <div className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar">
          {recentEmails.map((email, i) => (
            <div 
              key={email.id || i} 
              onClick={() => navigate('/requests')}
              className="min-w-[280px] max-w-[320px] border border-gray-100 rounded-2xl p-4 flex flex-col bg-white hover:border-[#5B3FF5]/40 transition-all cursor-pointer shadow-xs"
            >
              <div className="flex items-center gap-2 mb-3">
                <div className="w-7 h-7 rounded-full bg-[#F5F7FB] flex items-center justify-center text-[#5B3FF5]">
                  <Mail size={12} />
                </div>
                <span className="text-xs font-medium text-[#7C8499] truncate">{email.sender}</span>
              </div>
              <h4 className="font-bold text-[#11132C] text-sm mb-1 line-clamp-1">{email.title}</h4>
              <p className="text-xs text-[#7C8499] mb-4 line-clamp-2">{email.snippet}</p>
              
              <div className="mt-auto flex justify-between items-center">
                <span className="text-[11px] text-[#7C8499]">{email.time}</span>
                <div className={`px-2.5 py-1 rounded-full flex items-center gap-1.5 text-[11px] font-semibold ${email.color}`}>
                  <div className={`w-1.5 h-1.5 rounded-full ${email.dot}`} />
                  {email.status}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
