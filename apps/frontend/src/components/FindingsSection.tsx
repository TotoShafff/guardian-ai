import { useId } from 'react'

import type { Evidence, EvidenceSource, Finding } from '../api/types'
import { evidenceSourceLabel, severityLabel, severityTone } from '../lib/presentation'
import { EmptyState } from './EmptyState'
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

/** Renders one findings group (blocking or non-blocking) exactly as returned by the API. */
export function FindingsSection({ title, findings, evidence, emptyMessage }: FindingsSectionProps) {
  const headingId = useId()
  const evidenceById = new Map(evidence.map((item) => [item.id, item]))

  return (
    <section aria-labelledby={headingId} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h2 id={headingId} className="text-lg font-semibold text-slate-900">
        {title} <span className="font-normal text-slate-400">({findings.length})</span>
      </h2>

      {findings.length === 0 ? (
        <div className="mt-3">
          <EmptyState message={emptyMessage} />
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {findings.map((finding) => {
            const sources = sourcesFor(finding, evidenceById)
            return (
              <li key={finding.id} className="rounded-md border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-medium text-slate-900">{finding.title}</h3>
                  <StatusBadge label={severityLabel(finding.severity)} tone={severityTone(finding.severity)} />
                </div>
                <p className="mt-1 text-sm text-slate-600">{finding.description}</p>
                <p className="mt-2 text-xs text-slate-400">
                  {finding.is_fixable ? 'Fixable' : 'Not automatically fixable'}
                  {sources.length > 0 && ` · Source: ${sources.map(evidenceSourceLabel).join(', ')}`}
                </p>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
