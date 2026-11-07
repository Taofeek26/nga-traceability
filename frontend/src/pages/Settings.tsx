import { useState, type FormEvent } from 'react'
import { useApiGet } from '../api/useApiGet'
import { api, ApiError } from '../api/client'
import { Alert, ButtonIcon, PageHeader } from '../components/ui'

interface SettingsResponse {
  premium_rate_per_kg: string
  allocation_mode: 'full' | 'spread'
}

export default function Settings() {
  const { data, error: loadError } = useApiGet<SettingsResponse>('/settings')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setMsg('')
    setError('')
    setBusy(true)
    const form = new FormData(e.currentTarget)
    try {
      await api.put('/settings', {
        premium_rate_per_kg: Number(form.get('premium_rate_per_kg')),
        allocation_mode: form.get('allocation_mode'),
      })
      setMsg('Saved')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  if (loadError) return <Alert message={loadError} kind="error" />
  if (!data) return <p className="text-muted">Loading…</p>

  return (
    <>
      <PageHeader title="Settings" desc="Configuration for this LBA account." eyebrow="Administration" />
      {msg && <Alert message={msg} kind="success" />}
      {error && <Alert message={error} kind="error" />}

      <form className="card" onSubmit={onSubmit}>
        <div className="card__body">
          <div className="form-section">
            <div>
              <div className="form-section__title">Premium rate</div>
              <p className="form-section__desc">Used to calculate each farmer's accrued premium (delivered kg &times; rate). Set to 0 if you track premium entirely through manual incentive entries.</p>
            </div>
            <div className="field" style={{ maxWidth: 260 }}>
              <label className="label" htmlFor="premium-rate">Premium per kg</label>
              <div className="input-group">
                <span className="input-group__addon">&#8358;</span>
                <input className="input" id="premium-rate" type="number" step="0.01" name="premium_rate_per_kg" defaultValue={data.premium_rate_per_kg} />
                <span className="input-group__addon">/ kg</span>
              </div>
            </div>
          </div>

          <div className="form-section">
            <div>
              <div className="form-section__title">Lot allocation style</div>
              <p className="form-section__desc">How much of a farmer's remaining potential volume a single lot is allowed to use.</p>
            </div>
            <div className="stack-sm">
              <label className="card" style={{ display: 'flex', gap: 'var(--space-3)', padding: 'var(--space-3) var(--space-4)', cursor: 'pointer' }}>
                <input type="radio" name="allocation_mode" value="full" defaultChecked={data.allocation_mode === 'full'} style={{ marginTop: 4 }} />
                <span>
                  <strong>Use full remaining potential at once</strong>
                  <br /><span className="text-muted" style={{ fontSize: 'var(--text-sm)' }}>A farmer's whole remaining quota can be used in a single lot if needed. Fewer, larger deliveries per farmer.</span>
                </span>
              </label>
              <label className="card" style={{ display: 'flex', gap: 'var(--space-3)', padding: 'var(--space-3) var(--space-4)', cursor: 'pointer' }}>
                <input type="radio" name="allocation_mode" value="spread" defaultChecked={data.allocation_mode === 'spread'} style={{ marginTop: 4 }} />
                <span>
                  <strong>Spread across deliveries (more realistic)</strong>
                  <br /><span className="text-muted" style={{ fontSize: 'var(--text-sm)' }}>Each lot uses a randomized portion (roughly 45&ndash;90%) of a farmer's remaining quota instead of the full amount, so it takes multiple deliveries to use up their potential — closer to how farmers actually deliver over a season. Falls back to full use automatically when a lot genuinely needs it.</span>
                </span>
              </label>
            </div>
          </div>
        </div>
        <div className="card__footer">
          <button className="btn btn--primary" type="submit" disabled={busy}><ButtonIcon name="check" busy={busy} />Save changes</button>
        </div>
      </form>
    </>
  )
}
