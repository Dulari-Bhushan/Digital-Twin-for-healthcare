import { useEffect, useMemo, useState } from 'react'
import { getSeries, postWhatIf } from '../api'
import { LANGS, makeT } from '../i18n'
import { dayStats } from '../utils'
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
    <div className="habit" style={{ background: done === false ? '#f6f5fb' : '#fff' }}>
      <div className="fill" style={{ width: `${p * 100}%`, background: t.bg }} />
      <div className="bub">{e}</div>
      <div><b style={{ fontSize: 15 }}>{name}</b><div className="muted" style={{ fontSize: 12, fontWeight: 600 }}>{sub}</div></div>
      <div style={{ fontWeight: 800, color: t.dd }}>{done === true ? '✓' : done === false ? '✕' : goal}</div>
    </div>
  )
}

function Today({ t, at, day, setDay, st, days, nudgeDone, setNudgeDone }) {
  const s = status(at)
  const tn = TONE[s.tone]
  const cur = st[day]
  const habits = cur ? [
    { e: '🎯', name: t('habit_range'), sub: t('habit_range_sub', { pct: pct(cur.tir) }), value: cur.tir / 0.7, done: cur.tir >= 0.7, tone: 'mint' },
    { e: '👟', name: t('habit_steps'), sub: t('habit_steps_sub', { n: Math.round(cur.steps).toLocaleString() }), value: cur.steps / 6000, done: cur.steps >= 6000, tone: 'sky' },
    { e: '🛡️', name: t('habit_nolow'), sub: cur.low > 0 ? t('habit_nolow_sub_bad', { pct: pct(cur.low, 1) }) : t('habit_nolow_sub_ok'), value: cur.low > 0 ? 0.2 : 1, done: cur.low === 0, tone: 'lav' },
    { e: '🍚', name: t('habit_carbs'), sub: t('habit_carbs_sub', { g: Math.round(cur.carbs), m: cur.meals }), value: Math.min(1, 220 / Math.max(cur.carbs, 1)), done: cur.carbs <= 220, tone: 'butter' },
  ] : []
  const ok = habits.filter((h) => h.done)
  const bad = habits.filter((h) => !h.done)
  return (
    <>
      <div className="p-h">{t('today_title1')}<br /><span style={{ color: 'var(--muted)', fontWeight: 600 }}>{t('today_title2')}</span></div>
      <div className="days">
        {days.map((dd) => <button key={dd.k} className={`day ${day === dd.k ? 'on' : ''}`} onClick={() => setDay(dd.k)}>{dd.k === 0 ? t('day_today') : dd.label}</button>)}
      </div>
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
      <div className="p-card" style={{ background: 'var(--butter)' }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--butter-dd)' }}>{t('one_thing')}</div>
        <div style={{ fontWeight: 800, fontSize: 20, margin: '4px 0', color: 'var(--butter-dd)', lineHeight: 1.3 }}>{s.nudgeE} {t(`${s.k}_nudge`)}</div>
        <button className={`big-btn ${nudgeDone ? 'done' : ''}`} onClick={() => setNudgeDone(!nudgeDone)}>{nudgeDone ? `${t('well_done')} ✓` : t('mark_done')}</button>
      </div>
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
        <div className="xl">{bars.map((b) => <span key={b.k}>{dayName(series, b.s.startIdx, locale)}</span>)}</div>
        <div style={{ display: 'flex', justifyContent: 'space-around', marginTop: 18 }}>
          <div style={{ textAlign: 'center' }}><div className="num" style={{ fontSize: 26, color: 'var(--lav-dd)' }}>{pct(last.tir)}</div><div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>{t('today_lbl')}</div></div>
          <div style={{ textAlign: 'center' }}><div className="num" style={{ fontSize: 26, color: 'var(--lav-dd)' }}>{pct(m.tir)}</div><div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>{t('two_weeks')}</div></div>
        </div>
      </div>
      <div className="p-card" style={{ background: 'var(--mint)', display: 'flex', alignItems: 'center', gap: 16 }}>
        <SegRing size={118} stroke={16} segments={[{ v: m.tir, color: '#2fa176' }, { v: Math.max(0, 1 - m.tir - m.tbr), color: '#f6b26b' }, { v: m.tbr, color: '#e85f8b' }]}>
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
        <Ring value={lv} size={84} stroke={11} color={lv > 0.6 ? '#e85f8b' : lv > 0.3 ? '#e0a912' : '#2fa176'}><div className="num" style={{ fontSize: 18 }}>{pct(lv)}</div></Ring>)}
      {card(ep > 0.4 ? 'rose' : ep > 0.2 ? 'butter' : 'mint', <EyeArt size={30} />, t('eyes'), t(`dr${d.eye.grade}`), t('eyes_text'),
        <Ring value={ep} size={84} stroke={11} color={ep > 0.4 ? '#e85f8b' : ep > 0.2 ? '#e0a912' : '#2fa176'}><div className="num" style={{ fontSize: 18 }}>{pct(ep)}</div></Ring>)}
      {card(kidneyHigh ? 'rose' : 'sky', <KidneyArt size={30} />, t('kidneys'), kidneyHigh ? t('kidney_watch') : t('kidney_ok'),
        t('kidney_text', { now: lab.egfr.toFixed(0), later: kp.egfr.at(-1).toFixed(0) }),
        <Ring value={Math.min(1, lab.egfr / 120)} size={84} stroke={11} color={kidneyHigh ? '#e85f8b' : '#4a8fe9'}><div className="num" style={{ fontSize: 18 }}>{lab.egfr.toFixed(0)}</div></Ring>)}
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
          <button key={o.key} onClick={() => setPick(i)} className="habit" style={{ border: pick === i ? '2px solid var(--lav-d)' : '2px solid transparent', textAlign: 'left', background: pick === i ? 'var(--lav)' : '#f6f5fb' }}>
            <div className="bub">{o.e}</div><b>{t(o.key)}</b><span style={{ color: 'var(--lav-d)', fontWeight: 800 }}>{pick === i ? '●' : '○'}</span>
          </button>
        ))}
      </div>
      {res && pick !== null && (
        <div className="p-card" style={{ background: 'var(--mint)' }}>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 14, alignItems: 'center' }}>
            <div style={{ textAlign: 'center' }}><Ring value={res.metrics.before.tir} size={92} stroke={12} color="#b9b3d8"><div className="num" style={{ fontSize: 20 }}>{pct(res.metrics.before.tir)}</div></Ring><div className="muted" style={{ fontSize: 11, fontWeight: 700 }}>{t('today_lbl')}</div></div>
            <b style={{ fontSize: 24, color: 'var(--mint-d)' }}>→</b>
            <div style={{ textAlign: 'center' }}><Ring value={res.metrics.after.tir} size={92} stroke={12} color="#2fa176"><div className="num" style={{ fontSize: 20, color: 'var(--mint-dd)' }}>{pct(res.metrics.after.tir)}</div></Ring><div style={{ fontSize: 11, fontWeight: 700, color: 'var(--mint-dd)' }}>{t('with_change')}</div></div>
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

export default function PatientApp({ d, at, pid }) {
  const [tab, setTab] = useState(Number(new URLSearchParams(window.location.search).get('tab') || 0))
  const [day, setDay] = useState(0)
  const [nudgeDone, setNudgeDone] = useState(false)
  const [series14, setSeries14] = useState(null)
  const [lang, setLang] = useState(initialLang)
  const locale = LANGS.find((l) => l.code === lang).locale
  const t = useMemo(() => makeT(lang), [lang])
  const pick = (code) => { setLang(code); try { window.localStorage.setItem('kaya-lang', code) } catch (e) { /* ignore */ } }
  useEffect(() => { setSeries14(null); setDay(0); setNudgeDone(false); getSeries(pid, 14).then(setSeries14) }, [pid])
  const st = useMemo(() => (series14 ? [...Array(13)].map((_, k) => dayStats(series14, k)) : []), [series14])
  const days = useMemo(() => (series14 ? [3, 2, 1, 0].map((k) => ({ k, label: st[k] ? dayName(series14, st[k].startIdx, locale, true) : '' })) : []), [series14, st, locale])
  const tabs = [['🏠', 'tab_today'], ['📊', 'tab_insights'], ['🫀', 'tab_body'], ['✨', 'tab_try']]
  return (
    <div className="stage">
      <div className="blob" style={{ width: 340, height: 340, left: '8%', top: 60, background: 'var(--peach)' }} />
      <div className="blob" style={{ width: 280, height: 280, right: '9%', top: 140, background: 'var(--sky)' }} />
      <div className="blob" style={{ width: 220, height: 220, left: '20%', bottom: 30, background: 'var(--mint)' }} />
      <div className="phone">
        <div className="status">
          <span>9:41</span>
          <span className="langs" role="group" aria-label="Language">
            {LANGS.map((l) => <button key={l.code} className={lang === l.code ? 'on' : ''} onClick={() => pick(l.code)} title={l.code}>{l.label}</button>)}
          </span>
        </div>
        <div className="screen">
          {!series14 ? <div className="muted" style={{ padding: 30 }}>{t('loading')}</div> : (
            tab === 0 ? <Today t={t} at={at} day={day} setDay={setDay} st={st} days={days} nudgeDone={nudgeDone} setNudgeDone={setNudgeDone} /> :
            tab === 1 ? <Insights t={t} series={series14} st={st} d={d} locale={locale} /> :
            tab === 2 ? <Body t={t} d={d} /> : <Try t={t} pid={pid} />
          )}
          {lang !== 'en' && <p className="note" style={{ marginTop: 10 }}>{t('lang_note')}</p>}
        </div>
        <div className="tabs">
          {tabs.map(([e, k], i) => <button key={k} className={`tab ${tab === i ? 'on' : ''}`} onClick={() => setTab(i)}><span>{e}</span>{t(k)}</button>)}
        </div>
      </div>
    </div>
  )
}
