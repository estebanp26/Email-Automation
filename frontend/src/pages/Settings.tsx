import { useState, useEffect } from 'react';
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
  Zap,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Play,
  Save,
  Server
} from 'lucide-react';
import { 
  getN8nConfig, 
  saveN8nConfig, 
  testN8nConnection, 
  sendIncomingEmailSimulation,
  getDispatchWebhookUrl,
  getIncomingWebhookUrl,
  type N8nConfig
} from '../services/n8n';

export default function Settings() {
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

  // n8n Integration State
  const [n8nSettings, setN8nSettings] = useState<N8nConfig>(getN8nConfig());
  const [isTestingN8n, setIsTestingN8n] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; url?: string } | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulateResult, setSimulateResult] = useState<{ success: boolean; message: string } | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    setN8nSettings(getN8nConfig());
  }, []);

  const handleSaveN8n = () => {
    saveN8nConfig(n8nSettings);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const handleTestConnection = async () => {
    setIsTestingN8n(true);
    setTestResult(null);
    saveN8nConfig(n8nSettings);
    const res = await testN8nConnection();
    setTestResult(res);
    setIsTestingN8n(false);
  };

  const handleSimulateEmail = async () => {
    setIsSimulating(true);
    setSimulateResult(null);
    saveN8nConfig(n8nSettings);

    const res = await sendIncomingEmailSimulation({
      source_provider: 'OUTLOOK',
      sender_name: 'Santiago Morales',
      sender_email: 'santiago.morales@riwi.io',
      email_subject: 'Justificación médica - Incapacidad 2 días',
      email_body: 'Buenos días equipo HSE, adjunto constancia médica por cuadro viral desde hoy 28 de septiembre.',
      attachments: [{ filename: 'incapacidad_santiago.pdf', mime_type: 'application/pdf' }]
    });

    if (res.success) {
      setSimulateResult({
        success: true,
        message: '¡Correo simulado recibido correctamente por el Webhook de n8n!'
      });
    } else {
      setSimulateResult({
        success: false,
        message: res.error || 'No se pudo enviar el correo simulado al webhook.'
      });
    }
    setIsSimulating(false);
  };

  return (
    <div className="flex flex-col gap-8 pb-10">
      
      {/* TOP HEADER */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-[28px] font-bold text-[#151A2D]">Configuración</h1>
          <p className="text-[#7B8195] mt-1 text-sm">Administra tu cuenta, integraciones de n8n y seguridad.</p>
        </div>
        <div className="flex items-center gap-5">
          <span className="text-sm font-medium text-[#7B8195] hidden sm:block">Perfil de acciones <span className="ml-1 text-[10px]">▼</span></span>
          <div className="relative cursor-pointer hover:bg-gray-100 p-2 rounded-full transition-colors">
            <Bell size={20} className="text-[#7B8195]" />
            <span className="absolute top-1.5 right-2 w-2 h-2 bg-[#FF5C67] rounded-full border border-white" />
          </div>
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#5B3DF5] to-[#7357FF] flex items-center justify-center text-white font-bold shadow-md shadow-[#5B3DF5]/20 cursor-pointer">
            PA
          </div>
        </div>
      </div>

      {/* ================================================================ */}
      {/* CARD DESTACADA: CONEXIÓN N8N WORKFLOW                            */}
      {/* ================================================================ */}
      <motion.div 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-[24px] border-2 border-[#5B3DF5]/30 shadow-[0_4px_25px_rgba(91,61,245,0.06)] p-6 md:p-8"
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#E8EAF2] pb-6 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#5B3DF5] to-[#7357FF] text-white flex items-center justify-center shadow-md shadow-[#5B3DF5]/25">
              <Zap size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-[20px] font-bold text-[#151A2D]">Conexión con n8n Workflow</h2>
                <span className="text-[11px] font-bold uppercase tracking-wider bg-[#5B3DF5]/10 text-[#5B3DF5] px-2.5 py-0.5 rounded-full">
                  Workflow HSE
                </span>
              </div>
              <p className="text-[13px] text-[#7B8195]">
                Configura los endpoints de los webhooks para resolución manual y recepción de correos.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSaveN8n}
              className="bg-[#5B3DF5] hover:bg-[#4828E0] text-white font-bold text-xs px-4 py-2.5 rounded-xl flex items-center gap-1.5 transition-all shadow-md shadow-[#5B3DF5]/20 cursor-pointer"
            >
              {saveSuccess ? <Check size={16} /> : <Save size={16} />}
              {saveSuccess ? '¡Guardado!' : 'Guardar Configuración'}
            </button>
          </div>
        </div>

        {/* Inputs de configuración */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* URL Base */}
          <div className="lg:col-span-2 space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-[#7B8195] flex items-center gap-1.5">
              <Server size={14} /> URL Base de n8n
            </label>
            <input 
              type="text"
              value={n8nSettings.baseUrl}
              onChange={e => setN8nSettings({...n8nSettings, baseUrl: e.target.value})}
              placeholder="http://localhost:5678 o https://tu-instancia.app.n8n.cloud"
              className="w-full bg-[#F8F9FD] border border-[#E8EAF2] rounded-xl px-4 py-2.5 text-sm font-mono text-[#151A2D] focus:outline-none focus:border-[#5B3DF5]"
            />
            <p className="text-[11px] text-[#7B8195]">
              Normalmente <code>http://localhost:5678</code> cuando se ejecuta local o en Docker.
            </p>
          </div>

          {/* Selector de Modo Test / Prod */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-[#7B8195]">
              Modo de Ejecución del Webhook
            </label>
            <div className="flex rounded-xl bg-[#F8F9FD] p-1 border border-[#E8EAF2]">
              <button
                type="button"
                onClick={() => setN8nSettings({...n8nSettings, useTestWebhook: true})}
                className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  n8nSettings.useTestWebhook ? 'bg-white text-[#5B3DF5] shadow-xs' : 'text-[#7B8195] hover:text-[#151A2D]'
                }`}
              >
                Prueba (/webhook-test/)
              </button>
              <button
                type="button"
                onClick={() => setN8nSettings({...n8nSettings, useTestWebhook: false})}
                className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  !n8nSettings.useTestWebhook ? 'bg-white text-[#5B3DF5] shadow-xs' : 'text-[#7B8195] hover:text-[#151A2D]'
                }`}
              >
                Producción (/webhook/)
              </button>
            </div>
            <p className="text-[11px] text-[#7B8195]">
              {n8nSettings.useTestWebhook 
                ? 'Activo: Usa para probar paso a paso dando clic en "Listen for test event" en n8n.' 
                : 'Activo: Para workflows activos en ejecución permanente.'}
            </p>
          </div>
        </div>

        {/* URLs Calculadas */}
        <div className="bg-[#F8F9FD] border border-[#E8EAF2] rounded-2xl p-4 mb-6 space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-[#7B8195]">Rutas de Webhook enlazadas</p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="bg-white p-3 rounded-xl border border-[#E8EAF2]">
              <span className="font-bold text-[#111827] block mb-1">1. Despacho Manual HSE:</span>
              <code className="text-[#5B3DF5] font-mono text-[11px] break-all">
                {getDispatchWebhookUrl()}
              </code>
            </div>

            <div className="bg-white p-3 rounded-xl border border-[#E8EAF2]">
              <span className="font-bold text-[#111827] block mb-1">2. Ingesta de Correo:</span>
              <code className="text-[#20B486] font-mono text-[11px] break-all">
                {getIncomingWebhookUrl()}
              </code>
            </div>
          </div>
        </div>

        {/* Botones de Prueba y Simulación */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleTestConnection}
            disabled={isTestingN8n}
            className="bg-white border border-[#E8EAF2] hover:bg-[#F8F9FD] text-[#151A2D] font-bold text-xs px-4 py-2.5 rounded-xl flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50"
          >
            {isTestingN8n ? <RefreshCw size={14} className="animate-spin text-[#5B3DF5]" /> : <Zap size={14} className="text-[#5B3DF5]" />}
            Probar Conectividad con n8n
          </button>

          <button
            onClick={handleSimulateEmail}
            disabled={isSimulating}
            className="bg-white border border-[#E8EAF2] hover:bg-[#F8F9FD] text-[#151A2D] font-bold text-xs px-4 py-2.5 rounded-xl flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50"
          >
            {isSimulating ? <RefreshCw size={14} className="animate-spin text-[#20B486]" /> : <Play size={14} className="text-[#20B486]" />}
            Simular Envío de Correo Entrante
          </button>
        </div>

        {/* Mensaje de Resultado de Conexión */}
        {testResult && (
          <div className={`mt-4 p-4 rounded-xl text-xs border flex items-start gap-2.5 ${
            testResult.success ? 'bg-[#20B486]/10 border-[#20B486]/30 text-[#136c50]' : 'bg-[#FF5C67]/10 border-[#FF5C67]/30 text-[#9c242c]'
          }`}>
            {testResult.success ? <CheckCircle2 size={16} className="shrink-0 mt-0.5" /> : <AlertTriangle size={16} className="shrink-0 mt-0.5" />}
            <div>
              <p className="font-bold">{testResult.message}</p>
              {testResult.url && <p className="font-mono mt-1 opacity-80">{testResult.url}</p>}
            </div>
          </div>
        )}

        {/* Mensaje de Resultado de Simulación */}
        {simulateResult && (
          <div className={`mt-4 p-4 rounded-xl text-xs border flex items-start gap-2.5 ${
            simulateResult.success ? 'bg-[#20B486]/10 border-[#20B486]/30 text-[#136c50]' : 'bg-[#FF5C67]/10 border-[#FF5C67]/30 text-[#9c242c]'
          }`}>
            {simulateResult.success ? <CheckCircle2 size={16} className="shrink-0 mt-0.5" /> : <AlertTriangle size={16} className="shrink-0 mt-0.5" />}
            <div>
              <p className="font-bold">{simulateResult.message}</p>
            </div>
          </div>
        )}
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
                <p className="text-[13px] font-bold text-[#151A2D] mb-2">Idioma</p>
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
