/**
 * Small typed client for the Guardian AI review API.
 *
 * Uses native `fetch` only and throws `ApiError` for network failures,
 * non-2xx responses, invalid JSON, or empty successful responses.
 */

import { env } from '../config/env'
import type {
  ReviewCreateRequest,
  ReviewHistoryResponse,
  ReviewResponse,
  ReviewSummary,
} from './types'

/** Error thrown for any failed API call. */
export class ApiError extends Error {
  /** HTTP status code, or 0 when the request never reached the server. */
  readonly status: number

  /** The backend's `detail` message, when it was a plain string. */
  readonly detail: string | null

  constructor(
    message: string,
    status: number,
    detail: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

/** Extract a FastAPI-style `{ "detail": "..." }` message when available. */
function extractDetail(body: unknown): string | null {
  if (body !== null && typeof body === 'object' && 'detail' in body) {
    const { detail } = body as { detail: unknown }

    if (typeof detail === 'string' && detail.trim() !== '') {
      return detail
    }
  }

  return null
}

/** Read a response body and parse it as JSON without failing on an empty body. */
async function parseJsonBody(response: Response): Promise<unknown> {
  const text = await response.text()

  if (text.trim() === '') {
    return null
  }

  try {
    return JSON.parse(text) as unknown
  } catch {
    throw new ApiError(
      'El servidor devolvió una respuesta que no es JSON válido.',
      response.status,
    )
  }
}

/** Send one request to the configured Guardian AI API. */
async function request<TResponse>(
  path: string,
  init?: RequestInit,
): Promise<TResponse> {
  let response: Response

  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...init?.headers,
      },
    })
  } catch {
    throw new ApiError(
      'No se pudo conectar con la API de Guardian AI. Verificá que el backend esté ejecutándose.',
      0,
    )
  }

  const body = await parseJsonBody(response)

  if (!response.ok) {
    const detail = extractDetail(body)

    throw new ApiError(
      detail ?? `La solicitud a la API falló con el estado ${response.status}.`,
      response.status,
      detail,
    )
  }

  if (body === null) {
    throw new ApiError(
      'El servidor devolvió una respuesta vacía.',
      response.status,
    )
  }

  return body as TResponse
}

/** `POST /reviews` — trigger a review and return its complete result. */
export function createReview(
  payload: ReviewCreateRequest,
): Promise<ReviewResponse> {
  return request<ReviewResponse>('/reviews', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** `GET /reviews/{id}` — retrieve a previously persisted review result. */
export function getReview(reviewId: string): Promise<ReviewResponse> {
  return request<ReviewResponse>(
    `/reviews/${encodeURIComponent(reviewId)}`,
  )
}

/** `GET /reviews` — list recent persisted reviews for the history panel. */
export async function getReviews(): Promise<ReviewSummary[]> {
  const body = await request<ReviewHistoryResponse>('/reviews')
  return body.reviews
}