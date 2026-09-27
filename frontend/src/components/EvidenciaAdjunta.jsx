/**
 * Tarjeta de evidencias con cajas espaciales de Strata Core.
 * Proyecto: Email-Automation con Strata Core.
 *
 * Descripción:
 *   Presenta cada adjunto de justification_attachments con sus
 *   spatial_boxes (sellos, firmas, fechas, nombres) para la
 *   auditoría visual de la Team Leader en la vista dividida.
 */
import { FileText, ScanSearch } from 'lucide-react'

function listaCajas(cajas) {
  if (!cajas) return []
  if (Array.isArray(cajas)) return cajas
  if (Array.isArray(cajas.cajas)) return cajas.cajas
  if (Array.isArray(cajas.boxes)) return cajas.boxes
  return []
}

export default function EvidenciaAdjunta({ evidencia }) {
  const cajas = listaCajas(evidencia.spatial_boxes)
  return (
    <article className="rounded-2xl bg-[#F4F6FB] p-4 ring-1 ring-slate-100">
      <div className="flex items-center gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white text-[#5b36f5] ring-1 ring-slate-100">
          <FileText className="size-5" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-[13px] font-bold text-slate-900">
            {evidencia.file_name || 'Adjunto sin nombre'}
          </p>
          <p className="text-[11.5px] font-medium text-slate-500">
            {evidencia.mime_type || 'Tipo desconocido'}
            {evidencia.file_size_bytes ? ` · ${(evidencia.file_size_bytes / 1024).toFixed(1)} KB` : ''}
          </p>
        </div>
      </div>

      {evidencia.file_path_or_url && (
        <a
          href={evidencia.file_path_or_url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 block truncate text-[12px] font-semibold text-[#5b36f5] hover:underline"
          title="Abrir evidencia original"
        >
          Abrir evidencia original
        </a>
      )}

      <div className="mt-3 rounded-xl bg-white p-3 ring-1 ring-slate-100">
        <p className="flex items-center gap-1.5 text-[12px] font-bold text-slate-800">
          <ScanSearch className="size-4 text-[#5b36f5]" />
          Cajas espaciales ({cajas.length})
        </p>
        {cajas.length === 0 ? (
          <p className="mt-1 text-[12px] text-slate-500">
            Sin cajas detectadas por Strata Core para este adjunto.
          </p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {cajas.map((caja, indice) => (
              <li
                key={indice}
                className="flex flex-wrap items-center gap-x-3 gap-y-0.5 rounded-lg bg-slate-50 px-2.5 py-1.5 text-[11.5px] font-medium text-slate-600"
              >
                <span className="font-bold text-slate-800">
                  {caja.etiqueta || caja.label || caja.tipo || `Región ${indice + 1}`}
                </span>
                <span className="tabular-nums">
                  x0:{caja.x0 ?? caja.x ?? '?'} y0:{caja.y0 ?? caja.y ?? '?'} x1:{caja.x1 ?? '?'} y1:{caja.y1 ?? '?'}
                </span>
                {caja.confianza ?? caja.confidence ? (
                  <span className="tabular-nums text-[#5b36f5]">
                    {(Number(caja.confianza ?? caja.confidence) * 100).toFixed(0)}%
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  )
}
