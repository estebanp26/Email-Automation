import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Bell, 
  User, 
  Lock, 
  Shield, 
  Building, 
  MapPin, 
  Phone, 
  Mail, 
  Edit3, 
  Check,
  Settings as SettingsIcon,
  LogOut,
  Plus,
  Trash2,
  Save,
  X,
  SlidersHorizontal,
  CheckCircle2,
  KeyRound
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface NotificationsConfig {
  newRequests: boolean;
  approvedRequests: boolean;
  deniedRequests: boolean;
  pendingRequests: boolean;
  newReports: boolean;
}

interface SystemRule {
  id: string;
  name: string;
  value: string;
  category: string;
  description: string;
}

export default function Settings() {
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const navigate = useNavigate();
  const { logout } = useAuth();

  // Toast feedback state
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // 1. Profile State
  const [profile, setProfile] = useState(() => {
    const saved = localStorage.getItem('hse_user_profile');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return {
      firstName: 'Paola',
      lastName: 'Admin',
      email: 'paola@riwi.io',
      phone: '+57 300 000 0000',
      role: 'HSE Manager',
      city: 'Barranquilla'
    };
  });
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [profileDraft, setProfileDraft] = useState(profile);

  // 2. Organization Info State
  const [orgInfo, setOrgInfo] = useState(() => {
    const saved = localStorage.getItem('hse_org_info');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return {
      organization: 'RIWI',
      city: 'Barranquilla',
      manager: 'Paola Admin',
      contactEmail: 'hse@riwi.io',
      phone: '+57 300 000 0000'
    };
  });
  const [isEditingOrg, setIsEditingOrg] = useState(false);
  const [orgDraft, setOrgDraft] = useState(orgInfo);

  // 3. Security state
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(() => {
    return localStorage.getItem('hse_2fa_enabled') === 'true';
  });
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordData, setPasswordData] = useState({ current: '', newPass: '', confirm: '' });

  // 4. Notifications state
  const [notifications, setNotifications] = useState<NotificationsConfig>(() => {
    const saved = localStorage.getItem('hse_notifications_config');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return {
      newRequests: true,
      approvedRequests: true,
      deniedRequests: false,
      pendingRequests: true,
      newReports: false
    };
  });

  // 5. Alert Emails (Add / Modify / Remove)
  const [alertEmails, setAlertEmails] = useState<string[]>(() => {
    const saved = localStorage.getItem('hse_alert_emails');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return ['bienestar@riwi.io', 'coordinacion.baq@riwi.io'];
  });
  const [newAlertEmail, setNewAlertEmail] = useState('');

  // 6. Dynamic HSE System Rules (Add / Modify / Remove)
  const [rules, setRules] = useState<SystemRule[]>(() => {
    const saved = localStorage.getItem('hse_system_rules');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return [
      {
        id: 'rule-1',
        name: 'Tolerancia de Retraso',
        value: '15 minutos',
        category: 'Asistencia',
        description: 'Margen de gracia biométrica antes de marcar falta o retraso.'
      },
      {
        id: 'rule-2',
        name: 'Plazo Radicación Excusas',
        value: '3 días hábiles',
        category: 'Justificaciones',
        description: 'Tiempo máximo para adjuntar certificado médico en el portal.'
      },
      {
        id: 'rule-3',
        name: 'Umbral Mínimo Requerido',
        value: '85% asistencia',
        category: 'Cumplimiento',
        description: 'Porcentaje mínimo de presencialidad para certificación.'
      },
      {
        id: 'rule-4',
        name: 'Filtro IA Pre-Aprobación EPS',
        value: 'Activo (Sura/Sanitas)',
        category: 'Automatización',
        description: 'Clasificación semántica automática de incapacidades médicas.'
      }
    ];
  });

  // Modal / Form state for Rule (Add / Edit)
  const [showRuleModal, setShowRuleModal] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);
  const [ruleForm, setRuleForm] = useState({ name: '', value: '', category: 'Asistencia', description: '' });

  // Persistence effects
  useEffect(() => {
    localStorage.setItem('hse_user_profile', JSON.stringify(profile));
  }, [profile]);

  useEffect(() => {
    localStorage.setItem('hse_org_info', JSON.stringify(orgInfo));
  }, [orgInfo]);

  useEffect(() => {
    localStorage.setItem('hse_2fa_enabled', String(twoFactorEnabled));
  }, [twoFactorEnabled]);

  useEffect(() => {
    localStorage.setItem('hse_notifications_config', JSON.stringify(notifications));
  }, [notifications]);

  useEffect(() => {
    localStorage.setItem('hse_alert_emails', JSON.stringify(alertEmails));
  }, [alertEmails]);

  useEffect(() => {
    localStorage.setItem('hse_system_rules', JSON.stringify(rules));
  }, [rules]);

  // Handlers for Profile
  const handleSaveProfile = () => {
    setProfile(profileDraft);
    setIsEditingProfile(false);
    showToast('Perfil actualizado correctamente');
  };

  // Handlers for Org Info
  const handleSaveOrg = () => {
    setOrgInfo(orgDraft);
    setIsEditingOrg(false);
    showToast('Información institucional actualizada');
  };

  // Handlers for Rules (Add / Modify / Remove)
  const handleOpenAddRule = () => {
    setEditingRuleId(null);
    setRuleForm({ name: '', value: '', category: 'Asistencia', description: '' });
    setShowRuleModal(true);
  };

  const handleOpenEditRule = (rule: SystemRule) => {
    setEditingRuleId(rule.id);
    setRuleForm({
      name: rule.name,
      value: rule.value,
      category: rule.category,
      description: rule.description
    });
    setShowRuleModal(true);
  };

  const handleSaveRule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleForm.name.trim() || !ruleForm.value.trim()) return;

    if (editingRuleId) {
      setRules(prev => prev.map(r => r.id === editingRuleId ? {
        ...r,
        name: ruleForm.name.trim(),
        value: ruleForm.value.trim(),
        category: ruleForm.category,
        description: ruleForm.description.trim()
      } : r));
      showToast('Parámetro modificado exitosamente');
    } else {
      const newRule: SystemRule = {
        id: `rule-${Date.now()}`,
        name: ruleForm.name.trim(),
        value: ruleForm.value.trim(),
        category: ruleForm.category,
        description: ruleForm.description.trim()
      };
      setRules(prev => [...prev, newRule]);
      showToast('Nuevo parámetro agregado');
    }
    setShowRuleModal(false);
  };

  const handleDeleteRule = (id: string, name: string) => {
    setRules(prev => prev.filter(r => r.id !== id));
    showToast(`Regla "${name}" eliminada`);
  };

  // Handlers for Alert Emails (Add / Remove)
  const handleAddAlertEmail = (e: React.FormEvent) => {
    e.preventDefault();
    const email = newAlertEmail.trim().toLowerCase();
    if (!email || !email.includes('@')) return;
    if (alertEmails.includes(email)) {
      showToast('Este correo ya está en la lista');
      return;
    }
    setAlertEmails(prev => [...prev, email]);
    setNewAlertEmail('');
    showToast('Canal de notificación agregado');
  };

  const handleRemoveAlertEmail = (emailToRemove: string) => {
    setAlertEmails(prev => prev.filter(e => e !== emailToRemove));
    showToast('Canal de notificación eliminado');
  };

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault();
    if (!passwordData.current || !passwordData.newPass) {
      showToast('Diligencia los campos obligatorios');
      return;
    }
    if (passwordData.newPass !== passwordData.confirm) {
      showToast('Las contraseñas no coinciden');
      return;
    }
    setShowPasswordModal(false);
    setPasswordData({ current: '', newPass: '', confirm: '' });
    showToast('Contraseña actualizada con éxito');
  };

  return (
    <div className="flex flex-col gap-6 pb-12 relative">
      
      {/* TOAST FLOTANTE */}
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

      {/* TOP HEADER */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-[28px] font-bold text-[#151A2D]">Configuración HSE</h1>
          <p className="text-[#7B8195] mt-1 text-sm">
            Administra perfil, reglas de asistencia, seguridad y canales de alerta del sistema.
          </p>
        </div>
        
        <div className="flex items-center gap-3 self-end sm:self-auto relative">
          <div 
            className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#5B3DF5] to-[#7357FF] flex items-center justify-center text-white font-bold shadow-md shadow-[#5B3DF5]/20 cursor-pointer select-none"
            onClick={() => setShowProfileMenu(!showProfileMenu)}
          >
            PA
          </div>
          {showProfileMenu && (
            <div className="absolute top-12 right-0 w-48 bg-white rounded-xl shadow-lg border border-gray-100 py-2 z-50">
              <button 
                onClick={() => navigate('/requests')} 
                className="w-full text-left px-4 py-2 text-sm text-[#11132C] hover:bg-gray-50 flex items-center gap-3 transition-colors cursor-pointer"
              >
                <Bell size={16} className="text-[#7C8499]" />
                Bandeja de Solicitudes
              </button>
              <button 
                onClick={() => navigate('/settings')} 
                className="w-full text-left px-4 py-2 text-sm text-[#11132C] hover:bg-gray-50 flex items-center gap-3 transition-colors cursor-pointer"
              >
                <SettingsIcon size={16} className="text-[#7C8499]" />
                Configuración
              </button>
              <button 
                onClick={() => { logout(); navigate('/login', { replace: true }); }} 
                className="w-full text-left px-4 py-2 text-sm text-[#FF5C67] hover:bg-red-50 flex items-center gap-3 transition-colors cursor-pointer"
              >
                <LogOut size={16} className="text-[#FF5C67]" />
                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </div>

      {/* BALANCED 2-COLUMN GRID (Sin huecos, diseño armónico y fluido) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        
        {/* COLUMNA IZQUIERDA */}
        <div className="flex flex-col gap-6">
          
          {/* CARD 1 — MI PERFIL (Funcional y Editable) */}
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-[24px] border border-[#E8EAF2] shadow-[0_2px_10px_rgba(21,26,45,0.02)] p-6"
          >
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#F0EDFF] text-[#5B3DF5] flex items-center justify-center">
                  <User size={20} strokeWidth={2} />
                </div>
                <div>
                  <h2 className="text-[17px] font-bold text-[#151A2D]">Mi Perfil HSE</h2>
                  <p className="text-[13px] text-[#7B8195]">Información de la cuenta y contacto oficial.</p>
                </div>
              </div>
              
              {!isEditingProfile ? (
                <button 
                  onClick={() => { setProfileDraft(profile); setIsEditingProfile(true); }}
                  className="text-[#5B3DF5] hover:text-[#7357FF] text-[13px] font-bold flex items-center gap-1.5 bg-[#F0EDFF] hover:bg-[#E5E0FF] px-3.5 py-1.5 rounded-xl transition-colors cursor-pointer"
                >
                  <Edit3 size={14} /> Editar
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <button 
                    onClick={() => setIsEditingProfile(false)}
                    className="text-[#7B8195] hover:text-[#151A2D] text-[12px] font-semibold px-2.5 py-1.5 rounded-lg border border-gray-200 cursor-pointer"
                  >
                    Cancelar
                  </button>
                  <button 
                    onClick={handleSaveProfile}
                    className="text-white text-[12px] font-bold flex items-center gap-1 bg-[#5B3DF5] hover:bg-[#4a32cc] px-3 py-1.5 rounded-lg shadow-sm cursor-pointer"
                  >
                    <Save size={13} /> Guardar
                  </button>
                </div>
              )}
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-5 mb-6 p-4 rounded-2xl bg-[#F8F9FE] border border-[#E8EAF2]">
              <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-[#5B3DF5] to-[#7357FF] flex items-center justify-center text-white text-2xl font-bold shadow-md shadow-[#5B3DF5]/20 border-4 border-white shrink-0">
                {profile.firstName[0]}{profile.lastName[0]}
              </div>
              <div className="text-center sm:text-left flex-1 min-w-0">
                <h3 className="text-[18px] font-bold text-[#151A2D] leading-tight truncate">
                  {profile.firstName} {profile.lastName}
                </h3>
                <p className="text-[14px] font-semibold text-[#5B3DF5] mt-0.5">{profile.role}</p>
                <div className="flex items-center justify-center sm:justify-start gap-1.5 text-[12px] text-[#7B8195] mt-1.5">
                  <MapPin size={13} className="text-[#5B3DF5]" /> {profile.city}, Colombia · Sede Principal
                </div>
              </div>
            </div>

            {/* Inputs / Fields */}
            {!isEditingProfile ? (
              <div className="space-y-3.5">
                <div className="grid grid-cols-2 gap-3.5">
                  <Field label="Nombre" value={profile.firstName} />
                  <Field label="Apellido" value={profile.lastName} />
                </div>
                <div className="relative">
                  <Field label="Correo electrónico" value={profile.email} icon={<Mail size={14} />} />
                  <span className="absolute top-2.5 right-3 text-[10px] font-bold text-[#5B3DF5] bg-[#F0EDFF] px-2 py-0.5 rounded-md">
                    Corporativo
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3.5">
                  <Field label="Teléfono" value={profile.phone} icon={<Phone size={14} />} />
                  <Field label="Cargo" value={profile.role} />
                </div>
              </div>
            ) : (
              <div className="space-y-3.5">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] font-bold text-[#7B8195] uppercase">Nombre</label>
                    <input 
                      type="text" 
                      value={profileDraft.firstName}
                      onChange={e => setProfileDraft({...profileDraft, firstName: e.target.value})}
                      className="w-full mt-1 px-3 py-2 border border-[#E8EAF2] rounded-xl text-sm font-medium focus:border-[#5B3DF5] focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-bold text-[#7B8195] uppercase">Apellido</label>
                    <input 
                      type="text" 
                      value={profileDraft.lastName}
                      onChange={e => setProfileDraft({...profileDraft, lastName: e.target.value})}
                      className="w-full mt-1 px-3 py-2 border border-[#E8EAF2] rounded-xl text-sm font-medium focus:border-[#5B3DF5] focus:outline-none"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-[11px] font-bold text-[#7B8195] uppercase">Correo Electrónico</label>
                  <input 
                    type="email" 
                    value={profileDraft.email}
                    onChange={e => setProfileDraft({...profileDraft, email: e.target.value})}
                    className="w-full mt-1 px-3 py-2 border border-[#E8EAF2] rounded-xl text-sm font-medium focus:border-[#5B3DF5] focus:outline-none"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] font-bold text-[#7B8195] uppercase">Teléfono</label>
                    <input 
                      type="text" 
                      value={profileDraft.phone}
                      onChange={e => setProfileDraft({...profileDraft, phone: e.target.value})}
                      className="w-full mt-1 px-3 py-2 border border-[#E8EAF2] rounded-xl text-sm font-medium focus:border-[#5B3DF5] focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-bold text-[#7B8195] uppercase">Cargo</label>
                    <input 
                      type="text" 
                      value={profileDraft.role}
                      onChange={e => setProfileDraft({...profileDraft, role: e.target.value})}
                      className="w-full mt-1 px-3 py-2 border border-[#E8EAF2] rounded-xl text-sm font-medium focus:border-[#5B3DF5] focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            )}
          </motion.div>

          {/* CARD 2 — PARÁMETROS Y REGLAS HSE (Funcional: Agregar, Modificar, Quitar) */}
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-[24px] border border-[#E8EAF2] shadow-[0_2px_10px_rgba(21,26,45,0.02)] p-6"
          >
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#F0EDFF] text-[#5B3DF5] flex items-center justify-center">
                  <SlidersHorizontal size={20} strokeWidth={2} />
                </div>
                <div>
                  <h2 className="text-[17px] font-bold text-[#151A2D]">Reglas y Parámetros HSE</h2>
                  <p className="text-[13px] text-[#7B8195]">Criterios institucionales y tolerancias activas.</p>
                </div>
              </div>
              
              <button 
                onClick={handleOpenAddRule}
                className="text-white text-[13px] font-bold flex items-center gap-1.5 bg-[#5B3DF5] hover:bg-[#4a32cc] px-3.5 py-1.5 rounded-xl transition-all shadow-md shadow-[#5B3DF5]/20 cursor-pointer"
              >
                <Plus size={15} /> Agregar Regla
              </button>
            </div>

            <div className="space-y-3">
              {rules.map((rule) => (
                <div 
                  key={rule.id}
                  className="p-4 rounded-2xl border border-[#E8EAF2] hover:border-[#5B3DF5]/30 transition-all bg-[#FBFBFE] group flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded-md bg-[#F0EDFF] text-[#5B3DF5]">
                        {rule.category}
                      </span>
                      <h4 className="text-[14px] font-bold text-[#151A2D] truncate">{rule.name}</h4>
                    </div>
                    <p className="text-[12px] text-[#7B8195] line-clamp-1">{rule.description}</p>
                    <div className="mt-1 text-[13px] font-extrabold text-[#11132C]">
                      Valor: <span className="text-[#5B3DF5] font-mono">{rule.value}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                    <button 
                      onClick={() => handleOpenEditRule(rule)}
                      className="p-2 text-[#7B8195] hover:text-[#5B3DF5] hover:bg-white rounded-lg border border-transparent hover:border-gray-200 transition-colors cursor-pointer"
                      title="Modificar parámetro"
                    >
                      <Edit3 size={15} />
                    </button>
                    <button 
                      onClick={() => handleDeleteRule(rule.id, rule.name)}
                      className="p-2 text-[#7B8195] hover:text-[#FF5C67] hover:bg-red-50 rounded-lg border border-transparent hover:border-red-100 transition-colors cursor-pointer"
                      title="Quitar regla"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

        </div>

        {/* COLUMNA DERECHA */}
        <div className="flex flex-col gap-6">
          
          {/* CARD 3 — SEGURIDAD & ACCESO */}
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-[24px] border border-[#E8EAF2] shadow-[0_2px_10px_rgba(21,26,45,0.02)] p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-[#F0EDFF] text-[#5B3DF5] flex items-center justify-center">
                <Lock size={20} strokeWidth={2} />
              </div>
              <div>
                <h2 className="text-[17px] font-bold text-[#151A2D]">Seguridad y Autenticación</h2>
                <p className="text-[13px] text-[#7B8195]">Protección de cuenta y controles de acceso.</p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Contraseña */}
              <div className="border border-[#E8EAF2] rounded-[18px] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white">
                <div>
                  <h3 className="text-[14px] font-bold text-[#151A2D] flex items-center gap-2">
                    <KeyRound size={15} className="text-[#5B3DF5]" />
                    Contraseña de Acceso
                  </h3>
                  <p className="text-[12px] text-[#7B8195] mt-0.5">Último cambio realizado hace 14 días.</p>
                </div>
                <button 
                  onClick={() => setShowPasswordModal(true)}
                  className="bg-[#F6F7FB] hover:bg-[#E8EAF2] text-[#151A2D] font-bold text-[13px] px-4 py-2 rounded-xl transition-colors cursor-pointer shrink-0"
                >
                  Cambiar Contraseña
                </button>
              </div>

              {/* 2FA Switch */}
              <div className="border border-[#E8EAF2] rounded-[18px] p-4 flex items-center justify-between bg-white">
                <div>
                  <h3 className="text-[14px] font-bold text-[#151A2D] flex items-center gap-2">
                    <Shield size={15} className={twoFactorEnabled ? "text-[#20B486]" : "text-[#5B3DF5]"} />
                    Autenticación en Dos Pasos (2FA)
                  </h3>
                  <p className="text-[12px] text-[#7B8195] mt-0.5">
                    {twoFactorEnabled ? 'Protección activa mediante código de verificación.' : 'Añade una capa extra de seguridad para tu rol HSE.'}
                  </p>
                </div>
                <button 
                  onClick={() => {
                    const next = !twoFactorEnabled;
                    setTwoFactorEnabled(next);
                    showToast(next ? '2FA activado correctamente' : '2FA desactivado');
                  }}
                  className={`w-12 h-7 rounded-full relative transition-colors cursor-pointer shrink-0 ${twoFactorEnabled ? 'bg-[#20B486]' : 'bg-[#E8EAF2]'}`}
                >
                  <div className={`absolute top-1 left-1 w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${twoFactorEnabled ? 'translate-x-5' : 'translate-x-0'}`} />
                </button>
              </div>

              {/* Sesión actual */}
              <div className="border border-[#E8EAF2] rounded-[18px] p-4 bg-[#F8F9FE]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold text-xs">
                      OK
                    </div>
                    <div>
                      <p className="text-[13px] font-bold text-[#151A2D]">Sesión Actual Segura</p>
                      <p className="text-[11px] text-[#7B8195]">Token JWT vigente · Barranquilla, Colombia</p>
                    </div>
                  </div>
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                    Activa
                  </span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* CARD 4 — CANALES DE NOTIFICACIÓN Y ALERTAS (Funcional: Agregar / Quitar correos) */}
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white rounded-[24px] border border-[#E8EAF2] shadow-[0_2px_10px_rgba(21,26,45,0.02)] p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-[#F0EDFF] text-[#5B3DF5] flex items-center justify-center">
                <Bell size={20} strokeWidth={2} />
              </div>
              <div>
                <h2 className="text-[17px] font-bold text-[#151A2D]">Notificaciones y Canales</h2>
                <p className="text-[13px] text-[#7B8195]">Configura eventos a alertar y destinatarios.</p>
              </div>
            </div>

            {/* Checkboxes de Eventos */}
            <div className="space-y-3 mb-6">
              <Checkbox 
                label="Nuevas solicitudes radicadas por Coders" 
                checked={notifications.newRequests} 
                onChange={() => {
                  setNotifications(prev => ({ ...prev, newRequests: !prev.newRequests }));
                  showToast('Preferencia guardada');
                }} 
              />
              <Checkbox 
                label="Alertas de inasistencias críticas (> 3 faltas)" 
                checked={notifications.approvedRequests} 
                onChange={() => {
                  setNotifications(prev => ({ ...prev, approvedRequests: !prev.approvedRequests }));
                  showToast('Preferencia guardada');
                }} 
              />
              <Checkbox 
                label="Solicitudes pendientes de revisión Team Leader" 
                checked={notifications.pendingRequests} 
                onChange={() => {
                  setNotifications(prev => ({ ...prev, pendingRequests: !prev.pendingRequests }));
                  showToast('Preferencia guardada');
                }} 
              />
            </div>

            {/* Sección: Correos de Alerta HSE (Agregar / Quitar) */}
            <div className="border-t border-[#E8EAF2] pt-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-[13px] font-bold text-[#151A2D]">Canales y Correos Autorizados</h3>
                <span className="text-[11px] font-semibold text-[#7B8195]">{alertEmails.length} activos</span>
              </div>

              {/* Formulario para agregar correo */}
              <form onSubmit={handleAddAlertEmail} className="flex gap-2 mb-3">
                <input 
                  type="email"
                  placeholder="ejemplo@riwi.io"
                  value={newAlertEmail}
                  onChange={e => setNewAlertEmail(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-xs bg-white border border-[#E8EAF2] rounded-xl focus:border-[#5B3DF5] focus:outline-none"
                />
                <button
                  type="submit"
                  className="bg-[#5B3DF5] hover:bg-[#4a32cc] text-white px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1 shadow-sm cursor-pointer shrink-0"
                >
                  <Plus size={14} /> Agregar
                </button>
              </form>

              {/* Lista de correos con botón quitar */}
              <div className="space-y-2">
                {alertEmails.map(email => (
                  <div 
                    key={email}
                    className="flex items-center justify-between p-2.5 rounded-xl bg-[#F8F9FE] border border-[#E8EAF2] text-xs"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <Mail size={13} className="text-[#5B3DF5] shrink-0" />
                      <span className="font-semibold text-[#151A2D] truncate">{email}</span>
                    </div>
                    <button
                      onClick={() => handleRemoveAlertEmail(email)}
                      className="text-[#7B8195] hover:text-red-500 p-1 transition-colors cursor-pointer"
                      title="Quitar correo"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

        </div>
      </div>

      {/* FILA INFERIOR — INFORMACIÓN DE LA ORGANIZACIÓN (RIWI) */}
      <motion.div 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-white rounded-[24px] border border-[#E8EAF2] shadow-[0_2px_10px_rgba(21,26,45,0.02)] p-6 md:p-8"
      >
        <div className="flex justify-between items-start mb-6 border-b border-[#E8EAF2] pb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-[#F0EDFF] text-[#5B3DF5] flex items-center justify-center">
              <Building size={24} strokeWidth={2} />
            </div>
            <div>
              <h2 className="text-[18px] font-bold text-[#151A2D]">Información Institucional RIWI</h2>
              <p className="text-[14px] text-[#7B8195]">Datos generales de la sede y coordinación HSE.</p>
            </div>
          </div>

          {!isEditingOrg ? (
            <button 
              onClick={() => { setOrgDraft(orgInfo); setIsEditingOrg(true); }}
              className="text-[#5B3DF5] hover:text-[#7357FF] text-[13px] font-bold flex items-center gap-1.5 bg-[#F0EDFF] hover:bg-[#E5E0FF] px-4 py-2 rounded-xl transition-colors cursor-pointer"
            >
              <Edit3 size={14} /> Editar Datos
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setIsEditingOrg(false)}
                className="text-[#7B8195] hover:text-[#151A2D] text-[12px] font-semibold px-3 py-1.5 rounded-lg border border-gray-200 cursor-pointer"
              >
                Cancelar
              </button>
              <button 
                onClick={handleSaveOrg}
                className="text-white text-[12px] font-bold flex items-center gap-1.5 bg-[#5B3DF5] hover:bg-[#4a32cc] px-4 py-1.5 rounded-lg shadow-sm cursor-pointer"
              >
                <Save size={13} /> Guardar
              </button>
            </div>
          )}
        </div>

        {!isEditingOrg ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <Field label="Organización" value={orgInfo.organization} />
            <Field label="Sede / Ciudad" value={orgInfo.city} />
            <Field label="Responsable HSE" value={orgInfo.manager} />
            <Field label="Correo de contacto" value={orgInfo.contactEmail} icon={<Mail size={14} />} />
            <Field label="Teléfono" value={orgInfo.phone} icon={<Phone size={14} />} />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <div>
              <label className="text-[11px] font-bold text-[#7B8195] uppercase">Organización</label>
              <input 
                type="text" 
                value={orgDraft.organization}
                onChange={e => setOrgDraft({...orgDraft, organization: e.target.value})}
                className="w-full mt-1 px-3 py-2 border border-[#E8EAF2] rounded-xl text-xs font-semibold focus:border-[#5B3DF5] focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[11px] font-bold text-[#7B8195] uppercase">Sede / Ciudad</label>
              <input 
                type="text" 
                value={orgDraft.city}
                onChange={e => setOrgDraft({...orgDraft, city: e.target.value})}
                className="w-full mt-1 px-3 py-2 border border-[#E8EAF2] rounded-xl text-xs font-semibold focus:border-[#5B3DF5] focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[11px] font-bold text-[#7B8195] uppercase">Responsable HSE</label>
              <input 
                type="text" 
                value={orgDraft.manager}
                onChange={e => setOrgDraft({...orgDraft, manager: e.target.value})}
                className="w-full mt-1 px-3 py-2 border border-[#E8EAF2] rounded-xl text-xs font-semibold focus:border-[#5B3DF5] focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[11px] font-bold text-[#7B8195] uppercase">Correo Institucional</label>
              <input 
                type="email" 
                value={orgDraft.contactEmail}
                onChange={e => setOrgDraft({...orgDraft, contactEmail: e.target.value})}
                className="w-full mt-1 px-3 py-2 border border-[#E8EAF2] rounded-xl text-xs font-semibold focus:border-[#5B3DF5] focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[11px] font-bold text-[#7B8195] uppercase">Teléfono</label>
              <input 
                type="text" 
                value={orgDraft.phone}
                onChange={e => setOrgDraft({...orgDraft, phone: e.target.value})}
                className="w-full mt-1 px-3 py-2 border border-[#E8EAF2] rounded-xl text-xs font-semibold focus:border-[#5B3DF5] focus:outline-none"
              />
            </div>
          </div>
        )}
      </motion.div>

      {/* MODAL PARA AGREGAR / MODIFICAR REGLAS */}
      <AnimatePresence>
        {showRuleModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl border border-gray-100"
            >
              <div className="flex justify-between items-center mb-5">
                <h3 className="text-lg font-bold text-[#11132C]">
                  {editingRuleId ? 'Modificar Parámetro HSE' : 'Nuevo Parámetro del Sistema'}
                </h3>
                <button 
                  onClick={() => setShowRuleModal(false)}
                  className="p-1 text-gray-400 hover:text-gray-700 transition-colors cursor-pointer"
                >
                  <X size={20} />
                </button>
              </div>

              <form onSubmit={handleSaveRule} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">Nombre del Parámetro</label>
                  <input 
                    type="text" 
                    required
                    placeholder="Ej: Tolerancia de retraso"
                    value={ruleForm.name}
                    onChange={e => setRuleForm({ ...ruleForm, name: e.target.value })}
                    className="w-full px-3.5 py-2.5 border border-[#E8EAF2] rounded-xl text-sm focus:border-[#5B3DF5] focus:outline-none font-medium"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">Valor / Límite</label>
                    <input 
                      type="text" 
                      required
                      placeholder="Ej: 20 min"
                      value={ruleForm.value}
                      onChange={e => setRuleForm({ ...ruleForm, value: e.target.value })}
                      className="w-full px-3.5 py-2.5 border border-[#E8EAF2] rounded-xl text-sm focus:border-[#5B3DF5] focus:outline-none font-semibold text-[#5B3DF5]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">Categoría</label>
                    <select 
                      value={ruleForm.category}
                      onChange={e => setRuleForm({ ...ruleForm, category: e.target.value })}
                      className="w-full px-3 py-2.5 border border-[#E8EAF2] rounded-xl text-sm focus:border-[#5B3DF5] focus:outline-none font-medium bg-white"
                    >
                      <option value="Asistencia">Asistencia</option>
                      <option value="Justificaciones">Justificaciones</option>
                      <option value="Cumplimiento">Cumplimiento</option>
                      <option value="Automatización">Automatización</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">Descripción / Propósito</label>
                  <textarea 
                    rows={3}
                    placeholder="Explica cómo aplica este criterio institucional..."
                    value={ruleForm.description}
                    onChange={e => setRuleForm({ ...ruleForm, description: e.target.value })}
                    className="w-full px-3.5 py-2 border border-[#E8EAF2] rounded-xl text-sm focus:border-[#5B3DF5] focus:outline-none resize-none font-normal"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={() => setShowRuleModal(false)}
                    className="px-4 py-2 text-sm font-semibold text-gray-500 hover:text-gray-800 cursor-pointer"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 bg-[#5B3DF5] hover:bg-[#4a32cc] text-white rounded-xl text-sm font-bold shadow-md shadow-[#5B3DF5]/20 cursor-pointer"
                  >
                    {editingRuleId ? 'Guardar Cambios' : 'Crear Parámetro'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL PARA CAMBIO DE CONTRASEÑA */}
      <AnimatePresence>
        {showPasswordModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-3xl p-6 sm:p-8 max-w-sm w-full shadow-2xl border border-gray-100"
            >
              <div className="flex justify-between items-center mb-5">
                <h3 className="text-lg font-bold text-[#11132C]">Cambiar Contraseña</h3>
                <button 
                  onClick={() => setShowPasswordModal(false)}
                  className="p-1 text-gray-400 hover:text-gray-700 transition-colors cursor-pointer"
                >
                  <X size={20} />
                </button>
              </div>

              <form onSubmit={handleChangePassword} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">Contraseña Actual</label>
                  <input 
                    type="password"
                    required
                    value={passwordData.current}
                    onChange={e => setPasswordData({ ...passwordData, current: e.target.value })}
                    className="w-full px-3.5 py-2 border border-[#E8EAF2] rounded-xl text-sm focus:border-[#5B3DF5] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">Nueva Contraseña</label>
                  <input 
                    type="password"
                    required
                    value={passwordData.newPass}
                    onChange={e => setPasswordData({ ...passwordData, newPass: e.target.value })}
                    className="w-full px-3.5 py-2 border border-[#E8EAF2] rounded-xl text-sm focus:border-[#5B3DF5] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-[#7B8195] uppercase mb-1">Confirmar Nueva Contraseña</label>
                  <input 
                    type="password"
                    required
                    value={passwordData.confirm}
                    onChange={e => setPasswordData({ ...passwordData, confirm: e.target.value })}
                    className="w-full px-3.5 py-2 border border-[#E8EAF2] rounded-xl text-sm focus:border-[#5B3DF5] focus:outline-none"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
                  <button
                    type="button"
                    onClick={() => setShowPasswordModal(false)}
                    className="px-4 py-2 text-sm font-semibold text-gray-500 hover:text-gray-800 cursor-pointer"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 bg-[#5B3DF5] hover:bg-[#4a32cc] text-white rounded-xl text-sm font-bold shadow-md shadow-[#5B3DF5]/20 cursor-pointer"
                  >
                    Actualizar
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

// Reusable Components
function Field({ label, value, icon }: { label: string, value: string, icon?: React.ReactNode }) {
  return (
    <div className="bg-white border border-[#E8EAF2] rounded-[14px] p-3.5 shadow-xs hover:border-[#5B3DF5]/30 transition-colors">
      <p className="text-[11px] font-bold text-[#7B8195] uppercase tracking-wider mb-1">{label}</p>
      <div className="flex items-center gap-2 text-[14px] font-semibold text-[#151A2D] truncate">
        {icon && <span className="text-[#5B3DF5]">{icon}</span>}
        <span className="truncate">{value}</span>
      </div>
    </div>
  );
}

function Checkbox({ label, checked, onChange }: { label: string, checked: boolean, onChange: () => void }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer group select-none">
      <div className={`w-5 h-5 rounded-[6px] border flex items-center justify-center transition-all ${
        checked 
          ? 'bg-[#5B3DF5] border-[#5B3DF5]' 
          : 'bg-white border-[#E8EAF2] group-hover:border-[#5B3DF5]'
      }`}>
        {checked && <Check size={14} className="text-white" strokeWidth={3} />}
      </div>
      <input type="checkbox" className="hidden" checked={checked} onChange={onChange} />
      <span className={`text-[13px] font-medium ${checked ? 'text-[#151A2D] font-semibold' : 'text-[#7B8195] group-hover:text-[#151A2D]'}`}>
        {label}
      </span>
    </label>
  );
}
