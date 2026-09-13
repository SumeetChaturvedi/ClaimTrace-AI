import { useEffect, useRef, useState } from 'react'
import { ApiError } from './client'

export type ApiState<T> =
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string }

/**
 * Minimal fetch-on-mount hook: loading -> success | error. Intentionally
 * small — no cache, no retries, no global store. Deps drive re-fetching
 * (e.g. a changed project id).
 */
export function useApiQuery<T>(fetcher: () => Promise<T>, deps: unknown[]): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({ status: 'loading' })
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })
    fetcherRef
      .current()
      .then((data) => {
        if (!cancelled) setState({ status: 'success', data })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        const message = err instanceof ApiError ? err.message : 'Something went wrong.'
        setState({ status: 'error', error: message })
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
