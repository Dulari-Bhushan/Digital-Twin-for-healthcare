import { useEffect, useState } from 'react'
import { postWhatIf } from '../api'
import { DR, pct } from '../utils'

const TRY = [
  { label: 'Walk for 20 minutes after meals', body: { carb_scale: 1, walk_after_meals: 20, baseline_shift: 0, steps_delta: 2000 } },
  { label: 'Eat about a quarter less rice and roti', body: { carb_scale: 0.75, walk_after_meals: 0, baseline_shift: 0, steps_delta: 0 } },
  { label: 'Do both', body: { carb_scale: 0.75, walk_after_meals: 20, baseline_shift: 0, steps_delta: 2000 } },
]

function status(at) {
  if (at.p_hypo > 0.3 || at.glucose < 80)
    return { bg: '#b42318', title: 'Your sugar may drop soon', body: 'Have a small snack with some carbohydrate, such as a fruit or a biscuit, and check again in 15 minutes.', nudge: 'Eat a small snack now.' }
  if (at.p_hyper > 0.6 || at.glucose > 200)
    return { bg: '#b45309', title: 'Your sugar is likely to run high', body: 'A short walk after your meal helps your body use the sugar.', nudge: 'Take a 15-minute walk now.' }
  return { bg: '#0f766e', title: 'Your sugar is steady', body: 'You are doing well. Keep your usual routine.', nudge: 'Keep going: a walk after dinner keeps tonight smooth.' }
}

function Light({ label, level, text }) {
  const c = level === 'high' ? 'var(--high)' : level === 'mid' ? 'var(--med)' : 'var(--low)'
  return (
    <div className="organ">
      <div><b>{label}</b><div className="muted">{text}</div></div>
      <span className="light" style={{ background: c }} aria-label={level} />
    </div>
  )
}

export default function PatientView({ d, at }) {
  const s = status(at)
  const tl = d.liver.timeline
  const [pick, setPick] = useState(null)
  const [res, setRes] = useState(null)
  useEffect(() => { setPick(null); setRes(null) }, [d.profile.id])
  useEffect(() => { if (pick !== null) postWhatIf(d.profile.id, TRY[pick].body).then(setRes) }, [pick, d.profile.id])
  const liver = tl.steatosis.at(-1)
  const eye = d.eye.progression_2y
  const m = d.metrics
  return (
    <div className="patient-wrap">
      <div className="hero" style={{ background: s.bg }}>
        <h1>{s.title}</h1>
        <p>{s.body}</p>
        <p style={{ marginTop: 14, fontSize: 28, fontWeight: 700 }}>{Math.round(at.glucose)} <span style={{ fontSize: 15, fontWeight: 500 }}>mg/dL now</span></p>
      </div>
      <div className="nudge">
        <span style={{ fontSize: 28 }} aria-hidden="true">→</span>
        <div><div className="muted" style={{ fontSize: 12 }}>Today's one thing</div><div className="big">{s.nudge}</div></div>
      </div>
      <div className="card">
        <div className="card-head"><h2>How your sugar has been</h2></div>
        <p style={{ margin: 0, fontSize: 15 }}>Over the last two weeks, your sugar was in the healthy range <b>{pct(m.tir)}</b> of the time. A good goal is more than 70%.</p>
        <div className="bar" style={{ height: 10 }}><i style={{ width: pct(m.tir), background: m.tir > 0.7 ? 'var(--low)' : m.tir > 0.5 ? 'var(--med)' : 'var(--high)' }} /></div>
      </div>
      <div className="card">
        <div className="card-head"><h2>What your sugar does to your body</h2></div>
        <Light label="Liver" level={liver > 0.6 ? 'high' : liver > 0.3 ? 'mid' : 'low'} text={liver > 0.6 ? 'Fat is likely building up. Your doctor may want a scan.' : liver > 0.3 ? 'Some risk of fat build-up. Habits matter here.' : 'Looking healthy.'} />
        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '12px 0' }} />
        <Light label="Eyes" level={eye > 0.4 ? 'high' : eye > 0.2 ? 'mid' : 'low'} text={`${DR[d.eye.grade]}. ${eye > 0.4 ? 'Please keep your yearly eye check.' : 'Keep up your yearly eye check.'}`} />
        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '12px 0' }} />
        <Light label="Kidneys" level={d.profile.labs.uacr_mg_g >= 30 || d.profile.labs.egfr < 60 ? 'high' : 'low'} text={d.profile.labs.uacr_mg_g >= 30 || d.profile.labs.egfr < 60 ? 'Your doctor is watching your kidney tests.' : 'Tests look healthy.'} />
      </div>
      <div className="card">
        <div className="card-head"><h2>Try a change</h2><span className="sim">Simulation</span></div>
        <div className="row" style={{ flexWrap: 'wrap' }}>
          {TRY.map((t, i) => <button key={t.label} className={`btn ${pick === i ? 'primary' : ''}`} onClick={() => setPick(i)}>{t.label}</button>)}
        </div>
        {res && pick !== null && (
          <p style={{ fontSize: 15, marginBottom: 0 }}>
            If you <b>{TRY[pick].label.toLowerCase()}</b>, your time in the healthy range could move from <b>{pct(res.metrics.before.tir)}</b> to <b>{pct(res.metrics.after.tir)}</b>,
            and your chance of liver fat build-up over the next year from <b>{pct(res.liver.before.steatosis.at(-1))}</b> to <b>{pct(res.liver.after.steatosis.at(-1))}</b>.
          </p>
        )}
        <div className="note">This is an estimate to help you decide, not a promise. Talk to your doctor before changing your treatment. Hindi, Telugu and Kannada versions are planned.</div>
      </div>
    </div>
  )
}
