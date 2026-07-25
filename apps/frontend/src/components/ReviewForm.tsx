import { type FormEvent, useState } from 'react'

import type { ReviewCreateRequest } from '../api/types'

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
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div>
        <label htmlFor="target_reference" className="block text-sm font-medium text-slate-700">
          Referencia de la revisión
        </label>
        <input
          id="target_reference"
          name="target_reference"
          type="text"
          value={targetReference}
          onChange={(event) => setTargetReference(event.target.value)}
          disabled={isSubmitting}
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500"
        />
      </div>

      <div>
        <label htmlFor="target_path" className="block text-sm font-medium text-slate-700">
          Ruta del proyecto
        </label>
        <input
          id="target_path"
          name="target_path"
          type="text"
          value={targetPath}
          onChange={(event) => setTargetPath(event.target.value)}
          disabled={isSubmitting}
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500"
        />
      </div>

      <div>
        <label htmlFor="code" className="block text-sm font-medium text-slate-700">
          Código a revisar
        </label>
        <textarea
          id="code"
          name="code"
          rows={10}
          value={code}
          onChange={(event) => setCode(event.target.value)}
          disabled={isSubmitting}
          spellCheck={false}
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-500"
        />
      </div>

      {validationError !== null && (
        <p role="alert" className="text-sm text-red-600">
          {validationError}
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex items-center justify-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-indigo-300"
      >
        {isSubmitting ? 'Ejecutando revisión...' : 'Ejecutar revisión'}
      </button>
    </form>
  )
}
