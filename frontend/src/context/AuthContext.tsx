import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, setToken } from '../api/client'

export interface SessionUser {
  user_id: number
  lba_id: number
  org_name: string
  user_name: string
  role: 'admin' | 'to' | 'lba'
  email: string
}

interface AuthState {
  user: SessionUser | null
  ready: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

const USER_KEY = 'lba_user'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const raw = localStorage.getItem(USER_KEY)
    if (raw) {
      try { setUser(JSON.parse(raw)) } catch { /* ignore corrupt value */ }
    }
    setReady(true)
  }, [])

  function persist(token: string, sessionUser: SessionUser) {
    setToken(token)
    localStorage.setItem(USER_KEY, JSON.stringify(sessionUser))
    setUser(sessionUser)
  }

  async function login(email: string, password: string) {
    const data = await api.post<{ token: string; user: SessionUser }>('/auth/login', { email, password })
    persist(data.token, data.user)
  }

  function logout() {
    setToken(null)
    localStorage.removeItem(USER_KEY)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, ready, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
