import { useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { useApiGet } from '../api/useApiGet'
import { api, ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Alert, Avatar, ButtonIcon, EmptyState, FarmerStatusBadge, Icon, LotStatusBadge, PageHeader, PageLoader, ProgressBar } from '../components/ui'
import { formatKg, formatNaira } from '../components/format'

interface Farmer {
  farmer_code: string
  full_name: string
  community: string | null
  farmer_uid: string | null
  gender: string | null
  date_of_birth: string | null
  phone_number: string | null
  nin: string | null
  num_plots: number
  farm_size_ha: number
  potential_volume_kg: number
  active: boolean
}

interface Delivery {
  lot_id: number
  lot_date: string
  status: string
  receipt_number: number
  allocated_volume_kg: number
}

interface Incentive {
  id: number
  incentive_date: string
  type: string
  amount: number
  note: string | null
}

interface FarmerDetailResponse {
  farmer: Farmer
  deliveries: Delivery[]
  delivered: number
  pending: number
  remaining: number
  incentives: Incentive[]
  premium_rate: number
  premium_accrued: number
  other_incentives: number
  total_entitlement: number
}

export default function FarmerDetail() {
  const { code } = useParams<{ code: string }>()
  const { user } = useAuth()
  const { data, error, reload } = useApiGet<FarmerDetailResponse>(code ? `/farmers/${code}` : null, [code])
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')

  async function toggleActive() {
    setBusy(true)
    setActionError('')
    try {
      await api.post(`/farmers/${code}/toggle-active`)
      reload()
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  async function addIncentive(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const formEl = e.currentTarget
    const form = new FormData(formEl)
    setBusy(true)
    setActionError('')
    try {
      await api.post(`/farmers/${code}/incentives`, {
        type: form.get('type'),
        amount: Number(form.get('amount')),
        incentive_date: form.get('incentive_date'),
        note: form.get('note') || '',
      })
      formEl.reset()
      reload()
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  if (error && !data) return <Alert message={error} kind="error" />
  if (!data) return <PageLoader />

  const { farmer: f, deliveries, delivered, pending, remaining, incentives, premium_rate, premium_accrued, other_incentives, total_entitlement } = data
  const pct = f.potential_volume_kg > 0 ? (delivered / f.potential_volume_kg) * 100 : 0

  return (
    <>
      <header className="page-header">
        <div className="profile">
          <Avatar fullName={f.full_name} size="xl" tone="gold" />
          <div>
            <h1 className="profile__name">{f.full_name}</h1>
            <div className="page-header__meta">
              <span className="code-tag">{f.farmer_code}</span>
              <span><Icon name="map-pin" size="sm" />{f.community || 'No community on file'}</span>
              <FarmerStatusBadge active={f.active} pct={pct} />
            </div>
          </div>
        </div>
        {user?.role === 'admin' && (
          <div className="page-header__actions">
            <button className={f.active ? 'btn btn--secondary' : 'btn btn--primary'} type="button" disabled={busy} onClick={toggleActive}>
              <ButtonIcon name="power" busy={busy} />{f.active ? 'Mark inactive' : 'Reactivate'}
            </button>
          </div>
        )}
      </header>

      {actionError && <Alert message={actionError} kind="error" />}

      <section className="stats">
        <div className="stat">
          <div className="stat__top"><span className="stat__label">Potential volume</span><span className="stat__icon stat__icon--green"><Icon name="leaf" size="sm" /></span></div>
          <div className="stat__value">{formatKg(f.potential_volume_kg)}<span className="stat__unit">kg</span></div>
        </div>
        <div className="stat">
          <div className="stat__top"><span className="stat__label">Delivered (accepted)</span><span className="stat__icon"><Icon name="scale" size="sm" /></span></div>
          <div className="stat__value">{formatKg(delivered)}<span className="stat__unit">kg</span></div>
          {pending > 0 && <div className="stat__meta">{formatKg(pending)} kg pending review</div>}
        </div>
        <div className="stat">
          <div className="stat__top"><span className="stat__label">Remaining quota</span><span className={'stat__icon' + (remaining <= 0 ? ' stat__icon--red' : ' stat__icon--brown')}><Icon name="package" size="sm" /></span></div>
          <div className="stat__value">{formatKg(remaining)}<span className="stat__unit">kg</span></div>
        </div>
        <div className="stat">
          <div className="stat__top"><span className="stat__label">Plots</span><span className="stat__icon stat__icon--brown"><Icon name="map-pin" size="sm" /></span></div>
          <div className="stat__value">{f.num_plots}</div>
          <div className="stat__meta">{f.farm_size_ha} ha farm size</div>
        </div>
      </section>

      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card__body">
          <div className="meter">
            <div className="meter__head">
              <span className="meter__label">Quota used</span>
              <span className="meter__value">{Math.round(pct)}% &middot; {formatKg(delivered)} / {formatKg(f.potential_volume_kg)} kg</span>
            </div>
            <ProgressBar pct={pct} size="" />
          </div>
        </div>
      </div>

      <div className="grid grid--main-aside">
        <div className="stack">
          <div className="card">
            <div className="card__header">
              <div>
                <div className="card__title"><Icon name="wallet" />Entitlements</div>
                <div className="card__subtitle">Premium at {formatNaira(premium_rate)}/kg plus logged incentives</div>
              </div>
            </div>
            <div className="summary" style={{ margin: 0, border: 0, borderRadius: 0, boxShadow: 'none', borderBottom: '1px solid var(--color-border-subtle)' }}>
              <div className="summary__item"><div className="summary__label">Premium accrued</div><div className="summary__value">{formatNaira(premium_accrued)}</div></div>
              <div className="summary__item"><div className="summary__label">Other incentives</div><div className="summary__value">{formatNaira(other_incentives)}</div></div>
              <div className="summary__item"><div className="summary__label">Total entitlement</div><div className="summary__value" style={{ color: 'var(--gold-hover)' }}>{formatNaira(total_entitlement)}</div></div>
            </div>
            {user?.role === 'admin' && (
              <div className="card__body">
                <form onSubmit={addIncentive}>
                  <div className="form-grid">
                    <div className="field">
                      <label className="label" htmlFor="inc-type">Type</label>
                      <select className="select" id="inc-type" name="type" defaultValue="Bonus">
                        <option>Bonus</option>
                        <option>Training stipend</option>
                        <option>Input support</option>
                        <option>Other</option>
                      </select>
                    </div>
                    <div className="field">
                      <label className="label" htmlFor="inc-amount">Amount</label>
                      <div className="input-group">
                        <span className="input-group__addon">&#8358;</span>
                        <input className="input" id="inc-amount" type="number" step="0.01" name="amount" required />
                      </div>
                    </div>
                    <div className="field">
                      <label className="label" htmlFor="inc-date">Date</label>
                      <input className="input" id="inc-date" type="date" name="incentive_date" required />
                    </div>
                    <div className="field">
                      <label className="label" htmlFor="inc-note">Note <span className="label__optional">(optional)</span></label>
                      <input className="input" id="inc-note" type="text" name="note" />
                    </div>
                  </div>
                  <div className="form-actions">
                    <button className="btn btn--accent" type="submit" disabled={busy}><ButtonIcon name="plus" busy={busy} />Add incentive</button>
                  </div>
                </form>
              </div>
            )}
            {incentives.length > 0 && (
              <div className="table-wrap" style={{ borderTop: '1px solid var(--color-border-subtle)' }}>
                <table className="table table--compact">
                  <thead><tr><th>Date</th><th>Type</th><th className="is-num">Amount</th><th className="hide-sm">Note</th></tr></thead>
                  <tbody>
                    {incentives.map((i) => (
                      <tr key={i.id}>
                        <td>{i.incentive_date}</td>
                        <td><span className="badge badge--gold badge--plain">{i.type}</span></td>
                        <td className="is-num">{formatNaira(i.amount)}</td>
                        <td className="hide-sm is-muted">{i.note || ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card__header">
              <div className="card__title"><Icon name="truck" />Delivery history</div>
              {deliveries.length > 0 && <span className="text-muted" style={{ fontSize: 'var(--text-sm)' }}>{deliveries.length} {deliveries.length === 1 ? 'delivery' : 'deliveries'}</span>}
            </div>
            <div className="card__body card__body--flush">
              {deliveries.length > 0 ? (
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>Lot date</th><th>Receipt no.</th><th className="is-num">Volume (kg)</th><th>Status</th><th className="is-action"><span className="sr-only">Open</span></th></tr></thead>
                    <tbody>
                      {deliveries.map((d, i) => (
                        <tr key={i}>
                          <td>{d.lot_date}</td>
                          <td><span className="mono">{d.receipt_number}</span></td>
                          <td className="is-num">{formatKg(d.allocated_volume_kg, 2)}</td>
                          <td><LotStatusBadge status={d.status} /></td>
                          <td className="is-action"><a className="link-arrow" href={`/lots/${d.lot_id}`}>View lot <Icon name="chevron-right" /></a></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="No deliveries yet" text="This farmer hasn't been allocated to any lot." iconName="truck" />
              )}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__header"><div className="card__title"><Icon name="user" />Farmer details</div></div>
          <div className="card__body" style={{ paddingTop: 'var(--space-2)', paddingBottom: 'var(--space-2)' }}>
            <dl className="dl">
              <dt>Farmer code</dt><dd className="mono">{f.farmer_code}</dd>
              {f.farmer_uid && <><dt>Farmer ID</dt><dd className="mono">{f.farmer_uid}</dd></>}
              <dt>Gender</dt><dd>{f.gender || '—'}</dd>
              <dt>Date of birth</dt><dd>{f.date_of_birth || '—'}</dd>
              <dt>Phone number</dt><dd>{f.phone_number || '—'}</dd>
              <dt>National ID (NIN)</dt><dd className="mono">{f.nin || '—'}</dd>
              <dt>Community</dt><dd>{f.community || '—'}</dd>
              <dt>Plots</dt><dd>{f.num_plots}</dd>
              <dt>Farm size</dt><dd>{f.farm_size_ha} ha</dd>
            </dl>
          </div>
        </div>
      </div>
    </>
  )
}
