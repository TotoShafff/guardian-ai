import { useId } from 'react'

import type { Finding, FixAttempt } from '../api/types'
import { proposalFixExplanation } from '../lib/presentation'
import { EmptyState } from './EmptyState'

interface FixAttemptsSectionProps {
  fixAttempts: FixAttempt[]
  findings: Finding[]
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
      className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
    >
      <h2
        id={headingId}
        className="text-lg font-semibold text-slate-900"
      >
        Propuestas de corrección{' '}
        <span className="font-normal text-slate-400">
          ({fixAttempts.length})
        </span>
      </h2>

      {fixAttempts.length === 0 ? (
        <div className="mt-3">
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
                className="rounded-md border border-slate-200 p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-2 text-sm">
                  <div className="min-w-0 space-y-1">
                    <p className="font-medium text-slate-900">
                      Propuesta para: {proposalFor}
                    </p>
                    {finding !== undefined && (
                      <p className="break-all font-mono text-xs text-slate-400">
                        Hallazgo {attempt.finding_id}
                      </p>
                    )}
                  </div>

                  <span className="shrink-0 font-medium text-slate-700">
                    Propuesta #{attempt.attempt_number}
                  </span>
                </div>

                <div className="mt-3 text-sm text-slate-700">
                  <p className="font-medium text-slate-500">Qué corrige:</p>
                  <p className="mt-1">{proposalFixExplanation(finding)}</p>
                </div>

                <pre className="mt-3 overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
                  <code>{attempt.patch}</code>
                </pre>

                <p className="mt-3 text-xs text-slate-500">
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
