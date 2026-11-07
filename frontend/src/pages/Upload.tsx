import { useRef, useState, type DragEvent, type FormEvent } from 'react'
import { api, ApiError } from '../api/client'
import { Alert, ButtonIcon, Icon, PageHeader } from '../components/ui'

export default function Upload() {
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [templateBusy, setTemplateBusy] = useState(false)
  const [exportBusy, setExportBusy] = useState(false)
  const [clearBusy, setClearBusy] = useState(false)
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
    if (!confirm('This permanently deletes every farmer and lot record. Continue?')) return
    const form = new FormData(formEl)
    setError('')
    setMsg('')
    setClearBusy(true)
    try {
      await api.post('/farmers/clear-all', { confirm: form.get('confirm') })
      setMsg('All data cleared.')
      formEl.reset()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Type CLEAR exactly to confirm.')
    } finally {
      setClearBusy(false)
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
                {['Farmer id', 'Gender', 'Date of birth', 'Phone number', 'NIN', 'Community Name', 'Num plots', 'Total Farm Size Mapped (Ha)'].map((c) => (
                  <span key={c} className="code-tag" style={{ background: 'var(--cream)', color: 'var(--taupe)' }}>{c}</span>
                ))}
              </div>
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

      <div className="danger-zone" style={{ marginTop: 'var(--space-10)' }}>
        <div className="danger-zone__header">
          <span className="danger-zone__icon"><Icon name="trash" /></span>
          <div>
            <div className="danger-zone__title">Clear all data</div>
            <p className="danger-zone__text">Removes every farmer, lot, delivery and incentive record for this LBA. Use this to start a new season from scratch. This cannot be undone — there is no backup.</p>
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
