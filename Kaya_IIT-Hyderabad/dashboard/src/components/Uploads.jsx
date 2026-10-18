import { useEffect, useRef, useState } from 'react'
import { deleteUpload, getUploads, uploadReport } from '../api'
import { TONE } from '../ui'

const CAT = { 'blood test': 'cat_blood', 'scan or x-ray': 'cat_scan', prescription: 'cat_rx', 'discharge summary': 'cat_discharge', 'eye report': 'cat_eye', other: 'cat_other' }
const CAT_EN = { 'blood test': 'Blood test', 'scan or x-ray': 'Scan or X-ray', prescription: 'Prescription', 'discharge summary': 'Discharge summary', 'eye report': 'Eye report', other: 'Other' }
const MAX = 8 * 1024 * 1024
const OK = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp']
const fmt = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
const fileUrl = (pid, u) => `/api/patients/${pid}/uploads/${u.id}/file`

function Thumb({ pid, u, size = 52 }) {
  const box = { width: size, height: size, borderRadius: 12, flex: 'none', display: 'grid', placeItems: 'center', background: '#fff', overflow: 'hidden', fontSize: size / 2 }
  return u.media.startsWith('image/') ? <img src={fileUrl(pid, u)} alt="" style={{ ...box, objectFit: 'cover' }} /> : <div style={box}>📄</div>
}

/** Patient app: choose a PDF or photo, name it, upload it, and manage what was uploaded. */
export function PatientUploads({ t, pid, today }) {
  const [items, setItems] = useState(null)
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('blood test')
  const [date, setDate] = useState(today)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const input = useRef(null)
  useEffect(() => { setItems(null); getUploads(pid).then((d) => setItems(d.items)).catch(() => setItems([])) }, [pid])
  useEffect(() => setDate(today), [today])

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
    uploadReport(pid, file, { title, category, date })
      .then((m) => { setItems((x) => [m, ...(x || [])]); reset() })
      .catch((e) => setErr(e.message))
      .finally(() => setBusy(false))
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
      <div className="sect"><span>{t('up_mine')}</span><small>{items ? items.length : ''}</small></div>
      {items && items.length === 0 && <div className="muted" style={{ fontSize: 13, fontWeight: 600 }}>{t('up_none')}</div>}
      {items && items.map((u) => (
        <div key={u.id} className="rep-row" style={{ cursor: 'default' }}>
          <Thumb pid={pid} u={u} />
          <span style={{ minWidth: 0, flex: 1 }}><b>{u.title}</b><small>{t(CAT[u.category] || 'cat_other')} · {fmt(u.date)}</small></span>
          <a className="filt on" style={{ textDecoration: 'none' }} href={fileUrl(pid, u)} target="_blank" rel="noreferrer">{t('up_open')}</a>
          <button className="filt" onClick={() => remove(u)}>{t('up_remove')}</button>
        </div>
      ))}
    </>
  )
}

/** Doctor view: what the patient has uploaded, clearly marked as not verified. */
export function DoctorUploads({ pid }) {
  const [items, setItems] = useState(null)
  useEffect(() => { setItems(null); getUploads(pid).then((d) => setItems(d.items)).catch(() => setItems([])) }, [pid])
  if (!items) return null
  return (
    <section className="card soft rec-sec" style={{ boxShadow: 'none' }}>
      <div className="card-h"><h2>Uploaded by the patient</h2><span className="chip" style={{ background: TONE.butter.bg, color: TONE.butter.dd }}>not verified</span><span className="chip">{items.length}</span></div>
      {items.length === 0 ? <div className="muted" style={{ fontWeight: 600 }}>Nothing uploaded yet. Patients can add a PDF or a photo of a report from the Reports tab of their app.</div> : (
        <div style={{ display: 'grid', gap: 8 }}>
          {items.map((u) => (
            <div key={u.id} className="rep-row" style={{ cursor: 'default' }}>
              <Thumb pid={pid} u={u} size={56} />
              <span style={{ minWidth: 0, flex: 1 }}><b>{u.title}</b><small>{CAT_EN[u.category] || 'Other'} · report dated {fmt(u.date)} · uploaded {u.uploaded} · {u.size_kb} KB · {u.ext.toUpperCase()}</small></span>
              <a className="btn sm go" style={{ textDecoration: 'none' }} href={fileUrl(pid, u)} target="_blank" rel="noreferrer">Open</a>
            </div>
          ))}
        </div>
      )}
      <div className="note">Files are checked by content and size only. They are not read, interpreted or virus scanned, and nothing in the twin uses them. Review them like any outside document.</div>
    </section>
  )
}
