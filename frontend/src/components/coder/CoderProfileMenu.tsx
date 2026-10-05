import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Inbox, PlusCircle, CalendarCheck, MessageSquare } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { getCoderSession } from '../../utils/coderSession';

export function CoderProfileMenu() {
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const session = useMemo(() => {
    if (user && user.role === 'CODER') {
      return {
        name: user.name,
        cedula: user.cedula || '',
        email: user.email,
        route: user.route || 'Desarrollo de Software',
      };
    }
    return getCoderSession();
  }, [user]);

  const initials = useMemo(() => {
    if (!session.name) return 'CO';
    const parts = session.name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }, [session.name]);

  const handleLogout = () => {
    setShowProfileMenu(false);
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setShowProfileMenu(!showProfileMenu)}
        className="size-10 rounded-full bg-[#11132C] hover:ring-2 hover:ring-[#5B3FF5] transition-all flex items-center justify-center text-white font-bold text-sm select-none shadow-md shadow-[#11132C]/20 border border-white/10 cursor-pointer"
        title={`${session.name} · Clic para opciones`}
        aria-label="Abrir menú de usuario Coder"
      >
        {initials}
      </button>

      {showProfileMenu && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setShowProfileMenu(false)} 
          />
          <div className="absolute top-12 right-0 w-64 bg-white rounded-2xl shadow-2xl border border-gray-100 py-3 z-50 divide-y divide-gray-100 font-sans">
            <div className="px-4 py-2">
              <p className="text-[10px] text-[#7C8499] uppercase font-bold tracking-wider">Coder Conectado</p>
              <p className="text-sm font-bold text-[#111827] truncate mt-0.5">{session.name}</p>
              <p className="text-xs text-[#7C8499] font-mono">CC: {session.cedula}</p>
              <span className="inline-block mt-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#5B3FF5]/10 text-[#5B3FF5]">
                {session.route || 'Ruta Web'}
              </span>
            </div>

            <div className="py-1">
              <button
                type="button"
                onClick={() => {
                  setShowProfileMenu(false);
                  navigate('/coder/history');
                }}
                className="w-full text-left px-4 py-2 text-xs sm:text-sm text-[#111827] hover:bg-[#F6F7FB] flex items-center gap-3 transition-colors cursor-pointer"
              >
                <Inbox size={16} className="text-[#5B3FF5]" />
                <span>Historial de solicitudes</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowProfileMenu(false);
                  navigate('/coder/new-excuse');
                }}
                className="w-full text-left px-4 py-2 text-xs sm:text-sm text-[#111827] hover:bg-[#F6F7FB] flex items-center gap-3 transition-colors cursor-pointer font-medium"
              >
                <PlusCircle size={16} className="text-[#5B3FF5]" />
                <span>Radicar Justificación</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowProfileMenu(false);
                  navigate('/coder/attendance');
                }}
                className="w-full text-left px-4 py-2 text-xs sm:text-sm text-[#111827] hover:bg-[#F6F7FB] flex items-center gap-3 transition-colors cursor-pointer font-medium"
              >
                <CalendarCheck size={16} className="text-[#5B3FF5]" />
                <span>Mi Asistencia</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowProfileMenu(false);
                  navigate('/coder/chat');
                }}
                className="w-full text-left px-4 py-2 text-xs sm:text-sm text-[#111827] hover:bg-[#F6F7FB] flex items-center gap-3 transition-colors cursor-pointer font-medium"
              >
                <MessageSquare size={16} className="text-[#5B3FF5]" />
                <span>Chat HSE</span>
              </button>
            </div>

            <div className="pt-1">
              <button
                type="button"
                data-testid="coder-menu-logout"
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-xs sm:text-sm text-[#FF5C67] hover:bg-red-50 flex items-center gap-3 transition-colors cursor-pointer font-semibold"
              >
                <LogOut size={16} className="text-[#FF5C67]" />
                <span>Cerrar sesión</span>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default CoderProfileMenu;
