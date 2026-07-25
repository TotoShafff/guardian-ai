/**
 * Types mirroring the backend's `ReviewResponse` and its nested schemas
 * (see `apps/backend/app/api/schemas.py`) field for field. Values coming
 * from the API must be rendered verbatim — never recomputed here (see
 * `docs/DECISIONS.md` ADR-015).
 */

export type ReviewStatus = 'pending' | 'running' | 'approved' | 'blocked' | 'failed'

export type EvidenceSource = 'llm' | 'ruff' | 'mypy' | 'pytest' | 'eslint' | 'tsc' | 'vitest'

export type EvidenceSeverity = 'blocking' | 'non_blocking' | 'info'

export type ValidationStatus = 'passed' | 'failed' | 'error'

export interface Evidence {
  id: string
  review_id: string
  source: EvidenceSource
  severity: EvidenceSeverity
  category: string
  message: string
  file_path: string | null
  line_start: number | null
  line_end: number | null
  suggested_fix: string | null
  confidence: number | null
  created_at: string
}

export interface Finding {
  id: string
  review_id: string
  evidence_ids: string[]
  severity: EvidenceSeverity
  title: string
  description: string
  is_fixable: boolean
  created_at: string
}

export interface ValidationResult {
  status: ValidationStatus
  tool: string
  message: string
}

export interface FixAttempt {
  id: string
  finding_id: string
  patch: string
  attempt_number: number
  validation_results: ValidationResult[]
  created_at: string
}

export interface Decision {
  status: ReviewStatus
  rationale: string
  blocking_findings: Finding[]
  non_blocking_findings: Finding[]
  fix_attempts: FixAttempt[]
}

/** Mirrors `ReviewResponse` returned by both `POST /reviews` and `GET /reviews/{id}`. */
export interface ReviewResponse {
  id: string
  target_reference: string
  status: ReviewStatus
  created_at: string
  updated_at: string | null
  evidence: Evidence[]
  findings: Finding[]
  fix_attempts: FixAttempt[]
  decision: Decision | null
  error: string | null
}

/** Mirrors `ReviewCreateRequest`, the body accepted by `POST /reviews`. */
export interface ReviewCreateRequest {
  target_reference: string
  target_path: string
  code: string
}

/** Mirrors `ReviewSummaryResponse` from `GET /reviews`. */
export interface ReviewSummary {
  id: string
  target_reference: string
  target_path: string
  status: ReviewStatus
  created_at: string
  completed_at: string | null
  blocking_findings_count: number
  non_blocking_findings_count: number
}

/** Mirrors `ReviewHistoryResponse` from `GET /reviews`. */
export interface ReviewHistoryResponse {
  reviews: ReviewSummary[]
}
