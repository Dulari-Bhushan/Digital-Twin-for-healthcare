import { useEffect, useMemo, useRef, useState } from 'react'
import { Ring, TONE, pct, useWidth } from '../ui'
import LineChart from './LineChart'
import { initialsOf } from './Doctor'

const get = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json() })

const TREND = [
  { key: 'rmssd_night', title: 'Night HRV (RMSSD, ms)', color: '#0F6E68', fmt: (v) => Math.round(v) },
  { key: 'rhr', title: 'Resting heart rate (bpm)', color: '#c4645b', fmt: (v) => Math.round(v) },
  { key: 'sleep_h', title: 'Sleep (hours)', color: '#4f8196', fmt: (v) => v.toFixed(1) },
  { key: 'steps24', title: 'Steps per day', color: '#d9894a', fmt: (v) => Math.round(v / 100) * 100 },
  { key: 'hypo_min', title: 'Time below 70 mg/dL (min per day)', color: '#b8741f', fmt: (v) => Math.round(v), only: (pr) => pr.on_insulin_or_su },
]

function Timeline({ art, idx, reveal }) {
  const [ref, W] = useWidth()
  const m = art.mornings
  const H = 190, pad = { l: 40, r: 14, t: 14, b: 26 }
  const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b
  const k0 = m[0].k, k1 = m[m.length - 1].k
  const top = Math.max(0.5, ...m.map((x) => x.p)) * 1.08
  const x = (k) => pad.l + ((k - k0) / (k1 - k0)) * iw
  const y = (v) => pad.t + ih - (v / top) * ih
  const cur = m[idx]
  const evs = art.outcome.events, bn = art.outcome.benign_episodes
  return (
    <div ref={ref} style={{ width: '100%', minWidth: 0, overflow: 'hidden' }}>
      <svg width={W} height={H} role="img" aria-label="Combined 72 hour risk by morning">
        {[0, 0.25, 0.5, 0.75].filter((v) => v <= top).map((v) => (
          <g key={v}><line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="rgba(28,52,50,.07)" strokeDasharray="3 5" />
            <text x={pad.l - 8} y={y(v) + 4} textAnchor="end" fontSize="11" fontWeight="600" fill="#667b78">{Math.round(v * 100)}%</text></g>
        ))}
        {m.filter((_, i) => i % 3 === 0).map((r) => <text key={r.k} x={x(r.k)} y={H - 8} textAnchor="middle" fontSize="11" fontWeight="600" fill="#667b78">Day {r.k}</text>)}
        <line x1={pad.l} x2={W - pad.r} y1={y(art.threshold)} y2={y(art.threshold)} stroke="#c4645b" strokeDasharray="6 5" strokeWidth="1.6" />
        <text x={W - pad.r} y={y(art.threshold) - 5} textAnchor="end" fontSize="11" fontWeight="800" fill="#8a3b34">alert threshold {pct(art.threshold)}</text>
        {reveal && bn.map((b, i) => <g key={`b${i}`}><line x1={x(b.day)} x2={x(b.day)} y1={pad.t} y2={pad.t + ih} stroke="#E9A23B" strokeWidth="2" strokeDasharray="2 4" />
          <text x={x(b.day)} y={pad.t + 10} textAnchor="middle" fontSize="11" fontWeight="800" fill="#77501a">episode resolved</text></g>)}
        {reveal && evs.map((e, i) => <g key={`c${i}`}><rect x={x(e.day)} width={Math.max(0, Math.min(x(e.day + 3), W - pad.r) - x(e.day))} y={pad.t} height={ih} fill="rgba(28,52,50,.07)" />
          <text x={x(e.day) + 4} y={pad.t + ih - 6} fontSize="11" fontWeight="700" fill="#667b78">in care, not scored</text></g>)}
        {reveal && evs.map((e, i) => <g key={`e${i}`}><line x1={x(e.day)} x2={x(e.day)} y1={pad.t} y2={pad.t + ih} stroke="#c4645b" strokeWidth="2.4" />
          <text x={x(e.day) - 4} y={pad.t + 10} textAnchor="end" fontSize="11" fontWeight="800" fill="#8a3b34">cardiac event</text></g>)}
        <polyline fill="none" stroke="#0F6E68" strokeWidth="3.2" strokeLinejoin="round" strokeLinecap="round"
          points={m.slice(0, idx + 1).map((r) => `${x(r.k).toFixed(1)},${y(r.p).toFixed(1)}`).join(' ')} />
        {m.slice(0, idx + 1).filter((r) => r.alert).map((r) => <path key={r.k} d={`M${x(r.k)} ${y(r.p) - 9} l7 9 l-7 9 l-7 -9Z`} fill="#c4645b" stroke="#fff" strokeWidth="1.5" />)}
        <circle cx={x(cur.k)} cy={y(cur.p)} r="6" fill="#fff" stroke="#0F6E68" strokeWidth="4" />
      </svg>
      <div className="legend"><span><i style={{ background: '#0F6E68' }} />Combined 72 h risk each morning</span><span><i style={{ background: '#c4645b' }} />Alert raised</span></div>
    </div>
  )
}

function Verdict({ art, idx }) {
  const m = art.mornings, cur = m[idx], thr = art.threshold
  const noRecord = art.profile.record_missing > 0
  if (cur.abstain) return { tone: 'butter', head: 'Not enough data', text: `Only ${cur.n_nights} of the last 7 nights have wearable data, so Kaya does not score this morning and raises no alert. Wearing the watch overnight brings the score back.` }
  const recent = m.slice(Math.max(0, idx - 2), idx + 1).filter((x) => x.alert)
  const since = recent.length ? idx - m.indexOf(recent[0]) : null
  const bg = cur.record_pct > 0.75 ? 'high' : cur.record_pct > 0.4 ? 'moderate' : 'low'
  const basis = noRecord ? 'There is no clinical record on file, so this rests on the wearable and glucose sensor alone.' : `Background risk from the record is ${bg}.`
  if (cur.alert) return { tone: 'rose', head: 'Review suggested', text: `Worth a look within ${art.horizon_h} hours: the wearable pattern changed and the combined risk is ${pct(cur.p)}, over the alert line of ${pct(thr)}. ${basis}` }
  if (since != null) return { tone: 'rose', head: 'Review still open', text: `Raised ${since} day${since > 1 ? 's' : ''} ago and the risk is still elevated (${pct(cur.p)}).` }
  if (cur.p_wearable >= thr) return { tone: 'butter', head: 'Watching', text: `The wearable pattern looks unusual, but ${noRecord ? 'the record is empty and ' : "this patient's background risk is low, so "}the combined risk (${pct(cur.p)}) stays under the alert line. No alert is raised.` }
  return { tone: 'mint', head: 'No action needed', text: `Combined risk ${pct(cur.p)}, below the alert line of ${pct(thr)}.` }
}

function Evidence({ ev }) {
  if (!ev) return null
  const rows = [['static_logistic', 'Record only (a risk score)'], ['rule', 'Simple clinical rule'], ['wearable', 'Wearable week only'], ['fused', 'Kaya: record + wearable']]
  const al = ev.alert_replay
  return (
    <div className="card soft">
      <div className="card-h"><h2>How well does it work?</h2><span className="chip">held-out patients · {ev.folds}-fold cross-validation</span></div>
      <div className="muted" style={{ fontSize: 13, marginBottom: 10 }}>
        {ev.n_patients.toLocaleString()} synthetic patients, {ev.n_mornings.toLocaleString()} mornings. The question each morning: will this patient have a cardiovascular event in the next {ev.horizon_h} hours?
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead><tr style={{ textAlign: 'left', color: 'var(--muted)', fontSize: 12 }}>
            <th style={{ padding: '6px 8px' }}>Input</th><th>AUROC (95% CI)</th><th>Events caught</th><th>Alerts that were right</th><th>False alerts / patient-month</th><th>Median warning</th></tr></thead>
          <tbody>
            {rows.map(([k, label]) => {
              const a = ev.auroc_with_ci[k], r = al[k]
              return (
                <tr key={k} style={{ background: k === 'fused' ? 'var(--lav)' : 'transparent', fontWeight: k === 'fused' ? 800 : 600 }}>
                  <td style={{ padding: '8px' }}>{label}</td>
                  <td>{a.auroc.toFixed(2)} ({a.ci95[0].toFixed(2)} to {a.ci95[1].toFixed(2)})</td>
                  <td>{pct(r.sensitivity)}</td><td>{pct(r.precision)}</td><td>{r.false_alerts_per_patient_month.toFixed(1)}</td><td>{r.median_lead_h.toFixed(0)} h</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>
        The wearable week is what tells us a prodrome is under way, and it carries most of the early warning. Once a patient is in a prodrome, the record is the better guide to whether it turns dangerous: on that question alone the record scores AUROC {ev.prodrome_event_vs_benign.static_logistic.toFixed(2)} and the wearable {ev.prodrome_event_vs_benign.wearable.toFixed(2)}. The combined score has to do both jobs at once, so it improves on the wearable alone only modestly ({ev.auroc_with_ci.fused.auroc.toFixed(2)} against {ev.auroc_with_ci.wearable.auroc.toFixed(2)}).
        Synthetic cohort: it shows the mechanism works, not clinical accuracy. Decision support, not a diagnosis.
      </div>
    </div>
  )
}

const GAP_ROWS = [0, 0.3, 0.5]

function Robustness({ r }) {
  const lows = r.glucose_lows_ablation
  const gaps = r.wearable_gaps_and_noise.filter((x) => x.noise === 0 && GAP_ROWS.includes(x.gap))
  const gain = (k) => { const g = lows[k].auroc_without_lows.fused_minus_this; return g ? `${g.mean >= 0 ? '+' : ''}${g.mean.toFixed(3)} (${g.ci95[0].toFixed(3)} to ${g.ci95[1].toFixed(3)})` : '' }
  const th = { textAlign: 'left', color: 'var(--muted)', fontSize: 12, padding: '4px 8px' }, td = { padding: '6px 8px' }
  return (
    <div className="card soft">
      <div className="card-h"><h2>When the data is thin or messy</h2><span className="chip">{r.n_test_patients} held-out patients</span></div>
      <div className="muted" style={{ fontSize: 13, marginBottom: 12 }}>
        A wearable is not always worn, and a new patient may have no record. These are the stress tests we ran, so the limits are on the page and not a surprise.
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 22 }}>
        <div>
          <h3>Do glucose lows help?</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead><tr><th style={th}>Patients</th><th style={th}>AUROC with / without lows</th><th style={th}>Gain</th></tr></thead>
            <tbody>{['everyone', 'insulin_or_sulfonylurea'].map((k) => (
              <tr key={k}><td style={td}>{k === 'everyone' ? 'Everyone' : 'On insulin or sulfonylurea'}</td>
                <td style={td}>{lows[k].auroc_with_lows.auroc.toFixed(3)} / {lows[k].auroc_without_lows.auroc.toFixed(3)}</td><td style={td}>{gain(k)}</td></tr>))}</tbody>
          </table>
          <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>The simulator links severe lows to heart episodes, so this shows the flag can use the link, not that real patients have it.</div>
        </div>
        <div>
          <h3>Watch off for whole days</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead><tr><th style={th}>Days missing</th><th style={th}>Scored</th><th style={th}>AUROC, trained on clean data</th><th style={th}>AUROC, trained with gaps</th><th style={th}>Events caught / false alerts per month</th></tr></thead>
            <tbody>{gaps.map((x) => (
              <tr key={x.gap}><td style={td}>{Math.round(x.gap * 100)}%</td><td style={td}>{Math.round(x.share_scored * 100)}%</td>
                <td style={td}>{x.trained_clean.auroc_all_mornings.toFixed(3)}</td><td style={{ ...td, fontWeight: 800 }}>{x.trained_with_gaps.auroc_all_mornings.toFixed(3)}</td>
                <td style={td}>{Math.round(x.trained_with_gaps.alerts_with_abstain.sensitivity * 100)}% / {x.trained_with_gaps.alerts_with_abstain.false_alerts_per_patient_month.toFixed(1)}</td></tr>))}</tbody>
          </table>
          <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>With fewer than {r.min_nights} usable nights in the last seven, Kaya says "not enough data" and raises no alert, so fewer events are caught as more days go missing.</div>
        </div>
        <div>
          <h3>No record on file</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead><tr><th style={th}>Record fields missing</th><th style={th}>Kaya AUROC</th><th style={th}>Wearable alone</th></tr></thead>
            <tbody>{r.thin_record.map((x) => (
              <tr key={x.record_fields_missing}><td style={td}>{Math.round(x.record_fields_missing * 100)}%</td><td style={td}>{x.fused_auroc.toFixed(3)}</td><td style={td}>{x.wearable_only_auroc.toFixed(3)}</td></tr>))}</tbody>
          </table>
          <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>A missing field is filled with the average patient. With no record the score falls back to the wearable and glucose sensor.</div>
        </div>
      </div>
      <div className="muted" style={{ fontSize: 12, marginTop: 12 }}>The simulated wearable data was built with a prodrome in it, and real devices are noisier, so these numbers are an upper bound until the flag is tested on real patients.</div>
    </div>
  )
}

/** `pid` is the patient chosen in the glucose twin (the same people appear here); `onPick` reports a change back, and `onOpenTwin` jumps there. */
export default function Heart({ pid = null, onPick = () => {}, onOpenTwin = () => {} }) {
  const [list, setList] = useState([])
  const [sel, setSel] = useState(null)
  const [art, setArt] = useState(null)
  const [ev, setEv] = useState(null)
  const [idx, setIdx] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [err, setErr] = useState(null)
  const timer = useRef(null)

  useEffect(() => {
    const want = Number(new URLSearchParams(window.location.search).get('hp')) || pid
    get('/api/cardio/patients').then((p) => { setList(p); setSel(p.find((x) => x.id === want)?.id ?? p.find((x) => x.group === 'demo')?.id ?? p[0]?.id ?? null) }).catch((e) => setErr(String(e)))
    get('/api/cardio/evidence').then(setEv).catch(() => {})
  }, [])
  useEffect(() => {
    if (sel == null) return
    setPlaying(false)
    get(`/api/cardio/${sel}`).then((a) => {
      setArt(a)
      const day = Number(new URLSearchParams(window.location.search).get('day'))
      setIdx(Math.max(0, a.mornings.findIndex((m) => m.k === day)))
    }).catch((e) => setErr(String(e)))
  }, [sel])
  useEffect(() => {
    clearInterval(timer.current)
    if (!playing || !art) return
    timer.current = setInterval(() => setIdx((i) => { if (i + 1 >= art.mornings.length) { setPlaying(false); return i } return i + 1 }), 700)
    return () => clearInterval(timer.current)
  }, [playing, art])

  const cur = art?.mornings[idx]
  const verdict = useMemo(() => (art ? Verdict({ art, idx }) : null), [art, idx])
  if (err) return <div style={{ padding: 40 }}>Heart watch is not available: {err}. Build it with <code>src/api/build_cardio_artifacts.py</code>.</div>
  if (!art || !cur) return <div className="stage muted">Loading Heart watch…</div>
  const pr = art.profile
  const last = idx === art.mornings.length - 1
  const tone = TONE[verdict.tone]
  const noRecord = pr.record_missing > 0
  const nn = cur.n_nights, quality = nn >= 6 ? 'mint' : nn >= art.min_nights ? 'butter' : 'rose'
  const confidence = cur.abstain ? ['rose', 'Confidence: none, not scored'] : nn >= 6 && !noRecord ? ['mint', 'Confidence: normal'] : ['butter', 'Confidence: lower']
  const chips = noRecord ? [['butter', `Record not on file (${pr.record_missing} fields)`]] : [
    pr.prior_cvd && ['rose', 'Prior cardiovascular disease'], pr.smoker && ['peach', 'Smoker'], pr.sbp >= 140 && ['peach', `BP ${pr.sbp}`],
    pr.on_insulin_or_su && ['butter', 'Insulin / sulfonylurea'], ['sky', `Diabetes ${pr.duration_yrs} y`], ['sky', `HbA1c ${pr.hba1c}`], ['sky', `LDL ${pr.ldl}`],
  ].filter(Boolean)
  chips.push([quality, `Wearable data: ${nn} of 7 nights`], confidence)
  const lows = pr.on_insulin_or_su && !cur.abstain && cur.lows_7d >= 1

  return (
    <div className="layout two-col">
      <aside className="side">
        <h2>Heart watch</h2>
        <div className="muted" style={{ fontSize: 13, padding: '0 6px 4px' }}>A week of sleep, heart rate, HRV and glucose lows, read together with the record. Scores come from models that never saw these patients.</div>
        {[['demo', 'The glucose twin patients'], ['edge', 'Edge cases: messy data']].map(([grp, title]) => (
          <div key={grp}>
            <div className="muted" style={{ fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.06em', padding: '10px 6px 2px' }}>{title}</div>
            {list.filter((p) => p.group === grp).map((p) => (
              <button key={p.id} className={`pt ${sel === p.id ? 'on' : ''}`} onClick={() => { setSel(p.id); if (p.group === 'demo') onPick(p.id) }}>
                <span className="av" style={{ background: TONE.sky.bg, color: TONE.sky.dd, fontSize: 16 }}>{initialsOf(p.name)}</span>
                <span><b>{p.name}</b><small>Age {p.age} · {p.sex === 'F' ? 'Female' : 'Male'}{p.prior_cvd ? ' · prior CVD' : ''}{p.story === 'patchy_data' ? ' · watch often off' : ''}{p.record_missing ? ' · no record' : ''}</small></span>
                <span className="chip" style={{ background: p.alerts ? TONE.rose.bg : TONE.mint.bg, color: p.alerts ? TONE.rose.dd : TONE.mint.dd }}>{p.alerts ? `${p.alerts} alert${p.alerts > 1 ? 's' : ''}` : 'quiet'}</span>
              </button>
            ))}
          </div>
        ))}
      </aside>
      <main className="bento">
        <div className="c12 card lav">
          <div className="row wrap" style={{ gap: 14 }}>
            <span className="av" style={{ background: '#fff', color: 'var(--lav-dd)', width: 64, height: 64, borderRadius: 22, fontSize: 22 }}>{initialsOf(pr.name)}</span>
            <div style={{ flex: 1, minWidth: 220 }}>
              <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-.03em' }}>{pr.name}</h1>
              <div className="muted" style={{ fontWeight: 600 }}>{pr.age} y · {pr.sex === 'F' ? 'Female' : 'Male'} · BMI {pr.bmi}{pr.egfr != null ? ` · eGFR ${pr.egfr}` : ''}</div>
              <div className="row wrap" style={{ gap: 6, marginTop: 8 }}>{chips.map(([t, label]) => <span key={label} className={`chip ${t}`}>{label}</span>)}</div>
              {pr.group === 'demo' && <button className="btn sm" style={{ marginTop: 10 }} onClick={() => onOpenTwin(pr.id)}>Open this patient's glucose twin</button>}
            </div>
            <div style={{ minWidth: 260, flex: 1 }}>
              <div className="row" style={{ gap: 10 }}>
                <button className="btn go sm" onClick={() => { if (last) setIdx(0); setPlaying((p) => !p) }}>{playing ? 'Pause' : last ? 'Replay the month' : 'Replay the month'}</button>
                <b className="num" style={{ fontSize: 20 }}>Day {cur.k}</b><span className="muted" style={{ fontSize: 13 }}>10:00 morning check</span>
              </div>
              <input type="range" min="0" max={art.mornings.length - 1} value={idx} onChange={(e) => { setPlaying(false); setIdx(Number(e.target.value)) }} aria-label="Morning" style={{ marginTop: 12 }} />
            </div>
          </div>
        </div>

        <div className="c4 card" style={{ '--card': tone.bg }}>
          <h3 style={{ color: tone.dd }}>This morning's verdict</h3>
          <div style={{ fontSize: 30, fontWeight: 800, letterSpacing: '-.03em', color: tone.dd, margin: '6px 0' }}>{verdict.head}</div>
          <div style={{ color: tone.dd, fontWeight: 600 }}>{verdict.text}</div>
          <div style={{ color: tone.dd, fontSize: 12, marginTop: 10, opacity: 0.85 }}>Decision support: it points to a patient worth a look. It is not a diagnosis.</div>
        </div>

        <div className="c8 card soft">
          <div className="card-h"><h2>Two streams, one decision</h2><span className="chip">late fusion</span></div>
          <div className="row wrap" style={{ gap: 22, justifyContent: 'space-around', alignItems: 'center' }}>
            <div style={{ textAlign: 'center' }}>
              <Ring value={cur.abstain ? 0 : Math.min(1, cur.p_wearable)} size={118} color={cur.p_wearable >= art.threshold ? 'var(--peach-d)' : 'var(--sky-d)'}><b className="num" style={{ fontSize: 22 }}>{cur.abstain ? 'n/a' : pct(cur.p_wearable)}</b></Ring>
              <div style={{ fontWeight: 800, marginTop: 6 }}>Wearable + glucose pattern</div><div className="muted" style={{ fontSize: 12 }}>sleep, HRV, heart rate, steps, glucose lows</div>
            </div>
            <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--muted)' }}>+</div>
            <div style={{ textAlign: 'center' }}>
              <Ring value={noRecord ? 0 : cur.record_pct} size={118} color={cur.record_pct > 0.75 ? 'var(--rose-d)' : 'var(--mint-d)'}><b className="num" style={{ fontSize: 22 }}>{noRecord ? 'n/a' : Math.round(cur.record_pct * 100)}</b></Ring>
              <div style={{ fontWeight: 800, marginTop: 6 }}>{noRecord ? 'Record not on file' : 'Record risk percentile'}</div><div className="muted" style={{ fontSize: 12 }}>{noRecord ? 'scored as an average patient' : 'age, BP, HbA1c, LDL, history'}</div>
            </div>
            <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--muted)' }}>=</div>
            <div style={{ textAlign: 'center' }}>
              <Ring value={cur.abstain ? 0 : Math.min(1, cur.p)} size={118} color={cur.p >= art.threshold ? 'var(--rose-d)' : 'var(--lav-d)'}><b className="num" style={{ fontSize: 22 }}>{cur.abstain ? 'n/a' : pct(cur.p)}</b></Ring>
              <div style={{ fontWeight: 800, marginTop: 6 }}>Combined {art.horizon_h} h risk</div><div className="muted" style={{ fontSize: 12 }}>alert at {pct(art.threshold)}</div>
            </div>
          </div>
        </div>

        {lows && (
          <div className="c12 card butter">
            <div className="row wrap" style={{ gap: 14 }}>
              <span className="chip" style={{ background: '#fff', color: 'var(--butter-dd)' }}>Medicine check</span>
              <div style={{ flex: 1, minWidth: 260, fontWeight: 600, color: 'var(--butter-dd)' }}>
                {cur.lows_7d} day{cur.lows_7d > 1 ? 's' : ''} with glucose below 70 mg/dL in the last week ({cur.low_min_7d} minutes), while on insulin or a sulfonylurea.
                Lows can set off heart-rhythm problems, so the dose, its timing and the meals around it are worth reviewing with the patient.
              </div>
            </div>
          </div>
        )}

        <div className="c8 card soft">
          <div className="card-h"><h2>The last week, night by night</h2><span className="chip">days 1 to {cur.k}</span></div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 18 }}>
            {TREND.filter((t) => !t.only || t.only(pr)).map((t) => {
              const y = art.nights[t.key].slice(1, cur.k + 1)                   // nights without data stay gaps
              return (
                <div key={t.key}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--muted)' }}>{t.title}</div>
                  <LineChart series={[{ name: t.title, y, color: t.color }]} height={150} yFmt={t.fmt} xTickEvery={7} xLabel={(i) => `D${i + 1}`} />
                </div>
              )
            })}
          </div>
        </div>

        <div className="c4 card soft">
          <div className="card-h"><h2>Why this score</h2></div>
          {cur.abstain ? <div className="muted">Not scored this morning, so there is nothing to explain.</div> : cur.drivers.length === 0 ? <div className="muted">Nothing is pushing the risk up this morning.</div> : (
            <div style={{ display: 'grid', gap: 10 }}>
              {cur.drivers.map((d) => {
                const mx = Math.max(...cur.drivers.map((x) => x.push), 0.01)
                const wear = d.stream === 'wearable', glu = d.stream === 'glucose'
                return (
                  <div key={d.label}>
                    <div className="row" style={{ gap: 8, justifyContent: 'space-between' }}>
                      <b style={{ fontSize: 13 }}>{d.label}</b>
                      <span className={`chip ${wear ? 'sky' : glu ? 'butter' : 'peach'}`}>{wear ? 'wearable' : glu ? 'glucose sensor' : 'record'}</span>
                    </div>
                    <div style={{ height: 8, borderRadius: 6, background: 'rgba(15,110,104,.1)', marginTop: 4 }}>
                      <div style={{ width: `${(d.push / mx) * 100}%`, height: '100%', borderRadius: 6, background: wear ? 'var(--sky-d)' : glu ? 'var(--butter-d)' : 'var(--peach-d)' }} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
          <div className="muted" style={{ fontSize: 12, marginTop: 12 }}>Bars show how much each factor raised the score, from the record, the wearable and the glucose sensor on one scale.</div>
        </div>

        <div className="c12 card soft">
          <div className="card-h"><h2>Month timeline</h2>
            <span className="sp" />{!last && <span className="muted" style={{ fontSize: 12 }}>Replay to the end to see what really happened.</span>}</div>
          <Timeline art={art} idx={idx} reveal={last} />
        </div>
        <div className="c12"><Evidence ev={ev} /></div>
        {ev?.robustness && <div className="c12"><Robustness r={ev.robustness} /></div>}
      </main>
    </div>
  )
}
