import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { ApiError } from './api/client'
import {
  makeDecision,
  makeEvidence,
  makeFinding,
  makeFixAttempt,
  makeReviewResponse,
  makeReviewSummary,
} from './test/fixtures'

const { createReviewMock, getReviewMock, getReviewsMock } = vi.hoisted(() => ({
  createReviewMock: vi.fn(),
  getReviewMock: vi.fn(),
  getReviewsMock: vi.fn(),
}))

vi.mock('./api/client', async () => {
  const actual = await vi.importActual<typeof import('./api/client')>('./api/client')
  return {
    ...actual,
    createReview: createReviewMock,
    getReview: getReviewMock,
    getReviews: getReviewsMock,
  }
})

beforeEach(() => {
  createReviewMock.mockReset()
  getReviewMock.mockReset()
  getReviewsMock.mockReset()
  getReviewsMock.mockResolvedValue([])
})

async function openHistoryTab(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('tab', { name: 'Historial' }))
}

describe('App', () => {
  it('renders the Guardian AI logo and shortened header subtitle', () => {
    render(<App />)

    expect(screen.getByAltText('Logo de Guardian AI')).toBeInTheDocument()
    expect(screen.getByText('Revisión de código asistida por agentes')).toBeInTheDocument()
    expect(
      screen.queryByText(
        'Revisión de código asistida por agentes y evidencia determinística',
      ),
    ).not.toBeInTheDocument()
    // Former green shield mark used this path; navigation icons may still use SVG.
    expect(
      document.querySelector('path[d="M12 3 5 6v5c0 4.5 2.8 7.8 7 9 4.2-1.2 7-4.5 7-9V6l-7-3Z"]'),
    ).not.toBeInTheDocument()
  })

  it('shows Nueva revisión by default and does not mix the history table underneath', async () => {
    getReviewsMock.mockResolvedValue([
      makeReviewSummary({ target_reference: 'demo/hidden-in-new-tab' }),
    ])
    render(<App />)

    expect(screen.getByRole('tab', { name: 'Nueva revisión' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByRole('button', { name: /ejecutar revisión/i })).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText('demo/hidden-in-new-tab')).not.toBeInTheDocument()
    expect(screen.queryByText('Historial de revisiones')).not.toBeInTheDocument()
  })

  it('shows the history table when Historial is selected', async () => {
    const user = userEvent.setup()
    getReviewsMock.mockResolvedValue([
      makeReviewSummary({
        id: 'review-a',
        target_reference: 'demo/inventory-review',
        status: 'blocked',
        blocking_findings_count: 1,
        non_blocking_findings_count: 1,
      }),
      makeReviewSummary({
        id: 'review-b',
        target_reference: 'demo/checkout-review',
        status: 'approved',
      }),
    ])
    render(<App />)

    await openHistoryTab(user)

    expect(await screen.findByText('Historial de revisiones')).toBeInTheDocument()
    const table = screen.getByRole('table')
    expect(within(table).getByText('demo/inventory-review')).toBeInTheDocument()
    expect(within(table).getByText('demo/checkout-review')).toBeInTheDocument()
    expect(within(table).getByText('Bloqueado')).toBeInTheDocument()
    expect(within(table).getByText('Aprobado')).toBeInTheDocument()
  })

  it('calls the API client with the submitted form values', async () => {
    const user = userEvent.setup()
    createReviewMock.mockResolvedValue(makeReviewResponse())
    render(<App />)

    await user.click(screen.getByRole('button', { name: /ejecutar revisión/i }))

    await waitFor(() => expect(createReviewMock).toHaveBeenCalledTimes(1))
    expect(createReviewMock).toHaveBeenCalledWith({
      target_reference: 'demo/checkout-review',
      target_path: './examples/ecommerce',
      code: expect.stringContaining('checkout_total'),
    })
  })

  it('disables the submit button while the request is in flight', async () => {
    const user = userEvent.setup()
    let resolveRequest: (value: ReturnType<typeof makeReviewResponse>) => void = () => {}
    createReviewMock.mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve
      }),
    )
    render(<App />)

    await user.click(screen.getByRole('button', { name: /ejecutar revisión/i }))

    expect(screen.getByRole('button', { name: /ejecutando revisión/i })).toBeDisabled()

    resolveRequest(makeReviewResponse())
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /ejecutar revisión/i })).toBeEnabled(),
    )
  })

  it('shows an error message when the API call fails', async () => {
    const user = userEvent.setup()
    createReviewMock.mockRejectedValue(
      new ApiError('La solicitud a la API falló con el estado 500.', 500),
    )
    render(<App />)

    await user.click(screen.getByRole('button', { name: /ejecutar revisión/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/estado 500/i)
  })

  it('renders decision, findings, evidence, patch, and validation results for a complete response', async () => {
    const user = userEvent.setup()
    createReviewMock.mockResolvedValue(
      makeReviewResponse({
        status: 'blocked',
        evidence: [makeEvidence()],
        decision: makeDecision({
          status: 'blocked',
          rationale: 'Revisión bloqueada: 1 hallazgos bloqueantes y 1 no bloqueantes.',
          blocking_findings: [makeFinding()],
          non_blocking_findings: [
            makeFinding({
              id: 'finding-2',
              severity: 'non_blocking',
              title: 'Falta docstring',
            }),
          ],
        }),
        fix_attempts: [makeFixAttempt()],
      }),
    )
    render(<App />)

    await user.click(screen.getByRole('button', { name: /ejecutar revisión/i }))

    expect(
      await screen.findByText('Revisión bloqueada: 1 hallazgos bloqueantes y 1 no bloqueantes.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Importación no utilizada')).toBeInTheDocument()
    expect(
      screen.getAllByText('El módulo `os` fue importado, pero no se utiliza.').length,
    ).toBeGreaterThanOrEqual(2)
    expect(screen.getByText(/-import os/)).toBeInTheDocument()
    expect(screen.getByText(/propuestas de corrección/i)).toBeInTheDocument()
    expect(screen.getByText('Propuesta #1')).toBeInTheDocument()
    expect(screen.getByText('Propuesta para: Importación no utilizada')).toBeInTheDocument()
    expect(screen.getByText('Qué corrige:')).toBeInTheDocument()
    expect(
      screen.getByText('Propuesta generada por IA. Requiere revisión del desarrollador.'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Aprobado')).not.toBeInTheDocument()
    expect(screen.queryByText('Passed')).not.toBeInTheDocument()
    expect(screen.queryByText('mock_validator')).not.toBeInTheDocument()
    expect(
      screen.queryByText('El parche fue aceptado por la validación determinística simulada.'),
    ).not.toBeInTheDocument()
    expect(screen.queryByText('No se encontraron problemas')).not.toBeInTheDocument()
  })

  it('renders explicit empty states for empty arrays and a null decision', async () => {
    const user = userEvent.setup()
    createReviewMock.mockResolvedValue(
      makeReviewResponse({ decision: null, evidence: [], findings: [], fix_attempts: [] }),
    )
    render(<App />)

    await user.click(screen.getByRole('button', { name: /ejecutar revisión/i }))

    expect(
      await screen.findByText(/todavía no se registró una decisión/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/no se reportaron hallazgos bloqueantes/i)).toBeInTheDocument()
    expect(screen.getByText(/no se reportaron hallazgos no bloqueantes/i)).toBeInTheDocument()
    expect(screen.getByText(/no se recopiló evidencia/i)).toBeInTheDocument()
    expect(
      screen.getByText(/no se generaron propuestas de corrección para esta revisión/i),
    ).toBeInTheDocument()
  })

  it('renders an empty history state on the Historial tab', async () => {
    const user = userEvent.setup()
    render(<App />)

    await openHistoryTab(user)

    expect(await screen.findByText('Todavía no hay revisiones guardadas.')).toBeInTheDocument()
    expect(getReviewsMock).toHaveBeenCalled()
  })

  it('loads a historical review via GET, shows a detail view, and never POSTs', async () => {
    const user = userEvent.setup()
    getReviewsMock.mockResolvedValue([
      makeReviewSummary({
        id: 'historic-1',
        target_reference: 'demo/inventory-review',
      }),
    ])
    getReviewMock.mockResolvedValue(
      makeReviewResponse({
        id: 'historic-1',
        target_reference: 'demo/inventory-review',
        decision: makeDecision({
          rationale: 'Revisión bloqueada: 2 hallazgos bloqueantes y 1 no bloqueantes.',
        }),
      }),
    )
    render(<App />)

    await openHistoryTab(user)
    const table = await screen.findByRole('table')
    expect(within(table).getByText('demo/inventory-review')).toBeInTheDocument()

    await user.click(within(table).getByRole('button', { name: 'Ver revisión' }))

    expect(
      await screen.findByText('Revisión bloqueada: 2 hallazgos bloqueantes y 1 no bloqueantes.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Volver al historial' })).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(getReviewMock).toHaveBeenCalledWith('historic-1')
    expect(createReviewMock).not.toHaveBeenCalled()
  })

  it('shows a loading state while opening a historical review', async () => {
    const user = userEvent.setup()
    let resolveReview: (value: ReturnType<typeof makeReviewResponse>) => void = () => {}
    getReviewsMock.mockResolvedValue([makeReviewSummary({ id: 'historic-1' })])
    getReviewMock.mockReturnValue(
      new Promise((resolve) => {
        resolveReview = resolve
      }),
    )
    render(<App />)

    await openHistoryTab(user)
    const table = await screen.findByRole('table')
    await user.click(within(table).getByRole('button', { name: 'Ver revisión' }))

    expect(screen.getByText('Cargando revisión...')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()

    resolveReview(
      makeReviewResponse({
        id: 'historic-1',
        decision: makeDecision({ rationale: 'Detalle histórico cargado.' }),
      }),
    )
    expect(await screen.findByText('Detalle histórico cargado.')).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.queryByText('Cargando revisión...')).not.toBeInTheDocument(),
    )
  })

  it('returns to the history table when Volver al historial is pressed', async () => {
    const user = userEvent.setup()
    getReviewsMock.mockResolvedValue([
      makeReviewSummary({
        id: 'historic-1',
        target_reference: 'demo/inventory-review',
      }),
    ])
    getReviewMock.mockResolvedValue(
      makeReviewResponse({
        id: 'historic-1',
        decision: makeDecision({ rationale: 'Detalle histórico.' }),
      }),
    )
    render(<App />)

    await openHistoryTab(user)
    await user.click(within(await screen.findByRole('table')).getByRole('button', { name: 'Ver revisión' }))
    expect(await screen.findByText('Detalle histórico.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Volver al historial' }))

    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.queryByText('Detalle histórico.')).not.toBeInTheDocument()
    // List was kept in memory; no forced refetch required.
    expect(getReviewsMock.mock.calls.length).toBeGreaterThanOrEqual(1)
  })

  it('shows a Spanish error when the historical detail request fails', async () => {
    const user = userEvent.setup()
    getReviewsMock.mockResolvedValue([makeReviewSummary({ id: 'historic-1' })])
    getReviewMock.mockRejectedValue(
      new ApiError('No se pudo cargar la revisión seleccionada.', 500),
    )
    render(<App />)

    await openHistoryTab(user)
    await user.click(within(await screen.findByRole('table')).getByRole('button', { name: 'Ver revisión' }))

    expect(
      await screen.findByText('No se pudo cargar la revisión seleccionada.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Volver al historial' })).toBeInTheDocument()
  })

  it('refreshes the history after a successful new review without leaving Nueva revisión', async () => {
    const user = userEvent.setup()
    createReviewMock.mockImplementation(async () => {
      const result = makeReviewResponse({
        id: 'new-review',
        target_reference: 'demo/post-run-review',
      })
      getReviewsMock.mockResolvedValue([
        makeReviewSummary({
          id: 'new-review',
          target_reference: 'demo/post-run-review',
        }),
      ])
      return result
    })
    render(<App />)

    await user.click(screen.getByRole('button', { name: /ejecutar revisión/i }))

    expect(await screen.findByText('demo/post-run-review')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Nueva revisión' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(getReviewsMock.mock.calls.length).toBeGreaterThanOrEqual(2)

    await openHistoryTab(user)
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getByText('demo/post-run-review')).toBeInTheDocument()
  })

  it('keeps the current new-review result when switching tabs', async () => {
    const user = userEvent.setup()
    createReviewMock.mockResolvedValue(
      makeReviewResponse({
        decision: makeDecision({ rationale: 'Resultado de la revisión nueva.' }),
      }),
    )
    getReviewsMock.mockResolvedValue([
      makeReviewSummary({ target_reference: 'demo/older-review' }),
    ])
    render(<App />)

    await user.click(screen.getByRole('button', { name: /ejecutar revisión/i }))
    expect(await screen.findByText('Resultado de la revisión nueva.')).toBeInTheDocument()

    await openHistoryTab(user)
    expect(screen.queryByText('Resultado de la revisión nueva.')).not.toBeInTheDocument()
    const table = await screen.findByRole('table')
    expect(within(table).getByText('demo/older-review')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Nueva revisión' }))
    expect(screen.getByText('Resultado de la revisión nueva.')).toBeInTheDocument()
    // Only one report visible on Nueva revisión.
    expect(screen.queryByText('demo/older-review')).not.toBeInTheDocument()
  })

  it('does not show two reports at once when opening a historical review', async () => {
    const user = userEvent.setup()
    createReviewMock.mockResolvedValue(
      makeReviewResponse({
        decision: makeDecision({ rationale: 'Resultado de la revisión nueva.' }),
      }),
    )
    getReviewsMock.mockResolvedValue([
      makeReviewSummary({
        id: 'historic-1',
        target_reference: 'demo/inventory-review',
      }),
    ])
    getReviewMock.mockResolvedValue(
      makeReviewResponse({
        id: 'historic-1',
        decision: makeDecision({ rationale: 'Resultado histórico distinto.' }),
      }),
    )
    render(<App />)

    await user.click(screen.getByRole('button', { name: /ejecutar revisión/i }))
    expect(await screen.findByText('Resultado de la revisión nueva.')).toBeInTheDocument()

    await openHistoryTab(user)
    await user.click(within(await screen.findByRole('table')).getByRole('button', { name: 'Ver revisión' }))

    expect(await screen.findByText('Resultado histórico distinto.')).toBeInTheDocument()
    expect(screen.queryByText('Resultado de la revisión nueva.')).not.toBeInTheDocument()
  })

  it('shows a history error and retries on Reintentar', async () => {
    const user = userEvent.setup()
    let shouldFail = true
    getReviewsMock.mockImplementation(async () => {
      if (shouldFail) {
        throw new ApiError('falló', 500)
      }
      return [makeReviewSummary({ target_reference: 'demo/recovered' })]
    })
    render(<App />)

    await openHistoryTab(user)

    expect(
      await screen.findByText('No se pudo cargar el historial de revisiones.'),
    ).toBeInTheDocument()

    shouldFail = false
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    const table = await screen.findByRole('table')
    expect(within(table).getByText('demo/recovered')).toBeInTheDocument()
  })
})
