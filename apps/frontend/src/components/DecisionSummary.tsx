import { useId } from 'react'

import type { ReviewResponse } from '../api/types'
import {
  formatDateTime,
  reviewStatusLabel,
  reviewStatusTone,
} from '../lib/presentation'
import { EmptyState } from './EmptyState'
import { StatusBadge } from './StatusBadge'

interface DecisionSummaryProps {
  review: ReviewResponse
}

export function DecisionSummary({ review }: DecisionSummaryProps) {
  const headingId = useId()
  const { decision } = review
  const displayedStatus = decision?.status ?? review.status

  return (
    <section
      aria-labelledby={headingId}
      className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2
          id={headingId}
          className="text-lg font-semibold text-slate-900"
        >
          Resumen de la decisión
        </h2>

        <StatusBadge
          label={reviewStatusLabel(displayedStatus)}
          tone={reviewStatusTone(displayedStatus)}
        />
      </div>

      <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-medium text-slate-500">Referencia de la revisión</dt>
          <dd className="mt-0.5 text-slate-900">
            {review.target_reference}
          </dd>
        </div>

        <div>
          <dt className="font-medium text-slate-500">ID de revisión</dt>
          <dd className="mt-0.5 break-all font-mono text-xs text-slate-900">
            {review.id}
          </dd>
        </div>

        <div>
          <dt className="font-medium text-slate-500">Creada el</dt>
          <dd className="mt-0.5 text-slate-900">
            {formatDateTime(review.created_at)}
          </dd>
        </div>

        <div>
          <dt className="font-medium text-slate-500">Finalizada el</dt>
          <dd className="mt-0.5 text-slate-900">
            {formatDateTime(review.updated_at)}
          </dd>
        </div>
      </dl>

      <div className="mt-4">
        <h3 className="text-sm font-medium text-slate-500">Fundamento</h3>

        {decision !== null ? (
          <p className="mt-1 text-sm text-slate-900">
            {decision.rationale}
          </p>
        ) : (
          <div className="mt-1">
            <EmptyState message="Todavía no se registró una decisión para esta revisión." />
          </div>
        )}
      </div>

      {review.error !== null && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3"
        >
          <h3 className="text-sm font-medium text-red-800">
            Error de la revisión
          </h3>
          <p className="mt-1 text-sm text-red-700">
            {review.error}
          </p>
        </div>
      )}
    </section>
  )
}
