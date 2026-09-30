import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import type { UserRole } from '../../types';
import { isTokenExpired } from '../../utils/jwt';

export interface ProtectedRouteProps {
  children?: React.ReactNode;
  allowedRoles?: UserRole[];
}

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { user, token, isAuthenticated, isLoading, logout } = useAuth();
  const location = useLocation();

  // 1. Mientras se restaura la sesión desde localStorage, mostrar pantalla de carga
  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#171B3A] text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-[#5B3FF5] border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-slate-300 font-medium">Verificando sesión...</span>
        </div>
      </div>
    );
  }

  // 2. Si no existe sesión activa o token
  if (!isAuthenticated || !token || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 3. Validar vigencia del JWT con el campo 'exp'
  if (isTokenExpired(token)) {
    logout();
    return <Navigate to="/login" state={{ expired: true }} replace />;
  }

  // 4. Control de Acceso Basado en Roles (RBAC)
  if (allowedRoles && allowedRoles.length > 0) {
    const hasRole = allowedRoles.includes(user.role);

    if (!hasRole) {
      // Redirección obligatoria a /403 cuando el rol no tiene permisos
      return <Navigate to="/403" replace />;
    }
  }

  return <>{children ? children : <Outlet />}</>;
}

export default ProtectedRoute;
