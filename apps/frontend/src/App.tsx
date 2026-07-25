import { useEffect, useState } from 'react'
import { ApiError, createReview, getReview, getReviews } from './api/client'
import type { ReviewCreateRequest, ReviewResponse, ReviewSummary } from './api/types'
import { ReviewForm } from './components/ReviewForm'
import { ReviewHistory } from './components/ReviewHistory'
import { ReviewResult } from './components/ReviewResult'

type ResultState =
  | { status: 'idle' }
  | { status: 'submitting' }
  | { status: 'loading_review' }
  | { status: 'success'; result: ReviewResponse }
  | { status: 'error'; message: string }

type HistoryState =
  | { status: 'loading' }
  | { status: 'ready'; reviews: ReviewSummary[] }
  | { status: 'error'; message: string }

function App() {
  const [resultState, setResultState] = useState<ResultState>({ status: 'idle' })
  const [historyState, setHistoryState] = useState<HistoryState>({ status: 'loading' })
  const [loadingReviewId, setLoadingReviewId] = useState<string | null>(null)

  async function loadHistory() {
    setHistoryState({ status: 'loading' })
    try {
      const reviews = await getReviews()
      setHistoryState({ status: 'ready', reviews })
    } catch {
      setHistoryState({
        status: 'error',
        message: 'No se pudo cargar el historial de revisiones.',
      })
    }
  }

  useEffect(() => {
    void loadHistory()
  }, [])

  async function handleSubmit(payload: ReviewCreateRequest) {
    setResultState({ status: 'submitting' })
    try {
      const result = await createReview(payload)
      setResultState({ status: 'success', result })
      await loadHistory()
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Ocurrió un error al ejecutar la revisión.'
      setResultState({ status: 'error', message })
    }
  }

  async function handleSelectReview(reviewId: string) {
    setLoadingReviewId(reviewId)
    setResultState({ status: 'loading_review' })
    try {
      const result = await getReview(reviewId)
      setResultState({ status: 'success', result })
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'No se pudo cargar la revisión seleccionada.'
      setResultState({ status: 'error', message })
    } finally {
      setLoadingReviewId(null)
    }
  }

  const isSubmitting = resultState.status === 'submitting'

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-xl font-semibold text-slate-900">Guardian AI</h1>
          <p className="mt-1 text-sm text-slate-500">
            Ejecutá una revisión de código con IA y analizá una decisión respaldada por evidencia.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <ReviewForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />

        <ReviewHistory
          reviews={historyState.status === 'ready' ? historyState.reviews : []}
          isLoading={historyState.status === 'loading'}
          error={historyState.status === 'error' ? historyState.message : null}
          loadingReviewId={loadingReviewId}
          onSelect={handleSelectReview}
          onRetry={() => {
            void loadHistory()
          }}
        />

        {resultState.status === 'error' && (
          <p
            role="alert"
            className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {resultState.message}
          </p>
        )}

        {resultState.status === 'loading_review' && (
          <p className="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
            Cargando revisión...
          </p>
        )}

        {resultState.status === 'success' && <ReviewResult review={resultState.result} />}
      </main>
    </div>
  )
}

export default App
