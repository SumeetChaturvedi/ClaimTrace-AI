import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, getInvestigation } from '../api/client'
import type { InvestigationRecord } from '../api/types'

export type InvestigationRecordState =
  | { status: 'loading' }
  | { status: 'not-found' }
  | { status: 'ready'; record: InvestigationRecord }
  | { status: 'error'; error: string }

/**
 * Fetches one persisted investigation by (projectId, investigationId) and
 * keeps it current. Never calls createInvestigation() — reopening an
 * investigation is a read, full stop, so Gemini is never re-invoked just to
 * view a result that already exists (see api/client.ts's getInvestigation
 * docstring).
 *
 * If the fetched record's status is still "running", this polls again after
 * a short delay — a plain repeated GET, not a background job queue — until
 * it reaches a terminal status. Realistically this only fires if a second
 * tab/window opens the same investigation while the first tab's create
 * request is still in flight: a single POST here always blocks until the
 * record is terminal before the frontend ever has an id to navigate to, so
 * under normal use this hook only ever observes 'completed' or 'failed'.
 *
 * A 404 (nonexistent id, OR an id that belongs to a different project — the
 * backend deliberately returns the identical 404 for both, so the frontend
 * can't and shouldn't try to tell them apart) surfaces as 'not-found'.
 */
export function useInvestigationRecord(
  projectId: number | null,
  investigationId: string | null,
): { state: InvestigationRecordState; refetch: () => void } {
  const [state, setState] = useState<InvestigationRecordState>({ status: 'loading' })
  const [reloadToken, setReloadToken] = useState(0)
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const refetch = useCallback(() => setReloadToken((t) => t + 1), [])

  useEffect(() => {
    if (projectId === null || investigationId === null) return
    let cancelled = false
    // eslint-disable-next-line react/set-state-in-effect
    setState({ status: 'loading' })

    const load = () => {
      getInvestigation(projectId, investigationId)
        .then((record) => {
          if (cancelled) return
          setState({ status: 'ready', record })
          if (record.status === 'running') {
            pollTimeoutRef.current = setTimeout(load, 2000)
          }
        })
        .catch((err: unknown) => {
          if (cancelled) return
          if (err instanceof ApiError && err.status === 404) {
            setState({ status: 'not-found' })
          } else {
            const message = err instanceof ApiError ? err.message : 'Something went wrong.'
            setState({ status: 'error', error: message })
          }
        })
    }
    load()

    return () => {
      cancelled = true
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current)
    }
  }, [projectId, investigationId, reloadToken])

  return { state, refetch }
}
