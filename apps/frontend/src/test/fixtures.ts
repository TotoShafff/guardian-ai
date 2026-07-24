import type { Decision, Evidence, Finding, FixAttempt, ReviewResponse } from '../api/types'

export function makeEvidence(overrides: Partial<Evidence> = {}): Evidence {
  return {
    id: 'evidence-1',
    review_id: 'review-1',
    source: 'ruff',
    severity: 'blocking',
    category: 'F401',
    message: '`os` imported but unused',
    file_path: 'app/example.py',
    line_start: 1,
    line_end: null,
    suggested_fix: null,
    confidence: null,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeFinding(overrides: Partial<Finding> = {}): Finding {
  return {
    id: 'finding-1',
    review_id: 'review-1',
    evidence_ids: ['evidence-1'],
    severity: 'blocking',
    title: 'Unused import',
    description: '`os` is imported but never used',
    is_fixable: true,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeFixAttempt(overrides: Partial<FixAttempt> = {}): FixAttempt {
  return {
    id: 'fix-attempt-1',
    finding_id: 'finding-1',
    patch: '--- a/app/example.py\n+++ b/app/example.py\n@@ -1 +1 @@\n-import os\n',
    attempt_number: 1,
    validation_results: [{ status: 'passed', tool: 'ruff', message: 'No issues found' }],
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeDecision(overrides: Partial<Decision> = {}): Decision {
  return {
    status: 'approved',
    rationale: 'No blocking findings were reported.',
    blocking_findings: [],
    non_blocking_findings: [],
    fix_attempts: [],
    ...overrides,
  }
}

export function makeReviewResponse(overrides: Partial<ReviewResponse> = {}): ReviewResponse {
  return {
    id: 'review-1',
    target_reference: 'demo/checkout-review',
    status: 'approved',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:05:00Z',
    evidence: [],
    findings: [],
    fix_attempts: [],
    decision: makeDecision(),
    error: null,
    ...overrides,
  }
}
