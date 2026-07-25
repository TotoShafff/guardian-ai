interface IconProps {
  className?: string
  title?: string
}

export function TerminalIcon({ className = 'h-4 w-4', title }: IconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
    >
      {title ? <title>{title}</title> : null}
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path strokeLinecap="round" d="M7 9.5 10 12l-3 2.5M12.5 14.5H17" />
    </svg>
  )
}

export function HistoryIcon({ className = 'h-4 w-4', title }: IconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
    >
      {title ? <title>{title}</title> : null}
      <path strokeLinecap="round" d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3L4.5 9" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 4.5V9H9" />
      <path strokeLinecap="round" d="M12 8v4.5l3 1.5" />
    </svg>
  )
}

export function AlertIcon({ className = 'h-4 w-4', title }: IconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
    >
      {title ? <title>{title}</title> : null}
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4M12 16.5h.01" />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M10.3 4.8 2.9 17.2A2 2 0 0 0 4.6 20h14.8a2 2 0 0 0 1.7-2.8L13.7 4.8a2 2 0 0 0-3.4 0Z"
      />
    </svg>
  )
}

export function InfoIcon({ className = 'h-4 w-4', title }: IconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
    >
      {title ? <title>{title}</title> : null}
      <circle cx="12" cy="12" r="8.25" />
      <path strokeLinecap="round" d="M12 11v5M12 8h.01" />
    </svg>
  )
}

export function CodeIcon({ className = 'h-4 w-4', title }: IconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
    >
      {title ? <title>{title}</title> : null}
      <path strokeLinecap="round" strokeLinejoin="round" d="m8 8-4 4 4 4M16 8l4 4-4 4" />
    </svg>
  )
}
