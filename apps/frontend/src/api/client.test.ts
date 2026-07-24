import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, createReview, getReview } from './client'
import type { ReviewCreateRequest, ReviewResponse } from './types'

const REQUEST_PAYLOAD: ReviewCreateRequest = {
  target_reference: 'demo/checkout-review',
  target_path: './examples/ecommerce',
  code: `from decimal import Decimal

from ecommerce.cart import Cart
from ecommerce.inventory import Inventory


def checkout_total(
    cart: Cart,
    inventory: Inventory,
    discount_percent: Decimal,
) -> Decimal:
    for item in cart.items:
        inventory.reserve(item.product_id, item.quantity)

    subtotal = cart.subtotal()
    return subtotal - ((subtotal * discount_percent) / Decimal(100))
`,
}

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('createReview', () => {
  it('sends a POST request with the given payload and returns the parsed body', async () => {
    const responseBody = { id: 'review-1' } as unknown as ReviewResponse
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(responseBody))
    vi.stubGlobal('fetch', fetchMock)

    const result = await createReview(REQUEST_PAYLOAD)

    expect(result).toEqual(responseBody)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toMatch(/\/reviews$/)
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual(REQUEST_PAYLOAD)
  })

  it('throws ApiError using the backend detail for a non-2xx response', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ detail: 'target_path must not be blank' }, { status: 422 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(createReview(REQUEST_PAYLOAD)).rejects.toMatchObject({
      name: 'ApiError',
      message: 'target_path must not be blank',
      status: 422,
    })
  })

  it('falls back to a generic message when detail is missing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({}, { status: 500 })))

    await expect(createReview(REQUEST_PAYLOAD)).rejects.toThrow(/status 500/)
  })

  it('throws ApiError when the response body is not valid JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response('not json', { status: 200, headers: { 'Content-Type': 'application/json' } }),
      ),
    )

    await expect(createReview(REQUEST_PAYLOAD)).rejects.toBeInstanceOf(ApiError)
  })

  it('throws ApiError when the network request itself fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(createReview(REQUEST_PAYLOAD)).rejects.toMatchObject({
      name: 'ApiError',
      status: 0,
    })
  })
})

describe('getReview', () => {
  it('sends a GET request to /reviews/{id}', async () => {
    const responseBody = { id: 'review-1' } as unknown as ReviewResponse
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(responseBody))
    vi.stubGlobal('fetch', fetchMock)

    const result = await getReview('review-1')

    expect(result).toEqual(responseBody)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit | undefined]
    expect(url).toMatch(/\/reviews\/review-1$/)
    expect(init?.method).toBeUndefined()
  })

  it('throws ApiError for a 404 response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Review not found' }, { status: 404 })),
    )

    await expect(getReview('missing-id')).rejects.toMatchObject({
      status: 404,
      detail: 'Review not found',
    })
  })
})

it('throws ApiError when a successful response body is empty', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response('', {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    ),
  )

  await expect(createReview(REQUEST_PAYLOAD)).rejects.toMatchObject({
    name: 'ApiError',
    message: 'The server returned an empty response.',
    status: 200,
  })
})
