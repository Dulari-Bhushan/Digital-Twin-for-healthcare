import { useEffect, useRef, useState } from 'react'

export const pct = (x, d = 0) => `${(x * 100).toFixed(d)}%`
export const fmtDT = (iso, i = 0, step = 5) =>
  new Date(new Date(iso).getTime() + i * step * 60000).toLocaleString('en-IN', {
    weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC',
  })
export const fmtHM = (iso, i = 0, step = 5) =>
  new Date(new Date(iso).getTime() + i * step * 60000).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC',
  })

export const DR = ['No retinopathy', 'Mild', 'Moderate', 'Severe', 'Proliferative']

export function useWidth() {
  const ref = useRef(null)
  const [w, setW] = useState(640)
  useEffect(() => {
    if (!ref.current) return
    const ro = new ResizeObserver((e) => setW(Math.max(280, e[0].contentRect.width)))
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  return [ref, w]
}

export const riskColor = (p, hi = 0.5, mid = 0.25) => (p >= hi ? 'var(--high)' : p >= mid ? 'var(--med)' : 'var(--low)')

/** Plain-language reason an alert fired, built from the data the model saw. */
export function explain(series, idx, type) {
  if (!series || idx < 6) return ''
  const g = series.glucose
  const slope = (g[idx] - g[idx - 6]) / 30
  let meal = null
  for (let k = idx; k >= Math.max(0, idx - 36); k--) {
    if (series.meal_carbs[k] > 0) { meal = { carbs: series.meal_carbs[k], mins: (idx - k) * 5 }; break }
  }
  const trend = Math.abs(slope) < 0.4 ? 'steady' : slope > 0 ? `rising ${slope.toFixed(1)} mg/dL per min` : `falling ${Math.abs(slope).toFixed(1)} mg/dL per min`
  const m = meal ? `, ${Math.round(meal.carbs)} g of carbohydrate eaten ${meal.mins} min earlier` : ', no recent meal logged'
  return `Glucose ${Math.round(g[idx])} mg/dL and ${trend}${m}.`
}
