import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Layout } from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Requests from './pages/Requests';
import Reports from './pages/Reports';
import Students from './pages/Students';
import Login from './pages/Login';
import Settings from './pages/Settings';
import Forbidden from './pages/Forbidden';
import NotFound from './pages/NotFound';
import { CoderLayout } from './components/coder/CoderLayout';
import CoderHistory from './pages/coder/CoderHistory';
import ExcuseSubmissionForm from './pages/coder/ExcuseSubmissionForm';
import CoderChat from './pages/coder/CoderChat';
import CoderAttendance from './pages/coder/CoderAttendance';
import type { UserRole } from './types';

// Roles administrativos autorizados para el portal HSE
const ADMIN_ROLES: UserRole[] = ['HSE_ANALYST', 'TEAM_LEADER', 'ADMIN'];

// Rol exclusivo de Coder
const CODER_ROLES: UserRole[] = ['CODER'];

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Ruta pública de Login unificado */}
          <Route path="/login" element={<Login />} />

          {/* Ruta de Acceso Denegado 403 */}
          <Route path="/403" element={<Forbidden />} />

          {/* Rutas Administrativas (HSE_ANALYST, TEAM_LEADER, ADMIN) */}
          <Route
            element={
              <ProtectedRoute allowedRoles={ADMIN_ROLES}>
                <Layout />
              </ProtectedRoute>
            }
          >
            {/* Panel Dashboard accesible tanto en raíz / como en /dashboard */}
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/requests" element={<Requests />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/students" element={<Students />} />
            <Route path="/settings" element={<Settings />} />
          </Route>

          {/* Rutas del Portal Coder (Exclusivo para CODER) */}
          <Route
            path="/coder"
            element={
              <ProtectedRoute allowedRoles={CODER_ROLES}>
                <CoderLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="new-excuse" replace />} />
            <Route path="history" element={<CoderHistory />} />
            <Route path="new-excuse" element={<ExcuseSubmissionForm />} />
            <Route path="attendance" element={<CoderAttendance />} />
            <Route path="chat" element={<CoderChat />} />
          </Route>

          {/* Rutas 404 Not Found (explícita y comodín) */}
          <Route path="/404" element={<NotFound />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
