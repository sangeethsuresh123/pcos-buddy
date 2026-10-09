import { useState } from 'react'
import { api, storage, type RiskAssessment } from '../api'
import { AlertIcon, CheckIcon } from '../components/icons'
import { Badge, Button, Card, CardHeader, Field, Spinner, ToggleField } from '../components/ui'

type NumField = {
  key: string
  label: string
  min: number
  max: number
  step?: number
  unit?: string
  hint?: string
}

const GROUPS: { title: string; description: string; fields: NumField[] }[] = [
  {
    title: 'About you',
    description: 'Basic vitals and history',
    fields: [
      { key: 'age', label: 'Age', min: 10, max: 60, unit: 'yrs' },
      { key: 'blood_group', label: 'Blood group code', min: 1, max: 20, hint: 'As coded in your clinical record (1-20)' },
      { key: 'pulse_rate', label: 'Pulse rate', min: 40, max: 150, unit: 'bpm' },
      { key: 'hb', label: 'Haemoglobin', min: 5, max: 20, step: 0.1, unit: 'g/dl' },
      { key: 'marriage_status', label: 'Marriage status', min: 0, max: 40, unit: 'yrs' },
    ],
  },
  {
    title: 'Menstrual cycle',
    description: 'Cycle pattern over recent months',
    fields: [
      { key: 'cycle_ri', label: 'Cycle (R/I)', min: 0, max: 5, hint: 'Regular/irregular code from your record' },
      { key: 'cycle_length', label: 'Cycle length', min: 1, max: 120, unit: 'days' },
    ],
  },
  {
    title: 'Hormones & blood work',
    description: 'Values from your latest lab report',
    fields: [
      { key: 'i_beta_hcg', label: 'I beta-HCG', min: 0, max: 1000, step: 0.01, unit: 'mIU/mL' },
      { key: 'ii_beta_hcg', label: 'II beta-HCG', min: 0, max: 1000, step: 0.01, unit: 'mIU/mL' },
      { key: 'fsh', label: 'FSH', min: 0, max: 50, step: 0.01, unit: 'mIU/mL' },
      { key: 'tsh', label: 'TSH', min: 0, max: 50, step: 0.01, unit: 'mIU/L' },
      { key: 'prl', label: 'Prolactin (PRL)', min: 0, max: 150, step: 0.01, unit: 'ng/mL' },
      { key: 'vit_d3', label: 'Vitamin D3', min: 0, max: 100, step: 0.1, unit: 'ng/mL' },
      { key: 'prg', label: 'Progesterone (PRG)', min: 0, max: 60, step: 0.01, unit: 'ng/mL' },
      { key: 'rbs', label: 'Random blood sugar', min: 30, max: 400, unit: 'mg/dl' },
    ],
  },
  {
    title: 'Body measurements',
    description: 'From your measurements or scan',
    fields: [
      { key: 'waist_hip_ratio', label: 'Waist : hip ratio', min: 0.5, max: 1.5, step: 0.01 },
    ],
  },
  {
    title: 'Ultrasound',
    description: 'Follicle counts per ovary',
    fields: [
      { key: 'follicle_no_l', label: 'Follicle count (left)', min: 0, max: 50 },
      { key: 'follicle_no_r', label: 'Follicle count (right)', min: 0, max: 50 },
    ],
  },
]

const BINARY: { key: string; label: string }[] = [
  { key: 'weight_gain', label: 'Unexplained weight gain' },
  { key: 'hair_growth', label: 'Excess hair growth (hirsutism)' },
  { key: 'skin_darkening', label: 'Skin darkening' },
  { key: 'hair_loss', label: 'Hair loss / thinning' },
  { key: 'reg_exercise', label: 'Regular exercise' },
]

const DEFAULTS: Record<string, number> = {
  age: 26,
  blood_group: 11,
  pulse_rate: 72,
  hb: 12.5,
  marriage_status: 0,
  cycle_ri: 2,
  cycle_length: 30,
  i_beta_hcg: 2,
  ii_beta_hcg: 180,
  fsh: 5.7,
  tsh: 2,
  prl: 22,
  vit_d3: 20,
  prg: 0.5,
  rbs: 100,
  waist_hip_ratio: 0.88,
  follicle_no_l: 8,
  follicle_no_r: 8,
  weight_gain: 0,
  hair_growth: 0,
  skin_darkening: 0,
  hair_loss: 0,
  reg_exercise: 0,
}

export default function Risk() {
  const [values, setValues] = useState<Record<string, number>>({ ...DEFAULTS })
  const [result, setResult] = useState<RiskAssessment | null>(storage.getLastAssessment())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = (key: string, v: number) => setValues((prev) => ({ ...prev, [key]: v }))

  const submit = async () => {
    setError(null)
    const missing = Object.entries(values).filter(([, v]) => !Number.isFinite(v))
    if (missing.length > 0) {
      setError('Please fill in every field before running the assessment.')
      return
    }
    setLoading(true)
    try {
      const res = await api.predict(values)
      setResult(storage.setLastAssessment(res))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Assessment failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const tone =
    result?.risk_level === 'high' ? 'bad' : result?.risk_level === 'moderate' ? 'warn' : 'good'

  return (
    <div className="page">
      {result && (
        <Card className="result-card">
          <CardHeader
            title="Your result"
            subtitle={
              result.assessed_at
                ? new Date(result.assessed_at).toLocaleString()
                : 'Previous assessment'
            }
            action={<Badge tone={tone}>{result.risk_level} risk</Badge>}
          />
          <p className="big-number">
            {(result.probability_pcos * 100).toFixed(0)}
            <span className="big-unit">% likelihood of PCOS</span>
          </p>
          <div className="gauge" aria-hidden>
            <div
              className={`gauge-fill tone-${tone}`}
              style={{ width: `${Math.round(result.probability_pcos * 100)}%` }}
            />
          </div>
          <p className="result-diagnosis">{result.diagnosis}</p>
          <ul className="recommendations">
            {result.recommendations.map((rec) => (
              <li key={rec}>
                <CheckIcon size={15} />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {error && (
        <div className="alert alert-error" role="alert">
          <AlertIcon size={17} />
          <span>{error}</span>
        </div>
      )}

      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault()
          void submit()
        }}
      >
        {GROUPS.map((group) => (
          <Card key={group.title}>
            <CardHeader title={group.title} subtitle={group.description} />
            <div className="field-grid">
              {group.fields.map((f) => (
                <Field
                  key={f.key}
                  label={f.label}
                  unit={f.unit}
                  hint={f.hint}
                  min={f.min}
                  max={f.max}
                  step={f.step}
                  value={values[f.key]}
                  onChange={(v) => set(f.key, v)}
                />
              ))}
            </div>
          </Card>
        ))}

        <Card>
          <CardHeader title="Symptoms" subtitle="Select what applies to you today" />
          <div className="field-grid">
            {BINARY.map((f) => (
              <ToggleField
                key={f.key}
                label={f.label}
                value={values[f.key]}
                onChange={(v) => set(f.key, v)}
              />
            ))}
          </div>
        </Card>

        <div className="form-actions">
          <Button type="submit" variant="primary" disabled={loading} fullWidth>
            {loading ? 'Analysing…' : 'Run assessment'}
          </Button>
          <Button
            variant="ghost"
            onClick={() => setValues({ ...DEFAULTS })}
            disabled={loading}
            fullWidth
          >
            Reset to defaults
          </Button>
        </div>
        {loading && <Spinner label="Running the model on your inputs…" />}
      </form>

      <p className="disclaimer">
        The score is produced by a Gradient Boosting model trained on clinical PCOS data and is
        for screening support only.
      </p>
    </div>
  )
}
