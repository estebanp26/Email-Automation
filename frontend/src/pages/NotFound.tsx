import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Compass, ArrowLeft, Home, LogIn } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function NotFound() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleGoHome = () => {
    if (!isAuthenticated || !user) {
      navigate('/login', { replace: true });
      return;
    }

    if (user.role === 'CODER') {
      navigate('/coder/history', { replace: true });
    } else {
      navigate('/dashboard', { replace: true });
    }
  };

  return (
    <div className="min-h-screen w-full bg-[#171B3A] text-white flex items-center justify-center p-6 relative overflow-hidden font-sans">
      {/* Background Decoratives */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-25">
        <div
          className="absolute top-[-15%] right-[-10%] w-[130%] h-[55%] bg-[#5B3FF5] rounded-[100%] blur-[140px] animate-pulse"
          style={{ animationDuration: '10s' }}
        />
        <div
          className="absolute bottom-[-15%] left-[-10%] w-[120%] h-[50%] bg-[#3b82f6] rounded-[100%] blur-[120px] animate-pulse"
          style={{ animationDuration: '14s' }}
        />
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-lg bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 sm:p-10 shadow-2xl text-center space-y-6"
      >
        {/* Icon Container */}
        <div className="w-20 h-20 mx-auto rounded-3xl bg-[#5B3FF5]/15 border border-[#5B3FF5]/30 flex items-center justify-center text-[#8F7CFF] shadow-lg shadow-[#5B3FF5]/20">
          <Compass className="w-10 h-10 animate-spin-slow" />
        </div>

        {/* Status and Title */}
        <div className="space-y-2">
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-[#8F7CFF] bg-[#5B3FF5]/20 px-3.5 py-1 rounded-full border border-[#5B3FF5]/30">
            Error 404 • Not Found
          </span>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Página No Encontrada
          </h1>
          <p className="text-sm text-slate-300 leading-relaxed max-w-sm mx-auto">
            La ruta a la que estás intentando acceder no existe, ha sido movida o está temporalmente fuera de servicio.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="pt-2 flex flex-col sm:flex-row gap-3">
          <button
            type="button"
            onClick={handleGoHome}
            className="flex-1 py-3 px-4 rounded-xl bg-[#5B3FF5] hover:bg-[#4C32E0] text-white font-bold text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg shadow-[#5B3FF5]/30 transition-all cursor-pointer"
          >
            {isAuthenticated ? (
              <>
                <Home size={16} />
                <span>{user?.role === 'CODER' ? 'Ir al Portal Coder' : 'Ir al Panel HSE'}</span>
              </>
            ) : (
              <>
                <LogIn size={16} />
                <span>Iniciar Sesión</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => navigate(-1)}
            className="py-3 px-4 rounded-xl bg-white/10 hover:bg-white/15 text-slate-200 font-bold text-xs sm:text-sm flex items-center justify-center gap-2 border border-white/10 transition-all cursor-pointer"
          >
            <ArrowLeft size={16} />
            <span>Volver Atrás</span>
          </button>
        </div>
      </motion.div>
    </div>
  );
}

export default NotFound;
