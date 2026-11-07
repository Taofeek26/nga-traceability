import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApiGet } from '../api/useApiGet'
import { useAuth } from '../context/AuthContext'
import { Alert, Avatar, EmptyState, FarmerStatusBadge, Icon, MiniMeter, PageHeader } from '../components/ui'
import { formatKg } from '../components/format'

interface Farmer {
  farmer_code: string
  full_name: string
  community: string | null
  potential_volume_kg: number
  delivered: number
  active: boolean
}

interface FarmersResponse {
  farmers: Farmer[]
  q: string
}

export default function Farmers() {
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const q = params.get('q') || ''
  const [search, setSearch] = useState(q)

  const { data, error } = useApiGet<FarmersResponse>(`/farmers?q=${encodeURIComponent(q)}`, [q])

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setParams(search ? { q: search } : {})
  }

  const farmers = data?.farmers ?? []

  return (
    <>
      <PageHeader
        title="Farmers"
        desc={`${farmers.length} farmer(s) ${q ? `matching "${q}"` : 'in your register'}.`}
      >
        <a className="btn btn--soft" href="/farmers/export"><Icon name="download" />Export</a>
        {user?.role === 'admin' && <a className="btn btn--secondary" href="/upload"><Icon name="upload" />Import from Excel</a>}
      </PageHeader>

      {error && <Alert message={error} kind="error" />}

      <div className="card">
        <form className="toolbar" onSubmit={onSubmit} role="search">
          <div className="input-group input-group--icon toolbar__search">
            <span className="input-group__icon"><Icon name="search" /></span>
            <input className="input" type="search" value={search} onChange={(e) => setSearch(e.target.value)}
                   placeholder="Search name, code or community…" aria-label="Search farmers" />
          </div>
          {q && <a className="btn btn--ghost btn--sm" href="/farmers"><Icon name="x" />Clear</a>}
          <div className="toolbar__end text-muted" style={{ fontSize: 'var(--text-sm)' }}>{farmers.length} result(s)</div>
        </form>

        {farmers.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Farmer</th>
                  <th className="hide-sm">Community</th>
                  <th className="is-num hide-sm">Potential (kg)</th>
                  <th className="is-num hide-sm">Delivered (kg)</th>
                  <th className="is-num hide-sm">Remaining (kg)</th>
                  <th className="hide-sm">Quota used</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {farmers.map((f) => {
                  const remaining = f.potential_volume_kg - f.delivered
                  const pct = f.potential_volume_kg > 0 ? (f.delivered / f.potential_volume_kg) * 100 : 0
                  return (
                    <tr key={f.farmer_code}>
                      <td>
                        <a className="cell-person" href={`/farmers/${f.farmer_code}`} style={{ textDecoration: 'none' }}>
                          <Avatar fullName={f.full_name} />
                          <span><span className="cell-primary">{f.full_name}</span><span className="cell-secondary mono">{f.farmer_code}</span></span>
                        </a>
                      </td>
                      <td className="hide-sm">{f.community || '—'}</td>
                      <td className="is-num hide-sm">{formatKg(f.potential_volume_kg)}</td>
                      <td className="is-num hide-sm">{formatKg(f.delivered)}</td>
                      <td className="is-num hide-sm">{formatKg(remaining)}</td>
                      <td className="hide-sm"><MiniMeter pct={pct} /></td>
                      <td><FarmerStatusBadge active={f.active} pct={pct} /></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : q ? (
          <EmptyState title={`No farmers match "${q}"`} text="Try a different name, farmer code or community." iconName="search" />
        ) : (
          <EmptyState title="No farmers yet" text="Upload your farmer master list to build the register." iconName="users" actionHref="/upload" actionLabel="Upload master list" />
        )}
      </div>
    </>
  )
}
