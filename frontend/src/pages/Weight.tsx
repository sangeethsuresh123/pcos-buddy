import { useCallback, useEffect, useState } from 'react'
import { api, type Analytics, type Entry } from '../api'
import LineChart from '../components/LineChart'
import {
  AlertIcon,
  ArrowDownIcon,
  ArrowUpIcon,
  CheckIcon,
  InfoIcon,
  PlusIcon,
  RulerIcon,
  TrashIcon,
} from '../components/icons'
import { Badge, Button, Card, CardHeader, ProgressBar, Spinner, StatTile } from '../components/ui'

const CATEGORY_TONE: Record<string, 'good' | 'warn' | 'bad'> = {
  normal: 'good',
  underweight: 'warn',
  overweight: 'warn',
  obese: 'bad',
}

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function Weight() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [entries, setEntries] = useState<Entry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [height, setHeight] = useState('')
  const [date, setDate] = useState(today())
  const [weight, setWeight] = useState('')
  const [waist, setWaist] = useState('')
  const [hip, setHip] = useState('')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)

  const reload = useCallback(async () => {
    try {
      const [a, e] = await Promise.all([api.getAnalytics(), api.getEntries()])
      setAnalytics(a)
      setEntries(e)
      if (a.height_cm) setHeight(String(a.height_cm))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const saveHeight = async () => {
    const value = Number(height)
    if (!Number.isFinite(value) || value < 120 || value > 230) {
      setError('Enter a height between 120 and 230 cm.')
      return
    }
    setError(null)
    try {
      await api.setProfile(value)
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save height')
    }
  }

  const saveEntry = async () => {
    const w = Number(weight)
    if (!Number.isFinite(w) || w < 25 || w > 400) {
      setError('Weight must be between 25 and 400 kg.')
      return
    }
    const payload: Entry = { date, weight_kg: w }
    if (waist.trim()) payload.waist_cm = Number(waist)
    if (hip.trim()) payload.hip_cm = Number(hip)
    if (notes.trim()) payload.notes = notes.trim()

    setSaving(true)
    setError(null)
    try {
      await api.addEntry(payload)
      setWeight('')
      setWaist('')
      setHip('')
      setNotes('')
      setNotice(`Entry for ${date} saved.`)
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save entry')
    } finally {
      setSaving(false)
    }
  }

  const removeEntry = async (id: number) => {
    setError(null)
    try {
      await api.deleteEntry(id)
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete entry')
    }
  }

  if (loading) {
    return (
      <div className="page">
        <Spinner label="Loading your tracker…" />
      </div>
    )
  }

  const trendIcon =
    analytics?.trend_direction === 'increasing' ? (
      <ArrowUpIcon size={14} />
    ) : analytics?.trend_direction === 'decreasing' ? (
      <ArrowDownIcon size={14} />
    ) : null
  const delta = analytics?.delta_30d_kg ?? null
  const series = analytics?.series.map((p) => ({ date: p.date, value: p.weight_kg })) ?? []

  return (
    <div className="page">
      {error && (
        <div className="alert alert-error" role="alert">
          <AlertIcon size={17} />
          <span>{error}</span>
        </div>
      )}
      {notice && (
        <div className="alert alert-info" role="status">
          <InfoIcon size={17} />
          <span>{notice}</span>
        </div>
      )}

      {!analytics?.height_cm && (
        <Card>
          <CardHeader
            title="Set your height"
            subtitle="Needed for BMI and waist-to-height analysis"
            action={<RulerIcon size={20} />}
          />
          <div className="inline-form">
            <input
              className="input"
              type="number"
              inputMode="decimal"
              placeholder="Height in cm"
              value={height}
              min={120}
              max={230}
              onChange={(e) => setHeight(e.target.value)}
            />
            <Button onClick={() => void saveHeight()}>Save height</Button>
          </div>
        </Card>
      )}

      <div className="stat-grid">
        <StatTile
          label="Latest weight"
          value={
            analytics?.latest ? (
              <>
                {analytics.latest.weight_kg.toFixed(1)}
                <span className="stat-unit">kg</span>
              </>
            ) : (
              '—'
            )
          }
          hint={analytics?.latest ? analytics.latest.date : 'No entries yet'}
        />
        <StatTile
          label="BMI"
          value={analytics?.bmi ?? '—'}
          tone={analytics?.bmi_category ? CATEGORY_TONE[analytics.bmi_category] : 'neutral'}
          hint={
            analytics?.bmi_category
              ? analytics.bmi_category.charAt(0).toUpperCase() + analytics.bmi_category.slice(1)
              : analytics?.height_cm
                ? 'Add weight entry'
                : 'Set height first'
          }
        />
        <StatTile
          label="30-day change"
          value={
            delta === null ? (
              '—'
            ) : (
              <>
                {delta > 0 ? '+' : ''}
                {delta.toFixed(1)}
                <span className="stat-unit">kg</span>
              </>
            )
          }
          tone={delta === null ? 'neutral' : delta > 0.15 ? 'warn' : delta < -0.15 ? 'good' : 'neutral'}
          hint={analytics?.pace_kg_per_week !== null && analytics?.pace_kg_per_week !== undefined
            ? `${analytics.pace_kg_per_week > 0 ? '+' : ''}${analytics.pace_kg_per_week} kg/week`
            : undefined}
        />
        <StatTile
          label="Trend (90d)"
          value={
            analytics?.trend_slope_kg_per_month === null ||
            analytics?.trend_slope_kg_per_month === undefined ? (
              '—'
            ) : (
              <>
                {analytics.trend_slope_kg_per_month > 0 ? '+' : ''}
                {analytics.trend_slope_kg_per_month}
                <span className="stat-unit">kg/mo</span>
              </>
            )
          }
          tone={
            analytics?.trend_direction === 'increasing'
              ? 'warn'
              : analytics?.trend_direction === 'decreasing'
                ? 'good'
                : 'neutral'
          }
          hint={
            <span className="hint-with-icon">
              {trendIcon}
              {analytics?.trend_direction ?? 'stable'}
            </span>
          }
        />
      </div>

      <Card>
        <CardHeader
          title="Weight trend"
          subtitle={
            analytics && analytics.entry_count > 0
              ? `${analytics.entry_count} entries`
              : 'Your chart appears after the first log'
          }
          action={
            analytics?.waist_height_ratio ? (
              <Badge tone={analytics.waist_height_ratio >= 0.5 ? 'warn' : 'good'}>
                WHtR {analytics.waist_height_ratio}
              </Badge>
            ) : analytics?.waist_hip_ratio ? (
              <Badge tone={analytics.waist_hip_ratio > 0.85 ? 'warn' : 'good'}>
                WHR {analytics.waist_hip_ratio}
              </Badge>
            ) : undefined
          }
        />
        {series.length > 0 ? (
          <LineChart points={series} height={220} unit=" kg" />
        ) : (
          <p className="muted">Log your first entry below to start the chart.</p>
        )}
      </Card>

      {analytics?.milestones && (
        <Card>
          <CardHeader
            title="Milestones"
            subtitle={
              analytics.baseline
                ? `Since ${analytics.baseline.date} (${analytics.baseline.weight_kg.toFixed(1)} kg)`
                : undefined
            }
          />
          <div className="milestone-list">
            {[
              { key: 'five_percent', label: '5% weight loss' },
              { key: 'ten_percent', label: '10% weight loss' },
            ].map(({ key, label }) => {
              const m = analytics.milestones![key]
              if (!m) return null
              return (
                <div className="milestone" key={key}>
                  <div className="milestone-head">
                    <span>
                      {label}
                      {m.achieved && <CheckIcon size={14} className="milestone-check" />}
                    </span>
                    <span className="muted">
                      {m.loss_required_kg} kg · target {m.target_weight_kg} kg
                    </span>
                  </div>
                  <ProgressBar value={m.progress} tone={m.achieved ? 'good' : ''} />
                  <span className="milestone-progress">{Math.round(m.progress * 100)}%</span>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {analytics && analytics.flags.length > 0 && (
        <Card>
          <CardHeader title="Insights" subtitle="Based on your recent entries" />
          <ul className="flag-list">
            {analytics.flags.map((flag) => (
              <li key={flag.type + flag.message} className={`flag flag-${flag.severity}`}>
                {flag.severity === 'positive' ? (
                  <CheckIcon size={16} />
                ) : flag.severity === 'warning' ? (
                  <AlertIcon size={16} />
                ) : (
                  <InfoIcon size={16} />
                )}
                <span>{flag.message}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card>
        <CardHeader title="Log an entry" subtitle="One entry per day — saving again updates it" />
        <div className="field-grid">
          <label className="field">
            <span className="field-label">Date</span>
            <input
              className="input"
              type="date"
              value={date}
              max={today()}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
          <label className="field">
            <span className="field-label">
              Weight<span className="field-unit">kg</span>
            </span>
            <input
              className="input"
              type="number"
              inputMode="decimal"
              step="0.1"
              placeholder="e.g. 68.4"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
            />
          </label>
          <label className="field">
            <span className="field-label">
              Waist <span className="field-unit">cm, optional</span>
            </span>
            <input
              className="input"
              type="number"
              inputMode="decimal"
              step="0.1"
              placeholder="e.g. 84"
              value={waist}
              onChange={(e) => setWaist(e.target.value)}
            />
          </label>
          <label className="field">
            <span className="field-label">
              Hip <span className="field-unit">cm, optional</span>
            </span>
            <input
              className="input"
              type="number"
              inputMode="decimal"
              step="0.1"
              placeholder="e.g. 98"
              value={hip}
              onChange={(e) => setHip(e.target.value)}
            />
          </label>
          <label className="field field-span">
            <span className="field-label">Notes (optional)</span>
            <input
              className="input"
              type="text"
              maxLength={200}
              placeholder="e.g. weighed in the morning, post-workout"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </label>
        </div>
        <Button onClick={() => void saveEntry()} disabled={saving} fullWidth>
          <PlusIcon size={16} />
          {saving ? 'Saving…' : 'Save entry'}
        </Button>
      </Card>

      {entries.length > 0 && (
        <Card>
          <CardHeader title="History" subtitle={`${entries.length} entries`} />
          <ul className="entry-list">
            {[...entries].reverse().map((entry) => (
              <li key={entry.id} className="entry-row">
                <div>
                  <span className="entry-date">{entry.date}</span>
                  <span className="entry-weight">{entry.weight_kg.toFixed(1)} kg</span>
                  {(entry.waist_cm || entry.hip_cm) && (
                    <span className="muted">
                      {entry.waist_cm ? `W ${entry.waist_cm} ` : ''}
                      {entry.hip_cm ? `· H ${entry.hip_cm}` : ''}
                    </span>
                  )}
                  {entry.notes && <span className="entry-notes">{entry.notes}</span>}
                </div>
                <button
                  className="icon-btn"
                  aria-label={`Delete entry from ${entry.date}`}
                  onClick={() => entry.id && void removeEntry(entry.id)}
                >
                  <TrashIcon />
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
