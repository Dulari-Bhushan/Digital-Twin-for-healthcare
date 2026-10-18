import { useEffect, useMemo, useState } from 'react'
import { getSeries, postWhatIf } from '../api'
import { fmtDay, fmtDT, dayStats } from '../utils'
import { DR, EyeArt, KidneyArt, LiverArt, Ring, SegRing, TONE, pct } from '../ui'

const TRY = [
  { e: '🚶', label: 'Walk 20 min after meals', body: { carb_scale: 1, walk_after_meals: 20, baseline_shift: 0, steps_delta: 2000 } },
  { e: '🍚', label: 'A quarter less rice and roti', body: { carb_scale: 0.75, walk_after_meals: 0, baseline_shift: 0, steps_delta: 0 } },
  { e: '✨', label: 'Do both', body: { carb_scale: 0.75, walk_after_meals: 20, baseline_shift: 0, steps_delta: 2000 } },
]

function status(at) {
  if (at.p_hypo > 0.3 || at.glucose < 80)
    return { tone: 'rose', e: '🍬', title: 'Your sugar may dip soon', body: 'Have a small snack with some carbohydrate and check again in 15 minutes.', nudge: 'Have a small snack now', nudgeE: '🍎' }
  if (at.p_hyper > 0.6 || at.glucose > 200)
    return { tone: 'peach', e: '🌤️', title: 'Your sugar may run high', body: 'A short walk after your meal helps your body use the sugar.', nudge: 'Take a 15-minute walk', nudgeE: '🚶' }
  return { tone: 'mint', e: '🌿', title: 'Your sugar is steady', body: 'You are doing well. Keep your usual routine.', nudge: 'Keep going: walk after dinner', nudgeE: '🌙' }
}

function Habit({ e, name, sub, value, goal, done, tone }) {
  const t = TONE[tone]
  const p = Math.max(0, Math.min(1, value))
  return (
    <div className="habit" style={{ background: done === false ? '#f6f5fb' : '#fff' }}>
      <div className="fill" style={{ width: `${p * 100}%`, background: t.bg }} />
      <div className="bub">{e}</div>
      <div><b style={{ fontSize: 15 }}>{name}</b><div className="muted" style={{ fontSize: 12, fontWeight: 600 }}>{sub}</div></div>
      <div style={{ fontWeight: 800, color: t.dd }}>{done === true ? '✓' : done === false ? '✕' : goal}</div>
    </div>
  )
}

function Today({ d, at, day, setDay, st, days, nudgeDone, setNudgeDone }) {
  const s = status(at)
  const t = TONE[s.tone]
  const cur = st[day]
  const habits = cur ? [
    { e: '🎯', name: 'Healthy range', sub: `${pct(cur.tir)} of the day, goal 70%`, value: cur.tir / 0.7, done: cur.tir >= 0.7, tone: 'mint' },
    { e: '👟', name: 'Steps', sub: `${Math.round(cur.steps).toLocaleString()} of 6,000`, value: cur.steps / 6000, done: cur.steps >= 6000, tone: 'sky' },
    { e: '🛡️', name: 'No low sugar', sub: cur.low > 0 ? `${pct(cur.low, 1)} of the day below 70` : 'No dips below 70', value: cur.low > 0 ? 0.2 : 1, done: cur.low === 0, tone: 'lav' },
    { e: '🍚', name: 'Carbs under 220 g', sub: `${Math.round(cur.carbs)} g in ${cur.meals} meals`, value: Math.min(1, 220 / Math.max(cur.carbs, 1)), done: cur.carbs <= 220, tone: 'butter' },
  ] : []
  return (
    <>
      <div className="p-h">Your day<br /><span style={{ color: 'var(--muted)', fontWeight: 600 }}>for today</span></div>
      <div className="days">
        {days.map((dd) => <button key={dd.k} className={`day ${day === dd.k ? 'on' : ''}`} onClick={() => setDay(dd.k)}>{dd.k === 0 ? 'TODAY' : dd.label}</button>)}
      </div>
      <div className="p-card" style={{ background: t.bg, display: 'flex', gap: 14, alignItems: 'center' }}>
        <Ring value={Math.min(1, Math.max(0, (at.glucose - 40) / 260))} size={108} stroke={13} color={t.d}>
          <div className="num" style={{ fontSize: 30, color: t.dd }}>{Math.round(at.glucose)}</div>
          <div style={{ fontSize: 10, fontWeight: 700, color: t.dd }}>mg/dL now</div>
        </Ring>
        <div>
          <div style={{ fontSize: 26 }}>{s.e}</div>
          <div style={{ fontWeight: 800, fontSize: 18, color: t.dd, lineHeight: 1.2 }}>{s.title}</div>
          <div style={{ fontSize: 13, color: t.dd, opacity: 0.85, marginTop: 4 }}>{s.body}</div>
        </div>
      </div>
      <div className="p-card" style={{ background: 'var(--butter)' }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--butter-dd)' }}>TODAY'S ONE THING</div>
        <div style={{ fontWeight: 800, fontSize: 20, margin: '4px 0', color: 'var(--butter-dd)' }}>{s.nudgeE} {s.nudge}</div>
        <button className={`big-btn ${nudgeDone ? 'done' : ''}`} onClick={() => setNudgeDone(!nudgeDone)}>{nudgeDone ? 'Well done! ✓' : 'Mark as done'}</button>
      </div>
      <div className="sect"><span>My habits</span><small>{habits.filter((h) => h.done).length} of {habits.length} completed</small></div>
      {habits.filter((h) => h.done).length > 0 && <div style={{ fontWeight: 800, fontSize: 13, color: 'var(--muted)', margin: '4px 0 8px' }}>Completed</div>}
      {habits.filter((h) => h.done).map((h) => <Habit key={h.name} {...h} />)}
      {habits.filter((h) => !h.done).length > 0 && <div style={{ fontWeight: 800, fontSize: 13, color: 'var(--muted)', margin: '8px 0' }}>Needs attention</div>}
      {habits.filter((h) => !h.done).map((h) => <Habit key={h.name} {...h} />)}
    </>
  )
}

function Insights({ series, st, d }) {
  const bars = useMemo(() => [...Array(7)].map((_, i) => ({ k: 6 - i, s: st[6 - i] })).filter((b) => b.s), [st])
  const last = st[0]
  const avg = d.metrics.tir
  return (
    <>
      <div className="p-h">Time in range<br /><span style={{ color: 'var(--muted)', fontWeight: 600 }}>weekly</span></div>
      <div className="p-card" style={{ background: 'var(--lav)' }}>
        <div className="bars" style={{ marginTop: 28 }}>
          {bars.map((b, i) => (
            <div key={b.k} className={`bar ${i === bars.length - 1 ? 'on' : ''}`} style={{ height: `${Math.max(4, b.s.tir * 100)}%` }}><b style={{ color: 'var(--lav-dd)' }}>{Math.round(b.s.tir * 100)}%</b></div>
          ))}
        </div>
        <div className="xl">{bars.map((b) => <span key={b.k}>{fmtDay(series.start, b.s.startIdx).split(' ')[0].toUpperCase()}</span>)}</div>
        <div style={{ display: 'flex', justifyContent: 'space-around', marginTop: 18 }}>
          <div style={{ textAlign: 'center' }}><div className="num" style={{ fontSize: 26, color: 'var(--lav-dd)' }}>{pct(last.tir)}</div><div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>Today</div></div>
          <div style={{ textAlign: 'center' }}><div className="num" style={{ fontSize: 26, color: 'var(--lav-dd)' }}>{pct(avg)}</div><div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>Two weeks</div></div>
        </div>
      </div>
      <div className="p-card" style={{ background: 'var(--mint)', display: 'flex', alignItems: 'center', gap: 16 }}>
        <SegRing size={118} stroke={16} segments={[{ v: d.metrics.tir, color: '#2fa176' }, { v: Math.max(0, 1 - d.metrics.tir - d.metrics.tbr), color: '#f6b26b' }, { v: d.metrics.tbr, color: '#e85f8b' }]}>
          <div className="num" style={{ fontSize: 24, color: 'var(--mint-dd)' }}>{pct(d.metrics.tir)}</div>
        </SegRing>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--mint-dd)', lineHeight: 1.7 }}>
          🟢 In range {pct(d.metrics.tir)}<br />🟠 Above range {pct(d.metrics.tar)}<br />🔴 Below range {pct(d.metrics.tbr, 1)}
        </div>
      </div>
      <p className="note" style={{ marginTop: 14 }}>A good goal is more than 70% of the day in the healthy range.</p>
    </>
  )
}

function Body({ d }) {
  const tl = d.liver.timeline
  const lv = tl.steatosis.at(-1)
  const ep = d.eye.progression_2y
  const lab = d.profile.labs
  const kidneyHigh = lab.uacr_mg_g >= 30 || lab.egfr < 60
  const card = (tone, art, title, level, text, ring) => (
    <div className="p-card" style={{ background: TONE[tone].bg }}>
      <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
        {ring}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><div className="organ-ill" style={{ width: 42, height: 42, borderRadius: 14 }}>{art}</div><b style={{ fontSize: 18, color: TONE[tone].dd }}>{title}</b></div>
          <div style={{ fontWeight: 800, color: TONE[tone].dd, marginTop: 6 }}>{level}</div>
          <div style={{ fontSize: 13, color: TONE[tone].dd, opacity: 0.85 }}>{text}</div>
        </div>
      </div>
    </div>
  )
  return (
    <>
      <div className="p-h">Your body<br /><span style={{ color: 'var(--muted)', fontWeight: 600 }}>what sugar does</span></div>
      {card(lv > 0.6 ? 'rose' : lv > 0.3 ? 'butter' : 'mint', <LiverArt size={30} />, 'Liver', lv > 0.6 ? 'Fat is likely building up' : lv > 0.3 ? 'Some risk of fat build-up' : 'Looking healthy',
        lv > 0.3 ? 'Habits matter here. Your doctor may suggest a scan.' : 'Keep your habits steady.',
        <Ring value={lv} size={84} stroke={11} color={lv > 0.6 ? '#e85f8b' : lv > 0.3 ? '#e0a912' : '#2fa176'}><div className="num" style={{ fontSize: 18 }}>{pct(lv)}</div></Ring>)}
      {card(ep > 0.4 ? 'rose' : ep > 0.2 ? 'butter' : 'mint', <EyeArt size={30} />, 'Eyes', DR[d.eye.grade], 'Keep your yearly eye check.',
        <Ring value={ep} size={84} stroke={11} color={ep > 0.4 ? '#e85f8b' : ep > 0.2 ? '#e0a912' : '#2fa176'}><div className="num" style={{ fontSize: 18 }}>{pct(ep)}</div></Ring>)}
      {card(kidneyHigh ? 'rose' : 'sky', <KidneyArt size={30} />, 'Kidneys', kidneyHigh ? 'Your doctor is watching' : 'Tests look healthy', `Kidney filter score ${lab.egfr.toFixed(0)}.`,
        <Ring value={Math.min(1, lab.egfr / 120)} size={84} stroke={11} color={kidneyHigh ? '#e85f8b' : '#4a8fe9'}><div className="num" style={{ fontSize: 18 }}>{lab.egfr.toFixed(0)}</div></Ring>)}
      <p className="note" style={{ marginTop: 14 }}>The rings show your estimated chance over the next year (liver, eyes) and your latest kidney score. These are estimates to guide a conversation with your doctor.</p>
    </>
  )
}

function Try({ pid }) {
  const [pick, setPick] = useState(2)
  const [res, setRes] = useState(null)
  useEffect(() => { setPick(2); setRes(null) }, [pid])
  useEffect(() => { if (pick !== null) postWhatIf(pid, TRY[pick].body).then(setRes) }, [pick, pid])
  return (
    <>
      <div className="p-h">Try a change<br /><span style={{ color: 'var(--muted)', fontWeight: 600 }}>see what could happen</span></div>
      <div style={{ display: 'grid', gap: 10, marginTop: 16 }}>
        {TRY.map((t, i) => (
          <button key={t.label} onClick={() => setPick(i)} className="habit" style={{ border: pick === i ? '2px solid var(--lav-d)' : '2px solid transparent', textAlign: 'left', background: pick === i ? 'var(--lav)' : '#f6f5fb' }}>
            <div className="bub">{t.e}</div><b>{t.label}</b><span style={{ color: 'var(--lav-d)', fontWeight: 800 }}>{pick === i ? '●' : '○'}</span>
          </button>
        ))}
      </div>
      {res && pick !== null && (
        <div className="p-card" style={{ background: 'var(--mint)' }}>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 14, alignItems: 'center' }}>
            <div style={{ textAlign: 'center' }}><Ring value={res.metrics.before.tir} size={92} stroke={12} color="#b9b3d8"><div className="num" style={{ fontSize: 20 }}>{pct(res.metrics.before.tir)}</div></Ring><div className="muted" style={{ fontSize: 11, fontWeight: 700 }}>Today</div></div>
            <b style={{ fontSize: 24, color: 'var(--mint-d)' }}>→</b>
            <div style={{ textAlign: 'center' }}><Ring value={res.metrics.after.tir} size={92} stroke={12} color="#2fa176"><div className="num" style={{ fontSize: 20, color: 'var(--mint-dd)' }}>{pct(res.metrics.after.tir)}</div></Ring><div style={{ fontSize: 11, fontWeight: 700, color: 'var(--mint-dd)' }}>With change</div></div>
          </div>
          <p style={{ marginTop: 14, fontWeight: 700, color: 'var(--mint-dd)', lineHeight: 1.5 }}>
            {res.metrics.after.tir - res.metrics.before.tir >= 0.02
              ? `Your time in the healthy range could go from ${pct(res.metrics.before.tir)} to ${pct(res.metrics.after.tir)}`
              : `Your sugar swings could calm down by about ${Math.max(0, Math.round((1 - res.metrics.after.gv_cv / res.metrics.before.gv_cv) * 100))}%`}
            , and your chance of liver fat build-up over a year from {pct(res.liver.before.steatosis.at(-1))} to {pct(res.liver.after.steatosis.at(-1))}.
          </p>
        </div>
      )}
      <p className="note" style={{ marginTop: 14 }}>This is a simulation to help you decide, not a promise. Talk to your doctor before changing your treatment. Hindi, Telugu and Kannada versions are planned.</p>
    </>
  )
}

export default function PatientApp({ d, at, pid }) {
  const [tab, setTab] = useState(Number(new URLSearchParams(window.location.search).get('tab') || 0))
  const [day, setDay] = useState(0)
  const [nudgeDone, setNudgeDone] = useState(false)
  const [series14, setSeries14] = useState(null)
  useEffect(() => { setSeries14(null); setDay(0); setNudgeDone(false); getSeries(pid, 14).then(setSeries14) }, [pid])
  const st = useMemo(() => (series14 ? [...Array(13)].map((_, k) => dayStats(series14, k)) : []), [series14])
  const days = useMemo(() => (series14 ? [3, 2, 1, 0].map((k) => ({ k, label: st[k] ? fmtDay(series14.start, st[k].startIdx) : '' })) : []), [series14, st])
  const tabs = [['🏠', 'Today'], ['📊', 'Insights'], ['🫀', 'Body'], ['✨', 'Try']]
  return (
    <div className="stage">
      <div className="blob" style={{ width: 340, height: 340, left: '8%', top: 60, background: 'var(--peach)' }} />
      <div className="blob" style={{ width: 280, height: 280, right: '9%', top: 140, background: 'var(--sky)' }} />
      <div className="blob" style={{ width: 220, height: 220, left: '20%', bottom: 30, background: 'var(--mint)' }} />
      <div className="phone">
        <div className="status"><span>9:41</span><span>●●● ▮</span></div>
        <div className="screen">
          {!series14 ? <div className="muted" style={{ padding: 30 }}>Loading…</div> : (
            tab === 0 ? <Today d={d} at={at} day={day} setDay={setDay} st={st} days={days} nudgeDone={nudgeDone} setNudgeDone={setNudgeDone} /> :
            tab === 1 ? <Insights series={series14} st={st} d={d} /> :
            tab === 2 ? <Body d={d} /> : <Try pid={pid} />
          )}
        </div>
        <div className="tabs">
          {tabs.map(([e, l], i) => <button key={l} className={`tab ${tab === i ? 'on' : ''}`} onClick={() => setTab(i)}><span>{e}</span>{l}</button>)}
        </div>
      </div>
    </div>
  )
}
