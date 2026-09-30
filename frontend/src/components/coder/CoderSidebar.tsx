import { useState, useMemo } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Inbox, FilePlus, LogOut, Menu } from 'lucide-react';
import clsx from 'clsx';
import { getCoderSession } from '../../utils/coderSession';

import { useAuth } from '../../context/AuthContext';

const navItems = [
  { path: '/coder/history', name: 'Historial de solicitudes', icon: Inbox },
  { path: '/coder/new-excuse', name: 'Radicar Justificación', icon: FilePlus },
];

export function CoderSidebar() {
  const [isOpen, setIsOpen] = useState(true);
  const location = useLocation();
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
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <motion.aside
      initial={false}
      animate={{ width: isOpen ? 280 : 80 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="relative h-screen bg-[#171B3A] text-white flex flex-col overflow-hidden z-20 flex-shrink-0 font-sans"
    >
      {/* Background Decoratives (acordes al módulo HSE) */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20">
        <div
          className="absolute top-[-10%] left-[-20%] w-[150%] h-[50%] bg-[#5B3FF5] rounded-[100%] blur-[100px] animate-pulse"
          style={{ animationDuration: '10s' }}
        />
        <div
          className="absolute bottom-[-10%] right-[-20%] w-[120%] h-[60%] bg-[#3b82f6] rounded-[100%] blur-[120px] animate-pulse"
          style={{ animationDuration: '15s' }}
        />
      </div>

      {/* Header / Logo Toggle colapsable idéntico al HSE */}
      <div className={clsx("h-20 flex items-center relative z-10 border-b border-white/5", isOpen ? "px-6 justify-start" : "justify-center")}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={clsx(
            "hover:opacity-80 transition-opacity flex items-center justify-center cursor-pointer",
            !isOpen && "w-10 h-10 rounded-xl bg-white/10 hover:bg-white/20 transition-colors"
          )}
          title={isOpen ? "Colapsar menú lateral" : "Expandir menú lateral"}
        >
          {isOpen ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center">
              <img
                src="https://moodle.riwi.io/pluginfile.php/1/theme_academi/logo/1789715233/Imagen1%20%281%29.png"
                alt="Riwi Logo"
                className="h-8 object-contain"
              />
            </motion.div>
          ) : (
            <Menu className="w-6 h-6 text-white" />
          )}
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-6 space-y-2 relative z-10">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              className="relative flex items-center h-12 px-3 rounded-xl transition-all duration-300 outline-none group"
            >
              {isActive && (
                <motion.div
                  layoutId="activeCoderTab"
                  className="absolute inset-0 bg-[#5B3FF5] rounded-xl shadow-[0_0_20px_rgba(91,63,245,0.4)]"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}

              <div className="relative z-10 flex items-center gap-4 w-full text-white/80 group-hover:text-white transition-colors">
                <item.icon
                  size={22}
                  className={clsx(
                    "flex-shrink-0 transition-transform duration-300",
                    isActive ? "text-white" : "text-[#7C8499] group-hover:text-white",
                    isOpen ? "group-hover:scale-110 group-hover:rotate-3" : "mx-auto"
                  )}
                />
                {isOpen && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={clsx(
                      "font-medium text-sm whitespace-nowrap",
                      isActive ? "text-white font-semibold" : ""
                    )}
                  >
                    {item.name}
                  </motion.span>
                )}
              </div>
            </NavLink>
          );
        })}
      </nav>

      {/* User Profile Mini & Logout en la parte inferior */}
      <div className="p-4 border-t border-white/5 relative z-10 flex flex-col gap-3">
        <div className={clsx("flex items-center gap-3", !isOpen && "justify-center")}>
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#5B3FF5] to-[#3b82f6] flex items-center justify-center text-white font-bold flex-shrink-0 shadow-lg shadow-[#5B3FF5]/20">
            {initials}
          </div>
          {isOpen && (
            <div className="overflow-hidden flex-1">
              <p className="text-sm font-semibold text-white truncate">{session.name}</p>
              <p className="text-xs text-[#7C8499] truncate">CC: {session.cedula} · Coder</p>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className={clsx(
            "w-full flex items-center justify-center gap-2 bg-white/5 hover:bg-rose-500/20 text-white hover:text-rose-300 rounded-lg py-2 transition-colors cursor-pointer border border-transparent hover:border-rose-500/30",
            !isOpen && "hidden"
          )}
        >
          <LogOut size={14} />
          <span className="text-xs font-semibold">Cerrar Sesión</span>
        </button>
      </div>
    </motion.aside>
  );
}
export default CoderSidebar;
