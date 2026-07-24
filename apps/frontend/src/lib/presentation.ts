/**
 * Presentation-only label/color mappings for backend enum values.
 *
 * These never change *which* bucket a status/severity belongs to (that is
 * always decided by the backend, see `docs/DECISIONS.md` ADR-015) — they
 * only pick a human-readable label and a visual tone for it.
 */

import type { EvidenceSeverity, EvidenceSource, ReviewStatus, ValidationStatus } from '../api/types'

export type BadgeTone = 'success' | 'danger' | 'warning' | 'info' | 'neutral'

const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  pending: 'Pending',
  running: 'Running',
  approved: 'Approved',
  blocked: 'Blocked',
  failed: 'Failed',
}

const REVIEW_STATUS_TONES: Record<ReviewStatus, BadgeTone> = {
  pending: 'neutral',
  running: 'info',
  approved: 'success',
  blocked: 'danger',
  failed: 'danger',
}

export function reviewStatusLabel(status: ReviewStatus): string {
  return REVIEW_STATUS_LABELS[status]
}

export function reviewStatusTone(status: ReviewStatus): BadgeTone {
  return REVIEW_STATUS_TONES[status]
}

const SEVERITY_LABELS: Record<EvidenceSeverity, string> = {
  blocking: 'Blocking',
  non_blocking: 'Non-blocking',
  info: 'Info',
}

const SEVERITY_TONES: Record<EvidenceSeverity, BadgeTone> = {
  blocking: 'danger',
  non_blocking: 'warning',
  info: 'info',
}

export function severityLabel(severity: EvidenceSeverity): string {
  return SEVERITY_LABELS[severity]
}

export function severityTone(severity: EvidenceSeverity): BadgeTone {
  return SEVERITY_TONES[severity]
}

const VALIDATION_STATUS_LABELS: Record<ValidationStatus, string> = {
  passed: 'Passed',
  failed: 'Failed',
  error: 'Error',
}

const VALIDATION_STATUS_TONES: Record<ValidationStatus, BadgeTone> = {
  passed: 'success',
  failed: 'danger',
  error: 'danger',
}

export function validationStatusLabel(status: ValidationStatus): string {
  return VALIDATION_STATUS_LABELS[status]
}

export function validationStatusTone(status: ValidationStatus): BadgeTone {
  return VALIDATION_STATUS_TONES[status]
}

const EVIDENCE_SOURCE_LABELS: Record<EvidenceSource, string> = {
  llm: 'LLM',
  ruff: 'Ruff',
  mypy: 'Mypy',
  pytest: 'Pytest',
  eslint: 'ESLint',
  tsc: 'tsc',
  vitest: 'Vitest',
}

export function evidenceSourceLabel(source: EvidenceSource): string {
  return EVIDENCE_SOURCE_LABELS[source]
}

/** Format an ISO timestamp for display, or an em dash when absent/invalid. */
export function formatDateTime(value: string | null): string {
  if (value === null) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}
