import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useApiGet } from '../api/useApiGet'
import { api, ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { Alert, Avatar, ButtonIcon, Icon, LotStatusBadge } from '../components/ui'
import { CERTIFICATIONS, formatKg } from '../components/format'

interface Lot {
  id: number
  lot_no: number
  lot_date: string
  receipt_start: number
  receipt_end: number
  total_volume_kg: number
  status: string
  note: string | null
  vehicle_plate: string | null
  driver_name: string | null
  waybill_number: string | null
  bags_declared: number | null
  moisture_pct: number | null
  certification: string | null
}

interface LotRow {
  receipt_number: number
  allocated_volume_kg: number
  num_bags: number | null
  delivered_date: string
  farmer_code: string
  full_name: string
  community: string | null
}

interface LotDetailResponse {
  lot: Lot
  rows: LotRow[]
  reviewer: string | null
}

const ROLES_CAN_REVIEW_LOT = new Set(['admin', 'lba'])

export default function LotResult() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const { data, error, reload } = useApiGet<LotDetailResponse>(id ? `/lots/${id}` : null, [id])
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const [msg, setMsg] = useState('')
  const [certification, setCertification] = useState('')

  async function review(action: 'accept' | 'reject') {
    if (action === 'accept' && !certification) {
      setActionError('Choose which certification this lot is being sold under (or "None / not applicable") before accepting.')
      return
    }
    setBusy(true)
    setActionError('')
    try {
      await api.post(`/lots/${id}/${action}`, action === 'accept' ? { certification: certification === 'none' ? null : certification } : undefined)
      setMsg(action === 'accept' ? 'Lot accepted' : 'Lot rejected')
      reload()
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  async function exportSlip() {
    setBusy(true)
    try {
      const resp = await api.get<{ download_url: string }>(`/lots/${id}/export`)
      window.open(resp.download_url, '_blank')
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not generate the export.')
    } finally {
      setBusy(false)
    }
  }

  async function generateReceipts() {
    setBusy(true)
    setActionError('')
    try {
      const resp = await api.post<{ download_url: string }>(`/lots/${id}/receipts`)
      window.open(resp.download_url, '_blank')
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not generate receipts.')
    } finally {
      setBusy(false)
    }
  }

  if (error && !data) return <Alert message={error} kind="error" />
  if (!data) return <p className="text-muted">Loading…</p>

  const { lot, rows, reviewer } = data
  const canReview = user ? ROLES_CAN_REVIEW_LOT.has(user.role) : false
  const hasSlipDetails = lot.vehicle_plate || lot.driver_name || lot.waybill_number || lot.bags_declared || lot.moisture_pct || lot.certification

  return (
    <>
      <header className="page-header">
        <div>
          <div className="page-header__eyebrow">{lot.lot_date}</div>
          <h1 className="page-header__title">Lot #{lot.lot_no}</h1>
          {lot.note && <p className="page-header__desc">{lot.note}</p>}
        </div>
        <div className="page-header__actions">
          <LotStatusBadge status={lot.status} />
          <a className="btn btn--secondary" href="/lots/new"><Icon name="plus" />Record another</a>
          {lot.status === 'accepted' && canReview && (
            <button className="btn btn--secondary" type="button" disabled={busy} onClick={generateReceipts}>
              <ButtonIcon name="file-sheet" busy={busy} />Generate receipts
            </button>
          )}
          <button className="btn btn--accent" type="button" disabled={busy} onClick={exportSlip}><ButtonIcon name="download" busy={busy} />Export delivery slip</button>
        </div>
      </header>

      {msg && <Alert message={msg} kind="success" />}
      {actionError && <Alert message={actionError} kind="error" />}

      {lot.status === 'pending' && (
        canReview ? (
          <div className="card" style={{ marginBottom: 'var(--space-5)', border: '1px solid var(--color-border)' }}>
            <div className="card__body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
              <div>
                <strong>This lot is pending review.</strong>{' '}
                <span className="text-muted">Its volume doesn't count against any farmer's quota — or as delivered — until it's accepted.</span>
              </div>
              <div className="cluster" style={{ alignItems: 'center' }}>
                <div className="field" style={{ marginBottom: 0, minWidth: 220 }}>
                  <label className="label" htmlFor="certification" style={{ fontSize: 'var(--text-xs)' }}>Selling to (certification) <span style={{ color: 'var(--color-danger, #c0392b)' }}>*</span></label>
                  <select className="select" id="certification" value={certification} required
                          onChange={(e) => { setCertification(e.target.value); setActionError('') }}>
                    <option value="" disabled>Choose a certification…</option>
                    {Object.entries(CERTIFICATIONS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    <option value="none">None / not applicable</option>
                  </select>
                </div>
                <button className="btn btn--secondary" type="button" disabled={busy}
                        onClick={() => { if (confirm('Reject this lot?')) review('reject') }}>
                  <ButtonIcon name="x" busy={busy} />Reject
                </button>
                <button className="btn btn--primary" type="button" disabled={busy || !certification} onClick={() => review('accept')}>
                  <ButtonIcon name="check" busy={busy} />Accept lot
                </button>
              </div>
            </div>
          </div>
        ) : (
          <Alert kind="warning" message="This lot is pending review. An Admin or LBA user needs to accept or reject it before it counts against farmer quota." />
        )
      )}
      {lot.status === 'rejected' && (
        <Alert kind="error" message={`This lot was rejected${reviewer ? ` by ${reviewer}` : ''} and never counted against farmer quota.`} />
      )}
      {lot.status === 'accepted' && (
        <Alert kind="success" message={
          `Accepted${reviewer ? ` by ${reviewer}` : ''} — counted against farmer quota and premium.`
          + (lot.certification ? ` Selling to ${CERTIFICATIONS[lot.certification] || lot.certification}.` : '')
        } />
      )}

      <div className="summary">
        <div className="summary__item"><div className="summary__label">Lot date</div><div className="summary__value">{lot.lot_date}</div></div>
        <div className="summary__item"><div className="summary__label">Receipts</div><div className="summary__value mono">{lot.receipt_start}&ndash;{lot.receipt_end}</div></div>
        <div className="summary__item"><div className="summary__label">Farmers</div><div className="summary__value">{rows.length}</div></div>
        <div className="summary__item"><div className="summary__label">Total volume</div><div className="summary__value">{formatKg(lot.total_volume_kg, 2)} kg</div></div>
      </div>

      {hasSlipDetails && (
        <div className="summary" style={{ marginTop: 'var(--space-3)' }}>
          {lot.vehicle_plate && <div className="summary__item"><div className="summary__label">Vehicle plate</div><div className="summary__value">{lot.vehicle_plate}</div></div>}
          {lot.driver_name && <div className="summary__item"><div className="summary__label">Escort / driver</div><div className="summary__value">{lot.driver_name}</div></div>}
          {lot.waybill_number && <div className="summary__item"><div className="summary__label">Waybill no.</div><div className="summary__value mono">{lot.waybill_number}</div></div>}
          {!!lot.bags_declared && <div className="summary__item"><div className="summary__label">Bags (calculated)</div><div className="summary__value">{lot.bags_declared}</div></div>}
          {!!lot.moisture_pct && <div className="summary__item"><div className="summary__label">Moisture / humidity</div><div className="summary__value">{lot.moisture_pct}%</div></div>}
          {lot.certification && <div className="summary__item"><div className="summary__label">Certification</div><div className="summary__value">{CERTIFICATIONS[lot.certification] || lot.certification}</div></div>}
        </div>
      )}

      <div className="card">
        <div className="card__header"><div className="card__title"><Icon name="file-sheet" />Farmer list</div></div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Receipt no.</th><th>Farmer</th><th className="hide-sm">Community</th><th className="hide-sm">Date delivered</th><th className="is-num hide-sm">Bags</th><th className="is-num">Volume (kg)</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.receipt_number}>
                  <td><span className="code-tag">{r.receipt_number}</span></td>
                  <td>
                    <a className="cell-person" href={`/farmers/${r.farmer_code}`} style={{ textDecoration: 'none' }}>
                      <Avatar fullName={r.full_name} />
                      <span><span className="cell-primary">{r.full_name}</span><span className="cell-secondary mono">{r.farmer_code}</span></span>
                    </a>
                  </td>
                  <td className="hide-sm">{r.community || '—'}</td>
                  <td className="hide-sm">{r.delivered_date}</td>
                  <td className="is-num hide-sm">{r.num_bags ?? '—'}</td>
                  <td className="is-num">{formatKg(r.allocated_volume_kg, 2)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={4}>Total</td>
                <td className="is-num hide-sm">{rows.reduce((s, r) => s + (r.num_bags || 0), 0) || '—'}</td>
                <td className="is-num">{formatKg(lot.total_volume_kg, 2)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <div className="action-bar">
        <span className="action-bar__text"><strong>{rows.length} farmers</strong> &middot; {formatKg(lot.total_volume_kg, 2)} kg &middot; <LotStatusBadge status={lot.status} /></span>
        <div className="cluster">
          <a className="btn btn--secondary" href="/lots/new">Record another</a>
          <button className="btn btn--accent" type="button" disabled={busy} onClick={exportSlip}><ButtonIcon name="download" busy={busy} />Export .xlsx</button>
        </div>
      </div>
    </>
  )
}
