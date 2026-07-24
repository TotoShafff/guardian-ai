import { useState } from 'react'
import { ApiError, createReview } from './api/client'
import type { ReviewCreateRequest, ReviewResponse } from './api/types'
import { ReviewForm } from './components/ReviewForm'
import { ReviewResult } from './components/ReviewResult'

type AppState =
  | { status: 'idle' }
  | { status: 'submitting' }
  | { status: 'success'; result: ReviewResponse }
  | { status: 'error'; message: string }

function App() {
  const [state, setState] = useState<AppState>({ status: 'idle' })

  async function handleSubmit(payload: ReviewCreateRequest) {
    setState({ status: 'submitting' })
    try {
      const result = await createReview(payload)
      setState({ status: 'success', result })
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Something went wrong while running the review.'
      setState({ status: 'error', message })
    }
  }

  const isSubmitting = state.status === 'submitting'

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-xl font-semibold text-slate-900">Guardian AI</h1>
          <p className="mt-1 text-sm text-slate-500">
            Trigger an agentic code review and inspect its evidence-backed decision.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <ReviewForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />

        {state.status === 'error' && (
          <p role="alert" className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {state.message}
          </p>
        )}

        {state.status === 'success' && <ReviewResult review={state.result} />}
      </main>
    </div>
  )
}

export default App
