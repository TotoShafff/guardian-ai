import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { makeReviewSummary } from '../test/fixtures'
import { ReviewHistory } from './ReviewHistory'

describe('ReviewHistory', () => {
  it('renders the empty state when there are no reviews', () => {
    render(
      <ReviewHistory
        reviews={[]}
        isLoading={false}
        error={null}
        loadingReviewId={null}
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getByText('Historial de revisiones')).toBeInTheDocument()
    expect(screen.getByText('Todavía no hay revisiones guardadas.')).toBeInTheDocument()
  })

  it('renders several reviews with translated statuses and finding counts', () => {
    render(
      <ReviewHistory
        reviews={[
          makeReviewSummary({
            id: 'review-a',
            target_reference: 'demo/inventory-review',
            status: 'blocked',
            blocking_findings_count: 2,
            non_blocking_findings_count: 1,
          }),
          makeReviewSummary({
            id: 'review-b',
            target_reference: 'demo/checkout-review',
            status: 'approved',
            blocking_findings_count: 0,
            non_blocking_findings_count: 0,
          }),
        ]}
        isLoading={false}
        error={null}
        loadingReviewId={null}
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getByText('demo/inventory-review')).toBeInTheDocument()
    expect(screen.getByText('demo/checkout-review')).toBeInTheDocument()
    expect(screen.getByText('Bloqueado')).toBeInTheDocument()
    expect(screen.getByText('Aprobado')).toBeInTheDocument()
    expect(screen.getByText(/2 bloqueantes · 1 no bloqueantes/)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Ver revisión' })).toHaveLength(2)
  })

  it('calls onSelect when Ver revisión is clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()

    render(
      <ReviewHistory
        reviews={[makeReviewSummary({ id: 'review-42' })]}
        isLoading={false}
        error={null}
        loadingReviewId={null}
        onSelect={onSelect}
        onRetry={vi.fn()}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Ver revisión' }))

    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith('review-42')
  })

  it('shows the loading label on the selected review button', () => {
    render(
      <ReviewHistory
        reviews={[makeReviewSummary({ id: 'review-42' })]}
        isLoading={false}
        error={null}
        loadingReviewId="review-42"
        onSelect={vi.fn()}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: 'Cargando revisión...' })).toBeDisabled()
  })

  it('shows an error and calls onRetry when Reintentar is clicked', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(
      <ReviewHistory
        reviews={[]}
        isLoading={false}
        error="No se pudo cargar el historial de revisiones."
        loadingReviewId={null}
        onSelect={vi.fn()}
        onRetry={onRetry}
      />,
    )

    expect(
      screen.getByText('No se pudo cargar el historial de revisiones.'),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
