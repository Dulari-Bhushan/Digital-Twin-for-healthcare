import { useEffect, useMemo, useState } from 'react'
import { apptAct, bookAppointment, getClinic, getSchedule, removeBlock, runningLate, unavailable } from '../api'

const iso = (d) => d.toISOString().slice(0, 10)
const utc = (s) => new Date(`${s}T00:00:00Z`)
const addDays = (s, n) => { const d = utc(s); d.setUTCDate(d.getUTCDate() + n); return iso(d) }
const monday = (s) => { const d = utc(s); const k = (d.getUTCDay() + 6) % 7; return addDays(s, -k) }
const dayLabel = (s, long = false) => utc(s).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC', ...(long ? { year: 'numeric' } : {}) })
const when = (slot) => (slot ? `${dayLabel(slot.slice(0, 10))} ${slot.slice(11)}` : 'as soon as possible')
const REASON = { routine: 'Routine check', follow_up: 'Follow-up', screening: 'Eye, kidney or foot test', results: 'Discuss results', other: 'Something else' }
const STATUS = { requested: 'Waiting', confirmed: 'Confirmed', declined: 'Declined', cancelled: 'Cancelled', completed: 'Done', no_show: 'No-show' }
export const reasonText = (r) => REASON[r] || r
export const whenText = when

function Pill({ a, active, onClick }) {
  const cls = a.urgent ? 'urgent' : a.status
  return (
    <button className={`cal-pill ${cls} ${active ? 'on' : ''}`} onClick={onClick} title={`${a.name} · ${REASON[a.reason] || a.reason} · ${STATUS[a.status]}`}>
      {a.urgent ? '! ' : ''}{a.name.split(' ')[0]}{a.delay_min ? ` +${a.delay_min}m` : ''}
    </button>
  )
}

/** The clinic calendar for one week, shared by reception and the doctor. Click a person to see their request and act on it,
 *  click an empty slot to book someone in. role decides who the changes are recorded as. */
export default function Schedule({ role, patients, onChanged, onOpenPatient }) {
  const [clinic, setClinic] = useState(null)
  const [start, setStart] = useState(null)
  const [data, setData] = useState(null)
  const [sel, setSel] = useState(null)               // { appt } or { slot }
  const [err, setErr] = useState('')
  const [flash, setFlash] = useState('')
  const load = (s = start) => (s ? getSchedule(s, 7).then(setData).catch((e) => setErr(e.message)) : null)
  useEffect(() => { getClinic().then((c) => { setClinic(c); setStart(c.first_open_day) }).catch((e) => setErr(e.message)) }, [])
  useEffect(() => { if (!start) return undefined; load(start); const id = setInterval(() => load(start), 6000); return () => clearInterval(id) }, [start])
  const changed = (msg) => { setFlash(msg); setErr(''); setSel(null); load(); if (onChanged) onChanged(); setTimeout(() => setFlash(''), 5000) }
  const fail = (e) => setErr(e.message || 'Something went wrong')

  const open = useMemo(() => (data ? data.days.filter((d) => !d.closed) : []), [data])
  const times = useMemo(() => (open[0] ? open[0].slots.map((s) => s.time) : []), [open])
  const cell = (d, time) => d.slots.find((s) => s.time === time)
  const current = sel && sel.id && data ? data.days.flatMap((d) => d.slots).flatMap((s) => s.appts).find((a) => a.id === sel.id) : null
  const freeSlots = useMemo(() => open.flatMap((d) => d.slots.filter((s) => !s.past && !s.block && !s.appts.some((a) => ['requested', 'confirmed'].includes(a.status))).map((s) => ({ v: `${d.date} ${s.time}`, label: `${dayLabel(d.date)} ${s.time}${s.reserved ? ' (urgent slot)' : ''}` }))), [open])
  const busySlots = useMemo(() => open.flatMap((d) => d.slots.filter((s) => !s.past && !s.block).map((s) => ({ v: `${d.date} ${s.time}`, label: `${dayLabel(d.date)} ${s.time}${s.reserved ? ' (urgent slot)' : ''}` }))), [open])

  if (!clinic || !data) return <div className="muted" style={{ padding: 20 }}>{err || 'Loading the calendar…'}</div>
  const stat = (n, label, tone) => <span className={`chip ${tone}`}>{n} {label}</span>
  const allAppts = open.flatMap((d) => d.slots.flatMap((s) => s.appts))
  const week = open.length ? `${dayLabel(open[0].date)} to ${dayLabel(open.at(-1).date)}` : ''

  return (
    <div className="cal">
      <div className="card-h" style={{ flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>Calendar</h2>
        <span className="chip">{week}</span>
        {stat(allAppts.filter((a) => a.status === 'confirmed').length, 'confirmed', 'mint')}
        {stat(allAppts.filter((a) => a.status === 'requested').length, 'waiting', 'butter')}
        <span style={{ flex: 1 }} />
        <button className="btn sm" onClick={() => setStart(addDays(start, -7))}>‹ Earlier</button>
        <button className="btn sm" onClick={() => setStart(clinic.first_open_day)}>Next open day</button>
        <button className="btn sm" onClick={() => setStart(addDays(start, 7))}>Later ›</button>
      </div>
      {flash && <div className="cal-flash" role="status">✓ {flash}</div>}
      {err && <div className="cal-err" role="alert">{err}</div>}

      <div className="cal-wrap">
        <div className="cal-grid" style={{ gridTemplateColumns: `58px repeat(${open.length}, minmax(96px, 1fr))` }}>
          <div />
          {open.map((d) => <div key={d.date} className="cal-dh"><b>{dayLabel(d.date)}</b><small>{d.slots.filter((s) => !s.past && !s.block && !s.reserved && !s.appts.some((a) => ['requested', 'confirmed'].includes(a.status))).length} free</small></div>)}
          {times.map((t) => (
            <div key={t} style={{ display: 'contents' }}>
              <div className="cal-t">{t}</div>
              {open.map((d) => {
                const c = cell(d, t)
                if (!c) return <div key={d.date + t} className="cal-cell off" />
                const hold = c.appts.filter((a) => ['requested', 'confirmed'].includes(a.status))
                const isSel = sel && sel.slot === `${d.date} ${t}`
                const cls = c.block ? 'blocked' : c.past ? 'past' : hold.length ? 'busy' : c.reserved ? 'reserved' : 'free'
                return (
                  <div key={d.date + t} className={`cal-cell ${cls} ${isSel ? 'sel' : ''}`} title={c.block ? `Doctor away: ${c.block.reason || 'no reason given'}` : c.reserved ? 'Held back for urgent cases' : ''}
                    onClick={(e) => { if (e.target.closest('button')) return; if (!c.block && !c.past && !hold.length) setSel({ slot: `${d.date} ${t}`, reserved: c.reserved }) }}>
                    {c.block ? <span className="cal-away">away</span> : c.appts.map((a) => <Pill key={a.id} a={a} active={sel && sel.id === a.id} onClick={() => setSel({ id: a.id })} />)}
                    {!c.block && !c.past && !c.appts.length && c.reserved && <span className="cal-res">urgent</span>}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
        <div className="cal-legend">
          <span><i className="free" />free</span><span><i className="req" />waiting for reception</span><span><i className="conf" />confirmed</span>
          <span><i className="urg" />urgent</span><span><i className="res" />kept for urgent cases</span><span><i className="blk" />doctor away</span>
        </div>
      </div>

      {current && <Detail key={current.id} a={current} role={role} free={freeSlots} busy={busySlots} onOpenPatient={onOpenPatient} onDone={changed} onFail={fail} />}
      {sel && sel.slot && <Book key={sel.slot} slot={sel.slot} reserved={sel.reserved} role={role} patients={patients} onDone={changed} onFail={fail} onClose={() => setSel(null)} />}
      <Tools role={role} clinic={clinic} days={open} blocks={data.blocks} onDone={changed} onFail={fail} />
    </div>
  )
}

function Detail({ a, role, free, busy, onOpenPatient, onDone, onFail }) {
  const [slot, setSlot] = useState('')
  const [reason, setReason] = useState('')
  const [squeeze, setSqueeze] = useState(false)
  const [moving, setMoving] = useState(false)
  const list = squeeze ? busy : free
  const run = (action, body, msg) => apptAct(a.id, action, { actor: role, ...body }).then(() => onDone(msg)).catch(onFail)
  const requested = a.status === 'requested'
  const confirmed = a.status === 'confirmed'
  return (
    <section className="card soft cal-detail">
      <div className="card-h" style={{ flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0 }}>{a.name}</h3>
        <span className={`chip ${a.urgent ? 'rose' : requested ? 'butter' : confirmed ? 'mint' : ''}`}>{a.urgent ? 'Urgent · ' : ''}{STATUS[a.status]}</span>
        {onOpenPatient && <button className="btn sm" onClick={() => onOpenPatient(a.pid)}>Open record</button>}
      </div>
      <div className="cal-facts">
        <div><small>When</small><b>{when(a.slot)}{a.expected ? ` · expected about ${a.expected}` : ''}</b></div>
        <div><small>Reason</small><b>{REASON[a.reason] || a.reason}</b></div>
        {a.note && <div style={{ gridColumn: '1 / -1' }}><small>Note from the patient</small><b>{a.note}</b></div>}
        {a.late_cancel && <div style={{ gridColumn: '1 / -1' }}><span className="chip rose">cancelled with less than 24 hours' notice</span></div>}
      </div>
      {(requested || confirmed) && (
        <div className="cal-actions">
          {requested && (!a.slot || moving) && (
            <label>Time <select value={slot} onChange={(e) => setSlot(e.target.value)}><option value="">Choose a slot…</option>{list.map((s) => <option key={s.v} value={s.v}>{s.label}</option>)}</select></label>
          )}
          {requested && <button className="btn sm go" disabled={!a.slot && !slot} onClick={() => run('confirm', { slot: slot || undefined, override: squeeze }, `${a.name} confirmed for ${when(slot || a.slot)}. They have been told.`)}>{a.urgent && !a.slot ? 'Place in the chosen slot' : 'Confirm'}</button>}
          {requested && a.slot && !moving && <button className="btn sm" onClick={() => setMoving(true)}>Offer another time</button>}
          {confirmed && !moving && <button className="btn sm" onClick={() => setMoving(true)}>Move to another time</button>}
          {moving && confirmed && (
            <>
              <label>New time <select value={slot} onChange={(e) => setSlot(e.target.value)}><option value="">Choose a slot…</option>{list.map((s) => <option key={s.v} value={s.v}>{s.label}</option>)}</select></label>
              <button className="btn sm go" disabled={!slot} onClick={() => run('move', { slot, reason, override: squeeze }, `${a.name} moved to ${when(slot)}. They have been told.`)}>Move and tell the patient</button>
            </>
          )}
          {(a.urgent || moving) && <label className="cal-check"><input type="checkbox" checked={squeeze} onChange={(e) => setSqueeze(e.target.checked)} /> allow double booking (urgent)</label>}
          <label>Message to the patient (optional) <input value={reason} maxLength={200} placeholder="for example: the doctor asked to see you earlier" onChange={(e) => setReason(e.target.value)} /></label>
          {requested && <button className="btn sm" onClick={() => run('decline', { reason }, `${a.name}'s request declined. They have been told.`)}>Decline</button>}
          {confirmed && <button className="btn sm" onClick={() => run('cancel', { reason }, `${a.name}'s appointment cancelled. They have been told and the slot is free.`)}>Cancel it</button>}
          {confirmed && <button className="btn sm" onClick={() => run('close', { status: 'completed' }, `${a.name} marked as seen.`)}>Seen</button>}
          {confirmed && <button className="btn sm" onClick={() => run('close', { status: 'no_show' }, `${a.name} marked as not attended.`)}>Did not come</button>}
        </div>
      )}
      <details className="cal-hist"><summary>History</summary>{(a.history || []).map((h, i) => <div key={i}><small>{h.at}</small> <b>{h.actor}</b> {h.event} {h.detail}</div>)}</details>
    </section>
  )
}

function Book({ slot, reserved, role, patients, onDone, onFail, onClose }) {
  const [pid, setPid] = useState('')
  const [reason, setReason] = useState('routine')
  const [note, setNote] = useState('')
  const [urgent, setUrgent] = useState(!!reserved)
  return (
    <section className="card soft cal-detail">
      <div className="card-h"><h3 style={{ margin: 0 }}>Book {when(slot)}</h3>{reserved && <span className="chip rose">urgent slot</span>}<span style={{ flex: 1 }} /><button className="btn sm" onClick={onClose}>Close</button></div>
      <div className="cal-actions">
        <label>Patient <select value={pid} onChange={(e) => setPid(e.target.value)}><option value="">Choose…</option>{patients.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
        <label>Reason <select value={reason} onChange={(e) => setReason(e.target.value)}>{Object.entries(REASON).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Note <input value={note} maxLength={300} onChange={(e) => setNote(e.target.value)} /></label>
        <label className="cal-check"><input type="checkbox" checked={urgent} onChange={(e) => setUrgent(e.target.checked)} /> urgent case</label>
        <button className="btn sm go" disabled={!pid} onClick={() => bookAppointment({ pid: Number(pid), slot, reason, note, urgent, actor: role }).then(() => onDone('Booked and confirmed. The patient has been told.')).catch(onFail)}>Book and confirm</button>
      </div>
    </section>
  )
}

const TIMES = (() => { const o = []; for (let h = 9; h <= 17; h++) for (const m of ['00', '20', '40']) { if (h === 17 && m !== '00') continue; if (h === 12 || h === 13) continue; o.push(`${String(h).padStart(2, '0')}:${m}`) } return o })()

const ENDS = [...TIMES, '12:00', '14:00', '17:00'].filter((t, i, a) => a.indexOf(t) === i).sort()

function Tools({ role, clinic, days, blocks, onDone, onFail }) {
  const first = days[0] ? days[0].date : clinic.first_open_day
  const [day, setDay] = useState(first)
  const [from, setFrom] = useState('09:00')
  const [to, setTo] = useState('12:00')
  const [mode, setMode] = useState('move')
  const [reason, setReason] = useState('')
  const [plan, setPlan] = useState(null)
  const [mins, setMins] = useState(20)
  const [lateFrom, setLateFrom] = useState('09:00')
  const body = { date: day, start: from, end: to, mode, reason, actor: role }
  const names = (r) => `${r.name}`
  return (
    <section className="card soft cal-tools">
      <div className="card-h"><h3 style={{ margin: 0 }}>When the doctor is called away</h3><span className="chip">patients are told automatically</span></div>
      <div className="cal-actions">
        <label>Day <select value={day} onChange={(e) => { setDay(e.target.value); setPlan(null) }}>{days.map((d) => <option key={d.date} value={d.date}>{dayLabel(d.date)}</option>)}</select></label>
        <label>Away from <select value={from} onChange={(e) => { setFrom(e.target.value); setPlan(null) }}>{TIMES.map((t) => <option key={t}>{t}</option>)}</select></label>
        <label>Back at <select value={to} onChange={(e) => { setTo(e.target.value); setPlan(null) }}>{ENDS.map((t) => <option key={t}>{t}</option>)}</select></label>
        <label>Patients in that time <select value={mode} onChange={(e) => { setMode(e.target.value); setPlan(null) }}><option value="move">move to the next free slots</option><option value="cancel">cancel and tell them</option></select></label>
        <label>Reason (shown to patients) <input value={reason} maxLength={200} placeholder="for example: emergency operation" onChange={(e) => setReason(e.target.value)} /></label>
        <button className="btn sm" onClick={() => unavailable({ ...body, preview: true }).then(setPlan).catch(onFail)}>Show who is affected</button>
      </div>
      {plan && (
        <div className="cal-plan">
          {plan.affected.length === 0 ? <p className="muted">Nobody has an appointment in that time. Applying only blocks it for new bookings.</p> : (
            <table className="rt"><thead><tr><th>Patient</th><th>Now</th><th>{plan.mode === 'move' ? 'Would move to' : 'Would be'}</th></tr></thead>
              <tbody>{plan.affected.map((r) => <tr key={r.id}><td>{names(r)}{r.urgent ? ' (urgent)' : ''}</td><td>{when(r.old)}</td><td>{plan.mode === 'move' ? (r.new ? when(r.new) : 'no slot found, will be cancelled') : 'cancelled'}</td></tr>)}</tbody></table>
          )}
          <button className="btn sm go" onClick={() => unavailable({ ...body, preview: false }).then((o) => { setPlan(null); onDone(`Doctor away ${dayLabel(day)} ${from}-${to}. ${o.affected.length} patient(s) told.`) }).catch(onFail)}>Apply and tell {plan.affected.length} patient{plan.affected.length === 1 ? '' : 's'}</button>
        </div>
      )}
      <div className="card-h" style={{ marginTop: 16 }}><h3 style={{ margin: 0 }}>Running late</h3><span className="chip">keeps everyone's slot, tells them when to come</span></div>
      <div className="cal-actions">
        <label>Day <select value={day} onChange={(e) => setDay(e.target.value)}>{days.map((d) => <option key={d.date} value={d.date}>{dayLabel(d.date)}</option>)}</select></label>
        <label>From <select value={lateFrom} onChange={(e) => setLateFrom(e.target.value)}>{TIMES.map((t) => <option key={t}>{t}</option>)}</select></label>
        <label>Delay <select value={mins} onChange={(e) => setMins(Number(e.target.value))}>{[10, 15, 20, 30, 45, 60, 90].map((m) => <option key={m} value={m}>{m} minutes</option>)}</select></label>
        <button className="btn sm go" onClick={() => runningLate({ date: day, from_time: lateFrom, minutes: mins, reason, actor: role }).then((o) => onDone(`${o.informed} patient(s) told to expect about ${mins} minutes' delay.`)).catch(onFail)}>Tell waiting patients</button>
      </div>
      {blocks.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <small className="muted">Times blocked for new bookings</small>
          {blocks.map((b) => <div key={b.id} className="cal-block"><b>{dayLabel(b.date)} {b.start}-{b.end}</b> {b.reason && <span>· {b.reason}</span>} <small>({b.by})</small> <button className="btn sm" onClick={() => removeBlock(b.id).then(() => onDone('Block removed. The slots are free again.')).catch(onFail)}>Remove</button></div>)}
        </div>
      )}
    </section>
  )
}
