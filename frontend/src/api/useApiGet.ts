import { useEffect, useState, useCallback } from 'react'
import { api, ApiError } from './client'

export function useApiGet<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const reload = useCallback(() => {
    if (!path) return
    setLoading(true)
    setError('')
    api.get<T>(path)
      .then((d) => setData(d))
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Something went wrong.'))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps])

  useEffect(reload, [reload])

  return { data, error, loading, reload }
}
