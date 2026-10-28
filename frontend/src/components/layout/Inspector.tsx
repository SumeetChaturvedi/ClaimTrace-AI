import { useInspector, type InspectorContent } from './InspectorContext'
import { LinkButton } from '../ui/LinkButton'
import { SectionLabel, Prose, Muted, NotAvailable } from '../ui/Typography'
import { Badge } from '../ui/Badge'
import { citationLocationLabel, derivationBadgeLabel } from '../../lib/documentFormat'
import { formatEnumLabel } from '../../lib/eventTimeline'
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
          {content.kind === 'timelineEvent' && <EventInspector content={content} onNavigate={close} />}
          {content.kind !== 'citation' && content.kind !== 'contractClause' && content.kind !== 'timelineEvent' && (
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
  if (kind === 'contractClause') return 'Contract Provision'
  if (kind === 'timelineEvent') return 'Extracted Event'
  return 'Evidence Detail'
}

function CitationInspector({
  content,
  onNavigate,
}: {
  content: Extract<InspectorContent, { kind: 'citation' }>
  onNavigate: () => void
}) {
  const { citation, documentName, documentType, documentDate, documentDerivationKind, projectId, investigationId } = content
  const provenanceLabel = derivationBadgeLabel(documentDerivationKind)
  return (
    <div className={styles.section}>
      <div>
        <SectionLabel>Source</SectionLabel>
        <dl className={styles.metaList}>
          <div>
            <dt>Document</dt>
            <dd>
              {documentName ?? `Document #${citation.document_id}`}
              {provenanceLabel && (
                <span className={styles.provenanceBadge}>
                  <Badge tone="neutral">{provenanceLabel}</Badge>
                </span>
              )}
            </dd>
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

function EventInspector({
  content,
  onNavigate,
}: {
  content: Extract<InspectorContent, { kind: 'timelineEvent' }>
  onNavigate: () => void
}) {
  const { event, matchingCitation, documentName, documentType, projectId, investigationId } = content

  return (
    <div className={styles.section}>
      <div className={styles.aiNotice}>
        <Badge tone="amber">AI-extracted</Badge>
        <Muted>
          An evidence-linked candidate for investigator review, not a verified fact or legal
          conclusion. Confirm it against the supporting excerpt below before relying on it.
        </Muted>
      </div>

      <div>
        <SectionLabel>Source</SectionLabel>
        <dl className={styles.metaList}>
          <div>
            <dt>Document</dt>
            <dd>{documentName ?? `Document #${event.document_id}`}</dd>
          </div>
          <div>
            <dt>Type</dt>
            <dd>{documentType ?? <Muted>Not recorded</Muted>}</dd>
          </div>
          <div>
            <dt>Passage reference</dt>
            <dd>{event.chunk_id}</dd>
          </div>
        </dl>
      </div>

      <div>
        <SectionLabel>Event</SectionLabel>
        <dl className={styles.metaList}>
          <div>
            <dt>Event type</dt>
            <dd>{event.event_type ? formatEnumLabel(event.event_type) : <NotAvailable reason="No existing event-type category fit this evidence" />}</dd>
          </div>
          <div>
            <dt>Assertion type</dt>
            <dd>{event.assertion_type ? formatEnumLabel(event.assertion_type) : <NotAvailable reason="The evidence did not clearly support a classification" />}</dd>
          </div>
          <div>
            <dt>Event date</dt>
            <dd>
              {event.event_date ?? <Muted>Unknown — not resolved from the evidence</Muted>}
              {event.event_date && <span className={styles.dateBasis}> ({formatEnumLabel(event.event_date_basis)})</span>}
            </dd>
          </div>
          <div>
            <dt>Attributed party</dt>
            <dd>{event.attributed_party ?? <NotAvailable reason="The evidence did not support attributing this to a specific party" />}</dd>
          </div>
        </dl>
      </div>

      <div>
        <SectionLabel>Supporting excerpt</SectionLabel>
        <Prose>{event.excerpt}</Prose>
        <p className={styles.viewerNote}>
          This excerpt's own event date may differ from the date the source message or document
          was sent — the two are tracked separately and are never the same field.
        </p>
      </div>

      {matchingCitation ? (
        <div>
          <LinkButton
            variant="secondary"
            to={`/projects/${projectId}/investigations/${investigationId}/source/${matchingCitation.chunk_id}`}
            onClick={onNavigate}
          >
            Open source document
          </LinkButton>
          <p className={styles.viewerNote}>
            For a PDF, opens the original document positioned at the cited page. For a Word
            document, shows this extracted passage with a link to download the original.
          </p>
        </div>
      ) : (
        <Muted>
          This event's exact source view can't be opened separately in this investigation — the
          excerpt above is shown verbatim as returned.
        </Muted>
      )}
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
