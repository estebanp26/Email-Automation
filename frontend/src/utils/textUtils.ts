/**
 * Utilidades para normalización de texto, validación y detección total de tildes / acentos.
 * Permite buscar y validar términos en español con o sin tildes en todo el sistema Riwi HSE.
 */

/**
 * Detecta si una cadena contiene tildes, diéresis o virgulillas (á, é, í, ó, ú, ü, ñ).
 */
export function hasTildes(str: string = ''): boolean {
  if (!str) return false;
  return /[áéíóúÁÉÍÓÚüÜñÑ]/.test(str);
}

/**
 * Normaliza a Unicode NFC asegurando que caracteres con tildes no queden descompuestos.
 */
export function ensureProperAccents(str: string = ''): string {
  if (!str) return '';
  return str.normalize('NFC');
}

/**
 * Normaliza un texto removiendo tildes / diacríticos y convirtiendo a minúsculas
 * para que búsquedas como "medica", "médica", "MEDICA" coincidan exactamente.
 */
export function stripAccents(str: string = ''): string {
  if (!str) return '';
  return str
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

/**
 * Comprueba si target contiene query ignorando tildes y mayúsculas/minúsculas.
 */
export function matchesNormalized(target: string = '', query: string = ''): boolean {
  if (!query) return true;
  return stripAccents(target).includes(stripAccents(query));
}

/**
 * Validador de texto en español: acepta letras estándar, vocales con tildes (áéíóúÁÉÍÓÚ),
 * diéresis (üÜ), eñe (ñÑ), números, puntuación básica y espacios.
 */
export function isValidSpanishText(str: string = ''): boolean {
  if (!str) return false;
  const regex = /^[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s.,;:_()\-–—/'"¿?¡!#%&*+=[\]{}]+$/;
  return regex.test(str);
}
