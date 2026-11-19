import { useEffect, useState } from 'react'
import { getScreening, sendMessage } from '../api'
import { TONE } from '../ui'
import { fmtDate } from './Reports'

const STATE = { overdue: ['rose', 'Overdue'], soon: ['butter', 'Due soon'], ok: ['mint', 'Up to date'] }
const ICON = { eye: '👁️', uacr: '💧', egfr: '🫘', foot: '🦶' }

const ago = (d) => (d < 31 ? `${d} days ago` : d < 700 ? `${Math.round(d / 30.4)} months ago` : `${(d / 365).toFixed(1)} years ago`)
const left = (d) => (d < 0 ? `${ago(-d).replace(' ago', '')} late` : d < 31 ? `due in ${d} days` : `due in ${Math.round(d / 30.4)} months`)

/** Doctor view: which yearly diabetes tests are done, due soon or overdue, with one-click reminder and referral to the patient. */
export default function ScreeningCard({ pid }) {
  const [sc, setSc] = useState(null)
  const [busy, setBusy] = useState(null)
  const [err, setErr] = useState('')
  const load = () => getScreening(pid).then(setSc).catch(() => {})
  useEffect(() => { setSc(null); setErr(''); load() }, [pid])
  if (!sc) return null

  const send = (t, referral) => {
    const key = `${t.key}${referral ? 'r' : ''}`
    setBusy(key)
    setErr('')
    const late = t.state === 'overdue'
    const body = referral
      ? `I am referring you to an eye specialist for a retina exam. Please book it soon and bring your latest reports. Reply here if you need help finding a time.`
      : `Your ${t.label.toLowerCase()} is ${late ? 'overdue' : 'due soon'}. ${t.why}. Please book it in the next few weeks, and reply here if you need help finding a time.`
    sendMessage(pid, { kind: 'advice', title: `${referral ? 'Referral: ' : 'Screening reminder: '}${t.label}`, body, translate: true })
      .then(() => load())
      .catch((e) => setErr(e.message || 'Could not send'))
      .finally(() => setBusy(null))
  }

  return (
    <section className="card soft rec-sec" style={{ boxShadow: 'none' }}>
      <div className="card-h">
        <h2>Screening tracker</h2>
        <span className={`chip ${sc.overdue ? 'rose' : 'mint'}`}>{sc.headline}</span>
      </div>
      <div style={{ display: 'grid', gap: 8 }}>
        {sc.tests.map((t) => {
          const [tn, word] = STATE[t.state]
          const f = t.follow_up
          const act = t.state !== 'ok'
          return (
            <div key={t.key} style={{ display: 'grid', gridTemplateColumns: '34px 1fr auto', gap: 12, alignItems: 'center', padding: '10px 14px', borderRadius: 16, background: TONE[tn].bg, color: TONE[tn].dd }}>
              <span style={{ fontSize: 22 }}>{ICON[t.key]}</span>
              <div>
                <b>{t.label}</b> <span className="chip" style={{ marginLeft: 6, background: 'rgba(255,255,255,.7)' }}>{word}</span>
                <div style={{ fontSize: 13, opacity: 0.9 }}>
                  Last done {fmtDate(t.last_done)} ({ago(t.days_since)}) · {left(t.days_left)}
                  {act && <> · {t.why}</>}
                </div>
                {f && <div style={{ fontSize: 12.5, fontWeight: 700, marginTop: 2 }}>✓ {f.kind === 'referral' ? 'Referral' : 'Reminder'} sent {fmtDate(f.date)}; this clears when the new report arrives</div>}
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                {act && <button className="btn sm" disabled={busy === t.key} onClick={() => send(t, false)}>{f && f.kind === 'reminder' ? 'Remind again' : 'Remind patient'}</button>}
                {act && t.can_refer && <button className="btn sm go" disabled={busy === `${t.key}r`} onClick={() => send(t, true)}>{f && f.kind === 'referral' ? 'Refer again' : 'Refer to eye specialist'}</button>}
              </div>
            </div>
          )
        })}
      </div>
      {err && <div className="note" style={{ color: 'var(--rose-dd)' }}>{err}</div>}
      <div className="note">A yearly test counts as done when its report is in the record. The messages go to the patient app. The test history is synthetic.</div>
    </section>
  )
}
