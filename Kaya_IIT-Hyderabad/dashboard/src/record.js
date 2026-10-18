// Analytics for the full patient record: daily history, typical-day glucose profile, meal responses and the risk-factor
// breakdowns behind the eye and kidney simulations. Everything is computed from the 14-day series the API returns.

export const mean = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0)
export const sum = (a) => a.reduce((x, y) => x + y, 0)
export const pctl = (arr, p) => {
  const s = [...arr].sort((a, b) => a - b)
  const i = (s.length - 1) * p
  const lo = Math.floor(i)
  const hi = Math.ceil(i)
  return s[lo] + (s[hi] - s[lo]) * (i - lo)
}
export const dayLabel = (series, idx, opts = { weekday: 'short', day: 'numeric' }) =>
  new Date(new Date(series.start).getTime() + (idx - series.t0) * 5 * 60000).toLocaleDateString('en-IN', { ...opts, timeZone: 'UTC' })

/** One row per calendar day (the last day is partial, up to the latest reading). */
export function dailyStats(series) {
  const n = series.glucose.length
  const out = []
  for (let s = 0; s < n; s += 288) {
    const e = Math.min(n, s + 288)
    const g = series.glucose.slice(s, e)
    if (g.length < 48) continue
    const m = mean(g)
    const sd = Math.sqrt(mean(g.map((v) => (v - m) ** 2)))
    const meals = series.meal_carbs.slice(s, e)
    out.push({
      idx: s + series.t0, n: g.length, partial: g.length < 288, mean: m, cv: (sd / m) * 100,
      tir: g.filter((v) => v >= 70 && v <= 180).length / g.length, tar: g.filter((v) => v > 180).length / g.length, tbr: g.filter((v) => v < 70).length / g.length,
      min: Math.min(...g), max: Math.max(...g), steps: sum(series.steps.slice(s, e)), carbs: sum(meals), meals: meals.filter((v) => v > 0).length,
      hr: mean(series.heart_rate.slice(s, e)), sleep: (series.sleep_stage.slice(s, e).filter((v) => v > 0).length * 5) / 60,
      lowMin: g.filter((v) => v < 70).length * 5,
    })
  }
  return out
}

/** Typical-day profile: percentiles of glucose by time of day across all days (an ambulatory glucose profile). */
export function agp(series) {
  const slots = Array.from({ length: 288 }, () => [])
  series.glucose.forEach((v, i) => slots[(i + series.t0) % 288].push(v))
  const at = (p) => slots.map((x) => pctl(x, p))
  return { p10: at(0.1), p25: at(0.25), p50: at(0.5), p75: at(0.75), p90: at(0.9) }
}

const BUCKETS = [['Breakfast', 5, 11], ['Lunch', 11, 16], ['Evening snack', 16, 19], ['Dinner', 19, 24]]
/** How glucose responded after each logged meal, grouped by time of day. */
export function mealResponses(series) {
  const g = series.glucose
  const events = []
  series.meal_carbs.forEach((c, i) => {
    if (c <= 0 || i + 6 >= g.length) return
    const w = g.slice(i, Math.min(g.length, i + 37))
    const peak = Math.max(...w)
    events.push({ i, hour: (((i + series.t0) % 288) * 5) / 60, carbs: c, base: g[i], peak, rise: peak - g[i], mins: w.indexOf(peak) * 5 })
  })
  const groups = BUCKETS.map(([name, a, b]) => {
    const ev = events.filter((e) => e.hour >= a && e.hour < b)
    return { name, n: ev.length, carbs: mean(ev.map((e) => e.carbs)), rise: mean(ev.map((e) => e.rise)), peak: mean(ev.map((e) => e.peak)), mins: mean(ev.map((e) => e.mins)) }
  }).filter((x) => x.n > 0)
  return { events, groups, worst: [...events].sort((a, b) => b.peak - a.peak).slice(0, 5) }
}

/** What pushes the 2-year retinopathy progression risk up or down (same coefficients as src/models/eye_risk.py). */
export function eyeFactors(profile, metrics, grade) {
  const t = [
    ['HbA1c', `${profile.hba1c}%`, 0.4 * (profile.hba1c - 7)],
    ['Diabetes duration', `${profile.duration_yrs} y`, 0.07 * profile.duration_yrs],
    ['Systolic blood pressure', `${profile.sbp.toFixed(0)} mmHg`, 0.018 * (profile.sbp - 120)],
    ['Glucose variability (CV)', `${metrics.gv_cv.toFixed(0)}%`, 0.035 * (metrics.gv_cv - 25)],
    ['Time in range', `${(metrics.tir * 100).toFixed(0)}%`, -0.014 * (metrics.tir * 100 - 50)],
    ['Current retinopathy grade', `grade ${grade}`, 0.55 * grade],
  ]
  return t.map(([label, value, contrib]) => ({ label, value, contrib }))
}

/** Components of the eGFR decline slope (same assumptions as src/models/kidney_dynamic.py). */
export function kidneySlope(profile, metrics) {
  const lab = profile.labs
  const parts = [
    ['Age-related decline', 'baseline', 0.9],
    ['HbA1c above 7', `${profile.hba1c}%`, 0.4 * Math.max(profile.hba1c - 7, 0)],
    ['Systolic BP above 120', `${profile.sbp.toFixed(0)} mmHg`, 0.03 * Math.max(profile.sbp - 120, 0)],
    ['Albuminuria (UACR 30 or more)', `${lab.uacr_mg_g.toFixed(0)} mg/g`, lab.uacr_mg_g >= 30 ? 1.2 : 0],
    ['Glucose variability above 28%', `${metrics.gv_cv.toFixed(0)}%`, 0.02 * Math.max(metrics.gv_cv - 28, 0)],
  ]
  return parts.map(([label, value, contrib]) => ({ label, value, contrib }))
}

export const FEATURE_NAMES = {
  age: ['Age', ' y'], male: ['Male sex', ''], bmi: ['BMI', ''], waist_cm: ['Waist', ' cm'], alt: ['ALT', ' U/L'], ast: ['AST', ' U/L'],
  platelets: ['Platelets', ''], hba1c: ['HbA1c', '%'], hdl: ['HDL', ' mg/dL'], diabetes: ['Diabetes', ''], sbp: ['Systolic BP', ' mmHg'], dbp: ['Diastolic BP', ' mmHg'],
}

/** Reference-range flags for the lab table. */
export function labFlag(name, v, sex) {
  const M = (tone, text) => ({ tone, text })
  switch (name) {
    case 'alt': return v > 40 ? M('butter', 'High') : M('mint', 'Normal')
    case 'ast': return v > 40 ? M('butter', 'High') : M('mint', 'Normal')
    case 'platelets': return v < 150 ? M('rose', 'Low') : v > 400 ? M('butter', 'High') : M('mint', 'Normal')
    case 'triglycerides': return v >= 200 ? M('rose', 'High') : v >= 150 ? M('butter', 'Borderline') : M('mint', 'Normal')
    case 'hdl': return v < (sex === 'F' ? 50 : 40) ? M('butter', 'Low') : M('mint', 'Normal')
    case 'fib4': return v >= 2.67 ? M('rose', 'High risk') : v >= 1.3 ? M('butter', 'Indeterminate') : M('mint', 'Low risk')
    case 'stiffness': return v >= 13 ? M('rose', 'Cirrhosis range') : v >= 8 ? M('butter', 'Fibrosis likely (F2+)') : M('mint', 'Below 8 kPa')
    case 'fat': return v >= 5.5 ? M('butter', 'Steatosis') : M('mint', 'Normal')
    case 'egfr': return v < 30 ? M('rose', 'Severely reduced') : v < 60 ? M('rose', 'Reduced') : v < 90 ? M('butter', 'Mildly reduced') : M('mint', 'Normal')
    case 'uacr': return v >= 300 ? M('rose', 'Severely increased (A3)') : v >= 30 ? M('rose', 'Moderately increased (A2)') : M('mint', 'Normal (A1)')
    case 'hba1c': return v >= 9 ? M('rose', 'Well above target') : v >= 7 ? M('butter', 'Above 7% target') : M('mint', 'At target')
    case 'bp': return v >= 140 ? M('rose', 'High') : v >= 130 ? M('butter', 'Elevated') : M('mint', 'Normal')
    default: return M('mint', '')
  }
}
export const egfrStage = (e) => (e >= 90 ? 'G1' : e >= 60 ? 'G2' : e >= 45 ? 'G3a' : e >= 30 ? 'G3b' : e >= 15 ? 'G4' : 'G5')
