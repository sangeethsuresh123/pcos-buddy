import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type SymptomEntry, type CycleAnalysis } from '../api'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  DropIcon,
  HeartIcon,
  InfoIcon,
  MoonIcon,
  PlusIcon,
  SunIcon,
  TrashIcon,
  AlertIcon,
} from '../components/icons'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Field,
  Modal,
  Spinner,
} from '../components/ui'

const FLOW_LABELS = ['None', 'Spotting', 'Light', 'Medium', 'Heavy']
const FLOW_COLORS = ['transparent', '#fecaca', '#fca5a5', '#ef4444', '#b91c1c']

const SYMPTOM_GROUPS: { title: string; icon: React.ReactNode; fields: { key: string; label: string; max: number; hint?: string }[] }[] = [
  {
    title: 'Period',
    icon: <DropIcon size={18} />,
    fields: [
      { key: 'period_flow', label: 'Flow', max: 4, hint: '0=None, 1=Spotting, 2=Light, 3=Medium, 4=Heavy' },
      { key: 'period_day', label: 'Cycle day', max: 60, hint: 'Day 1 = first day of period' },
      { key: 'cycle_length', label: 'Cycle length', max: 60, hint: 'Total days if known' },
    ],
  },
  {
    title: 'Physical',
    icon: <HeartIcon size={18} />,
    fields: [
      { key: 'abdominal_pain', label: 'Abdominal pain', max: 10 },
      { key: 'breast_tenderness', label: 'Breast tenderness', max: 10 },
      { key: 'bloating', label: 'Bloating', max: 10 },
      { key: 'headache', label: 'Headache', max: 10 },
      { key: 'fatigue', label: 'Fatigue', max: 10 },
      { key: 'acne', label: 'Acne', max: 10 },
      { key: 'hair_loss', label: 'Hair loss', max: 10 },
      { key: 'hirsutism', label: 'Excess hair', max: 10 },
      { key: 'skin_darkening', label: 'Skin darkening', max: 10 },
    ],
  },
  {
    title: 'Mood & Mind',
    icon: <MoonIcon size={18} />,
    fields: [
      { key: 'mood_swings', label: 'Mood swings', max: 10 },
      { key: 'anxiety', label: 'Anxiety', max: 10 },
      { key: 'depression', label: 'Low mood', max: 10 },
      { key: 'irritability', label: 'Irritability', max: 10 },
    ],
  },
  {
    title: 'Lifestyle',
    icon: <SunIcon size={18} />,
    fields: [
      { key: 'exercise_minutes', label: 'Exercise', max: 300, hint: 'Minutes' },
      { key: 'sleep_hours', label: 'Sleep', max: 24, hint: 'Hours' },
      { key: 'stress_level', label: 'Stress', max: 10 },
      { key: 'diet_quality', label: 'Diet quality', max: 10 },
    ],
  },
]

const ALL_SYMPTOM_KEYS = SYMPTOM_GROUPS.flatMap(g => g.fields.map(f => f.key))

function todayISO() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function startOfWeek(date: Date) {
  const d = new Date(date)
  d.setDate(d.getDate() - d.getDay())
  return d
}

export default function Symptoms() {
  const [viewDate, setViewDate] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState<string>(todayISO())
  const [entries, setEntries] = useState<Map<string, SymptomEntry>>(new Map())
  const [analysis, setAnalysis] = useState<CycleAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [formValues, setFormValues] = useState<Record<string, number | string>>({})
  const [activeTab, setActiveTab] = useState(0)

  const load = useCallback(async () => {
    try {
      const [e, a] = await Promise.all([
        api.getEntriesSymptoms(),
        api.getSymptomsAnalysis(),
      ])
      const map = new Map<string, SymptomEntry>()
      e.forEach(entry => map.set(entry.date, entry))
      setEntries(map)
      setAnalysis(a)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const entryForSelected = entries.get(selectedDate)

  useEffect(() => {
    if (entryForSelected) {
      const vals: Record<string, number | string> = { date: selectedDate }
      ALL_SYMPTOM_KEYS.forEach(k => { vals[k] = entryForSelected[k as keyof SymptomEntry] ?? '' })
      setFormValues(vals)
    } else {
      const vals: Record<string, number | string> = { date: selectedDate }
      ALL_SYMPTOM_KEYS.forEach(k => { vals[k] = '' })
      setFormValues(vals)
    }
  }, [selectedDate, entryForSelected])

  const handleChange = (key: string, value: number | string) => {
    setFormValues(prev => ({ ...prev, [key]: value }))
  }

  const saveEntry = async () => {
    setError(null)
    setSaving(true)
    try {
      const payload = { ...formValues }
      Object.keys(payload).forEach(k => {
        if (payload[k] === '') delete payload[k]
      })
      await api.addSymptomEntry(payload as SymptomEntry)
      setNotice(`Saved ${selectedDate}`)
      await load()
      setModalOpen(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save')
    } finally {
      setSaving(false)
    }
  }

  const deleteEntry = async (dateStr: string) => {
    const entry = entries.get(dateStr)
    if (!entry || !entry.id) return
    setError(null)
    try {
      await api.deleteSymptomEntry(entry.id)
      setNotice(`Deleted ${dateStr}`)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete')
    }
  }

  const openModal = (dateStr: string) => {
    setSelectedDate(dateStr)
    setModalOpen(true)
  }

  const prevMonth = () => setViewDate(d => new Date(d.getFullYear(), d.getMonth() - 1, 1))
  const nextMonth = () => setViewDate(d => new Date(d.getFullYear(), d.getMonth() + 1, 1))

  const monthDays = useMemo(() => {
    const year = viewDate.getFullYear()
    const month = viewDate.getMonth()
    const firstDay = new Date(year, month, 1)
    const start = startOfWeek(firstDay)
    const days: (Date | null)[] = []
    for (let i = 0; i < 42; i++) {
      const d = new Date(start)
      d.setDate(start.getDate() + i)
      days.push(d.getMonth() === month ? d : null)
    }
    return days
  }, [viewDate])

  const monthName = viewDate.toLocaleString('default', { month: 'long', year: 'numeric' })

  const phaseColors: Record<string, string> = {
    menstrual: '#ef4444',
    follicular: '#22c55e',
    luteal: '#f59e0b',
    'late-luteal': '#f97316',
    'pre-period': '#a855f7',
  }

  if (loading) {
    return <div className="page"><Spinner label="Loading symptom tracker…" /></div>
  }

  const phase = analysis?.phase ?? 'unknown'
  const nextPeriod = analysis?.next_period_estimate
  const avgCycle = analysis?.avg_cycle_length
  const avgPeriod = analysis?.avg_period_length

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

      <Card>
        <CardHeader
          title="Symptom tracker"
          subtitle="Log daily symptoms & period — see cycle patterns"
          action={
            <Badge tone={phaseColors[phase] as any}><span className="phase-badge">{phase}</span></Badge>
          }
        />
        <div className="symptoms-header">
          <div className="calendar-nav">
            <Button variant="ghost" onClick={prevMonth}><ChevronLeftIcon size={18} /></Button>
            <span className="calendar-title">{monthName}</span>
            <Button variant="ghost" onClick={nextMonth}><ChevronRightIcon size={18} /></Button>
          </div>
          <div className="cycle-summary">
            {avgCycle && <span><strong>{avgCycle}</strong> avg cycle</span>}
            {avgPeriod && <span><strong>{avgPeriod}</strong> avg period</span>}
            {nextPeriod && <span>Next ≈ <strong>{new Date(nextPeriod).toLocaleDateString()}</strong></span>}
          </div>
        </div>
        <div className="calendar-grid" role="grid" aria-label="Symptom calendar">
          {['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(d => (
            <div key={d} className="calendar-day-header">{d}</div>
          ))}
          {monthDays.map((d, i) => {
            if (!d) return <div key={i} className="calendar-day empty" />
            const iso = d.toISOString().split('T')[0]
            const entry = entries.get(iso)
            const isToday = iso === todayISO()
            const isSelected = iso === selectedDate
            const flow = entry?.period_flow ?? 0
            return (
              <button
                key={i}
                className={`calendar-day${isToday ? ' today' : ''}${isSelected ? ' selected' : ''}${flow > 0 ? ' has-flow' : ''}${entry ? ' has-entry' : ''}`}
                onClick={() => openModal(iso)}
                style={flow > 0 ? { backgroundColor: FLOW_COLORS[flow] } : undefined}
                aria-label={`${d.toLocaleDateString()}${entry ? ', has entry' : ''}${flow > 0 ? `, flow: ${FLOW_LABELS[flow]}` : ''}`}
              >
                <span className="day-number">{d.getDate()}</span>
                {flow > 0 && <span className="flow-dot" aria-hidden="true" />}
                {entry && <span className="entry-dot" aria-hidden="true" />}
              </button>
            )
          })}
        </div>
      </Card>

      <Card>
        <CardHeader title="Cycle insights" subtitle="Patterns detected from your logs" />
        {analysis && analysis.symptom_patterns && Object.keys(analysis.symptom_patterns).length > 0 ? (
          <div className="insight-grid">
            {Object.entries(analysis.symptom_patterns).map(([phase, symptoms]) => (
              <div key={phase} className="insight-card">
                <h4 className="insight-phase">{phase.charAt(0).toUpperCase() + phase.slice(1)}</h4>
                <ul>
                  {(symptoms as Array<{symptom: string; frequency: number}>).slice(0, 3).map((s, i) => (
                    <li key={i}>
                      <span className="symptom-name">{s.symptom.replace(/_/g, ' ')}</span>
                      <span className="symptom-freq">{s.frequency}x</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">Log at least 2 periods to see cycle patterns.</p>
        )}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={`Log symptoms — ${selectedDate}`} size="lg">
        <form onSubmit={e => { e.preventDefault(); void saveEntry() }}>
          <div className="form-tabs">
            {SYMPTOM_GROUPS.map((group, gi) => (
              <button type="button" key={group.title} className={`form-tab${gi === activeTab ? ' active' : ''}`} onClick={() => setActiveTab(gi)}>
                {group.icon}
                <span>{group.title}</span>
              </button>
            ))}
          </div>
          <div className="form-panels">
            {SYMPTOM_GROUPS.map((group, gi) => (
              <div key={group.title} className={`form-panel${gi === activeTab ? ' active' : ''}`}>
                <div className="field-grid">
                  {group.fields.map(f => (
                    <Field
                      key={f.key}
                      label={f.label}
                      hint={f.hint}
                      min={0}
                      max={f.max}
                      step={f.key === 'sleep_hours' ? 0.5 : 1}
                      value={formValues[f.key] === '' ? NaN : Number(formValues[f.key])}
                      onChange={v => handleChange(f.key, v ?? '')}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="field">
            <label className="field-label">Notes</label>
            <textarea
              className="input"
              value={formValues.notes as string}
              onChange={e => handleChange('notes', e.target.value)}
              maxLength={500}
              rows={3}
              placeholder="Optional notes…"
            />
          </div>
          <div className="modal-actions">
            {entryForSelected && entryForSelected.id && (
              <Button variant="danger" type="button" onClick={() => deleteEntry(selectedDate)}>
                <TrashIcon size={16} />
                Delete entry
              </Button>
            )}
            <Button type="submit" disabled={saving} variant="primary">
              <PlusIcon size={16} />
              {saving ? 'Saving…' : entryForSelected ? 'Update entry' : 'Save entry'}
            </Button>
          </div>
        </form>
      </Modal>

      <p className="disclaimer">
        This tracker helps you spot patterns. Share it with your clinician for personalized care.
      </p>
    </div>
  )
}