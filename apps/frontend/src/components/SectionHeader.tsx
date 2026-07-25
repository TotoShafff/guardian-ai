import type { ReactNode } from 'react'

interface SectionHeaderProps {
  id?: string
  title: string
  count?: number
  icon?: ReactNode
  description?: string
  action?: ReactNode
}

export function SectionHeader({
  id,
  title,
  count,
  icon,
  description,
  action,
}: SectionHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          {icon !== undefined && (
            <span className="text-[var(--color-terminal-cyan)]">{icon}</span>
          )}
          <h2
            id={id}
            className="text-base font-semibold tracking-wide text-[var(--color-terminal-text)]"
          >
            {title}
          </h2>
          {count !== undefined && (
            <span className="rounded border border-[var(--color-terminal-border)] bg-[var(--color-terminal-elevated)] px-2 py-0.5 font-mono text-xs text-[var(--color-terminal-muted)]">
              {count}
            </span>
          )}
        </div>
        {description !== undefined && (
          <p className="mt-1 text-sm text-[var(--color-terminal-muted)]">{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}
