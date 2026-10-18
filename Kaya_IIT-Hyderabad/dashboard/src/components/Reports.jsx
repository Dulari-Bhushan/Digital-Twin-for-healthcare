import { useEffect, useMemo, useState } from 'react'
import { getReports } from '../api'
import { DR, TONE } from '../ui'
import LineChart from './LineChart'

const TYPES = [['all', 'All'], ['lab', 'Blood and urine'], ['imaging', 'Scans'], ['cardiac', 'Heart'], ['clinic', 'Clinic'], ['device', 'Wearable']]
const ICON = { lab: '🧪', imaging: '🩻', cardiac: '🫀', clinic: '📋', device: '⌚' }
const TREND_KEYS = [['hba1c', 'HbA1c (%)', '#0F6E68'], ['egfr', 'eGFR', '#4f8196'], ['uacr', 'Urine albumin (mg/g)', '#d9894a'], ['alt', 'ALT (U/L)', '#E9A23B'], ['ldl', 'LDL (mg/dL)', '#4d8f6b'], ['sbp', 'Systolic BP', '#c4645b'], ['weight', 'Weight (kg)', '#0B4F4B']]

export const fmtDate = (iso, long = true) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-IN', long ? { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' } : { day: 'numeric', month: 'short', timeZone: 'UTC' })
const num = (v, dec) => (typeof v === 'number' ? v.toLocaleString('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec }) : v)
const tone = (t) => TONE[t] || TONE.mint

/* ---------------------------------------------------------------- what changed since the last visit */
function valText(it, v) {
  if (it.key === 'dr') return DR[v]
  return `${num(v, it.dec)}${it.unit ? ` ${it.unit}` : ''}`
}
function deltaText(it) {
  if (it.key === 'dr') return it.direction === 'same' ? 'no change' : it.delta > 0 ? 'one grade worse' : 'one grade better'
  if (it.direction === 'same') return 'about the same'
  const d = `${it.delta > 0 ? '+' : '-'}${num(Math.abs(it.delta), it.dec)}${it.unit && it.unit !== '%' ? ` ${it.unit}` : it.unit}`
  return it.key === 'uacr' || it.key === 'alt' ? `${d} (${it.delta_pct > 0 ? '+' : ''}${it.delta_pct}%)` : d
}
const DIR = { worse: ['rose', '▲ worse'], better: ['mint', '▼ better'], same: ['sky', '● same'] }
function dirMark(it) {
  // arrows show the direction of the number; colour shows whether that is good
  const up = it.delta > 0
  if (it.direction === 'same') return ['sky', '●']
  return [it.direction === 'worse' ? 'rose' : 'mint', up ? '▲' : '▼']
}

export function ChangesCard({ ch, audience = 'doctor', onOpen }) {
  if (!ch) return null
  const visit = ch.items.filter((i) => i.scope === 'visit')
  const week = ch.items.filter((i) => i.scope === 'week')
  const moved = visit.filter((i) => i.direction !== 'same').sort((a, b) => b.severity - a.severity)
  const same = visit.filter((i) => i.direction === 'same')
  const doc = audience === 'doctor'
  const tile = (it) => {
    const [tn, ar] = dirMark(it)
    return (
      <div key={it.key} className="chg-tile" style={{ background: TONE[tn].bg, color: TONE[tn].dd }}>
        <div className="l">{doc ? it.label : it.plain_label}</div>
        <div className="v"><span>{valText(it, it.before)}</span> <span style={{ opacity: 0.6 }}>→</span> <b>{valText(it, it.after)}</b></div>
        <div className="d">{ar} {deltaText(it)}</div>
      </div>
    )
  }
  return (
    <section className={doc ? 'card soft chg' : 'chg-p'} style={doc ? undefined : { background: 'var(--lav)', borderRadius: 28, padding: 16 }}>
      <div className="chg-h">
        <div>
          <h2 style={doc ? undefined : { fontSize: 18 }}>{doc ? 'What changed since the last visit' : 'Since your last visit'}</h2>
          <div className="muted" style={{ fontSize: 12, fontWeight: 600 }}>Last visit {fmtDate(ch.last_visit)} · {ch.months_ago} months ago</div>
        </div>
        <div className="row" style={{ gap: 6 }}>
          {['worse', 'better', 'same'].map((k) => <span key={k} className={`chip ${DIR[k][0]}`}>{ch.counts[k]} {k === 'same' ? 'unchanged' : k}</span>)}
          {doc && onOpen && <button className="btn sm" onClick={() => onOpen('reports')}>All reports ›</button>}
        </div>
      </div>
      {doc && ch.attention.length > 0 && (
        <div className="chg-attn">
          {ch.attention.map((a, i) => <div key={i} style={{ background: TONE[a.tone].bg, color: TONE[a.tone].dd }}><b>!</b> {a.text}</div>)}
        </div>
      )}
      {!doc && ch.counts.worse > 0 && <p className="note" style={{ margin: '4px 0 8px', fontSize: 13 }}>Some results moved the wrong way. That is useful to know, not a reason to panic. Your doctor will go through them with you.</p>}
      {moved.length > 0 && <div className="chg-grid">{moved.map(tile)}</div>}
      {same.length > 0 && <div className="chg-same">Unchanged: {same.map((i) => (doc ? i.label : i.plain_label)).join(', ')}.</div>}
      {ch.new_medicines.length > 0 && <div className="chg-same">New medicine since then: <b>{ch.new_medicines.join('; ')}</b></div>}
      {week.length > 0 && (
        <>
          <div className="chg-sub">{doc ? 'Wearable data: last 7 days against the 7 days before' : 'Your last 7 days compared with the week before'}</div>
          <div className="chg-grid">{week.map(tile)}</div>
        </>
      )}
    </section>
  )
}

/* ---------------------------------------------------------------- trends across lab reports */
export function Trends({ data, keys = TREND_KEYS, height = 190 }) {
  const [k, setK] = useState(keys[0][0])
  const sel = keys.find((x) => x[0] === k) || keys[0]
  const y = data[sel[0]]
  const lo = Math.min(...y), hi = Math.max(...y)
  const pad = (hi - lo) * 0.25 || hi * 0.1 || 1
  return (
    <div>
      <div className="row wrap" style={{ gap: 6, marginBottom: 8 }}>
        {keys.map(([key, label]) => <button key={key} className={`filt ${key === sel[0] ? 'on' : ''}`} onClick={() => setK(key)}>{label}</button>)}
      </div>
      <LineChart height={height} yDomain={[Math.max(0, lo - pad), hi + pad]} yFmt={(v) => (hi < 20 ? v.toFixed(1) : Math.round(v))} xTickEvery={1} xLabel={(i) => new Date(`${data.dates[i]}T00:00:00Z`).toLocaleDateString('en-IN', { month: 'short', year: '2-digit', timeZone: 'UTC' })}
        series={[{ name: sel[1], y, color: sel[2] }]} />
    </div>
  )
}

/* ---------------------------------------------------------------- one report, laid out like the paper copy */
function Prev({ r }) {
  if (!r.prev || typeof r.value !== 'number') return <span className="muted">-</span>
  const dlt = r.value - r.prev.value
  const same = Math.abs(dlt) < 1e-9
  return <span className="muted" style={{ fontSize: 12 }}>{same ? '=' : dlt > 0 ? '▲' : '▼'} was {r.prev.value} ({fmtDate(r.prev.date, false)})</span>
}

export function ReportDoc({ rep, pid, audience, profile }) {
  const [cam, setCam] = useState(false)
  useEffect(() => setCam(false), [rep.id])
  const doc = audience === 'doctor'
  return (
    <article className="rep-doc">
      <header className="rep-doc-h">
        <div style={{ minWidth: 0 }}>
          <div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>{rep.facility}</div>
          <h2 style={{ fontSize: doc ? 22 : 19, letterSpacing: '-.01em', margin: '2px 0' }}>{ICON[rep.type]} {rep.name}</h2>
          <div className="muted" style={{ fontSize: 12.5, fontWeight: 600 }}>{fmtDate(rep.date)} · {rep.clinician}</div>
        </div>
        <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
          <span className={`chip ${rep.new ? 'butter' : 'mint'}`}>{rep.new && rep.status !== 'Latest' ? 'New · ' : ''}{rep.status}</span>
          <a className="btn sm" style={{ textDecoration: 'none' }} href={`/api/patients/${pid}/reports/${rep.id}.pdf`} target="_blank" rel="noreferrer">📄 PDF</a>
        </div>
      </header>
      {!doc && <div className="rep-simple"><b>In simple words</b><p>{rep.plain}</p></div>}
      {profile && doc && <div className="muted" style={{ fontSize: 12, fontWeight: 600, margin: '2px 0 10px' }}>{profile.name} · ID {profile.id} · {profile.age} y · {profile.sex === 'F' ? 'female' : 'male'}</div>}
      {rep.meds && rep.meds.length > 0 && (
        <div className="rep-sec"><h3>Medicines in force at this visit</h3>
          {rep.meds.map((m) => <div key={m.name} className="rep-med"><b>{m.name}</b> <span>{m.dose}</span><small>{m.purpose}</small></div>)}
        </div>
      )}
      {rep.sections.map((s) => (
        <div key={s.title} className="rep-sec">
          <h3>{s.title}</h3>
          {doc ? (
            <div style={{ overflowX: 'auto' }}>
              <table className="rt">
                <thead><tr><th>Test</th><th>Result</th><th>Reference</th><th>Flag</th><th>Previous</th></tr></thead>
                <tbody>{s.rows.map((r) => (
                  <tr key={r.test}><td><b>{r.test}</b></td><td><b>{r.value}</b> {r.unit}</td><td className="muted">{r.ref}</td>
                    <td>{r.flag && <span className="chip" style={{ background: tone(r.tone).bg, color: tone(r.tone).dd }}>{r.flag}</span>}</td><td><Prev r={r} /></td></tr>
                ))}</tbody>
              </table>
            </div>
          ) : s.rows.map((r) => (
            <div key={r.test} className="rep-prow">
              <div style={{ minWidth: 0 }}><b>{r.test}</b>{r.ref && <div className="muted" style={{ fontSize: 11.5 }}>Healthy: {r.ref}</div>}</div>
              <div style={{ textAlign: 'right' }}>
                <b style={{ fontSize: 16 }}>{r.value} <small className="muted">{r.unit}</small></b>
                <div>{r.flag && <span className="chip" style={{ background: tone(r.tone).bg, color: tone(r.tone).dd, fontSize: 11, padding: '3px 9px' }}>{r.flag}</span>}</div>
              </div>
            </div>
          ))}
        </div>
      ))}
      {rep.image && (
        <div className="rep-sec">
          <h3>Image</h3>
          <div className="row" style={{ gap: 6, marginBottom: 8 }}>
            <button className={`filt ${!cam ? 'on' : ''}`} onClick={() => setCam(false)}>Photograph</button>
            <button className={`filt ${cam ? 'on' : ''}`} onClick={() => setCam(true)}>Where the model looked</button>
          </div>
          <img className="rimg" style={{ maxWidth: 360 }} src={cam ? rep.image_cam : rep.image} alt={cam ? 'Grad-CAM heatmap' : `Fundus photograph, grade ${rep.grade}`} />
          <div className="note">A representative IDRiD image (CC BY 4.0) of this grade is shown because the patient is synthetic.</div>
        </div>
      )}
      {doc && rep.findings.length > 0 && <div className="rep-sec"><h3>Findings</h3><ul>{rep.findings.map((f, i) => <li key={i}>{f}</li>)}</ul></div>}
      <div className="rep-sec"><h3>Impression</h3><p style={{ margin: 0, fontWeight: 700 }}>{rep.impression}</p></div>
      {rep.recommendations.length > 0 && <div className="rep-sec"><h3>{doc ? 'Recommendations' : 'What happens next'}</h3><ul>{rep.recommendations.map((f, i) => <li key={i}>{f}</li>)}</ul></div>}
      <div className="note">Synthetic report for a demonstration. It describes an invented person and has no clinical meaning.</div>
    </article>
  )
}

/* ---------------------------------------------------------------- the list */
function Row({ r, on, onPick }) {
  return (
    <button className={`rep-row ${on ? 'on' : ''}`} onClick={() => onPick(r.id)}>
      <span className="ic">{ICON[r.type]}</span>
      <span style={{ minWidth: 0, flex: 1 }}>
        <b>{r.name}</b>
        <small>{fmtDate(r.date)} · {r.facility.split(',')[0].replace(' (synthetic)', '')}</small>
      </span>
      {r.new && <span className="dot" title="New" />}
    </button>
  )
}

/** ?report=EYE (or LAB, LIV, VIS, FOOT, ECG, CXR, CGM) opens that kind of report first; handy for demos. */
function pickByUrl(data) {
  const q = new URLSearchParams(window.location.search).get('report')
  return q ? data.reports.find((r) => r.code === q.toUpperCase())?.id || null : null
}

function useReports(pid) {
  const [data, setData] = useState(null)
  useEffect(() => { setData(null); getReports(pid).then(setData) }, [pid])
  return data
}

/** Doctor view: list and report side by side, with trends above. */
export function ReportsTab({ pid, d }) {
  const data = useReports(pid)
  const [type, setType] = useState('all')
  const [sel, setSel] = useState(null)
  const list = useMemo(() => (data ? data.reports.filter((r) => type === 'all' || r.type === type) : []), [data, type])
  useEffect(() => { if (data && !sel) setSel(pickByUrl(data) || data.reports[0].id) }, [data, sel])
  if (!data) return <div className="muted" style={{ padding: 30 }}>Loading the reports…</div>
  const cur = data.reports.find((r) => r.id === sel) || list[0]
  const counts = (t) => (t === 'all' ? data.reports.length : data.reports.filter((r) => r.type === t).length)
  return (
    <>
      <section className="card soft rec-sec" style={{ boxShadow: 'none' }}>
        <div className="card-h"><h2>Trends across lab reports</h2><span className="chip">{data.trends.dates.length} panels · {fmtDate(data.trends.dates[0], false)} to {fmtDate(data.trends.dates.at(-1), false)}</span></div>
        <Trends data={data.trends} />
      </section>
      <div className="rep-grid">
        <section className="card soft rep-list" style={{ boxShadow: 'none' }}>
          <div className="card-h" style={{ marginBottom: 8 }}><h2>All reports</h2><span className="chip">{list.length}</span></div>
          <div className="row wrap" style={{ gap: 6, marginBottom: 10 }}>
            {TYPES.filter(([k]) => counts(k) > 0).map(([k, label]) => <button key={k} className={`filt ${type === k ? 'on' : ''}`} onClick={() => setType(k)}>{label} {counts(k)}</button>)}
          </div>
          <div className="rep-scroll">{list.map((r) => <Row key={r.id} r={r} on={cur && cur.id === r.id} onPick={setSel} />)}</div>
        </section>
        <section className="card soft rep-view" style={{ boxShadow: 'none' }}>{cur && <ReportDoc rep={cur} pid={pid} audience="doctor" profile={d.profile} />}</section>
      </div>
      <section className="card soft rec-sec" style={{ boxShadow: 'none' }}>
        <div className="card-h"><h2>Current medicines</h2><span className="chip">{data.medications.length}</span></div>
        <table className="rt"><thead><tr><th>Medicine</th><th>Dose</th><th>Since</th><th>Why</th></tr></thead>
          <tbody>{data.medications.map((m) => <tr key={m.name}><td><b>{m.name}</b></td><td>{m.dose}</td><td>{/^\d{4}/.test(m.since) ? fmtDate(m.since) : m.since}</td><td className="muted">{m.purpose}</td></tr>)}</tbody></table>
      </section>
    </>
  )
}

/** Patient app: plain-language list, tap a report to read it. */
export function PatientReports({ t, pid, changes }) {
  const data = useReports(pid)
  const [type, setType] = useState('all')
  const [open, setOpen] = useState(null)
  useEffect(() => setOpen(null), [pid])
  useEffect(() => { if (data && !open) setOpen(pickByUrl(data)) }, [data])
  if (!data) return <div className="muted" style={{ padding: 30 }}>{t('loading')}</div>
  if (open) {
    const rep = data.reports.find((r) => r.id === open)
    return (
      <>
        <button className="filt on" style={{ margin: '8px 0 6px' }} onClick={() => setOpen(null)}>‹ {t('rep_back')}</button>
        <ReportDoc rep={rep} pid={pid} audience="patient" />
      </>
    )
  }
  const types = [['all', t('rep_all')], ['lab', '🧪'], ['imaging', '🩻'], ['clinic', '📋'], ['cardiac', '🫀']]
  const list = data.reports.filter((r) => type === 'all' || r.type === type)
  return (
    <>
      <div className="p-h">{t('rep_title1')}<br /><span style={{ color: 'var(--muted)', fontWeight: 600 }}>{t('rep_title2')}</span></div>
      <div style={{ marginTop: 12 }}><ChangesCard ch={changes} audience="patient" /></div>
      <div className="sect"><span>{t('rep_trends')}</span></div>
      <div className="p-card" style={{ background: '#f0f5f4', marginTop: 4 }}>
        <Trends data={data.trends} keys={TREND_KEYS.filter(([k]) => ['hba1c', 'egfr', 'sbp'].includes(k))} height={150} />
      </div>
      <div className="sect"><span>{t('rep_meds')}</span><small>{data.medications.length}</small></div>
      {data.medications.map((m) => <div key={m.name} className="rep-med p"><b>{m.name}</b> <span>{m.dose}</span><small>{m.purpose}</small></div>)}
      <div className="sect"><span>{t('rep_all_title')}</span><small>{list.length}</small></div>
      <div className="row wrap" style={{ gap: 6, marginBottom: 8 }}>
        {types.map(([k, label]) => <button key={k} className={`filt ${type === k ? 'on' : ''}`} onClick={() => setType(k)}>{label}</button>)}
      </div>
      {list.map((r) => <Row key={r.id} r={r} on={false} onPick={setOpen} />)}
      <p className="note" style={{ marginTop: 14 }}>{t('rep_note')}</p>
    </>
  )
}
