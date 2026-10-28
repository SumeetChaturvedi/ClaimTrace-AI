/**
 * Format-detection helpers (Phase 7: Multi-Format Evidence).
 *
 * The backend derives a document's format from its own filename extension
 * (see backend/app/ingestion/pipeline.py's _SUPPORTED_EXTENSIONS) rather
 * than a separate stored field, since the filename already carries it
 * unambiguously — these helpers mirror that exact convention on the
 * frontend rather than inventing a new "format" field that doesn't exist
 * on DocumentSummary/Citation.
 *
 * Citation.page (see api/types.ts) means different things for different
 * formats: a true page number for a PDF, a 1-based paragraph ordinal for a
 * DOCX (DOCX has no reliable native page concept — see
 * backend/app/ingestion/docx_extraction.py). Every place that renders
 * `citation.page` should use citationLocationLabel() rather than
 * hardcoding "Page", so a DOCX-derived citation is never presented as if
 * it had a PDF page number it doesn't have.
 */

export function isDocxFilename(filename: string | null | undefined): boolean {
  return !!filename && filename.toLowerCase().endsWith('.docx')
}

/** Phase 8A (Email Thread Intelligence): an email message's body is stored
 * as an ordinary Document — this mirrors isDocxFilename() exactly, by the
 * same filename-extension convention, rather than adding a separate
 * "format" field. doc_type is also 'EMAIL' for these (see
 * backend/app/email_ingestion/pipeline.py), which SourceViewPage/
 * DocumentSourceViewPage check directly since they already have the full
 * DocumentSummary in hand; this filename-based helper exists for the rarer
 * case of deciding before that fetch resolves, matching the DOCX
 * convention's own shape. */
export function isEmailFilename(filename: string | null | undefined): boolean {
  return !!filename && filename.toLowerCase().endsWith('.eml')
}

/** "Page" or "Paragraph", depending on the citing document's own format. */
export function citationLocationLabel(filename: string | null | undefined): string {
  return isDocxFilename(filename) ? 'Paragraph' : 'Page'
}

/** Short form for inline use, e.g. "p.12" vs "¶12". */
export function citationLocationShort(filename: string | null | undefined, location: number): string {
  return isDocxFilename(filename) ? `¶${location}` : `p.${location}`
}

/**
 * Phase W2.3 (Multimodal Image Understanding): the one, shared label for a
 * Document's derivation_kind, reused everywhere a document's provenance is
 * shown (CitationList, EvidencePanel, Inspector, ProjectPage's document
 * register) instead of four separate copies of the same two strings.
 * Returns null for an ordinary document (derivation_kind is null/undefined)
 * — callers render nothing in that case, never a badge implying a document
 * is image-derived when it isn't.
 */
export function derivationBadgeLabel(derivationKind: string | null | undefined): string | null {
  if (derivationKind === 'ocr_transcription') return 'OCR'
  if (derivationKind === 'visual_description') return 'AI description'
  return null
}
