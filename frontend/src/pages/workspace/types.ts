export type WorkspaceTab = 'finding' | 'evidence' | 'events' | 'timeline' | 'contract' | 'documents' | 'trace'

export const WORKSPACE_TABS: { id: WorkspaceTab; label: string }[] = [
  { id: 'finding', label: 'Finding' },
  { id: 'evidence', label: 'Evidence' },
  // Phase 8B.3: AI-extracted event candidates (ExtractedEvent), distinct
  // from the deterministic, document-level "Timeline" tab below it
  // (TimelineEntry, Phase 4, no LLM involved) — kept as separate tabs
  // rather than merged, since they are genuinely different concepts with
  // different confidence characteristics.
  { id: 'events', label: 'Events' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'contract', label: 'Contract' },
  { id: 'documents', label: 'Documents' },
  { id: 'trace', label: 'Process' },
]
