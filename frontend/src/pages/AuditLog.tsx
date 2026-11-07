import { useApiGet } from '../api/useApiGet'
import { Alert, EmptyState, PageHeader } from '../components/ui'

interface AuditEntry {
  id: number
  action: string
  entity_type: string | null
  entity_id: string | null
  details: string | null
  created_at: string
  actor_name: string | null
}

const ACTION_LABELS: Record<string, string> = {
  'lot.created': 'Created a lot',
  'lot.accepted': 'Accepted a lot',
  'lot.rejected': 'Rejected a lot',
  'lot.receipts_generated': 'Generated receipts',
  'farmers.uploaded': 'Uploaded master data',
  'data.cleared': 'Cleared all data',
  'user.created': 'Added a team member',
  'user.toggled_active': 'Toggled a team member',
  'settings.updated': 'Updated settings',
  'document.uploaded': 'Uploaded a document',
  'document.deleted': 'Deleted a document',
}

export default function AuditLog() {
  const { data, error } = useApiGet<{ entries: AuditEntry[] }>('/audit-log')
  const entries = data?.entries ?? []

  return (
    <>
      <PageHeader title="Audit Log" desc="Who did what, and when. Last 200 actions." eyebrow="Administration" />
      {error && <Alert message={error} kind="error" />}

      <div className="card">
        {entries.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>When</th><th>Who</th><th>Action</th><th className="hide-sm">Detail</th></tr></thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td className="mono" style={{ whiteSpace: 'nowrap' }}>{e.created_at.replace('T', ' ').slice(0, 19)}</td>
                    <td>{e.actor_name || '—'}</td>
                    <td>{ACTION_LABELS[e.action] || e.action}{e.entity_id ? <span className="cell-secondary mono"> #{e.entity_id}</span> : null}</td>
                    <td className="hide-sm is-muted">{e.details || ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No activity yet" text="Actions like recording a lot, uploading master data, or changing settings will show up here." iconName="history" />
        )}
      </div>
    </>
  )
}
