import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ReviewForm } from './ReviewForm'

describe('ReviewForm', () => {
  it('calls onSubmit with the (default) form values', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<ReviewForm onSubmit={onSubmit} isSubmitting={false} />)

    await user.click(screen.getByRole('button', { name: /ejecutar revisión/i }))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    const payload = onSubmit.mock.calls[0][0]
    expect(payload.target_reference).not.toBe('')
    expect(payload.target_path).not.toBe('')
    expect(payload.code).not.toBe('')
  })

  it('does not submit when a required field is cleared', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<ReviewForm onSubmit={onSubmit} isSubmitting={false} />)

    await user.clear(screen.getByLabelText(/referencia de la revisión/i))
    await user.click(screen.getByRole('button', { name: /ejecutar revisión/i }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent(/obligatorios/i)
  })

  it('disables the form controls while submitting', () => {
    render(<ReviewForm onSubmit={vi.fn()} isSubmitting={true} />)

    expect(screen.getByLabelText(/referencia de la revisión/i)).toBeDisabled()
    expect(screen.getByLabelText(/ruta del proyecto/i)).toBeDisabled()
    expect(screen.getByLabelText(/código a revisar/i)).toBeDisabled()
    expect(
      screen.getByRole('button', { name: /ejecutando revisión/i }),
    ).toBeDisabled()
  })

  it('preserves entered values across re-renders', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<ReviewForm onSubmit={vi.fn()} isSubmitting={false} />)

    const referenceInput = screen.getByLabelText(/referencia de la revisión/i)
    await user.clear(referenceInput)
    await user.type(referenceInput, 'my/custom-branch')

    rerender(<ReviewForm onSubmit={vi.fn()} isSubmitting={false} />)

    expect(screen.getByLabelText(/referencia de la revisión/i)).toHaveValue('my/custom-branch')
  })
})
