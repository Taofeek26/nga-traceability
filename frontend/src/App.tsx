import { Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './components/AppShell'
import ProtectedRoute from './components/ProtectedRoute'
import RequireRole from './components/RequireRole'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Farmers from './pages/Farmers'
import FarmerDetail from './pages/FarmerDetail'
import Lots from './pages/Lots'
import NewLot from './pages/NewLot'
import LotResult from './pages/LotResult'
import Settings from './pages/Settings'
import Users from './pages/Users'
import Upload from './pages/Upload'
import Documents from './pages/Documents'
import AuditLog from './pages/AuditLog'
import Profile from './pages/Profile'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="farmers" element={<Farmers />} />
        <Route path="farmers/:code" element={<FarmerDetail />} />
        <Route path="lots" element={<Lots />} />
        <Route path="lots/new" element={<RequireRole roles={['admin', 'to']}><NewLot /></RequireRole>} />
        <Route path="lots/:id" element={<LotResult />} />
        <Route path="settings" element={<RequireRole roles={['admin']}><Settings /></RequireRole>} />
        <Route path="users" element={<RequireRole roles={['admin']}><Users /></RequireRole>} />
        <Route path="upload" element={<RequireRole roles={['admin']}><Upload /></RequireRole>} />
        <Route path="documents" element={<Documents />} />
        <Route path="audit-log" element={<RequireRole roles={['admin']}><AuditLog /></RequireRole>} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
