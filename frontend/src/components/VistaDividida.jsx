/**
 * Vista dividida de justificación y evidencias.
 * Proyecto: Email-Automation con Strata Core.
 *
 * Descripción:
 *   Panel izquierdo: detalle real de la justificación seleccionada
 *   (remitente, documento, cohorte, ruta, método de identificación y
 *   motivo de la IA). Panel derecho: evidencias con spatial_boxes.
 */
import { FileSearch, X } from 'lucide-react'
import EvidenciaAdjunta from './EvidenciaAdjunta'
import { formatearHora } from '../lib/cliente_api'

export default function VistaDividida({
  justificacion,
  evidencias = [],
  cargandoEvidencias = false,
  errorEvidencias = null,
  alCerrar,
}) {
  if (!justificacion) {
    return (
      <section
        className="flex h-full flex-col items-center justify-center rounded-2xl bg-white p-8 text-center shadow-[0_8px_30px_-12px_rgba(30,34,53,0.15)] ring-1 ring-slate-100"
        aria-label="Sin justificación seleccionada"
      >
        <FileSearch className="size-10 text-slate-200" />
        <p className="mt-3 text-[14px] font-bold text-slate-700">
          Seleccione una justificación
        </p>
        <p className="mt-1 max-w-[280px] text-[12.5px] text-slate-500">
          Pulse un caso de la bandeja para ver su detalle y las evidencias con cajas espaciales.
        </p>
      </section>
    )
  }

  return (
    <section
      className="grid grid-cols-2 gap-4 max-lg:grid-cols-1"
      aria-label={`Detalle de ${justificacion.sender_name || 'justificación'}`}
    >
      {/* Panel izquierdo: detalle */}
      <article className="rounded-2xl bg-white p-6 shadow-[0_8px_30px_-12px_rgba(30,34,53,0.15)] ring-1 ring-slate-100">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11.5px] font-bold uppercase tracking-wide text-[#5b36f5]">
              {justificacion.status || 'Sin estado'}
            </p>
            <h2 className="mt-1 text-[16px] font-extrabold tracking-tight text-slate-900">
              {justificacion.sender_name || 'Sin remitente'}
            </h2>
            <p className="mt-0.5 text-[12.5px] font-medium text-slate-500">
              {justificacion.sender_email || 'Sin correo'} · {formatearHora(justificacion.created_at)}
            </p>
          </div>
          <button
            type="button"
            onClick={alCerrar}
            title="Cerrar detalle"
            className="grid size-8 place-items-center rounded-full bg-slate-100 text-slate-500 transition-colors hover:bg-slate-200 hover:text-slate-800"
          >
            <X className="size-4" />
          </button>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-3 text-[12.5px]">
          {[
            ['Documento', justificacion.cc_coder || 'Sin documento'],
            ['Cohorte', justificacion.cohort_group || 'Sin cohorte'],
            ['Ruta', justificacion.academic_route || 'No asignada'],
            ['Identificación', justificacion.identification_method || 'Sin método'],
            ['Tipo', justificacion.tipo_novedad || 'Sin clasificar'],
            ['Proveedor', justificacion.source_provider || 'Sin origen'],
          ].map(([etiqueta, valor]) => (
            <div key={etiqueta} className="rounded-xl bg-[#F4F6FB] px-3 py-2 ring-1 ring-slate-100">
              <dt className="text-[11px] font-bold uppercase tracking-wide text-slate-400">{etiqueta}</dt>
              <dd className="mt-0.5 font-semibold text-slate-800">{valor}</dd>
            </div>
          ))}
        </dl>

        <div className="mt-4">
          <p className="text-[12px] font-bold uppercase tracking-wide text-slate-400">Asunto</p>
          <p className="mt-1 text-[13px] font-semibold text-slate-800">
            {justificacion.email_subject || 'Sin asunto'}
          </p>
        </div>
        <div className="mt-3">
          <p className="text-[12px] font-bold uppercase tracking-wide text-slate-400">Motivo de la decisión</p>
          <p className="mt-1 text-[13px] leading-relaxed text-slate-600">
            {justificacion.motivo_decision || 'Sin motivo registrado por la IA.'}
          </p>
        </div>
      </article>

      {/* Panel derecho: evidencias */}
      <article className="rounded-2xl bg-white p-6 shadow-[0_8px_30px_-12px_rgba(30,34,53,0.15)] ring-1 ring-slate-100">
        <h3 className="text-[14px] font-bold tracking-tight text-slate-900">
          Evidencias ({cargandoEvidencias ? '…' : evidencias.length})
        </h3>
        {cargandoEvidencias && (
          <div className="mt-4 space-y-3" aria-label="Cargando evidencias">
            {[0, 1].map((clave) => (
              <div key={clave} className="h-28 animate-pulse rounded-2xl bg-slate-100" />
            ))}
          </div>
        )}
        {!cargandoEvidencias && errorEvidencias && (
          <p className="mt-4 rounded-xl bg-red-50 p-3 text-[12.5px] font-medium text-red-600" role="alert">
            No se pudieron cargar las evidencias: {errorEvidencias}
          </p>
        )}
        {!cargandoEvidencias && !errorEvidencias && evidencias.length === 0 && (
          <p className="mt-4 rounded-xl bg-[#F4F6FB] p-4 text-[12.5px] text-slate-500 ring-1 ring-slate-100">
            Esta justificación aún no tiene adjuntos con cajas espaciales.
          </p>
        )}
        {!cargandoEvidencias && !errorEvidencias && evidencias.length > 0 && (
          <div className="slim-scroll mt-4 max-h-[420px] space-y-3 overflow-y-auto pr-1">
            {evidencias.map((evidencia) => (
              <EvidenciaAdjunta key={evidencia.id} evidencia={evidencia} />
            ))}
          </div>
        )}
      </article>
    </section>
  )
}
