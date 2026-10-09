export type Entry = {
  id?: number
  date: string
  weight_kg: number
  waist_cm?: number | null
  hip_cm?: number | null
  notes?: string | null
}

export type Milestone = {
  target_weight_kg: number
  loss_required_kg: number
  progress: number
  achieved: boolean
}

export type Flag = {
  type: string
  severity: 'positive' | 'warning' | 'info'
  message: string
}

export type Analytics = {
  entry_count: number
  latest: Entry | null
  baseline: Entry | null
  height_cm: number | null
  bmi: number | null
  bmi_category: string | null
  waist_height_ratio: number | null
  waist_hip_ratio: number | null
  delta_30d_kg: number | null
  delta_90d_kg: number | null
  trend_slope_kg_per_month: number | null
  trend_direction: 'increasing' | 'decreasing' | 'stable'
  pace_kg_per_week: number | null
  milestones: Record<string, Milestone> | null
  flags: Flag[]
  series: { date: string; weight_kg: number; bmi: number | null }[]
}

export type PredictionResult = {
  prediction: number
  diagnosis: string
  probability_pcos: number
  probability_no_pcos: number
  risk_level: 'low' | 'moderate' | 'high'
  recommendations: string[]
}

export type ChatMessage = {
  response: string
  session_id: string
  sources: string[]
}

export type RiskAssessment = PredictionResult & { assessed_at: string }

export type User = {
  id: number
  email: string
  created_at: string
}

export type AuthConfig = {
  google_enabled: boolean
  google_login_url: string | null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    if (res.status === 401) window.dispatchEvent(new Event('auth:unauthorized'))
    let detail = res.statusText
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (body.detail) detail = JSON.stringify(body.detail)
    } catch {
      // keep statusText
    }
    throw new Error(detail)
  }
  return (await res.json()) as T
}

export const api = {
  register: (email: string, password: string) =>
    request<User>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<User>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  logout: () => request<{ message: string }>('/api/auth/logout', { method: 'POST' }),

  me: () => request<User>('/api/auth/me'),

  authConfig: () => request<AuthConfig>('/api/auth/config'),

  getProfile: () => request<{ height_cm: number | null }>('/api/weight/profile'),

  setProfile: (height_cm: number) =>
    request<{ height_cm: number | null }>('/api/weight/profile', {
      method: 'PUT',
      body: JSON.stringify({ height_cm }),
    }),

  getEntries: () => request<Entry[]>('/api/weight/entries'),

  addEntry: (entry: Entry) =>
    request<Entry>('/api/weight/entries', {
      method: 'POST',
      body: JSON.stringify(entry),
    }),

  deleteEntry: (id: number) =>
    request<{ deleted: boolean }>(`/api/weight/entries/${id}`, { method: 'DELETE' }),

  getAnalytics: () => request<Analytics>('/api/weight/analytics'),

  predict: (features: Record<string, number>) =>
    request<PredictionResult>('/api/ml/predict', {
      method: 'POST',
      body: JSON.stringify(features),
    }),

  chat: (message: string, sessionId: string | null) =>
    request<ChatMessage>('/api/chat/', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId, use_rag: true }),
    }),
}

export const storage = {
  getLastAssessment(): RiskAssessment | null {
    try {
      const raw = localStorage.getItem('pcos.lastAssessment')
      return raw ? (JSON.parse(raw) as RiskAssessment) : null
    } catch {
      return null
    }
  },
  setLastAssessment(result: PredictionResult) {
    const withDate: RiskAssessment = {
      ...result,
      assessed_at: new Date().toISOString(),
    }
    localStorage.setItem('pcos.lastAssessment', JSON.stringify(withDate))
    return withDate
  },
}
