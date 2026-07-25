import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { proposalFixExplanation } from '../lib/presentation'
import { makeFinding, makeFixAttempt } from '../test/fixtures'
import { FixAttemptsSection } from './FixAttemptsSection'

describe('proposalFixExplanation', () => {
  it('prefers the finding description when present', () => {
    const finding = makeFinding({
      title: 'Importación no utilizada',
      description: 'El módulo `os` fue importado, pero no se utiliza.',
    })

    expect(proposalFixExplanation(finding)).toBe(
      'El módulo `os` fue importado, pero no se utiliza.',
    )
  })

  it('falls back to the finding title when description is blank', () => {
    const finding = makeFinding({
      title: 'Falta validar discount_percent',
      description: '   ',
    })

    expect(proposalFixExplanation(finding)).toBe(
      'Corrige: Falta validar discount_percent.',
    )
  })
})

describe('FixAttemptsSection', () => {
  it('renders the empty state when there are no proposals', () => {
    render(<FixAttemptsSection fixAttempts={[]} findings={[]} />)

    expect(screen.getByText('Propuestas de corrección')).toBeInTheDocument()
    expect(
      screen.getByText('No se generaron propuestas de corrección para esta revisión.'),
    ).toBeInTheDocument()
  })

  it('renders proposal metadata, explanation, diff, and reviewer note', () => {
    const finding = makeFinding({
      id: 'finding-1',
      title: 'Importación no utilizada',
      description: 'El módulo `os` fue importado, pero no se utiliza.',
    })
    const attempt = makeFixAttempt({
      finding_id: finding.id,
      attempt_number: 1,
      validation_results: [
        {
          status: 'passed',
          tool: 'mock_validator',
          message: 'El parche fue aceptado por la validación determinística simulada.',
        },
      ],
    })

    render(<FixAttemptsSection fixAttempts={[attempt]} findings={[finding]} />)

    expect(screen.getByText('Propuestas de corrección')).toBeInTheDocument()
    expect(screen.getByText('Propuesta #1')).toBeInTheDocument()
    expect(
      screen.getByText('Propuesta para: Importación no utilizada'),
    ).toBeInTheDocument()
    expect(screen.getByText('Qué corrige:')).toBeInTheDocument()
    expect(
      screen.getByText('El módulo `os` fue importado, pero no se utiliza.'),
    ).toBeInTheDocument()
    expect(screen.getByText(/-import os/)).toBeInTheDocument()
    expect(
      screen.getByText('Propuesta generada por IA. Requiere revisión del desarrollador.'),
    ).toBeInTheDocument()

    expect(screen.queryByText('Aprobado')).not.toBeInTheDocument()
    expect(screen.queryByText('Passed')).not.toBeInTheDocument()
    expect(screen.queryByText('mock_validator')).not.toBeInTheDocument()
    expect(
      screen.queryByText('El parche fue aceptado por la validación determinística simulada.'),
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/validación simulada/i)).not.toBeInTheDocument()
  })
})
