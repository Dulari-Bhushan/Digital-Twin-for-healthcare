import { useWidth } from '../ui'
import { dayLabel } from '../record'

const clamp = (v, lo = 40, hi = 400) => Math.min(hi, Math.max(lo, v))
const wrap = { width: '100%', minWidth: 0, overflow: 'hidden' }

/** Full CGM trace for the whole history, with day markers. */
export function CgmChart({ series, height = 230 }) {
  const [ref, W] = useWidth()
  const pad = { l: 38, r: 10, t: 12, b: 26 }
  const iw = W - pad.l - pad.r
  const ih = height - pad.t - pad.b
  const g = series.glucose
  const ymax = Math.max(260, Math.ceil(Math.max(...g) / 50) * 50)
  const x = (i) => pad.l + (i / (g.length - 1)) * iw
  const y = (v) => pad.t + ih - ((clamp(v, 40, ymax) - 40) / (ymax - 40)) * ih
  const pts = g.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const days = []
  for (let i = 0; i < g.length; i += 288) days.push(i)
  return (
    <div ref={ref} style={wrap}>
      <svg width={W} height={height} role="img" aria-label="Full glucose history">
        <rect x={pad.l} y={y(180)} width={iw} height={y(70) - y(180)} rx="10" fill="#dfeee2" opacity=".75" />
        {[70, 180, 250, 320].filter((v) => v <= ymax).map((v) => (
          <g key={v}><line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="rgba(28,52,50,.07)" strokeDasharray="3 5" />
            <text x={pad.l - 6} y={y(v) + 4} fontSize="11" fontWeight="600" fill="#667b78" textAnchor="end">{v}</text></g>
        ))}
        {days.map((i, k) => (
          <g key={i}><line x1={x(i)} x2={x(i)} y1={pad.t} y2={height - pad.b} stroke="rgba(28,52,50,.10)" />
            {k % 2 === 0 && <text x={x(i) + 3} y={height - 8} fontSize="10" fontWeight="600" fill="#667b78">{dayLabel(series, i + series.t0, { day: 'numeric', month: 'short' })}</text>}</g>
        ))}
        <polyline points={pts} fill="none" stroke="#0F6E68" strokeWidth="1.3" strokeLinejoin="round" />
        {g.map((v, i) => (v < 70 ? <circle key={i} cx={x(i)} cy={y(v)} r="2.2" fill="#c4645b" /> : null))}
      </svg>
    </div>
  )
}

/** Daily time-in-range as stacked columns: below, in, above range. */
export function StackedTir({ days, series, height = 200 }) {
  const [ref, W] = useWidth()
  const pad = { l: 8, r: 8, t: 22, b: 30 }
  const bw = (W - pad.l - pad.r) / days.length
  const ih = height - pad.t - pad.b
  return (
    <div ref={ref} style={wrap}>
      <svg width={W} height={height} role="img" aria-label="Daily time in range">
        {days.map((d, k) => {
          const x = pad.l + k * bw + bw * 0.14
          const w = bw * 0.72
          const h = (v) => v * ih
          const y0 = pad.t + ih
          return (
            <g key={k}>
              <rect x={x} y={y0 - h(d.tbr)} width={w} height={h(d.tbr)} fill="#c4645b" rx="3"><title>{`Below 70: ${(d.tbr * 100).toFixed(1)}%`}</title></rect>
              <rect x={x} y={y0 - h(d.tbr) - h(d.tir)} width={w} height={h(d.tir)} fill="#4d8f6b"><title>{`In range: ${(d.tir * 100).toFixed(0)}%`}</title></rect>
              <rect x={x} y={y0 - h(d.tbr) - h(d.tir) - h(d.tar)} width={w} height={h(d.tar)} fill="#e9a23b" rx="3"><title>{`Above 180: ${(d.tar * 100).toFixed(0)}%`}</title></rect>
              <text x={x + w / 2} y={pad.t - 6} fontSize="10" fontWeight="800" fill="#1c3432" textAnchor="middle">{Math.round(d.tir * 100)}</text>
              <text x={x + w / 2} y={height - 14} fontSize="9.5" fontWeight="600" fill="#667b78" textAnchor="middle">{dayLabel(series, d.idx, { weekday: 'short' })}</text>
              <text x={x + w / 2} y={height - 3} fontSize="9.5" fontWeight="600" fill="#667b78" textAnchor="middle">{dayLabel(series, d.idx, { day: 'numeric' })}</text>
            </g>
          )
        })}
      </svg>
      <div className="legend"><span><i style={{ background: '#4d8f6b' }} />In range 70-180 (% shown on top)</span><span><i style={{ background: '#e9a23b' }} />Above 180</span><span><i style={{ background: '#c4645b' }} />Below 70</span></div>
    </div>
  )
}

/** Ambulatory glucose profile: the median day with 25-75% and 10-90% bands. */
export function AgpChart({ agp, height = 240 }) {
  const [ref, W] = useWidth()
  const pad = { l: 38, r: 10, t: 12, b: 24 }
  const iw = W - pad.l - pad.r
  const ih = height - pad.t - pad.b
  const ymax = Math.max(260, Math.ceil(Math.max(...agp.p90) / 50) * 50)
  const x = (i) => pad.l + (i / 287) * iw
  const y = (v) => pad.t + ih - ((clamp(v, 40, ymax) - 40) / (ymax - 40)) * ih
  const band = (hi, lo) => [...hi.map((v, i) => `${x(i)},${y(v)}`), ...lo.map((v, i) => `${x(287 - i)},${y(lo[287 - i])}`)].join(' ')
  return (
    <div ref={ref} style={wrap}>
      <svg width={W} height={height} role="img" aria-label="Typical day glucose profile">
        <rect x={pad.l} y={y(180)} width={iw} height={y(70) - y(180)} rx="10" fill="#dfeee2" opacity=".7" />
        {[70, 180, 250].filter((v) => v <= ymax).map((v) => (
          <g key={v}><line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="rgba(28,52,50,.08)" strokeDasharray="3 5" />
            <text x={pad.l - 6} y={y(v) + 4} fontSize="11" fontWeight="600" fill="#667b78" textAnchor="end">{v}</text></g>
        ))}
        {[0, 6, 12, 18, 24].map((h) => <text key={h} x={pad.l + (h / 24) * iw} y={height - 7} fontSize="10.5" fontWeight="600" fill="#667b78" textAnchor={h === 0 ? 'start' : h === 24 ? 'end' : 'middle'}>{String(h).padStart(2, '0')}:00</text>)}
        <polygon points={band(agp.p90, agp.p10)} fill="#0F6E68" opacity=".12" />
        <polygon points={band(agp.p75, agp.p25)} fill="#0F6E68" opacity=".22" />
        <polyline points={agp.p50.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')} fill="none" stroke="#0F6E68" strokeWidth="2.6" strokeLinejoin="round" />
      </svg>
      <div className="legend"><span><i style={{ background: '#0F6E68' }} />Median day</span><span><i style={{ background: '#0F6E68', opacity: 0.35 }} />25-75% of days</span><span><i style={{ background: '#0F6E68', opacity: 0.15 }} />10-90% of days</span></div>
    </div>
  )
}

/** Simple bar chart with an optional goal line. */
export function Bars({ values, labels, color = '#0F6E68', goal = null, fmt = (v) => Math.round(v), height = 150, unit = '' }) {
  const [ref, W] = useWidth()
  const pad = { l: 6, r: 6, t: 20, b: 24 }
  const max = Math.max(...values, goal || 0) * 1.12 || 1
  const bw = (W - pad.l - pad.r) / values.length
  const ih = height - pad.t - pad.b
  return (
    <div ref={ref} style={wrap}>
      <svg width={W} height={height} role="img">
        {goal != null && <g><line x1={pad.l} x2={W - pad.r} y1={pad.t + ih * (1 - goal / max)} y2={pad.t + ih * (1 - goal / max)} stroke="#4d8f6b" strokeDasharray="4 4" strokeWidth="1.5" />
          <text x={pad.l} y={pad.t + ih * (1 - goal / max) - 3} fontSize="10" fontWeight="700" fill="#2e5f45" textAnchor="start">goal {fmt(goal)}{unit}</text></g>}
        {values.map((v, i) => {
          const h = (v / max) * ih
          const x = pad.l + i * bw + bw * 0.16
          return (
            <g key={i}>
              <rect x={x} y={pad.t + ih - h} width={bw * 0.68} height={Math.max(2, h)} rx="5" fill={color} opacity={i === values.length - 1 ? 1 : 0.55}><title>{`${labels[i]}: ${fmt(v)}${unit}`}</title></rect>
              <text x={x + bw * 0.34} y={pad.t + ih - h - 4} fontSize="9.5" fontWeight="800" fill="#1c3432" textAnchor="middle">{fmt(v)}</text>
              <text x={x + bw * 0.34} y={height - 8} fontSize="9.5" fontWeight="600" fill="#667b78" textAnchor="middle">{labels[i]}</text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

/** Horizontal contribution bars (positive pushes risk up, negative pulls it down). */
export function Contrib({ items, unitNote }) {
  const mx = Math.max(...items.map((i) => Math.abs(i.contrib)), 0.01)
  return (
    <div>
      {items.map((it) => (
        <div key={it.label} style={{ display: 'grid', gridTemplateColumns: '1.3fr 0.8fr 1.6fr', gap: 10, alignItems: 'center', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
          <div style={{ fontWeight: 700, fontSize: 13 }}>{it.label}</div>
          <div className="muted" style={{ fontSize: 12, fontWeight: 600 }}>{it.value}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 9, borderRadius: 6, background: 'rgba(28,52,50,.06)', position: 'relative' }}>
              <div style={{ position: 'absolute', height: '100%', borderRadius: 6, width: `${(Math.abs(it.contrib) / mx) * 50}%`, left: it.contrib >= 0 ? '50%' : `${50 - (Math.abs(it.contrib) / mx) * 50}%`, background: it.contrib >= 0 ? 'var(--rose-d)' : 'var(--mint-d)' }} />
              <div style={{ position: 'absolute', left: '50%', top: -2, bottom: -2, width: 1, background: 'rgba(28,52,50,.3)' }} />
            </div>
            <span style={{ width: 54, textAlign: 'right', fontSize: 12, fontWeight: 800, color: it.contrib >= 0 ? 'var(--rose-dd)' : 'var(--mint-dd)' }}>{it.contrib >= 0 ? '+' : ''}{it.contrib.toFixed(2)}</span>
          </div>
        </div>
      ))}
      {unitNote && <div className="note">{unitNote}</div>}
    </div>
  )
}

export function DataTable({ head, rows, widths }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="rt">
        <thead><tr>{head.map((h, i) => <th key={i} style={widths ? { width: widths[i] } : undefined}>{h}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
      </table>
    </div>
  )
}
