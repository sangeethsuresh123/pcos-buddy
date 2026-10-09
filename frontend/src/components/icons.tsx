type IconProps = { size?: number; className?: string }

function stroke(size: number, className?: string) {
  return {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    className,
    'aria-hidden': true,
  }
}

export function HomeIcon({ size = 22, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V21h5v-6h4v6h5V9.5" />
    </svg>
  )
}

export function PulseIcon({ size = 22, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M3 12h4l2.5-6 4 12 2.5-6H21" />
    </svg>
  )
}

export function TrendIcon({ size = 22, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M3 17l5.5-5.5 3.5 3.5L21 6" />
      <path d="M15 6h6v6" />
    </svg>
  )
}

export function ChatIcon({ size = 22, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M21 12a8 8 0 0 1-8 8H8l-4 3v-4.6A8 8 0 0 1 4 12a8 8 0 0 1 8-8h1a8 8 0 0 1 8 8z" />
    </svg>
  )
}

export function PlusIcon({ size = 20, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

export function TrashIcon({ size = 18, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13" />
    </svg>
  )
}

export function SendIcon({ size = 18, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M21 3 10.5 13.5" />
      <path d="M21 3l-6.8 18-3.7-7.5L3 9.8 21 3z" />
    </svg>
  )
}

export function ArrowUpIcon({ size = 16, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M12 19V5M6 11l6-6 6 6" />
    </svg>
  )
}

export function ArrowDownIcon({ size = 16, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M12 5v14M6 13l6 6 6-6" />
    </svg>
  )
}

export function SparkIcon({ size = 18, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M12 3.5 13.6 8a2 2 0 0 0 1.2 1.2l4.5 1.6-4.5 1.6A2 2 0 0 0 13.6 14L12 18.5 10.4 14a2 2 0 0 0-1.2-1.2L4.7 11.2l4.5-1.6A2 2 0 0 0 10.4 8z" />
      <path d="M19 3v3M17.5 4.5h3" />
    </svg>
  )
}

export function CheckIcon({ size = 16, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M4.5 12.5 9.5 17.5 19.5 6.5" />
    </svg>
  )
}

export function AlertIcon({ size = 18, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <path d="M12 3.8 21 19.5H3z" />
      <path d="M12 10v4M12 17h.01" />
    </svg>
  )
}

export function InfoIcon({ size = 18, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </svg>
  )
}

export function RulerIcon({ size = 18, className }: IconProps) {
  return (
    <svg {...stroke(size, className)}>
      <rect x="3" y="8" width="18" height="8" rx="2" />
      <path d="M7 8v3M11 8v4M15 8v3M19 8v4" />
    </svg>
  )
}
