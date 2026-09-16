import { useMemo, useState } from 'react'
import type { Citation, DocumentSummary } from '../../api/types'
import { useInspector } from '../../components/layout/InspectorContext'
import { SectionLabel, Muted } from '../../components/ui/Typography'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { EmptyState, LoadingState } from '../../components/ui/StateViews'
import { citationLocationShort } from '../../lib/documentFormat'
import styles from './EvidenceWorkbench.module.css'

/**
 * Evidence Workbench v1 — the Evidence tab's content. Read-oriented: every
 * row is a real Citation from this investigation's InvestigationResponse,
 * enriched (by document_id) with real GET /documents metadata already
 * fetched by InvestigationWorkspacePage. Nothing here is fetched
 * independently by a user-controlled id — `citations` and `documents` are
 * both handed down already resolved against the validated investigation.
 *
 * Deliberately does NOT implement "Key Evidence" / "Supporting" /
 * "Conflicting" lenses: no field on Citation, Evidence, or
 * InvestigationResponse (see api/types.ts) distinguishes evidence that
 * way. Adding them would mean inventing a classification the backend
 * never made. The two lenses beyond "All" that ARE implemented —
 * "By Document" (a real grouping of real citations by their real
 * document_id — labeled distinctly from the workspace's own top-level
 * "Documents" tab to avoid two same-named controls on screen at once) and
 * "Contractual" (a real filter on the real,
 * backend-classified `doc_type === 'CONTRACT'`, never a filename guess) —
 * are both backed entirely by fields that actually exist.
 */

type Lens = 'all' | 'documents' | 'contractual'
type SortKey = 'relevance' | 'page' | 'document'

interface EnrichedEvidence {
  citation: Citation
  document?: DocumentSummary
  documentLabel: string
}

interface DocumentGroup {
  key: string
  documentLabel: string
  document?: DocumentSummary
  items: EnrichedEvidence[]
}

export function EvidencePanel({
  citations,
  documents,
  documentNames,
  projectId,
  investigationId,
}: {
  citations: Citation[]
  documents: DocumentSummary[] | null
  documentNames: Record<number, string>
  projectId: number
  investigationId: string
}) {
  const { open, content } = useInspector()
  const activeChunkId = content?.kind === 'citation' && content.investigationId === investigationId ? content.citation.chunk_id : null
  const [lens, setLens] = useState<Lens>('all')
  const [query, setQuery] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('relevance')

  const documentsById = useMemo(() => {
    const map = new Map<number, DocumentSummary>()
    for (const d of documents ?? []) map.set(d.id, d)
    return map
  }, [documents])

  const enriched: EnrichedEvidence[] = useMemo(
    () =>
      citations.map((citation) => {
        const document = documentsById.get(citation.document_id)
        return {
          citation,
          document,
          documentLabel: document?.filename ?? documentNames[citation.document_id] ?? `Document #${citation.document_id}`,
        }
      }),
    [citations, documentsById, documentNames],
  )

  const hasContractualEvidence = enriched.some((e) => e.document?.doc_type === 'CONTRACT')

  const searched = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return enriched
    return enriched.filter(
      (e) => (e.citation.chunk_text ?? '').toLowerCase().includes(q) || e.documentLabel.toLowerCase().includes(q),
    )
  }, [enriched, query])

  const lensed = useMemo(() => {
    if (lens === 'contractual') return searched.filter((e) => e.document?.doc_type === 'CONTRACT')
    return searched
  }, [searched, lens])

  const sorted = useMemo(() => sortEvidence(lensed, sortKey), [lensed, sortKey])

  if (citations.length === 0) {
    return (
      <div className={styles.workbench}>
        <SectionLabel>Evidence</SectionLabel>
        <EmptyState title="No citations were returned for this investigation">
          <Muted>The investigation completed without any supporting citations, so there is no evidence to review.</Muted>
        </EmptyState>
      </div>
    )
  }

  const openCitation = (item: EnrichedEvidence) =>
    open({
      kind: 'citation',
      citation: item.citation,
      documentName: item.document?.filename ?? documentNames[item.citation.document_id],
      documentType: item.document?.doc_type,
      documentDate: item.document?.doc_date,
      projectId,
      investigationId,
    })

  const groups = lens === 'documents' ? groupByDocument(sorted) : null

  return (
    <div className={styles.workbench}>
      <div className={styles.intro}>
        <SectionLabel>Evidence</SectionLabel>
        <Muted>Review the source excerpts behind this investigation's finding.</Muted>
      </div>

      <div className={styles.controls}>
        <div className={styles.lenses}>
          <Button variant={lens === 'all' ? 'primary' : 'secondary'} onClick={() => setLens('all')}>
            All
          </Button>
          <Button variant={lens === 'documents' ? 'primary' : 'secondary'} onClick={() => setLens('documents')}>
            By Document
          </Button>
          {hasContractualEvidence && (
            <Button variant={lens === 'contractual' ? 'primary' : 'secondary'} onClick={() => setLens('contractual')}>
              Contractual
            </Button>
          )}
        </div>

        <div className={styles.searchSort}>
          <input
            type="search"
            className={styles.searchInput}
            placeholder="Search evidence…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search evidence"
          />
          <label className={styles.sortLabel}>
            Sort:
            <select
              className={styles.sortSelect}
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
            >
              <option value="relevance">Relevance</option>
              <option value="page">Page</option>
              <option value="document">Document</option>
            </select>
          </label>
        </div>
      </div>

      {documents === null && <LoadingState label="Resolving document metadata…" />}

      <Muted>
        {sorted.length === citations.length
          ? `${sorted.length} evidence item${sorted.length === 1 ? '' : 's'}`
          : `${sorted.length} of ${citations.length} evidence items`}
      </Muted>

      {sorted.length === 0 ? (
        <EmptyState title="No evidence matches this search">
          <Muted>
            Try a different search term, or clear it to see all {citations.length} citation
            {citations.length === 1 ? '' : 's'} again.
          </Muted>
        </EmptyState>
      ) : groups ? (
        <div className={styles.groups}>
          {groups.map((group) => (
            <div key={group.key} className={styles.group}>
              <div className={styles.groupHeader}>
                <span className={styles.groupName}>{group.documentLabel}</span>
                {group.document?.doc_type && <Badge tone="neutral">{group.document.doc_type}</Badge>}
                <Muted>
                  {group.items.length} citation{group.items.length === 1 ? '' : 's'}
                </Muted>
              </div>
              <ul className={styles.rowList}>
                {group.items.map((item, i) => (
                  <EvidenceRow
                    key={rowKey(item, i)}
                    item={item}
                    index={i}
                    active={item.citation.chunk_id === activeChunkId}
                    onOpen={() => openCitation(item)}
                  />
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : (
        <ul className={styles.rowList}>
          {sorted.map((item, i) => (
            <EvidenceRow
              key={rowKey(item, i)}
              item={item}
              index={i}
              active={item.citation.chunk_id === activeChunkId}
              onOpen={() => openCitation(item)}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

function EvidenceRow({
  item,
  index,
  active,
  onOpen,
}: {
  item: EnrichedEvidence
  index: number
  active: boolean
  onOpen: () => void
}) {
  const { citation, document, documentLabel } = item
  return (
    <li>
      <button className={`${styles.row} ${active ? styles.rowActive : ''}`} onClick={onOpen} aria-pressed={active}>
        <span className={styles.rowOrdinal}>{String(index + 1).padStart(2, '0')}</span>
        <div className={styles.rowBody}>
          <div className={styles.rowHeader}>
            <span className={styles.docName}>{documentLabel}</span>
            {citation.page != null && (
              <span className={styles.metaBit}>{citationLocationShort(documentLabel, citation.page)}</span>
            )}
            {document?.doc_date && <span className={styles.metaBit}>{document.doc_date}</span>}
          </div>
          <p className={styles.excerpt}>
            {citation.chunk_text ?? <Muted>No excerpt text was returned for this citation.</Muted>}
          </p>
          <div className={styles.rowFooter}>
            <span>Passage {citation.chunk_id}</span>
            <span>Relevance {citation.relevance_score.toFixed(2)}</span>
            {document?.doc_type && <Badge tone="neutral">{document.doc_type}</Badge>}
          </div>
        </div>
        <span className={styles.rowArrow} aria-hidden="true">→</span>
      </button>
    </li>
  )
}

function sortEvidence(items: EnrichedEvidence[], sortKey: SortKey): EnrichedEvidence[] {
  const copy = [...items]
  if (sortKey === 'relevance') {
    copy.sort((a, b) => b.citation.relevance_score - a.citation.relevance_score)
  } else if (sortKey === 'page') {
    // Null pages are never treated as page 0 — they consistently sort
    // after every citation that does have a real page number.
    copy.sort((a, b) => {
      const pa = a.citation.page
      const pb = b.citation.page
      if (pa == null && pb == null) return 0
      if (pa == null) return 1
      if (pb == null) return -1
      return pa - pb
    })
  } else if (sortKey === 'document') {
    copy.sort((a, b) => a.documentLabel.localeCompare(b.documentLabel))
  }
  return copy
}

function groupByDocument(items: EnrichedEvidence[]): DocumentGroup[] {
  const order: string[] = []
  const map = new Map<string, DocumentGroup>()
  for (const item of items) {
    const key = item.documentLabel
    if (!map.has(key)) {
      map.set(key, { key, documentLabel: key, document: item.document, items: [] })
      order.push(key)
    }
    map.get(key)!.items.push(item)
  }
  return order.map((key) => map.get(key)!)
}

function rowKey(item: EnrichedEvidence, index: number): string {
  return `${item.citation.document_id}-${item.citation.chunk_id}-${index}`
}
