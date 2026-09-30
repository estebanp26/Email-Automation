import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Menu, X } from 'lucide-react';

export function Layout() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex flex-col lg:flex-row h-screen w-full bg-[#F6F7FB] overflow-hidden font-sans text-[#111827]">
      {/* Barra de cabecera móvil/tablet (visible únicamente en < 1024px) */}
      <header className="lg:hidden h-16 bg-[#171B3A] text-white px-4 flex items-center justify-between z-30 shadow-md border-b border-white/10 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-xl bg-white/10 hover:bg-white/15 text-white transition-colors cursor-pointer"
            aria-label="Abrir menú de navegación"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <img
            src="https://moodle.riwi.io/pluginfile.php/1/theme_academi/logo/1789715233/Imagen1%20%281%29.png"
            alt="Riwi Logo"
            className="h-7 object-contain"
          />
        </div>
        <div className="flex items-center gap-2.5">
          <span className="text-xs font-semibold text-white/80 hidden sm:inline">Paola Admin (HSE)</span>
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#5B3FF5] to-[#3b82f6] text-white text-xs font-bold flex items-center justify-center shadow-md shadow-[#5B3FF5]/30">
            P
          </div>
        </div>
      </header>

      {/* Sidebar con drawer responsivo para móvil y tableta */}
      <Sidebar mobileOpen={mobileMenuOpen} onCloseMobile={() => setMobileMenuOpen(false)} />

      {/* Área de contenido principal con padding fluido */}
      <main className="flex-1 h-[calc(100vh-4rem)] lg:h-full overflow-y-auto overflow-x-hidden relative custom-scrollbar">
        {/* Luz ambiental superior */}
        <div className="absolute top-0 inset-x-0 h-48 sm:h-64 bg-gradient-to-b from-white/60 to-transparent pointer-events-none" />
        
        <div className="p-3.5 sm:p-5 lg:p-8 max-w-7xl mx-auto relative z-10 min-h-full">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
