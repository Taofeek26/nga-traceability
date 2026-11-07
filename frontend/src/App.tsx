import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './components/AppShell'
import ProtectedRoute from './components/ProtectedRoute'
import RequireRole from './components/RequireRole'
import { PageLoader } from './components/ui'
import Login from './pages/Login'

// Each page is its own chunk, fetched on first visit instead of all being
// in the one bundle the Dashboard has to wait on - the Dashboard route
// stays eager since it's the first thing almost every session loads.
import Dashboard from './pages/Dashboard'
const Farmers = lazy(() => import('./pages/Farmers'))
const FarmerDetail = lazy(() => import('./pages/FarmerDetail'))
const Lots = lazy(() => import('./pages/Lots'))
const NewLot = lazy(() => import('./pages/NewLot'))
const LotResult = lazy(() => import('./pages/LotResult'))
const Settings = lazy(() => import('./pages/Settings'))
const Users = lazy(() => import('./pages/Users'))
const Upload = lazy(() => import('./pages/Upload'))
const Documents = lazy(() => import('./pages/Documents'))
const AuditLog = lazy(() => import('./pages/AuditLog'))
const Profile = lazy(() => import('./pages/Profile'))

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
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
    </Suspense>
  )
}
