import { describe, expect, it } from 'vitest'
import { derivationBadgeLabel } from './documentFormat'

describe('derivationBadgeLabel', () => {
  it('labels an OCR-transcription document "OCR"', () => {
    expect(derivationBadgeLabel('ocr_transcription')).toBe('OCR')
  })

  it('labels a visual-description document "AI description"', () => {
    expect(derivationBadgeLabel('visual_description')).toBe('AI description')
  })

  it('returns null for an ordinary document (derivation_kind null)', () => {
    expect(derivationBadgeLabel(null)).toBeNull()
  })

  it('returns null when derivation_kind is not provided at all', () => {
    expect(derivationBadgeLabel(undefined)).toBeNull()
  })

  it('returns null for an unrecognized value rather than guessing a label', () => {
    expect(derivationBadgeLabel('some_future_kind')).toBeNull()
  })
})
