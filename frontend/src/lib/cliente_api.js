/**
 * Cliente HTTP del tablero HSE hacia la API puente.
 * Proyecto: Email-Automation con Strata Core.
 *
 * Descripción:
 *   Centraliza las lecturas reales de indicadores, justificaciones
 *   recientes, evidencias con cajas espaciales e identificación de
 *   codificadores. Base configurable con VITE_API_URL.
 */

const baseApi =
  import.meta.env.VITE_API_URL?.replace(/\/$/, '') || ''

function construirUrl(ruta) {
  return `${baseApi}${ruta}`
}

async function leerRespuesta(respuesta) {
  let cuerpo = null
  try {
    cuerpo = await respuesta.json()
  } catch {
    cuerpo = null
  }
  if (!respuesta.ok) {
    const mensaje =
      cuerpo?.detail || cuerpo?.error || `Error HTTP ${respuesta.status}`
    throw new Error(mensaje)
  }
  return cuerpo
}

/** Obtiene las métricas agregadas de vw_dashboard_kpis. */
export async function obtenerKpis(opciones = {}) {
  const respuesta = await fetch(construirUrl('/api/kpis'), {
    signal: opciones.senal,
  })
  return leerRespuesta(respuesta)
}

/** Obtiene las justificaciones recientes de vw_recent_justifications. */
export async function obtenerRecientes(limite = 20, opciones = {}) {
  const respuesta = await fetch(
    construirUrl(`/api/justificaciones/recientes?limite=${limite}`),
    { signal: opciones.senal },
  )
  return leerRespuesta(respuesta)
}

/** Obtiene los adjuntos con spatial_boxes de una justificación. */
export async function obtenerEvidencias(identificador, opciones = {}) {
  const respuesta = await fetch(
    construirUrl(`/api/justificaciones/${identificador}/evidencias`),
    { signal: opciones.senal },
  )
  return leerRespuesta(respuesta)
}

/** Identifica un codificador con la triple llave [correo, documento, nombre]. */
export async function identificarCodificador({ correo, documento, nombre }) {
  const respuesta = await fetch(construirUrl('/api/coders/identificar'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      p_email: correo || null,
      p_cc: documento || null,
      p_name: nombre || null,
    }),
  })
  return leerRespuesta(respuesta)
}

/** Formatea fechas ISO a hora local corta de Bogotá. */
export function formatearHora(fechaIso) {
  if (!fechaIso) return 'Sin fecha'
  const fecha = new Date(fechaIso)
  if (Number.isNaN(fecha.getTime())) return 'Sin fecha'
  return fecha.toLocaleString('es-CO', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Iniciales para el avatar a partir del nombre real del codificador. */
export function obtenerIniciales(nombre) {
  if (!nombre) return 'NA'
  const partes = nombre.trim().split(/\s+/)
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase()
  return (partes[0][0] + partes[1][0]).toUpperCase()
}
