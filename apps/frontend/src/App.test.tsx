import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { ApiError } from './api/client'
import { makeDecision, makeEvidence, makeFinding, makeFixAttempt, makeReviewResponse } from './test/fixtures'

const { createReviewMock } = vi.hoisted(() => ({ createReviewMock: vi.fn() }))

vi.mock('./api/client', async () => {
  const actual = await vi.importActual<typeof import('./api/client')>('./api/client')
  return {
    ...actual,
    createReview: createReviewMock,
  }
})

beforeEach(() => {
  createReviewMock.mockReset()
})

describe('App', () => {
  it('calls the API client with the submitted form values', async () => {
    const user = userEvent.setup()
    createReviewMock.mockResolvedValue(makeReviewResponse())
    render(<App />)

    await user.click(screen.getByRole('button', { name: /run review/i }))

    await waitFor(() => expect(createReviewMock).toHaveBeenCalledTimes(1))
    expect(createReviewMock.mock.calls[0][0]).toMatchObject({
      target_reference: expect.any(String),
      target_path: expect.any(String),
      code: expect.any(String),
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

    await user.click(screen.getByRole('button', { name: /run review/i }))

    expect(screen.getByRole('button', { name: /running review/i })).toBeDisabled()

    resolveRequest(makeReviewResponse())
    await waitFor(() => expect(screen.getByRole('button', { name: /run review/i })).toBeEnabled())
  })

  it('shows an error message when the API call fails', async () => {
    const user = userEvent.setup()
    createReviewMock.mockRejectedValue(new ApiError('The API request failed with status 500.', 500))
    render(<App />)

    await user.click(screen.getByRole('button', { name: /run review/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/status 500/i)
  })

  it('renders decision, findings, evidence, patch, and validation results for a complete response', async () => {
    const user = userEvent.setup()
    createReviewMock.mockResolvedValue(
      makeReviewResponse({
        status: 'blocked',
        evidence: [makeEvidence()],
        decision: makeDecision({
          status: 'blocked',
          rationale: 'One blocking finding was reported.',
          blocking_findings: [makeFinding()],
          non_blocking_findings: [
            makeFinding({ id: 'finding-2', severity: 'non_blocking', title: 'Missing docstring' }),
          ],
        }),
        fix_attempts: [makeFixAttempt()],
      }),
    )
    render(<App />)

    await user.click(screen.getByRole('button', { name: /run review/i }))

    expect(await screen.findByText('One blocking finding was reported.')).toBeInTheDocument()
    expect(screen.getByText('Unused import')).toBeInTheDocument()
    expect(screen.getByText('`os` imported but unused')).toBeInTheDocument()
    expect(screen.getByText(/-import os/)).toBeInTheDocument()
    expect(screen.getByText('No issues found')).toBeInTheDocument()
  })

  it('renders explicit empty states for empty arrays and a null decision', async () => {
    const user = userEvent.setup()
    createReviewMock.mockResolvedValue(
      makeReviewResponse({ decision: null, evidence: [], findings: [], fix_attempts: [] }),
    )
    render(<App />)

    await user.click(screen.getByRole('button', { name: /run review/i }))

    expect(await screen.findByText(/no decision has been recorded/i)).toBeInTheDocument()
    expect(screen.getByText(/no blocking findings were reported/i)).toBeInTheDocument()
    expect(screen.getByText(/no non-blocking findings were reported/i)).toBeInTheDocument()
    expect(screen.getByText(/no evidence was collected/i)).toBeInTheDocument()
    expect(screen.getByText(/no fix attempts were made/i)).toBeInTheDocument()
  })
})
