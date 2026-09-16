import { useState } from 'react'
import type { ContractClause } from '../../api/types'
import { useInspector } from '../../components/layout/InspectorContext'
import { SectionLabel, Muted, Prose } from '../../components/ui/Typography'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/StateViews'
import styles from './ContractPanel.module.css'

// Long FIDIC sub-clauses commonly run past a thousand characters; collapsing
// past this point keeps the workspace from being dominated by one clause
// while always leaving an explicit "Show full provision" affordance rather
// than truncating silently.
const COLLAPSE_CHARS = 420

/**
 * Contract tab (Phase 5: Contract Intelligence Productization) — the real
 * contract clauses this investigation's own project-scoped retrieval
 * (backend/app/contracts/) surfaced while building the answer, exposed
 * instead of being discarded once the reasoning prompt was built.
 *
 * A contract provision is NOT investigation evidence. Unlike a Citation, a
 * ContractClause carries no document_id/chunk_id/page (see
 * api/types.ts) — the backend's contract-package loader never records which
 * source file a clause came from, let alone a page. So unlike the Evidence
 * and Timeline tabs, there is deliberately no "Open source document" action
 * here and no page-anchored PDF to jump to — adding one would mean
 * fabricating a source location that doesn't exist. Each clause is shown as
 * real, verbatim contract text (clause number, title, topic, full wording),
 * with no AI paraphrase and no invented reason for its relevance beyond
 * "retrieved as relevant to this investigation" — the honest extent of what
 * the backend's deterministic topic/keyword retrieval establishes. Order is
 * preserved exactly as the backend returned it — never re-sorted, never
 * scored, never labeled "primary."
 */
export function ContractPanel({ clauses }: { clauses: ContractClause[] }) {
  const { open } = useInspector()

  if (clauses.length === 0) {
    return (
      <div className={styles.panel}>
        <SectionLabel>Contractual Context</SectionLabel>
        <EmptyState title="No contractual provisions were returned for this investigation">
          <Muted>
            This investigation's contract-clause retrieval did not return any provisions for this
            question, or this investigation predates Contract Intelligence exposure.
          </Muted>
        </EmptyState>
      </div>
    )
  }

  return (
    <div className={styles.panel}>
      <div className={styles.intro}>
        <SectionLabel>Contractual Context</SectionLabel>
        <Muted>Relevant provisions identified in this investigation.</Muted>
      </div>

      <ol className={styles.list}>
        {clauses.map((clause, i) => (
          <ClauseRow
            key={`${clause.clause_number}-${i}`}
            clause={clause}
            index={i}
            onInspect={() => open({ kind: 'contractClause', clause })}
          />
        ))}
      </ol>
    </div>
  )
}

function ClauseRow({ clause, index, onInspect }: { clause: ContractClause; index: number; onInspect: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = clause.text.length > COLLAPSE_CHARS
  const displayText = expanded || !isLong ? clause.text : `${clause.text.slice(0, COLLAPSE_CHARS).trimEnd()}…`

  return (
    <li className={styles.clause}>
      <div className={styles.clauseHeader}>
        <span className={styles.clauseOrdinal}>{String(index + 1).padStart(2, '0')}</span>
        <h3 className={styles.clauseTitle}>
          <span className={styles.clauseNumber}>{clause.clause_number}</span> {clause.title}
        </h3>
        <Badge tone="neutral">{clause.topic}</Badge>
      </div>

      <div className={styles.clauseText}>
        <Prose>{displayText}</Prose>
      </div>
      {isLong && (
        <button className={styles.showMore} onClick={() => setExpanded((v) => !v)}>
          {expanded ? 'Show less' : 'Show full provision'}
        </button>
      )}

      <div className={styles.clauseFooter}>
        <Muted>Retrieved as relevant to this investigation.</Muted>
        <Button variant="secondary" onClick={onInspect}>
          Inspect
        </Button>
      </div>
    </li>
  )
}
