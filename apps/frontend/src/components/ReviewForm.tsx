import { type FormEvent, useState } from 'react'

import type { ReviewCreateRequest } from '../api/types'
import { TerminalIcon } from './icons'
import { SectionHeader } from './SectionHeader'

const DEFAULT_TARGET_REFERENCE = 'demo/checkout-review'
const DEFAULT_TARGET_PATH = './examples/ecommerce'
const DEFAULT_CODE = `from decimal import Decimal

from ecommerce.cart import Cart
from ecommerce.inventory import Inventory


def checkout_total(cart: Cart, inventory: Inventory, discount_percent: Decimal) -> Decimal:
    for item in cart.items:
        inventory.reserve(item.product_id, item.quantity)

    subtotal = cart.subtotal()
    return subtotal - ((subtotal * discount_percent) / Decimal(100))
`

interface ReviewFormProps {
  onSubmit: (payload: ReviewCreateRequest) => Promise<void> | void
  isSubmitting: boolean
}

const fieldClass =
  'mt-1.5 block w-full rounded-md border border-[var(--color-terminal-border)] bg-[var(--color-terminal-bg)] px-3 py-2 font-mono text-sm text-[var(--color-terminal-text)] placeholder:text-[var(--color-terminal-faint)] shadow-inner focus:border-[var(--color-terminal-cyan)] focus:outline-none focus:ring-1 focus:ring-[var(--color-terminal-cyan)] disabled:cursor-not-allowed disabled:opacity-50'

export function ReviewForm({ onSubmit, isSubmitting }: ReviewFormProps) {
  const [targetReference, setTargetReference] = useState(DEFAULT_TARGET_REFERENCE)
  const [targetPath, setTargetPath] = useState(DEFAULT_TARGET_PATH)
  const [code, setCode] = useState(DEFAULT_CODE)
  const [validationError, setValidationError] = useState<string | null>(null)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (targetReference.trim() === '' || targetPath.trim() === '' || code.trim() === '') {
      setValidationError(
        'La referencia de la revisión, la ruta del proyecto y el código son obligatorios.',
      )
      return
    }

    setValidationError(null)
    onSubmit({
      target_reference: targetReference.trim(),
      target_path: targetPath.trim(),
      code,
    })
  }

  return (
    <form
      onSubmit={handleSubmit}
      aria-label="Ejecutar una revisión de código"
      className="space-y-5 rounded-xl border border-[var(--color-terminal-border)] bg-[var(--color-terminal-panel)] p-5 shadow-[0_0_0_1px_rgba(62,207,255,0.04)] sm:p-6"
    >
      <SectionHeader
        title="Nueva revisión"
        icon={<TerminalIcon />}
        description="Definí el objetivo y el código a analizar. Ruff, Pytest y el proveedor de IA aportarán evidencia."
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="target_reference"
            className="block text-xs font-medium tracking-wide text-[var(--color-terminal-muted)] uppercase"
          >
            Referencia de la revisión
          </label>
          <p className="mt-0.5 text-xs text-[var(--color-terminal-faint)]">
            Identificador legible de la revisión (rama, ticket o demo).
          </p>
          <input
            id="target_reference"
            name="target_reference"
            type="text"
            value={targetReference}
            onChange={(event) => setTargetReference(event.target.value)}
            disabled={isSubmitting}
            className={fieldClass}
          />
        </div>

        <div>
          <label
            htmlFor="target_path"
            className="block text-xs font-medium tracking-wide text-[var(--color-terminal-muted)] uppercase"
          >
            Ruta del proyecto
          </label>
          <p className="mt-0.5 text-xs text-[var(--color-terminal-faint)]">
            Ruta local donde se ejecutarán las herramientas determinísticas.
          </p>
          <input
            id="target_path"
            name="target_path"
            type="text"
            value={targetPath}
            onChange={(event) => setTargetPath(event.target.value)}
            disabled={isSubmitting}
            className={fieldClass}
          />
        </div>
      </div>

      <div>
        <label
          htmlFor="code"
          className="block text-xs font-medium tracking-wide text-[var(--color-terminal-muted)] uppercase"
        >
          Código a revisar
        </label>
        <p className="mt-0.5 text-xs text-[var(--color-terminal-faint)]">
          Fragmento o módulo bajo análisis. Se muestra como editor de solo texto.
        </p>
        <div className="mt-1.5 overflow-hidden rounded-md border border-[color-mix(in_srgb,var(--color-terminal-cyan)_35%,var(--color-terminal-border))] bg-[#05080d]">
          <div className="flex items-center gap-2 border-b border-[var(--color-terminal-border)] px-3 py-1.5">
            <span className="h-2 w-2 rounded-full bg-[var(--color-terminal-danger)]/70" />
            <span className="h-2 w-2 rounded-full bg-[var(--color-terminal-warning)]/70" />
            <span className="h-2 w-2 rounded-full bg-[var(--color-terminal-accent)]/70" />
            <span className="ml-2 font-mono text-[10px] tracking-wider text-[var(--color-terminal-faint)] uppercase">
              source.py
            </span>
          </div>
          <textarea
            id="code"
            name="code"
            rows={12}
            value={code}
            onChange={(event) => setCode(event.target.value)}
            disabled={isSubmitting}
            spellCheck={false}
            className="block w-full resize-y border-0 bg-transparent px-3 py-3 font-mono text-sm leading-relaxed text-[var(--color-terminal-text)] caret-[var(--color-terminal-accent)] focus:outline-none focus:ring-0 disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>
      </div>

      {validationError !== null && (
        <p
          role="alert"
          className="rounded-md border border-[color-mix(in_srgb,var(--color-terminal-danger)_40%,transparent)] bg-[color-mix(in_srgb,var(--color-terminal-danger)_10%,transparent)] px-3 py-2 text-sm text-[var(--color-terminal-danger)]"
        >
          {validationError}
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="focus-ring inline-flex items-center justify-center gap-2 rounded-md bg-[var(--color-terminal-accent)] px-4 py-2.5 text-sm font-semibold text-[#04140c] transition hover:bg-[color-mix(in_srgb,var(--color-terminal-accent)_88%,white)] disabled:cursor-not-allowed disabled:bg-[var(--color-terminal-border-strong)] disabled:text-[var(--color-terminal-faint)]"
      >
        {isSubmitting && (
          <span
            className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#04140c]/30 border-t-[#04140c]"
            aria-hidden="true"
          />
        )}
        {isSubmitting ? 'Ejecutando revisión...' : 'Ejecutar revisión'}
      </button>
    </form>
  )
}
