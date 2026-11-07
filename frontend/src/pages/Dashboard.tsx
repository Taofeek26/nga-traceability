import { useEffect, useState } from 'react'
import { api, ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Alert, EmptyState, Icon, LotStatusBadge, PageHeader, ProgressBar, StatTile, Avatar } from '../components/ui'
import { formatKg } from '../components/format'

interface Lot {
  id: number
  lot_no: number
  lot_date: string
  receipt_start: number
  receipt_end: number
  total_volume_kg: number
  status: string
}

interface NearLimitFarmer {
  farmer_code: string
  full_name: string
  potential_volume_kg: number
  delivered: number
}

interface DashboardData {
  n_farmers: number
  n_active: number
  potential: number
  delivered: number
  pending: number
  n_lots: number
  n_pending_lots: number
  recent_lots: Lot[]
  near_limit: NearLimitFarmer[]
}

export default function Dashboard() {
  const { user } = useAuth()
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<DashboardData>('/dashboard')
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Could not load the dashboard.'))
  }, [])

  if (error) return <Alert message={error} kind="error" />
  if (!data) return <p className="text-muted">Loading…</p>

  const usedPct = data.potential > 0 ? (data.delivered / data.potential) * 100 : 0
  const role = user?.role

  return (
    <>
      <PageHeader title="Dashboard" desc="Current state of your farmer register and deliveries." eyebrow={user?.org_name || 'Overview'}>
        {role === 'admin' && <a className="btn btn--secondary" href="/upload"><Icon name="upload" />Update master data</a>}
        {(role === 'admin' || role === 'to') && <a className="btn btn--accent" href="/lots/new"><Icon name="plus" />New lot</a>}
      </PageHeader>

      <section className="stats">
        <StatTile label="Farmers on file" value={data.n_farmers} iconName="users" tone="brown" meta={`${data.n_active} active`} />
        <StatTile label="Potential volume" value={formatKg(data.potential)} unit="kg" iconName="leaf" tone="green" meta="Season capacity of the register" />
        <StatTile label="Delivered (accepted)" value={formatKg(data.delivered)} unit="kg" iconName="scale" meta={`${Math.round(usedPct)}% of potential used`} />
        <StatTile label="Pending review" value={formatKg(data.pending)} unit="kg" iconName="receipt" meta={`${data.n_pending_lots} lot(s) awaiting accept/reject`} />
        <StatTile label="Lots recorded" value={data.n_lots} iconName="package" highlight meta="All time" />
      </section>

      {data.n_lots === 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div className="card__header">
            <div>
              <div className="card__title"><Icon name="sparkles" />Get started</div>
              <div className="card__subtitle">Three steps from master list to export-ready farmer list.</div>
            </div>
          </div>
          <div className="card__body">
            <ol className="steps">
              <li className={'step' + (data.n_farmers > 0 ? ' is-done' : '')}>
                <span className="step__num" />
                <span className="step__title">Upload your master list</span>
                <span className="step__text">Add or refresh the farmer register from Excel.</span>
                <a className="link-arrow" href="/upload">Master Data <Icon name="arrow-right" /></a>
              </li>
              <li className="step">
                <span className="step__num" />
                <span className="step__title">Record a lot</span>
                <span className="step__text">Enter the total volume and receipt range used.</span>
                <a className="link-arrow" href="/lots/new">New Lot <Icon name="arrow-right" /></a>
              </li>
              <li className="step">
                <span className="step__num" />
                <span className="step__title">Export the farmer list</span>
                <span className="step__text">The list is generated automatically and exports to .xlsx.</span>
              </li>
            </ol>
          </div>
        </div>
      )}

      <div className="grid grid--main-aside">
        <div className="card">
          <div className="card__header">
            <div className="card__title">Recent lots</div>
            <a className="link-arrow" href="/lots">View all <Icon name="arrow-right" /></a>
          </div>
          <div className="card__body card__body--flush">
            {data.recent_lots.length > 0 ? (
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>Date</th><th>Receipts</th><th className="is-num">Volume (kg)</th><th>Status</th><th className="is-action"><span className="sr-only">Open</span></th></tr></thead>
                  <tbody>
                    {data.recent_lots.map((l) => (
                      <tr key={l.id}>
                        <td><span className="cell-primary">{l.lot_date}</span><span className="cell-secondary">Lot #{l.lot_no}</span></td>
                        <td><span className="mono">{l.receipt_start}&ndash;{l.receipt_end}</span></td>
                        <td className="is-num">{formatKg(l.total_volume_kg, 1)}</td>
                        <td><LotStatusBadge status={l.status} /></td>
                        <td className="is-action"><a className="link-arrow" href={`/lots/${l.id}`}>Farmer list <Icon name="chevron-right" /></a></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState title="No lots recorded yet" text="When a lot arrives, enter its volume and receipt range to generate the farmer list." iconName="package" actionHref="/lots/new" actionLabel="Record first lot" />
            )}
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <div>
              <div className="card__title">Near their limit</div>
              <div className="card__subtitle">Active farmers at 90%+ of potential</div>
            </div>
            {data.near_limit.length > 0 && <span className="badge badge--warn">{data.near_limit.length}</span>}
          </div>
          <div className="card__body">
            {data.near_limit.length > 0 ? (
              <div className="stack-sm">
                {data.near_limit.map((f) => {
                  const pct = (f.delivered / f.potential_volume_kg) * 100
                  return (
                    <a key={f.farmer_code} className="cell-person" href={`/farmers/${f.farmer_code}`} style={{ textDecoration: 'none' }}>
                      <Avatar fullName={f.full_name} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="meter__head" style={{ marginBottom: 6 }}>
                          <span className="cell-primary">{f.full_name}</span>
                          <span className="text-muted num" style={{ fontSize: 'var(--text-xs)' }}>{formatKg(f.potential_volume_kg - f.delivered)} kg left</span>
                        </div>
                        <ProgressBar pct={pct} size="sm" />
                      </div>
                    </a>
                  )
                })}
              </div>
            ) : (
              <div className="empty-state" style={{ padding: 'var(--space-6) 0' }}>
                <div className="empty-state__icon"><Icon name="check" /></div>
                <p className="empty-state__text">No farmers are close to their quota.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
