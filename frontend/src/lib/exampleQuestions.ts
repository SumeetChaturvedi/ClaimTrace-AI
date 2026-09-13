/**
 * Example investigation questions, per project, to give a new user a
 * one-click starting point. These are real questions from the approved
 * benchmark suite (dataset/scripts/benchmarks.py) — copied verbatim, not
 * paraphrased — so running one produces a real, meaningful investigation.
 * Clicking one creates a genuine persisted investigation via
 * api/client.ts's createInvestigation() (Phase 2: Persistent
 * Investigations), exactly like a freely-typed question — it is not a
 * canned or pre-recorded result.
 */

export interface ExampleQuestion {
  id: string
  question: string
}

export const EXAMPLE_QUESTIONS: Record<number, ExampleQuestion[]> = {
  2: [
    {
      id: 'CONCURRENT-DELAY-P4',
      question:
        'Was the Contractor entitled to the full extension of time claimed for the Pier P4 ground condition delay, or should the concurrent plant breakdown reduce that entitlement?',
    },
    {
      id: 'PIER-P2-DEFECT-LIABILITY',
      question:
        'Is the map cracking found at the Pier P2 pier cap during the Defects Notification Period attributable to the Contractor, and should the Contractor bear the cost of rectification?',
    },
  ],
  3: [
    {
      id: 'KFI2-TERMINATION-FINAL-ACCOUNT',
      question:
        "Was the Employer contractually entitled to terminate the Contract, and how should the Contractor's financial claim, liquidated damages, and retention be resolved in the Final Account?",
    },
  ],
}
