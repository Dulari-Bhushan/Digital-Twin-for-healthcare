import { useState } from 'react'
import { TONE, tierTone } from '../ui'

const STORE_KEY = 'kaya.triage.v1'
const readStore = () => { try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {} } catch { return {} } }
const writeStore = (v) => { try { localStorage.setItem(STORE_KEY, JSON.stringify(v)) } catch { /* private window: parking just won't persist */ } }

const guard = (fn) => (e) => { if (e.target.closest('button, a, input, select, label')) return; fn() }

const FILTERS = [
  ['glucose', 'Glucose', (t) => ['hypo', 'tbr', 'tir'].includes(t.key)],
  ['liver', 'Liver', (t) => t.key === 'fib'],
  ['kidney', 'Kidney', (t) => t.key === 'egfr'],
  ['new', 'New since last visit', (t) => t.event],
  ['msg', 'Messages', (t) => t.key === 'msg'],
]
const SNOOZES = [['1 day', 1], ['3 days', 3], ['1 week', 7]]
const PAGE = 20

const eventKeys = (p) => p.triage.triggers.filter((t) => t.event).map((t) => t.key)
const topReasons = (p) => [...p.triage.triggers].sort((a, b) => (a.level === 'critical' ? 0 : 1) - (b.level === 'critical' ? 0 : 1) || (a.hours_ago ?? 1e9) - (b.hours_ago ?? 1e9))
/** Critical events first, newest first (a fresh hypo outranks a long-standing risk), then the rest by overall risk. */
const byUrgency = (a, b) => {
  const ha = a.triage.event_hours, hb = b.triage.event_hours
  if (ha != null || hb != null) return (ha ?? 1e9) - (hb ?? 1e9)
  return b.score - a.score
}
const agoText = (h) => (h < 24 ? `${h} h ago` : `${Math.round(h / 24)} d ago`)

function Spark({ pts, color }) {
  const lo = Math.min(...pts), hi = Math.max(...pts, lo + 0.04)
  const d = pts.map((v, i) => `${(i / (pts.length - 1)) * 34 + 1},${16 - ((v - lo) / (hi - lo)) * 14}`).join(' ')
  return <svg className="spark" width="36" height="18" viewBox="0 0 36 18" aria-hidden="true"><polyline points={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
}

function Row({ p, selected, onSelect, actions }) {
  const t = TONE[tierTone(p.tier)]
  const [first, ...rest] = topReasons(p)
  const title = first
    ? `${p.triage.triggers.map((x) => x.text).join('\n')}\n\nOverall risk ${Math.round(p.score * 100)}%`
    : `No flags. Overall risk ${Math.round(p.score * 100)}%, last reviewed ${p.triage.days_since_review} days ago. Moves up if something changes or it is not reviewed for 30 days.`
  return (
    <div className={`pt2 ${selected ? 'on' : ''}`} role="button" tabIndex={0} title={title}
      onClick={guard(() => onSelect(p.id))} onKeyDown={(e) => { if (e.key === 'Enter' && e.target === e.currentTarget) onSelect(p.id) }}>
      <span className="dot" style={{ background: t.d }} />
      <span className="nm"><b>{p.name}</b><small>{p.age}{p.sex} · HbA1c {p.hba1c}</small></span>
      <Spark pts={p.triage.trend} color={t.d} />
      <span className="rs">
        {first
          ? <span className={`rchip ${first.level === 'critical' ? 'crit' : ''}`}>{first.text}{first.event && first.hours_ago != null ? ` · ${agoText(first.hours_ago)}` : ''}</span>
          : <span className="rchip ok">Stable, no flags</span>}
        {rest.length > 0 && <span className="more">+{rest.length}</span>}
      </span>
      {actions && <span className="acts">{actions}</span>}
    </div>
  )
}

export function Sidebar({ patients, selected, onSelect }) {
  const [store, setStore] = useState(readStore)
  const [open, setOpen] = useState({ today: true, week: false, stable: false, parked: false })
  const [q, setQ] = useState('')
  const [flt, setFlt] = useState(null)
  const [limit, setLimit] = useState({})
  const now = Date.now()
  const save = (next) => { setStore(next); writeStore(next) }
  const park = (p, days) => save({ ...store, [p.id]: { until: days ? now + days * 864e5 : null, keys: eventKeys(p) } })
  const unpark = (id) => { const n = { ...store }; delete n[id]; save(n) }
  // a parked patient returns when the snooze ends, or when a change appears that they were not parked with
  const isParked = (p) => {
    const s = store[p.id]
    if (!s || (s.until && now > s.until)) return false
    return eventKeys(p).every((k) => s.keys.includes(k))
  }

  const text = q.trim().toLowerCase()
  const fdef = FILTERS.find((f) => f[0] === flt)
  const matches = (p) => (!text || p.name.toLowerCase().includes(text) || String(p.id).includes(text)) && (!fdef || p.triage.triggers.some(fdef[2]))
  const live = patients.filter((p) => !isParked(p))
  const buckets = { today: [], week: [], stable: [] }
  live.forEach((p) => buckets[p.triage.bucket].push(p))
  buckets.today.sort(byUrgency)
  buckets.week.sort((a, b) => b.score - a.score)
  buckets.stable.sort((a, b) => b.score - a.score)
  const parked = patients.filter(isParked)
  const filtering = Boolean(text || fdef)

  const nNew = live.filter((p) => p.triage.event_hours != null).length
  const nMsg = live.filter((p) => p.triage.unread_msgs).length
  const nOver = live.filter((p) => p.triage.triggers.some((t) => t.key === 'overdue' || t.key === 'stale')).length

  const section = (key, label, hint, list, mkActions) => {
    const shown = list.filter(matches)
    const isOpen = open[key] || (filtering && shown.length > 0)
    const cap = limit[key] || PAGE
    return (
      <section className={`bk ${key}`} key={key}>
        <button className="bk-h" onClick={() => setOpen({ ...open, [key]: !open[key] })} aria-expanded={isOpen}>
          <span className="caret">{isOpen ? '▾' : '▸'}</span>
          <b>{label}</b>
          <span className="cnt">{filtering ? `${shown.length} of ${list.length}` : list.length}</span>
          <small>{hint}</small>
        </button>
        {isOpen && (
          <div className="bk-b">
            {shown.length === 0 && <div className="muted" style={{ fontSize: 12, padding: '4px 8px' }}>{filtering ? 'No match here.' : 'Nobody here right now.'}</div>}
            {shown.slice(0, cap).map((p) => <Row key={p.id} p={p} selected={selected === p.id} onSelect={onSelect} actions={mkActions(p)} />)}
            {shown.length > cap && <button className="btn sm showmore" onClick={() => setLimit({ ...limit, [key]: cap + PAGE })}>Show {Math.min(PAGE, shown.length - cap)} more ({shown.length - cap} hidden)</button>}
          </div>
        )}
      </section>
    )
  }
  const doneActions = (p) => (
    <>
      <button className="mini" title="Mark as reviewed. Comes back if something new happens." onClick={() => park(p, 0)}>✓ Reviewed</button>
      <select className="mini" aria-label={`Snooze ${p.name}`} value="" onChange={(e) => e.target.value && park(p, Number(e.target.value))}>
        <option value="">💤 Snooze</option>
        {SNOOZES.map(([l, d]) => <option key={d} value={d}>{l}</option>)}
      </select>
    </>
  )

  return (
    <aside className="side">
      <h2>Today's priorities</h2>
      <div className="strip" aria-label="Panel summary">
        <span><b>{buckets.today.length}</b>act today</span>
        <span><b>{nNew}</b>new changes</span>
        <span><b>{nMsg}</b>unread</span>
        <span><b>{nOver}</b>overdue</span>
      </div>
      <div className="muted" style={{ fontSize: 12, padding: '0 6px' }}>
        {patients.length} patients · {buckets.week.length} to review this week · {buckets.stable.length} stable{parked.length ? ` · ${parked.length} parked` : ''}
      </div>
      <input className="srch" type="search" placeholder="Search name or ID" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search patients" />
      <div className="fchips">
        {FILTERS.map(([k, l]) => <button key={k} className={`fchip ${flt === k ? 'on' : ''}`} aria-pressed={flt === k} onClick={() => setFlt(flt === k ? null : k)}>{l}</button>)}
      </div>
      {section('today', 'Act today', 'critical or new', buckets.today, doneActions)}
      {section('week', 'Review this week', 'flagged, not urgent', buckets.week, doneActions)}
      {section('stable', 'Stable', 'no flags', buckets.stable, doneActions)}
      {parked.length > 0 && section('parked', 'Reviewed / snoozed', 'returns on new change', parked, (p) => (
        <button className="mini" onClick={() => unpark(p.id)}>{store[p.id].until ? `Snoozed until ${new Date(store[p.id].until).toLocaleDateString()} · Undo` : 'Reviewed · Undo'}</button>
      ))}
    </aside>
  )
}
