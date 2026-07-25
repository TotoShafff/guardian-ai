import { useId } from 'react'

import type { Finding, FixAttempt } from '../api/types'
import { proposalFixExplanation } from '../lib/presentation'
import { CodeIcon } from './icons'
import { EmptyState } from './EmptyState'
import { SectionHeader } from './SectionHeader'

interface FixAttemptsSectionProps {
  fixAttempts: FixAttempt[]
  findings: Finding[]
}

function DiffBlock({ patch }: { patch: string }) {
  const lines = patch.split('\n')

  return (
    <pre className="mt-3 overflow-x-auto rounded-md border border-[var(--color-terminal-border)] bg-[#05080d] p-0 text-xs leading-relaxed text-[var(--color-terminal-text)]">
      <code className="block min-w-full font-mono">
        {lines.map((line, index) => {
          let rowClass = 'block whitespace-pre px-3 py-0.5 text-[var(--color-terminal-muted)]'
          if (line.startsWith('+') && !line.startsWith('+++')) {
            rowClass =
              'block whitespace-pre px-3 py-0.5 bg-[color-mix(in_srgb,var(--color-terminal-accent)_12%,transparent)] text-[var(--color-terminal-accent)]'
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            rowClass =
              'block whitespace-pre px-3 py-0.5 bg-[color-mix(in_srgb,var(--color-terminal-danger)_12%,transparent)] text-[var(--color-terminal-danger)]'
          } else if (line.startsWith('@@')) {
            rowClass =
              'block whitespace-pre px-3 py-0.5 text-[var(--color-terminal-cyan)]'
          }

          return (
            <span key={`${index}-${line.slice(0, 24)}`} className={rowClass}>
              {line.length === 0 ? ' ' : line}
            </span>
          )
        })}
      </code>
    </pre>
  )
}

export function FixAttemptsSection({
  fixAttempts,
  findings,
}: FixAttemptsSectionProps) {
  const headingId = useId()
  const findingsById = new Map(findings.map((finding) => [finding.id, finding]))

  return (
    <section
      aria-labelledby={headingId}
      className="rounded-xl border border-[var(--color-terminal-border)] bg-[var(--color-terminal-panel)] p-5 sm:p-6"
    >
      <SectionHeader
        id={headingId}
        title="Propuestas de corrección"
        count={fixAttempts.length}
        icon={<CodeIcon />}
      />

      {fixAttempts.length === 0 ? (
        <div className="mt-4">
          <EmptyState message="No se generaron propuestas de corrección para esta revisión." />
        </div>
      ) : (
        <ul className="mt-4 space-y-4">
          {fixAttempts.map((attempt) => {
            const finding = findingsById.get(attempt.finding_id)
            const proposalFor = finding?.title.trim() || 'hallazgo relacionado'

            return (
              <li
                key={attempt.id}
                className="rounded-lg border border-[var(--color-terminal-border)] bg-[var(--color-terminal-elevated)]/35 p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-2 text-sm">
                  <div className="min-w-0 space-y-1">
                    <p className="font-medium text-[var(--color-terminal-text)]">
                      Propuesta para: {proposalFor}
                    </p>
                    {finding !== undefined && (
                      <p className="break-all font-mono text-xs text-[var(--color-terminal-faint)]">
                        Hallazgo {attempt.finding_id}
                      </p>
                    )}
                  </div>

                  <span className="shrink-0 rounded border border-[var(--color-terminal-border)] bg-[var(--color-terminal-bg)] px-2 py-0.5 font-mono text-xs text-[var(--color-terminal-cyan)]">
                    Propuesta #{attempt.attempt_number}
                  </span>
                </div>

                <div className="mt-3 text-sm text-[var(--color-terminal-text)]">
                  <p className="font-mono text-[10px] tracking-[0.14em] text-[var(--color-terminal-faint)] uppercase">
                    Qué corrige:
                  </p>
                  <p className="mt-1 text-[var(--color-terminal-muted)]">
                    {proposalFixExplanation(finding)}
                  </p>
                </div>

                <DiffBlock patch={attempt.patch} />

                <p className="mt-3 font-mono text-xs text-[var(--color-terminal-faint)]">
                  Propuesta generada por IA. Requiere revisión del desarrollador.
                </p>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
