import { useApiGet } from '../api/useApiGet'
import { useAuth } from '../context/AuthContext'
import { Alert, EmptyState, Icon, LotStatusBadge, PageHeader } from '../components/ui'
import { certificationLabel, formatKg } from '../components/format'

interface Lot {
  id: number
  lot_no: number
  lot_date: string
  receipt_start: number
  receipt_end: number
  n_farmers: number
  total_volume_kg: number
  status: string
  note: string | null
  certification: string | null
}

export default function Lots() {
  const { user } = useAuth()
  const { data, error } = useApiGet<{ lots: Lot[] }>('/lots')
  const lots = data?.lots ?? []
  const canCreate = user?.role === 'admin' || user?.role === 'to'

  return (
    <>
      <PageHeader title="Lot History" desc={`${lots.length} lot(s) recorded.`}>
        {canCreate && <a className="btn btn--accent" href="/lots/new"><Icon name="plus" />New lot</a>}
      </PageHeader>

      {error && <Alert message={error} kind="error" />}

      <div className="card">
        {lots.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Lot</th><th>Receipts</th><th className="is-num">Farmers</th><th className="is-num">Volume (kg)</th><th>Status</th><th>Certification</th><th className="hide-sm">Note</th><th className="is-action"><span className="sr-only">Open</span></th></tr>
              </thead>
              <tbody>
                {lots.map((l) => (
                  <tr key={l.id}>
                    <td><span className="cell-primary">{l.lot_date}</span><span className="cell-secondary">Lot #{l.lot_no}</span></td>
                    <td><span className="code-tag">{l.receipt_start}&ndash;{l.receipt_end}</span></td>
                    <td className="is-num">{l.n_farmers}</td>
                    <td className="is-num">{formatKg(l.total_volume_kg, 2)}</td>
                    <td><LotStatusBadge status={l.status} /></td>
                    <td>{l.certification ? <span className="badge badge--gold badge--plain">{certificationLabel(l.certification)}</span> : <span className="is-muted">&mdash;</span>}</td>
                    <td className="hide-sm is-muted">{l.note || ''}</td>
                    <td className="is-action"><a className="btn btn--ghost btn--sm" href={`/lots/${l.id}`}>View <Icon name="chevron-right" /></a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No lots recorded yet" text="Record a lot to generate its farmer list automatically." iconName="history" actionHref="/lots/new" actionLabel="Record first lot" />
        )}
      </div>
    </>
  )
}
