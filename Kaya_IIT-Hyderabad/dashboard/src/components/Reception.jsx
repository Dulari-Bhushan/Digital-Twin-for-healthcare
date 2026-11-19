import { useEffect, useState } from 'react'
import { apptAct, getApptQueue, getClinic, getSchedule } from '../api'
import Schedule, { reasonText, whenText } from './Schedule'

function Request({ a, slots, onDone, onFail }) {
  const [slot, setSlot] = useState('')
  const [why, setWhy] = useState('')
  const [declining, setDeclining] = useState(false)
  const act = (action, body, msg) => apptAct(a.id, action, { actor: 'reception', ...body }).then(() => onDone(msg)).catch(onFail)
  return (
    <div className={`rq ${a.urgent ? 'urgent' : ''}`}>
      <div className="rq-h">
        <b>{a.name}</b>
        {a.urgent && <span className="chip rose">Urgent</span>}
        <small>{a.created.slice(5, 16).replace('-', '/')}</small>
      </div>
      <div className="rq-w">{whenText(a.slot)} · {reasonText(a.reason)}</div>
      {a.note && <div className="rq-n">“{a.note}”</div>}
      {a.urgent && !a.slot && (
        <label className="rq-sel">Place in <select value={slot} onChange={(e) => setSlot(e.target.value)}><option value="">Choose a slot…</option>{slots.map((s) => <option key={s.v} value={s.v}>{s.label}</option>)}</select></label>
      )}
      {declining ? (
        <div className="rq-a">
          <input value={why} maxLength={200} placeholder="Reason shown to the patient" onChange={(e) => setWhy(e.target.value)} />
          <button className="btn sm" onClick={() => act('decline', { reason: why }, `${a.name}'s request declined. They have been told.`)}>Send</button>
          <button className="btn sm" onClick={() => setDeclining(false)}>Back</button>
        </div>
      ) : (
        <div className="rq-a">
          <button className="btn sm go" disabled={!a.slot && !slot} onClick={() => act('confirm', { slot: slot || undefined }, `${a.name} confirmed for ${whenText(slot || a.slot)}. They have been told.`)}>{a.slot ? 'Confirm' : 'Place and confirm'}</button>
          <button className="btn sm" onClick={() => setDeclining(true)}>Decline</button>
        </div>
      )}
    </div>
  )
}

/** Reception: requests waiting for an answer (urgent first) beside the calendar. */
export default function Reception({ patients, onChanged, onOpenPatient }) {
  const [q, setQ] = useState([])
  const [slots, setSlots] = useState([])
  const [flash, setFlash] = useState('')
  const [err, setErr] = useState('')
  const load = () => {
    getApptQueue().then((d) => setQ(d.items)).catch(() => {})
    getClinic().then((c) => getSchedule(c.first_open_day, 7)).then((s) => setSlots(s.days.filter((d) => !d.closed).flatMap((d) => d.slots
      .filter((x) => !x.past && !x.block && !x.appts.some((a) => ['requested', 'confirmed'].includes(a.status)))
      .map((x) => ({ v: `${d.date} ${x.time}`, label: `${whenText(`${d.date} ${x.time}`)}${x.reserved ? ' (urgent slot)' : ''}`, reserved: x.reserved }))))).catch(() => {})
  }
  useEffect(() => { load(); const id = setInterval(load, 6000); return () => clearInterval(id) }, [])
  const done = (m) => { setFlash(m); setErr(''); load(); if (onChanged) onChanged(); setTimeout(() => setFlash(''), 5000) }
  const urgent = q.filter((a) => a.urgent)
  return (
    <div className="recep">
      <aside className="recep-q">
        <div className="card-h"><h2 style={{ margin: 0 }}>Requests</h2><span className={`chip ${q.length ? 'butter' : 'mint'}`}>{q.length} waiting</span>{urgent.length > 0 && <span className="chip rose">{urgent.length} urgent</span>}</div>
        {flash && <div className="cal-flash" role="status">✓ {flash}</div>}
        {err && <div className="cal-err" role="alert">{err}</div>}
        {q.length === 0 ? <p className="muted">No requests waiting. New ones from the patient app appear here within seconds.</p> : q.map((a) => <Request key={a.id} a={a} slots={slots} onDone={done} onFail={(e) => setErr(e.message)} />)}
        <p className="note">Urgent requests need no time: choose one of the slots held back for urgent cases, or any free slot. Patients cannot book the urgent slots themselves.</p>
      </aside>
      <section className="recep-c">
        <Schedule role="reception" patients={patients} onChanged={() => { load(); if (onChanged) onChanged() }} onOpenPatient={onOpenPatient} />
      </section>
    </div>
  )
}
