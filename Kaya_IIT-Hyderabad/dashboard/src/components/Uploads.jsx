import { useEffect, useRef, useState } from 'react'
import { deleteUpload, getUploads, readUpload, uploadReport, verifyUpload } from '../api'
import { TONE } from '../ui'
import { showVal } from './Reports'

const CAT = { 'blood test': 'cat_blood', 'scan or x-ray': 'cat_scan', prescription: 'cat_rx', 'discharge summary': 'cat_discharge', 'eye report': 'cat_eye', other: 'cat_other' }
const CAT_EN = { 'blood test': 'Blood test', 'scan or x-ray': 'Scan or X-ray', prescription: 'Prescription', 'discharge summary': 'Discharge summary', 'eye report': 'Eye report', other: 'Other' }
const MAX = 8 * 1024 * 1024
const OK = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp']
const fmt = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
const EN_STATE = { pending: 'Reading…', reading: 'Reading…', no_values: 'Text read; no lab values recognised', failed: 'Could not be read', no_text: 'No text found', off: '' }
/** One line about whether the document was read, in the patient's language when `t` is given. */
function statusLine(u, t) {
  const o = u.ocr || { state: 'off' }
  if (o.state === 'off') return null
  const tone = o.state === 'done' ? 'var(--mint-dd)' : o.state === 'failed' || o.state === 'no_text' ? 'var(--rose-dd)' : 'var(--muted)'
  const txt = t
    ? { pending: t('ocr_reading'), reading: t('ocr_reading'), done: t('ocr_done', { n: o.results }), no_values: t('ocr_text'), failed: t('ocr_failed'), no_text: t('ocr_notext') }[o.state]
    : o.state === 'done' ? `Read automatically: ${o.results} lab values added to the reports` : EN_STATE[o.state]
  return <small style={{ color: tone, fontWeight: 800 }}>{o.state === 'pending' || o.state === 'reading' ? '⏳ ' : o.state === 'done' ? '✓ ' : ''}{txt}</small>
}

const isBusy = (u) => u.ocr && (u.ocr.state === 'pending' || u.ocr.state === 'reading')

/** While any upload is still being read, check again every few seconds; when some finish, call onChange(finishedItems). */
function useReadingPoll(pid, items, setItems, onChange) {
  const busy = !!items && items.some(isBusy)
  const waiting = useRef([])
  useEffect(() => {
    if (!busy) return undefined
    waiting.current = items.filter(isBusy).map((u) => u.id)
    const id = setInterval(() => getUploads(pid).then((d) => {
      setItems(d.items)
      const fin = d.items.filter((u) => waiting.current.includes(u.id) && !isBusy(u))
      if (fin.length) { waiting.current = waiting.current.filter((x) => !fin.some((u) => u.id === x)); if (onChange) onChange(fin) }
    }).catch(() => {}), 2500)
    return () => clearInterval(id)
  }, [busy, pid]) // eslint-disable-line
}

const fileUrl = (pid, u) => `/api/patients/${pid}/uploads/${u.id}/file`

function Thumb({ pid, u, size = 52 }) {
  const box = { width: size, height: size, borderRadius: 12, flex: 'none', display: 'grid', placeItems: 'center', background: '#fff', overflow: 'hidden', fontSize: size / 2 }
  return u.media.startsWith('image/') ? <img src={fileUrl(pid, u)} alt="" style={{ ...box, objectFit: 'cover' }} /> : <div style={box}>📄</div>
}

/** The result of a reading: what was found, in simple words, and a way to open the new report. */
function ReadSummary({ t, uid, reports, onOpen, onClose }) {
  const rep = reports && reports.find((r) => r.upload_id === uid)
  if (!rep) return <div className="p-card" style={{ background: 'var(--mint)' }}><b style={{ color: 'var(--mint-dd)' }}>⏳ {t('ocr_reading')}</b></div>
  const rows = rep.sections.flatMap((s) => s.rows)
  const bad = rows.filter((r) => r.tone !== 'mint')
  return (
    <div className="p-card" style={{ background: 'var(--mint)' }}>
      <div style={{ fontWeight: 800, fontSize: 17, color: 'var(--mint-dd)' }}>✅ {t('sum_title')}</div>
      {rows.length > 0 && <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--mint-dd)', margin: '4px 0' }}>{t('sum_counts', { n: rows.length, k: bad.length })}</div>}
      {bad.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '6px 0' }}>
          {bad.map((r) => <span key={r.key} className="chip" style={{ background: TONE[r.tone].bg, color: TONE[r.tone].dd }}>{r.test} {showVal(r)} {r.unit}</span>)}
        </div>
      )}
      <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--mint-dd)', lineHeight: 1.5 }}>{t('sum_note')}</div>
      <button className="big-btn" onClick={() => { onClose(); if (onOpen) onOpen(rep.id) }}>{t('sum_view')}</button>
    </div>
  )
}

/** Patient app: choose a PDF or photo, name it, upload it, then decide whether the AI may read it. */
export function PatientUploads({ t, pid, today, onChange, reports, onOpenReport }) {
  const [items, setItems] = useState(null)
  const [avail, setAvail] = useState(false)
  const [ask, setAsk] = useState(null)         // an upload that was just saved and is waiting for the patient's yes or no
  const [doneId, setDoneId] = useState(null)   // an upload that has just been read, for the summary card
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('blood test')
  const [date, setDate] = useState(today)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const input = useRef(null)
  useEffect(() => { setItems(null); getUploads(pid).then((d) => { setItems(d.items); setAvail(d.reading_available) }).catch(() => setItems([])) }, [pid])
  useEffect(() => setDate(today), [today])
  useReadingPoll(pid, items, setItems, (fin) => {
    if (onChange) onChange()
    const ok = fin.find((u) => u.ocr.state === 'done' || u.ocr.state === 'no_values')
    if (ok) setDoneId(ok.id)
  })

  const pick = (e) => {
    const f = e.target.files && e.target.files[0]
    if (!f) return
    setErr(null)
    if (!OK.includes(f.type)) { setErr(t('up_bad')); return }
    if (f.size > MAX) { setErr(t('up_big')); return }
    setFile(f)
    setTitle(f.name.replace(/\.[^.]+$/, '').slice(0, 60))
  }
  const reset = () => { setFile(null); setTitle(''); if (input.current) input.current.value = '' }
  const send = () => {
    setBusy(true); setErr(null)
    uploadReport(pid, file, { title, category, date, read: false })
      .then((m) => { setItems((x) => [m, ...(x || [])]); reset(); setDoneId(null); if (avail) setAsk(m) })
      .catch((e) => setErr(e.message))
      .finally(() => setBusy(false))
  }
  const startRead = (u) => {
    setAsk(null); setDoneId(null)
    readUpload(pid, u.id).then((m) => setItems((x) => (x || []).map((i) => (i.id === m.id ? m : i)))).catch((e) => setErr(e.message))
  }
  const remove = (u) => { if (window.confirm(t('up_confirm'))) deleteUpload(pid, u.id).then((d) => setItems(d.items)).catch(() => {}) }

  return (
    <>
      <div className="p-card" style={{ background: 'var(--sky)' }}>
        <div style={{ fontWeight: 800, fontSize: 17, color: 'var(--sky-dd)' }}>📎 {t('up_title')}</div>
        <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--sky-dd)', opacity: 0.85, margin: '2px 0 10px' }}>{t('up_sub')}</div>
        <input ref={input} id="up-file" type="file" accept="application/pdf,image/png,image/jpeg,image/webp" onChange={pick} style={{ display: 'none' }} />
        {!file ? (
          <label htmlFor="up-file" className="big-btn" style={{ display: 'block', textAlign: 'center', marginTop: 0, cursor: 'pointer' }}>{t('up_choose')}</label>
        ) : (
          <div style={{ display: 'grid', gap: 8 }}>
            <div className="up-file">{file.type === 'application/pdf' ? '📄' : '🖼️'} <b>{file.name}</b> <small>{Math.max(1, Math.round(file.size / 1024))} KB</small><button className="mini" style={{ background: 'var(--rose-d)', width: 30, height: 30 }} onClick={reset} aria-label={t('up_remove')}>✕</button></div>
            <label className="up-l">{t('up_name')}<input className="up-in" value={title} maxLength={80} onChange={(e) => setTitle(e.target.value)} /></label>
            <label className="up-l">{t('up_type')}
              <select className="up-in" value={category} onChange={(e) => setCategory(e.target.value)}>{Object.entries(CAT).map(([k, key]) => <option key={k} value={k}>{t(key)}</option>)}</select>
            </label>
            <label className="up-l">{t('up_date')}<input className="up-in" type="date" value={date} max={today} onChange={(e) => setDate(e.target.value)} /></label>
            <button className="big-btn" style={{ marginTop: 4 }} disabled={busy} onClick={send}>{busy ? t('up_busy') : t('up_btn')}</button>
          </div>
        )}
        {err && <div style={{ marginTop: 8, fontWeight: 700, fontSize: 13, color: 'var(--rose-dd)' }}>{err}</div>}
        <div className="note" style={{ color: 'var(--sky-dd)' }}>{t('up_note')}</div>
      </div>
      {ask && (
        <div className="p-card" style={{ background: 'var(--butter)' }}>
          <div style={{ fontWeight: 800, fontSize: 17, color: 'var(--butter-dd)' }}>🤖 {t('ask_read_title')}</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--butter-dd)', margin: '4px 0 2px' }}><span style={{ overflowWrap: 'anywhere' }}>“{ask.title}”</span> {t('ask_saved')}</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--butter-dd)', opacity: 0.9, lineHeight: 1.5 }}>{t('ask_read_body')}</div>
          <button className="big-btn" onClick={() => startRead(ask)}>{t('ask_read_yes')}</button>
          <button className="big-btn alt" onClick={() => setAsk(null)}>{t('ask_read_no')}</button>
        </div>
      )}
      {doneId && <ReadSummary t={t} uid={doneId} reports={reports} onOpen={onOpenReport} onClose={() => setDoneId(null)} />}
      <div className="sect"><span>{t('up_mine')}</span><small>{items ? items.length : ''}</small></div>
      {items && items.length === 0 && <div className="muted" style={{ fontSize: 13, fontWeight: 600 }}>{t('up_none')}</div>}
      {items && items.map((u) => (
        <div key={u.id} className="rep-row up-row" style={{ cursor: 'default' }}>
          <Thumb pid={pid} u={u} />
          <span style={{ minWidth: 0, flex: 1 }}><b>{u.title}</b><small>{t(CAT[u.category] || 'cat_other')} · {fmt(u.date)}</small>{statusLine(u, t)}</span>
          <div className="up-actions">
            {avail && u.ocr && ['off', 'failed', 'no_text'].includes(u.ocr.state) && <button className="filt on" onClick={() => startRead(u)}>🤖 {t('up_readbtn')}</button>}
            <a className="filt on" style={{ textDecoration: 'none' }} href={fileUrl(pid, u)} target="_blank" rel="noreferrer">{t('up_open')}</a>
            <button className="filt" onClick={() => remove(u)}>{t('up_remove')}</button>
          </div>
        </div>
      ))}
    </>
  )
}

/** Doctor view: what the patient has uploaded, marked not verified until a clinician confirms it. */
export function DoctorUploads({ pid, onChange }) {
  const [items, setItems] = useState(null)
  const [asking, setAsking] = useState(null)       // upload id waiting for the "I checked the original" confirmation
  const [busy, setBusy] = useState(null)
  const setVerified = (u, v) => {
    setBusy(u.id)
    verifyUpload(pid, u.id, v).then((m) => { setItems((x) => (x || []).map((i) => (i.id === m.id ? m : i))); setAsking(null); if (onChange) onChange([m]) })
      .catch(() => {}).finally(() => setBusy(null))
  }
  useEffect(() => { setItems(null); getUploads(pid).then((d) => setItems(d.items)).catch(() => setItems([])) }, [pid])
  useReadingPoll(pid, items, setItems, onChange)
  if (!items) return null
  return (
    <section className="card soft rec-sec" style={{ boxShadow: 'none' }}>
      <div className="card-h"><h2>Uploaded by the patient</h2>
        {items.length > 0 && items.every((u) => u.verified)
          ? <span className="chip" style={{ background: TONE.mint.bg, color: TONE.mint.dd }}>all verified</span>
          : <span className="chip" style={{ background: TONE.butter.bg, color: TONE.butter.dd }}>{items.filter((u) => u.verified).length ? `${items.filter((u) => u.verified).length} of ${items.length} verified` : 'not verified'}</span>}
        <span className="chip">{items.length}</span></div>
      {items.length === 0 ? <div className="muted" style={{ fontWeight: 600 }}>Nothing uploaded yet. Patients can add a PDF or a photo of a report from the Reports tab of their app.</div> : (
        <div style={{ display: 'grid', gap: 8 }}>
          {items.map((u) => (
            <div key={u.id} className="rep-row" style={{ cursor: 'default' }}>
              <Thumb pid={pid} u={u} size={56} />
              <span style={{ minWidth: 0, flex: 1 }}><b>{u.title}</b><small>{CAT_EN[u.category] || 'Other'} · report dated {fmt(u.date)} · uploaded {u.uploaded} · {u.size_kb} KB · {u.ext.toUpperCase()}</small>{statusLine(u, null)}
                {u.verified && <small style={{ color: 'var(--mint-dd)', fontWeight: 800 }}>✓ Verified by a clinician{u.verified_at ? ` on ${u.verified_at.slice(0, 10)}` : ''}</small>}
                {asking === u.id && <small style={{ color: 'var(--butter-dd)', fontWeight: 700 }}>Confirm that you checked this against the original document. The patient will see it as verified.</small>}</span>
              <span className="row" style={{ gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                {u.verified
                  ? <button className="btn sm" disabled={busy === u.id} onClick={() => setVerified(u, false)}>Undo</button>
                  : asking === u.id
                    ? <><button className="btn sm go" disabled={busy === u.id} onClick={() => setVerified(u, true)}>Yes, I checked it</button><button className="btn sm" onClick={() => setAsking(null)}>Cancel</button></>
                    : <button className="btn sm" style={{ background: TONE.mint.bg, color: TONE.mint.dd }} onClick={() => setAsking(u.id)}>✓ Mark as verified</button>}
                <a className="btn sm go" style={{ textDecoration: 'none' }} href={fileUrl(pid, u)} target="_blank" rel="noreferrer">Open</a>
              </span>
            </div>
          ))}
        </div>
      )}
      <div className="note">Files are checked by content and size only and are not virus scanned. Where the patient chose automatic reading, the text and any lab values found appear in the report list marked unverified until you mark the upload verified; nothing in the twin uses them either way. Check against the original, like any outside document.</div>
    </section>
  )
}
