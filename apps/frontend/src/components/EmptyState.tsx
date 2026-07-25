interface EmptyStateProps {
  message: string
}

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <p className="rounded-lg border border-dashed border-[var(--color-terminal-border-strong)] bg-[color-mix(in_srgb,var(--color-terminal-elevated)_55%,transparent)] px-4 py-4 font-mono text-sm text-[var(--color-terminal-muted)]">
      {message}
    </p>
  )
}
