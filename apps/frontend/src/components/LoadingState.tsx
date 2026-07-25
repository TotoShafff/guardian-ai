interface LoadingStateProps {
  message: string
}

export function LoadingState({ message }: LoadingStateProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-3 rounded-lg border border-[var(--color-terminal-border)] bg-[var(--color-terminal-panel)] px-4 py-3"
    >
      <span
        className="inline-block h-2.5 w-2.5 animate-pulse rounded-full bg-[var(--color-terminal-pending)] shadow-[0_0_8px_var(--color-terminal-pending)]"
        aria-hidden="true"
      />
      <p className="font-mono text-sm text-[var(--color-terminal-muted)]">{message}</p>
      <div className="ml-auto hidden h-2 w-24 animate-pulse rounded bg-[var(--color-terminal-elevated)] sm:block" />
    </div>
  )
}
