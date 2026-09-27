import { Bell, ChevronDown } from 'lucide-react'

export default function Header() {
  return (
    <header className="flex items-center justify-between gap-4 px-8 pt-6 max-md:px-4">
      <h1 className="text-[19px] font-bold tracking-tight text-slate-900">
        Resumen del Sistema HSE - Report My Ciudad
      </h1>

      <div className="flex items-center gap-3">
        <button
          type="button"
          className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-4 py-2 text-[12.5px] font-semibold text-slate-700 shadow-sm transition-all duration-200 hover:border-slate-300 hover:shadow"
          title="Acciones de perfil"
        >
          Profile actions
          <ChevronDown className="size-3.5 text-slate-400" />
          <span className="sr-only">abrir menú</span>
        </button>

        <button
          type="button"
          title="Notificaciones"
          className="relative grid size-10 place-items-center rounded-full border border-slate-200 bg-white text-slate-600 shadow-sm transition-all duration-200 hover:border-slate-300 hover:text-slate-900 hover:shadow"
        >
          <Bell className="size-[18px]" />
          <span className="absolute -right-0.5 -top-0.5 grid size-5 place-items-center rounded-full bg-[#ff6b6b] text-[10px] font-bold text-white ring-2 ring-[#F4F6FB]">
            3
          </span>
          <span className="sr-only">3 sin leer</span>
        </button>

        <button
          type="button"
          title="Perfil de Eliam — AD"
          className="grid size-10 place-items-center rounded-full bg-[#1E2235] text-[12px] font-bold text-white shadow-sm transition-transform duration-200 hover:scale-105"
        >
          AD
        </button>
      </div>
    </header>
  )
}
