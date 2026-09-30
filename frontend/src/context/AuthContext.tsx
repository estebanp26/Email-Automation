import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { AuthContextType, AuthUser } from '../types';
import { decodeJwt, isTokenExpired, normalizeRole } from '../utils/jwt';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Cerrar sesión y limpiar almacenamiento
  const logout = useCallback(() => {
    localStorage.removeItem('hse_token');
    localStorage.removeItem('hse_role');
    localStorage.removeItem('hse_coder_session');
    setToken(null);
    setUser(null);
  }, []);

  // Iniciar sesión con un nuevo token JWT
  const login = useCallback((newToken: string, userData?: Partial<AuthUser>) => {
    if (!newToken || isTokenExpired(newToken)) {
      console.warn('Intento de login con token inválido o expirado');
      logout();
      return;
    }

    const payload = decodeJwt(newToken);
    if (!payload) {
      console.warn('No se pudo decodificar el payload del token');
      logout();
      return;
    }

    const normalizedRole = normalizeRole(userData?.role || payload.role);
    const authUser: AuthUser = {
      id: userData?.id || payload.sub || 'user-unknown',
      email: userData?.email || payload.email || '',
      name: userData?.name || payload.name || 'Usuario',
      role: normalizedRole,
      cedula: userData?.cedula || payload.cedula,
      route: userData?.route || payload.route,
    };

    // Persistir en localStorage
    localStorage.setItem('hse_token', newToken);
    localStorage.setItem('hse_role', normalizedRole);

    // Mantener compatibilidad con módulo de Coder
    if (normalizedRole === 'CODER') {
      const coderSession = {
        id: authUser.id,
        name: authUser.name,
        cedula: authUser.cedula || '',
        email: authUser.email,
        route: authUser.route || 'Desarrollo de Software',
      };
      localStorage.setItem('hse_coder_session', JSON.stringify(coderSession));
    }

    setToken(newToken);
    setUser(authUser);
  }, [logout]);

  // Recuperación automática de sesión al montar o recargar (F5)
  useEffect(() => {
    try {
      const savedToken = localStorage.getItem('hse_token');
      const savedRole = localStorage.getItem('hse_role');

      if (!savedToken) {
        logout();
        setIsLoading(false);
        return;
      }

      // Validar si el token está expirado o corrupto
      if (isTokenExpired(savedToken)) {
        console.info('Sesión expirada detectada. Cerrando sesión...');
        logout();
        setIsLoading(false);
        return;
      }

      const payload = decodeJwt(savedToken);
      if (!payload) {
        console.warn('Token guardado con formato inválido');
        logout();
        setIsLoading(false);
        return;
      }

      const normalizedRole = normalizeRole(savedRole || payload.role);
      
      // Intentar recuperar datos adicionales si es coder
      let coderData: any = {};
      if (normalizedRole === 'CODER') {
        try {
          const rawCoder = localStorage.getItem('hse_coder_session');
          if (rawCoder) coderData = JSON.parse(rawCoder);
        } catch {
          // ignore
        }
      }

      const recoveredUser: AuthUser = {
        id: payload.sub || coderData.id || 'user-id',
        email: payload.email || coderData.email || '',
        name: payload.name || coderData.name || 'Usuario',
        role: normalizedRole,
        cedula: payload.cedula || coderData.cedula,
        route: payload.route || coderData.route,
      };

      setToken(savedToken);
      setUser(recoveredUser);
      if (!savedRole) {
        localStorage.setItem('hse_role', normalizedRole === 'HSE_ANALYST' ? 'hse' : normalizedRole.toLowerCase());
      }
    } catch (e) {
      console.error('Error restaurando sesión:', e);
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: Boolean(user && token && !isTokenExpired(token)),
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe ser utilizado dentro de un AuthProvider');
  }
  return context;
}

export default AuthContext;
