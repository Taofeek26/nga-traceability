import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Avatar, Icon } from './ui'

const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  to: 'Traceability Officer',
  lba: 'Sourcing Manager',
}

export default function AccountMenu() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  if (!user) return null

  return (
    <div className="account-menu" ref={ref} style={{ position: 'relative' }}>
      <button
        type="button"
        className="btn btn--ghost btn--sm"
        onClick={() => setOpen((o) => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <Avatar fullName={user.user_name} tone="gold" />
        <span>{user.user_name}</span>
      </button>

      {open && (
        <div
          role="menu"
          className="card"
          style={{
            position: 'absolute', right: 0, top: 'calc(100% + 8px)', width: 280, zIndex: 50,
            boxShadow: 'var(--shadow-lg, 0 8px 24px rgba(0,0,0,.14))',
          }}
        >
          <div className="card__body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <strong>{user.user_name}</strong>
            <span className="text-muted" style={{ fontSize: 'var(--text-sm)' }}>{user.email}</span>
            <span className="badge badge--ok" style={{ alignSelf: 'flex-start' }}>{ROLE_LABELS[user.role] || user.role}</span>
          </div>
          <div style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
            <button
              type="button"
              role="menuitem"
              className="btn btn--ghost"
              style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 0 }}
              onClick={() => { setOpen(false); navigate('/profile') }}
            >
              <Icon name="user" size="sm" />Profile
            </button>
          </div>
          <div style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
            <button
              type="button"
              role="menuitem"
              className="btn btn--ghost"
              style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 0, color: 'var(--color-danger, #c0392b)' }}
              onClick={logout}
            >
              <Icon name="logout" size="sm" />Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
