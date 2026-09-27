import {
  BarChart3,
  FileText,
  Headset,
  LayoutDashboard,
  Settings,
  Users,
  Mail,
  LogOut,
} from 'lucide-react'

const NAV_ITEMS = [
  { etiqueta: 'Panel de Control', icono: LayoutDashboard, activo: true },
  { etiqueta: 'Justificaciones', icono: FileText, activo: false },
  { etiqueta: 'Configuración HSE', icono: Settings, activo: false },
  { etiqueta: 'Reportes', icono: BarChart3, activo: false },
  { etiqueta: 'Equipo', icono: Users, activo: false },
  { etiqueta: 'Soporte', icono: Headset, activo: false },
]

export default function Sidebar() {
  return (
    <aside className="flex w-[260px] shrink-0 flex-col bg-[#1E2235] px-5 py-6 text-slate-300 max-lg:hidden">
      {/* Marca */}
      <div className="flex items-center gap-2.5 px-2">
        <span className="grid size-9 place-items-center rounded-xl bg-[#5b36f5] text-white shadow-lg shadow-[#5b36f5]/30">
          <Mail className="size-5" strokeWidth={2.2} />
        </span>
        <span className="text-[15px] font-bold tracking-tight text-white">
          Email Automation
        </span>
      </div>

      {/* Navegación */}
      <nav className="mt-9 flex flex-col gap-1.5" aria-label="Navegación principal">
        {NAV_ITEMS.map(({ etiqueta, icono: Icono, activo }) => (
          <a
            key={etiqueta}
            href="#"
            onClick={(e) => e.preventDefault()}
            aria-current={activo ? 'page' : undefined}
            title={etiqueta}
            className={[
              'group flex items-center gap-3 rounded-full px-4 py-2.5 text-[13.5px] font-medium transition-all duration-200',
              activo
                ? 'bg-[#5b36f5] text-white shadow-lg shadow-[#5b36f5]/40'
                : 'text-slate-400 hover:bg-white/5 hover:text-white',
            ].join(' ')}
          >
            <Icono
              className={`size-[18px] transition-colors ${
                activo ? 'text-white' : 'text-slate-500 group-hover:text-slate-200'
              }`}
              strokeWidth={2}
            />
            {etiqueta}
          </a>
        ))}
      </nav>

      <div className="flex-1" />

      {/* Tarjeta inferior */}
      <div className="rounded-2xl bg-[#C9F5E8] p-4 text-[#1E2235] shadow-xl">
        <p className="text-[13.5px] font-bold leading-tight">
          Plan de Control
          <br />
          HSE
        </p>
        <div className="mt-3 space-y-1.5 text-[11.5px] font-medium">
          <p className="flex items-center gap-1.5">
            <span className="inline-block size-2 rounded-full bg-[#5b36f5]" />
            <span className="text-slate-600">Renews</span>
            <span className="font-bold text-[#5b36f5]">#5b36f5</span>
          </p>
          <p className="flex items-center gap-1.5">
            <span className="inline-block size-2 rounded-full bg-[#151833]" />
            <span className="text-slate-600">Context Sept. &apos;22</span>
            <span className="font-bold text-[#151833]">#151833</span>
          </p>
        </div>
        <button
          type="button"
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-[#1E2235] py-2.5 text-[12.5px] font-semibold text-white transition-all duration-200 hover:bg-[#151833] hover:shadow-lg active:scale-[0.98]"
        >
          <LogOut className="size-4" />
          Sign Out
        </button>
      </div>
    </aside>
  )
}
