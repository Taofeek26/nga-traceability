import { useRef, useState, type DragEvent, type FormEvent } from 'react'
import { useApiGet } from '../api/useApiGet'
import { api, ApiError } from '../api/client'
import { Alert, ButtonIcon, EmptyState, Icon, PageHeader, PageLoader } from '../components/ui'

interface Doc {
  id: number
  filename: string
  content_type: string | null
  size_bytes: number | null
  note: string | null
  created_at: string
  uploaded_by_name: string | null
}

function formatSize(bytes: number | null): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function Documents() {
  const { data, error: loadError, loading, reload } = useApiGet<{ documents: Doc[] }>('/documents')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [busyId, setBusyId] = useState<number | null>(null)
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
    setError('')
    const file = fileInput.current?.files?.[0]
    if (!file) return
    setBusy(true)
    try {
      const form = new FormData()
      form.append('file', file)
      await api.post('/documents', form)
      setFileName('')
      if (fileInput.current) fileInput.current.value = ''
      reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  async function download(id: number) {
    setBusyId(id)
    try {
      const resp = await api.get<{ download_url: string }>(`/documents/${id}/download`)
      window.open(resp.download_url, '_blank')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not generate the download link.')
    } finally {
      setBusyId(null)
    }
  }

  async function remove(id: number) {
    if (!confirm('Delete this document? This cannot be undone.')) return
    setBusyId(id)
    try {
      await api.delete(`/documents/${id}`)
      reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not delete the document.')
    } finally {
      setBusyId(null)
    }
  }

  const docs = data?.documents ?? []

  if (loading && !data) return <PageLoader />

  return (
    <>
      <PageHeader title="Documents" desc="Supporting evidence for traceability — certificates, lab results, contracts. Any file type." />

      {(error || loadError) && <Alert message={error || loadError} kind="error" />}

      <form className="card" onSubmit={onSubmit} style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card__header">
          <div>
            <div className="card__title"><Icon name="upload" />Upload a document</div>
            <div className="card__subtitle">PDF, image, Word, or any other file format</div>
          </div>
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
            <input ref={fileInput} type="file" required
                   onChange={(e) => setFileName(e.target.files?.[0]?.name || '')} />
            <span className="dropzone__icon"><Icon name="file-sheet" size="lg" /></span>
            <span className="dropzone__title">Drop a file here or <u>browse</u></span>
            <span className="dropzone__hint">Any file type accepted</span>
            <span className="dropzone__file">{fileName}</span>
          </label>
        </div>
        <div className="card__footer">
          <button className="btn btn--primary" type="submit" disabled={busy}><ButtonIcon name="upload" busy={busy} />Upload</button>
        </div>
      </form>

      <div className="card">
        <div className="card__header"><div className="card__title"><Icon name="file-sheet" />Uploaded documents</div></div>
        {docs.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>File</th><th className="hide-sm">Uploaded by</th><th className="hide-sm">Date</th><th className="is-num hide-sm">Size</th><th className="is-action" /></tr></thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.id}>
                    <td><span className="cell-primary">{d.filename}</span></td>
                    <td className="hide-sm is-muted">{d.uploaded_by_name || '—'}</td>
                    <td className="hide-sm is-muted">{d.created_at.slice(0, 10)}</td>
                    <td className="is-num hide-sm">{formatSize(d.size_bytes)}</td>
                    <td className="is-action">
                      <div className="cluster">
                        <button className="btn btn--ghost btn--sm" type="button" disabled={busyId === d.id} onClick={() => download(d.id)}><ButtonIcon name="download" busy={busyId === d.id} />Download</button>
                        <button className="btn btn--ghost btn--sm" type="button" disabled={busyId === d.id} onClick={() => remove(d.id)}><ButtonIcon name="trash" busy={busyId === d.id} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No documents yet" text="Upload certificates or other supporting evidence for traceability." iconName="file-sheet" />
        )}
      </div>
    </>
  )
}
