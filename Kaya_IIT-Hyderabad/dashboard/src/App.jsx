import { useEffect, useMemo, useRef, useState } from 'react'
import { getPatient, getPatients, getSeries } from './api'
import GlucoseChart from './components/GlucoseChart'
import { Alerts, Organs, PatientHeader, PatientList, TwinNow } from './components/Panels'
import PatientView from './components/PatientView'
import WhatIf from './components/WhatIf'
import { fmtDT } from './utils'

const HORIZ = [30, 60, 120]

function atCursor(series, cursor) {
  const k = series.forecast.t.indexOf(series.t0 + cursor)
  if (k < 0) return null
  const g = series.glucose[cursor]
  const clamp = (v) => Math.min(400, Math.max(40, v))
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
  const [patients, setPatients] = useState([])
  const [sel, setSel] = useState(null)
  const [mode, setMode] = useState('doctor')
  const [d, setD] = useState(null)
  const [series, setSeries] = useState(null)
  const [cursor, setCursor] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [err, setErr] = useState(null)
  const timer = useRef(null)

  useEffect(() => {
    getPatients().then((p) => {
      setPatients(p)
      const demo = [...p].sort((a, b) => b.alerts_24h - a.alerts_24h || b.score - a.score)[0]
      setSel(demo.id)
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

  const range = useMemo(() => {
    if (!series) return [0, 0]
    return [series.forecast.t[0] - series.t0, series.forecast.t[series.forecast.t.length - 1] - series.t0]
  }, [series])

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

  const at = useMemo(() => (series ? atCursor(series, cursor) : null), [series, cursor])

  if (err) return <div style={{ padding: 40 }}>Could not reach the Kaya API: {err}. Start it with <code>uvicorn app:app --app-dir src/api</code>.</div>

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="mark"><svg width="16" height="16" viewBox="0 0 32 32"><path d="M9 6v20M9 16l12-10M9 16l12 10" stroke="white" strokeWidth="4" fill="none" strokeLinecap="round" /></svg></span>
          Kaya <small>multi-organ digital twin for Type 2 Diabetes</small>
        </div>
        <span className="spacer" />
        <span className="chip" title="All patients are synthetic. Kaya is decision support for clinicians, not a diagnostic device.">Synthetic data · Decision support</span>
        <div className="seg" role="tablist">
          <button className={mode === 'doctor' ? 'on' : ''} onClick={() => setMode('doctor')}>Doctor</button>
          <button className={mode === 'patient' ? 'on' : ''} onClick={() => setMode('patient')}>Patient</button>
        </div>
      </header>
      <div className="body">
        <PatientList patients={patients} selected={sel} onSelect={setSel} />
        <main className="main">
          {!d || !series || !at ? <div className="muted">Loading the twin…</div> : mode === 'patient' ? <PatientView d={d} at={at} /> : (
            <>
              <PatientHeader d={d} />
              <div className="card">
                <div className="card-head">
                  <h2>Glucose twin <span className="muted" style={{ fontWeight: 400 }}>· {fmtDT(series.start, cursor)}</span></h2>
                  <div className="row">
                    <button className="btn small" onClick={() => { if (cursor >= range[1]) setCursor(range[0]); setPlaying(!playing) }}>{playing ? 'Pause' : 'Replay last 3 days'}</button>
                    <button className="btn small" onClick={() => { setPlaying(false); setCursor(range[1]) }}>Now</button>
                  </div>
                </div>
                <TwinNow at={at} metrics={d.metrics} />
                <div style={{ marginTop: 12 }}>
                  <GlucoseChart series={series} cursor={cursor} />
                </div>
                <input type="range" min={range[0]} max={range[1]} step="1" value={cursor} aria-label="Replay position"
                  onChange={(e) => { setPlaying(false); setCursor(Number(e.target.value)) }} style={{ width: '100%', accentColor: 'var(--accent)' }} />
              </div>
              <Organs d={d} />
              <WhatIf pid={sel} />
              <Alerts alerts={series.alerts.filter((a) => a.t - series.t0 <= cursor)} series={series} />
            </>
          )}
        </main>
      </div>
    </div>
  )
}
