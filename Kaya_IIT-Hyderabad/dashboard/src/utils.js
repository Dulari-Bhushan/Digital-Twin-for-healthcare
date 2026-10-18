export const fmtDT = (iso, i = 0, step = 5) =>
  new Date(new Date(iso).getTime() + i * step * 60000).toLocaleString('en-IN', {
    weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC',
  })
export const fmtHM = (iso, i = 0, step = 5) =>
  new Date(new Date(iso).getTime() + i * step * 60000).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC',
  })
export const fmtDay = (iso, i = 0, step = 5) =>
  new Date(new Date(iso).getTime() + i * step * 60000).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', timeZone: 'UTC' })

/** Plain-language reason an alert fired, built from the data the model saw. */
export function explain(series, idx) {
  if (!series || idx < 6) return ''
  const g = series.glucose
  const slope = (g[idx] - g[idx - 6]) / 30
  let meal = null
  for (let k = idx; k >= Math.max(0, idx - 36); k--) {
    if (series.meal_carbs[k] > 0) { meal = { carbs: series.meal_carbs[k], mins: (idx - k) * 5 }; break }
  }
  const trend = Math.abs(slope) < 0.4 ? 'steady' : slope > 0 ? `rising ${slope.toFixed(1)} mg/dL per min` : `falling ${Math.abs(slope).toFixed(1)} mg/dL per min`
  const m = meal ? `, ${Math.round(meal.carbs)} g carbs eaten ${meal.mins} min earlier` : ', no recent meal logged'
  return `Glucose ${Math.round(g[idx])} and ${trend}${m}.`
}

/** Per-day stats from the end of a series: day 0 is the most recent full 24 h. */
export function dayStats(series, dayFromEnd) {
  const n = series.glucose.length
  const e = n - 288 * dayFromEnd
  const s = e - 288
  if (s < 0) return null
  const g = series.glucose.slice(s, e)
  const inR = g.filter((v) => v >= 70 && v <= 180).length / g.length
  const low = g.filter((v) => v < 70).length / g.length
  const steps = series.steps.slice(s, e).reduce((a, b) => a + b, 0)
  const meals = series.meal_carbs.slice(s, e)
  return {
    tir: inR, low, steps, carbs: meals.reduce((a, b) => a + b, 0), meals: meals.filter((v) => v > 0).length,
    mean: g.reduce((a, b) => a + b, 0) / g.length, startIdx: s,
  }
}
