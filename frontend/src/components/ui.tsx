import type { ReactNode } from 'react'

export function Card({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={`card ${className}`}>{children}</section>
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <header className="card-header">
      <div>
        <h2 className="card-title">{title}</h2>
        {subtitle && <p className="card-subtitle">{subtitle}</p>}
      </div>
      {action}
    </header>
  )
}

export function StatTile({
  label,
  value,
  hint,
  tone = 'neutral',
  icon,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: 'neutral' | 'good' | 'warn' | 'bad'
  icon?: ReactNode
}) {
  return (
    <div className={`stat-tile tone-${tone}`}>
      <div className="stat-label">
        {icon}
        {label}
      </div>
      <div className="stat-value">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  )
}

export function Badge({
  children,
  tone = 'neutral',
}: {
  children: ReactNode
  tone?: 'neutral' | 'good' | 'warn' | 'bad' | 'info'
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}

export function Button({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  disabled,
  fullWidth,
}: {
  children: ReactNode
  onClick?: () => void
  type?: 'button' | 'submit'
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  disabled?: boolean
  fullWidth?: boolean
}) {
  return (
    <button
      type={type}
      className={`btn btn-${variant}${fullWidth ? ' btn-block' : ''}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  )
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="spinner-wrap" role="status">
      <span className="spinner" />
      {label && <span className="spinner-label">{label}</span>}
    </div>
  )
}

export function ProgressBar({ value, tone }: { value: number; tone?: string }) {
  const pct = Math.max(0, Math.min(1, value)) * 100
  return (
    <div className="progress">
      <div
        className={`progress-fill${tone ? ` progress-${tone}` : ''}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export function Field({
  label,
  value,
  onChange,
  min,
  max,
  step,
  unit,
  hint,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  min: number
  max: number
  step?: number
  unit?: string
  hint?: string
}) {
  return (
    <label className="field">
      <span className="field-label">
        {label}
        {unit && <span className="field-unit">{unit}</span>}
      </span>
      <input
        className="input"
        type="number"
        inputMode="decimal"
        value={Number.isFinite(value) ? value : ''}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(e.target.value === '' ? NaN : Number(e.target.value))}
      />
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}

export function ToggleField({
  label,
  value,
  onChange,
}: {
  label: string
  value: number
  onChange: (v: number) => void
}) {
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      <div className="segmented" role="group" aria-label={label}>
        <button
          type="button"
          className={`segment${value === 0 ? ' active' : ''}`}
          onClick={() => onChange(0)}
        >
          No
        </button>
        <button
          type="button"
          className={`segment${value === 1 ? ' active' : ''}`}
          onClick={() => onChange(1)}
        >
          Yes
        </button>
      </div>
    </div>
  )
}

export function SelectField({
  label,
  value,
  onChange,
  options,
  hint,
}: {
  label: string
  value: number | string
  onChange: (v: number | string) => void
  options: { value: number | string; label: string }[]
  hint?: string
}) {
  return (
    <label className="field">
      <span className="field-label">
        {label}
      </span>
      <select
        className="input"
        value={value === '' ? '' : value}
        onChange={(e) => onChange(e.target.value === '' ? '' : (isNaN(Number(e.target.value)) ? e.target.value : Number(e.target.value)))}
      >
        <option value="">Select…</option>
        {options.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}

export function Modal({
  open,
  onClose,
  title,
  children,
  size = 'md',
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
}) {
  if (!open) return null

  const sizeClasses = { sm: 'max-w-[360px]', md: 'max-w-[500px]', lg: 'max-w-[640px]', xl: 'max-w-[800px]' }

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className={`modal ${sizeClasses[size]}`} onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 id="modal-title" className="modal-title">{title}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
        <div className="modal-body">
          {children}
        </div>
      </div>
    </div>
  )
}
