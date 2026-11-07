import type { ReactNode } from 'react'
import { useAuth, type SessionUser } from '../context/AuthContext'
import { Alert } from './ui'

export default function RequireRole({ roles, children }: { roles: SessionUser['role'][]; children: ReactNode }) {
  const { user } = useAuth()
  if (!user || !roles.includes(user.role)) {
    return <Alert kind="error" message="You don't have permission to do that." />
  }
  return <>{children}</>
}
