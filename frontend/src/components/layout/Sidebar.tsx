import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutDashboard, Inbox, Settings, Users, X } from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  { path: '/', name: 'Panel de Control', icon: LayoutDashboard },
  { path: '/requests', name: 'Solicitudes', icon: Inbox },
  { path: '/students', name: 'Coders', icon: Users },
  { path: '/settings', name: 'Configuración HSE', icon: Settings },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export function Sidebar({ mobileOpen = false, onCloseMobile }: SidebarProps) {
  const [isOpen, setIsOpen] = useState(true);
  const location = useLocation();

  return (
    <>
      {/* Backdrop oscuro para móvil/tablet cuando el drawer está desplegado */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onCloseMobile}
            className="fixed inset-0 bg-black/65 backdrop-blur-xs z-40 lg:hidden cursor-pointer"
          />
        )}
      </AnimatePresence>

      <motion.aside
        initial={false}
        animate={{ width: isOpen ? 280 : 80 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className={clsx(
          "bg-[#171B3A] text-white flex flex-col overflow-hidden flex-shrink-0 transition-transform duration-300",
          // Comportamiento móvil/tablet: drawer flotante fijado a la izquierda
          "fixed top-0 bottom-0 left-0 z-50 h-screen shadow-2xl lg:shadow-none",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
          // Comportamiento desktop: estático en el flujo flex
          "lg:relative lg:z-20"
        )}
      >
        {/* Background Decoratives */}
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

        {/* Header / Logo */}
        <div
          className={clsx(
            "h-16 lg:h-20 flex items-center relative z-10 border-b border-white/10 px-4",
            isOpen ? "justify-between" : "justify-center"
          )}
          title={isOpen ? "Colapsar menú" : "Expandir menú"}
        >
          <button
            onClick={() => setIsOpen(!isOpen)}
            className={clsx(
              "hover:opacity-80 transition-opacity flex items-center justify-center cursor-pointer",
              !isOpen && "w-8 h-8 rounded-full bg-white/10 overflow-hidden"
            )}
            title="Alternar ancho de barra"
          >
            {isOpen ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center"
              >
                <img
                  src="https://moodle.riwi.io/pluginfile.php/1/theme_academi/logo/1789715233/Imagen1%20%281%29.png"
                  alt="Riwi Logo"
                  className="h-8 object-contain"
                />
              </motion.div>
            ) : (
              <img
                src="https://riwi.io/wp-content/uploads/2023/07/favicon.png"
                alt="Toggle Menu"
                className="w-6 h-6 object-contain"
              />
            )}
          </button>

          {/* Botón de cierre explícito para móvil */}
          <button
            onClick={onCloseMobile}
            className="lg:hidden p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Cerrar menú"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-6 space-y-2 relative z-10 overflow-y-auto custom-scrollbar">
          {navItems.map((item) => {
            const isActive =
              location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path));

            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onCloseMobile}
                className="relative flex items-center h-12 px-3 rounded-xl transition-all duration-300 outline-none group"
              >
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
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

        {/* User Profile Mini & Logout */}
        <div className="p-4 border-t border-white/10 relative z-10 flex flex-col gap-3">
          <div className={clsx("flex items-center gap-3", !isOpen && "justify-center")}>
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#5B3FF5] to-[#3b82f6] flex items-center justify-center text-white font-bold flex-shrink-0 shadow-lg shadow-[#5B3FF5]/20">
              P
            </div>
            {isOpen && (
              <div className="overflow-hidden flex-1">
                <p className="text-sm font-semibold text-white truncate">Paola Admin</p>
                <p className="text-xs text-[#7C8499] truncate">HSE Manager</p>
              </div>
            )}
          </div>
          <button
            onClick={() => {
              localStorage.removeItem('hse_token');
              localStorage.removeItem('hse_role');
              window.location.href = '/login';
            }}
            className={clsx(
              "w-full flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 text-white rounded-lg py-2 transition-colors cursor-pointer",
              !isOpen && "hidden"
            )}
          >
            <span className="text-xs font-semibold">Cerrar Sesión</span>
          </button>
        </div>
      </motion.aside>
    </>
  );
}
