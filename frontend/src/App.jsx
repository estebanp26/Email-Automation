/**
 * Tablero HSE con datos reales de la API puente.
 * Proyecto: Email-Automation con Strata Core.
 *
 * Descripción:
 *   Carga indicadores y justificaciones recientes desde /api/kpis y
 *   /api/justificaciones/recientes. Gestiona carga, error y vacío, y
 *   abre la vista dividida con evidencias (spatial_boxes) al
 *   seleccionar un caso.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Bot, CircleCheckBig, Clock3, Inbox, Plus } from 'lucide-react'
import ChartCard from './components/ChartCard'
import Header from './components/Header'
import KpiCard from './components/KpiCard'
import RecentMessages from './components/RecentMessages'
import Sidebar from './components/Sidebar'
import VistaDividida from './components/VistaDividida'
import {
  obtenerEvidencias,
  obtenerKpis,
  obtenerRecientes,
} from './lib/cliente_api'

function formatoNumero(valor) {
  if (valor === null || valor === undefined) return '0'
  return Number(valor).toLocaleString('es-CO')
}

export default function App() {
  const [kpis, setKpis] = useState(null)
  const [registros, setRegistros] = useState([])
  const [cargandoKpis, setCargandoKpis] = useState(true)
  const [cargandoCasos, setCargandoCasos] = useState(true)
  const [errorKpis, setErrorKpis] = useState(null)
  const [errorCasos, setErrorCasos] = useState(null)
  const [seleccionada, setSeleccionada] = useState(null)
  const [evidencias, setEvidencias] = useState([])
  const [cargandoEvidencias, setCargandoEvidencias] = useState(false)
  const [errorEvidencias, setErrorEvidencias] = useState(null)

  const cargarTablero = useCallback(async (senal) => {
    setCargandoKpis(true)
    setCargandoCasos(true)
    setErrorKpis(null)
    setErrorCasos(null)
    try {
      const indicadores = await obtenerKpis({ senal })
      setKpis(indicadores)
    } catch (error) {
      if (error.name !== 'AbortError') setErrorKpis(error.message)
    } finally {
      setCargandoKpis(false)
    }
    try {
      const respuesta = await obtenerRecientes(20, { senal })
      setRegistros(respuesta.registros || [])
    } catch (error) {
      if (error.name !== 'AbortError') setErrorCasos(error.message)
    } finally {
      setCargandoCasos(false)
    }
  }, [])

  useEffect(() => {
    const controlador = new AbortController()
    cargarTablero(controlador.signal)
    return () => controlador.abort()
  }, [cargarTablero])

  const manejarSeleccion = useCallback(async (registro) => {
    setSeleccionada(registro)
    setEvidencias([])
    setErrorEvidencias(null)
    setCargandoEvidencias(true)
    try {
      const respuesta = await obtenerEvidencias(registro.id)
      setEvidencias(respuesta.evidencias || [])
    } catch (error) {
      setErrorEvidencias(error.message)
    } finally {
      setCargandoEvidencias(false)
    }
  }, [])

  const indicadores = useMemo(
    () => [
      {
        titulo: 'Recibidas',
        valor: formatoNumero(kpis?.total_recibidos),
        icono: Inbox,
        acento: 'bg-violet-100 text-[#5b36f5]',
      },
      {
        titulo: 'Aprobadas',
        valor: formatoNumero(kpis?.total_aprobados),
        icono: CircleCheckBig,
        acento: 'bg-emerald-100 text-emerald-600',
      },
      {
        titulo: 'Pendientes',
        valor: formatoNumero(kpis?.total_pendientes),
        icono: Clock3,
        acento: 'bg-amber-100 text-amber-600',
      },
      {
        titulo: 'Automatización',
        valor: kpis?.tasa_automatizacion_pct === null || kpis?.tasa_automatizacion_pct === undefined
          ? '0%'
          : `${kpis.tasa_automatizacion_pct}%`,
        icono: Bot,
        acento: 'bg-sky-100 text-sky-600',
      },
    ],
    [kpis],
  )

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
                Tablero HSE — Riwi
              </h2>
              <p className="mt-1 text-[13px] font-medium text-slate-500">
                Justificaciones reales con evidencias verificables
              </p>
            </div>
            <button
              type="button"
              title="Reintentar carga de datos reales"
              onClick={() => cargarTablero()}
              className="flex items-center gap-2 rounded-full bg-[#5b36f5] px-5 py-2.5 text-[13px] font-bold text-white shadow-lg shadow-[#5b36f5]/30 transition-all duration-200 hover:bg-[#4728c9] hover:shadow-xl hover:shadow-[#5b36f5]/30 active:scale-[0.98]"
            >
              <Plus className="size-4" strokeWidth={2.5} />
              Actualizar datos
            </button>
          </section>

          {/* Indicadores reales */}
          <section
            className="grid grid-cols-4 gap-5 max-lg:grid-cols-2 max-sm:grid-cols-1"
            aria-label="Resumen de indicadores reales"
          >
            {indicadores.map((indicador) => (
              <KpiCard
                key={indicador.titulo}
                {...indicador}
                cargando={cargandoKpis}
                error={errorKpis}
              />
            ))}
          </section>
          {errorKpis && (
            <p className="rounded-xl bg-red-50 px-4 py-3 text-[12.5px] font-medium text-red-600 ring-1 ring-red-100" role="alert">
              Indicadores no disponibles: {errorKpis}. Verifique que la API responda en
              {' '}{import.meta.env.VITE_API_URL || 'http://localhost:8000'}.
            </p>
          )}

          {/* Gráfico + bandeja real */}
          <section className="grid grid-cols-5 gap-5 max-xl:grid-cols-1">
            <div className="col-span-3 max-xl:col-span-1">
              <ChartCard kpis={kpis} cargando={cargandoKpis} error={errorKpis} />
            </div>
            <div className="col-span-2 max-xl:col-span-1">
              <RecentMessages
                registros={registros}
                cargando={cargandoCasos}
                error={errorCasos}
                seleccionadoId={seleccionada?.id}
                alSeleccionar={manejarSeleccion}
                alReintentar={() => cargarTablero()}
              />
            </div>
          </section>

          {/* Vista dividida con evidencias */}
          <VistaDividida
            justificacion={seleccionada}
            evidencias={evidencias}
            cargandoEvidencias={cargandoEvidencias}
            errorEvidencias={errorEvidencias}
            alCerrar={() => setSeleccionada(null)}
          />
        </main>
      </div>
    </div>
  )
}
