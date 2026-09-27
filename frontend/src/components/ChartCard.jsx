import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const DATOS = [
  { mes: 'Ene', monto: 13.2, meta: 14 },
  { mes: 'Feb', monto: 9.5, meta: 14 },
  { mes: 'Mar', monto: 12.4, meta: 14 },
  { mes: 'Abr', monto: 6.8, meta: 14 },
  { mes: 'May', monto: 11.1, meta: 14 },
  { mes: 'Jun', monto: 8.3, meta: 14 },
  { mes: 'Jun', monto: 10.6, meta: 14 },
]

function ContenidoEmergente({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-slate-100 bg-white px-3 py-2 text-xs shadow-xl">
      <p className="font-bold text-slate-900">{label}</p>
      <p className="mt-1 font-semibold text-[#ff6b6b]">
        Monto: ${payload[0]?.value}k
      </p>
      <p className="font-medium text-slate-400">Meta: ${payload[1]?.value}k</p>
    </div>
  )
}

export default function ChartCard() {
  return (
    <section
      className="rounded-2xl bg-white p-6 shadow-[0_8px_30px_-12px_rgba(30,34,53,0.15)] ring-1 ring-slate-100"
      aria-label="Flujo de ingesta mensual"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-[15.5px] font-bold tracking-tight text-slate-900">
            Flujo de Ingesta Mensual
          </h2>
          <p className="mt-0.5 text-[12px] font-medium text-slate-400">
            Hectáre vs Expsines, Last 6 months
          </p>
        </div>
        <div className="flex items-center gap-4 text-[11.5px] font-semibold">
          <span className="flex items-center gap-1.5 text-slate-600">
            <span className="inline-block size-2.5 rounded-full bg-[#ff6b6b]" />
            Sales Amount
          </span>
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="inline-block size-2.5 rounded-full bg-slate-200" />
            Monthly Goal
          </span>
        </div>
      </div>

      <div className="mt-4 h-[260px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={DATOS} barCategoryGap="28%" margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
            <CartesianGrid vertical={false} stroke="#eef1f6" strokeDasharray="0" />
            <XAxis
              dataKey="mes"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12, fontWeight: 600, fill: '#94a3b8' }}
              dy={8}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12, fontWeight: 500, fill: '#94a3b8' }}
              ticks={[0, 4, 7, 11, 14]}
              tickFormatter={(v) => `$${v}k`}
            />
            <Tooltip content={<ContenidoEmergente />} cursor={{ fill: '#f4f6fb' }} />
            <Bar dataKey="meta" fill="#eef1f6" radius={[6, 6, 6, 6]} barSize={22} />
            <Bar dataKey="monto" fill="#ff6b6b" radius={[6, 6, 6, 6]} barSize={22} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
