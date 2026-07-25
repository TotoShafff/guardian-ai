import { useId } from 'react'

import type { Evidence, EvidenceSource, Finding } from '../api/types'
import { evidenceSourceLabel, severityLabel, severityTone } from '../lib/presentation'
import { AlertIcon } from './icons'
import { EmptyState } from './EmptyState'
import { SectionHeader } from './SectionHeader'
import { StatusBadge } from './StatusBadge'

interface FindingsSectionProps {
  title: string
  findings: Finding[]
  /** The review's full evidence list, used only to look up which source(s) back each finding. */
  evidence: Evidence[]
  emptyMessage: string
}

/** The distinct evidence sources backing one finding, in first-seen order. */
function sourcesFor(finding: Finding, evidenceById: Map<string, Evidence>): EvidenceSource[] {
  const seen = new Set<EvidenceSource>()
  for (const evidenceId of finding.evidence_ids) {
    const source = evidenceById.get(evidenceId)?.source
    if (source !== undefined) {
      seen.add(source)
    }
  }
  return Array.from(seen)
}

function accentForSeverity(severity: Finding['severity']): string {
  if (severity === 'blocking') {
    return 'border-l-[var(--color-terminal-danger)]'
  }
  if (severity === 'non_blocking') {
    return 'border-l-[var(--color-terminal-warning)]'
  }
  return 'border-l-[var(--color-terminal-cyan)]'
}

/** Renders one findings group (blocking or non-blocking) exactly as returned by the API. */
export function FindingsSection({ title, findings, evidence, emptyMessage }: FindingsSectionProps) {
  const headingId = useId()
  const evidenceById = new Map(evidence.map((item) => [item.id, item]))

  return (
    <section
      aria-labelledby={headingId}
      className="rounded-xl border border-[var(--color-terminal-border)] bg-[var(--color-terminal-panel)] p-5 sm:p-6"
    >
      <SectionHeader
        id={headingId}
        title={title}
        count={findings.length}
        icon={<AlertIcon />}
      />

      {findings.length === 0 ? (
        <div className="mt-4">
          <EmptyState message={emptyMessage} />
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {findings.map((finding) => {
            const sources = sourcesFor(finding, evidenceById)
            return (
              <li
                key={finding.id}
                className={`rounded-lg border border-[var(--color-terminal-border)] border-l-4 bg-[var(--color-terminal-elevated)]/40 p-4 ${accentForSeverity(finding.severity)}`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-medium text-[var(--color-terminal-text)]">
                    {finding.title}
                  </h3>
                  <StatusBadge
                    label={severityLabel(finding.severity)}
                    tone={severityTone(finding.severity)}
                  />
                </div>
                <p className="mt-2 text-sm leading-relaxed text-[var(--color-terminal-muted)]">
                  {finding.description}
                </p>
                <p className="mt-3 font-mono text-xs text-[var(--color-terminal-faint)]">
                  {finding.is_fixable ? 'Corregible' : 'No corregible automáticamente'}
                  {sources.length > 0 &&
                    ` · Fuente: ${sources.map(evidenceSourceLabel).join(', ')}`}
                </p>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
