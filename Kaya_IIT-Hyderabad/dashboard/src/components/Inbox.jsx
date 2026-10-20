import { useEffect, useState } from 'react'
import { getMessages, readMessage } from '../api'

const ACT = { come_to_clinic: 'msg_act_clinic', go_to_er: 'msg_act_er', call_clinic: 'msg_act_call' }
const RX = { start: 'rx_start', stop: 'rx_stop', change_dose: 'rx_dose' }

/** Messages from the doctor, checked every few seconds so an urgent message shows up while the patient is at home. */
export function useInbox(pid) {
  const [items, setItems] = useState([])
  const load = () => getMessages(pid).then((d) => setItems(d.items)).catch(() => {})
  useEffect(() => { setItems([]); load(); const id = setInterval(load, 4000); return () => clearInterval(id) }, [pid])
  const ack = (m) => readMessage(pid, m.id).then(load).catch(() => {})
  return { items, ack }
}

export function InboxBanners({ t, inbox, showPast }) {
  const unread = inbox.items.filter((m) => !m.read)
  const urgent = unread.filter((m) => m.kind === 'urgent')
  const advice = unread.filter((m) => m.kind === 'advice')
  const past = inbox.items.filter((m) => m.read && m.kind !== 'prescription').slice(0, 3)
  return (
    <>
      {urgent.map((m) => (
        <div key={m.id} className="in-urgent" role="alert">
          <div className="in-h">🚨 {t('msg_urgent')}</div>
          <b>{m.title}</b>
          <p>{m.body}</p>
          {m.action && <div className="in-act">{t(ACT[m.action])}</div>}
          <button onClick={() => inbox.ack(m)}>{t('msg_seen')}</button>
        </div>
      ))}
      {advice.map((m) => (
        <div key={m.id} className="in-advice">
          <div className="in-h">💬 {t('msg_advice')}</div>
          <b>{m.title}</b>
          <p>{m.body}</p>
          <button onClick={() => inbox.ack(m)}>{t('msg_seen')}</button>
        </div>
      ))}
      {showPast && past.length > 0 && (
        <details className="in-past">
          <summary>{t('msg_past')} ({past.length})</summary>
          {past.map((m) => <div key={m.id}><b>{m.title}</b><small>{m.created.slice(0, 10)}</small><p>{m.body}</p></div>)}
        </details>
      )}
    </>
  )
}

export function RxModal({ t, inbox, onOpenReports }) {
  const rx = inbox.items.find((m) => m.kind === 'prescription' && !m.read)
  if (!rx) return null
  return (
    <div className="rx-overlay" role="dialog" aria-modal="true">
      <div className="rx-card">
        <div className="in-h">℞ {t('rx_title')}</div>
        <div className="rx-list">
          {rx.changes.map((c, i) => (
            <div key={i} className={`rx-row ${c.action}`}>
              <span className="rx-tag">{t(RX[c.action])}</span>
              <div><b>{c.medicine}</b>{c.dose && <span> · {c.dose}</span>}{c.instructions && <small>{c.instructions}</small>}</div>
            </div>
          ))}
        </div>
        {rx.body && <div className="rx-note"><b>{t('rx_note_title')}</b><p>{rx.body}</p></div>}
        <button className="big-btn" onClick={() => { inbox.ack(rx); onOpenReports() }}>{t('rx_ok')}</button>
      </div>
    </div>
  )
}
