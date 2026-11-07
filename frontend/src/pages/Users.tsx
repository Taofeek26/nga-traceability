import { useState, type FormEvent } from 'react'
import { useApiGet } from '../api/useApiGet'
import { api, ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Alert, Avatar, Icon, PageHeader } from '../components/ui'

interface TeamMember {
  id: number
  name: string
  email: string
  role: 'admin' | 'to' | 'lba'
  active: boolean
}

interface UsersResponse {
  team: TeamMember[]
  roles: string[]
  role_labels: Record<string, string>
}

export default function Users() {
  const { user } = useAuth()
  const { data, error: loadError, reload } = useApiGet<UsersResponse>('/users')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function toggleActive(id: number) {
    setBusy(true)
    setError('')
    try {
      await api.post(`/users/${id}/toggle-active`)
      reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "You can't deactivate your own account.")
    } finally {
      setBusy(false)
    }
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setMsg('')
    setError('')
    setBusy(true)
    const form = new FormData(e.currentTarget)
    const name = form.get('name')
    try {
      const resp = await api.post<{ name: string; role_label: string }>('/users', {
        name,
        email: form.get('email'),
        password: form.get('password'),
        role: form.get('role'),
      })
      setMsg(`${resp.name} added as ${resp.role_label}`)
      e.currentTarget.reset()
      reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  if (loadError && !data) return <Alert message={loadError} kind="error" />
  if (!data) return <p className="text-muted">Loading…</p>

  return (
    <>
      <PageHeader title="Team" desc="Who can access this LBA's account, and what they can do." eyebrow="Administration" />
      {msg && <Alert message={msg} kind="success" />}
      {error && <Alert message={error} kind="error" />}

      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card__header"><div className="card__title"><Icon name="users" />Team members</div></div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Name</th><th className="hide-sm">Email</th><th>Role</th><th>Status</th><th className="is-action" /></tr></thead>
            <tbody>
              {data.team.map((u) => (
                <tr key={u.id}>
                  <td><span className="cell-person"><Avatar fullName={u.name} /><span className="cell-primary">{u.name}</span></span></td>
                  <td className="hide-sm is-muted">{u.email}</td>
                  <td><span className="badge badge--gold badge--plain">{data.role_labels[u.role]}</span></td>
                  <td>{u.active ? <span className="badge badge--ok">Active</span> : <span className="badge badge--inactive">Inactive</span>}</td>
                  <td className="is-action">
                    {u.id !== user?.user_id ? (
                      <button className="btn btn--ghost btn--sm" type="button" disabled={busy} onClick={() => toggleActive(u.id)}>
                        {u.active ? 'Deactivate' : 'Reactivate'}
                      </button>
                    ) : (
                      <span className="text-muted" style={{ fontSize: 'var(--text-xs)' }}>You</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card__header">
          <div>
            <div className="card__title"><Icon name="plus" />Add a team member</div>
            <div className="card__subtitle">They'll log in with this email and password directly — there's no invite email to send.</div>
          </div>
        </div>
        <form onSubmit={onSubmit}>
          <div className="card__body">
            <div className="form-grid">
              <div className="field">
                <label className="label" htmlFor="user-name">Name</label>
                <input className="input" id="user-name" type="text" name="name" required />
              </div>
              <div className="field">
                <label className="label" htmlFor="user-email">Email</label>
                <input className="input" id="user-email" type="email" name="email" required />
              </div>
              <div className="field">
                <label className="label" htmlFor="user-password">Password</label>
                <input className="input" id="user-password" type="password" name="password" minLength={8} required />
                <span className="hint">At least 8 characters.</span>
              </div>
              <div className="field">
                <label className="label" htmlFor="user-role">Role</label>
                <select className="select" id="user-role" name="role" required defaultValue="to">
                  <option value="to">Traceability Officer — can create lots, can't touch Master Data/Settings</option>
                  <option value="lba">Sourcing Manager — can accept/reject lots, can't create them</option>
                  <option value="admin">Admin — full access, only role that can upload Master Data</option>
                </select>
              </div>
            </div>
          </div>
          <div className="card__footer">
            <button className="btn btn--primary" type="submit" disabled={busy}><Icon name="plus" />Add team member</button>
          </div>
        </form>
      </div>
    </>
  )
}
