import { ChevronRight } from 'lucide-react'

const RESUMEN = [
  { etiqueta: 'Incapacidad Médica', valor: 24, punto: 'bg-blue-500' },
  { etiqueta: 'Equipo', valor: 16, punto: 'bg-emerald-500' },
  { etiqueta: 'Constancia Laboral', valor: 5, punto: 'bg-orange-400' },
]

export default function RecentMessages() {
  return (
    <section
      className="flex flex-col rounded-2xl bg-white p-6 shadow-[0_8px_30px_-12px_rgba(30,34,53,0.15)] ring-1 ring-slate-100"
      aria-label="Gestión de mensajes recientes"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-[15.5px] font-bold tracking-tight text-slate-900">
          Gestión de Mensajes Recientes
        </h2>
        <button
          type="button"
          title="Ver todas las justificaciones"
          className="flex items-center gap-1 text-[12px] font-bold text-[#5b36f5] transition-colors hover:text-[#4728c9]"
        >
          Ver todo
          <ChevronRight className="size-3.5" />
        </button>
      </div>

      {/* Mensaje destacado */}
      <article className="mt-4 flex gap-3 rounded-2xl bg-[#F4F6FB] p-4 ring-1 ring-slate-100 transition-all duration-200 hover:bg-slate-100">
        <span
          className="grid size-10 shrink-0 place-items-center rounded-full bg-[#5b36f5] text-[12px] font-bold text-white"
          aria-hidden="true"
        >
          JP
        </span>
        <div className="min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-[13px] font-bold text-slate-900">
              Juan Perez
            </p>
            <span className="shrink-0 text-[11px] font-medium text-slate-400">
              hace 10 min
            </span>
          </div>
          <p className="mt-0.5 truncate text-[12px] font-semibold text-slate-700">
            Sub: Problemas de iluminación en Calle 10
          </p>
          <p className="mt-0.5 line-clamp-2 text-[12px] leading-relaxed text-slate-500">
            Hola, solicito la revisión de las luminarias del sector porque
            permanecen apagadas…
          </p>
        </div>
      </article>

      {/* Contadores por tipo */}
      <ul className="mt-4 space-y-1">
        {RESUMEN.map(({ etiqueta, valor, punto }) => (
          <li key={etiqueta}>
            <button
              type="button"
              title={`Ver ${etiqueta}`}
              className="group flex w-full items-center justify-between rounded-xl px-3 py-2.5 transition-colors duration-200 hover:bg-slate-50"
            >
              <span className="flex items-center gap-2.5 text-[13px] font-medium text-slate-600 group-hover:text-slate-900">
                <span className={`inline-block size-2.5 rounded-full ${punto}`} />
                {etiqueta}
              </span>
              <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-[12.5px] font-bold tabular-nums text-slate-800 transition-colors group-hover:bg-[#1E2235] group-hover:text-white">
                {valor}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
