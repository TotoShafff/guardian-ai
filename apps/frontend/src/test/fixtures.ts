import type {
  Decision,
  Evidence,
  Finding,
  FixAttempt,
  ReviewResponse,
  ReviewSummary,
} from '../api/types'

export function makeEvidence(overrides: Partial<Evidence> = {}): Evidence {
  return {
    id: 'evidence-1',
    review_id: 'review-1',
    source: 'ruff',
    severity: 'blocking',
    category: 'F401',
    message: '`os` imported but unused', // API keeps original tool text
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
    title: 'Importación no utilizada',
    description: 'El módulo `os` fue importado, pero no se utiliza.',
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
    validation_results: [
      { status: 'passed', tool: 'ruff', message: 'No se encontraron problemas' },
    ],
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeDecision(overrides: Partial<Decision> = {}): Decision {
  return {
    status: 'approved',
    rationale: 'Revisión aprobada: 0 hallazgos bloqueantes y 0 no bloqueantes.',
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

export function makeReviewSummary(overrides: Partial<ReviewSummary> = {}): ReviewSummary {
  return {
    id: 'review-1',
    target_reference: 'demo/checkout-review',
    target_path: './examples/ecommerce',
    status: 'blocked',
    created_at: '2026-07-25T18:40:00Z',
    completed_at: '2026-07-25T18:41:00Z',
    blocking_findings_count: 2,
    non_blocking_findings_count: 1,
    ...overrides,
  }
}
