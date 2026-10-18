import { useCallback, useEffect, useState } from 'react'
import { TONE } from '../ui'

const hdr = (token) => (token ? { 'x-admin-token': token } : {})
const j = async (r) => {
  if (r.status === 401) throw new Error('401')
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}
const getOverview = (token) => fetch('/api/admin/overview', { headers: hdr(token) }).then(j)
const runSelftest = (token) => fetch('/api/admin/selftest', { method: 'POST', headers: hdr(token) }).then(j)

const up = (s) => (s >= 3600 ? `${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} min` : s >= 60 ? `${Math.floor(s / 60)} min ${s % 60} s` : `${s} s`)
const Pill = ({ tone, children }) => <span className="chip" style={{ background: TONE[tone].bg, color: TONE[tone].dd }}>{children}</span>
const statusTone = (s) => (['loaded', 'configured', 'enabled', 'precomputed', 'in process', 'ok'].includes(s) ? 'mint' : s === 'not configured' ? 'butter' : 'rose')
const Kpi = ({ label, value, sub, tone = 'lav' }) => <div className="kpi2" style={{ background: TONE[tone].bg, color: TONE[tone].dd }}><div className="l">{label}</div><div className="v">{value}</div>{sub && <div className="s">{sub}</div>}</div>
const Sec = ({ title, hint, children }) => <section className="card soft rec-sec" style={{ boxShadow: 'none' }}><div className="card-h"><h2>{title}</h2>{hint && <span className="chip">{hint}</span>}</div>{children}</section>

export default function Admin() {
  const [token, setToken] = useState(() => { try { return window.sessionStorage.getItem('kaya-admin') || '' } catch (e) { return '' } })
  const [draft, setDraft] = useState('')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [test, setTest] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => getOverview(token).then((d) => { setData(d); setErr(null) }).catch((e) => setErr(e.message)), [token])
  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [load])

  const signIn = () => { try { window.sessionStorage.setItem('kaya-admin', draft) } catch (e) { /* ignore */ } setToken(draft) }
  const doTest = () => { setBusy(true); runSelftest(token).then(setTest).catch((e) => setTest({ ok: false, checks: [{ name: 'Self-test', ok: false, ms: 0, detail: e.message }] })).finally(() => { setBusy(false); load() }) }

  useEffect(() => { if (new URLSearchParams(window.location.search).get('selftest') === '1') doTest() }, []) // eslint-disable-line

  if (err === '401') {
    return (
      <div className="admin"><Sec title="Administrator sign-in" hint="token required">
        <p className="muted" style={{ marginBottom: 12 }}>This server was started with an admin token. Enter it to open the operations view.</p>
        <div className="row" style={{ gap: 8 }}>
          <input type="password" value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && signIn()} placeholder="Admin token" className="adm-in" />
          <button className="btn go" onClick={signIn}>Open</button>
        </div>
      </Sec></div>
    )
  }
  if (!data) return <div className="admin muted" style={{ padding: 30 }}>{err ? `Could not load the operations data: ${err}` : 'Loading…'}</div>

  const s = data.service, dt = data.data, tr = data.traffic
  const errRate = tr.total ? (100 * tr.errors) / tr.total : 0
  const worst = Math.max(0, ...tr.routes.map((r) => r.p95_ms))
  const failing = data.hardening.filter((h) => !h.ok).length
  return (
    <div className="admin">
      <div className="card lav adm-head">
        <div>
          <h1 style={{ fontSize: 26, letterSpacing: '-.02em' }}>Operations</h1>
          <div className="muted" style={{ fontWeight: 600, fontSize: 13 }}>Service health, models, data, traffic and audit trail for the person running Kaya. No patient data or secrets appear on this page.</div>
        </div>
        <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
          <Pill tone={data.auth === 'token' ? 'mint' : 'butter'}>{data.auth === 'token' ? 'Token protected' : 'Demo mode: no sign-in'}</Pill>
          <button className="btn go" onClick={doTest} disabled={busy}>{busy ? 'Running…' : '▶ Run self-test'}</button>
        </div>
      </div>

      <div className="rec-kpis">
        <Kpi label="Service" value={s.status === 'ok' ? 'Healthy' : 'Down'} sub={`up ${up(s.uptime_s)}`} tone={s.status === 'ok' ? 'mint' : 'rose'} />
        <Kpi label="Requests served" value={tr.total.toLocaleString()} sub={`${errRate.toFixed(1)}% server errors`} tone={errRate > 1 ? 'rose' : 'mint'} />
        <Kpi label="Slowest route (p95)" value={`${worst.toFixed(0)} ms`} sub="since the server started" tone={worst > 500 ? 'butter' : 'mint'} />
        <Kpi label="Patients loaded" value={dt.patients} sub={dt.synthetic ? 'synthetic data' : 'real data'} tone="lav" />
        <Kpi label="Assistant safety stops" value={(data.assistant.emergency || 0) + (data.assistant.medicine || 0)} sub="emergency or medicine questions handled in code" tone="sky" />
        <Kpi label="Hardening to do" value={failing} sub="before real patient data" tone={failing ? 'butter' : 'mint'} />
      </div>

      {test && (
        <Sec title="Self-test" hint={test.ok ? 'all required checks passed' : 'something failed'}>
          <table className="rt"><thead><tr><th>Check</th><th>Result</th><th>Time</th><th>Detail</th></tr></thead>
            <tbody>{test.checks.map((c) => <tr key={c.name}><td><b>{c.name}</b></td><td><Pill tone={c.ok ? 'mint' : c.warn ? 'butter' : 'rose'}>{c.ok ? 'pass' : c.warn ? 'warning' : 'fail'}</Pill></td><td>{c.ms} ms</td><td className="muted">{c.detail}</td></tr>)}</tbody></table>
        </Sec>
      )}

      <div className="rec-grid2">
        <Sec title="Integrations">
          <div style={{ overflowX: 'auto' }}><table className="rt"><tbody>{data.integrations.map((i) => <tr key={i.name}><td><b>{i.name}</b></td><td><Pill tone={statusTone(i.status)}>{i.status}</Pill></td><td className="muted">{i.detail}</td></tr>)}</tbody></table></div>
        </Sec>
        <Sec title="Service and data">
          <div className="kvgrid">
            {[['API version', s.api_version], ['Started', s.started], ['Python', s.python], ['Platform', s.platform], ['Artifacts', `${dt.artifact_files} files, ${dt.artifact_mb} MB`], ['Last built', dt.built], ['Retina images', dt.eye_images],
              ['Dashboard build', dt.dashboard_build ? 'present' : 'missing'], ['Diary files', dt.diary_files], ['Patient uploads', dt.uploaded_files]].map(([k, v]) => <div key={k}><span className="muted">{k}</span><b>{String(v)}</b></div>)}
          </div>
        </Sec>
      </div>

      <Sec title="Models" hint="what is running and how it was validated">
        <div style={{ overflowX: 'auto' }}>
          <table className="rt"><thead><tr><th>Model</th><th>Serves</th><th>Status</th><th>Validation</th></tr></thead>
            <tbody>{data.models.map((m) => <tr key={m.name}><td><b>{m.name}</b><div className="muted" style={{ fontSize: 12 }}>{m.what}</div></td><td>{m.serves}</td><td><Pill tone={statusTone(m.status)}>{m.status}</Pill>{m.size_kb > 0 && <div className="muted" style={{ fontSize: 12 }}>{m.size_kb} KB</div>}</td><td className="muted">{m.validation}</td></tr>)}</tbody></table>
        </div>
      </Sec>

      <div className="rec-grid2">
        <Sec title="Traffic" hint="busiest routes">
          <div style={{ overflowX: 'auto' }}>
            <table className="rt"><thead><tr><th>Route</th><th>Calls</th><th>p50</th><th>p95</th><th>Errors</th></tr></thead>
              <tbody>{tr.routes.length ? tr.routes.map((r) => <tr key={r.route}><td style={{ fontFamily: 'monospace', fontSize: 12 }}>{r.route}</td><td>{r.count}</td><td>{r.p50_ms} ms</td><td>{r.p95_ms} ms</td><td>{r.errors || '-'}</td></tr>) : <tr><td colSpan="5" className="muted">No requests yet.</td></tr>}</tbody></table>
          </div>
        </Sec>
        <Sec title="Assistant safety" hint="outcomes, never the questions">
          <table className="rt"><tbody>{['chat', 'navigate', 'medicine', 'emergency', 'unavailable', 'error'].map((k) => <tr key={k}><td><b>{k}</b></td><td>{data.assistant[k] || 0}</td></tr>)}</tbody></table>
          <div className="note">Emergency and medicine questions are answered by fixed rules and never reach the language model. Message text is not stored.</div>
        </Sec>
      </div>

      <Sec title="Audit trail" hint="latest 30 events, kept in memory">
        <table className="rt"><thead><tr><th>Time (UTC)</th><th>Actor</th><th>Action</th><th>Detail</th></tr></thead>
          <tbody>{data.audit.length ? data.audit.map((a, i) => <tr key={i}><td>{a.time}</td><td>{a.actor}</td><td><b>{a.action}</b></td><td className="muted">{a.detail}</td></tr>) : <tr><td colSpan="4" className="muted">Nothing yet. Use the doctor or patient view and refresh.</td></tr>}</tbody></table>
      </Sec>

      <Sec title="Before this touches real patient data" hint={`${failing} open`}>
        <div style={{ display: 'grid', gap: 8 }}>
          {data.hardening.map((h) => (
            <div key={h.item} className="adm-chk" style={{ background: TONE[h.ok ? 'mint' : 'butter'].bg, color: TONE[h.ok ? 'mint' : 'butter'].dd }}>
              <b>{h.ok ? '✓' : '!'} {h.item}</b><span>{h.note}</span>
            </div>
          ))}
        </div>
      </Sec>
    </div>
  )
}
