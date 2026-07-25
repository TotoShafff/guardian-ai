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

function MetricCard({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string | number
  mono?: boolean
}) {
  return (
    <div className="rounded-lg border border-[var(--color-terminal-border)] bg-[var(--color-terminal-elevated)]/70 px-3 py-3">
      <dt className="font-mono text-[10px] tracking-[0.14em] text-[var(--color-terminal-faint)] uppercase">
        {label}
      </dt>
      <dd
        className={`mt-1.5 text-lg font-semibold text-[var(--color-terminal-text)] ${mono ? 'break-all font-mono text-sm' : ''}`}
      >
        {value}
      </dd>
    </div>
  )
}

export function DecisionSummary({ review }: DecisionSummaryProps) {
  const headingId = useId()
  const { decision } = review
  const displayedStatus = decision?.status ?? review.status
  const tone = reviewStatusTone(displayedStatus)
  const blockingCount = decision?.blocking_findings.length ?? 0
  const nonBlockingCount = decision?.non_blocking_findings.length ?? 0

  const panelTone =
    tone === 'success'
      ? 'border-[color-mix(in_srgb,var(--color-terminal-accent)_35%,var(--color-terminal-border))] bg-[color-mix(in_srgb,var(--color-terminal-accent)_6%,var(--color-terminal-panel))]'
      : tone === 'danger'
        ? 'border-[color-mix(in_srgb,var(--color-terminal-danger)_40%,var(--color-terminal-border))] bg-[color-mix(in_srgb,var(--color-terminal-danger)_7%,var(--color-terminal-panel))]'
        : 'border-[var(--color-terminal-border)] bg-[var(--color-terminal-panel)]'

  return (
    <section
      aria-labelledby={headingId}
      className={`rounded-xl border p-5 shadow-[0_0_0_1px_rgba(62,207,255,0.03)] sm:p-6 ${panelTone}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2
          id={headingId}
          className="text-base font-semibold tracking-wide text-[var(--color-terminal-text)]"
        >
          Resumen de la decisión
        </h2>

        <StatusBadge
          label={reviewStatusLabel(displayedStatus)}
          tone={tone}
        />
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Estado" value={reviewStatusLabel(displayedStatus)} />
        <MetricCard label="Bloqueantes" value={blockingCount} />
        <MetricCard label="No bloqueantes" value={nonBlockingCount} />
        <MetricCard
          label="Creada el"
          value={formatDateTime(review.created_at)}
          mono
        />
      </dl>

      <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-[var(--color-terminal-border)] bg-[var(--color-terminal-bg)]/50 px-3 py-3">
          <dt className="font-mono text-[10px] tracking-[0.14em] text-[var(--color-terminal-faint)] uppercase">
            Referencia de la revisión
          </dt>
          <dd className="mt-1 font-mono text-sm text-[var(--color-terminal-text)]">
            {review.target_reference}
          </dd>
        </div>
        <div className="rounded-lg border border-[var(--color-terminal-border)] bg-[var(--color-terminal-bg)]/50 px-3 py-3">
          <dt className="font-mono text-[10px] tracking-[0.14em] text-[var(--color-terminal-faint)] uppercase">
            ID de revisión
          </dt>
          <dd className="mt-1 break-all font-mono text-xs text-[var(--color-terminal-muted)]">
            {review.id}
          </dd>
        </div>
        <div className="rounded-lg border border-[var(--color-terminal-border)] bg-[var(--color-terminal-bg)]/50 px-3 py-3 sm:col-span-2">
          <dt className="font-mono text-[10px] tracking-[0.14em] text-[var(--color-terminal-faint)] uppercase">
            Finalizada el
          </dt>
          <dd className="mt-1 font-mono text-sm text-[var(--color-terminal-text)]">
            {formatDateTime(review.updated_at)}
          </dd>
        </div>
      </dl>

      <div className="mt-5">
        <h3 className="font-mono text-[10px] tracking-[0.14em] text-[var(--color-terminal-faint)] uppercase">
          Fundamento
        </h3>

        {decision !== null ? (
          <p className="mt-2 text-sm leading-relaxed text-[var(--color-terminal-text)]">
            {decision.rationale}
          </p>
        ) : (
          <div className="mt-2">
            <EmptyState message="Todavía no se registró una decisión para esta revisión." />
          </div>
        )}
      </div>

      {review.error !== null && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-[color-mix(in_srgb,var(--color-terminal-danger)_40%,transparent)] bg-[color-mix(in_srgb,var(--color-terminal-danger)_10%,transparent)] px-4 py-3"
        >
          <h3 className="text-sm font-medium text-[var(--color-terminal-danger)]">
            Error de la revisión
          </h3>
          <p className="mt-1 text-sm text-[var(--color-terminal-danger)]/90">
            {review.error}
          </p>
        </div>
      )}
    </section>
  )
}
