import { useMemo } from 'react'
import { useWidth } from '../ui'
import { fmtDT } from '../utils'

const clamp = (v) => Math.min(400, Math.max(40, v))

/** Glucose over time with the forecast fan at the replay cursor. Soft pastel styling. */
export default function GlucoseChart({ series, cursor, height = 320 }) {
  const [ref, W] = useWidth()
  const H = height
  const pad = { l: 40, r: 58, t: 18, b: 32 }
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

  const line = (from, to) => {
    let d = ''
    for (let i = from; i <= to; i++) d += `${i === from ? 'M' : 'L'}${x(i).toFixed(1)},${y(g[i]).toFixed(1)}`
    return d
  }
  const k = fcIndex.get(cursor)
  const fan = useMemo(() => {
    if (k === undefined) return null
    const q = series.forecast.q[k]
    const now = g[cursor]
    return { now, pts: [6, 12, 24].map((s, h) => ({ i: cursor + s, lo: now + q[h][0], md: now + q[h][1], hi: now + q[h][2] })) }
  }, [k, cursor, series])

  const ticks = []
  for (let i = 0; i < n; i += 144) ticks.push(i)
  const yt = [70, 120, 180, 250, 320].filter((v) => v <= ymax)
  const area = `${line(0, cursor)}L${x(cursor)},${y(ymin)}L${x(0)},${y(ymin)}Z`

  return (
    <div ref={ref} style={{ width: '100%', minWidth: 0, overflow: 'hidden' }}>
      <svg width={W} height={H} role="img" aria-label="Glucose over time with forecast">
        <defs>
          <linearGradient id="gl-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0F6E68" stopOpacity=".28" />
            <stop offset="100%" stopColor="#0F6E68" stopOpacity="0" />
          </linearGradient>
        </defs>
        <rect x={pad.l} y={y(180)} width={iw} height={y(70) - y(180)} rx="14" fill="#dfeee2" opacity=".75" />
        <text x={pad.l + 10} y={y(180) + 18} fontSize="11" fontWeight="700" fill="#2e5f45">healthy range 70–180</text>
        {yt.map((v) => (
          <g key={v}>
            <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="rgba(28,52,50,.07)" strokeDasharray="3 5" />
            <text x={pad.l - 8} y={y(v) + 4} textAnchor="end" fontSize="11" fontWeight="600" fill="#667b78">{v}</text>
          </g>
        ))}
        {ticks.map((i) => <text key={i} x={x(i)} y={H - 10} fontSize="11" fontWeight="600" fill="#667b78">{fmtDT(series.start, i)}</text>)}
        {series.meal_carbs.map((c, i) => c > 0 && i <= cursor ? (
          <circle key={`m${i}`} cx={x(i)} cy={H - pad.b - 8} r={3 + Math.min(c, 120) / 24} fill="#f5d58f" stroke="#E9A23B" strokeWidth="1.5">
            <title>{`${Math.round(c)} g carbohydrate`}</title>
          </circle>
        ) : null)}
        {cursor < n - 1 && <path d={line(cursor, n - 1)} fill="none" stroke="#a9c4c0" strokeWidth="2" opacity=".55" strokeLinecap="round" />}
        <path d={area} fill="url(#gl-area)" />
        <path d={line(0, cursor)} fill="none" stroke="#0F6E68" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
        {fan && (
          <g>
            <polygon fill="#d9894a" opacity=".2"
              points={[`${x(cursor)},${y(fan.now)}`, ...fan.pts.map((p) => `${x(p.i)},${y(p.hi)}`), ...[...fan.pts].reverse().map((p) => `${x(p.i)},${y(p.lo)}`)].join(' ')} />
            <polyline fill="none" stroke="#d9894a" strokeWidth="3" strokeDasharray="2 7" strokeLinecap="round"
              points={[`${x(cursor)},${y(fan.now)}`, ...fan.pts.map((p) => `${x(p.i)},${y(p.md)}`)].join(' ')} />
            {fan.pts.map((p, h) => (
              <g key={h}>
                <circle cx={x(p.i)} cy={y(p.md)} r="6" fill="#fff" stroke="#d9894a" strokeWidth="3" />
                <text x={x(p.i) + 11} y={y(p.md) + 4} fontSize="12" fontWeight="800" fill="#85501f">{Math.round(clamp(p.md))}</text>
              </g>
            ))}
          </g>
        )}
        {series.alerts.filter((a) => a.t - series.t0 <= cursor).map((a, i) => (
          <g key={i} transform={`translate(${x(a.t - series.t0)},${pad.t + 10})`}>
            <circle r="9" fill={a.type === 'hypo' ? '#f4dcd7' : '#f6e6d6'} stroke={a.type === 'hypo' ? '#c4645b' : '#d9894a'} strokeWidth="2" />
            <text y="4" textAnchor="middle" fontSize="11" fontWeight="800" fill={a.type === 'hypo' ? '#8a3b34' : '#85501f'}>!</text>
            <title>{`${a.type === 'hypo' ? 'Low' : 'High'} glucose alert, probability ${(a.prob * 100).toFixed(0)}%`}</title>
          </g>
        ))}
        <line x1={x(cursor)} x2={x(cursor)} y1={pad.t} y2={H - pad.b} stroke="#1c3432" strokeWidth="1.5" strokeDasharray="4 5" opacity=".3" />
        <circle cx={x(cursor)} cy={y(g[cursor])} r="9" fill="#fff" stroke="#0F6E68" strokeWidth="4" />
      </svg>
      <div className="legend">
        <span><i style={{ background: '#0F6E68' }} />Measured</span>
        <span><i style={{ background: '#d9894a' }} />Twin forecast, 80% range</span>
        <span><i style={{ background: '#a9c4c0' }} />What happens next</span>
        <span><i style={{ background: '#f5d58f', border: '1.5px solid #E9A23B' }} />Meals</span>
        <span><i style={{ background: '#f6e6d6', border: '2px solid #d9894a', borderRadius: '50%' }} />Alert</span>
      </div>
    </div>
  )
}
