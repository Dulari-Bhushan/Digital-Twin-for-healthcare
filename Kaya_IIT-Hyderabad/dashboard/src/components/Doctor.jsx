import { useEffect, useRef, useState } from 'react'
import { postWhatIf } from '../api'
import { fmtDT, fmtHM, explain } from '../utils'
import { DR, EyeArt, KidneyArt, LiverArt, Ring, SegRing, TONE, pct, tierTone } from '../ui'
import GlucoseChart from './GlucoseChart'
import LineChart from './LineChart'

const FEAT = {
  age: ['Age', ' y'], male: ['Male sex', ''], bmi: ['BMI', ''], waist_cm: ['Waist', ' cm'], alt: ['ALT', ' U/L'], ast: ['AST', ' U/L'],
  platelets: ['Platelets', ''], hba1c: ['HbA1c', '%'], hdl: ['HDL', ' mg/dL'], diabetes: ['Diabetes', ''], sbp: ['Systolic BP', ' mmHg'], dbp: ['Diastolic BP', ' mmHg'],
}

/** Top drivers of a model's risk for this patient (SHAP): bars grow with influence, rose raises risk, mint lowers it. */
function Drivers({ items, title }) {
  if (!items || !items.length) return null
  const top = items.slice(0, 4)
  const mx = Math.max(...top.map((i) => Math.abs(i.shap)), 0.01)
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--muted)', marginBottom: 6 }}>{title}</div>
      {top.map((it) => {
        const [name, unit] = FEAT[it.feature] || [it.feature, '']
        const up = it.shap > 0
        return (
          <div key={it.feature} style={{ display: 'grid', gridTemplateColumns: '1fr 70px', gap: 8, alignItems: 'center', marginBottom: 5 }}>
            <div style={{ fontSize: 12, fontWeight: 700 }}>{name} {it.feature === 'diabetes' || it.feature === 'male' ? (it.value ? 'yes' : 'no') : (Math.abs(it.value) >= 10 ? Math.round(it.value) : it.value) + unit}
              <span style={{ color: up ? 'var(--rose-dd)' : 'var(--mint-dd)', fontWeight: 800 }}> {up ? 'raises' : 'lowers'}</span></div>
            <div style={{ height: 8, borderRadius: 6, background: 'rgba(255,255,255,.8)' }}>
              <div style={{ width: `${(Math.abs(it.shap) / mx) * 100}%`, height: '100%', borderRadius: 6, background: up ? 'var(--rose-d)' : 'var(--mint-d)' }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

const avatarOf = (p) => (p.sex === 'F' ? (p.age >= 60 ? '👵' : '👩') : p.age >= 60 ? '👴' : '👨')

export function Sidebar({ patients, selected, onSelect }) {
  return (
    <aside className="side">
      <h2>Today's priorities</h2>
      <div className="muted" style={{ fontSize: 13, padding: '0 6px 4px' }}>{patients.length} patients · sorted by who needs you most</div>
      {patients.map((p) => {
        const t = TONE[tierTone(p.tier)]
        return (
          <button key={p.id} className={`pt ${selected === p.id ? 'on' : ''}`} onClick={() => onSelect(p.id)}>
            <span className="av" style={{ background: t.bg, color: t.dd, fontSize: 22 }}>{avatarOf(p)}</span>
            <span><b>Patient {p.id}</b><small>{p.age} y · {p.sex === 'F' ? 'female' : 'male'} · HbA1c {p.hba1c}</small></span>
            <span className="chip" style={{ background: t.bg, color: t.dd }}>{p.tier}</span>
            <span className="why">{p.reasons.length ? p.reasons.join(' · ') : 'Stable, no flags'}</span>
          </button>
        )
      })}
    </aside>
  )
}

export function Hero({ d }) {
  const p = d.profile
  const t = TONE[tierTone(d.summary.tier)]
  return (
    <div className="card lav hero">
      <div className="avatar">{avatarOf({ sex: p.sex, age: p.age })}</div>
      <div>
        <h1>Patient {p.id}</h1>
        <div className="facts">
          <span className="chip">{p.age} y, {p.sex === 'F' ? 'female' : 'male'}</span>
          <span className="chip">BMI {p.bmi}</span>
          <span className="chip">HbA1c {p.hba1c}%</span>
          <span className="chip">T2D {p.duration_yrs} y</span>
          <span className="chip">BP {p.sbp}/{p.dbp}</span>
          <span className="chip">{p.metformin ? '💊 Metformin' : 'No metformin'}</span>
          {p.on_insulin_or_su && <span className="chip rose">⚠️ Low-glucose risk drugs</span>}
          <span className="chip sky">🧬 PNPLA3 {p.pnpla3_g_alleles} · TCF7L2 {p.tcf7l2_t_alleles}</span>
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <a className="btn sm go" style={{ textDecoration: 'none', marginBottom: 10 }} href={`/api/patients/${p.id}/report.pdf`} target="_blank" rel="noreferrer">📄 Download clinical summary</a>
        <br />
        <span className="chip" style={{ background: t.bg, color: t.dd, fontSize: 14, padding: '9px 16px' }}>
          {d.summary.tier === 'high' ? '🔥' : d.summary.tier === 'medium' ? '👀' : '🌿'} {d.summary.tier} priority
        </span>
        <div style={{ marginTop: 10, display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end', maxWidth: 360 }}>
          {d.summary.reasons.map((r) => <span key={r} className="chip">{r}</span>)}
        </div>
      </div>
    </div>
  )
}

export function GlucoseCard({ series, cursor, at, metrics, playing, setPlaying, setCursor, range, live }) {
  const g = series.glucose
  const slope = cursor >= 6 ? (g[cursor] - g[cursor - 6]) / 30 : 0
  const arrow = Math.abs(slope) < 0.4 ? '→' : slope > 0 ? (slope > 1.5 ? '⇈' : '↗') : slope < -1.5 ? '⇊' : '↘'
  const tones = ['sky', 'lav', 'peach']
  return (
    <div className="card soft">
      <div className="card-h">
        <h2>Glucose twin</h2>
        <span className="chip lav">{fmtDT(series.start, cursor)}</span>
        {live.on && <span className="chip rose"><span className="livedot" /> LIVE · model runs on every reading{live.latency != null ? ` · ${live.latency} ms` : ''}</span>}
        <span className="sp" style={{ flex: 1 }} />
        <button className={`btn sm ${live.active ? '' : 'go'}`} onClick={live.active ? live.stop : live.start}>
          {live.active ? '■ Stop live feed' : '● Go live'}
        </button>
        <span className="chip mint">Real-data validated</span>
      </div>
      <div className="row wrap" style={{ alignItems: 'stretch', gap: 14, marginBottom: 14 }}>
        <div className="bubble" style={{ background: 'var(--lav)', minWidth: 190 }}>
          <div className="t">Glucose now</div>
          <div className="v" style={{ fontSize: 44 }}>{Math.round(at.glucose)}<span style={{ fontSize: 22, marginLeft: 6 }}>{arrow}</span></div>
          <div className="r">mg/dL · TIR {pct(metrics.tir)} · GV {metrics.gv_cv.toFixed(0)}%</div>
        </div>
        <div className="bubbles" style={{ flex: 1, minWidth: 320 }}>
          {at.forecast.map((f, i) => (
            <div className="bubble" key={f.minutes} style={{ background: TONE[tones[i]].bg, color: TONE[tones[i]].dd }}>
              <div className="t">In {f.minutes} min</div>
              <div className="v">{Math.round(f.median)}</div>
              <div className="r">{Math.round(f.lo)}–{Math.round(f.hi)} (80%)</div>
            </div>
          ))}
        </div>
      </div>
      <GlucoseChart series={series} cursor={cursor} />
      {live.on ? (
        <div className="player"><div style={{ flex: 1, fontSize: 13, fontWeight: 700, color: 'var(--rose-dd)' }}>Streaming a simulated wearable feed: a new reading every 5 minutes of patient time. {live.count} received. The twin forecasts from each one as it arrives.</div></div>
      ) : (
      <div className="player">
        <button className="play" aria-label={playing ? 'Pause' : 'Play'}
          onClick={() => { if (cursor >= range[1]) setCursor(range[0]); setPlaying(!playing) }}>{playing ? '❚❚' : '▶'}</button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)', marginBottom: 6 }}>Replay the last 3 days: the twin forecasts, then reality unfolds</div>
          <input type="range" min={range[0]} max={range[1]} step="1" value={cursor} aria-label="Replay position"
            onChange={(e) => { setPlaying(false); setCursor(Number(e.target.value)) }} />
        </div>
        <button className="btn sm" onClick={() => { setPlaying(false); setCursor(range[1]) }}>Now</button>
      </div>
      )}
    </div>
  )
}

export function ProbCard({ at }) {
  const items = [
    { label: 'High in 2 h', p: at.p_hyper, tone: 'peach', color: '#f0814f', sub: 'chance of > 180' },
    { label: 'Low in 2 h', p: at.p_hypo, tone: 'sky', color: '#4a8fe9', sub: 'chance of < 70' },
  ]
  return (
    <div className="card peach">
      <div className="card-h"><h2>Next 2 hours</h2><span className="chip">Calibrated</span></div>
      <div className="row" style={{ justifyContent: 'space-around' }}>
        {items.map((it) => (
          <div key={it.label} style={{ textAlign: 'center' }}>
            <Ring value={it.p} size={112} stroke={14} color={it.color}>
              <div className="num" style={{ fontSize: 26 }}>{pct(it.p)}</div>
            </Ring>
            <div style={{ fontWeight: 800, marginTop: 8 }}>{it.label}</div>
            <div className="muted" style={{ fontSize: 12 }}>{it.sub}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function RangeCard({ metrics }) {
  const mid = Math.max(0, 1 - metrics.tir - metrics.tbr - metrics.tar)
  return (
    <div className="card mint" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="card-h"><h2>Time in range</h2><span className="chip">14 days</span></div>
      <div className="row" style={{ gap: 18, flex: 1, justifyContent: 'center' }}>
        <SegRing size={132} stroke={18}
          segments={[{ v: metrics.tir, color: '#2fa176' }, { v: metrics.tar + mid, color: '#f6b26b' }, { v: metrics.tbr, color: '#e85f8b' }]}>
          <div className="num" style={{ fontSize: 30 }}>{pct(metrics.tir)}</div>
          <div className="muted" style={{ fontSize: 11, fontWeight: 700 }}>in range</div>
        </SegRing>
        <div style={{ display: 'grid', gap: 8, fontSize: 13, fontWeight: 700 }}>
          <span><i style={{ background: '#2fa176', display: 'inline-block', width: 12, height: 12, borderRadius: 4, marginRight: 8 }} />70–180: {pct(metrics.tir)}</span>
          <span><i style={{ background: '#f6b26b', display: 'inline-block', width: 12, height: 12, borderRadius: 4, marginRight: 8 }} />Above 180: {pct(metrics.tar)}</span>
          <span><i style={{ background: '#e85f8b', display: 'inline-block', width: 12, height: 12, borderRadius: 4, marginRight: 8 }} />Below 70: {pct(metrics.tbr, 1)}</span>
          <span className="muted">Est. HbA1c {metrics.gmi.toFixed(1)}</span>
        </div>
      </div>
    </div>
  )
}

export function Organs({ d }) {
  const tl = d.liver.timeline
  const lab = d.profile.labs
  const cl = d.profile.clinic
  const lv = tl.steatosis.at(-1)
  const kp = d.kidney.projection
  const stage = lab.egfr >= 90 ? 'G1' : lab.egfr >= 60 ? 'G2' : lab.egfr >= 45 ? 'G3a' : lab.egfr >= 30 ? 'G3b' : 'G4+'
  const ep = d.eye.progression_2y
  return (
    <>
      <div className="card butter c4">
        <div className="organ-top">
          <div className="organ-ill"><LiverArt size={44} /></div>
          <div><h2>Liver</h2><span className="chip mint" style={{ marginTop: 4 }}>Real-data model</span></div>
        </div>
        <div className="row" style={{ gap: 16 }}>
          <Ring value={lv} size={116} stroke={14} color={lv >= 0.6 ? '#e85f8b' : lv >= 0.3 ? '#f0814f' : '#2fa176'}>
            <div className="num" style={{ fontSize: 26 }}>{pct(lv)}</div>
            <div className="muted" style={{ fontSize: 10, fontWeight: 700 }}>fat risk, 12 m</div>
          </Ring>
          <div style={{ flex: 1 }}>
            <div className="stat" style={{ marginBottom: 8 }}><div className="l">Now → 12 months</div><div className="v">{pct(tl.steatosis[0])} → {pct(lv)}</div></div>
            <div className="stat"><div className="l">Advanced fibrosis</div><div className="v">{pct(tl.adv_fibrosis[0], 1)} → {pct(tl.adv_fibrosis.at(-1), 1)}</div></div>
          </div>
        </div>
        <Drivers items={d.explain?.steatosis} title="What drives this liver risk" />
        <div className="note">Baseline from a model validated on real NHANES FibroScan data (AUROC 0.83). The drift from glucose habits is a simulation with editable assumptions. Latest simulated FibroScan {cl.liver_stiffness_kpa} kPa.</div>
      </div>

      <div className="card rose c4">
        <div className="organ-top">
          <div className="organ-ill"><EyeArt size={44} /></div>
          <div><h2>Eyes</h2><span className="chip mint" style={{ marginTop: 4 }}>Grader: real data</span></div>
        </div>
        <div className="photos">
          <figure style={{ margin: 0 }}><img src={`/eye-img/grade${d.eye.grade}.jpg`} alt={`Example fundus photo, grade ${d.eye.grade}`} /><figcaption>Example photo</figcaption></figure>
          <figure style={{ margin: 0 }}><img src={`/eye-img/grade${d.eye.grade}_cam.jpg`} alt="Grad-CAM heatmap" /><figcaption>Where the model looked</figcaption></figure>
        </div>
        <div className="row" style={{ gap: 10 }}>
          <div className="stat" style={{ flex: 1 }}><div className="l">Grade</div><div className="v" style={{ fontSize: 17 }}>{DR[d.eye.grade]}</div></div>
          <div className="stat" style={{ flex: 1 }}><div className="l">2-year progression</div><div className="v">{pct(ep)}</div></div>
        </div>
        <div className="note">Photos are representative IDRiD images (CC BY 4.0) of the recorded grade. Grader: APTOS kappa 0.89, Indian IDRiD 0.71 after fine-tuning. Progression risk is a simulation.</div>
      </div>

      <div className="card sky c4">
        <div className="organ-top">
          <div className="organ-ill"><KidneyArt size={44} /></div>
          <div><h2>Kidneys</h2><span className="chip mint" style={{ marginTop: 4 }}>Real-data model</span></div>
        </div>
        <div className="row" style={{ gap: 16 }}>
          <Ring value={kp.albuminuria.at(-1)} size={112} stroke={14} color={kp.albuminuria.at(-1) >= 0.5 ? '#e85f8b' : kp.albuminuria.at(-1) >= 0.25 ? '#f0814f' : '#4a8fe9'}>
            <div className="num" style={{ fontSize: 24 }}>{pct(kp.albuminuria.at(-1))}</div>
            <div className="muted" style={{ fontSize: 10, fontWeight: 700 }}>albumin, 12 m</div>
          </Ring>
          <div style={{ flex: 1, display: 'grid', gap: 8 }}>
            <div className="stat"><div className="l">eGFR now → in 5 years</div><div className="v">{lab.egfr.toFixed(0)} → {kp.egfr.at(-1).toFixed(0)}</div></div>
            <div className="stat"><div className="l">Urine albumin / creatinine</div>
              <div className="v" style={{ color: lab.uacr_mg_g >= 30 ? 'var(--rose-dd)' : 'inherit' }}>{lab.uacr_mg_g.toFixed(0)} <span style={{ fontSize: 12 }}>mg/g</span></div></div>
          </div>
        </div>
        <div style={{ marginTop: 10 }}>
          <LineChart height={130} yDomain={[Math.floor(Math.min(...kp.egfr) / 10) * 10 - 5, Math.ceil(Math.max(...kp.egfr) / 10) * 10 + 5]} xTickEvery={2} xLabel={(i) => `${kp.month[i] / 12}y`}
            series={[{ name: 'eGFR at current habits', y: kp.egfr, color: '#4a8fe9' }]} />
        </div>
        <Drivers items={d.explain?.albuminuria} title="What drives the albuminuria risk" />
        <div className="row" style={{ gap: 8, marginTop: 6 }}>
          <span className="chip">{stage}</span>
          <span className="chip">{kp.slope_per_year.toFixed(1)} per year</span>
          <span className="chip" style={{ background: kp.years_to_egfr60 && kp.years_to_egfr60 < 10 ? 'var(--rose)' : undefined }}>{lab.egfr < 60 ? 'Already below 60' : `eGFR 60 in ~${kp.years_to_egfr60} y`}</span>
        </div>
        <div className="note">Albuminuria and reduced-eGFR risk come from a model validated on real NHANES data (AUROC 0.76 and 0.85). The eGFR path and glucose-driven drift are simulations with editable assumptions.</div>
      </div>
    </>
  )
}

const PRESETS = [
  { e: '🚶', name: 'Walk after meals', v: { carb_scale: 1, walk_after_meals: 20, baseline_shift: 0, steps_delta: 2000 } },
  { e: '🍚', name: 'Smaller portions', v: { carb_scale: 0.75, walk_after_meals: 0, baseline_shift: 0, steps_delta: 0 } },
  { e: '💊', name: 'Medication tuned', v: { carb_scale: 1, walk_after_meals: 0, baseline_shift: -15, steps_delta: 0 } },
  { e: '✨', name: 'All three', v: { carb_scale: 0.75, walk_after_meals: 20, baseline_shift: -12, steps_delta: 2000 } },
]
const ZERO = { carb_scale: 1, walk_after_meals: 0, baseline_shift: 0, steps_delta: 0 }

function Delta({ label, before, after, fmt, lowerBetter = true }) {
  const same = Math.abs(after - before) < 1e-9
  const better = lowerBetter ? after < before : after > before
  const t = TONE[same ? 'lav' : better ? 'mint' : 'rose']
  const arrow = same ? '' : after > before ? '↑' : '↓'
  return (
    <div className="delta" style={{ background: t.bg, color: t.dd }}>
      <div className="l">{label}</div>
      <div className="v"><s>{fmt(before)}</s> → {fmt(after)} <span>{arrow}</span></div>
    </div>
  )
}

export function WhatIfStudio({ pid }) {
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
    }, 180)
    return () => clearTimeout(timer.current)
  }, [v, pid])
  const set = (k) => (e) => setV({ ...v, [k]: Number(e.target.value) })
  const m = res?.metrics
  const ctl = (emoji, label, key, min, max, step, out) => (
    <div className="ctl">
      <div className="bub" style={{ fontSize: 22 }}>{emoji}</div>
      <div><b>{label}</b><input type="range" min={min} max={max} step={step} value={v[key]} onChange={set(key)} /></div>
      <output>{out}</output>
    </div>
  )
  return (
    <div className="card lav">
      <div className="card-h">
        <h2>What-if studio ✨</h2>
        <span className="chip">Simulation, not a prediction</span>
      </div>
      <div className="study">
        <div>
          <div className="row wrap" style={{ gap: 8, marginBottom: 14 }}>
            {PRESETS.map((p) => (
              <button key={p.name} className={`preset ${JSON.stringify(v) === JSON.stringify(p.v) ? 'on' : ''}`} onClick={() => setV(p.v)}>{p.e} {p.name}</button>
            ))}
            <button className="preset" onClick={() => setV(ZERO)}>↺ Reset</button>
          </div>
          {ctl('🍚', 'Carbohydrate portions', 'carb_scale', 0.5, 1.2, 0.05, `${Math.round(v.carb_scale * 100)}%`)}
          {ctl('🚶', 'Walk after meals', 'walk_after_meals', 0, 45, 5, `${v.walk_after_meals} min`)}
          {ctl('💊', 'Medication effect', 'baseline_shift', -40, 20, 1, `${v.baseline_shift > 0 ? '+' : ''}${v.baseline_shift} mg/dL`)}
          {ctl('👟', 'Daily steps', 'steps_delta', -3000, 8000, 500, `${v.steps_delta > 0 ? '+' : ''}${v.steps_delta}`)}
        </div>
        <div style={{ opacity: busy ? 0.6 : 1, transition: 'opacity .2s' }}>
          {!m && (
            <div className="stat" style={{ padding: 22, textAlign: 'center' }}>
              <div style={{ fontSize: 40 }}>🧪</div>
              <div style={{ fontWeight: 800, fontSize: 17, margin: '6px 0' }}>Pick a change to try</div>
              <div className="muted">The twin replays this patient's last 14 days with the change and shows what happens to glucose and to the organs.</div>
            </div>
          )}
          {m && (
            <>
              <div className="row" style={{ gap: 18, marginBottom: 14, justifyContent: 'center' }}>
                <div style={{ textAlign: 'center' }}>
                  <Ring value={m.before.tir} size={104} stroke={13} color="#b9b3d8"><div className="num" style={{ fontSize: 22 }}>{pct(m.before.tir)}</div></Ring>
                  <div className="muted" style={{ fontSize: 12, fontWeight: 700, marginTop: 4 }}>Today</div>
                </div>
                <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--lav-d)' }}>→</div>
                <div style={{ textAlign: 'center' }}>
                  <Ring value={m.after.tir} size={104} stroke={13} color="#2fa176"><div className="num" style={{ fontSize: 22 }}>{pct(m.after.tir)}</div></Ring>
                  <div style={{ fontSize: 12, fontWeight: 700, marginTop: 4, color: 'var(--mint-dd)' }}>With the change</div>
                </div>
              </div>
              <div className="deltas">
                <Delta label="Time above 180" before={m.before.tar} after={m.after.tar} fmt={(x) => pct(x)} />
                <Delta label="Variability (CV)" before={m.before.gv_cv} after={m.after.gv_cv} fmt={(x) => `${x.toFixed(0)}%`} />
                <Delta label="Liver fat risk, 12 m" before={res.liver.before.steatosis.at(-1)} after={res.liver.after.steatosis.at(-1)} fmt={(x) => pct(x)} />
                <Delta label="Fibrosis risk, 12 m" before={res.liver.before.adv_fibrosis.at(-1)} after={res.liver.after.adv_fibrosis.at(-1)} fmt={(x) => pct(x, 1)} />
                <Delta label="Eye progression, 2 y" before={res.eye.before} after={res.eye.after} fmt={(x) => pct(x)} />
                <Delta label="eGFR in 5 years" before={res.kidney.before.egfr.at(-1)} after={res.kidney.after.egfr.at(-1)} fmt={(x) => x.toFixed(0)} lowerBetter={false} />
                <Delta label="Albuminuria risk, 12 m" before={res.kidney.before.albuminuria.at(-1)} after={res.kidney.after.albuminuria.at(-1)} fmt={(x) => pct(x)} />
              </div>
            </>
          )}
        </div>
      </div>
      {res && (
        <div className="study" style={{ marginTop: 18 }}>
          <div className="card soft" style={{ boxShadow: 'none' }}>
            <h3 style={{ marginBottom: 8 }}>Yesterday, as lived vs with the change</h3>
            <LineChart height={190} yDomain={[40, 300]} xTickEvery={72} xLabel={(i) => fmtHM(res.glucose_last_day.start, i)} band={[70, 180]}
              series={[{ name: 'As lived', y: res.glucose_last_day.before, color: '#b9b3d8' }, { name: 'With the change', y: res.glucose_last_day.after, color: '#2fa176' }]} />
          </div>
          <div className="card soft" style={{ boxShadow: 'none' }}>
            <h3 style={{ marginBottom: 8 }}>Liver fat risk over 12 months</h3>
            <LineChart height={190} yDomain={[0, 1]} yFmt={(x) => `${Math.round(x * 100)}%`} xTickEvery={3} xLabel={(i) => `${i}m`}
              series={[{ name: 'Current habits', y: res.liver.before.steatosis, color: '#b9b3d8' }, { name: 'With the change', y: res.liver.after.steatosis, color: '#7160e6' }]} />
          </div>
        </div>
      )}
      <div className="note">{res?.assumptions || 'Effect sizes are literature-informed assumptions shown for transparency.'}</div>
    </div>
  )
}

export function AlertsCard({ alerts, series }) {
  const list = [...alerts].reverse().slice(0, 6)
  return (
    <div className="card soft">
      <div className="card-h"><h2>Alert timeline 🔔</h2><span className="chip peach">About 1 false alert per patient-day</span></div>
      <div className="tl">
        {list.length === 0 && <div className="muted">No alerts in this window. 🌿</div>}
        {list.map((a, i) => {
          const idx = a.t - series.t0
          const low = a.type === 'hypo'
          const t = TONE[low ? 'rose' : 'peach']
          return (
            <div className="al" key={i}>
              <div className="bub" style={{ background: t.bg, fontSize: 20 }}>{low ? '🍬' : '📈'}</div>
              <div>
                <b>{low ? 'Low glucose expected' : 'High glucose expected'}</b>
                <span className="chip" style={{ background: t.bg, color: t.dd, marginLeft: 8 }}>{pct(a.prob)}</span>
                <div className="muted" style={{ fontSize: 13, marginTop: 2 }}>Why: {explain(series, idx)}</div>
              </div>
              <span className="muted" style={{ fontSize: 12, fontWeight: 700 }}>{fmtDT(series.start, idx)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
