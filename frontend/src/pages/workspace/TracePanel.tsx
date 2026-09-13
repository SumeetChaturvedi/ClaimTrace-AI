import { SectionLabel, Muted } from '../../components/ui/Typography'
import styles from './panels.module.css'

export function TracePanel({ steps }: { steps: string[] }) {
  return (
    <div className={styles.panel}>
      <SectionLabel>Investigation Process</SectionLabel>
      <Muted>
        A high-level summary of the stages ClaimTrace worked through for this investigation. This
        is not a detailed record of every action taken.
      </Muted>
      {steps.length === 0 ? (
        <Muted>No process steps were returned for this investigation.</Muted>
      ) : (
        <ol className={styles.traceList}>
          {steps.map((step, i) => (
            <li key={i}>{step}</li>
          ))}
        </ol>
      )}
    </div>
  )
}
