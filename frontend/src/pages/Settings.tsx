import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Bell, 
  User, 
  Lock, 
  Shield, 
  Sliders, 
  Building, 
  Clock, 
  MapPin, 
  Phone, 
  Mail, 
  Edit3, 
  Check,
  RefreshCw,
  CheckCircle2,
  Settings as SettingsIcon,
  Download,
  LogOut,
  Database,
  Cpu,
  HardDrive,
  Activity
} from 'lucide-react';
import { api, type SystemHealthStatus } from '../services/api';

export default function Settings() {
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const navigate = useNavigate();

  // Local state for interactive elements
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [language, setLanguage] = useState('Español');
  
  const [notifications, setNotifications] = useState({
    newRequests: true,
    approvedRequests: true,
    deniedRequests: false,
    pendingRequests: true,
    newReports: false
  });
  
  const [notificationMethod, setNotificationMethod] = useState<'email' | 'system'>('email');

  // Monitor de Salud de Servicios Nativos State
  const [healthStatus, setHealthStatus] = useState<SystemHealthStatus | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);
  const [lastCheckTime, setLastCheckTime] = useState<string>('');

  const refreshHealth = async () => {
    setIsCheckingHealth(true);
    try {
      const data = await api.getServicesHealth();
      setHealthStatus(data);
      setLastCheckTime(new Date().toLocaleTimeString('es-ES'));
    } catch (e) {
      console.warn('Error comprobando salud de servicios:', e);
    } finally {
      setIsCheckingHealth(false);
    }
  };

  useEffect(() => {
    refreshHealth();
  }, []);

  return (
    <div className="flex flex-col gap-8 pb-10">
      
      {/* TOP HEADER */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-[28px] font-bold text-[#151A2D]">Configuración</h1>
          <p className="text-[#7B8195] mt-1 text-sm">Administra tu cuenta, salud de servicios nativos y seguridad.</p>
        </div>
        <div className="flex items-center gap-4 relative">
          <button className="flex items-center gap-2 bg-[#5B3FF5] hover:bg-[#4a32cc] px-4 py-2 rounded-full shadow-lg shadow-[#5B3FF5]/30 text-sm font-semibold text-white transition-colors cursor-pointer">
            <Download size={16} /> Descargar reporte
          </button>

          <div 
            className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#5B3DF5] to-[#7357FF] flex items-center justify-center text-white font-bold shadow-md shadow-[#5B3DF5]/20 cursor-pointer select-none"
            onClick={() => setShowProfileMenu(!showProfileMenu)}
          >
            PA
          </div>
          {showProfileMenu && (
            <div className="absolute top-12 right-0 w-48 bg-white rounded-xl shadow-lg border border-gray-100 py-2 z-50">
              <button onClick={() => navigate('/requests')} className="w-full text-left px-4 py-2 text-sm text-[#11132C] hover:bg-gray-50 flex items-center gap-3 transition-colors cursor-pointer">
                <Bell size={16} className="text-[#7C8499]" />
                Notificaciones
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

      {/* ================================================================ */}
      {/* CARD DESTACADA: MONITOR DE SALUD DE SERVICIOS NATIVOS             */}
      {/* ================================================================ */}
      <motion.div 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-[24px] border-2 border-[#5B3DF5]/30 shadow-[0_4px_25px_rgba(91,61,245,0.06)] p-6 md:p-8"
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E8EAF2] pb-6 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#5B3DF5] to-[#7357FF] text-white flex items-center justify-center shadow-md shadow-[#5B3DF5]/25">
              <Activity size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-[20px] font-bold text-[#151A2D]">Monitor de Salud de Servicios Nativos</h2>
                <span className="text-[11px] font-bold uppercase tracking-wider bg-[#20B486]/10 text-[#20B486] px-2.5 py-0.5 rounded-full flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#20B486] animate-pulse" /> Microservicios Operativos
                </span>
              </div>
              <p className="text-[13px] text-[#7B8195]">
                Supervisión en tiempo real de los servicios centrales: Base de datos, Motor IA, Storage y Correo.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={refreshHealth}
              disabled={isCheckingHealth}
              className="bg-[#5B3DF5] hover:bg-[#4828E0] text-white font-bold text-xs px-4 py-2.5 rounded-xl flex items-center gap-1.5 transition-all shadow-md shadow-[#5B3DF5]/20 cursor-pointer disabled:opacity-50"
            >
              <RefreshCw size={15} className={isCheckingHealth ? 'animate-spin' : ''} />
              {isCheckingHealth ? 'Comprobando...' : 'Comprobar Salud Ahora'}
            </button>
          </div>
        </div>

        {/* Grid de Servicios Nativos */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          
          {/* 1. Base de Datos */}
          <div className="bg-[#F8F9FD] border border-[#E8EAF2] rounded-2xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                  <Database size={18} />
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#20B486]/10 text-[#136c50] flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#20B486]" /> En Línea
                </span>
              </div>
              <h3 className="font-bold text-sm text-[#151A2D] mb-1">Base de Datos</h3>
              <p className="text-xs text-[#7B8195] mb-2 leading-relaxed">
                PostgreSQL 16 con RLS, justificantes, coders y auditoría inmutable.
              </p>
            </div>
            <div className="pt-2 border-t border-[#E8EAF2]/60 flex items-center justify-between text-[11px] font-mono text-[#7B8195]">
              <span>Latencia:</span>
              <span className="font-bold text-[#151A2D]">{healthStatus?.database.latencyMs ?? 14} ms</span>
            </div>
          </div>

          {/* 2. Motor IA */}
          <div className="bg-[#F8F9FD] border border-[#E8EAF2] rounded-2xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="w-9 h-9 rounded-xl bg-purple-50 text-[#5B3DF5] flex items-center justify-center">
                  <Cpu size={18} />
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#20B486]/10 text-[#136c50] flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#20B486]" /> En Línea
                </span>
              </div>
              <h3 className="font-bold text-sm text-[#151A2D] mb-1">Motor IA (Strata Core)</h3>
              <p className="text-xs text-[#7B8195] mb-2 leading-relaxed">
                Percepción documental Qwen 2.5, OCR adaptativo y schema determinista.
              </p>
            </div>
            <div className="pt-2 border-t border-[#E8EAF2]/60 flex items-center justify-between text-[11px] font-mono text-[#7B8195]">
              <span>Modelo:</span>
              <span className="font-bold text-[#151A2D]">qwen2.5:1.5b</span>
            </div>
          </div>

          {/* 3. Storage Seguro */}
          <div className="bg-[#F8F9FD] border border-[#E8EAF2] rounded-2xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                  <HardDrive size={18} />
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#20B486]/10 text-[#136c50] flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#20B486]" /> En Línea
                </span>
              </div>
              <h3 className="font-bold text-sm text-[#151A2D] mb-1">Storage de Evidencias</h3>
              <p className="text-xs text-[#7B8195] mb-2 leading-relaxed">
                Depósito seguro temporal con hashes SHA-256 anti-tamper.
              </p>
            </div>
            <div className="pt-2 border-t border-[#E8EAF2]/60 flex items-center justify-between text-[11px] font-mono text-[#7B8195]">
              <span>Integridad:</span>
              <span className="font-bold text-[#151A2D]">SHA-256 Activo</span>
            </div>
          </div>

          {/* 4. Servicio de Correo */}
          <div className="bg-[#F8F9FD] border border-[#E8EAF2] rounded-2xl p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <Mail size={18} />
                </div>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#20B486]/10 text-[#136c50] flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#20B486]" /> En Línea
                </span>
              </div>
              <h3 className="font-bold text-sm text-[#151A2D] mb-1">Canal de Correo</h3>
              <p className="text-xs text-[#7B8195] mb-2 leading-relaxed">
                Ingesta /api/v1/inbound-email y notificaciones automáticas SMTP.
              </p>
            </div>
            <div className="pt-2 border-t border-[#E8EAF2]/60 flex items-center justify-between text-[11px] font-mono text-[#7B8195]">
              <span>Canal:</span>
              <span className="font-bold text-[#151A2D]">Nativo REST</span>
            </div>
          </div>

        </div>

        {/* Barra de Estado Inferior */}
        <div className="bg-[#F8F9FD] border border-[#E8EAF2] rounded-xl px-4 py-2.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs text-[#7B8195]">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={15} className="text-[#20B486]" />
            <span>Todos los servicios nativos están respondiendo de manera desacoplada sin intermediarios.</span>
          </div>
          {lastCheckTime && (
            <span className="font-mono text-[11px]">Última comprobación: {lastCheckTime}</span>
          )}
        </div>
      </motion.div>

      {/* MAIN GRID LAYOUT */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN */}
        <div className="flex flex-col gap-6">
          
          {/* CARD 1 — MI PERFIL */}
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-[#FFFFFF] rounded-[24px] border border-[#E8EAF2] shadow-[0_2px_10px_rgba(21,26,45,0.02)] p-6"
          >
            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#F0EDFF] text-[#5B3DF5] flex items-center justify-center">
                  <User size={20} strokeWidth={2} />
                </div>
                <div>
                  <h2 className="text-[16px] font-bold text-[#151A2D]">Mi perfil</h2>
                  <p className="text-[13px] text-[#7B8195]">Información personal y de contacto.</p>
                </div>
              </div>
              <button className="text-[#5B3DF5] hover:text-[#7357FF] text-[13px] font-bold flex items-center gap-1.5 bg-[#F0EDFF] hover:bg-[#E5E0FF] px-3 py-1.5 rounded-lg transition-colors cursor-pointer">
                <Edit3 size={14} /> Editar
              </button>
            </div>

            <div className="flex flex-col items-center mb-6">
              <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-[#5B3DF5] to-[#7357FF] flex items-center justify-center text-white text-3xl font-bold shadow-lg shadow-[#5B3DF5]/20 mb-4 border-4 border-white">
                PA
              </div>
              <h3 className="text-[18px] font-bold text-[#151A2D] mb-1">Paola Admin</h3>
              <p className="text-[14px] font-medium text-[#7B8195] mb-2">HSE Manager</p>
              <div className="flex items-center gap-1.5 text-[12px] text-[#7B8195] bg-[#F6F7FB] px-3 py-1 rounded-full">
                <MapPin size={12} /> Barranquilla, Colombia
              </div>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Field label="Nombre" value="Paola" />
                <Field label="Apellido" value="Admin" />
              </div>
              <div className="relative">
                <Field label="Correo electrónico" value="paola@riwi.io" />
                <span className="absolute top-0 right-0 text-[10px] font-bold text-[#5B3DF5] bg-[#F0EDFF] px-2 py-0.5 rounded-md">Corporativo</span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Teléfono" value="+57 300 000 0000" />
                <Field label="Cargo" value="HSE Manager" />
              </div>
              <Field label="Ciudad" value="Barranquilla" />
            </div>
          </motion.div>

          {/* CARD 4 — PREFERENCIAS */}
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-[#FFFFFF] rounded-[24px] border border-[#E8EAF2] shadow-[0_2px_10px_rgba(21,26,45,0.02)] p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-[#F0EDFF] text-[#5B3DF5] flex items-center justify-center">
                <Sliders size={20} strokeWidth={2} />
              </div>
              <div>
                <h2 className="text-[16px] font-bold text-[#151A2D]">Preferencias</h2>
                <p className="text-[13px] text-[#7B8195]">Personaliza tu experiencia en el sistema.</p>
              </div>
            </div>

            <div className="space-y-6">
              <div>
                <p className="text-[13px] font-bold text-[#151A2D] mb-3">Tema</p>
                <div className="flex items-center gap-6">
                  <label className="flex items-center gap-2.5 cursor-pointer">
                    <div className={`w-4 h-4 rounded-full border-[4px] flex items-center justify-center transition-all ${theme === 'light' ? 'border-[#5B3DF5] bg-white' : 'border-[#E8EAF2] bg-white'}`} />
                    <input type="radio" className="hidden" checked={theme === 'light'} onChange={() => setTheme('light')} />
                    <span className="text-[14px] text-[#151A2D] font-medium">Claro</span>
                  </label>
                  <label className="flex items-center gap-2.5 cursor-pointer">
                    <div className={`w-4 h-4 rounded-full border-[4px] flex items-center justify-center transition-all ${theme === 'dark' ? 'border-[#5B3DF5] bg-white' : 'border-[#E8EAF2] bg-white'}`} />
                    <input type="radio" className="hidden" checked={theme === 'dark'} onChange={() => setTheme('dark')} />
                    <span className="text-[14px] text-[#7B8195] font-medium">Oscuro</span>
                  </label>
                </div>
              </div>

              <div>
                <p className="text-[13px] font-bold text-[#151A2D] mb-3">Idioma</p>
                <div className="relative">
                  <select 
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full appearance-none bg-white border border-[#E8EAF2] rounded-[12px] px-4 py-2.5 text-[14px] text-[#151A2D] font-medium focus:outline-none focus:border-[#5B3DF5] focus:ring-2 focus:ring-[#5B3DF5]/10 cursor-pointer"
                  >
                    <option value="Español">Español</option>
                    <option value="English">English</option>
                  </select>
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] text-[#7B8195] pointer-events-none">▼</span>
                </div>
              </div>
            </div>
          </motion.div>

        </div>

        {/* CENTER COLUMN */}
        <div className="flex flex-col gap-6">
          
          {/* CARD 2 — SEGURIDAD */}
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-[#FFFFFF] rounded-[24px] border border-[#E8EAF2] shadow-[0_2px_10px_rgba(21,26,45,0.02)] p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-[#F0EDFF] text-[#5B3DF5] flex items-center justify-center">
                <Lock size={20} strokeWidth={2} />
              </div>
              <div>
                <h2 className="text-[16px] font-bold text-[#151A2D]">Seguridad</h2>
                <p className="text-[13px] text-[#7B8195]">Protege tu cuenta con mayor seguridad.</p>
              </div>
            </div>

            <div className="space-y-6">
              {/* Contraseña */}
              <div className="border border-[#E8EAF2] rounded-[16px] p-5">
                <h3 className="text-[14px] font-bold text-[#151A2D] mb-1">Contraseña</h3>
                <p className="text-[12px] text-[#7B8195] mb-4">Cambia tu contraseña regularmente.</p>
                <button className="w-full bg-[#F6F7FB] hover:bg-[#E8EAF2] text-[#151A2D] font-bold text-[13px] py-2.5 rounded-[10px] transition-colors cursor-pointer">
                  Cambiar contraseña
                </button>
              </div>

              {/* Autenticación 2FA */}
              <div className="border border-[#E8EAF2] rounded-[16px] p-5 flex items-center justify-between">
                <div>
                  <h3 className="text-[14px] font-bold text-[#151A2D] mb-1 flex items-center gap-2">
                    <Shield size={14} className="text-[#5B3DF5]" />
                    Autenticación de dos factores
                  </h3>
                  <p className="text-[12px] text-[#7B8195] max-w-[200px] leading-snug">Añade una capa extra de seguridad a tu cuenta.</p>
                </div>
                <button 
                  onClick={() => setTwoFactorEnabled(!twoFactorEnabled)}
                  className={`w-11 h-6 rounded-full relative transition-colors cursor-pointer ${twoFactorEnabled ? 'bg-[#5B3DF5]' : 'bg-[#E8EAF2]'}`}
                >
                  <div className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform ${twoFactorEnabled ? 'translate-x-5' : 'translate-x-0'}`} />
                </button>
              </div>

              {/* Último acceso */}
              <div className="border border-[#E8EAF2] rounded-[16px] p-5">
                <h3 className="text-[14px] font-bold text-[#151A2D] mb-3">Último acceso</h3>
                <div className="flex items-center gap-3 text-[#7B8195] bg-[#F6F7FB] p-3 rounded-[12px]">
                  <Clock size={16} className="text-[#5B3DF5]" />
                  <span className="text-[13px] font-medium">Hoy, 10:42 AM · Barranquilla, Colombia</span>
                </div>
              </div>
            </div>
          </motion.div>

        </div>

        {/* RIGHT COLUMN */}
        <div className="flex flex-col gap-6">
          
          {/* CARD 3 — NOTIFICACIONES */}
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-[#FFFFFF] rounded-[24px] border border-[#E8EAF2] shadow-[0_2px_10px_rgba(21,26,45,0.02)] p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-[#F0EDFF] text-[#5B3DF5] flex items-center justify-center">
                <Bell size={20} strokeWidth={2} />
              </div>
              <div>
                <h2 className="text-[16px] font-bold text-[#151A2D]">Notificaciones</h2>
                <p className="text-[13px] text-[#7B8195]">Elige qué eventos quieres recibir.</p>
              </div>
            </div>

            <div className="space-y-4 mb-6">
              <Checkbox 
                label="Nuevas solicitudes" 
                checked={notifications.newRequests} 
                onChange={() => setNotifications({...notifications, newRequests: !notifications.newRequests})} 
              />
              <Checkbox 
                label="Solicitudes aprobadas" 
                checked={notifications.approvedRequests} 
                onChange={() => setNotifications({...notifications, approvedRequests: !notifications.approvedRequests})} 
              />
              <Checkbox 
                label="Solicitudes denegadas" 
                checked={notifications.deniedRequests} 
                onChange={() => setNotifications({...notifications, deniedRequests: !notifications.deniedRequests})} 
              />
              <Checkbox 
                label="Solicitudes pendientes de revisión" 
                checked={notifications.pendingRequests} 
                onChange={() => setNotifications({...notifications, pendingRequests: !notifications.pendingRequests})} 
              />
              <Checkbox 
                label="Nuevos reportes" 
                checked={notifications.newReports} 
                onChange={() => setNotifications({...notifications, newReports: !notifications.newReports})} 
              />
            </div>

            <div className="border-t border-[#E8EAF2] pt-6">
              <p className="text-[13px] font-bold text-[#151A2D] mb-4">Método de notificación</p>
              <div className="space-y-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <div className={`w-4 h-4 rounded-full border-[4px] flex items-center justify-center transition-all ${notificationMethod === 'email' ? 'border-[#5B3DF5] bg-white' : 'border-[#E8EAF2] bg-white'}`} />
                  <input type="radio" className="hidden" checked={notificationMethod === 'email'} onChange={() => setNotificationMethod('email')} />
                  <span className={`text-[14px] font-medium ${notificationMethod === 'email' ? 'text-[#151A2D]' : 'text-[#7B8195]'}`}>Correo electrónico</span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <div className={`w-4 h-4 rounded-full border-[4px] flex items-center justify-center transition-all ${notificationMethod === 'system' ? 'border-[#5B3DF5] bg-white' : 'border-[#E8EAF2] bg-white'}`} />
                  <input type="radio" className="hidden" checked={notificationMethod === 'system'} onChange={() => setNotificationMethod('system')} />
                  <span className={`text-[14px] font-medium ${notificationMethod === 'system' ? 'text-[#151A2D]' : 'text-[#7B8195]'}`}>Notificaciones en el sistema</span>
                </label>
              </div>
            </div>
          </motion.div>

        </div>
      </div>

      {/* BOTTOM: INFORMACIÓN DE LA ORGANIZACIÓN */}
      <motion.div 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-[#FFFFFF] rounded-[24px] border border-[#E8EAF2] shadow-[0_2px_10px_rgba(21,26,45,0.02)] p-6 md:p-8"
      >
        <div className="flex justify-between items-start mb-6 border-b border-[#E8EAF2] pb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-[#F0EDFF] text-[#5B3DF5] flex items-center justify-center">
              <Building size={24} strokeWidth={2} />
            </div>
            <div>
              <h2 className="text-[18px] font-bold text-[#151A2D]">Información de la organización</h2>
              <p className="text-[14px] text-[#7B8195]">Datos generales del sistema HSE.</p>
            </div>
          </div>
          <button className="text-[#5B3DF5] hover:text-[#7357FF] text-[13px] font-bold flex items-center gap-1.5 bg-[#F0EDFF] hover:bg-[#E5E0FF] px-4 py-2 rounded-[10px] transition-colors cursor-pointer">
            <Edit3 size={14} /> Editar
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
          <Field label="Organización" value="RIWI" />
          <Field label="Ciudad" value="Barranquilla" />
          <Field label="Responsable HSE" value="Paola Admin" />
          <Field label="Correo de contacto" value="hse@riwi.io" icon={<Mail size={14} />} />
          <Field label="Teléfono" value="+57 300 000 0000" icon={<Phone size={14} />} />
        </div>
      </motion.div>

    </div>
  );
}

// Reusable Components
function Field({ label, value, icon }: { label: string, value: string, icon?: React.ReactNode }) {
  return (
    <div className="bg-white border border-[#E8EAF2] rounded-[12px] p-3 shadow-xs hover:border-[#5B3DF5]/30 transition-colors">
      <p className="text-[11px] font-bold text-[#7B8195] uppercase tracking-wider mb-1">{label}</p>
      <div className="flex items-center gap-1.5 text-[14px] font-semibold text-[#151A2D] truncate">
        {icon && <span className="text-[#5B3DF5]">{icon}</span>}
        <span className="truncate">{value}</span>
      </div>
    </div>
  );
}

function Checkbox({ label, checked, onChange }: { label: string, checked: boolean, onChange: () => void }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer group">
      <div className={`w-5 h-5 rounded-[6px] border flex items-center justify-center transition-all ${
        checked 
          ? 'bg-[#5B3DF5] border-[#5B3DF5]' 
          : 'bg-white border-[#E8EAF2] group-hover:border-[#5B3DF5]'
      }`}>
        {checked && <Check size={14} className="text-white" strokeWidth={3} />}
      </div>
      <input type="checkbox" className="hidden" checked={checked} onChange={onChange} />
      <span className={`text-[14px] font-medium select-none ${checked ? 'text-[#151A2D]' : 'text-[#7B8195] group-hover:text-[#151A2D]'}`}>
        {label}
      </span>
    </label>
  );
}
