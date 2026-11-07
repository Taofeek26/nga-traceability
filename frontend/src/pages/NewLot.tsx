import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApiGet } from '../api/useApiGet'
import { api, ApiError } from '../api/client'
import { Alert, Avatar, Icon, PageHeader } from '../components/ui'

interface EligibilityResponse {
  n_eligible: number
  standard_bag_kg: number
}

interface FarmerOption {
  farmer_code: string
  full_name: string
}

function randomSuggestedDate(): string {
  const d = new Date()
  d.setDate(d.getDate() - Math.floor(Math.random() * 15)) // 0-14 days back, same window as the original app
  return d.toISOString().slice(0, 10)
}

export default function NewLot() {
  const navigate = useNavigate()
  const { data, error: loadError } = useApiGet<EligibilityResponse>('/lots/eligibility')
  const [lotDate] = useState(randomSuggestedDate)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const today = new Date().toISOString().slice(0, 10)

  const nEligible = data?.n_eligible ?? 0
  const standardBagKg = data?.standard_bag_kg ?? 62.5

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<FarmerOption[]>([])
  const [selected, setSelected] = useState<FarmerOption[]>([])

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      return
    }
    const timer = setTimeout(() => {
      api.get<{ farmers: FarmerOption[] }>(`/farmers?q=${encodeURIComponent(query)}`)
        .then((resp) => setResults(resp.farmers))
        .catch(() => setResults([]))
    }, 250)
    return () => clearTimeout(timer)
  }, [query])

  function addPreferred(f: FarmerOption) {
    if (selected.some((s) => s.farmer_code === f.farmer_code)) return
    setSelected((s) => [...s, f])
    setQuery('')
    setResults([])
  }

  function removePreferred(code: string) {
    setSelected((s) => s.filter((f) => f.farmer_code !== code))
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError('')
    setBusy(true)
    const form = new FormData(e.currentTarget)
    try {
      const resp = await api.post<{ lot_id: number }>('/lots', {
        lot_date: form.get('lot_date'),
        total_volume_kg: Number(form.get('total_volume_kg')),
        receipt_start: Number(form.get('receipt_start')),
        receipt_end: Number(form.get('receipt_end')),
        note: form.get('note') || '',
        vehicle_plate: form.get('vehicle_plate') || '',
        driver_name: form.get('driver_name') || '',
        waybill_number: form.get('waybill_number') || '',
        moisture_pct: form.get('moisture_pct') || '',
        preferred_farmer_codes: selected.map((f) => f.farmer_code),
      })
      navigate(`/lots/${resp.lot_id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader title="Record a new lot" desc="Enter what you actually know about the delivery — the total volume and the receipt range used. The farmer list is generated automatically from the active register." eyebrow="Traceability" />

      {(error || loadError) && <Alert message={error || loadError} kind="error" />}
      {nEligible === 0 ? (
        <Alert kind="warning" message="Upload a master list first, or check that farmers aren't all at their limit." title="No active farmers have remaining quota" />
      ) : (
        <Alert kind="info" message={`${nEligible} farmer(s) currently eligible (active, with remaining quota). The number of receipts (end − start + 1) cannot exceed this.`} />
      )}

      <form className="card" onSubmit={onSubmit}>
        <div className="card__body">
          <div className="form-section">
            <div>
              <div className="form-section__title">Delivery</div>
              <p className="form-section__desc">When the lot arrived and its total weighed volume.</p>
            </div>
            <div className="form-grid">
              <div className="field">
                <label className="label" htmlFor="lot-date">Lot date</label>
                <input className="input" id="lot-date" type="date" name="lot_date" defaultValue={lotDate} max={today} required />
              </div>
              <div className="field">
                <label className="label" htmlFor="lot-volume">Total lot volume</label>
                <div className="input-group">
                  <input className="input" id="lot-volume" type="number" step="0.01" min="0.01" name="total_volume_kg" required placeholder="0.00" />
                  <span className="input-group__addon">kg</span>
                </div>
              </div>
            </div>
          </div>

          <div className="form-section">
            <div>
              <div className="form-section__title">Receipt booklet</div>
              <p className="form-section__desc">The first and last receipt numbers used for this lot. One receipt = one farmer.</p>
            </div>
            <div className="field">
              <span className="label" id="receipt-label">Receipt range</span>
              <div className="range-pair" role="group" aria-labelledby="receipt-label">
                <input className="input" type="number" min="1" name="receipt_start" required placeholder="Start, e.g. 1001" aria-label="Start number" />
                <span className="range-pair__sep">&ndash;</span>
                <input className="input" type="number" min="1" name="receipt_end" required placeholder="End, e.g. 1030" aria-label="End number" />
              </div>
              <span className="hint">Up to {nEligible} receipts allowed.</span>
            </div>
          </div>

          <div className="form-section">
            <div>
              <div className="form-section__title">Preferred farmers <span className="label__optional">(optional)</span></div>
              <p className="form-section__desc">Search by name or code to make sure specific farmers are included in this lot's allocation. The rest of the receipts are still filled randomly from the eligible register.</p>
            </div>
            <div>
              <div className="field" style={{ position: 'relative' }}>
                <input
                  className="input"
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search farmer name or code…"
                  aria-label="Search farmers to prefer"
                />
                {results.length > 0 && (
                  <div className="card" style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 20, maxHeight: 240, overflowY: 'auto' }}>
                    {results.map((f) => (
                      <button
                        key={f.farmer_code}
                        type="button"
                        className="btn btn--ghost"
                        style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 0 }}
                        onClick={() => addPreferred(f)}
                      >
                        <Avatar fullName={f.full_name} size="sm" />
                        <span className="cell-primary">{f.full_name}</span>
                        <span className="cell-secondary mono">{f.farmer_code}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {selected.length > 0 && (
                <div className="chips" style={{ marginTop: 'var(--space-2)' }}>
                  {selected.map((f) => (
                    <span key={f.farmer_code} className="code-tag" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      {f.full_name} ({f.farmer_code})
                      <button type="button" onClick={() => removePreferred(f.farmer_code)} aria-label={`Remove ${f.full_name}`}
                              style={{ background: 'none', border: 0, cursor: 'pointer', padding: 0, display: 'inline-flex' }}>
                        <Icon name="x" size="sm" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
              {selected.length > nEligible && (
                <p className="hint" style={{ color: 'var(--color-danger, #c0392b)' }}>More preferred farmers selected than receipts available.</p>
              )}
            </div>
          </div>

          <div className="form-section">
            <div>
              <div className="form-section__title">Delivery slip details <span className="label__optional">(optional)</span></div>
              <p className="form-section__desc">From the vehicle's paperwork, if available — appears on the exported delivery slip.</p>
            </div>
            <div className="form-grid">
              <div className="field">
                <label className="label" htmlFor="vehicle-plate">Vehicle plate number</label>
                <input className="input" id="vehicle-plate" type="text" name="vehicle_plate" placeholder="e.g. NNR 655 XA" />
              </div>
              <div className="field">
                <label className="label" htmlFor="driver-name">Escort / driver's name</label>
                <input className="input" id="driver-name" type="text" name="driver_name" placeholder="e.g. Muhammed" />
              </div>
              <div className="field">
                <label className="label" htmlFor="waybill">Waybill number</label>
                <input className="input" id="waybill" type="text" name="waybill_number" placeholder="e.g. 0024" />
              </div>
              <div className="field">
                <label className="label" htmlFor="moisture">Moisture / humidity (%)</label>
                <input className="input" id="moisture" type="number" step="0.1" min="0" max="100" name="moisture_pct" placeholder="e.g. 7.5" />
              </div>
            </div>
            <p className="hint" style={{ marginTop: 'var(--space-2)' }}>
              Number of bags isn't entered — it's calculated from the weighed volume at the standard {standardBagKg}kg per bag, then split across farmers in proportion to their volume share.
            </p>
          </div>

          <div className="form-section">
            <div>
              <div className="form-section__title">Reference</div>
              <p className="form-section__desc">Anything else that helps identify this lot later.</p>
            </div>
            <div className="field">
              <label className="label" htmlFor="lot-note">Note <span className="label__optional">(optional)</span></label>
              <input className="input" id="lot-note" type="text" name="note" placeholder="e.g. broker name…" />
            </div>
          </div>
        </div>
        <div className="card__footer">
          <a className="btn btn--ghost" href="/lots">Cancel</a>
          <button className="btn btn--primary" type="submit" disabled={busy || nEligible === 0}>
            <Icon name="sparkles" />Generate farmer list
          </button>
        </div>
      </form>
    </>
  )
}
