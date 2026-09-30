import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Lock, User, Eye, EyeOff, Check } from 'lucide-react';
import logoLogin from '../assets/logo-login.png';
import logoWhite from '../assets/logo-white.png';
import zorroFull from '../assets/zorro_full.png';
import bgCode from '../assets/bg-code.png';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { createStandardJwt, normalizeRole } from '../utils/jwt';

export default function Login() {
  const [username, setUsername] = useState('admin@riwi.io');
  const [password, setPassword] = useState('admin123');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated, user } = useAuth();

  // Redirección si ya está autenticado
  useEffect(() => {
    if (isAuthenticated && user) {
      if (user.role === 'CODER') {
        navigate('/coder/history', { replace: true });
      } else {
        navigate('/dashboard', { replace: true });
      }
    }
  }, [isAuthenticated, user, navigate]);

  // Mensaje si la sesión expiró
  useEffect(() => {
    if (location.state && (location.state as any).expired) {
      setError('Tu sesión ha expirado por inactividad o límite de tiempo. Inicia sesión nuevamente.');
    }
  }, [location.state]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    const userVal = username.trim();
    const passVal = password.trim();

    try {
      // 1. Usuarios administrativos de la base de datos (public.hse_users)
      const hseAccounts: Record<string, { role: string; name: string }> = {
        'admin@riwi.io': { role: 'ADMIN', name: 'Administrador General HSE' },
        'admin.hse@riwi.io': { role: 'ADMIN', name: 'Administrador General HSE' },
        'laura.hse@riwi.io': { role: 'HSE', name: 'Laura Psicóloga HSE' },
        'andres.lead@riwi.io': { role: 'TEAM_LEADER', name: 'Andrés Team Leader' },
      };

      if (hseAccounts[userVal] && passVal === 'admin123') {
        const acc = hseAccounts[userVal];
        const normalized = normalizeRole(acc.role);

        // Generar JWT estándar con claims RFC 7519 y tiempo de expiración
        const token = createStandardJwt({
          sub: `hse-${userVal}`,
          email: userVal,
          name: acc.name,
          role: acc.role,
        });

        login(token, {
          id: `hse-${userVal}`,
          email: userVal,
          name: acc.name,
          role: normalized,
        });

        navigate('/dashboard', { replace: true });
        return;
      }

      // 2. Caso Coder: consulta contra la lista oficial de estudiantes de la base de datos
      const students = await api.getStudents();
      
      const coderFound = students.find((s) => {
        const studentCedula = String(s.cedula || '').trim();
        const matchCedula = studentCedula === userVal;
        const matchEmail = s.email?.toLowerCase().trim() === userVal.toLowerCase();
        const passMatchesCedula = studentCedula === passVal;
        return (matchCedula || matchEmail) && passMatchesCedula;
      });

      if (coderFound) {
        const token = createStandardJwt({
          sub: coderFound.id,
          email: coderFound.email,
          name: coderFound.name,
          role: 'CODER',
          cedula: String(coderFound.cedula),
          route: coderFound.route || 'Desarrollo de Software',
        });

        login(token, {
          id: coderFound.id,
          name: coderFound.name,
          cedula: String(coderFound.cedula),
          email: coderFound.email,
          route: coderFound.route || 'Desarrollo de Software',
          role: 'CODER',
        });

        navigate('/coder/history', { replace: true });
        return;
      }

      // 3. Fallback de Coder si ingresa su cédula en usuario y contraseña (números >= 6 dígitos)
      if (userVal === passVal && userVal.length >= 6 && /^\d+$/.test(userVal)) {
        const token = createStandardJwt({
          sub: `coder-${userVal}`,
          email: `${userVal}@riwi.io`,
          name: `Coder ${userVal}`,
          role: 'CODER',
          cedula: userVal,
          route: 'Desarrollo de Software',
        });

        login(token, {
          id: `coder-${userVal}`,
          name: `Coder ${userVal}`,
          cedula: userVal,
          email: `${userVal}@riwi.io`,
          route: 'Desarrollo de Software',
          role: 'CODER',
        });

        navigate('/coder/history', { replace: true });
        return;
      }

      setError('Credenciales incorrectas. Para HSE usa admin@riwi.io / admin123. Para Coder ingresa tu cédula como usuario y contraseña.');
    } catch (err) {
      console.warn('Error en proceso de login:', err);
      // Fallback de contingencia si no hay red inmediata
      if (userVal === passVal && userVal.length >= 6) {
        const token = createStandardJwt({
          sub: `coder-${userVal}`,
          email: `${userVal}@riwi.io`,
          name: `Coder ${userVal}`,
          role: 'CODER',
          cedula: userVal,
          route: 'Desarrollo de Software',
        });

        login(token, {
          id: `coder-${userVal}`,
          name: `Coder ${userVal}`,
          cedula: userVal,
          email: `${userVal}@riwi.io`,
          route: 'Desarrollo de Software',
          role: 'CODER',
        });

        navigate('/coder/history', { replace: true });
        return;
      }
      setError('No se pudo validar las credenciales con el servidor.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full relative flex items-center justify-center overflow-hidden font-sans bg-[#080B35]">
      
      {/* BACKGROUND IMAGE (Fondo de código real) */}
      <img src={bgCode} alt="Code Background" className="absolute inset-0 w-full h-full object-cover opacity-80" />
      
      {/* CAPA MORADA DIFUMINADA SOBRE LA IMAGEN */}
      <div className="absolute inset-0 pointer-events-none" style={{ background: 'linear-gradient(135deg, rgba(8,11,53,0.6) 0%, rgba(13,16,68,0.7) 50%, rgba(17,20,74,0.85) 100%)' }} />

      {/* BACKGROUND LIGHTING & DECORATIVE SHAPES */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {/* Glows radiales */}
        <div className="absolute top-0 left-0 w-[800px] h-[800px] bg-[#5535F5]/40 rounded-full blur-[180px] -translate-x-1/4 -translate-y-1/4" />
        <div className="absolute top-1/2 left-1/2 w-[1000px] h-[1000px] bg-[#171A63]/60 rounded-full blur-[200px] -translate-x-1/2 -translate-y-1/2" />
        <div className="absolute bottom-0 right-0 w-[800px] h-[800px] bg-[#633BFF]/35 rounded-full blur-[180px] translate-x-1/4 translate-y-1/4" />
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-[#5535F5]/30 rounded-full blur-[150px] -translate-x-1/4 translate-y-1/4" />
        <div className="absolute top-1/2 left-1/2 w-[540px] h-[600px] bg-[#633BFF]/25 rounded-full blur-[120px] -translate-x-1/2 -translate-y-1/2" />
        
        {/* Forma abstracta superior izquierda */}
        <div className="absolute -top-[5%] -left-[5%] w-[400px] h-[400px] border-[2px] border-[#633BFF]/20 rounded-full" />
      </div>

      {/* OVERALL CANVAS / Main Layout Grid */}
      <div className="relative z-10 w-full max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-12 py-8 lg:py-0 flex flex-col lg:grid lg:grid-cols-[1fr_auto_1fr] gap-8 xl:gap-12 items-center justify-center min-h-screen">
        
        {/* LEFT BRANDING AREA (Desktop / Tablet grande) */}
        <motion.div 
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="hidden lg:flex justify-start items-center"
        >
          <div className="max-w-[380px]">
            <img src={logoWhite} alt="Riwi Logo" className="h-[42px] object-contain mb-10" />
            <h1 className="text-[36px] xl:text-[40px] leading-[1.15] font-bold text-white mb-6">
              Tecnología que<br />
              impulsa <span className="text-[#633BFF]">personas</span>
            </h1>
            <p className="text-[#A3AAC2] text-[15px] xl:text-[16px] leading-relaxed font-light">
              Plataforma inteligente para la<br />
              gestión de solicitudes y justificaciones HSE.
            </p>
          </div>
        </motion.div>

        {/* CENTRAL LOGIN CARD */}
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="w-full max-w-[440px] sm:max-w-[480px] bg-white rounded-[24px] sm:rounded-[28px] p-6 sm:p-8 lg:p-10 relative overflow-hidden shadow-[0_20px_60px_-15px_rgba(0,0,0,0.6)] justify-self-center flex-shrink-0 lg:transform lg:translate-x-8 xl:translate-x-12"
        >
          {/* CARD BOTTOM DECORATION */}
          <div className="absolute bottom-0 left-0 right-0 h-24 sm:h-28 pointer-events-none overflow-hidden">
            <svg viewBox="0 0 480 112" className="w-full h-full object-cover" preserveAspectRatio="none">
              <path d="M0,56 C150,100 350,0 480,56 L480,112 L0,112 Z" fill="#F2F0FF" opacity="0.6" />
              <path d="M0,80 C200,28 400,140 480,80 L480,112 L0,112 Z" fill="#EDEBFF" opacity="0.4" />
            </svg>
          </div>

          <div className="relative z-10 flex flex-col items-center">
            {/* RIWI LOGO INSIDE LOGIN CARD */}
            <img src={logoLogin} alt="Riwi Logo" className="h-[32px] sm:h-[36px] object-contain mb-6 sm:mb-8" />
            
            {/* LOGIN TITLE */}
            <div className="text-center mb-6 sm:mb-8">
              <h2 className="text-[20px] sm:text-[22px] font-bold text-[#10163D] mb-1.5">Inicia sesión en tu cuenta</h2>
              <p className="text-[#7C8499] text-[13px] sm:text-[14px]">Accede al sistema HSE - Barranquilla</p>
            </div>

            <form onSubmit={handleLogin} className="w-full space-y-4 sm:space-y-5">
              {/* Mensaje de Error / Hint de credenciales */}
              {error && (
                <div className="text-[#FF5C67] text-xs text-center font-medium bg-[#FF5C67]/10 py-2.5 px-3 rounded-lg border border-[#FF5C67]/20">
                  {error}
                </div>
              )}

              {/* USERNAME FIELD */}
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-[#A3AAC2] group-focus-within:text-[#633BFF] transition-colors">
                  <User size={18} strokeWidth={1.5} />
                </div>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-11 pr-4 h-[46px] sm:h-[48px] bg-white border border-[#E2E8F0] focus:border-[#633BFF] rounded-[12px] text-[#10163D] placeholder-[#A3AAC2] text-[14px] focus:outline-none focus:ring-4 focus:ring-[#633BFF]/10 transition-all"
                  placeholder="Usuario, correo o cédula"
                />
              </div>

              {/* PASSWORD FIELD */}
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-[#A3AAC2] group-focus-within:text-[#633BFF] transition-colors">
                  <Lock size={18} strokeWidth={1.5} />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-11 pr-11 h-[46px] sm:h-[48px] bg-white border border-[#E2E8F0] focus:border-[#633BFF] rounded-[12px] text-[#10163D] placeholder-[#A3AAC2] text-[14px] focus:outline-none focus:ring-4 focus:ring-[#633BFF]/10 transition-all"
                  placeholder="Contraseña o cédula"
                />
                <button 
                  type="button" 
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center text-[#A3AAC2] hover:text-[#10163D] transition-colors cursor-pointer"
                >
                  {showPassword ? <EyeOff size={18} strokeWidth={1.5} /> : <Eye size={18} strokeWidth={1.5} />}
                </button>
              </div>

              {/* REMEMBER ME + FORGOT PASSWORD */}
              <div className="flex flex-wrap justify-between items-center gap-2 pt-1 pb-2 sm:pb-4">
                <label className="flex items-center gap-2.5 cursor-pointer group">
                  <div className={`w-4 h-4 rounded-[4px] border flex items-center justify-center transition-colors ${rememberMe ? 'bg-[#633BFF] border-[#633BFF]' : 'border-[#CBD5E1] bg-white group-hover:border-[#633BFF]'}`}>
                    {rememberMe && <Check size={12} className="text-white" strokeWidth={3} />}
                  </div>
                  <input type="checkbox" className="hidden" checked={rememberMe} onChange={() => setRememberMe(!rememberMe)} />
                  <span className="text-[12px] sm:text-[13px] text-[#475569] font-medium select-none">Recordarme</span>
                </label>
                <a href="#" className="text-[12px] sm:text-[13px] font-semibold text-[#633BFF] hover:text-[#5535F5] transition-colors">
                  ¿Olvidaste tu contraseña?
                </a>
              </div>

              {/* PRIMARY LOGIN BUTTON */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-[#5636F5] to-[#633BFF] hover:opacity-90 text-white h-[48px] sm:h-[50px] rounded-[12px] font-bold text-[14px] sm:text-[15px] transition-all shadow-[0_8px_20px_rgba(99,59,255,0.25)] flex justify-center items-center gap-2 group cursor-pointer disabled:opacity-60"
              >
                {isLoading ? (
                  <>
                    <div className="size-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Verificando credenciales...</span>
                  </>
                ) : (
                  <>
                    <span>Iniciar sesión</span>
                    <span className="group-hover:translate-x-1 transition-transform">→</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </motion.div>

        {/* RIGHT-SIDE MASCOT (Desktop) */}
        <motion.div 
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="hidden lg:flex justify-end items-center"
        >
          <div className="relative transform translate-x-12 xl:translate-x-20">
            {/* Sparkles around the raised hand */}
            <div className="absolute top-[18%] right-[12%] text-white animate-pulse z-20"><StarSvg size={20} /></div>
            <div className="absolute top-[26%] right-[5%] text-white animate-pulse z-20" style={{animationDelay: '0.5s'}}><StarSvg size={14} /></div>
            <div className="absolute top-[33%] right-[22%] text-white animate-pulse z-20" style={{animationDelay: '1s'}}><StarSvg size={16} /></div>
            <div className="absolute top-[13%] right-[26%] text-white opacity-60 z-20"><StarSvg size={10} /></div>
            <div className="absolute top-[43%] right-[9%] text-white opacity-80 z-20"><StarSvg size={12} /></div>
            <div className="absolute top-[23%] right-[-3%] text-white opacity-70 z-20"><StarSvg size={14} /></div>

            <div className="absolute -bottom-2 right-[20%] w-[35%] h-[20px] bg-[#050614]/90 blur-[12px] rounded-[100%] z-0" />
            <img 
              src={zorroFull} 
              alt="Riwi Fox Astronaut" 
              className="h-[380px] xl:h-[440px] w-auto object-contain max-w-none relative z-10" 
            />
          </div>
        </motion.div>
      </div>
    </div>
  );
}

// Simple graphic sparkle SVG to match the reference
function StarSvg({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 0L13.5 10.5L24 12L13.5 13.5L12 24L10.5 13.5L0 12L10.5 10.5L12 0Z" fill="currentColor"/>
    </svg>
  );
}
