export interface CoderSession {
  id?: string;
  name: string;
  cedula: string;
  email: string;
  route: string;
  group?: string;
}

export function getCoderSession(): CoderSession {
  const fallback: CoderSession = {
    name: 'Coder Riwi',
    cedula: '1000000126',
    email: 'coder@riwi.io',
    route: 'Desarrollo de Software',
  };

  try {
    const raw = localStorage.getItem('hse_coder_session');
    if (raw) {
      return { ...fallback, ...JSON.parse(raw) };
    }
  } catch (e) {
    console.warn('Error leyendo sesión de coder:', e);
  }
  return fallback;
}
