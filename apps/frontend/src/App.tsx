import { useEffect, useState } from 'react'
import { ApiError, createReview, getReview, getReviews } from './api/client'
import type { ReviewCreateRequest, ReviewResponse, ReviewSummary } from './api/types'
import { LoadingState } from './components/LoadingState'
import { ReviewForm } from './components/ReviewForm'
import { ReviewHistory } from './components/ReviewHistory'
import { ReviewResult } from './components/ReviewResult'
import { StatusBadge } from './components/StatusBadge'
import { HistoryIcon, TerminalIcon } from './components/icons'
import {
  formatDateTimeShort,
  reviewStatusLabel,
  reviewStatusTone,
} from './lib/presentation'
import guardianLogo from './assets/guardian-logo.png'

type TabId = 'new' | 'history'

type CurrentResultState =
  | { status: 'idle' }
  | { status: 'submitting' }
  | { status: 'success'; result: ReviewResponse }
  | { status: 'error'; message: string }

type HistoryListState =
  | { status: 'loading' }
  | { status: 'ready'; reviews: ReviewSummary[] }
  | { status: 'error'; message: string }

type HistoryDetailState =
  | { status: 'idle' }
  | { status: 'loading'; reviewId: string }
  | { status: 'success'; result: ReviewResponse }
  | { status: 'error'; message: string }

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('new')
  const [currentResult, setCurrentResult] = useState<CurrentResultState>({
    status: 'idle',
  })
  const [historyList, setHistoryList] = useState<HistoryListState>({
    status: 'loading',
  })
  const [historyDetail, setHistoryDetail] = useState<HistoryDetailState>({
    status: 'idle',
  })

  async function loadHistory() {
    setHistoryList({ status: 'loading' })
    try {
      const reviews = await getReviews()
      setHistoryList({ status: 'ready', reviews })
    } catch {
      setHistoryList({
        status: 'error',
        message: 'No se pudo cargar el historial de revisiones.',
      })
    }
  }

  useEffect(() => {
    void loadHistory()
  }, [])

  async function handleSubmit(payload: ReviewCreateRequest) {
    setCurrentResult({ status: 'submitting' })
    try {
      const result = await createReview(payload)
      setCurrentResult({ status: 'success', result })
      await loadHistory()
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Ocurrió un error al ejecutar la revisión.'
      setCurrentResult({ status: 'error', message })
    }
  }

  async function handleSelectReview(reviewId: string) {
    setActiveTab('history')
    setHistoryDetail({ status: 'loading', reviewId })
    try {
      const result = await getReview(reviewId)
      setHistoryDetail({ status: 'success', result })
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'No se pudo cargar la revisión seleccionada.'
      setHistoryDetail({ status: 'error', message })
    }
  }

  function handleBackToHistory() {
    setHistoryDetail({ status: 'idle' })
  }

  const isSubmitting = currentResult.status === 'submitting'
  const loadingReviewId =
    historyDetail.status === 'loading' ? historyDetail.reviewId : null
  const showingHistoryDetail =
    historyDetail.status === 'loading' ||
    historyDetail.status === 'success' ||
    historyDetail.status === 'error'

  const tabBase =
    'focus-ring inline-flex items-center gap-2 rounded-t-md border border-transparent px-3 py-2.5 text-sm font-medium transition'
  const tabActive =
    'border-[var(--color-terminal-border)] border-b-[var(--color-terminal-panel)] bg-[var(--color-terminal-panel)] text-[var(--color-terminal-accent)] shadow-[inset_0_-2px_0_0_var(--color-terminal-accent)]'
  const tabInactive =
    'text-[var(--color-terminal-muted)] hover:bg-[var(--color-terminal-elevated)]/50 hover:text-[var(--color-terminal-text)]'

  return (
    <div className="app-shell">
      <header className="border-b border-[var(--color-terminal-border)] bg-[color-mix(in_srgb,var(--color-terminal-surface)_92%,transparent)] backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex min-w-0 items-start gap-3">
              <div className="mt-0.5 h-10 w-10 shrink-0 overflow-hidden rounded-full border border-[color-mix(in_srgb,var(--color-terminal-cyan)_40%,var(--color-terminal-border))] bg-black shadow-[0_0_12px_rgba(62,207,255,0.22)] sm:h-12 sm:w-12 md:h-14 md:w-14">
                <img
                  src={guardianLogo}
                  alt="Logo de Guardian AI"
                  width={56}
                  height={56}
                  className="h-full w-full object-cover"
                />
              </div>
              <div className="min-w-0">
                <h1 className="font-mono text-xl font-semibold tracking-[0.04em] text-[var(--color-terminal-text)]">
                  Guardian AI
                </h1>
                <p className="mt-1 max-w-2xl font-mono text-xs leading-relaxed text-[var(--color-terminal-muted)] sm:text-sm">
                  Revisión de código asistida por agentes
                </p>
              </div>
            </div>

            <div
              className="inline-flex items-center gap-2 rounded-full border border-[color-mix(in_srgb,var(--color-terminal-accent)_30%,var(--color-terminal-border))] bg-[color-mix(in_srgb,var(--color-terminal-accent)_8%,var(--color-terminal-panel))] px-3 py-1.5"
              aria-label="Estado de la interfaz: sistema activo"
            >
              <span
                className="h-2 w-2 animate-pulse rounded-full bg-[var(--color-terminal-accent)] shadow-[0_0_8px_var(--color-terminal-accent)]"
                aria-hidden="true"
              />
              <span className="font-mono text-[10px] tracking-[0.16em] text-[var(--color-terminal-accent)] uppercase">
                Sistema activo
              </span>
            </div>
          </div>

          <nav
            className="mt-6 flex gap-1 border-b border-[var(--color-terminal-border)]"
            aria-label="Secciones principales"
            role="tablist"
          >
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'new'}
              aria-current={activeTab === 'new' ? 'page' : undefined}
              onClick={() => setActiveTab('new')}
              className={`${tabBase} ${activeTab === 'new' ? tabActive : tabInactive}`}
            >
              <TerminalIcon className="h-3.5 w-3.5" />
              Nueva revisión
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'history'}
              aria-current={activeTab === 'history' ? 'page' : undefined}
              onClick={() => setActiveTab('history')}
              className={`${tabBase} ${activeTab === 'history' ? tabActive : tabInactive}`}
            >
              <HistoryIcon className="h-3.5 w-3.5" />
              Historial
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        {activeTab === 'new' && (
          <>
            <ReviewForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />

            {currentResult.status === 'submitting' && (
              <LoadingState message="Ejecutando revisión..." />
            )}

            {currentResult.status === 'error' && (
              <p
                role="alert"
                aria-live="assertive"
                className="rounded-lg border border-[color-mix(in_srgb,var(--color-terminal-danger)_40%,transparent)] bg-[color-mix(in_srgb,var(--color-terminal-danger)_10%,transparent)] px-4 py-3 text-sm text-[var(--color-terminal-danger)]"
              >
                {currentResult.message}
              </p>
            )}

            {currentResult.status === 'success' && (
              <ReviewResult review={currentResult.result} />
            )}
          </>
        )}

        {activeTab === 'history' && !showingHistoryDetail && (
          <ReviewHistory
            reviews={historyList.status === 'ready' ? historyList.reviews : []}
            isLoading={historyList.status === 'loading'}
            error={historyList.status === 'error' ? historyList.message : null}
            loadingReviewId={loadingReviewId}
            onSelect={handleSelectReview}
            onRetry={() => {
              void loadHistory()
            }}
          />
        )}

        {activeTab === 'history' && historyDetail.status === 'loading' && (
          <LoadingState message="Cargando revisión..." />
        )}

        {activeTab === 'history' && historyDetail.status === 'error' && (
          <div className="space-y-4">
            <button
              type="button"
              onClick={handleBackToHistory}
              className="focus-ring text-sm font-medium text-[var(--color-terminal-cyan)] hover:text-[var(--color-terminal-accent)]"
            >
              Volver al historial
            </button>
            <p
              role="alert"
              aria-live="assertive"
              className="rounded-lg border border-[color-mix(in_srgb,var(--color-terminal-danger)_40%,transparent)] bg-[color-mix(in_srgb,var(--color-terminal-danger)_10%,transparent)] px-4 py-3 text-sm text-[var(--color-terminal-danger)]"
            >
              {historyDetail.message}
            </p>
          </div>
        )}

        {activeTab === 'history' && historyDetail.status === 'success' && (
          <div className="space-y-6">
            <div className="rounded-xl border border-[var(--color-terminal-border)] bg-[var(--color-terminal-panel)] p-5 sm:p-6">
              <p className="font-mono text-[10px] tracking-[0.14em] text-[var(--color-terminal-faint)] uppercase">
                Historial / Detalle de revisión
              </p>
              <button
                type="button"
                onClick={handleBackToHistory}
                className="focus-ring mt-3 text-sm font-medium text-[var(--color-terminal-cyan)] hover:text-[var(--color-terminal-accent)]"
              >
                Volver al historial
              </button>

              <div className="mt-4 flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 space-y-2">
                  <p className="font-mono text-lg font-semibold text-[var(--color-terminal-text)]">
                    {historyDetail.result.target_reference}
                  </p>
                  <p className="font-mono text-sm text-[var(--color-terminal-muted)]">
                    {formatDateTimeShort(historyDetail.result.created_at)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge label="Revisión guardada" tone="info" />
                  <StatusBadge
                    label={reviewStatusLabel(historyDetail.result.status)}
                    tone={reviewStatusTone(historyDetail.result.status)}
                  />
                </div>
              </div>
            </div>

            <ReviewResult review={historyDetail.result} />
          </div>
        )}
      </main>
    </div>
  )
}

export default App
