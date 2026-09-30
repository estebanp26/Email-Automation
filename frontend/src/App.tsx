import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Requests from './pages/Requests';
import Reports from './pages/Reports';
import Students from './pages/Students';
import Login from './pages/Login';
import Settings from './pages/Settings';
import { CoderLayout } from './components/coder/CoderLayout';
import ExcuseSubmissionForm from './pages/coder/ExcuseSubmissionForm';

function ProtectedRoute({ children, role }: { children: React.ReactNode; role?: 'hse' | 'coder' }) {
  const token = localStorage.getItem('hse_token');
  const userRole = localStorage.getItem('hse_role');
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // Si un coder intenta entrar a la vista HSE, lo redirigimos a su portal
  if (role === 'hse' && userRole === 'coder') {
    return <Navigate to="/coder/new-excuse" replace />;
  }

  return <>{children}</>;
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />

        {/* Rutas HSE (Admin / Team Leader) */}
        <Route
          path="/"
          element={
            <ProtectedRoute role="hse">
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="requests" element={<Requests />} />
          <Route path="reports" element={<Reports />} />
          <Route path="students" element={<Students />} />
          <Route path="settings" element={<Settings />} />
        </Route>

        {/* Vista Coder: Formulario de Justificaciones y Excusas */}
        <Route
          path="/coder/new-excuse"
          element={
            <CoderLayout>
              <ExcuseSubmissionForm />
            </CoderLayout>
          }
        />

        {/* Ruta comodín */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
