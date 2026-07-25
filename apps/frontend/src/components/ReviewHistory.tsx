import type { ReviewSummary } from '../api/types'
import {
  formatDateTimeShort,
  reviewStatusLabel,
  reviewStatusTone,
} from '../lib/presentation'
import { EmptyState } from './EmptyState'
import { HistoryIcon } from './icons'
import { LoadingState } from './LoadingState'
import { SectionHeader } from './SectionHeader'
import { StatusBadge } from './StatusBadge'

interface ReviewHistoryProps {
  reviews: ReviewSummary[]
  isLoading: boolean
  error: string | null
  loadingReviewId: string | null
  onSelect: (reviewId: string) => void
  onRetry: () => void
}

const actionButtonClass =
  'focus-ring rounded-md border border-[var(--color-terminal-border-strong)] bg-[var(--color-terminal-elevated)] px-3 py-1.5 font-mono text-xs font-medium tracking-wide text-[var(--color-terminal-cyan)] uppercase transition hover:border-[var(--color-terminal-cyan)] hover:bg-[color-mix(in_srgb,var(--color-terminal-cyan)_10%,var(--color-terminal-elevated))] disabled:cursor-not-allowed disabled:opacity-50'

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
      className="rounded-xl border border-[var(--color-terminal-border)] bg-[var(--color-terminal-panel)] p-5 sm:p-6"
    >
      <SectionHeader
        id="review-history-heading"
        title="Historial de revisiones"
        icon={<HistoryIcon />}
        description="Consultá revisiones persistidas y recuperá su evidencia sin ejecutar nuevamente el análisis."
        action={
          error !== null ? (
            <button
              type="button"
              onClick={onRetry}
              className="focus-ring text-sm font-medium text-[var(--color-terminal-cyan)] hover:text-[var(--color-terminal-accent)]"
            >
              Reintentar
            </button>
          ) : undefined
        }
      />

      {isLoading ? (
        <div className="mt-4">
          <LoadingState message="Cargando historial..." />
        </div>
      ) : error !== null ? (
        <div className="mt-4">
          <EmptyState message={error} />
        </div>
      ) : reviews.length === 0 ? (
        <div className="mt-4">
          <EmptyState message="Todavía no hay revisiones guardadas." />
        </div>
      ) : (
        <>
          <div className="mt-4 hidden overflow-hidden rounded-lg border border-[var(--color-terminal-border)] md:block">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--color-terminal-border)] bg-[var(--color-terminal-elevated)] font-mono text-[10px] tracking-[0.12em] text-[var(--color-terminal-faint)] uppercase">
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Fecha
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Referencia
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Ruta
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Estado
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Bloqueantes
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    No bloqueantes
                  </th>
                  <th scope="col" className="px-3 py-2.5 font-medium">
                    Acción
                  </th>
                </tr>
              </thead>
              <tbody>
                {reviews.map((review, index) => {
                  const isOpening = loadingReviewId === review.id
                  const rowBg =
                    index % 2 === 0
                      ? 'bg-[var(--color-terminal-bg)]/30'
                      : 'bg-transparent'

                  return (
                    <tr
                      key={review.id}
                      className={`border-b border-[var(--color-terminal-border)]/70 last:border-0 transition hover:bg-[color-mix(in_srgb,var(--color-terminal-cyan)_6%,transparent)] ${rowBg}`}
                    >
                      <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-[var(--color-terminal-muted)]">
                        {formatDateTimeShort(review.created_at)}
                      </td>
                      <td className="max-w-[12rem] truncate px-3 py-3 font-mono text-sm text-[var(--color-terminal-text)]">
                        {review.target_reference}
                      </td>
                      <td className="max-w-[12rem] truncate px-3 py-3 font-mono text-xs text-[var(--color-terminal-faint)]">
                        {review.target_path}
                      </td>
                      <td className="px-3 py-3">
                        <StatusBadge
                          label={reviewStatusLabel(review.status)}
                          tone={reviewStatusTone(review.status)}
                        />
                      </td>
                      <td className="px-3 py-3 font-mono text-[var(--color-terminal-text)]">
                        {review.blocking_findings_count}
                      </td>
                      <td className="px-3 py-3 font-mono text-[var(--color-terminal-text)]">
                        {review.non_blocking_findings_count}
                      </td>
                      <td className="px-3 py-3">
                        <button
                          type="button"
                          onClick={() => onSelect(review.id)}
                          disabled={loadingReviewId !== null}
                          className={actionButtonClass}
                        >
                          {isOpening ? 'Cargando revisión...' : 'Ver revisión'}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <ul className="mt-4 space-y-3 md:hidden">
            {reviews.map((review) => {
              const isOpening = loadingReviewId === review.id

              return (
                <li
                  key={review.id}
                  className="rounded-lg border border-[var(--color-terminal-border)] bg-[var(--color-terminal-elevated)]/40 p-4"
                >
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-mono text-sm text-[var(--color-terminal-text)]">
                        {review.target_reference}
                      </p>
                      <StatusBadge
                        label={reviewStatusLabel(review.status)}
                        tone={reviewStatusTone(review.status)}
                      />
                    </div>
                    <p className="break-all font-mono text-xs text-[var(--color-terminal-faint)]">
                      {review.target_path}
                    </p>
                    <p className="font-mono text-xs text-[var(--color-terminal-muted)]">
                      {formatDateTimeShort(review.created_at)}
                    </p>
                    <p className="font-mono text-xs text-[var(--color-terminal-muted)]">
                      Bloqueantes: {review.blocking_findings_count} · No
                      bloqueantes: {review.non_blocking_findings_count}
                    </p>
                    <button
                      type="button"
                      onClick={() => onSelect(review.id)}
                      disabled={loadingReviewId !== null}
                      className={`${actionButtonClass} mt-1 w-full py-2`}
                    >
                      {isOpening ? 'Cargando revisión...' : 'Ver revisión'}
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        </>
      )}
    </section>
  )
}
