import { useId } from 'react'

import type { Evidence } from '../api/types'
import {
  evidenceSourceLabel,
  severityLabel,
  severityTone,
  translateEvidenceMessage,
} from '../lib/presentation'
import { EmptyState } from './EmptyState'
import { InfoIcon } from './icons'
import { SectionHeader } from './SectionHeader'
import { StatusBadge } from './StatusBadge'

interface EvidenceSectionProps {
  evidence: Evidence[]
}

function formatLocation(item: Evidence): string | null {
  if (item.file_path === null && item.line_start === null) {
    return null
  }

  const path = item.file_path ?? 'archivo desconocido'
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
    <section
      aria-labelledby={headingId}
      className="rounded-xl border border-[var(--color-terminal-border)] bg-[var(--color-terminal-panel)] p-5 sm:p-6"
    >
      <SectionHeader
        id={headingId}
        title="Evidencia"
        count={evidence.length}
        icon={<InfoIcon />}
      />

      {evidence.length === 0 ? (
        <div className="mt-4">
          <EmptyState message="No se recopiló evidencia para esta revisión." />
        </div>
      ) : (
        <ul className="mt-4 space-y-3">
          {evidence.map((item) => {
            const location = formatLocation(item)
            return (
              <li
                key={item.id}
                className="overflow-hidden rounded-lg border border-[var(--color-terminal-border)] bg-[#080d14]"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-terminal-border)] bg-[var(--color-terminal-elevated)]/60 px-3 py-2">
                  <span className="font-mono text-xs tracking-wide text-[var(--color-terminal-cyan)]">
                    {evidenceSourceLabel(item.source)}
                    <span className="text-[var(--color-terminal-faint)]"> · </span>
                    <span className="text-[var(--color-terminal-accent)]">{item.category}</span>
                  </span>
                  <StatusBadge
                    label={severityLabel(item.severity)}
                    tone={severityTone(item.severity)}
                  />
                </div>
                <div className="space-y-2 px-3 py-3 text-sm">
                  <p className="text-[var(--color-terminal-text)]">
                    {translateEvidenceMessage(item.message)}
                  </p>
                  {location !== null && (
                    <p className="font-mono text-xs text-[var(--color-terminal-muted)]">
                      {location}
                    </p>
                  )}
                  {item.suggested_fix !== null && (
                    <p className="text-xs text-[var(--color-terminal-muted)]">
                      <span className="font-medium text-[var(--color-terminal-faint)]">
                        Corrección sugerida:{' '}
                      </span>
                      {item.suggested_fix}
                    </p>
                  )}
                  {item.confidence !== null && (
                    <p className="font-mono text-xs text-[var(--color-terminal-faint)]">
                      Confianza: {Math.round(item.confidence * 100)}%
                    </p>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
