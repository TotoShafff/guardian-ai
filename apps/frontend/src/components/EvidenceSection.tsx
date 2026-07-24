import { useId } from 'react'

import type { Evidence } from '../api/types'
import { evidenceSourceLabel, severityLabel, severityTone } from '../lib/presentation'
import { EmptyState } from './EmptyState'
import { StatusBadge } from './StatusBadge'

interface EvidenceSectionProps {
  evidence: Evidence[]
}

function formatLocation(item: Evidence): string | null {
  if (item.file_path === null && item.line_start === null) {
    return null
  }

  const path = item.file_path ?? 'unknown file'
  if (item.line_start === null) {
    return path
  }

  const hasRange = item.line_end !== null && item.line_end !== item.line_start
  const lines = hasRange ? `${item.line_start}-${item.line_end}` : `${item.line_start}`
  return `${path}:${lines}`
}

export function EvidenceSection({ evidence }: EvidenceSectionProps) {
  const headingId = useId()

  return (
    <section aria-labelledby={headingId} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h2 id={headingId} className="text-lg font-semibold text-slate-900">
        Evidence <span className="font-normal text-slate-400">({evidence.length})</span>
      </h2>

      {evidence.length === 0 ? (
        <div className="mt-3">
          <EmptyState message="No evidence was collected for this review." />
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {evidence.map((item) => {
            const location = formatLocation(item)
            return (
              <li key={item.id} className="rounded-md border border-slate-200 p-4 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-slate-900">
                    {evidenceSourceLabel(item.source)} · {item.category}
                  </span>
                  <StatusBadge label={severityLabel(item.severity)} tone={severityTone(item.severity)} />
                </div>
                <p className="mt-1 text-slate-600">{item.message}</p>
                {location !== null && <p className="mt-1 font-mono text-xs text-slate-400">{location}</p>}
                {item.suggested_fix !== null && (
                  <p className="mt-2 text-xs text-slate-600">
                    <span className="font-medium">Suggested fix: </span>
                    {item.suggested_fix}
                  </p>
                )}
                {item.confidence !== null && (
                  <p className="mt-1 text-xs text-slate-400">Confidence: {Math.round(item.confidence * 100)}%</p>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
