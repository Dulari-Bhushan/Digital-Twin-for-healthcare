import { useEffect, useState } from 'react'
import { getLog } from '../api'
import { TONE } from '../ui'
import { fmtDate } from './Reports'

const FEEL = { good: ['😊', 'mint', 'Good'], ok: ['😐', 'butter', 'So-so'], low: ['😟', 'rose', 'Unwell'] }

const lastDates = (todayIso, n) => [...Array(n)].map((_, k) => {
  const d = new Date(`${todayIso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() - (n - 1 - k))
  return d.toISOString().slice(0, 10)
})

/** Doctor view: what the patient says they did over the last 14 days (medicines, walks, how they felt). */
export default function DiarySection({ pid }) {
  const [log, setLog] = useState(null)
  useEffect(() => { setLog(null); getLog(pid).then(setLog).catch(() => {}) }, [pid])
  if (!log) return null
  const s = log.summary
  const dates = lastDates(log.today.date, 14)
  const has = (d, k, v) => log.entries.find((e) => e.date === d && e.kind === k && (v === undefined || e.value === v))
  const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0)
  const kp = (label, value, sub, tn) => <div className="kpi2" style={{ background: TONE[tn].bg, color: TONE[tn].dd }}><div className="l">{label}</div><div className="v">{value}</div><div className="s">{sub}</div></div>
  const am = pct(s.morning.taken, s.morning.of)
  const pm = pct(s.evening.taken, s.evening.of)
  const dot = (on, color) => <span className="dgdot" style={{ background: on ? color : 'rgba(42,39,66,.08)' }} />
  const seen = new Set()
  const notes = log.entries.filter((e) => e.note && !seen.has(e.note) && seen.add(e.note)).slice(0, 4)
  const mine = log.entries.filter((e) => e.source === 'patient')
  return (
    <section className="card soft rec-sec" style={{ boxShadow: 'none' }}>
      <div className="card-h"><h2>Patient diary and adherence</h2><span className="chip">last 14 days · logged by the patient in the app</span></div>
      <div className="rec-kpis">
        {kp('Morning medicines', `${s.morning.taken} of ${s.morning.of}`, `${am}% of days`, am >= 85 ? 'mint' : am >= 60 ? 'butter' : 'rose')}
        {kp('Evening medicines', `${s.evening.taken} of ${s.evening.of}`, `${pm}% of finished days`, pm >= 85 ? 'mint' : pm >= 60 ? 'butter' : 'rose')}
        {kp('Days with a walk', `${s.walk_days} of 14`, s.walk_min_avg ? `about ${s.walk_min_avg} min each` : 'none logged', s.walk_days >= 8 ? 'mint' : s.walk_days >= 4 ? 'butter' : 'rose')}
        {kp('Felt unwell', `${s.feel.low} days`, `${s.feel.good} good, ${s.feel.ok} so-so`, s.feel.low >= 5 ? 'rose' : s.feel.low >= 2 ? 'butter' : 'mint')}
      </div>
      <div style={{ overflowX: 'auto', marginTop: 14 }}>
        <div className="dg" style={{ gridTemplateColumns: `92px repeat(14, minmax(18px, 1fr))` }}>
          <span />
          {dates.map((d) => <small key={d}>{new Date(`${d}T00:00:00Z`).getUTCDate()}</small>)}
          <span className="lbl">Morning</span>{dates.map((d) => <i key={d}>{dot(has(d, 'med', 'morning'), '#2fa176')}</i>)}
          <span className="lbl">Evening</span>{dates.map((d, k) => <i key={d}>{dot(has(d, 'med', 'evening'), '#2fa176')}</i>)}
          <span className="lbl">Walk</span>{dates.map((d) => <i key={d}>{dot(has(d, 'walk'), '#4a8fe9')}</i>)}
          <span className="lbl">Feeling</span>{dates.map((d) => { const f = has(d, 'feel'); return <i key={d} title={f ? FEEL[f.value][2] : 'not logged'}>{f ? dot(true, TONE[FEEL[f.value][1]].d) : dot(false)}</i> })}
        </div>
      </div>
      <div className="legend"><span><i style={{ background: '#2fa176' }} />Medicine taken</span><span><i style={{ background: '#4a8fe9' }} />Walked</span><span><i style={{ background: TONE.mint.d }} />Felt good</span><span><i style={{ background: TONE.rose.d }} />Felt unwell</span><span>Grey: not logged</span></div>
      {notes.length > 0 && (
        <div style={{ marginTop: 12, display: 'grid', gap: 6 }}>
          {notes.map((e) => <div key={e.id} className="rep-med" style={{ background: TONE[FEEL[e.value]?.[1] || 'butter'].bg, color: TONE[FEEL[e.value]?.[1] || 'butter'].dd }}><b>{fmtDate(e.date)} · {e.time}</b><span>{e.note}</span></div>)}
        </div>
      )}
      {mine.length > 0 && <div className="note">Entered in the patient app just now: {mine.map((e) => `${e.kind} ${e.value}`).join(', ')}.</div>}
      <div className="note">Self-reported, so it shows what the patient remembers to log, not what they took. The 14 days are synthetic; entries made in the patient app are added live.</div>
    </section>
  )
}
