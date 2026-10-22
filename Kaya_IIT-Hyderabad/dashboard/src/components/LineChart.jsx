import { useWidth } from '../ui'

/** Pastel multi-series line chart. series: [{ name, y, color, dash? }]. A null value is a gap in the line. */
const runs = (y) => {
  const out = []
  let cur = null
  y.forEach((v, i) => { if (v == null) { cur = null } else { if (!cur) { cur = []; out.push(cur) } cur.push([i, v]) } })
  return out
}

export default function LineChart({ series, yDomain, yFmt = (v) => Math.round(v), xTickEvery, xLabel = (i) => i, band = null, height = 190 }) {
  const [ref, W] = useWidth()
  const pad = { l: 40, r: 14, t: 12, b: 26 }
  const iw = W - pad.l - pad.r
  const ih = height - pad.t - pad.b
  const n = series[0].y.length
  const all = series.flatMap((s) => s.y).filter((v) => v != null)
  const [lo, hi] = yDomain || [Math.min(...all), Math.max(...all)]
  const x = (i) => pad.l + (i / (n - 1)) * iw
  const y = (v) => pad.t + ih - ((v - lo) / (hi - lo || 1)) * ih
  const yt = Array.from({ length: 4 }, (_, k) => lo + ((hi - lo) * k) / 3)
  const xt = []
  for (let i = 0; i < n; i += xTickEvery) xt.push(i)
  return (
    <div ref={ref} style={{ width: '100%', minWidth: 0, overflow: 'hidden' }}>
      <svg width={W} height={height} role="img">
        {band && <rect x={pad.l} width={iw} y={y(band[1])} height={y(band[0]) - y(band[1])} rx="12" fill="#dfeee2" opacity=".7" />}
        {yt.map((v, i) => (
          <g key={i}>
            <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="rgba(28,52,50,.07)" strokeDasharray="3 5" />
            <text x={pad.l - 8} y={y(v) + 4} textAnchor="end" fontSize="11" fontWeight="600" fill="#667b78">{yFmt(v)}</text>
          </g>
        ))}
        {xt.map((i) => <text key={i} x={x(i)} y={height - 8} fontSize="11" fontWeight="600" fill="#667b78" textAnchor={i === 0 ? 'start' : 'middle'}>{xLabel(i)}</text>)}
        {series.map((s) => runs(s.y).map((r, j) => (r.length === 1
          ? <circle key={`${s.name}${j}`} cx={x(r[0][0])} cy={y(r[0][1])} r="3.2" fill={s.color} />
          : <polyline key={`${s.name}${j}`} fill="none" stroke={s.color} strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" strokeDasharray={s.dash}
            points={r.map(([i, v]) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')} />)))}
      </svg>
      <div className="legend">
        {series.map((s) => <span key={s.name}><i style={{ background: s.color }} />{s.name}</span>)}
      </div>
    </div>
  )
}
