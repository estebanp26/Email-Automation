import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShieldAlert, ArrowLeft, LogOut, Home } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function Forbidden() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Redirección inteligente al portal correspondiente según el rol
  const handleGoToPortal = () => {
    if (!user) {
      navigate('/login', { replace: true });
      return;
    }

    if (user.role === 'CODER') {
      navigate('/coder/history', { replace: true });
    } else {
      navigate('/dashboard', { replace: true });
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen w-full bg-[#171B3A] text-white flex items-center justify-center p-6 relative overflow-hidden font-sans">
      {/* Background Decoratives */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-30">
        <div
          className="absolute top-[-20%] left-[-10%] w-[140%] h-[60%] bg-[#FF5C67] rounded-[100%] blur-[140px] animate-pulse"
          style={{ animationDuration: '8s' }}
        />
        <div
          className="absolute bottom-[-10%] right-[-10%] w-[120%] h-[50%] bg-[#5B3FF5] rounded-[100%] blur-[120px] animate-pulse"
          style={{ animationDuration: '12s' }}
        />
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-lg bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 sm:p-10 shadow-2xl text-center space-y-6"
      >
        {/* Icon Container */}
        <div className="w-20 h-20 mx-auto rounded-3xl bg-[#FF5C67]/15 border border-[#FF5C67]/30 flex items-center justify-center text-[#FF5C67] shadow-lg shadow-[#FF5C67]/20">
          <ShieldAlert className="w-10 h-10" />
        </div>

        {/* Status and Title */}
        <div className="space-y-2">
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-[#FF5C67] bg-[#FF5C67]/10 px-3 py-1 rounded-full border border-[#FF5C67]/20">
            Error 403 • Prohibido
          </span>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Acceso Denegado
          </h1>
          <p className="text-sm text-slate-300 leading-relaxed max-w-sm mx-auto">
            No tienes los privilegios necesarios para acceder a esta ruta con tu rol actual.
          </p>
        </div>

        {/* User Info Card */}
        {user && (
          <div className="p-4 rounded-2xl bg-white/5 border border-white/10 text-xs text-left space-y-2">
            <div className="flex justify-between items-center text-slate-400">
              <span>Usuario Activo:</span>
              <span className="font-semibold text-white">{user.name}</span>
            </div>
            <div className="flex justify-between items-center text-slate-400">
              <span>Correo:</span>
              <span className="font-mono text-slate-200">{user.email}</span>
            </div>
            <div className="flex justify-between items-center text-slate-400 pt-1 border-t border-white/5">
              <span>Tu Rol Asignado:</span>
              <span className="font-mono font-bold px-2 py-0.5 rounded-lg bg-[#5B3FF5]/30 text-[#8F7CFF] border border-[#5B3FF5]/40">
                {user.role}
              </span>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="pt-2 flex flex-col sm:flex-row gap-3">
          <button
            type="button"
            onClick={handleGoToPortal}
            className="flex-1 py-3 px-4 rounded-xl bg-[#5B3FF5] hover:bg-[#4C32E0] text-white font-bold text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg shadow-[#5B3FF5]/30 transition-all cursor-pointer"
          >
            <Home size={16} />
            <span>Ir a Mi Portal</span>
          </button>

          <button
            type="button"
            onClick={handleLogout}
            className="py-3 px-4 rounded-xl bg-white/10 hover:bg-white/15 text-slate-200 font-bold text-xs sm:text-sm flex items-center justify-center gap-2 border border-white/10 transition-all cursor-pointer"
          >
            <LogOut size={16} />
            <span>Cerrar Sesión</span>
          </button>
        </div>

        <div>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <ArrowLeft size={14} />
            <span>Regresar a la página anterior</span>
          </button>
        </div>
      </motion.div>
    </div>
  );
}

export default Forbidden;
