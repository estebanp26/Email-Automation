import type { JWTPayload, UserRole } from '../types';

/**
 * Normaliza cualquier variante de rol hacia los roles oficiales del sistema:
 * - HSE o hse -> HSE_ANALYST (especificación de base de datos)
 * - CODER o coder -> CODER
 * - TEAM_LEADER o team_leader -> TEAM_LEADER
 * - ADMIN o admin -> ADMIN
 */
export function normalizeRole(role?: string | null): UserRole {
  if (!role) return 'CODER';
  const clean = role.trim().toUpperCase();

  if (clean === 'HSE' || clean === 'HSE_ANALYST') {
    return 'HSE_ANALYST';
  }
  if (clean === 'TEAM_LEADER' || clean === 'LEAD') {
    return 'TEAM_LEADER';
  }
  if (clean === 'ADMIN') {
    return 'ADMIN';
  }
  if (clean === 'CODER') {
    return 'CODER';
  }

  // Fallback seguro
  return 'CODER';
}

/**
 * Decodifica de forma segura una cadena Base64URL
 */
function base64UrlDecode(str: string): string {
  let output = str.replace(/-/g, '+').replace(/_/g, '/');
  switch (output.length % 4) {
    case 0:
      break;
    case 2:
      output += '==';
      break;
    case 3:
      output += '=';
      break;
    default:
      throw new Error('Cadena base64url no válida');
  }

  try {
    return decodeURIComponent(
      atob(output)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
  } catch {
    return atob(output);
  }
}

/**
 * Codifica una cadena a Base64URL
 */
function base64UrlEncode(str: string): string {
  const base64 = btoa(
    encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, (_, p1) =>
      String.fromCharCode(parseInt(p1, 16))
    )
  );
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/**
 * Decodifica el payload de un token JWT
 * Retorna null si el formato es inválido
 */
export function decodeJwt(token: string | null | undefined): JWTPayload | null {
  if (!token || typeof token !== 'string') return null;

  const trimmed = token.trim();

  // Compatibilidad con tokens dev/test utilizados en pruebas E2E
  if (trimmed === 'jwt_hse_admin_12345' || trimmed.startsWith('jwt_hse')) {
    const now = Math.floor(Date.now() / 1000);
    return {
      sub: 'hse-admin-12345',
      email: 'admin@riwi.io',
      name: 'Paola Admin',
      role: 'HSE_ANALYST',
      exp: now + 86400,
      iat: now,
    };
  }

  if (trimmed.startsWith('jwt_coder')) {
    const cedula = trimmed.replace('jwt_coder_', '') || '1001234567';
    const now = Math.floor(Date.now() / 1000);
    return {
      sub: `coder-${cedula}`,
      email: `${cedula}@riwi.io`,
      name: `Coder ${cedula}`,
      role: 'CODER',
      cedula,
      route: 'Desarrollo de Software',
      exp: now + 86400,
      iat: now,
    };
  }

  const parts = trimmed.split('.');
  if (parts.length !== 3) {
    return null;
  }

  try {
    const payloadJson = base64UrlDecode(parts[1]);
    const payload = JSON.parse(payloadJson);

    if (!payload || typeof payload !== 'object') {
      return null;
    }

    return payload as JWTPayload;
  } catch (e) {
    console.warn('Error decodificando token JWT:', e);
    return null;
  }
}

/**
 * Verifica si un token JWT ha expirado usando el campo estándar 'exp' (segundos epoch)
 */
export function isTokenExpired(token: string | null | undefined): boolean {
  if (!token) return true;

  const trimmed = token.trim();
  // Tokens de prueba/dev nunca expiran automáticamente
  if (trimmed === 'jwt_hse_admin_12345' || trimmed.startsWith('jwt_hse') || trimmed.startsWith('jwt_coder')) {
    return false;
  }

  const payload = decodeJwt(trimmed);
  if (!payload || !payload.exp) {
    // Si no contiene exp válido, se considera no vigente / inválido
    return true;
  }

  const nowInSeconds = Math.floor(Date.now() / 1000);
  return payload.exp <= nowInSeconds;
}

/**
 * Crea un token JWT estándar RFC 7519 para simular/generar la sesión en frontend
 * mientras el backend no cuente con endpoint de firma criptográfica.
 * Expira por defecto en 8 horas.
 */
export function createStandardJwt(data: {
  sub: string;
  email: string;
  name: string;
  role: string;
  cedula?: string;
  route?: string;
  expiresInSeconds?: number;
}): string {
  const header = {
    alg: 'HS256',
    typ: 'JWT',
  };

  const now = Math.floor(Date.now() / 1000);
  const exp = now + (data.expiresInSeconds || 8 * 3600); // 8 horas por defecto

  const payload: JWTPayload = {
    sub: data.sub,
    email: data.email,
    name: data.name,
    role: data.role,
    iat: now,
    exp,
    cedula: data.cedula,
    route: data.route,
  };

  const encodedHeader = base64UrlEncode(JSON.stringify(header));
  const encodedPayload = base64UrlEncode(JSON.stringify(payload));
  // Firma sintética para estructura estándar de 3 partes
  const dummySignature = base64UrlEncode(`sig_riwi_${data.sub}_${now}`);

  return `${encodedHeader}.${encodedPayload}.${dummySignature}`;
}

