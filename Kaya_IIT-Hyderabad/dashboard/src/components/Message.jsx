import { useEffect, useState } from 'react'
import { getMessages, getReports, markHandled, sendMessage, sendPrescription } from '../api'
import { TONE } from '../ui'

const URGENT = [
  { id: 'u_clinic', label: 'Come to the clinic today', action: 'come_to_clinic', title: 'Please come to the clinic today',
    body: 'I have looked at your recent readings and I would like to see you at the clinic today. Please come as soon as you can and bring your medicines.' },
  { id: 'u_er', label: 'Go to the emergency room now', action: 'go_to_er', title: 'Please go to the emergency room now',
    body: 'Your readings are a serious concern. Please go to the nearest emergency room now. If you feel very unwell, call 108 straight away.' },
  { id: 'u_call', label: 'Call the clinic', action: 'call_clinic', title: 'Please call the clinic',
    body: 'I would like to speak to you about your readings. Please call the clinic as soon as you see this message.' },
]
const ADVICE = [
  { id: 'a_walk', label: 'Walk after meals', title: 'Please walk after meals', body: 'Looking at your data, a 15 to 20 minute walk after dinner will help your sugar. Please try it every day this week.' },
  { id: 'a_bed', label: 'Check sugar before bed', title: 'Check your sugar before bed', body: 'Your data shows dips at night. Please check your sugar before bed and have a small snack if it is below 110.' },
  { id: 'a_portions', label: 'Smaller portions', title: 'Try smaller portions of rice and roti', body: 'Your sugar rises a lot after meals. Please try smaller portions of rice and roti, and add more vegetables and dal.' },
  { id: 'a_meds', label: 'I will change your medicines', title: 'I want to review your medicines', body: 'After looking at your data I would like to change your medicines. I will send you a new prescription shortly. Please do not change anything until then.' },
]
const ACTION_TEXT = { come_to_clinic: 'Come to the clinic', go_to_er: 'Go to the emergency room', call_clinic: 'Call the clinic' }
const CHECK_TEXT = { emergency: ['🚨 Possible emergency', 'rose'], doctor: ['Helper: needs a doctor', 'butter'], self_insisted: ['Sent after helper advice', 'sky'], unsure: ['Helper unavailable', 'sky'] }
const RX_TEXT = { start: 'Start', stop: 'Stop', change_dose: 'Change dose' }

function Segment({ value, onChange, options }) {
  return <div className="seg">{options.map(([k, label]) => <button key={k} type="button" className={value === k ? 'on' : ''} onClick={() => onChange(k)}>{label}</button>)}</div>
}

/** What the patient wrote to the doctor. Replying (or marking it handled) clears the flag on the patient list. */
function FromPatient({ pid, items, onSent }) {
  const [reply, setReply] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const theirs = items.filter((m) => m.kind === 'patient')
  const open = theirs.some((m) => !m.read)
  useEffect(() => { setReply(''); setErr(null) }, [pid])
  if (!theirs.length) return null
  const done = (p) => p.then(onSent).catch((e) => setErr(e.message)).finally(() => setBusy(false))
  const send = () => { setBusy(true); setErr(null); done(sendMessage(pid, { kind: 'advice', title: 'Reply from your doctor', body: reply, action: null, template: null, translate: true }).then(() => setReply(''))) }
  return (
    <section className="card soft rec-sec" style={{ boxShadow: 'none' }}>
      <div className="card-h"><h2>From the patient</h2>{open ? <span className="chip rose">Needs a reply</span> : <span className="chip mint">Answered</span>}</div>
      <div style={{ display: 'grid', gap: 8, marginBottom: 10 }}>
        {theirs.slice(0, 5).map((m) => (
          <div key={m.id} className="rep-row" style={{ cursor: 'default' }}>
            <span style={{ minWidth: 0, flex: 1 }}><b style={{ fontWeight: 700 }}>{m.body}</b><small>{m.created.slice(0, 16)}</small></span>
            <span style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              {CHECK_TEXT[m.check] && <span className="chip" style={{ background: TONE[CHECK_TEXT[m.check][1]].bg, color: TONE[CHECK_TEXT[m.check][1]].dd }}>{CHECK_TEXT[m.check][0]}</span>}
              <span className="chip" style={m.read ? { background: TONE.mint.bg, color: TONE.mint.dd } : { background: TONE.rose.bg, color: TONE.rose.dd }}>{m.read ? '✓ Handled' : 'Unanswered'}</span>
            </span>
          </div>
        ))}
      </div>
      {open && (
        <div className="medform" style={{ boxShadow: 'none', padding: 0, background: 'transparent' }}>
          <label>Reply<textarea rows={3} maxLength={1000} value={reply} placeholder="Your reply goes to the patient app within seconds" onChange={(e) => setReply(e.target.value)} /></label>
          <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
            <button className="btn go" disabled={busy || !reply.trim()} onClick={send}>Send reply</button>
            <button className="btn sm" disabled={busy} onClick={() => { setBusy(true); done(markHandled(pid)) }}>Mark as handled without replying</button>
            {err && <span style={{ fontWeight: 700, color: 'var(--rose-dd)' }}>{err}</span>}
          </div>
        </div>
      )}
    </section>
  )
}

function Compose({ pid, onSent }) {
  const [kind, setKind] = useState('urgent')
  const [f, setF] = useState({ title: '', body: '', action: 'come_to_clinic', template: null })
  const [translate, setTranslate] = useState(true)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const templates = kind === 'urgent' ? URGENT : ADVICE
  const apply = (t) => setF({ title: t.title, body: t.body, action: t.action || f.action, template: t.id })
  useEffect(() => { setF({ title: '', body: '', action: 'come_to_clinic', template: null }); setMsg(null) }, [kind, pid])
  const send = () => {
    setBusy(true); setMsg(null)
    sendMessage(pid, { kind, title: f.title, body: f.body, action: kind === 'urgent' ? f.action : null, template: f.template, translate })
      .then(() => { setMsg({ ok: true, text: kind === 'urgent' ? 'Urgent message sent. It shows at the top of the patient app.' : 'Message sent.' }); setF({ title: '', body: '', action: f.action, template: null }); onSent() })
      .catch((e) => setMsg({ ok: false, text: e.message })).finally(() => setBusy(false))
  }
  return (
    <section className="card soft rec-sec" style={{ boxShadow: 'none' }}>
      <div className="card-h"><h2>Send a message</h2><span className="chip">appears in the patient app within seconds</span></div>
      <Segment value={kind} onChange={setKind} options={[['urgent', '🚨 Urgent'], ['advice', '💬 Advice']]} />
      <div className="row wrap" style={{ gap: 6, margin: '12px 0 8px' }}>
        <span className="muted" style={{ fontSize: 12, fontWeight: 700 }}>Quick start</span>
        {templates.map((t) => <button key={t.label} className="preset" onClick={() => apply(t)}>{t.label}</button>)}
      </div>
      <div className="medform" style={{ boxShadow: 'none', padding: 0, background: 'transparent' }}>
        {kind === 'urgent' && (
          <label>What should the patient do?
            <Segment value={f.action} onChange={(a) => setF({ ...f, action: a })} options={Object.entries(ACTION_TEXT)} />
          </label>
        )}
        <label>Title<input type="text" value={f.title} maxLength={80} placeholder={kind === 'urgent' ? 'Urgent: please come to the clinic' : 'A short heading'} onChange={(e) => setF({ ...f, title: e.target.value, template: null })} /></label>
        <label>Message<textarea rows={4} maxLength={1000} value={f.body} placeholder="Write in plain words the patient will understand" onChange={(e) => setF({ ...f, body: e.target.value, template: null })} /></label>
        <label className="chk">
          <input type="checkbox" checked={translate} onChange={(e) => setTranslate(e.target.checked)} />
          {f.template ? 'This quick-start text is already available in Hindi, Telugu and Kannada.' : 'Translate for the patient into Hindi, Telugu and Kannada (sent to Sarvam AI; leave out names and other identifying details)'}
        </label>
        <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
          <button className="btn go" disabled={busy || !f.body.trim()} onClick={send}>{kind === 'urgent' ? '🚨 Send urgent message' : 'Send message'}</button>
          {msg && <span style={{ fontWeight: 700, color: msg.ok ? 'var(--mint-dd)' : 'var(--rose-dd)' }}>{msg.text}</span>}
        </div>
      </div>
    </section>
  )
}

function Prescribe({ pid, onSent }) {
  const [meds, setMeds] = useState([])
  const [rows, setRows] = useState({})          // current medicine -> { action: 'none'|'stop'|'change_dose', dose }
  const [added, setAdded] = useState([])        // new medicines: { medicine, dose, instructions }
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const load = () => getReports(pid).then((d) => setMeds(d.medications)).catch(() => {})
  useEffect(() => { setRows({}); setAdded([]); setNote(''); setMsg(null); load() }, [pid])
  const setRow = (name, patch) => setRows((r) => ({ ...r, [name]: { action: 'none', dose: '', ...r[name], ...patch } }))
  const changes = [
    ...meds.filter((m) => rows[m.name] && rows[m.name].action !== 'none').map((m) => ({ medicine: m.name, action: rows[m.name].action, dose: rows[m.name].dose || '', instructions: '' })),
    ...added.filter((a) => a.medicine.trim()).map((a) => ({ medicine: a.medicine.trim(), action: 'start', dose: a.dose, instructions: a.instructions })),
  ]
  const invalid = changes.some((c) => c.action !== 'stop' && !c.dose.trim())
  const send = () => {
    setBusy(true); setMsg(null)
    sendPrescription(pid, { changes, note })
      .then(() => { setMsg({ ok: true, text: 'Prescription sent. The medicine list and Reports tab are updated, and the patient app shows it.' }); setRows({}); setAdded([]); setNote(''); load(); onSent() })
      .catch((e) => setMsg({ ok: false, text: e.message })).finally(() => setBusy(false))
  }
  return (
    <section className="card soft rec-sec" style={{ boxShadow: 'none' }}>
      <div className="card-h"><h2>Consultation note and prescription</h2><span className="chip">virtual visit</span></div>
      <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>Change any medicine below, add a new one, and write your note. It is added to the patient's reports and medicine list, and pops up in their app.</div>
      {meds.map((m) => {
        const r = rows[m.name] || { action: 'none', dose: '' }
        return (
          <div key={m.name} className="medrow">
            <div style={{ minWidth: 0, flex: 1 }}><b>{m.name}</b><small>{m.dose}</small></div>
            <Segment value={r.action} onChange={(a) => setRow(m.name, { action: a })} options={[['none', 'No change'], ['stop', 'Stop'], ['change_dose', 'Change dose']]} />
            {r.action === 'change_dose' && <input className="rx-in" type="text" placeholder="New dose, for example 1000 mg twice a day" maxLength={80} value={r.dose} onChange={(e) => setRow(m.name, { dose: e.target.value })} />}
          </div>
        )
      })}
      {added.map((a, i) => (
        <div key={i} className="medrow" style={{ alignItems: 'flex-start' }}>
          <span className="chip mint">New</span>
          <div style={{ display: 'grid', gap: 6, flex: 1, minWidth: 220 }}>
            <input className="rx-in" type="text" placeholder="Medicine name" maxLength={60} value={a.medicine} onChange={(e) => setAdded(added.map((x, j) => (j === i ? { ...x, medicine: e.target.value } : x)))} />
            <input className="rx-in" type="text" placeholder="Dose, for example 100 mg once a day" maxLength={80} value={a.dose} onChange={(e) => setAdded(added.map((x, j) => (j === i ? { ...x, dose: e.target.value } : x)))} />
            <input className="rx-in" type="text" placeholder="Instructions, for example after breakfast" maxLength={200} value={a.instructions} onChange={(e) => setAdded(added.map((x, j) => (j === i ? { ...x, instructions: e.target.value } : x)))} />
          </div>
          <button className="btn sm" onClick={() => setAdded(added.filter((_, j) => j !== i))}>Remove</button>
        </div>
      ))}
      <div style={{ margin: '10px 0' }}><button className="preset" onClick={() => setAdded([...added, { medicine: '', dose: '', instructions: '' }])}>＋ Add a medicine</button></div>
      <div className="medform" style={{ boxShadow: 'none', padding: 0, background: 'transparent' }}>
        <label>Consultation note<textarea rows={4} maxLength={1000} value={note} placeholder="What you saw in the data and why you are changing the plan" onChange={(e) => setNote(e.target.value)} /></label>
        <div className="row" style={{ gap: 10, flexWrap: 'wrap' }}>
          <button className="btn go" disabled={busy || invalid || (!changes.length && !note.trim())} onClick={send}>Send prescription to the patient</button>
          {invalid && <span style={{ fontWeight: 700, color: 'var(--butter-dd)' }}>Give a dose for every medicine you start or change.</span>}
          {msg && <span style={{ fontWeight: 700, color: msg.ok ? 'var(--mint-dd)' : 'var(--rose-dd)' }}>{msg.text}</span>}
        </div>
        <div className="muted" style={{ fontSize: 11.5 }}>Demonstration only: all patients are synthetic and nothing here is a real prescription.</div>
      </div>
    </section>
  )
}

function Sent({ items: all }) {
  const items = all.filter((m) => m.kind !== 'patient')
  return (
    <section className="card soft rec-sec" style={{ boxShadow: 'none' }}>
      <div className="card-h"><h2>Sent to this patient</h2><span className="chip">{items.length}</span></div>
      {items.length === 0 ? <div className="muted" style={{ fontWeight: 600 }}>Nothing sent yet.</div> : (
        <div style={{ display: 'grid', gap: 8 }}>
          {items.map((m) => {
            const t = TONE[m.kind === 'urgent' ? 'rose' : m.kind === 'prescription' ? 'mint' : 'sky']
            return (
              <div key={m.id} className="rep-row" style={{ cursor: 'default' }}>
                <span className="chip" style={{ background: t.bg, color: t.dd }}>{m.kind === 'urgent' ? '🚨 Urgent' : m.kind === 'prescription' ? '℞ Prescription' : '💬 Advice'}</span>
                <span style={{ minWidth: 0, flex: 1 }}>
                  <b>{m.title}</b>
                  <small>{m.created.slice(0, 16)}{m.action ? ` · ${ACTION_TEXT[m.action]}` : ''}{m.changes?.length ? ` · ${m.changes.map((c) => `${RX_TEXT[c.action]} ${c.medicine}`).join(', ')}` : ''}</small>
                  {m.body && <small>{m.body.length > 140 ? `${m.body.slice(0, 140)}…` : m.body}</small>}
                </span>
                <span className="chip" style={m.read ? { background: TONE.mint.bg, color: TONE.mint.dd } : { background: TONE.butter.bg, color: TONE.butter.dd }}>{m.read ? '✓ Seen by the patient' : 'Not seen yet'}</span>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

export default function MessageTab({ pid }) {
  const [items, setItems] = useState([])
  const load = () => getMessages(pid).then((d) => setItems(d.items)).catch(() => {})
  const changed = () => { load(); window.dispatchEvent(new Event('kaya:messages')) }     // the patient list refreshes its flags
  useEffect(() => { setItems([]); load(); const id = setInterval(load, 5000); return () => clearInterval(id) }, [pid])
  return (
    <>
      <FromPatient pid={pid} items={items} onSent={changed} />
      <Compose pid={pid} onSent={changed} />
      <Prescribe pid={pid} onSent={changed} />
      <Sent items={items} />
    </>
  )
}
