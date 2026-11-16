import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import Layout from './components/Layout';
import Vehicles from './pages/owner/Vehicles';
import Reminders from './pages/owner/Reminders';
import Appointment from './pages/owner/Appointment';
import MyAppointments from './pages/owner/MyAppointments';
import Reports from './pages/owner/Reports';
import StationAppointments from './pages/station/StationAppointments';
import StationCheckin from './pages/station/StationCheckin';
import StationReportEntry from './pages/station/StationReportEntry';
import StationManagement from './pages/admin/StationManagement';
import StatisticsDashboard from './pages/admin/StatisticsDashboard';
import DataExport from './pages/admin/DataExport';
import UserManagement from './pages/admin/UserManagement';

export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export function RoleRoute({ children, roles }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

function App() {
  const { user, loading } = useAuth();
  if (loading) return null;

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
        <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<RoleGuardHome />} />
          <Route path="vehicles" element={<RoleRoute roles={['owner']}><Vehicles /></RoleRoute>} />
          <Route path="reminders" element={<RoleRoute roles={['owner']}><Reminders /></RoleRoute>} />
          <Route path="appointment" element={<RoleRoute roles={['owner']}><Appointment /></RoleRoute>} />
          <Route path="my-appointments" element={<RoleRoute roles={['owner']}><MyAppointments /></RoleRoute>} />
          <Route path="reports" element={<RoleRoute roles={['owner']}><Reports /></RoleRoute>} />
          <Route path="station-appointments" element={<RoleRoute roles={['station', 'admin']}><StationAppointments /></RoleRoute>} />
          <Route path="station-checkin" element={<RoleRoute roles={['station', 'admin']}><StationCheckin /></RoleRoute>} />
          <Route path="station-report" element={<RoleRoute roles={['station', 'admin']}><StationReportEntry /></RoleRoute>} />
          <Route path="stations" element={<RoleRoute roles={['admin']}><StationManagement /></RoleRoute>} />
          <Route path="users" element={<RoleRoute roles={['admin']}><UserManagement /></RoleRoute>} />
          <Route path="statistics" element={<RoleRoute roles={['admin']}><StatisticsDashboard /></RoleRoute>} />
          <Route path="export" element={<RoleRoute roles={['admin']}><DataExport /></RoleRoute>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

function RoleGuardHome() {
  const { user } = useAuth();
  if (user?.role === 'owner') return <Reminders />;
  if (user?.role === 'station') return <StationAppointments />;
  if (user?.role === 'admin') return <StatisticsDashboard />;
  return <Navigate to="/login" replace />;
}

export default App;
