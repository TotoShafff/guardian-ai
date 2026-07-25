import type { ReviewSummary } from '../api/types'
import { formatDateTime, reviewStatusLabel, reviewStatusTone } from '../lib/presentation'
import { EmptyState } from './EmptyState'
import { StatusBadge } from './StatusBadge'

interface ReviewHistoryProps {
  reviews: ReviewSummary[]
  isLoading: boolean
  error: string | null
  loadingReviewId: string | null
  onSelect: (reviewId: string) => void
  onRetry: () => void
}

export function ReviewHistory({
  reviews,
  isLoading,
  error,
  loadingReviewId,
  onSelect,
  onRetry,
}: ReviewHistoryProps) {
  return (
    <section
      aria-labelledby="review-history-heading"
      className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2
          id="review-history-heading"
          className="text-lg font-semibold text-slate-900"
        >
          Historial de revisiones
        </h2>

        {error !== null && (
          <button
            type="button"
            onClick={onRetry}
            className="text-sm font-medium text-indigo-600 hover:text-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            Reintentar
          </button>
        )}
      </div>

      {isLoading ? (
        <p className="mt-3 text-sm text-slate-500">Cargando historial...</p>
      ) : error !== null ? (
        <div className="mt-3">
          <EmptyState message={error} />
        </div>
      ) : reviews.length === 0 ? (
        <div className="mt-3">
          <EmptyState message="Todavía no hay revisiones guardadas." />
        </div>
      ) : (
        <ul className="mt-4 divide-y divide-slate-100">
          {reviews.map((review) => {
            const isOpening = loadingReviewId === review.id

            return (
              <li key={review.id} className="flex flex-wrap items-start justify-between gap-3 py-4 first:pt-0 last:pb-0">
                <div className="min-w-0 space-y-1">
                  <p className="truncate font-medium text-slate-900">
                    {review.target_reference}
                  </p>
                  <p className="truncate font-mono text-xs text-slate-500">
                    {review.target_path}
                  </p>
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <StatusBadge
                      label={reviewStatusLabel(review.status)}
                      tone={reviewStatusTone(review.status)}
                    />
                    <span className="text-xs text-slate-500">
                      {review.blocking_findings_count} bloqueantes ·{' '}
                      {review.non_blocking_findings_count} no bloqueantes
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    {formatDateTime(review.created_at)}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => onSelect(review.id)}
                  disabled={loadingReviewId !== null}
                  className="shrink-0 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isOpening ? 'Cargando revisión...' : 'Ver revisión'}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
