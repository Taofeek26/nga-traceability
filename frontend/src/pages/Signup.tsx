import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthShell from '../components/AuthShell'
import { Alert } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../api/client'

export default function Signup() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await signup(name, email, password, confirmPassword)
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      heading="Register your LBA"
      desc="Your farmer data stays private to this account — no other LBA can see it."
      switchLink={<>Already registered? <a href="/login">Log in</a></>}
    >
      {error && <Alert message={error} kind="error" />}
      <form onSubmit={onSubmit}>
        <div className="field">
          <label className="label" htmlFor="name">LBA / organisation name</label>
          <input className="input" id="name" type="text" required autoFocus placeholder="e.g. Agbor Buying Station"
                 autoComplete="organization" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="field">
          <label className="label" htmlFor="email">Email</label>
          <input className="input" id="email" type="email" required autoComplete="email"
                 value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="form-grid" style={{ marginTop: 'var(--space-5)' }}>
          <div className="field">
            <label className="label" htmlFor="password">Password</label>
            <input className="input" id="password" type="password" required minLength={8} autoComplete="new-password"
                   value={password} onChange={(e) => setPassword(e.target.value)} />
            <span className="hint">At least 8 characters.</span>
          </div>
          <div className="field">
            <label className="label" htmlFor="confirm_password">Confirm password</label>
            <input className="input" id="confirm_password" type="password" required minLength={8} autoComplete="new-password"
                   value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
          </div>
        </div>
        <div className="form-actions">
          <button className="btn btn--primary btn--lg btn--block" type="submit" disabled={busy}>
            {busy ? 'Creating account…' : 'Create account'}
          </button>
        </div>
      </form>
    </AuthShell>
  )
}
