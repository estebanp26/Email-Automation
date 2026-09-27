import { BarChart3, Clock3, Eye, Plus } from 'lucide-react'
import ChartCard from './components/ChartCard'
import Header from './components/Header'
import KpiCard from './components/KpiCard'
import RecentMessages from './components/RecentMessages'
import Sidebar from './components/Sidebar'

const INDICADORES = [
  {
    titulo: 'Respondidos',
    valor: '1,250',
    icono: BarChart3,
    acento: 'bg-violet-100 text-[#5b36f5]',
  },
  {
    titulo: 'Pendientes',
    valor: '385',
    icono: Clock3,
    acento: 'bg-amber-100 text-amber-600',
  },
  {
    titulo: 'En Revisión',
    valor: '150',
    icono: Eye,
    acento: 'bg-sky-100 text-sky-600',
  },
]

export default function App() {
  return (
    <div className="flex min-h-screen bg-[#F4F6FB] font-sans text-slate-900">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header />

        <main className="flex-1 space-y-6 px-8 py-6 max-md:px-4">
          {/* Banner de bienvenida */}
          <section className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-[20px] font-extrabold tracking-tight">
                ¡Bienvenido de nuevo, Eliam!
              </h2>
              <p className="mt-1 text-[13px] font-medium text-slate-500">
                Tu resumen operativo al día
              </p>
            </div>
            <button
              type="button"
              title="Crear una nueva novedad"
              className="flex items-center gap-2 rounded-full bg-[#5b36f5] px-5 py-2.5 text-[13px] font-bold text-white shadow-lg shadow-[#5b36f5]/30 transition-all duration-200 hover:bg-[#4728c9] hover:shadow-xl hover:shadow-[#5b36f5]/30 active:scale-[0.98]"
            >
              <Plus className="size-4" strokeWidth={2.5} />
              Crear Novedad
            </button>
          </section>

          {/* KPI */}
          <section
            className="grid grid-cols-3 gap-5 max-lg:grid-cols-1"
            aria-label="Resumen de indicadores"
          >
            {INDICADORES.map((kpi) => (
              <KpiCard key={kpi.titulo} {...kpi} />
            ))}
          </section>

          {/* Gráfico + mensajes */}
          <section className="grid grid-cols-5 gap-5 max-xl:grid-cols-1">
            <div className="col-span-3 max-xl:col-span-1">
              <ChartCard />
            </div>
            <div className="col-span-2 max-xl:col-span-1">
              <RecentMessages />
            </div>
          </section>
        </main>
      </div>
    </div>
  )
}
