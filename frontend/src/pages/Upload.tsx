import { useRef, useState, type DragEvent, type FormEvent } from 'react'
import { useApiGet } from '../api/useApiGet'
import { api, ApiError } from '../api/client'
import { Alert, ButtonIcon, Icon, PageHeader } from '../components/ui'

interface SeasonBackup {
  id: number
  season_start: string
  season_end: string
  n_farmers: number
  n_lots: number
  size_bytes: number
  created_at: string
  restored_at: string | null
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function Upload() {
  const { data: backupsData, reload: reloadBackups } =
    useApiGet<{ backups: SeasonBackup[]; register_is_empty: boolean }>('/season-backups')
  const backups = backupsData?.backups ?? []
  const registerIsEmpty = backupsData?.register_is_empty ?? false

  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [templateBusy, setTemplateBusy] = useState(false)
  const [exportBusy, setExportBusy] = useState(false)
  const [clearBusy, setClearBusy] = useState(false)
  const [backupBusyId, setBackupBusyId] = useState<number | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [fileName, setFileName] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  function onDrag(e: DragEvent, active: boolean) {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(active)
  }

  function onDrop(e: DragEvent<HTMLLabelElement>) {
    onDrag(e, false)
    const files = e.dataTransfer?.files
    if (files && files.length && fileInput.current) {
      fileInput.current.files = files
      setFileName(files[0].name)
    }
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setMsg('')
    setError('')
    const file = fileInput.current?.files?.[0]
    if (!file) return
    setBusy(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const resp = await api.post<{ inserted: number; updated: number; skipped: number }>('/farmers/upload', form)
      let m = `${resp.inserted} farmer(s) added, ${resp.updated} updated`
      if (resp.skipped) m += `, ${resp.skipped} row(s) skipped (missing farmer code)`
      setMsg(m)
      setFileName('')
      if (fileInput.current) fileInput.current.value = ''
      reloadBackups()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  async function downloadTemplate() {
    setTemplateBusy(true)
    try {
      const resp = await api.get<{ download_url: string }>('/farmers/upload-template')
      window.open(resp.download_url, '_blank')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not generate the template.')
    } finally {
      setTemplateBusy(false)
    }
  }

  async function downloadExport() {
    setExportBusy(true)
    try {
      const resp = await api.get<{ download_url: string }>('/farmers/export')
      window.open(resp.download_url, '_blank')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not generate the export.')
    } finally {
      setExportBusy(false)
    }
  }

  async function clearAll(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const formEl = e.currentTarget
    if (!confirm('This clears every farmer and lot record. A backup of the current data is taken automatically first, and you can restore it later. Continue?')) return
    const form = new FormData(formEl)
    setError('')
    setMsg('')
    setClearBusy(true)
    try {
      const resp = await api.post<{ ok: boolean; backup: { season_start: string; season_end: string } | null }>(
        '/farmers/clear-all', { confirm: form.get('confirm') }
      )
      setMsg(resp.backup
        ? `All data cleared. Backed up as a season covering ${resp.backup.season_start} to ${resp.backup.season_end} — see Season Backups below.`
        : 'All data cleared.')
      formEl.reset()
      reloadBackups()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Type CLEAR exactly to confirm.')
    } finally {
      setClearBusy(false)
    }
  }

  async function downloadBackup(id: number) {
    setBackupBusyId(id)
    setError('')
    try {
      const resp = await api.get<{ download_url: string }>(`/season-backups/${id}/download`)
      window.open(resp.download_url, '_blank')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not generate the download link.')
    } finally {
      setBackupBusyId(null)
    }
  }

  async function restoreBackup(id: number, b: SeasonBackup) {
    if (!confirm(`Restore the ${b.season_start} to ${b.season_end} season? This brings back ${b.n_farmers} farmer(s) and ${b.n_lots} lot(s).`)) return
    setBackupBusyId(id)
    setError('')
    setMsg('')
    try {
      const resp = await api.post<{ ok: boolean; n_farmers: number; n_lots: number }>(`/season-backups/${id}/restore`)
      setMsg(`Restored: ${resp.n_farmers} farmer(s) and ${resp.n_lots} lot(s) are back.`)
      reloadBackups()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not restore that season.')
    } finally {
      setBackupBusyId(null)
    }
  }

  async function deleteBackup(id: number, b: SeasonBackup) {
    if (!confirm(`Permanently delete the ${b.season_start} to ${b.season_end} season backup? This cannot be undone — the ${b.n_farmers} farmer(s) and ${b.n_lots} lot(s) in it will no longer be recoverable.`)) return
    setBackupBusyId(id)
    setError('')
    setMsg('')
    try {
      await api.delete(`/season-backups/${id}`)
      setMsg('Season backup deleted.')
      reloadBackups()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not delete that backup.')
    } finally {
      setBackupBusyId(null)
    }
  }

  return (
    <>
      <PageHeader title="Master Data" desc="Upload or refresh the farmer register. Re-uploading updates existing farmers (matched by Farmer Code) and adds new ones — nothing is deleted." eyebrow="Administration" />

      {msg && <Alert message={msg} kind="success" />}
      {error && <Alert message={error} kind="error" />}

      <form className="card" onSubmit={onSubmit}>
        <div className="card__header">
          <div>
            <div className="card__title"><Icon name="file-sheet" />Upload farmer list</div>
            <div className="card__subtitle">Excel workbook (.xlsx), first sheet is read</div>
          </div>
          <button type="button" className="btn btn--soft btn--sm" disabled={templateBusy} onClick={downloadTemplate}><ButtonIcon name="download" busy={templateBusy} />Template</button>
        </div>
        <div className="card__body">
          <label
            className={'dropzone' + (dragActive ? ' dropzone--active' : '')}
            onDragEnter={(e) => onDrag(e, true)}
            onDragOver={(e) => onDrag(e, true)}
            onDragLeave={(e) => onDrag(e, false)}
            onDragEnd={(e) => onDrag(e, false)}
            onDrop={onDrop}
          >
            <input ref={fileInput} type="file" accept=".xlsx" required
                   onChange={(e) => setFileName(e.target.files?.[0]?.name || '')} />
            <span className="dropzone__icon"><Icon name="upload" size="lg" /></span>
            <span className="dropzone__title">Drop your .xlsx here or <u>browse</u></span>
            <span className="dropzone__hint">Column names are not case sensitive</span>
            <span className="dropzone__file">{fileName}</span>
          </label>

          <div className="grid grid--2" style={{ marginTop: 'var(--space-5)', gap: 'var(--space-4)' }}>
            <div>
              <div className="label" style={{ marginBottom: 'var(--space-2)' }}>Required columns</div>
              <div className="chips">
                {['Farmer Code', 'Farmer Full name', 'Potential Volume'].map((c) => <span key={c} className="code-tag">{c}</span>)}
              </div>
              <p className="hint" style={{ marginTop: 'var(--space-2)' }}>"Farmer Full name" can also be given as separate "First name" + "Surname" columns.</p>
            </div>
            <div>
              <div className="label" style={{ marginBottom: 'var(--space-2)' }}>Optional columns</div>
              <div className="chips">
                {['Farmer id', 'Gender', 'Date of birth', 'Phone number', 'NIN', 'Community Name', 'Num plots', 'Total Farm Size Mapped (Ha)', 'Net Weight (Kg)'].map((c) => (
                  <span key={c} className="code-tag" style={{ background: 'var(--cream)', color: 'var(--taupe)' }}>{c}</span>
                ))}
              </div>
              <p className="hint" style={{ marginTop: 'var(--space-2)' }}>"Net Weight (Kg)" is for a farmer who already has delivery history from before this system — fill it in with their total delivered-to-date, from a register you tracked manually or a previous export from here. Leave it out, or at 0, for a farmer with no prior history.</p>
            </div>
          </div>
        </div>
        <div className="card__footer">
          <button className="btn btn--primary" type="submit" disabled={busy}><ButtonIcon name="upload" busy={busy} />Upload</button>
        </div>
      </form>

      <div className="card" style={{ marginTop: 'var(--space-6)' }}>
        <div className="card__header">
          <div>
            <div className="card__title"><Icon name="download" />Export yield monitoring</div>
            <div className="card__subtitle">Current register in the same layout, with delivered volume, variance and premium calculated per farmer.</div>
          </div>
          <button type="button" className="btn btn--soft btn--sm" disabled={exportBusy} onClick={downloadExport}><ButtonIcon name="download" busy={exportBusy} />Export .xlsx</button>
        </div>
      </div>

      <div className="card" style={{ marginTop: 'var(--space-6)' }}>
        <div className="card__header">
          <div>
            <div className="card__title"><Icon name="history" />Season backups</div>
            <div className="card__subtitle">Taken automatically every time "Clear all data" is used, named by the season it covers. Restore one to look back at a previous season, once your current register is empty.</div>
          </div>
        </div>
        {backups.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Season</th><th className="is-num">Farmers</th><th className="is-num">Lots</th><th>Size</th><th>Status</th><th className="is-action" /></tr>
              </thead>
              <tbody>
                {backups.map((b) => (
                  <tr key={b.id}>
                    <td><span className="cell-primary">{b.season_start} &rarr; {b.season_end}</span><span className="cell-secondary">Cleared {b.created_at.slice(0, 10)}</span></td>
                    <td className="is-num">{b.n_farmers}</td>
                    <td className="is-num">{b.n_lots}</td>
                    <td className="is-muted">{formatSize(b.size_bytes)}</td>
                    <td>{b.restored_at ? <span className="badge badge--ok">Restored</span> : <span className="is-muted">&mdash;</span>}</td>
                    <td className="is-action">
                      <span style={{ display: 'inline-flex', gap: 'var(--space-2)' }}>
                        <button type="button" className="btn btn--ghost btn--sm" disabled={backupBusyId === b.id} onClick={() => downloadBackup(b.id)}>
                          <ButtonIcon name="download" busy={backupBusyId === b.id} />Download
                        </button>
                        <button type="button" className="btn btn--soft btn--sm" disabled={backupBusyId === b.id || !registerIsEmpty}
                                title={registerIsEmpty ? '' : 'Clear the current register first'}
                                onClick={() => restoreBackup(b.id, b)}>
                          <ButtonIcon name="upload" busy={backupBusyId === b.id} />Restore
                        </button>
                        <button type="button" className="btn btn--ghost btn--sm" disabled={backupBusyId === b.id}
                                onClick={() => deleteBackup(b.id, b)}>
                          <ButtonIcon name="trash" busy={backupBusyId === b.id} />Delete
                        </button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="card__body"><p className="text-muted">No backups yet — one is taken automatically the first time you clear all data.</p></div>
        )}
      </div>

      <div className="danger-zone" style={{ marginTop: 'var(--space-10)' }}>
        <div className="danger-zone__header">
          <span className="danger-zone__icon"><Icon name="trash" /></span>
          <div>
            <div className="danger-zone__title">Clear all data</div>
            <p className="danger-zone__text">Removes every farmer, lot, delivery and incentive record for this LBA. Use this to start a new season from scratch. A full backup is taken automatically first — see Season Backups above to restore it later.</p>
          </div>
        </div>
        <form className="danger-zone__body" onSubmit={clearAll}>
          <div className="field" style={{ maxWidth: 280 }}>
            <label className="label" htmlFor="confirm-clear">Type <span className="mono">CLEAR</span> to confirm</label>
            <input className="input" id="confirm-clear" type="text" name="confirm" placeholder="CLEAR" required autoComplete="off" />
          </div>
          <div className="form-actions" style={{ marginTop: 'var(--space-4)' }}>
            <button className="btn btn--danger" type="submit" disabled={clearBusy}><ButtonIcon name="trash" busy={clearBusy} />Clear all data</button>
          </div>
        </form>
      </div>
    </>
  )
}
