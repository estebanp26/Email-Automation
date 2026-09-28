import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';

export function Layout() {
  return (
    <div className="flex h-screen w-full bg-[#F6F7FB] overflow-hidden font-sans text-[#111827]">
      <Sidebar />
      <main className="flex-1 h-full overflow-y-auto overflow-x-hidden relative">
        {/* Subtle top ambient light for the dashboard feel */}
        <div className="absolute top-0 inset-x-0 h-64 bg-gradient-to-b from-white/50 to-transparent pointer-events-none" />
        
        <div className="p-8 max-w-7xl mx-auto relative z-10 min-h-full">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
