type Point = { date: string; value: number }

function fmtDate(iso: string) {
  const d = new Date(`${iso}T00:00:00`)
  return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export default function LineChart({
  points,
  height = 200,
  unit = '',
  compact = false,
}: {
  points: Point[]
  height?: number
  unit?: string
  compact?: boolean
}) {
  if (points.length === 0) {
    return <p className="chart-empty">No data yet</p>
  }

  const W = 600
  const H = height
  const pad = compact ? { t: 8, r: 8, b: 8, l: 8 } : { t: 16, r: 14, b: 28, l: 44 }

  const values = points.map((p) => p.value)
  let min = Math.min(...values)
  let max = Math.max(...values)
  if (min === max) {
    min -= 1
    max += 1
  }
  const range = max - min
  min -= range * 0.1
  max += range * 0.1

  const times = points.map((p) => new Date(`${p.date}T00:00:00`).getTime())
  const tMin = Math.min(...times)
  const tMax = Math.max(...times)
  const span = tMax - tMin || 1

  const x = (t: number) => pad.l + ((t - tMin) / span) * (W - pad.l - pad.r)
  const y = (v: number) => pad.t + (1 - (v - min) / (max - min)) * (H - pad.t - pad.b)

  const line = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${x(times[i]).toFixed(1)},${y(p.value).toFixed(1)}`)
    .join(' ')
  const area = `${line} L${x(tMax).toFixed(1)},${(H - pad.b).toFixed(1)} L${x(tMin).toFixed(1)},${(H - pad.b).toFixed(1)} Z`

  const gridValues = [0, 0.5, 1].map((f) => min + f * (max - min))
  const last = points[points.length - 1]

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="Trend chart"
      style={{ height }}
    >
      <defs>
        <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.28" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {!compact &&
        gridValues.map((v) => (
          <g key={v}>
            <line
              x1={pad.l}
              x2={W - pad.r}
              y1={y(v)}
              y2={y(v)}
              className="chart-grid"
              vectorEffect="non-scaling-stroke"
            />
            <text x={pad.l - 6} y={y(v) + 4} className="chart-axis" textAnchor="end">
              {v.toFixed(1)}
            </text>
          </g>
        ))}

      <path d={area} fill="url(#chartFill)" />
      <path
        d={line}
        className="chart-line"
        fill="none"
        vectorEffect="non-scaling-stroke"
      />

      {points.length <= 30 &&
        points.map((p, i) => (
          <circle
            key={p.date}
            cx={x(times[i])}
            cy={y(p.value)}
            r={i === points.length - 1 ? 5 : 3}
            className={i === points.length - 1 ? 'chart-dot last' : 'chart-dot'}
            vectorEffect="non-scaling-stroke"
          />
        ))}

      {!compact && (
        <>
          <text x={pad.l} y={H - 8} className="chart-axis">
            {fmtDate(points[0].date)}
          </text>
          <text x={W - pad.r} y={H - 8} className="chart-axis" textAnchor="end">
            {fmtDate(last.date)}
          </text>
          <text
            x={x(times[times.length - 1]) - 8}
            y={y(last.value) - 10}
            className="chart-value"
            textAnchor="end"
          >
            {last.value.toFixed(1)}
            {unit}
          </text>
        </>
      )}
    </svg>
  )
}
