export default function KpiCard({ titulo, valor, icono: Icono, acento, cargando = false, error = null }) {
  const contenido = cargando ? '…' : (error ? '—' : (valor ?? '0'))
  return (
    <article
      className="group flex items-center justify-between rounded-2xl bg-white p-5 shadow-[0_8px_30px_-12px_rgba(30,34,53,0.15)] ring-1 ring-slate-100 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_-12px_rgba(30,34,53,0.25)]"
      title={error ? `Error al cargar ${titulo}` : `${titulo}: ${contenido}`}
      aria-busy={cargando}
    >
      <div>
        <p className="text-[12.5px] font-semibold uppercase tracking-wide text-slate-500">
          {titulo}
        </p>
        {cargando ? (
          <div className="mt-2 h-9 w-24 animate-pulse rounded-lg bg-slate-100" aria-label="Cargando indicador" />
        ) : (
          <p className="mt-1.5 text-[30px] font-extrabold tabular-nums tracking-tight text-slate-900">
            {contenido}
          </p>
        )}
        {error && (
          <p className="mt-1 text-[11.5px] font-medium text-red-500">
            No se pudo cargar
          </p>
        )}
      </div>
      <span
        className={`grid size-12 place-items-center rounded-2xl transition-transform duration-200 group-hover:scale-110 ${acento}`}
      >
        <Icono className="size-6" strokeWidth={2} />
      </span>
    </article>
  )
}
