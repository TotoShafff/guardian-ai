import type { Finding, ReviewResponse } from '../api/types'
import { DecisionSummary } from './DecisionSummary'
import { EvidenceSection } from './EvidenceSection'
import { FindingsSection } from './FindingsSection'
import { FixAttemptsSection } from './FixAttemptsSection'

interface ReviewResultProps {
  review: ReviewResponse
}

/** Collect findings from the top-level list and the decision buckets. */
function allFindings(review: ReviewResponse): Finding[] {
  const byId = new Map<string, Finding>()

  for (const finding of review.findings) {
    byId.set(finding.id, finding)
  }
  for (const finding of review.decision?.blocking_findings ?? []) {
    byId.set(finding.id, finding)
  }
  for (const finding of review.decision?.non_blocking_findings ?? []) {
    byId.set(finding.id, finding)
  }

  return [...byId.values()]
}

export function ReviewResult({ review }: ReviewResultProps) {
  return (
    <div className="space-y-6">
      <DecisionSummary review={review} />
      <FindingsSection
        title="Hallazgos bloqueantes"
        findings={review.decision?.blocking_findings ?? []}
        evidence={review.evidence}
        emptyMessage="No se reportaron hallazgos bloqueantes."
      />
      <FindingsSection
        title="Hallazgos no bloqueantes"
        findings={review.decision?.non_blocking_findings ?? []}
        evidence={review.evidence}
        emptyMessage="No se reportaron hallazgos no bloqueantes."
      />
      <EvidenceSection evidence={review.evidence} />
      <FixAttemptsSection
        fixAttempts={review.fix_attempts}
        findings={allFindings(review)}
      />
    </div>
  )
}
