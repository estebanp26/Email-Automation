/**
 * Bandeja de justificaciones recientes con datos reales de la API.
 * Proyecto: Email-Automation con Strata Core.
 *
 * Descripción:
 *   Muestra los registros de vw_recent_justifications con estados de
 *   carga, error y vacío. Al seleccionar un registro avisa al padre
 *   para abrir la vista dividida con sus evidencias (spatial_boxes).
 */
import { ChevronRight, Inbox } from 'lucide-react'
import {
  formatearHora,
  obtenerIniciales,
} from '../lib/cliente_api'

const COLOR_ESTADO = {
  APROBADO_AUTO: 'bg-emerald-500',
  APROBADO_MANUAL: 'bg-emerald-500',
  RECHAZADO_AUTO: 'bg-red-400',
  RECHAZADO_MANUAL: 'bg-red-400',
  REVISION_MANUAL: 'bg-amber-400',
}

function colorPorEstado(estado) {
  return COLOR_ESTADO[estado] || 'bg-slate-300'
}

export default function RecentMessages({
  registros = [],
  cargando = false,
  error = null,
  seleccionadoId = null,
  alSeleccionar,
  alReintentar,
}) {
  const resumenTipos = registros.reduce((acumulado, registro) => {
    const clave = registro.tipo_novedad || 'Sin clasificar'
    acumulado[clave] = (acumulado[clave] || 0) + 1
    return acumulado
  }, {})
  const entradasResumen = Object.entries(resumenTipos).slice(0, 5)

  return (
    <section
      className="flex flex-col rounded-2xl bg-white p-6 shadow-[0_8px_30px_-12px_rgba(30,34,53,0.15)] ring-1 ring-slate-100"
      aria-label="Justificaciones recientes reales"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-[15.5px] font-bold tracking-tight text-slate-900">
          Justificaciones Recientes
        </h2>
        <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-[12px] font-bold tabular-nums text-slate-700">
          {cargando ? '…' : `${registros.length} casos`}
        </span>
      </div>

      {/* Estado de carga */}
      {cargando && (
        <div className="mt-4 space-y-3" aria-label="Cargando justificaciones">
          {[0, 1, 2].map((clave) => (
            <div key={clave} className="flex animate-pulse gap-3 rounded-2xl bg-[#F4F6FB] p-4 ring-1 ring-slate-100">
              <span className="size-10 shrink-0 rounded-full bg-slate-200" />
              <div className="flex-1 space-y-2">
                <div className="h-3 w-2/3 rounded bg-slate-200" />
                <div className="h-3 w-full rounded bg-slate-200" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Estado de error */}
      {!cargando && error && (
        <div className="mt-4 rounded-2xl bg-red-50 p-4 text-center ring-1 ring-red-100" role="alert">
          <p className="text-[13px] font-bold text-red-700">
            No se pudieron cargar las justificaciones
          </p>
          <p className="mt-1 text-[12px] text-red-500">{error}</p>
          <button
            type="button"
            onClick={alReintentar}
            className="mt-3 rounded-full bg-red-600 px-4 py-2 text-[12px] font-bold text-white transition-colors hover:bg-red-700"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* Estado vacío */}
      {!cargando && !error && registros.length === 0 && (
        <div className="mt-4 flex flex-col items-center rounded-2xl bg-[#F4F6FB] p-8 text-center ring-1 ring-slate-100">
          <Inbox className="size-8 text-slate-300" />
          <p className="mt-2 text-[13px] font-bold text-slate-700">
            No hay justificaciones recientes
          </p>
          <p className="mt-1 text-[12px] text-slate-500">
            Cuando ingresen correos al sistema aparecerán en esta bandeja.
          </p>
        </div>
      )}

      {/* Lista real */}
      {!cargando && !error && registros.length > 0 && (
        <ul className="slim-scroll mt-4 max-h-[320px] space-y-2 overflow-y-auto pr-1">
          {registros.map((registro) => {
            const seleccionado = registro.id === seleccionadoId
            return (
              <li key={registro.id}>
                <button
                  type="button"
                  onClick={() => alSeleccionar?.(registro)}
                  title={`Ver ${registro.sender_name || 'caso'} — ${registro.email_subject || ''}`}
                  className={[
                    'flex w-full gap-3 rounded-2xl p-3 text-left ring-1 transition-all duration-200',
                    seleccionado
                      ? 'bg-[#5b36f5]/5 ring-[#5b36f5]/30'
                      : 'bg-[#F4F6FB] ring-slate-100 hover:bg-slate-100',
                  ].join(' ')}
                >
                  <span
                    className="grid size-10 shrink-0 place-items-center rounded-full bg-[#5b36f5] text-[12px] font-bold text-white"
                    aria-hidden="true"
                  >
                    {obtenerIniciales(registro.sender_name)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate text-[13px] font-bold text-slate-900">
                        {registro.sender_name || 'Sin remitente'}
                      </span>
                      <span className="shrink-0 text-[11px] font-medium text-slate-400">
                        {formatearHora(registro.created_at)}
                      </span>
                    </span>
                    <span className="mt-0.5 block truncate text-[12px] font-semibold text-slate-700">
                      {registro.email_subject || 'Sin asunto'}
                    </span>
                    <span className="mt-1 flex items-center gap-2 text-[11px] font-medium text-slate-500">
                      <span className={`inline-block size-2 rounded-full ${colorPorEstado(registro.status)}`} />
                      {registro.status || 'Sin estado'}
                      <span aria-hidden="true">·</span>
                      {registro.tipo_novedad || 'Sin clasificar'}
                      <span aria-hidden="true">·</span>
                      {registro.total_adjuntos ?? 0} adjuntos
                    </span>
                  </span>
                  <ChevronRight className="size-4 shrink-0 self-center text-slate-300" />
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {/* Resumen por tipo real */}
      {!cargando && !error && entradasResumen.length > 0 && (
        <ul className="mt-4 space-y-1 border-t border-slate-100 pt-3" aria-label="Resumen por tipo de novedad">
          {entradasResumen.map(([etiqueta, valor]) => (
            <li
              key={etiqueta}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-[13px] font-medium text-slate-600"
            >
              <span className="flex items-center gap-2.5">
                <span className="inline-block size-2.5 rounded-full bg-[#5b36f5]" />
                {etiqueta}
              </span>
              <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-[12.5px] font-bold tabular-nums text-slate-800">
                {valor}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
