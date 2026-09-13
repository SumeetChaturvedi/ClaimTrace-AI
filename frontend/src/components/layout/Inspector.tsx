import { useInspector, type InspectorContent } from './InspectorContext'
import { LinkButton } from '../ui/LinkButton'
import { SectionLabel, Prose, Muted } from '../ui/Typography'
import { Badge } from '../ui/Badge'
import { citationLocationLabel } from '../../lib/documentFormat'
import styles from './Inspector.module.css'

/**
 * Reusable Inspector shell. Renders inline on wide viewports, as an
 * overlay drawer on narrow ones (see Inspector.module.css). Content is
 * driven entirely by InspectorContext so any future screen can push
 * content into it without touching this component.
 */
export function Inspector() {
  const { content, isOpen, close } = useInspector()

  if (!isOpen || !content) return null

  return (
    <>
      <div className={styles.backdrop} onClick={close} aria-hidden="true" />
      <aside className={styles.inspector} aria-label="Inspector">
        <div className={styles.header}>
          <SectionLabel>{headerLabel(content.kind)}</SectionLabel>
          <button className={styles.closeButton} onClick={close} aria-label="Close">
            ×
          </button>
        </div>
        <div className={styles.body}>
          {content.kind === 'citation' && <CitationInspector content={content} onNavigate={close} />}
          {content.kind === 'contractClause' && <ContractClauseInspector content={content} />}
          {content.kind !== 'citation' && content.kind !== 'contractClause' && (
            <Muted>This item can't be inspected yet.</Muted>
          )}
        </div>
      </aside>
    </>
  )
}

// A contract provision is not investigation evidence (see ContractPanel's
// own docstring) — the header reflects which kind of thing is open, rather
// than calling everything "Evidence Detail".
function headerLabel(kind: InspectorContent['kind']): string {
  return kind === 'contractClause' ? 'Contract Provision' : 'Evidence Detail'
}

function CitationInspector({
  content,
  onNavigate,
}: {
  content: Extract<InspectorContent, { kind: 'citation' }>
  onNavigate: () => void
}) {
  const { citation, documentName, documentType, documentDate, projectId, investigationId } = content
  return (
    <div className={styles.section}>
      <div>
        <SectionLabel>Source</SectionLabel>
        <dl className={styles.metaList}>
          <div>
            <dt>Document</dt>
            <dd>{documentName ?? `Document #${citation.document_id}`}</dd>
          </div>
          <div>
            <dt>Type</dt>
            <dd>{documentType ?? <Muted>Not recorded</Muted>}</dd>
          </div>
          <div>
            <dt>Date</dt>
            <dd>{documentDate ?? <Muted>Not recorded</Muted>}</dd>
          </div>
          <div>
            <dt>{citationLocationLabel(documentName)}</dt>
            <dd>{citation.page ?? <Muted>Not recorded</Muted>}</dd>
          </div>
          <div>
            <dt>Passage reference</dt>
            <dd>{citation.chunk_id}</dd>
          </div>
        </dl>
      </div>

      <div>
        <SectionLabel>Cited passage</SectionLabel>
        <Prose>{citation.chunk_text ?? <Muted>No excerpt text was returned for this citation.</Muted>}</Prose>
      </div>

      <div>
        <SectionLabel>Relevance</SectionLabel>
        <p className={styles.relevanceValue}>{citation.relevance_score.toFixed(2)}</p>
        <Muted>How closely this passage matched the investigation question during retrieval.</Muted>
      </div>

      <div>
        <LinkButton
          variant="secondary"
          to={`/projects/${projectId}/investigations/${investigationId}/source/${citation.chunk_id}`}
          onClick={onNavigate}
        >
          Open source document
        </LinkButton>
        <p className={styles.viewerNote}>
          For a PDF, opens the original document positioned at the cited page. For a Word
          document, shows this extracted passage with a link to download the original.
        </p>
      </div>
    </div>
  )
}

function ContractClauseInspector({
  content,
}: {
  content: Extract<InspectorContent, { kind: 'contractClause' }>
}) {
  const { clause } = content
  return (
    <div className={styles.section}>
      <div>
        <SectionLabel>Provision</SectionLabel>
        <dl className={styles.metaList}>
          <div>
            <dt>Clause</dt>
            <dd>{clause.clause_number}</dd>
          </div>
          <div>
            <dt>Topic</dt>
            <dd>
              <Badge tone="neutral">{clause.topic}</Badge>
            </dd>
          </div>
        </dl>
      </div>

      <div>
        <SectionLabel>{clause.title}</SectionLabel>
        <Prose>{clause.text}</Prose>
      </div>

      <div>
        <p className={styles.viewerNote}>
          This is the full text of a contract provision retrieved as relevant to this
          investigation. It is contractual context, not investigation evidence — the project's
          contract package is not linked to a specific source document or page in the current
          system, so there is no source document to open for it.
        </p>
      </div>
    </div>
  )
}
