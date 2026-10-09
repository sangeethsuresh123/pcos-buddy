import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, storage, type Analytics } from '../api'
import LineChart from '../components/LineChart'
import { ArrowDownIcon, ArrowUpIcon, ChatIcon, PlusIcon, PulseIcon, SparkIcon, TrendIcon } from '../components/icons'
import { Badge, Button, Card, CardHeader, Spinner } from '../components/ui'

const TIPS = [
  'A 150-minute weekly mix of aerobic and resistance exercise improves insulin sensitivity in PCOS.',
  'Local, low-glycemic foods (millets, oats, dal) steady blood sugar better than refined carbs.',
  'Irregular cycles are one of the clearest early signals — track them in a cycle diary.',
  'Vitamin D deficiency is common in PCOS; ask your clinician to check your level.',
  'Poor sleep raises cravings and insulin resistance — aim for 7-8 hours nightly.',
  'Even 5-10% weight loss can restore ovulation and ease hormonal symptoms.',
  'Stress management (walks, breathing, therapy) lowers cortisol and helps cycle regularity.',
  'Omega-3 rich foods such as fish, walnuts and flaxseed may reduce inflammation.',
]

function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function Home() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const assessment = storage.getLastAssessment()

  useEffect(() => {
    api
      .getAnalytics()
      .then(setAnalytics)
      .catch(() => setAnalytics(null))
      .finally(() => setLoading(false))
  }, [])

  const tip = TIPS[new Date().getDate() % TIPS.length]
  const riskTone =
    assessment?.risk_level === 'high'
      ? 'bad'
      : assessment?.risk_level === 'moderate'
        ? 'warn'
        : 'good'
  const spark = analytics?.series.slice(-14).map((p) => ({ date: p.date, value: p.weight_kg })) ?? []
  const delta = analytics?.delta_30d_kg ?? null

  return (
    <div className="page">
      <Card className="hero">
        <div>
          <p className="hero-greeting">{greeting()}</p>
          <h2 className="hero-title">Your health, tracked</h2>
          <p className="hero-sub">
            {new Date().toLocaleDateString(undefined, {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
            })}
          </p>
        </div>
        <SparkIcon size={40} className="hero-icon" />
      </Card>

      <div className="grid-2">
        <Card>
          <CardHeader
            title="PCOS risk"
            subtitle={
              assessment
                ? `Assessed ${new Date(assessment.assessed_at).toLocaleDateString()}`
                : 'Takes about 2 minutes'
            }
            action={
              assessment ? (
                <Badge tone={riskTone}>{assessment.risk_level} risk</Badge>
              ) : (
                <Badge tone="info">not assessed</Badge>
              )
            }
          />
          {assessment ? (
            <>
              <p className="big-number">
                {(assessment.probability_pcos * 100).toFixed(0)}
                <span className="big-unit">% PCOS likelihood</span>
              </p>
              <p className="muted">{assessment.diagnosis}</p>
            </>
          ) : (
            <p className="muted">
              Answer a few clinical questions to get a likelihood score, risk level and
              personalised recommendations.
            </p>
          )}
          <Link to="/risk" className="card-link">
            <Button variant={assessment ? 'secondary' : 'primary'} fullWidth>
              {assessment ? 'Retake assessment' : 'Start risk check'}
            </Button>
          </Link>
        </Card>

        <Card>
          <CardHeader
            title="Weight"
            subtitle={
              analytics?.height_cm
                ? `Height ${analytics.height_cm} cm`
                : 'Set your height to unlock BMI'
            }
            action={
              analytics?.latest && delta !== null ? (
                <Badge tone={delta > 0.15 ? 'warn' : delta < -0.15 ? 'good' : 'neutral'}>
                  {delta > 0 ? <ArrowUpIcon size={13} /> : <ArrowDownIcon size={13} />}
                  {Math.abs(delta).toFixed(1)} kg / 30d
                </Badge>
              ) : undefined
            }
          />
          {loading ? (
            <Spinner label="Loading…" />
          ) : analytics?.latest ? (
            <>
              <p className="big-number">
                {analytics.latest.weight_kg.toFixed(1)}
                <span className="big-unit">kg</span>
                {analytics.bmi && (
                  <Badge tone={analytics.bmi_category === 'normal' ? 'good' : 'warn'}>
                    BMI {analytics.bmi}
                  </Badge>
                )}
              </p>
              {spark.length > 1 ? (
                <LineChart points={spark} height={90} compact />
              ) : (
                <p className="muted">Log more entries to see your trend.</p>
              )}
            </>
          ) : (
            <p className="muted">
              Log your weight, waist and hip measurements to see trends, BMI and milestones.
            </p>
          )}
          <Link to="/weight" className="card-link">
            <Button variant={analytics?.latest ? 'secondary' : 'primary'} fullWidth>
              <PlusIcon size={16} />
              {analytics?.latest ? 'Open tracker' : 'Log first entry'}
            </Button>
          </Link>
        </Card>
      </div>

      <div className="quick-actions">
        <Link to="/risk" className="quick-action">
          <PulseIcon size={22} />
          <span>Risk check</span>
        </Link>
        <Link to="/weight" className="quick-action">
          <TrendIcon size={22} />
          <span>Log weight</span>
        </Link>
        <Link to="/chat" className="quick-action">
          <ChatIcon size={22} />
          <span>Ask assistant</span>
        </Link>
      </div>

      <Card className="tip-card">
        <CardHeader title="Tip of the day" />
        <p className="tip-text">{tip}</p>
      </Card>

      <p className="disclaimer">
        This app provides educational guidance and screening support — it does not replace
        medical diagnosis or treatment.
      </p>
    </div>
  )
}
