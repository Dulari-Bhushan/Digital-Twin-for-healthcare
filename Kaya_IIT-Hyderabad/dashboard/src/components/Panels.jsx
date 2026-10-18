import { DR, explain, fmtDT, pct, riskColor } from '../utils'
import LineChart from './LineChart'

export function PatientList({ patients, selected, onSelect }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <h2>Today's priorities</h2>
        <span className="muted" style={{ fontSize: 12 }}>{patients.length} patients</span>
      </div>
      {patients.map((p) => (
        <button key={p.id} className={`pt ${selected === p.id ? 'on' : ''}`} onClick={() => onSelect(p.id)}>
          <div className="pt-row">
            <span className="pt-id">Patient {p.id}</span>
            <span className={`badge ${p.tier}`}>{p.tier}</span>
            <span className="spacer" />
            <span className="pt-meta">{p.age}{p.sex} · TIR {pct(p.tir)}</span>
          </div>
          <div className="pt-why">{p.reasons.length ? p.reasons.join(' · ') : 'Stable, no flags'}</div>
        </button>
      ))}
    </aside>
  )
}

export function PatientHeader({ d }) {
  const p = d.profile
  return (
    <div className="card">
      <div className="ph">
        <div>
          <h1>Patient {p.id}</h1>
          <div className="facts">
            <span><b>{p.age}</b> y, {p.sex === 'F' ? 'female' : 'male'}</span>
            <span>BMI <b>{p.bmi}</b></span>
            <span>Waist <b>{p.waist_cm}</b> cm</span>
            <span>T2D for <b>{p.duration_yrs}</b> y</span>
            <span>HbA1c <b>{p.hba1c}%</b></span>
            <span>BP <b>{p.sbp}/{p.dbp}</b></span>
            <span>{p.metformin ? 'Metformin' : 'No metformin'}{p.on_insulin_or_su ? ' · insulin/SU (hypo risk)' : ''}</span>
            <span>PNPLA3 G alleles <b>{p.pnpla3_g_alleles}</b> · TCF7L2 T alleles <b>{p.tcf7l2_t_alleles}</b></span>
          </div>
        </div>
        <span className="spacer" />
        <span className={`badge ${d.summary.tier}`} style={{ fontSize: 13, padding: '5px 12px' }}>{d.summary.tier} priority</span>
      </div>
    </div>
  )
}

export function TwinNow({ at, metrics }) {
  const tile = (f) => (
    <div className="kpi" key={f.minutes}>
      <div className="l">In {f.minutes} min</div>
      <div className="v">{Math.round(f.median)}</div>
      <div className="s">80% range {Math.round(f.lo)}–{Math.round(f.hi)} mg/dL</div>
    </div>
  )
  const prob = (label, p, warn) => (
    <div className="kpi">
      <div className="l">{label}</div>
      <div className="v" style={{ color: riskColor(p, 0.6, 0.3) }}>{pct(p)}</div>
      <div className="bar"><i style={{ width: `${Math.min(100, p * 100)}%`, background: riskColor(p, 0.6, 0.3) }} /></div>
      <div className="s">{warn}</div>
    </div>
  )
  return (
    <div className="grid4">
      <div className="kpi">
        <div className="l">Glucose now</div>
        <div className="v">{Math.round(at.glucose)} <span className="muted" style={{ fontSize: 13 }}>mg/dL</span></div>
        <div className="s">TIR {pct(metrics.tir)} · GV {metrics.gv_cv.toFixed(0)}%</div>
      </div>
      {at.forecast.map(tile)}
      {prob('High glucose within 2 h', at.p_hyper, 'Probability of crossing 180 mg/dL')}
      {prob('Low glucose within 2 h', at.p_hypo, 'Probability of dropping below 70 mg/dL')}
    </div>
  )
}

export function Alerts({ alerts, series }) {
  const list = [...alerts].reverse()
  return (
    <div className="card">
      <div className="card-head"><h2>Alert timeline</h2><span className="chip">Calibrated; ~1 false alert per patient-day</span></div>
      {list.length === 0 && <div className="muted">No alerts in this window.</div>}
      {list.slice(0, 8).map((a, i) => {
        const idx = a.t - series.t0
        return (
          <div className="alert" key={i}>
            <span className="dot" style={{ background: a.type === 'hypo' ? 'var(--high)' : 'var(--med)' }} />
            <div>
              <b>{a.type === 'hypo' ? 'Low glucose expected' : 'High glucose expected'}</b>
              <span className="muted"> · probability {pct(a.prob)}</span>
              <div className="muted" style={{ fontSize: 12 }}>Why: {explain(series, idx, a.type)}</div>
            </div>
            <span className="muted" style={{ fontSize: 12 }}>{fmtDT(series.start, idx)}</span>
          </div>
        )
      })}
    </div>
  )
}

const months = (i) => `${i}m`

export function Organs({ d }) {
  const tl = d.liver.timeline
  const cl = d.profile.clinic
  const lab = d.profile.labs
  const stage = lab.egfr >= 90 ? 'G1' : lab.egfr >= 60 ? 'G2' : lab.egfr >= 45 ? 'G3a' : lab.egfr >= 30 ? 'G3b' : 'G4+'
  return (
    <div className="grid3">
      <div className="card">
        <div className="card-head"><h2>Liver</h2><span className="real">Real-data model</span></div>
        <div className="kpi" style={{ marginBottom: 10 }}>
          <div className="l">Steatosis risk now → 12 months at current habits</div>
          <div className="v" style={{ color: riskColor(tl.steatosis.at(-1), 0.6, 0.3) }}>{pct(tl.steatosis[0])} → {pct(tl.steatosis.at(-1))}</div>
          <div className="s">Advanced fibrosis {pct(tl.adv_fibrosis[0], 1)} → {pct(tl.adv_fibrosis.at(-1), 1)}</div>
        </div>
        <LineChart height={150} yDomain={[0, 1]} yFmt={(v) => `${Math.round(v * 100)}%`} xTickEvery={3} xLabel={months}
          series={[{ name: 'Steatosis', y: tl.steatosis, color: 'var(--accent)' }, { name: 'Advanced fibrosis', y: tl.adv_fibrosis, color: 'var(--high)' }]} />
        <div className="note">Baseline from a model validated on real NHANES FibroScan data (AUROC 0.83). The 12-month drift from glucose habits is a simulation with editable assumptions. Latest simulated FibroScan: {cl.liver_stiffness_kpa} kPa; FIB-4 {lab.fib4}.</div>
      </div>
      <div className="card">
        <div className="card-head"><h2>Eye</h2><span className="real">Grader: real data</span></div>
        <div className="grid2" style={{ gap: 8, marginBottom: 10 }}>
          <figure style={{ margin: 0 }}>
            <img src={`/eye-img/grade${d.eye.grade}.jpg`} alt={`Example fundus photo, grade ${d.eye.grade}`} style={{ width: '100%', borderRadius: 8, display: 'block' }} />
            <figcaption className="muted" style={{ fontSize: 11, marginTop: 3 }}>Example fundus, grade {d.eye.grade}</figcaption>
          </figure>
          <figure style={{ margin: 0 }}>
            <img src={`/eye-img/grade${d.eye.grade}_cam.jpg`} alt="Grad-CAM heatmap" style={{ width: '100%', borderRadius: 8, display: 'block' }} />
            <figcaption className="muted" style={{ fontSize: 11, marginTop: 3 }}>Where the model looked</figcaption>
          </figure>
        </div>
        <div className="kpi" style={{ marginBottom: 10 }}>
          <div className="l">Retinopathy grade</div>
          <div className="v">{DR[d.eye.grade]}</div>
          <div className="s">Grade {d.eye.grade} of 4 at last exam</div>
        </div>
        <div className="kpi">
          <div className="l">2-year progression risk</div>
          <div className="v" style={{ color: riskColor(d.eye.progression_2y, 0.4, 0.2) }}>{pct(d.eye.progression_2y)}</div>
          <div className="bar"><i style={{ width: `${d.eye.progression_2y * 100}%`, background: riskColor(d.eye.progression_2y, 0.4, 0.2) }} /></div>
          <div className="s">HbA1c, duration, BP, glucose variability, time in range</div>
        </div>
        <div className="note">Images: representative IDRiD photos (CC BY 4.0) of this patient's recorded grade; patients are synthetic. The grader is validated on real images (APTOS held-out kappa 0.89; Indian IDRiD test 0.71 after local fine-tuning). The 2-year progression risk is a simulation: drivers follow DCCT/UKPDS directions, coefficients are assumptions.</div>
      </div>
      <div className="card">
        <div className="card-head"><h2>Kidney</h2><span className="chip">Monitoring</span></div>
        <div className="kpi" style={{ marginBottom: 10 }}>
          <div className="l">eGFR</div>
          <div className="v">{lab.egfr.toFixed(0)} <span className="muted" style={{ fontSize: 13 }}>mL/min · {stage}</span></div>
        </div>
        <div className="kpi">
          <div className="l">Urine albumin/creatinine</div>
          <div className="v" style={{ color: lab.uacr_mg_g >= 30 ? 'var(--high)' : 'var(--text)' }}>{lab.uacr_mg_g.toFixed(0)} <span className="muted" style={{ fontSize: 13 }}>mg/g</span></div>
          <div className="s">{lab.uacr_mg_g >= 30 ? 'Albuminuria: review' : 'Normal range'}</div>
        </div>
        <div className="note">Latest labs only. Kidney risk forecasting is on the roadmap.</div>
      </div>
    </div>
  )
}
