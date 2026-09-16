import type { InvestigationResponse, DocumentSummary } from '../../api/types'
import { Prose, Muted } from '../../components/ui/Typography'
import { CitationList } from '../../components/evidence/CitationList'
import styles from './panels.module.css'

/**
 * The backend returns one free-text `answer` string; there is no separate
 * structured breakdown into conclusion, support, and gaps (see
 * api/types.ts). Rather than parsing that prose to invent such sections,
 * this panel renders it faithfully as written, in full, and lets the
 * record's own qualifications (for example "insufficient evidence") speak
 * for themselves as a legitimate result, not an error.
 */
export function FindingPanel({
  response,
  documentNames,
  documents,
  projectId,
  investigationId,
}: {
  response: InvestigationResponse
  documentNames: Record<number, string>
  documents: DocumentSummary[] | null
  projectId: number
  investigationId: string
}) {
  return (
    <div className={styles.panel}>
      <div>
        <div className={styles.findingRule}>
          <span className={styles.findingRuleNode} aria-hidden="true" />
          <h2 className={styles.findingHeading}>Finding</h2>
        </div>
        <div className={styles.findingText}>
          <Prose>{response.answer}</Prose>
        </div>
      </div>

      <p className={styles.disclaimer}>
        ClaimTrace gathers and cites evidence to support this investigation. It does not
        adjudicate disputes or issue a legal or contractual determination. Review the finding
        against the underlying sources before relying on it.
      </p>

      {response.citations.length === 0 ? (
        <Muted>No supporting citations were returned for this finding.</Muted>
      ) : (
        <>
          <div className={styles.findingConnector} aria-hidden="true">
            <span className={styles.findingConnectorLine} />
            <span className={styles.findingConnectorNode} />
          </div>
          <CitationList
            citations={response.citations}
            documentNames={documentNames}
            documents={documents}
            projectId={projectId}
            investigationId={investigationId}
          />
          <Muted>See Evidence for the full excerpt list, or Documents for the sources reviewed.</Muted>
        </>
      )}
    </div>
  )
}
