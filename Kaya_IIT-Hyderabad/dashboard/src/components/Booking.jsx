import { useEffect, useState } from 'react'
import { cancelMyAppointment, getAvailability, getMyAppointments, getScreening, requestAppointment, seenAppointment } from '../api'

const REASONS = ['routine', 'follow_up', 'screening', 'results', 'other']
const fmt = (slot, locale) => {
  if (!slot) return null
  const d = new Date(slot.replace(' ', 'T'))                       // the clinic's own clock, read as written
  return `${d.toLocaleDateString(locale, { weekday: 'short', month: 'short', day: 'numeric' })} ${slot.slice(11)}`
}
const at = (date) => new Date(`${date}T12:00:00`)
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const addDays = (date, n) => { const d = at(date); d.setDate(d.getDate() + n); return iso(d) }

/** The patient's own appointments, checked every few seconds so a confirmation or a change from the clinic shows up while the app is open. */
export function useAppointments(pid) {
  const [data, setData] = useState(null)
  const load = () => getMyAppointments(pid).then(setData).catch(() => {})
  useEffect(() => { setData(null); load(); const id = setInterval(load, 5000); return () => clearInterval(id) }, [pid])
  const seen = (n) => seenAppointment(pid, n.appointment_id).then(load).catch(() => {})
  return { data, reload: load, seen }
}

/** Banners for what the clinic did: confirmed, moved, cancelled, running late. They stay until the patient says "I have seen this". */
export function ApptNotices({ t, locale, appts }) {
  const list = (appts.data && appts.data.notices) || []
  if (!list.length) return null
  const text = (n) => {
    const when = fmt(n.slot, locale)
    if (n.kind === 'confirmed') return t(n.urgent ? 'appt_n_urgent' : 'appt_n_confirmed', { when })
    if (n.kind === 'declined') return t('appt_n_declined', { when: when || t('appt_asap') })
    if (n.kind === 'moved') return t('appt_n_moved', { old: fmt(n.old, locale), when })
    if (n.kind === 'cancelled') return t('appt_n_cancelled', { when })
    if (n.kind === 'delayed') return t('appt_n_delayed', { min: n.minutes, time: n.expected })
    return ''
  }
  return list.map((n) => (
    <div key={n.id} className={n.kind === 'cancelled' || n.kind === 'declined' ? 'in-urgent' : 'in-advice'} role={n.kind === 'cancelled' ? 'alert' : 'status'}>
      <div className="in-h">📅 {t('appt_title')}</div>
      <b>{text(n)}</b>
      <p>{n.reason || ' '}</p>
      <button onClick={() => appts.seen(n)}>{t('msg_seen')}</button>
    </div>
  ))
}

/** Yearly tests the patient is overdue for or that fall due soon, from the doctor's screening tracker. */
export function useDueTests(pid) {
  const [tests, setTests] = useState([])
  useEffect(() => { setTests([]); getScreening(pid).then((d) => setTests(d.tests.filter((x) => x.state !== 'ok'))).catch(() => {}) }, [pid])
  return tests
}

/** The card that leads to booking. On the main (Today) screen it appears only when it matters: an appointment is coming up, or
 *  yearly checks are pending. In the Reports tab it is always there, so a patient can book at any time. */
export function ApptCard({ t, locale, appts, due, onOpen, always }) {
  const next = appts.data && appts.data.upcoming[0]
  const overdue = due.some((x) => x.state === 'overdue')
  if (!next && due.length === 0 && !always) return null
  const tone = next ? (next.status === 'confirmed' ? 'mint' : 'butter') : due.length ? (overdue ? 'rose' : 'butter') : 'sky'
  const names = due.map((x) => t(`appt_t_${x.key}`)).join(', ')
  return (
    <button className="p-card appt-card" style={{ background: `var(--${tone})`, color: `var(--${tone}-dd)` }} onClick={onOpen}>
      <span style={{ fontSize: 26 }}>{!next && due.length ? '⚠️' : '📅'}</span>
      <span style={{ flex: 1, textAlign: 'left' }}>
        <b>{next ? t('appt_next') : due.length ? t('appt_pending_title') : t('appt_book')}</b>
        <small style={{ display: 'block', opacity: 0.9 }}>
          {next ? `${next.slot ? fmt(next.slot, locale) : t('appt_asap')} · ${t(`appt_status_${next.status}`)}${next.expected ? ` · ${t('appt_expected', { time: next.expected })}` : ''}`
            : due.length ? `${names} · ${overdue ? t('appt_overdue') : t('appt_soon')}. ${t('appt_pending_cta')}` : t('appt_card_sub')}
        </small>
      </span>
      <span style={{ fontWeight: 800 }}>›</span>
    </button>
  )
}

/** Book, see and cancel appointments. The calendar shows which slots are free; the clinic confirms each request. */
export function BookingSheet({ t, locale, pid, appts, onClose }) {
  const [av, setAv] = useState(null)
  const [day, setDay] = useState(null)
  const [slot, setSlot] = useState(null)
  const [reason, setReason] = useState('routine')
  const [note, setNote] = useState('')
  const [urgent, setUrgent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const [err, setErr] = useState('')
  const [confirmCancel, setConfirmCancel] = useState(null)
  const [scr, setScr] = useState(null)
  const [month, setMonth] = useState(null)               // 'YYYY-MM', the month being shown
  const load = () => getAvailability().then((d) => setAv(d.days)).catch(() => setErr(t('appt_err')))
  useEffect(() => { load(); const id = setInterval(load, 8000); return () => clearInterval(id) }, [])
  useEffect(() => { getScreening(pid).then(setScr).catch(() => {}) }, [pid])
  const days = av || []
  const picked = days.find((d) => d.date === day)
  const todayIso = (appts.data && appts.data.now ? appts.data.now.slice(0, 10) : (days[0] || {}).date) || iso(new Date())
  const lastIso = days.length ? days[days.length - 1].date : addDays(todayIso, 27)
  const dueTests = ((scr && scr.tests) || []).filter((x) => x.state !== 'ok')
  const pins = {}
  dueTests.filter((x) => x.state === 'soon').forEach((x) => { (pins[x.due_date] = pins[x.due_date] || []).push(x) })
  const byDate = Object.fromEntries(days.map((d) => [d.date, d]))
  const curMonth = month || todayIso.slice(0, 7)
  const firstOfMonth = `${curMonth}-01`
  const lead = (at(firstOfMonth).getDay() + 6) % 7
  const daysInMonth = new Date(at(firstOfMonth).getFullYear(), at(firstOfMonth).getMonth() + 1, 0).getDate()
  const cells = [...Array(lead).fill(null)]
  for (let n = 1; n <= daysInMonth; n++) {
    const d = `${curMonth}-${String(n).padStart(2, '0')}`
    const info = byDate[d]
    cells.push({ date: d, n, open: !!info && info.free > 0, cls: d < todayIso ? 'past' : info ? (info.free > 0 ? 'free' : 'full') : 'closed', pins: pins[d] || [] })
  }
  while (cells.length % 7) cells.push(null)
  const monthName = at(firstOfMonth).toLocaleDateString(locale, { month: 'long', year: 'numeric' })
  const shiftMonth = (k) => { const d = at(firstOfMonth); d.setMonth(d.getMonth() + k); setMonth(iso(d).slice(0, 7)) }
  const canPrev = curMonth > todayIso.slice(0, 7)
  const canNext = curMonth < lastIso.slice(0, 7)
  const wd = [...Array(7)].map((_, i) => new Date(Date.UTC(2024, 0, 1 + i)).toLocaleDateString(locale, { weekday: 'short', timeZone: 'UTC' }))
  const dayLong = (d) => at(d).toLocaleDateString(locale, { weekday: 'long', month: 'long', day: 'numeric' })
  const dueDate = (d) => at(d).toLocaleDateString(locale, { month: 'short', day: 'numeric' })
  const pickTest = (x) => {
    setReason('screening'); setNote(x.label); setSlot(null)
    const first = days.find((d) => d.free > 0)
    if (first) setDay(first.date)
  }
  const mine = (appts.data && appts.data.upcoming) || []
  const send = () => {
    setBusy(true); setErr(''); setMsg(null)
    requestAppointment(pid, { slot: urgent ? null : slot, reason, note, urgent })
      .then(() => { setMsg(urgent ? t('appt_sent_urgent') : t('appt_sent')); setSlot(null); setNote(''); setUrgent(false); appts.reload(); load() })
      .catch((e) => { setErr(e.message); load(); setSlot(null) })
      .finally(() => setBusy(false))
  }
  const cancel = (a) => cancelMyAppointment(pid, a.id).then(() => { setConfirmCancel(null); setMsg(t('appt_cancelled')); appts.reload(); load() }).catch((e) => setErr(e.message))
  const isLate = (a) => !!(a.slot && appts.data && appts.data.now && new Date(a.slot.replace(' ', 'T')) - new Date(appts.data.now.replace(' ', 'T')) < 24 * 36e5)

  return (
    <div className="sheet" role="dialog" aria-label={t('appt_title')}>
      <div className="sheet-h">
        <div style={{ fontWeight: 800, fontSize: 18 }}>📅 {t('appt_title')}</div>
        <button className="x" onClick={onClose} aria-label={t('close')}>✕</button>
      </div>
      <div className="cd-body bk">
        <p className="cd-notice">ⓘ {t('appt_cancel_note')}</p>

        {mine.length > 0 && (
          <div className="bk-mine">
            <div className="bk-h">{t('appt_mine')}</div>
            {mine.map((a) => (
              <div key={a.id} className={`bk-appt ${a.status}`}>
                <div>
                  <b>{a.slot ? fmt(a.slot, locale) : t('appt_asap')}</b>
                  <span className="bk-st">{t(`appt_status_${a.status}`)}{a.urgent ? ` · ${t('appt_urgent_short')}` : ''}</span>
                  <small>{t(`appt_r_${a.reason}`)}{a.expected ? ` · ${t('appt_expected', { time: a.expected })}` : ''}</small>
                </div>
                {confirmCancel === a.id ? (
                  <div className="bk-conf">
                    <small>{t('appt_cancel_confirm')}</small>
                    {isLate(a) && <small className="bk-late">⚠ {t('appt_cancel_late')}</small>}
                    <button onClick={() => cancel(a)}>{t('appt_cancel_yes')}</button>
                    <button className="ghost" onClick={() => setConfirmCancel(null)}>{t('appt_keep')}</button>
                  </div>
                ) : <button className="ghost" onClick={() => setConfirmCancel(a.id)}>{t('appt_cancel')}</button>}
              </div>
            ))}
          </div>
        )}

        {msg && <div className="cd-ok" role="status">✓ {msg}</div>}
        {err && <div className="bk-err" role="alert">{err}</div>}

        <div className="bk-h">{t('appt_new')}</div>
        <div className="bk-chips" role="group" aria-label={t('appt_reason')}>
          {REASONS.map((r) => <button key={r} className={reason === r ? 'on' : ''} onClick={() => setReason(r)}>{t(`appt_r_${r}`)}</button>)}
        </div>

        <label className="bk-urgent"><input type="checkbox" checked={urgent} onChange={(e) => { setUrgent(e.target.checked); setSlot(null) }} /> <b>{t('appt_urgent_title')}</b> <small>{t('appt_urgent_sub')}</small></label>
        {urgent && <div className="bk-warn" role="alert">🚨 {t('appt_urgent_warn')}</div>}

        {!urgent && (
          <>
            {dueTests.length > 0 && (
              <div className="bk-due">
                <div className="bk-h">{t('appt_tests_due')}</div>
                <div className="bk-chips">
                  {dueTests.map((x) => (
                    <button key={x.key} className={x.state === 'overdue' ? 'overdue' : ''} onClick={() => pickTest(x)}>
                      {t(`appt_t_${x.key}`)} · {x.state === 'overdue' ? t('appt_overdue') : t('appt_due_on', { date: dueDate(x.due_date) })}
                    </button>
                  ))}
                </div>
                <small className="muted">{t('appt_due_tip')}</small>
              </div>
            )}
            {!av ? <p className="muted">{t('loading')}</p> : days.length === 0 ? <p className="muted">{t('appt_none_free')}</p> : (
              <>
                <div className="bk-h">{t('appt_choose_day')}</div>
                <div className="bk-month">
                  <button onClick={() => shiftMonth(-1)} disabled={!canPrev} aria-label="‹">‹</button>
                  <b>{monthName}</b>
                  <button onClick={() => shiftMonth(1)} disabled={!canNext} aria-label="›">›</button>
                </div>
                <div className="bk-cal" role="grid" aria-label={monthName}>
                  {wd.map((w) => <div key={w} className="bk-wd">{w}</div>)}
                  {cells.map((c, i) => c === null ? <span key={`b${i}`} className="bk-blank" /> : (
                    <button key={c.date} role="gridcell" aria-selected={day === c.date} aria-label={dayLong(c.date)} disabled={!c.open} className={`${c.cls} ${day === c.date ? 'on' : ''}`}
                      onClick={() => { setDay(c.date); setSlot(null) }}>
                      <span>{c.n}</span>
                      {c.pins.length > 0 && <b className="pin" title={c.pins.map((x) => t(`appt_t_${x.key}`)).join(', ')}>📌</b>}
                    </button>
                  ))}
                </div>
                <div className="bk-legend"><span><i className="f" />{t('appt_l_free')}</span><span><i className="t" />{t('appt_l_full')}</span><span><i className="c" />{t('appt_l_closed')}</span><span>📌 {t('appt_l_due')}</span></div>
                {!picked ? <p className="muted bk-hint">{t('appt_pick_day')}</p> : (
                  <>
                    <div className="bk-h">{t('appt_day_times', { day: dayLong(day) })}</div>
                    <div className="bk-grid" role="listbox" aria-label={t('appt_choose_time')}>
                      {picked.slots.map((s) => {
                        const free = s.state === 'free'
                        return (
                          <button key={s.time} role="option" aria-selected={slot === `${day} ${s.time}`} disabled={!free} className={`${s.state} ${slot === `${day} ${s.time}` ? 'on' : ''}`} onClick={() => setSlot(`${day} ${s.time}`)}
                            title={s.state === 'reserved' ? t('appt_reserved_hint') : undefined}>{s.time}{s.state === 'reserved' && <small>{t('appt_reserved')}</small>}</button>
                        )
                      })}
                    </div>
                    <div className="bk-legend"><span><i className="f" />{t('appt_free')}</span><span><i className="t" />{t('appt_taken')}</span><span><i className="r" />{t('appt_reserved')}</span></div>
                  </>
                )}
              </>
            )}
          </>
        )}

        <textarea rows={2} maxLength={300} value={note} placeholder={t('appt_note')} aria-label={t('appt_note')} onChange={(e) => setNote(e.target.value)} />
        <button className="cd-primary" disabled={busy || (!urgent && !slot)} onClick={send}>{busy ? t('appt_sending') : urgent ? t('appt_send_urgent') : slot ? `${t('appt_send')} · ${fmt(slot, locale)}` : t('appt_send')}</button>
        <p className="note" style={{ marginTop: 8 }}>{t('appt_confirm_note')}</p>
      </div>
    </div>
  )
}
