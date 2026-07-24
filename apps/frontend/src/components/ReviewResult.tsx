import type { ReviewResponse } from '../api/types'
import { DecisionSummary } from './DecisionSummary'
import { EvidenceSection } from './EvidenceSection'
import { FindingsSection } from './FindingsSection'
import { FixAttemptsSection } from './FixAttemptsSection'

interface ReviewResultProps {
  review: ReviewResponse
}

export function ReviewResult({ review }: ReviewResultProps) {
  return (
    <div className="space-y-6">
      <DecisionSummary review={review} />
      <FindingsSection
        title="Blocking findings"
        findings={review.decision?.blocking_findings ?? []}
        evidence={review.evidence}
        emptyMessage="No blocking findings were reported."
      />
      <FindingsSection
        title="Non-blocking findings"
        findings={review.decision?.non_blocking_findings ?? []}
        evidence={review.evidence}
        emptyMessage="No non-blocking findings were reported."
      />
      <EvidenceSection evidence={review.evidence} />
      <FixAttemptsSection fixAttempts={review.fix_attempts} />
    </div>
  )
}
