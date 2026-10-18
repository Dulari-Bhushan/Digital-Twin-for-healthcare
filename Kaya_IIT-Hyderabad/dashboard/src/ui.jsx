import { useEffect, useRef, useState } from 'react'

export const pct = (x, d = 0) => `${(x * 100).toFixed(d)}%`
export const DR = ['No retinopathy', 'Mild', 'Moderate', 'Severe', 'Proliferative']

export const TONE = {
  lav: { bg: 'var(--lav)', d: 'var(--lav-d)', dd: 'var(--lav-dd)' },
  mint: { bg: 'var(--mint)', d: 'var(--mint-d)', dd: 'var(--mint-dd)' },
  peach: { bg: 'var(--peach)', d: 'var(--peach-d)', dd: 'var(--peach-dd)' },
  butter: { bg: 'var(--butter)', d: 'var(--butter-d)', dd: 'var(--butter-dd)' },
  sky: { bg: 'var(--sky)', d: 'var(--sky-d)', dd: 'var(--sky-dd)' },
  rose: { bg: 'var(--rose)', d: 'var(--rose-d)', dd: 'var(--rose-dd)' },
}
export const tierTone = (t) => (t === 'high' ? 'rose' : t === 'medium' ? 'peach' : 'mint')
/** risk 0..1 -> tone: calm mint, warm butter, hot rose */
export const riskTone = (p, hi = 0.5, mid = 0.25) => (p >= hi ? 'rose' : p >= mid ? 'butter' : 'mint')

export function useWidth() {
  const ref = useRef(null)
  const [w, setW] = useState(640)
  useEffect(() => {
    if (!ref.current) return
    const ro = new ResizeObserver((e) => setW(Math.max(260, e[0].contentRect.width)))
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  return [ref, w]
}

/** Circular progress. value 0..1 */
export function Ring({ value = 0, size = 120, stroke = 14, color = 'var(--lav-d)', track = 'rgba(255,255,255,.85)', children }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const v = Math.max(0, Math.min(1, value))
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={`${c * v} ${c}`} style={{ transition: 'stroke-dasharray .7s ease' }} />
      </svg>
      <div className="ring-in">{children}</div>
    </div>
  )
}

/** Ring split into coloured segments. segments: [{ v: fraction, color }] */
export function SegRing({ segments, size = 140, stroke = 18, children }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  let acc = 0
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,.85)" strokeWidth={stroke} />
        {segments.map((s, i) => {
          const len = Math.max(0, c * s.v - (s.v > 0.02 ? 5 : 0))
          const el = (
            <circle key={i} cx={size / 2} cy={size / 2} r={r} fill="none" stroke={s.color} strokeWidth={stroke} strokeLinecap="round"
              strokeDasharray={`${len} ${c}`} strokeDashoffset={-c * acc} />
          )
          acc += s.v
          return el
        })}
      </svg>
      <div className="ring-in">{children}</div>
    </div>
  )
}

const ILL = { stroke: 'rgba(42,39,66,.28)', sw: 2 }
export function LiverArt({ size = 46, fill = '#ffc9a8' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M6 30C6 18 20 10 38 12c14 2 22 10 20 20-2 12-14 20-28 18-9-1-15-4-19-10-3-3-5-6-5-10Z" fill={fill} stroke={ILL.stroke} strokeWidth={ILL.sw} />
      <path d="M22 18c4 6 6 14 4 24" fill="none" stroke="rgba(255,255,255,.8)" strokeWidth="3" strokeLinecap="round" />
      <ellipse cx="46" cy="46" rx="6" ry="8" fill="#9fd9b5" stroke={ILL.stroke} strokeWidth={ILL.sw} />
    </svg>
  )
}
export function EyeArt({ size = 46 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M3 32C13 16 25 10 32 10s19 6 29 22C51 48 39 54 32 54S13 48 3 32Z" fill="#fff" stroke={ILL.stroke} strokeWidth={ILL.sw} />
      <circle cx="32" cy="32" r="12" fill="#8fc4ff" stroke={ILL.stroke} strokeWidth={ILL.sw} />
      <circle cx="32" cy="32" r="5.5" fill="#2a2742" />
      <circle cx="28" cy="28" r="2.2" fill="#fff" />
    </svg>
  )
}
export function KidneyArt({ size = 46 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M40 8c15 2 21 17 13 31-6 11-16 18-24 16-9-2-5-12 1-18 4-5 3-9-3-13C18 19 22 6 40 8Z" fill="#a9d3ff" stroke={ILL.stroke} strokeWidth={ILL.sw} />
      <path d="M38 18c8 2 11 10 7 18" fill="none" stroke="rgba(255,255,255,.85)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

export function Spark({ values, color = 'var(--lav-d)', w = 120, h = 36 }) {
  const lo = Math.min(...values), hi = Math.max(...values)
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - 4 - ((v - lo) / (hi - lo || 1)) * (h - 8)}`).join(' ')
  return <svg width={w} height={h}><polyline points={pts} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
}

export const Logo = () => (
  <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden="true"><path d="M9 6v20M9 16l12-10M9 16l12 10" stroke="#fff" strokeWidth="4.2" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
)
