import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthShell from '../components/AuthShell'
import { Alert, Spinner } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../api/client'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      heading="Welcome back"
      desc="Log in to your LBA's account."
      switchLink="No account yet? Contact your company admin."
    >
      {error && <Alert message={error} kind="error" />}
      <form onSubmit={onSubmit}>
        <div className="field">
          <label className="label" htmlFor="email">Email</label>
          <input className="input" id="email" type="email" required autoFocus autoComplete="email"
                 placeholder="you@lba.ng" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field">
          <label className="label" htmlFor="password">Password</label>
          <input className="input" id="password" type="password" required autoComplete="current-password"
                 value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <div className="form-actions">
          <button className="btn btn--primary btn--lg btn--block" type="submit" disabled={busy}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 'var(--space-2)' }}>
            {busy && <Spinner />}{busy ? 'Logging in…' : 'Log in'}
          </button>
        </div>
      </form>
    </AuthShell>
  )
}
