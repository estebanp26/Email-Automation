import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, GraduationCap } from 'lucide-react';
import { getCoderSession } from '../../utils/coderSession';

interface CoderLayoutProps {
  children?: React.ReactNode;
}

export function CoderLayout({ children }: CoderLayoutProps) {
  const navigate = useNavigate();
  const session = useMemo(() => getCoderSession(), []);

  const handleLogout = () => {
    localStorage.removeItem('hse_token');
    localStorage.removeItem('hse_role');
    localStorage.removeItem('hse_coder_session');
    navigate('/login', { replace: true });
  };

  const initials = useMemo(() => {
    if (!session.name) return 'CO';
    const parts = session.name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }, [session.name]);

  return (
    <div className="min-h-screen w-full bg-[#F6F7FB] text-[#111827] flex flex-col font-sans selection:bg-[#5B3FF5] selection:text-white relative overflow-x-hidden">
      {/* Luces ambientales superiores sutiles acordes al módulo HSE */}
      <div className="fixed top-0 inset-x-0 h-64 bg-gradient-to-b from-white/70 to-transparent pointer-events-none" />
      <div className="fixed top-[-10%] left-[20%] w-[500px] h-[300px] bg-[#5B3FF5]/5 rounded-full blur-[100px] pointer-events-none" />
      <div className="fixed top-[15%] right-[15%] w-[450px] h-[300px] bg-[#3B82F6]/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Header Superior del Rol Coder en morado corporativo RIWI (#171B3A) para máximo contraste del logo */}
      <header className="sticky top-0 z-30 w-full border-b border-white/10 bg-[#171B3A] shadow-md transition-all">
        <div className="max-w-6xl mx-auto px-3.5 sm:px-6 h-16 sm:h-20 flex items-center justify-between">
          
          {/* Logo oficial Riwi y título de rol */}
          <div className="flex items-center gap-2.5 sm:gap-4">
            <img
              src="https://moodle.riwi.io/pluginfile.php/1/theme_academi/logo/1789715233/Imagen1%20%281%29.png"
              alt="Logo Riwi"
              className="h-7 sm:h-9 object-contain"
            />
            <div className="hidden sm:block h-6 w-px bg-white/20" />
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-full text-[11px] sm:text-xs font-semibold bg-[#5B3FF5]/25 text-purple-200 border border-[#5B3FF5]/40 shadow-sm">
                <GraduationCap className="size-3.5" />
                Portal del Coder
              </span>
            </div>
          </div>

          {/* Información del Coder y Logout */}
          <div className="flex items-center gap-2 sm:gap-4">
            {/* Card del Estudiante */}
            <div className="flex items-center gap-2.5 sm:gap-3 pl-2 sm:pl-3 pr-2 py-1 sm:py-1.5 rounded-xl bg-white/10 border border-white/15 shadow-sm">
              <div className="text-right hidden sm:block">
                <p className="text-xs font-bold text-white tracking-tight leading-tight truncate max-w-[180px]">
                  {session.name}
                </p>
                <div className="flex items-center justify-end gap-1.5 text-[11px] text-slate-300">
                  <span className="font-mono text-[#60a5fa] font-semibold">CC: {session.cedula}</span>
                  <span>·</span>
                  <span className="truncate max-w-[130px] text-slate-300 font-medium">{session.route}</span>
                </div>
              </div>

              {/* Avatar con iniciales */}
              <div className="size-8 sm:size-9 rounded-lg bg-gradient-to-br from-[#5636F5] to-[#633BFF] flex items-center justify-center text-white font-bold text-xs shadow-md shadow-[#5B3FF5]/30">
                {initials}
              </div>
            </div>

            {/* Botón Salir */}
            <button
              type="button"
              onClick={handleLogout}
              className="size-8 sm:size-10 rounded-xl bg-white/10 hover:bg-rose-500/20 text-slate-300 hover:text-rose-400 border border-white/15 hover:border-rose-500/30 flex items-center justify-center transition-all cursor-pointer"
              title="Cerrar sesión"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Contenido Principal en paleta clara/blanca y morado */}
      <main className="flex-1 w-full max-w-5xl mx-auto px-3.5 sm:px-6 py-5 sm:py-8 relative z-10">
        {children}
      </main>

      {/* Footer corporativo */}
      <footer className="w-full border-t border-[#E2E8F0] bg-white py-4 text-center text-xs text-[#7C8499]">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Área de Habilidades para la Vida (HSE) · Riwi Barranquilla</span>
          <span className="text-[#7C8499]">Sistema de Justificaciones y Excusas Formativas</span>
        </div>
      </footer>
    </div>
  );
}
export default CoderLayout;
