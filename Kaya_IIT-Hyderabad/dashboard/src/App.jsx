import { useEffect, useMemo, useRef, useState } from 'react'
import { getPatient, getPatients, getSeries } from './api'
import { AlertsCard, GlucoseCard, Hero, Organs, ProbCard, RangeCard, Sidebar, WhatIfStudio } from './components/Doctor'
import PatientApp from './components/PatientApp'
import { useLive } from './live'
import { Logo } from './ui'

const HORIZ = [30, 60, 120]
const clamp = (v) => Math.min(400, Math.max(40, v))

function atCursor(series, cursor) {
  const k = series.forecast.t.indexOf(series.t0 + cursor)
  if (k < 0) return null
  const g = series.glucose[cursor]
  return {
    glucose: g,
    forecast: HORIZ.map((m, h) => ({
      minutes: m,
      lo: clamp(g + series.forecast.q[k][h][0]),
      median: clamp(g + series.forecast.q[k][h][1]),
      hi: clamp(g + series.forecast.q[k][h][2]),
    })),
    p_hyper: series.forecast.p[k][0],
    p_hypo: series.forecast.p[k][1],
  }
}

export default function App() {
  const params = new URLSearchParams(window.location.search)
  const [patients, setPatients] = useState([])
  const [sel, setSel] = useState(null)
  const [mode, setMode] = useState(params.get('view') === 'patient' ? 'patient' : 'doctor')
  const [d, setD] = useState(null)
  const [series, setSeries] = useState(null)
  const [cursor, setCursor] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [err, setErr] = useState(null)
  const timer = useRef(null)
  const live = useLive(sel)

  useEffect(() => {
    getPatients().then((p) => {
      setPatients(p)
      const demo = [...p].sort((a, b) => b.alerts_24h - a.alerts_24h || b.score - a.score)[0]
      setSel(params.get('p') ? Number(params.get('p')) : demo.id)
    }).catch((e) => setErr(String(e)))
  }, [])

  useEffect(() => {
    if (sel == null) return
    setPlaying(false)
    Promise.all([getPatient(sel), getSeries(sel, 3)]).then(([det, s]) => {
      setD(det); setSeries(s)
      setCursor(s.forecast.t[s.forecast.t.length - 1] - s.t0)
    }).catch((e) => setErr(String(e)))
  }, [sel])

  const range = useMemo(() => (series ? [series.forecast.t[0] - series.t0, series.forecast.t.at(-1) - series.t0] : [0, 0]), [series])

  useEffect(() => {
    clearInterval(timer.current)
    if (!playing) return
    timer.current = setInterval(() => {
      setCursor((c) => {
        if (c + 3 > range[1]) { setPlaying(false); return range[1] }
        return c + 3
      })
    }, 110)
    return () => clearInterval(timer.current)
  }, [playing, range])

  const liveOn = live.active && live.series && live.series.forecast.t.length > 0
  const shownSeries = liveOn ? live.series : series
  const shownCursor = liveOn ? live.series.glucose.length - 1 : cursor
  const at = useMemo(() => (shownSeries ? atCursor(shownSeries, shownCursor) : null), [shownSeries, shownCursor])
  if (err) return <div style={{ padding: 40 }}>Could not reach the Kaya API: {err}. Start it with <code>uvicorn app:app --app-dir src/api</code>.</div>
  const ready = d && series && at

  return (
    <div className="app">
      <header className="top">
        <div className="logo">
          <span className="mark"><Logo /></span>
          <div><b>Kaya</b><small>multi-organ digital twin for Type 2 Diabetes</small></div>
        </div>
        <span className="sp" />
        <span className="tag" title="All patients are synthetic. Decision support for clinicians, not a diagnostic device.">🧪 Synthetic data · Decision support</span>
        {mode === 'patient' && patients.length > 0 && (
          <select className="pick" value={sel ?? ''} onChange={(e) => setSel(Number(e.target.value))} aria-label="Choose patient">
            {patients.map((p) => <option key={p.id} value={p.id}>Patient {p.id}</option>)}
          </select>
        )}
        <div className="switch" role="tablist">
          <button className={mode === 'doctor' ? 'on' : ''} onClick={() => setMode('doctor')}>🩺 Doctor</button>
          <button className={mode === 'patient' ? 'on' : ''} onClick={() => setMode('patient')}>🙂 Patient</button>
        </div>
      </header>

      {mode === 'patient' ? (
        ready ? <PatientApp d={d} at={at} pid={sel} /> : <div className="stage muted">Loading…</div>
      ) : (
        <div className="layout">
          <Sidebar patients={patients} selected={sel} onSelect={setSel} />
          <main className="bento">
            {!ready ? <div className="c12 muted">Loading the twin…</div> : (
              <>
                <div className="c12"><Hero d={d} /></div>
                <div className="c8"><GlucoseCard series={shownSeries} cursor={shownCursor} at={at} metrics={d.metrics} playing={playing} setPlaying={setPlaying} setCursor={setCursor} range={range} live={{ on: liveOn, active: live.active, latency: live.latency, count: live.count, ended: live.ended, start: live.start, stop: live.stop }} /></div>
                <div className="c4" style={{ display: 'grid', gap: 20, gridTemplateRows: 'auto 1fr' }}>
                  <ProbCard at={at} />
                  <RangeCard metrics={d.metrics} />
                </div>
                <Organs d={d} />
                <div className="c12"><WhatIfStudio pid={sel} /></div>
                <div className="c12"><AlertsCard alerts={shownSeries.alerts.filter((a) => a.t - shownSeries.t0 <= shownCursor)} series={shownSeries} /></div>
              </>
            )}
          </main>
        </div>
      )}
    </div>
  )
}
