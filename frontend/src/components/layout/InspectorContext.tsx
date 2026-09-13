import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { Citation, ContractClause } from '../../api/types'

/**
 * Reusable Inspector content model. 'citation' (Evidence tab, Timeline tab)
 * and 'contractClause' (Contract tab, Phase 5) have real renderers.
 * 'document'/'timelineEvent' are declared for future screens that haven't
 * been built yet — Inspector.tsx renders a "not yet implemented"
 * placeholder for those.
 */
export type InspectorContent =
  | {
      kind: 'citation'
      citation: Citation
      documentName?: string
      documentType?: string | null
      documentDate?: string | null
      /** The investigation this citation came from, required so "Open
       * source" can link to a Source View nested under the same
       * project and investigation, never a bare /documents/:id lookup that
       * could cross project boundaries. */
      projectId: number
      investigationId: string
    }
  | { kind: 'document'; documentId: number }
  | { kind: 'timelineEvent' }
  | {
      kind: 'contractClause'
      /** The real ContractClause this investigation retrieved (Phase 5) —
       * clause_number/title/topic/text only. Deliberately no document/page:
       * see ContractClause's own definition in api/types.ts for why there is
       * no "Open source document" action for this kind. */
      clause: ContractClause
    }

interface InspectorContextValue {
  content: InspectorContent | null
  isOpen: boolean
  open: (content: InspectorContent) => void
  close: () => void
}

const InspectorContext = createContext<InspectorContextValue | null>(null)

export function InspectorProvider({ children }: { children: ReactNode }) {
  const [content, setContent] = useState<InspectorContent | null>(null)

  const open = useCallback((next: InspectorContent) => setContent(next), [])
  const close = useCallback(() => setContent(null), [])

  const value = useMemo(
    () => ({ content, isOpen: content !== null, open, close }),
    [content, open, close],
  )

  return <InspectorContext.Provider value={value}>{children}</InspectorContext.Provider>
}

export function useInspector(): InspectorContextValue {
  const ctx = useContext(InspectorContext)
  if (!ctx) throw new Error('useInspector must be used within InspectorProvider')
  return ctx
}
