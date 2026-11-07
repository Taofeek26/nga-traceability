import { useEffect, useState, useCallback, useRef } from 'react'
import { api, ApiError } from './client'

export function useApiGet<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const hasDataRef = useRef(false)

  const reload = useCallback(() => {
    if (!path) return
    setLoading(true)
    setError('')

    const attempt = (retriesLeft: number): void => {
      api.get<T>(path)
        .then((d) => {
          hasDataRef.current = true
          setData(d)
          setLoading(false)
        })
        .catch((err) => {
          // A background refresh (we already have data showing) is
          // non-critical and prone to one-off network blips - retry once
          // silently before surfacing anything, since the action that
          // triggered this reload has already succeeded regardless.
          if (retriesLeft > 0) {
            setTimeout(() => attempt(retriesLeft - 1), 800)
            return
          }
          console.error('useApiGet reload failed:', path, err)
          // Only alarm the user if we have nothing to show at all - a
          // failed background refresh of an already-loaded list should
          // stay quiet rather than imply the action that triggered it
          // (which already succeeded) went wrong.
          if (!hasDataRef.current) {
            setError(err instanceof ApiError ? err.message : 'Something went wrong.')
          }
          setLoading(false)
        })
    }
    attempt(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps])

  useEffect(reload, [reload])

  return { data, error, loading, reload }
}
