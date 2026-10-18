import { Logo } from '../ui'
import { useEffect, useMemo, useState } from 'react'
import { getLog, getSeries, postLog, postWhatIf } from '../api'
import { LANGS, makeT } from '../i18n'
import { getVoiceStatus } from '../voice'
import { dayStats, fmtHM } from '../utils'
import Assistant from './Assistant'
import { NowCard, QuickLog } from './PatientActions'
import { PatientReports } from './Reports'
import { EyeArt, KidneyArt, LiverArt, Ring, SegRing, TONE, pct } from '../ui'

const TRY = [
  { e: '🚶', key: 'try_walk', body: { carb_scale: 1, walk_after_meals: 20, baseline_shift: 0, steps_delta: 2000 } },
  { e: '🍚', key: 'try_less', body: { carb_scale: 0.75, walk_after_meals: 0, baseline_shift: 0, steps_delta: 0 } },
  { e: '✨', key: 'try_both', body: { carb_scale: 0.75, walk_after_meals: 20, baseline_shift: 0, steps_delta: 2000 } },
]

const dayName = (series, startIdx, locale, long = false) =>
  new Date(new Date(series.start).getTime() + startIdx * 5 * 60000).toLocaleDateString(locale, { weekday: 'short', day: long ? 'numeric' : undefined, timeZone: 'UTC' })

function status(at) {
  if (at.p_hypo > 0.3 || at.glucose < 80) return { tone: 'rose', e: '🍬', k: 'st_low', nudgeE: '🍎' }
  if (at.p_hyper > 0.6 || at.glucose > 200) return { tone: 'peach', e: '🌤️', k: 'st_high', nudgeE: '🚶' }
  return { tone: 'mint', e: '🌿', k: 'st_ok', nudgeE: '🌙' }
}

function Habit({ e, name, sub, value, goal, done, tone }) {
  const t = TONE[tone]
  const p = Math.max(0, Math.min(1, value))
  return (
    <div className="habit" style={{ background: done === false ? '#f0f5f4' : '#fff' }}>
      <div className="fill" style={{ width: `${p * 100}%`, background: t.bg }} />
      <div className="bub">{e}</div>
      <div><b style={{ fontSize: 15 }}>{name}</b><div className="muted" style={{ fontSize: 12, fontWeight: 600 }}>{sub}</div></div>
      <div style={{ fontWeight: 800, color: t.dd }}>{done === true ? '✓' : done === false ? '✕' : goal}</div>
    </div>
  )
}

function DayChart({ st, series, color }) {
  const g = st.glucose
  const W = 320, H = 132, pl = 28, pr = 8, pt = 8, pb = 20
  const ymax = Math.max(260, Math.ceil(Math.max(...g) / 50) * 50), ymin = 40
  const x = (i) => pl + (i / (g.length - 1)) * (W - pl - pr)
  const y = (v) => pt + (H - pt - pb) * (1 - (Math.min(Math.max(v, ymin), ymax) - ymin) / (ymax - ymin))
  const pts = g.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Glucose through the day">
      <rect x={pl} y={y(180)} width={W - pl - pr} height={y(70) - y(180)} rx="8" fill="#dfeee2" opacity=".8" />
      {[70, 180, 250].filter((v) => v <= ymax).map((v) => (
        <g key={v}><line x1={pl} x2={W - pr} y1={y(v)} y2={y(v)} stroke="rgba(28,52,50,.08)" strokeDasharray="3 4" /><text x={pl - 4} y={y(v) + 3} fontSize="9" fontWeight="700" fill="#667b78" textAnchor="end">{v}</text></g>
      ))}
      {[0, 72, 144, 216].map((i) => <text key={i} x={x(i)} y={H - 5} fontSize="9" fontWeight="700" fill="#667b78" textAnchor="middle">{fmtHM(series.start, st.startIdx + i)}</text>)}
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2.4" strokeLinejoin="round" strokeLinecap="round" />
      {g.map((v, i) => (v < 70 ? <circle key={`l${i}`} cx={x(i)} cy={y(v)} r="2.6" fill="#c4645b" /> : null))}
      {st.mealSeries.map((c, i) => (c > 0 ? <circle key={`m${i}`} cx={x(i)} cy={H - pb - 3} r={2.5 + Math.min(c, 120) / 40} fill="#f5d58f" stroke="#E9A23B" strokeWidth="1" /> : null))}
    </svg>
  )
}

function Today({ t, name, series, at, day, setDay, st, days, log, logIt, risky }) {
  const s = status(at)
  const cur = st[day]
  const live = day === 0
  const tone = live ? s.tone : cur.tir >= 0.6 ? 'mint' : cur.tir >= 0.3 ? 'butter' : 'rose'
  const tn = TONE[tone]
  const kind = cur.tir >= 0.6 ? 'day_good' : cur.tir >= 0.3 ? 'day_ok' : 'day_tough'
  const spikeTime = fmtHM(series.start, cur.peakIdx)
  const habits = [
    { e: '🎯', name: t('habit_range'), sub: t('habit_range_sub', { pct: pct(cur.tir) }), value: cur.tir / 0.7, done: cur.tir >= 0.7, tone: 'mint' },
    { e: '👟', name: t('habit_steps'), sub: t('habit_steps_sub', { n: Math.round(cur.steps).toLocaleString() }), value: cur.steps / 6000, done: cur.steps >= 6000, tone: 'sky' },
    { e: '🛡️', name: t('habit_nolow'), sub: cur.low > 0 ? t('day_low', { m: cur.lowMin }) : t('habit_nolow_sub_ok'), value: cur.low > 0 ? 0.2 : 1, done: cur.low === 0, tone: 'lav' },
    { e: '🍚', name: t('habit_carbs'), sub: t('habit_carbs_sub', { g: Math.round(cur.carbs), m: cur.meals }), value: Math.min(1, 220 / Math.max(cur.carbs, 1)), done: cur.carbs <= 220, tone: 'butter' },
  ]
  const ok = habits.filter((h) => h.done)
  const bad = habits.filter((h) => !h.done)
  return (
    <>
      <div className="muted" style={{ fontWeight: 700, fontSize: 13 }}>{t('hello', { name: name.split(' ')[0] })}</div>
      <div className="p-h">{t('today_title1')}<br /><span style={{ color: 'var(--muted)', fontWeight: 600 }}>{t('today_title2')}</span></div>
      <div className="days">
        {days.map((dd) => <button key={dd.k} className={`day ${day === dd.k ? 'on' : ''}`} onClick={() => setDay(dd.k)}>{dd.k === 0 ? t('day_today') : dd.label}</button>)}
      </div>
      {live ? (
        <div className="p-card" style={{ background: tn.bg, display: 'flex', gap: 14, alignItems: 'center' }}>
          <Ring value={Math.min(1, Math.max(0, (at.glucose - 40) / 260))} size={108} stroke={13} color={tn.d}>
            <div className="num" style={{ fontSize: 30, color: tn.dd }}>{Math.round(at.glucose)}</div>
            <div style={{ fontSize: 10, fontWeight: 700, color: tn.dd }}>{t('mgdl_now')}</div>
          </Ring>
          <div>
            <div style={{ fontSize: 26 }}>{s.e}</div>
            <div style={{ fontWeight: 800, fontSize: 18, color: tn.dd, lineHeight: 1.25 }}>{t(`${s.k}_title`)}</div>
            <div style={{ fontSize: 13, color: tn.dd, opacity: 0.85, marginTop: 4 }}>{t(`${s.k}_body`)}</div>
          </div>
        </div>
      ) : (
        <div className="p-card" style={{ background: tn.bg, display: 'flex', gap: 14, alignItems: 'center' }}>
          <Ring value={cur.tir} size={108} stroke={13} color={tn.d}>
            <div className="num" style={{ fontSize: 28, color: tn.dd }}>{pct(cur.tir)}</div>
            <div style={{ fontSize: 10, fontWeight: 700, color: tn.dd }}>{t('habit_range')}</div>
          </Ring>
          <div>
            <div style={{ fontWeight: 800, fontSize: 19, color: tn.dd, lineHeight: 1.25 }}>{t(kind)}</div>
            <div style={{ fontSize: 13, color: tn.dd, opacity: 0.9, marginTop: 4 }}>{t('day_sub', { pct: pct(cur.tir) })}</div>
          </div>
        </div>
      )}
      <div className="p-card" style={{ background: '#f0f5f4' }}>
        <div style={{ fontWeight: 800, fontSize: 13, color: 'var(--muted)', marginBottom: 4 }}>{t('day_chart')}</div>
        <DayChart st={cur} series={series} color={tn.d} />
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.5, marginTop: 4 }}>
          {cur.mealG ? t('day_spike', { v: Math.round(cur.peakVal), time: spikeTime, m: cur.mealMin, g: Math.round(cur.mealG) }) : t('day_spike_nomeal', { v: Math.round(cur.peakVal), time: spikeTime })}
          {cur.low > 0 ? ` ${t('day_low', { m: cur.lowMin })}.` : ''}
        </div>
      </div>
      {live && (
        <>
          <NowCard t={t} status={s} at={at} hour={(((series.t0 + series.glucose.length - 1) % 288) * 5) / 60} stepsToday={cur.steps} onRiskyDrugs={risky} log={log} logIt={logIt} />
          <QuickLog t={t} log={log} logIt={logIt} />
        </>
      )}
      <div className="sect"><span>{t('my_habits')}</span><small>{t('n_of_m', { n: ok.length, m: habits.length })}</small></div>
      {ok.length > 0 && <div style={{ fontWeight: 800, fontSize: 13, color: 'var(--muted)', margin: '4px 0 8px' }}>{t('completed')}</div>}
      {ok.map((h) => <Habit key={h.name} {...h} />)}
      {bad.length > 0 && <div style={{ fontWeight: 800, fontSize: 13, color: 'var(--muted)', margin: '8px 0' }}>{t('needs_attention')}</div>}
      {bad.map((h) => <Habit key={h.name} {...h} />)}
    </>
  )
}

function Insights({ t, series, st, d, locale }) {
  const bars = useMemo(() => [...Array(7)].map((_, i) => ({ k: 6 - i, s: st[6 - i] })).filter((b) => b.s), [st])
  const last = st[0]
  const m = d.metrics
  return (
    <>
      <div className="p-h">{t('ins_title1')}<br /><span style={{ color: 'var(--muted)', fontWeight: 600 }}>{t('ins_title2')}</span></div>
      <div className="p-card" style={{ background: 'var(--lav)' }}>
        <div className="bars" style={{ marginTop: 28 }}>
          {bars.map((b, i) => (
            <div key={b.k} className={`bar ${i === bars.length - 1 ? 'on' : ''}`} style={{ height: `${Math.max(4, b.s.tir * 100)}%` }}><b style={{ color: 'var(--lav-dd)' }}>{Math.round(b.s.tir * 100)}%</b></div>
          ))}
        </div>
        <div className="xl">{bars.map((b) => <span key={b.k}>{dayName(series, b.s.startIdx + 144, locale)}</span>)}</div>
        <div style={{ display: 'flex', justifyContent: 'space-around', marginTop: 18 }}>
          <div style={{ textAlign: 'center' }}><div className="num" style={{ fontSize: 26, color: 'var(--lav-dd)' }}>{pct(last.tir)}</div><div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>{t('today_lbl')}</div></div>
          <div style={{ textAlign: 'center' }}><div className="num" style={{ fontSize: 26, color: 'var(--lav-dd)' }}>{pct(m.tir)}</div><div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>{t('two_weeks')}</div></div>
        </div>
      </div>
      <div className="p-card" style={{ background: 'var(--mint)', display: 'flex', alignItems: 'center', gap: 16 }}>
        <SegRing size={118} stroke={16} segments={[{ v: m.tir, color: '#4d8f6b' }, { v: Math.max(0, 1 - m.tir - m.tbr), color: '#e9a23b' }, { v: m.tbr, color: '#c4645b' }]}>
          <div className="num" style={{ fontSize: 24, color: 'var(--mint-dd)' }}>{pct(m.tir)}</div>
        </SegRing>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--mint-dd)', lineHeight: 1.7 }}>
          🟢 {t('legend_in', { p: pct(m.tir) })}<br />🟠 {t('legend_above', { p: pct(m.tar) })}<br />🔴 {t('legend_below', { p: pct(m.tbr, 1) })}
        </div>
      </div>
      <p className="note" style={{ marginTop: 14 }}>{t('ins_note')}</p>
    </>
  )
}

function Body({ t, d }) {
  const tl = d.liver.timeline
  const lv = tl.steatosis.at(-1)
  const ep = d.eye.progression_2y
  const lab = d.profile.labs
  const kp = d.kidney.projection
  const kidneyHigh = lab.uacr_mg_g >= 30 || lab.egfr < 60 || kp.albuminuria.at(-1) >= 0.5
  const card = (tone, art, title, level, text, ring) => (
    <div className="p-card" style={{ background: TONE[tone].bg }}>
      <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
        {ring}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><div className="organ-ill" style={{ width: 42, height: 42, borderRadius: 14 }}>{art}</div><b style={{ fontSize: 18, color: TONE[tone].dd }}>{title}</b></div>
          <div style={{ fontWeight: 800, color: TONE[tone].dd, marginTop: 6, lineHeight: 1.3 }}>{level}</div>
          <div style={{ fontSize: 13, color: TONE[tone].dd, opacity: 0.85 }}>{text}</div>
        </div>
      </div>
    </div>
  )
  return (
    <>
      <div className="p-h">{t('body_title1')}<br /><span style={{ color: 'var(--muted)', fontWeight: 600 }}>{t('body_title2')}</span></div>
      {card(lv > 0.6 ? 'rose' : lv > 0.3 ? 'butter' : 'mint', <LiverArt size={30} />, t('liver'), lv > 0.6 ? t('liver_high') : lv > 0.3 ? t('liver_mid') : t('liver_ok'),
        lv > 0.3 ? t('liver_text_mid') : t('liver_text_ok'),
        <Ring value={lv} size={84} stroke={11} color={lv > 0.6 ? '#c4645b' : lv > 0.3 ? '#E9A23B' : '#4d8f6b'}><div className="num" style={{ fontSize: 18 }}>{pct(lv)}</div></Ring>)}
      {card(ep > 0.4 ? 'rose' : ep > 0.2 ? 'butter' : 'mint', <EyeArt size={30} />, t('eyes'), t(`dr${d.eye.grade}`), t('eyes_text'),
        <Ring value={ep} size={84} stroke={11} color={ep > 0.4 ? '#c4645b' : ep > 0.2 ? '#E9A23B' : '#4d8f6b'}><div className="num" style={{ fontSize: 18 }}>{pct(ep)}</div></Ring>)}
      {card(kidneyHigh ? 'rose' : 'sky', <KidneyArt size={30} />, t('kidneys'), kidneyHigh ? t('kidney_watch') : t('kidney_ok'),
        t('kidney_text', { now: lab.egfr.toFixed(0), later: kp.egfr.at(-1).toFixed(0) }),
        <Ring value={Math.min(1, lab.egfr / 120)} size={84} stroke={11} color={kidneyHigh ? '#c4645b' : '#4f8196'}><div className="num" style={{ fontSize: 18 }}>{lab.egfr.toFixed(0)}</div></Ring>)}
      <p className="note" style={{ marginTop: 14 }}>{t('body_note')}</p>
    </>
  )
}

function Try({ t, pid }) {
  const [pick, setPick] = useState(2)
  const [res, setRes] = useState(null)
  useEffect(() => { setPick(2); setRes(null) }, [pid])
  useEffect(() => { if (pick !== null) postWhatIf(pid, TRY[pick].body).then(setRes) }, [pick, pid])
  const tirUp = res && res.metrics.after.tir - res.metrics.before.tir >= 0.02
  return (
    <>
      <div className="p-h">{t('try_title1')}<br /><span style={{ color: 'var(--muted)', fontWeight: 600 }}>{t('try_title2')}</span></div>
      <div style={{ display: 'grid', gap: 10, marginTop: 16 }}>
        {TRY.map((o, i) => (
          <button key={o.key} onClick={() => setPick(i)} className="habit" style={{ border: pick === i ? '2px solid var(--lav-d)' : '2px solid transparent', textAlign: 'left', background: pick === i ? 'var(--lav)' : '#f0f5f4' }}>
            <div className="bub">{o.e}</div><b>{t(o.key)}</b><span style={{ color: 'var(--lav-d)', fontWeight: 800 }}>{pick === i ? '●' : '○'}</span>
          </button>
        ))}
      </div>
      {res && pick !== null && (
        <div className="p-card" style={{ background: 'var(--mint)' }}>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 14, alignItems: 'center' }}>
            <div style={{ textAlign: 'center' }}><Ring value={res.metrics.before.tir} size={92} stroke={12} color="#a9c4c0"><div className="num" style={{ fontSize: 20 }}>{pct(res.metrics.before.tir)}</div></Ring><div className="muted" style={{ fontSize: 11, fontWeight: 700 }}>{t('today_lbl')}</div></div>
            <b style={{ fontSize: 24, color: 'var(--mint-d)' }}>→</b>
            <div style={{ textAlign: 'center' }}><Ring value={res.metrics.after.tir} size={92} stroke={12} color="#4d8f6b"><div className="num" style={{ fontSize: 20, color: 'var(--mint-dd)' }}>{pct(res.metrics.after.tir)}</div></Ring><div style={{ fontSize: 11, fontWeight: 700, color: 'var(--mint-dd)' }}>{t('with_change')}</div></div>
          </div>
          <p style={{ marginTop: 14, fontWeight: 700, color: 'var(--mint-dd)', lineHeight: 1.6 }}>
            {tirUp
              ? t('try_msg_tir', { a: pct(res.metrics.before.tir), b: pct(res.metrics.after.tir) })
              : t('try_msg_gv', { n: Math.max(0, Math.round((1 - res.metrics.after.gv_cv / res.metrics.before.gv_cv) * 100)) })}
            {t('try_msg_liver', { a: pct(res.liver.before.steatosis.at(-1)), b: pct(res.liver.after.steatosis.at(-1)) })}
          </p>
        </div>
      )}
      <p className="note" style={{ marginTop: 14 }}>{t('try_note')}</p>
    </>
  )
}

function initialLang() {
  const q = new URLSearchParams(window.location.search).get('lang')
  if (q && LANGS.some((l) => l.code === q)) return q
  try { const s = window.localStorage.getItem('kaya-lang'); if (s && LANGS.some((l) => l.code === s)) return s } catch (e) { /* storage unavailable */ }
  return 'en'
}

export default function PatientApp({ d, at, pid, changes }) {
  const [tab, setTab] = useState(Number(new URLSearchParams(window.location.search).get('tab') || 0))
  const [day, setDay] = useState(0)
  const [log, setLog] = useState(null)
  const [series14, setSeries14] = useState(null)
  const [lang, setLang] = useState(initialLang)
  const [voice, setVoice] = useState({ enabled: false })
  const [askOpen, setAskOpen] = useState(new URLSearchParams(window.location.search).get('ask') === '1')
  const [large, setLarge] = useState(false)
  useEffect(() => { getVoiceStatus().then(setVoice) }, [])
  const locale = LANGS.find((l) => l.code === lang).locale
  const t = useMemo(() => makeT(lang), [lang])
  const pick = (code) => { setLang(code); try { window.localStorage.setItem('kaya-lang', code) } catch (e) { /* ignore */ } }
  useEffect(() => { setSeries14(null); setDay(Number(new URLSearchParams(window.location.search).get('day') || 0)); setLog(null); getLog(pid).then(setLog).catch(() => {}); getSeries(pid, 14).then(setSeries14) }, [pid])
  const logIt = (kind, value) => postLog(pid, { kind, value }).then(setLog).catch(() => {})
  const st = useMemo(() => (series14 ? [...Array(13)].map((_, k) => dayStats(series14, k)) : []), [series14])
  const days = useMemo(() => (series14 ? [3, 2, 1, 0].map((k) => ({ k, label: st[k] ? dayName(series14, st[k].startIdx + 144, locale, true) : '' })) : []), [series14, st, locale])
  const readout = () => {
    if (tab === 0) { const s = status(at); return `${t(`${s.k}_title`)}. ${t(`${s.k}_body`)} ${t(`${s.k}_nudge`)}` }
    if (tab === 1) return `${t('ins_title1')} ${t('ins_title2')}. ${t('legend_in', { p: pct(d.metrics.tir) })}. ${t('legend_above', { p: pct(d.metrics.tar) })}. ${t('ins_note')}`
    if (tab === 2) {
      const lv = d.liver.timeline.steatosis.at(-1)
      const lab = d.profile.labs
      const kh = lab.uacr_mg_g >= 30 || lab.egfr < 60 || d.kidney.projection.albuminuria.at(-1) >= 0.5
      return `${t('liver')}: ${lv > 0.6 ? t('liver_high') : lv > 0.3 ? t('liver_mid') : t('liver_ok')}. ${t('eyes')}: ${t(`dr${d.eye.grade}`)}. ${t('kidneys')}: ${kh ? t('kidney_watch') : t('kidney_ok')}.`
    }
    if (tab === 4) return `${t('rep_title1')} ${t('rep_title2')}.`
    return `${t('try_title1')}. ${t('try_title2')}.`
  }
  const tabs = [['🏠', 'tab_today'], ['📊', 'tab_insights'], ['🫀', 'tab_body'], ['✨', 'tab_try'], ['🧾', 'tab_reports']]
  return (
    <div className="stage">
      <div className="blob" style={{ width: 340, height: 340, left: '8%', top: 60, background: 'var(--peach)' }} />
      <div className="blob" style={{ width: 280, height: 280, right: '9%', top: 140, background: 'var(--sky)' }} />
      <div className="blob" style={{ width: 220, height: 220, left: '20%', bottom: 30, background: 'var(--mint)' }} />
      <div className={`phone ${large ? 'large' : ''}`}>
        <div className="status">
          <span>9:41</span>
          <span className="langs" role="group" aria-label="Language">
            {LANGS.map((l) => <button key={l.code} className={lang === l.code ? 'on' : ''} onClick={() => pick(l.code)} title={l.code}>{l.label}</button>)}
          </span>
        </div>
        <div className="p-brand"><Logo size={26} /><b>Kaya</b></div>
        <div className="screen">
          {!series14 ? <div className="muted" style={{ padding: 30 }}>{t('loading')}</div> : (
            tab === 0 ? <Today t={t} name={d.profile.name || `Patient ${d.profile.id}`} series={series14} at={at} day={day} setDay={setDay} st={st} days={days} log={log} logIt={logIt} risky={!!d.profile.on_insulin_or_su} /> :
            tab === 1 ? <Insights t={t} series={series14} st={st} d={d} locale={locale} /> :
            tab === 2 ? <Body t={t} d={d} /> : tab === 3 ? <Try t={t} pid={pid} /> : <PatientReports t={t} pid={pid} changes={changes} />
          )}
          {lang !== 'en' && <p className="note" style={{ marginTop: 10 }}>{t('lang_note')}</p>}
        </div>
        {!askOpen && <button className="vbtn" onClick={() => setAskOpen(true)} aria-label={t('ask_title')} title={t('ask_title')}>🎙️</button>}
        {askOpen && <Assistant t={t} lang={lang} pid={pid} tab={tab} voice={voice} screenText={readout()} large={large} onToggleLarge={() => setLarge(!large)} onNavigate={setTab} onClose={() => setAskOpen(false)} />}
        <div className="tabs">
          {tabs.map(([e, k], i) => <button key={k} className={`tab ${tab === i ? 'on' : ''}`} onClick={() => setTab(i)}><span>{e}</span>{t(k)}</button>)}
        </div>
      </div>
    </div>
  )
}
