import { useId } from 'react'

import type { FixAttempt } from '../api/types'
import {
  validationStatusLabel,
  validationStatusTone,
} from '../lib/presentation'
import { EmptyState } from './EmptyState'
import { StatusBadge } from './StatusBadge'

interface FixAttemptsSectionProps {
  fixAttempts: FixAttempt[]
}

export function FixAttemptsSection({
  fixAttempts,
}: FixAttemptsSectionProps) {
  const headingId = useId()

  return (
    <section
      aria-labelledby={headingId}
      className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
    >
      <h2
        id={headingId}
        className="text-lg font-semibold text-slate-900"
      >
        Fix attempts{' '}
        <span className="font-normal text-slate-400">
          ({fixAttempts.length})
        </span>
      </h2>

      {fixAttempts.length === 0 ? (
        <div className="mt-3">
          <EmptyState message="No fix attempts were made for this review." />
        </div>
      ) : (
        <ul className="mt-4 space-y-4">
          {fixAttempts.map((attempt) => (
            <li
              key={attempt.id}
              className="rounded-md border border-slate-200 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="break-all font-mono text-xs text-slate-500">
                  Finding {attempt.finding_id}
                </span>

                <span className="font-medium text-slate-700">
                  Attempt #{attempt.attempt_number}
                </span>
              </div>

              <pre className="mt-2 overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
                <code>{attempt.patch}</code>
              </pre>

              {attempt.validation_results.length === 0 ? (
                <div className="mt-3">
                  <EmptyState message="No validation results were recorded for this attempt." />
                </div>
              ) : (
                <ul className="mt-3 space-y-2">
                  {attempt.validation_results.map((result, index) => (
                    <li
                      key={`${result.tool}-${result.status}-${index}`}
                      className="flex flex-wrap items-center gap-2 text-sm"
                    >
                      <StatusBadge
                        label={validationStatusLabel(result.status)}
                        tone={validationStatusTone(result.status)}
                      />

                      <span className="font-medium text-slate-700">
                        {result.tool}
                      </span>

                      <span className="text-slate-500">
                        {result.message}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}