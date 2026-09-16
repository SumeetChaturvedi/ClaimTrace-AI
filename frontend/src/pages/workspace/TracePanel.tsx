import { SectionLabel, Muted } from '../../components/ui/Typography'
import styles from './panels.module.css'

/**
 * Investigation traceability (Phase 8A: visual refinement) — the exact
 * same real `reasoning_steps` the backend already returns, presented as a
 * connected vertical flow rather than a plain numbered list, so it reads
 * as "how this investigation actually proceeded" rather than an
 * implementation changelog. No new stage is added and none is renamed:
 * this only changes how the existing, real strings are laid out.
 */
export function TracePanel({ steps }: { steps: string[] }) {
  return (
    <div className={styles.panel}>
      <SectionLabel>Investigation Traceability</SectionLabel>
      <Muted>
        A high-level summary of the stages ClaimTrace worked through for this investigation. This
        is not a detailed record of every action taken.
      </Muted>
      {steps.length === 0 ? (
        <Muted>No process steps were returned for this investigation.</Muted>
      ) : (
        <ol className={styles.traceFlow}>
          {steps.map((step, i) => (
            <li key={i} className={styles.traceStep}>
              <span className={styles.traceMarker}>{String(i + 1).padStart(2, '0')}</span>
              <span className={styles.traceText}>{step}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
