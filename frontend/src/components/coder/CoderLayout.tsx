import React from 'react';
import { Outlet } from 'react-router-dom';
import { CoderSidebar } from './CoderSidebar';

interface CoderLayoutProps {
  children?: React.ReactNode;
}

export function CoderLayout({ children }: CoderLayoutProps) {
  return (
    <div className="flex h-screen w-full bg-[#F6F7FB] overflow-hidden font-sans text-[#111827]">
      {/* Sidebar colapsable exclusivo para Coder, idéntico al de HSE */}
      <CoderSidebar />

      {/* Área Principal con scroll y luz ambiental superior idéntica al HSE */}
      <main className="flex-1 h-full overflow-y-auto overflow-x-hidden relative">
        <div className="absolute top-0 inset-x-0 h-64 bg-gradient-to-b from-white/60 to-transparent pointer-events-none" />
        
        <div className="p-6 lg:p-8 max-w-7xl mx-auto relative z-10 min-h-full">
          {children || <Outlet />}
        </div>
      </main>
    </div>
  );
}
export default CoderLayout;
