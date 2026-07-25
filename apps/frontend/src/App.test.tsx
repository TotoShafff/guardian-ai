import { render, screen, waitFor } from '@testing-library/react'
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

describe('App', () => {
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

  it('renders an empty history state on load', async () => {
    render(<App />)

    expect(await screen.findByText('Todavía no hay revisiones guardadas.')).toBeInTheDocument()
    expect(getReviewsMock).toHaveBeenCalled()
  })

  it('loads a historical review without calling createReview', async () => {
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

    expect(await screen.findByText('demo/inventory-review')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Ver revisión' }))

    expect(
      await screen.findByText('Revisión bloqueada: 2 hallazgos bloqueantes y 1 no bloqueantes.'),
    ).toBeInTheDocument()
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

    await user.click(await screen.findByRole('button', { name: 'Ver revisión' }))

    expect(screen.getAllByText('Cargando revisión...').length).toBeGreaterThanOrEqual(1)

    resolveReview(makeReviewResponse({ id: 'historic-1' }))
    await waitFor(() =>
      expect(screen.queryByText('Cargando revisión...')).not.toBeInTheDocument(),
    )
  })

  it('refreshes the history after a successful new review', async () => {
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

    expect(await screen.findByText('Todavía no hay revisiones guardadas.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /ejecutar revisión/i }))

    await waitFor(() => {
      expect(screen.getAllByText('demo/post-run-review').length).toBeGreaterThanOrEqual(2)
    })
    expect(getReviewsMock.mock.calls.length).toBeGreaterThanOrEqual(2)
  })

  it('shows a history error and retries on Reintentar', async () => {
    const user = userEvent.setup()
    getReviewsMock
      .mockRejectedValueOnce(new ApiError('falló', 500))
      .mockResolvedValueOnce([makeReviewSummary({ target_reference: 'demo/recovered' })])
    render(<App />)

    expect(
      await screen.findByText('No se pudo cargar el historial de revisiones.'),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('demo/recovered')).toBeInTheDocument()
  })
})
