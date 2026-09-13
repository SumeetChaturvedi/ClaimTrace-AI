export type WorkspaceTab = 'finding' | 'evidence' | 'timeline' | 'contract' | 'documents' | 'trace'

export const WORKSPACE_TABS: { id: WorkspaceTab; label: string }[] = [
  { id: 'finding', label: 'Finding' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'contract', label: 'Contract' },
  { id: 'documents', label: 'Documents' },
  { id: 'trace', label: 'Process' },
]
