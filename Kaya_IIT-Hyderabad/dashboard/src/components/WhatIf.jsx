import { useEffect, useRef, useState } from 'react'
import { postWhatIf } from '../api'
import { fmtHM, pct } from '../utils'
import LineChart from './LineChart'

const PRESETS = [
  { name: 'Walk 20 min after meals', v: { carb_scale: 1, walk_after_meals: 20, baseline_shift: 0, steps_delta: 2000 } },
  { name: 'Smaller carb portions (-25%)', v: { carb_scale: 0.75, walk_after_meals: 0, baseline_shift: 0, steps_delta: 0 } },
  { name: 'Medication optimised', v: { carb_scale: 1, walk_after_meals: 0, baseline_shift: -15, steps_delta: 0 } },
  { name: 'All three', v: { carb_scale: 0.75, walk_after_meals: 20, baseline_shift: -12, steps_delta: 2000 } },
]
const ZERO = { carb_scale: 1, walk_after_meals: 0, baseline_shift: 0, steps_delta: 0 }

function Delta({ before, after, fmt, lowerIsBetter = true }) {
  const diff = after - before
  const good = Math.abs(diff) < 1e-9 ? null : lowerIsBetter ? diff < 0 : diff > 0
  return (
    <span className={`delta ${good === null ? '' : good ? 'good' : 'bad'}`}>
      {fmt(before)} → {fmt(after)}
    </span>
  )
}

export default function WhatIf({ pid }) {
  const [v, setV] = useState(ZERO)
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const timer = useRef(null)

  useEffect(() => { setV(ZERO); setRes(null) }, [pid])
  useEffect(() => {
    clearTimeout(timer.current)
    if (JSON.stringify(v) === JSON.stringify(ZERO)) { setRes(null); return }
    timer.current = setTimeout(() => {
      setBusy(true)
      postWhatIf(pid, v).then(setRes).catch(() => setRes(null)).finally(() => setBusy(false))
    }, 200)
    return () => clearTimeout(timer.current)
  }, [v, pid])

  const set = (k) => (e) => setV({ ...v, [k]: Number(e.target.value) })
  const m = res?.metrics
  return (
    <div className="card">
      <div className="card-head">
        <h2>What-if on the virtual patient</h2>
        <span className="sim">Simulation</span>
      </div>
      <div className="row" style={{ flexWrap: 'wrap', marginBottom: 6 }}>
        {PRESETS.map((p) => <button key={p.name} className="btn small" onClick={() => setV(p.v)}>{p.name}</button>)}
        <button className="btn small" onClick={() => setV(ZERO)}>Reset</button>
      </div>
      <div className="grid2">
        <div>
          <label className="slider"><span>Carbohydrate portions</span><input type="range" min="0.5" max="1.2" step="0.05" value={v.carb_scale} onChange={set('carb_scale')} /><output>{Math.round(v.carb_scale * 100)}%</output></label>
          <label className="slider"><span>Walk after meals</span><input type="range" min="0" max="45" step="5" value={v.walk_after_meals} onChange={set('walk_after_meals')} /><output>{v.walk_after_meals} min</output></label>
          <label className="slider"><span>Medication effect</span><input type="range" min="-40" max="20" step="1" value={v.baseline_shift} onChange={set('baseline_shift')} /><output>{v.baseline_shift > 0 ? '+' : ''}{v.baseline_shift} mg/dL</output></label>
          <label className="slider"><span>Daily steps</span><input type="range" min="-3000" max="8000" step="500" value={v.steps_delta} onChange={set('steps_delta')} /><output>{v.steps_delta > 0 ? '+' : ''}{v.steps_delta}</output></label>
        </div>
        <div>
          {!m && <div className="muted" style={{ padding: '14px 0' }}>Pick a scenario or move a slider. The twin re-runs this patient's last 14 days with the change and shows what happens to glucose and organ risk.</div>}
          {m && (
            <div style={{ opacity: busy ? 0.6 : 1 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <tbody>
                  <Row l="Time in range (70–180)"><Delta before={m.before.tir} after={m.after.tir} fmt={(x) => pct(x)} lowerIsBetter={false} /></Row>
                  <Row l="Time above 180"><Delta before={m.before.tar} after={m.after.tar} fmt={(x) => pct(x)} /></Row>
                  <Row l="Glucose variability (CV)"><Delta before={m.before.gv_cv} after={m.after.gv_cv} fmt={(x) => `${x.toFixed(0)}%`} /></Row>
                  <Row l="Estimated HbA1c (GMI)"><Delta before={m.before.gmi} after={m.after.gmi} fmt={(x) => x.toFixed(1)} /></Row>
                  <Row l="Liver steatosis risk, 12 months"><Delta before={res.liver.before.steatosis.at(-1)} after={res.liver.after.steatosis.at(-1)} fmt={(x) => pct(x)} /></Row>
                  <Row l="Advanced fibrosis, 12 months"><Delta before={res.liver.before.adv_fibrosis.at(-1)} after={res.liver.after.adv_fibrosis.at(-1)} fmt={(x) => pct(x, 1)} /></Row>
                  <Row l="Retinopathy progression, 2 years"><Delta before={res.eye.before} after={res.eye.after} fmt={(x) => pct(x)} /></Row>
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
      {res && (
        <div className="grid2" style={{ marginTop: 14 }}>
          <div>
            <h3 style={{ marginBottom: 6 }}>Yesterday's glucose, as lived vs with the change</h3>
            <LineChart height={190} yDomain={[40, 300]} xTickEvery={72} xLabel={(i) => fmtHM(res.glucose_last_day.start, i)}
              bands={[[70, 180]]}
              series={[{ name: 'As lived', y: res.glucose_last_day.before, color: 'var(--muted)' },
                { name: 'With the change', y: res.glucose_last_day.after, color: 'var(--accent)' }]} />
          </div>
          <div>
            <h3 style={{ marginBottom: 6 }}>Liver steatosis risk over 12 months</h3>
            <LineChart height={190} yDomain={[0, 1]} yFmt={(x) => `${Math.round(x * 100)}%`} xTickEvery={3} xLabel={(i) => `${i}m`}
              series={[{ name: 'Current habits', y: res.liver.before.steatosis, color: 'var(--muted)' },
                { name: 'With the change', y: res.liver.after.steatosis, color: 'var(--accent)' }]} />
          </div>
        </div>
      )}
      <div className="note">{res?.assumptions || 'Effect sizes are literature-informed assumptions shown for transparency. This is a simulation to support a conversation, not a prediction of the outcome.'}</div>
    </div>
  )
}

function Row({ l, children }) {
  return (
    <tr style={{ borderBottom: '1px solid var(--border)' }}>
      <td style={{ padding: '7px 0', color: 'var(--muted)' }}>{l}</td>
      <td style={{ padding: '7px 0', textAlign: 'right' }}>{children}</td>
    </tr>
  )
}
