import { useCallback, useEffect, useRef, useState } from 'react'

const CAP = 700      // steps kept on screen (about 2.4 days)
const DROP = 144     // steps dropped when the window slides

/**
 * Live feed from the Kaya API. The server streams one simulated wearable reading every few hundred ms and runs the
 * glucose model on each one, so every point on screen comes with a freshly computed forecast.
 */
export function useLive(pid) {
  const [state, setState] = useState({ active: false, series: null, latency: null, count: 0, ended: false })
  const ws = useRef(null)

  const stop = useCallback(() => {
    if (ws.current) { ws.current.close(); ws.current = null }
    setState((s) => ({ ...s, active: false }))
  }, [])

  const start = useCallback(() => {
    if (ws.current) ws.current.close()
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const sock = new WebSocket(`${proto}://${window.location.host}/ws/live/${pid}?interval=0.35&back_days=3`)
    ws.current = sock
    setState({ active: true, series: null, latency: null, count: 0, ended: false })
    sock.onmessage = (ev) => {
      const m = JSON.parse(ev.data)
      if (m.type === 'init') {
        setState((s) => ({
          ...s,
          series: {
            start: m.start, t0: m.t0, step_min: m.step_min, glucose: m.glucose, meal_carbs: m.meal_carbs, steps: m.steps,
            forecast: { t: [], q: [], p: [], horizons_min: [30, 60, 120] }, alerts: [],
          },
        }))
      } else if (m.type === 'tick') {
        setState((s) => {
          if (!s.series) return s
          let { start, t0, glucose, meal_carbs, steps, forecast, alerts } = s.series
          glucose = [...glucose, m.glucose]
          meal_carbs = [...meal_carbs, m.meal_carbs]
          steps = [...steps, m.steps]
          forecast = { ...forecast }
          if (m.forecast) {
            forecast.t = [...forecast.t, m.t]
            forecast.q = [...forecast.q, m.forecast.q]
            forecast.p = [...forecast.p, [m.forecast.p_hyper, m.forecast.p_hypo]]
            if (m.forecast.alerts.length) alerts = [...alerts, ...m.forecast.alerts.map((a) => ({ ...a, t: m.t, time: m.time }))]
          }
          if (glucose.length > CAP) {
            glucose = glucose.slice(DROP); meal_carbs = meal_carbs.slice(DROP); steps = steps.slice(DROP)
            t0 += DROP
            start = new Date(new Date(start).getTime() + DROP * 5 * 60000).toISOString()
            const keep = forecast.t.map((t, i) => (t >= t0 ? i : -1)).filter((i) => i >= 0)
            forecast = { ...forecast, t: keep.map((i) => forecast.t[i]), q: keep.map((i) => forecast.q[i]), p: keep.map((i) => forecast.p[i]) }
            alerts = alerts.filter((a) => a.t >= t0)
          }
          return {
            ...s, count: s.count + 1, latency: m.forecast ? m.forecast.inference_ms : s.latency,
            series: { start, t0, step_min: 5, glucose, meal_carbs, steps, forecast, alerts },
          }
        })
      } else if (m.type === 'end') {
        setState((s) => ({ ...s, active: false, ended: true }))
      }
    }
    sock.onclose = () => setState((s) => ({ ...s, active: false }))
  }, [pid])

  useEffect(() => () => { if (ws.current) ws.current.close() }, [pid])
  return { ...state, start, stop }
}
