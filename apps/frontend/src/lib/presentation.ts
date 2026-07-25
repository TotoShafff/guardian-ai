/**
 * Presentation-only label/color mappings for backend enum values and known
 * human-readable messages.
 *
 * These never change *which* bucket a status/severity belongs to (that is
 * always decided by the backend, see `docs/DECISIONS.md` ADR-015) — they
 * only pick a Spanish label and a visual tone for display.
 */

import type {
  EvidenceSeverity,
  EvidenceSource,
  Finding,
  ReviewStatus,
  ValidationStatus,
} from '../api/types'

export type BadgeTone =
  | 'success'
  | 'danger'
  | 'warning'
  | 'info'
  | 'neutral'
  | 'pending'

const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  pending: 'Pendiente',
  running: 'En ejecución',
  approved: 'Aprobado',
  blocked: 'Bloqueado',
  failed: 'Fallido',
}

const REVIEW_STATUS_TONES: Record<ReviewStatus, BadgeTone> = {
  pending: 'pending',
  running: 'pending',
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
  blocking: 'Bloqueante',
  non_blocking: 'No bloqueante',
  info: 'Informativo',
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
  passed: 'Aprobado',
  failed: 'Fallido',
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

/**
 * Known English evidence/tool messages translated for display only.
 * Unknown messages are returned unchanged.
 */
const EVIDENCE_MESSAGE_TRANSLATIONS: Record<string, string> = {
  '`os` imported but unused': 'El módulo `os` fue importado, pero no se utiliza.',
  'Failed: DID NOT RAISE ValueError':
    'La prueba esperaba que se lanzara ValueError, pero la excepción no ocurrió.',
  'The file is executable but no shebang is present':
    'El archivo figura como ejecutable, pero no contiene una línea shebang.',
}

export function translateEvidenceMessage(message: string): string {
  return EVIDENCE_MESSAGE_TRANSLATIONS[message] ?? message
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
  return date.toLocaleString('es-AR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

const SHORT_DATE_TIME = new Intl.DateTimeFormat('es-AR', {
  dateStyle: 'short',
  timeStyle: 'short',
})

/** Compact es-AR date/time for history tables. */
export function formatDateTimeShort(value: string | null): string {
  if (value === null) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return SHORT_DATE_TIME.format(date)
}

/**
 * One-sentence Spanish explanation of what a proposed patch addresses,
 * derived from the related finding (no diff parsing, no new API fields).
 */
export function proposalFixExplanation(finding: Finding | undefined): string {
  if (finding === undefined) {
    return 'Propone un cambio local para el hallazgo asociado.'
  }

  const description = finding.description.trim()
  if (description !== '') {
    return description
  }

  const title = finding.title.trim()
  if (title !== '') {
    return `Corrige: ${title}.`
  }

  return 'Propone un cambio local para el hallazgo asociado.'
}
