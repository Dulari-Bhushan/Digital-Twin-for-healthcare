import { useMemo } from 'react'
import { fmtDT, useWidth } from '../utils'

const clamp = (v) => Math.min(400, Math.max(40, v))

/**
 * Glucose over time with the twin's forecast fan drawn at the replay cursor.
 * Past is solid; the not-yet-replayed future is faded so forecast and reality can be compared.
 */
export default function GlucoseChart({ series, cursor, height = 300 }) {
  const [ref, W] = useWidth()
  const H = height
  const pad = { l: 44, r: 56, t: 14, b: 30 }
  const iw = W - pad.l - pad.r
  const ih = H - pad.t - pad.b
  const g = series.glucose
  const n = g.length
  const FUT = 36
  const ymax = Math.max(260, Math.ceil(Math.max(...g) / 50) * 50)
  const ymin = 40
  const x = (i) => pad.l + (i / (n - 1 + FUT)) * iw
  const y = (v) => pad.t + ih - ((clamp(v) - ymin) / (ymax - ymin)) * ih

  const fcIndex = useMemo(() => {
    const m = new Map()
    series.forecast.t.forEach((t, k) => m.set(t - series.t0, k))
    return m
  }, [series])

  const path = (from, to) => {
    let d = ''
    for (let i = from; i <= to; i++) d += `${i === from ? 'M' : 'L'}${x(i).toFixed(1)},${y(g[i]).toFixed(1)}`
    return d
  }
  const k = fcIndex.get(cursor)
  const fan = useMemo(() => {
    if (k === undefined) return null
    const q = series.forecast.q[k]
    const now = g[cursor]
    const steps = [6, 12, 24]
    const pts = steps.map((s, h) => ({ i: cursor + s, lo: now + q[h][0], md: now + q[h][1], hi: now + q[h][2] }))
    return { now, pts }
  }, [k, cursor, series])

  const ticks = []
  for (let i = 0; i < n; i += 144) ticks.push(i)
  const yt = [50, 70, 100, 150, 180, 250, 300, 350].filter((v) => v <= ymax)

  return (
    <div ref={ref} style={{ width: '100%', minWidth: 0, overflow: 'hidden' }}>
      <svg width={W} height={H} role="img" aria-label="Glucose over time with forecast">
        <rect x={pad.l} y={y(180)} width={iw} height={y(70) - y(180)} fill="var(--range)" />
        {yt.map((v) => (
          <g key={v}>
            <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="var(--border)" strokeDasharray={v === 70 || v === 180 ? '4 3' : '1 4'} />
            <text x={pad.l - 6} y={y(v) + 4} textAnchor="end" fontSize="11" fill="var(--muted)">{v}</text>
          </g>
        ))}
        {ticks.map((i) => (
          <g key={i}>
            <line x1={x(i)} x2={x(i)} y1={pad.t} y2={H - pad.b} stroke="var(--border)" strokeDasharray="1 4" />
            <text x={x(i)} y={H - 10} fontSize="11" fill="var(--muted)" textAnchor="start">{fmtDT(series.start, i)}</text>
          </g>
        ))}
        {series.meal_carbs.map((c, i) => c > 0 && i <= cursor ? (
          <circle key={`m${i}`} cx={x(i)} cy={H - pad.b - 6} r={2 + Math.min(c, 120) / 30} fill="var(--blue)" opacity=".75">
            <title>{`${Math.round(c)} g carbohydrate`}</title>
          </circle>
        ) : null)}
        {cursor < n - 1 && <path d={path(cursor, n - 1)} fill="none" stroke="var(--muted)" strokeWidth="1.5" opacity=".35" />}
        <path d={path(0, cursor)} fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinejoin="round" />
        {fan && (
          <g>
            <polygon
              fill="var(--accent)" opacity=".18"
              points={[`${x(cursor)},${y(fan.now)}`, ...fan.pts.map((p) => `${x(p.i)},${y(p.hi)}`), ...[...fan.pts].reverse().map((p) => `${x(p.i)},${y(p.lo)}`)].join(' ')}
            />
            <polyline fill="none" stroke="var(--accent)" strokeWidth="2" strokeDasharray="5 4"
              points={[`${x(cursor)},${y(fan.now)}`, ...fan.pts.map((p) => `${x(p.i)},${y(p.md)}`)].join(' ')} />
            {fan.pts.map((p, h) => (
              <g key={h}>
                <circle cx={x(p.i)} cy={y(p.md)} r="3.5" fill="var(--accent)" />
                <text x={x(p.i) + 6} y={y(p.md) - 6} fontSize="11" fill="var(--text)" fontWeight="600">{Math.round(clamp(p.md))}</text>
              </g>
            ))}
          </g>
        )}
        {series.alerts.filter((a) => a.t - series.t0 <= cursor).map((a, i) => (
          <g key={i} transform={`translate(${x(a.t - series.t0)},${pad.t + 6})`}>
            <polygon points="0,10 -6,-2 6,-2" fill={a.type === 'hypo' ? 'var(--high)' : 'var(--med)'} />
            <title>{`${a.type === 'hypo' ? 'Low' : 'High'} glucose alert, probability ${(a.prob * 100).toFixed(0)}%`}</title>
          </g>
        ))}
        <line x1={x(cursor)} x2={x(cursor)} y1={pad.t} y2={H - pad.b} stroke="var(--text)" strokeWidth="1" opacity=".45" />
        <circle cx={x(cursor)} cy={y(g[cursor])} r="4.5" fill="var(--surface)" stroke="var(--accent)" strokeWidth="2.5" />
      </svg>
      <div className="legend">
        <span><i style={{ background: 'var(--accent)' }} />Measured (CGM)</span>
        <span><i style={{ background: 'var(--accent)', opacity: 0.5 }} />Twin forecast: +30, +60, +120 min with 80% interval</span>
        <span><i style={{ background: 'var(--muted)', opacity: 0.4 }} />What happens next (faded during replay)</span>
        <span><i style={{ background: 'var(--blue)' }} />Meals</span>
        <span><i style={{ background: 'var(--med)' }} />High alert</span>
        <span><i style={{ background: 'var(--high)' }} />Low alert</span>
      </div>
    </div>
  )
}
