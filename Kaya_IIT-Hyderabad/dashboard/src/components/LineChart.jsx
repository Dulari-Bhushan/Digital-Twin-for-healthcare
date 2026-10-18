import { useWidth } from '../utils'

/** Small multi-series line chart. series: [{ name, y: number[], color, dash? }], x labels by index. */
export default function LineChart({ series, yDomain, yFmt = (v) => Math.round(v), xTickEvery, xLabel = (i) => i, bands = [], height = 200 }) {
  const [ref, W] = useWidth()
  const pad = { l: 44, r: 12, t: 10, b: 26 }
  const iw = W - pad.l - pad.r
  const ih = height - pad.t - pad.b
  const n = series[0].y.length
  const all = series.flatMap((s) => s.y)
  const [lo, hi] = yDomain || [Math.min(...all), Math.max(...all)]
  const x = (i) => pad.l + (i / (n - 1)) * iw
  const y = (v) => pad.t + ih - ((v - lo) / (hi - lo || 1)) * ih
  const yt = Array.from({ length: 4 }, (_, k) => lo + ((hi - lo) * k) / 3)
  const xt = []
  for (let i = 0; i < n; i += xTickEvery) xt.push(i)
  return (
    <div ref={ref} style={{ width: '100%', minWidth: 0, overflow: 'hidden' }}>
      <svg width={W} height={height} role="img">
        {bands.map((b, i) => <rect key={i} x={pad.l} width={iw} y={y(b[1])} height={y(b[0]) - y(b[1])} fill="var(--range)" />)}
        {yt.map((v, i) => (
          <g key={i}>
            <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="var(--border)" strokeDasharray="1 4" />
            <text x={pad.l - 6} y={y(v) + 4} textAnchor="end" fontSize="11" fill="var(--muted)">{yFmt(v)}</text>
          </g>
        ))}
        {xt.map((i) => <text key={i} x={x(i)} y={height - 8} fontSize="11" fill="var(--muted)" textAnchor={i === 0 ? 'start' : 'middle'}>{xLabel(i)}</text>)}
        {series.map((s) => (
          <polyline key={s.name} fill="none" stroke={s.color} strokeWidth="2" strokeDasharray={s.dash}
            points={s.y.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')} />
        ))}
      </svg>
      <div className="legend">
        {series.map((s) => (
          <span key={s.name}><i style={{ background: s.color, opacity: s.dash ? 0.6 : 1 }} />{s.name}</span>
        ))}
      </div>
    </div>
  )
}
