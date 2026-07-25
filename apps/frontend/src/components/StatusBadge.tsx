import type { BadgeTone } from '../lib/presentation'

const TONE_CLASSES: Record<BadgeTone, string> = {
  success:
    'border-[var(--color-terminal-accent-dim)] bg-[color-mix(in_srgb,var(--color-terminal-accent)_12%,transparent)] text-[var(--color-terminal-accent)]',
  danger:
    'border-[color-mix(in_srgb,var(--color-terminal-danger)_45%,transparent)] bg-[color-mix(in_srgb,var(--color-terminal-danger)_12%,transparent)] text-[var(--color-terminal-danger)]',
  warning:
    'border-[color-mix(in_srgb,var(--color-terminal-warning)_45%,transparent)] bg-[color-mix(in_srgb,var(--color-terminal-warning)_12%,transparent)] text-[var(--color-terminal-warning)]',
  info: 'border-[color-mix(in_srgb,var(--color-terminal-cyan)_45%,transparent)] bg-[color-mix(in_srgb,var(--color-terminal-cyan)_12%,transparent)] text-[var(--color-terminal-cyan)]',
  pending:
    'border-[color-mix(in_srgb,var(--color-terminal-pending)_45%,transparent)] bg-[color-mix(in_srgb,var(--color-terminal-pending)_12%,transparent)] text-[var(--color-terminal-pending)]',
  neutral:
    'border-[var(--color-terminal-border-strong)] bg-[var(--color-terminal-elevated)] text-[var(--color-terminal-muted)]',
}

interface StatusBadgeProps {
  label: string
  tone: BadgeTone
}

export function StatusBadge({ label, tone }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-[11px] font-medium tracking-wide uppercase ${TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  )
}
