/**
 * Gráfico de justificaciones por estado con datos reales.
 * Proyecto: Email-Automation con Strata Core.
 *
 * Descripción:
 *   Construye la distribución a partir de los indicadores reales de
 *   vw_dashboard_kpis. Sin datos simulados de ventas ni metas en inglés.
 */
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function ContenidoEmergente({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-slate-100 bg-white px-3 py-2 text-xs shadow-xl">
      <p className="font-bold text-slate-900">{label}</p>
      <p className="mt-1 font-semibold text-[#5b36f5]">
        Casos: {payload[0]?.value}
      </p>
    </div>
  )
}

export default function ChartCard({ kpis = null, cargando = false, error = null }) {
  const datos = kpis
    ? [
        { estado: 'Aprobadas', casos: Number(kpis.total_aprobados || 0) },
        { estado: 'Rechazadas', casos: Number(kpis.total_rechazados || 0) },
        { estado: 'Pendientes', casos: Number(kpis.total_pendientes || 0) },
      ]
    : []

  const total = datos.reduce((acumulado, fila) => acumulado + fila.casos, 0)

  return (
    <section
      className="rounded-2xl bg-white p-6 shadow-[0_8px_30px_-12px_rgba(30,34,53,0.15)] ring-1 ring-slate-100"
      aria-label="Justificaciones por estado"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-[15.5px] font-bold tracking-tight text-slate-900">
            Justificaciones por Estado
          </h2>
          <p className="mt-0.5 text-[12px] font-medium text-slate-400">
            Distribución real del sistema HSE de Riwi
          </p>
        </div>
        <span className="rounded-lg bg-[#F4F6FB] px-3 py-1.5 text-[12px] font-bold tabular-nums text-slate-700 ring-1 ring-slate-100">
          {cargando ? '…' : `${total} casos`}
        </span>
      </div>

      {cargando && (
        <div className="mt-4 h-[260px] animate-pulse rounded-xl bg-slate-100" aria-label="Cargando gráfico" />
      )}
      {!cargando && error && (
        <p className="mt-4 rounded-xl bg-red-50 p-4 text-[13px] font-medium text-red-600" role="alert">
          No se pudo cargar el gráfico: {error}
        </p>
      )}
      {!cargando && !error && total === 0 && (
        <p className="mt-4 rounded-xl bg-[#F4F6FB] p-6 text-center text-[13px] text-slate-500 ring-1 ring-slate-100">
          Aún no hay justificaciones para graficar. Los casos nuevos aparecerán aquí automáticamente.
        </p>
      )}
      {!cargando && !error && total > 0 && (
        <div className="mt-4 h-[260px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={datos} barCategoryGap="28%" margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
              <CartesianGrid vertical={false} stroke="#eef1f6" strokeDasharray="0" />
              <XAxis
                dataKey="estado"
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 12, fontWeight: 600, fill: '#94a3b8' }}
                dy={8}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 12, fontWeight: 500, fill: '#94a3b8' }}
                allowDecimals={false}
              />
              <Tooltip content={<ContenidoEmergente />} cursor={{ fill: '#f4f6fb' }} />
              <Bar dataKey="casos" fill="#5b36f5" radius={[6, 6, 6, 6]} barSize={42} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  )
}
