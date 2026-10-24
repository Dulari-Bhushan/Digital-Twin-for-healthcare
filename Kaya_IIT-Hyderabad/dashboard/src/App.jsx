import { useEffect, useMemo, useRef, useState } from 'react'
import { getChanges, getPatient, getPatients, getSeries } from './api'
import { AlertsCard, GlucoseCard, Hero, Organs, ProbCard, RangeCard, WhatIfStudio } from './components/Doctor'
import { Sidebar } from './components/Triage'
import PatientApp from './components/PatientApp'
import Record from './components/Record'
import Admin from './components/Admin'
import Heart from './components/Heart'
import { ChangesCard } from './components/Reports'
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
  const [mode, setMode] = useState(['patient', 'admin'].includes(params.get('view')) ? params.get('view') : 'doctor')
  const [docView, setDocView] = useState(params.get('view') === 'heart' ? 'heart' : 'twin')
  const [d, setD] = useState(null)
  const [series, setSeries] = useState(null)
  const [changes, setChanges] = useState(null)
  const [cursor, setCursor] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [err, setErr] = useState(null)
  const timer = useRef(null)
  const [record, setRecord] = useState(params.get('record') ? { tab: params.get('record') } : null)
  const openRecord = (tab) => setRecord({ tab })
  const live = useLive(sel)
  const [sideW, setSideW] = useState(() => { try { return Number(localStorage.getItem('kaya.sideW')) || 330 } catch { return 330 } })
  const dragSide = (e) => {
    e.preventDefault()
    const x0 = e.clientX, w0 = sideW
    let w = w0
    const move = (ev) => { w = Math.min(640, Math.max(240, w0 + ev.clientX - x0)); setSideW(w) }
    const up = () => {
      window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up)
      document.body.classList.remove('resizing')
      try { localStorage.setItem('kaya.sideW', String(w)) } catch { /* not persisted */ }
    }
    document.body.classList.add('resizing')
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', up)
  }

  useEffect(() => {
    getPatients().then((p) => {
      setPatients(p)
      const demo = p.find((x) => x.demo_tag) || [...p].sort((a, b) => b.alerts_24h - a.alerts_24h || b.score - a.score)[0]
      setSel(params.get('p') ? Number(params.get('p')) : demo.id)
    }).catch((e) => setErr(String(e)))
  }, [])

  useEffect(() => {                                   // flags change when a patient writes or the doctor replies
    const refresh = () => getPatients().then(setPatients).catch(() => {})
    const id = setInterval(refresh, 15000)
    window.addEventListener('kaya:messages', refresh)
    return () => { clearInterval(id); window.removeEventListener('kaya:messages', refresh) }
  }, [])

  useEffect(() => {
    if (sel == null) return
    setPlaying(false)
    setChanges(null)
    getChanges(sel).then(setChanges).catch(() => {})
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
          <Logo />
          <div><b>Kaya</b><small>Multi-Organ Digital Twin For Type 2 Diabetes</small></div>
        </div>
        <span className="sp" />
        <span className="tag" title="All patients are synthetic. Decision support for clinicians, not a diagnostic device.">🧪 Synthetic data · Decision support</span>
        {mode === 'patient' && patients.length > 0 && (
          <select className="pick" value={sel ?? ''} onChange={(e) => setSel(Number(e.target.value))} aria-label="Choose patient">
            {patients.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        )}
        <div className="switch" role="tablist">
          <button className={mode === 'doctor' ? 'on' : ''} onClick={() => setMode('doctor')}>Doctor</button>
          <button className={mode === 'patient' ? 'on' : ''} onClick={() => setMode('patient')}>Patient</button>
          <button className={mode === 'admin' ? 'on' : ''} onClick={() => setMode('admin')}>Admin</button>
        </div>
      </header>

      {record && d && d.profile.id === sel && <Record d={d} pid={sel} tab={record.tab} setTab={(tab) => setRecord({ tab })} onClose={() => setRecord(null)} changes={changes} />}
      {mode === 'doctor' && (
        <nav className="subnav" aria-label="Doctor views">
          <button className={docView === 'twin' ? 'on' : ''} onClick={() => setDocView('twin')}>Glucose twin</button>
          <button className={docView === 'heart' ? 'on' : ''} onClick={() => setDocView('heart')}>Heart watch</button>
        </nav>
      )}
      {mode === 'admin' ? <Admin /> : mode === 'doctor' && docView === 'heart' ? (sel == null ? <div className="stage muted">Loading…</div> : <Heart pid={sel} onPick={setSel} onOpenTwin={(id) => { setSel(id); setDocView('twin') }} />) : mode === 'patient' ? (
        ready ? <PatientApp d={d} at={at} pid={sel} changes={changes} /> : <div className="stage muted">Loading…</div>
      ) : (
        <div className="layout" style={{ '--sidew': `${sideW}px` }}>
          <Sidebar patients={patients} selected={sel} onSelect={(id) => { setSel(id); setRecord({ tab: 'catchup' }) }} />
          <div className="grip" role="separator" aria-orientation="vertical" aria-label="Drag to resize the patient list" title="Drag to resize · double-click to reset"
            onPointerDown={dragSide} onDoubleClick={() => { setSideW(330); try { localStorage.setItem('kaya.sideW', '330') } catch { /* ignore */ } }} />
          <main className="bento">
            {!ready ? <div className="c12 muted">Loading the twin…</div> : (
              <>
                <div className="c12"><Hero d={d} onOpen={openRecord} /></div>
                {changes && <div className="c12"><ChangesCard ch={changes} audience="doctor" onOpen={openRecord} /></div>}
                <div className="c8"><GlucoseCard series={shownSeries} cursor={shownCursor} at={at} metrics={d.metrics} playing={playing} setPlaying={setPlaying} setCursor={setCursor} range={range} onOpen={openRecord} live={{ on: liveOn, active: live.active, latency: live.latency, count: live.count, ended: live.ended, start: live.start, stop: live.stop }} /></div>
                <div className="c4" style={{ display: 'grid', gap: 20, gridTemplateRows: 'auto 1fr' }}>
                  <ProbCard at={at} onOpen={openRecord} />
                  <RangeCard metrics={d.metrics} onOpen={openRecord} />
                </div>
                <Organs d={d} onOpen={openRecord} />
                <div className="c12"><WhatIfStudio pid={sel} /></div>
                <div className="c12"><AlertsCard alerts={shownSeries.alerts.filter((a) => a.t - shownSeries.t0 <= shownCursor)} series={shownSeries} onOpen={openRecord} /></div>
              </>
            )}
          </main>
        </div>
      )}
    </div>
  )
}
