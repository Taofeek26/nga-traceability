import { useAuth } from '../context/AuthContext'
import { Avatar, PageHeader } from '../components/ui'

const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  to: 'Traceability Officer',
  lba: 'Sourcing Manager',
}

export default function Profile() {
  const { user } = useAuth()
  if (!user) return null

  return (
    <>
      <PageHeader title="Profile" desc="Your account on this LBA." />
      <div className="card" style={{ maxWidth: 480 }}>
        <div className="card__body" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
          <Avatar fullName={user.user_name} size="xl" tone="gold" />
          <div>
            <div style={{ fontWeight: 600, fontSize: 'var(--text-lg)' }}>{user.user_name}</div>
            <div className="text-muted">{user.org_name}</div>
          </div>
        </div>
        <div className="card__body" style={{ paddingTop: 0 }}>
          <dl className="dl">
            <dt>Email</dt><dd>{user.email}</dd>
            <dt>Role</dt><dd>{ROLE_LABELS[user.role] || user.role}</dd>
          </dl>
        </div>
      </div>
    </>
  )
}
