export default function KpiCard({ titulo, valor, icono: Icono, acento }) {
  return (
    <article
      className="group flex items-center justify-between rounded-2xl bg-white p-5 shadow-[0_8px_30px_-12px_rgba(30,34,53,0.15)] ring-1 ring-slate-100 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_-12px_rgba(30,34,53,0.25)]"
      title={`${titulo}: ${valor}`}
    >
      <div>
        <p className="text-[12.5px] font-semibold uppercase tracking-wide text-slate-500">
          {titulo}
        </p>
        <p className="mt-1.5 text-[30px] font-extrabold tabular-nums tracking-tight text-slate-900">
          {valor}
        </p>
      </div>
      <span
        className={`grid size-12 place-items-center rounded-2xl transition-transform duration-200 group-hover:scale-110 ${acento}`}
      >
        <Icono className="size-6" strokeWidth={2} />
      </span>
    </article>
  )
}
