import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// @testing-library/react only auto-registers its afterEach cleanup when it
// detects Jest; under Vitest this must be done explicitly, otherwise each
// test's rendered DOM leaks into the next one within the same file.
afterEach(() => cleanup())
