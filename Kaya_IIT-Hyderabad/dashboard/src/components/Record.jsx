import { useEffect, useMemo, useState } from 'react'
import { getSeries } from '../api'
import { DR, TONE, pct, tierTone } from '../ui'
import { explain, fmtDT } from '../utils'
import { FEATURE_NAMES, agp, dailyStats, dayLabel, egfrStage, eyeFactors, kidneySlope, labFlag, mealResponses, mean } from '../record'
import LineChart from './LineChart'
import DiarySection from './Diary'
import { ChangesCard, ReportsTab } from './Reports'
import { AgpChart, Bars, CgmChart, Contrib, DataTable, StackedTir } from './RecordCharts'

export const TABS = [['catchup', 'Catch-up'], ['overview', 'Overview'], ['reports', 'Reports'], ['glucose', 'Glucose'], ['liver', 'Liver'], ['eyes', 'Eyes'], ['kidneys', 'Kidneys'], ['alerts', 'Alerts'], ['profile', 'Profile and labs']]

const Section = ({ title, hint, children, tone }) => (
  <section className={`card ${tone || 'soft'} rec-sec`} style={{ boxShadow: 'none' }}>
    <div className="card-h"><h2>{title}</h2>{hint && <span className="chip">{hint}</span>}</div>
    {children}
  </section>
)
const Kpi = ({ label, value, sub, tone = 'lav' }) => (
  <div className="kpi2" style={{ background: TONE[tone].bg, color: TONE[tone].dd }}>
    <div className="l">{label}</div><div className="v">{value}</div>{sub && <div className="s">{sub}</div>}
  </div>
)
const Flag = ({ f }) => <span className="chip" style={{ background: TONE[f.tone].bg, color: TONE[f.tone].dd }}>{f.text}</span>
const Evidence = ({ real, children }) => (
  <div className="note" style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
    <span className={real ? 'real' : 'sim'} style={{ flex: 'none' }}>{real ? 'Real-data model' : 'Simulation'}</span><span>{children}</span>
  </div>
)

function Drivers({ items, title }) {
  if (!items || !items.length) return null
  const mx = Math.max(...items.map((i) => Math.abs(i.shap)), 0.01)
  return (
    <div>
      <h3 style={{ margin: '4px 0 8px' }}>{title}</h3>
      {items.map((it) => {
        const [name, unit] = FEATURE_NAMES[it.feature] || [it.feature, '']
        const up = it.shap > 0
        const val = it.feature === 'diabetes' || it.feature === 'male' ? (it.value ? 'yes' : 'no') : `${Math.abs(it.value) >= 10 ? Math.round(it.value) : it.value}${unit}`
        return (
          <div key={it.feature} style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.4fr 60px', gap: 10, alignItems: 'center', padding: '5px 0', borderBottom: '1px solid var(--line)' }}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{name} <span className="muted" style={{ fontWeight: 600 }}>{val}</span></div>
            <div style={{ height: 9, borderRadius: 6, background: 'rgba(28,52,50,.06)' }}>
              <div style={{ width: `${(Math.abs(it.shap) / mx) * 100}%`, height: '100%', borderRadius: 6, background: up ? 'var(--rose-d)' : 'var(--mint-d)' }} />
            </div>
            <div style={{ fontSize: 12, fontWeight: 800, textAlign: 'right', color: up ? 'var(--rose-dd)' : 'var(--mint-dd)' }}>{up ? 'raises' : 'lowers'}</div>
          </div>
        )
      })}
    </div>
  )
}

/** One-screen catch-up: is anything alarming, then the key numbers, changes, graphs and reports. */
function CatchUp({ d, days, series, go, changes, pid }) {
  const m = d.metrics, lab = d.profile.labs, kp = d.kidney.projection, tl = d.liver.timeline
  const alarms = []
  if (m.tbr > 0.002) alarms.push(`Low glucose: ${pct(m.tbr, 1)} of the last 14 days below 70 mg/dL${d.profile.on_insulin_or_su ? ' (on low-glucose risk drugs)' : ''}`)
  if (d.alerts.some((a) => a.type === 'hypo')) alarms.push('Low-glucose alert in the last 3 days')
  if (m.tir < 0.5) alarms.push(`Time in range only ${pct(m.tir)} (goal above 70%)`)
  if (d.profile.hba1c >= 9) alarms.push(`HbA1c ${d.profile.hba1c}% (target below 7%)`)
  if (lab.egfr < 60) alarms.push(`eGFR ${lab.egfr.toFixed(0)}: kidney function reduced`)
  if (lab.uacr_mg_g >= 30) alarms.push(`Urine albumin ${lab.uacr_mg_g.toFixed(0)} mg/g: albuminuria`)
  if (d.eye.grade >= 2) alarms.push(`Eyes: ${DR[d.eye.grade]}`)
  if (tl.adv_fibrosis.at(-1) > 0.2) alarms.push(`Liver: advanced fibrosis risk ${pct(tl.adv_fibrosis.at(-1), 1)} at 12 months`)
  if (changes) changes.items.filter((i) => i.scope === 'visit' && i.direction === 'worse' && i.severity >= 2).forEach((i) => alarms.push(`Worse since last visit: ${i.label}`))
  const bad = alarms.length > 0
  const tone = d.summary.tier === 'high' || alarms.length >= 3 ? 'rose' : bad ? 'butter' : 'mint'
  return (
    <>
      <section className="card rec-sec" style={{ boxShadow: 'none', background: TONE[tone].bg, color: TONE[tone].dd }}>
        <div className="card-h"><h2>{tone === 'mint' ? 'Nothing alarming right now' : tone === 'rose' ? 'Needs attention' : 'Worth a look'}</h2>
          <span className="chip">{d.summary.tier} priority</span></div>
        {bad ? <ul style={{ margin: 0, paddingLeft: 20, fontWeight: 700 }}>{alarms.map((a) => <li key={a}>{a}</li>)}</ul>
          : <div style={{ fontWeight: 700 }}>No low-glucose events, control and organ markers are within the usual targets.</div>}
        {d.summary.reasons.length > 0 && <div className="row wrap" style={{ gap: 6, marginTop: 10 }}>{d.summary.reasons.map((r) => <span key={r} className="chip">{r}</span>)}</div>}
      </section>
      <Overview d={d} days={days} series={series} go={go} changes={changes} />
      <Section title="Glucose, last 14 days" hint="Glucose tab for more"><CgmChart series={series} /></Section>
      <h2 style={{ margin: '18px 0 8px' }}>Reports, trends and medicines</h2>
      <ReportsTab pid={pid} d={d} />
    </>
  )
}

/* ------------------------------------------------------------------ tabs */
function Overview({ d, days, series, go, changes }) {
  const m = d.metrics
  const tl = d.liver.timeline
  const lab = d.profile.labs
  const kp = d.kidney.projection
  const steps = mean(days.map((x) => x.steps))
  const sleep = mean(days.map((x) => x.sleep))
  const lv = tl.steatosis.at(-1)
  const items = [
    { tab: 'glucose', tone: m.tir < 0.5 ? 'rose' : m.tir < 0.7 ? 'butter' : 'mint', title: 'Glucose control', text: `${pct(m.tir)} time in range over 14 days (goal above 70%); ${pct(m.tar)} above 180${m.tbr > 0.005 ? `; ${pct(m.tbr, 1)} below 70` : ''}.` },
    { tab: 'liver', tone: lv > 0.6 ? 'rose' : lv > 0.3 ? 'butter' : 'mint', title: 'Liver', text: `Fat risk ${pct(tl.steatosis[0])} now, ${pct(lv)} at 12 months; advanced fibrosis ${pct(tl.adv_fibrosis[0], 1)}, rising to ${pct(tl.adv_fibrosis.at(-1), 1)}.` },
    { tab: 'eyes', tone: d.eye.grade >= 2 || d.eye.progression_2y > 0.4 ? 'rose' : d.eye.progression_2y > 0.2 ? 'butter' : 'mint', title: 'Eyes', text: `${DR[d.eye.grade]}; ${pct(d.eye.progression_2y)} chance of progressing within 2 years.` },
    { tab: 'kidneys', tone: lab.egfr < 60 || lab.uacr_mg_g >= 30 ? 'rose' : kp.egfr.at(-1) < 60 ? 'butter' : 'mint', title: 'Kidneys', text: `eGFR ${lab.egfr.toFixed(0)} (${egfrStage(lab.egfr)}), UACR ${lab.uacr_mg_g.toFixed(0)} mg/g; about ${kp.egfr.at(-1).toFixed(0)} in 5 years at current habits.` },
    { tab: 'glucose', tone: steps < 4500 || sleep < 6 ? 'butter' : 'mint', title: 'Activity and sleep', text: `${Math.round(steps).toLocaleString()} steps a day (goal 6,000); about ${sleep.toFixed(1)} hours of sleep a night.` },
  ]
  return (
    <>
      <div className="rec-kpis">
        <Kpi label="Time in range" value={pct(m.tir)} sub="14 days" tone={m.tir < 0.5 ? 'rose' : m.tir < 0.7 ? 'butter' : 'mint'} />
        <Kpi label="Mean glucose" value={`${m.mean.toFixed(0)}`} sub={`mg/dL · est. HbA1c ${m.gmi.toFixed(1)}`} tone="lav" />
        <Kpi label="Variability (CV)" value={`${m.gv_cv.toFixed(0)}%`} sub="target below 36%" tone={m.gv_cv > 36 ? 'butter' : 'mint'} />
        <Kpi label="Lows (below 70)" value={pct(m.tbr, 1)} sub={`${days.reduce((a, x) => a + x.lowMin, 0)} min in 14 days`} tone={m.tbr > 0.01 ? 'rose' : 'mint'} />
        <Kpi label="Steps a day" value={Math.round(steps).toLocaleString()} sub="goal 6,000" tone={steps < 4500 ? 'butter' : 'mint'} />
        <Kpi label="Sleep" value={`${sleep.toFixed(1)} h`} sub="per night" tone={sleep < 6 ? 'butter' : 'mint'} />
      </div>
      <ChangesCard ch={changes} audience="doctor" onOpen={go} />
      <DiarySection pid={d.profile.id} />
      <Section title="Problem list" hint="click a row to open it">
        <div style={{ display: 'grid', gap: 10 }}>
          {items.map((it) => (
            <button key={it.title} className="prob" onClick={() => go(it.tab)} style={{ background: TONE[it.tone].bg, color: TONE[it.tone].dd }}>
              <b>{it.title}</b><span>{it.text}</span><span className="arrow">›</span>
            </button>
          ))}
        </div>
      </Section>
      <div className="rec-grid2">
        <Section title="Time in range, by day" hint="Glucose tab"><StackedTir days={days} series={series} height={170} /></Section>
        <Section title="Kidney filter path" hint="Kidneys tab">
          <LineChart height={170} yDomain={[Math.floor(Math.min(...kp.egfr) / 10) * 10 - 5, Math.ceil(Math.max(...kp.egfr) / 10) * 10 + 5]} xTickEvery={2} xLabel={(i) => `${kp.month[i] / 12}y`}
            series={[{ name: 'eGFR at current habits', y: kp.egfr, color: '#4f8196' }]} />
        </Section>
      </div>
      <Section title="Liver risk path" hint="Liver tab">
        <LineChart height={150} yDomain={[0, 1]} yFmt={(v) => `${Math.round(v * 100)}%`} xTickEvery={3} xLabel={(i) => `${i}m`}
          series={[{ name: 'Fat in the liver', y: tl.steatosis, color: '#4d8f6b' }, { name: 'Advanced fibrosis', y: tl.adv_fibrosis, color: '#c4645b' }]} />
      </Section>
    </>
  )
}

function GlucoseTab({ d, series, days }) {
  const pattern = useMemo(() => agp(series), [series])
  const meals = useMemo(() => mealResponses(series), [series])
  const labels = days.map((x) => dayLabel(series, x.idx, { weekday: 'short' }).slice(0, 3))
  const f = d.now.forecast
  return (
    <>
      <Section title="Forecast from the latest reading" hint={fmtDT(d.now.time.replace('+00:00', 'Z'), 0)} tone="peach">
        <div className="rec-kpis">
          <Kpi label="Glucose now" value={Math.round(d.now.glucose)} sub="mg/dL" tone="lav" />
          {f.map((x) => <Kpi key={x.minutes} label={`In ${x.minutes} min`} value={Math.round(x.median)} sub={`80% range ${Math.round(x.lo)}-${Math.round(x.hi)}`} tone="sky" />)}
          <Kpi label="High within 2 h" value={pct(d.now.p_hyper_2h)} sub="chance of above 180" tone={d.now.p_hyper_2h > 0.6 ? 'rose' : 'mint'} />
          <Kpi label="Low within 2 h" value={pct(d.now.p_hypo_2h)} sub="chance of below 70" tone={d.now.p_hypo_2h > 0.3 ? 'rose' : 'mint'} />
        </div>
        <Evidence real>Glucose forecaster validated on real CGMacros subjects (error 12.6 / 21.1 / 28.2 mg/dL at 30 / 60 / 120 min), with calibrated 80% ranges.</Evidence>
      </Section>
      <Section title="Full glucose history" hint={`${series.glucose.length.toLocaleString()} readings, every 5 minutes`}>
        <CgmChart series={series} />
        <div className="note">Red dots mark readings below 70 mg/dL. Healthy range 70-180 is shaded.</div>
      </Section>
      <Section title="Time in range, day by day"><StackedTir days={days} series={series} /></Section>
      <Section title="A typical day" hint="ambulatory glucose profile"><AgpChart agp={pattern} />
        <div className="note">The line is the middle value at each time of day across all days; the shaded bands show how much it varies. A wide band means unpredictable days.</div>
      </Section>
      <Section title="Daily record">
        <DataTable head={['Day', 'In range', 'Above', 'Below', 'Mean', 'CV', 'Min - max', 'Steps', 'Carbs (g)', 'Meals', 'Sleep', 'Low min']}
          rows={days.map((x) => [
            <b key="d">{dayLabel(series, x.idx)}{x.partial ? '*' : ''}</b>,
            <span key="t" style={{ color: x.tir >= 0.7 ? 'var(--mint-dd)' : x.tir < 0.4 ? 'var(--rose-dd)' : 'var(--butter-dd)', fontWeight: 800 }}>{pct(x.tir)}</span>,
            pct(x.tar), pct(x.tbr, 1), Math.round(x.mean), `${x.cv.toFixed(0)}%`, `${Math.round(x.min)}-${Math.round(x.max)}`, Math.round(x.steps).toLocaleString(), Math.round(x.carbs), x.meals, `${x.sleep.toFixed(1)} h`, x.lowMin || '-',
          ])} />
        <div className="note">* the latest day is partial (up to the most recent reading).</div>
      </Section>
      <div className="rec-grid2">
        <Section title="Steps a day"><Bars values={days.map((x) => x.steps)} labels={labels} color="#4f8196" goal={6000} fmt={(v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : Math.round(v))} /></Section>
        <Section title="Carbohydrate a day (g)"><Bars values={days.map((x) => x.carbs)} labels={labels} color="#E9A23B" goal={220} /></Section>
        <Section title="Sleep (hours)"><Bars values={days.map((x) => x.sleep)} labels={labels} color="#0F6E68" goal={7} fmt={(v) => v.toFixed(1)} /></Section>
        <Section title="Mean glucose (mg/dL)"><Bars values={days.map((x) => x.mean)} labels={labels} color="#d9894a" goal={154} /></Section>
      </div>
      <Section title="How glucose responds to meals" hint="3 hours after each logged meal">
        <DataTable head={['Meal', 'Meals logged', 'Avg carbs', 'Avg rise', 'Avg peak', 'Time to peak']}
          rows={meals.groups.map((g) => [<b key="n">{g.name}</b>, g.n, `${Math.round(g.carbs)} g`, `+${Math.round(g.rise)} mg/dL`, `${Math.round(g.peak)} mg/dL`, `${Math.round(g.mins)} min`])} />
        <h3 style={{ margin: '14px 0 6px' }}>Five highest peaks</h3>
        <DataTable head={['When', 'Carbs', 'Glucose at meal', 'Peak', 'Rise']}
          rows={meals.worst.map((e) => [dayLabel(series, e.i + series.t0, { weekday: 'short', day: 'numeric' }) + ` ${String(Math.floor(e.hour)).padStart(2, '0')}:${String(Math.round((e.hour % 1) * 60)).padStart(2, '0')}`, `${Math.round(e.carbs)} g`, Math.round(e.base), <b key="p">{Math.round(e.peak)}</b>, `+${Math.round(e.rise)}`])} />
      </Section>
    </>
  )
}

function LiverTab({ d }) {
  const tl = d.liver.timeline
  const lab = d.profile.labs
  const cl = d.profile.clinic
  const sex = d.profile.sex
  const m = d.metrics
  const load = [
    ['Time above 180 mg/dL', pct(m.tar), 'reference 25%', 2.0 * (m.tar - 0.25)],
    ['Glucose variability (CV)', `${m.gv_cv.toFixed(0)}%`, 'reference 28%', 0.04 * (m.gv_cv - 28)],
    ['Steps a day', Math.round(m.steps_per_day).toLocaleString(), 'reference 5,000', -0.12 * (m.steps_per_day - 5000) / 1000],
  ]
  const rows = [
    ['ALT', lab.alt, 'U/L', 'up to 40', labFlag('alt', lab.alt, sex)], ['AST', lab.ast, 'U/L', 'up to 40', labFlag('ast', lab.ast, sex)],
    ['Platelets', lab.platelets, 'x10^3/uL', '150 - 400', labFlag('platelets', lab.platelets, sex)], ['Triglycerides', lab.triglycerides, 'mg/dL', 'below 150', labFlag('triglycerides', lab.triglycerides, sex)],
    ['HDL', lab.hdl, 'mg/dL', sex === 'F' ? 'above 50' : 'above 40', labFlag('hdl', lab.hdl, sex)], ['FIB-4', lab.fib4, '', 'below 1.3', labFlag('fib4', lab.fib4, sex)],
    ['FibroScan stiffness', cl.liver_stiffness_kpa, 'kPa', 'below 8', labFlag('stiffness', cl.liver_stiffness_kpa, sex)], ['Liver fat (imaging)', cl.liver_fat_pct, '%', 'below 5.5', labFlag('fat', cl.liver_fat_pct, sex)],
  ]
  return (
    <>
      <div className="rec-kpis">
        <Kpi label="Fat in the liver, now" value={pct(tl.steatosis[0])} sub="from labs (real-data model)" tone="butter" />
        <Kpi label="At 12 months" value={pct(tl.steatosis.at(-1))} sub="at current habits" tone={tl.steatosis.at(-1) > 0.6 ? 'rose' : 'butter'} />
        <Kpi label="Advanced fibrosis, now" value={pct(tl.adv_fibrosis[0], 1)} sub="stiffness 8 kPa or more" tone="butter" />
        <Kpi label="At 12 months" value={pct(tl.adv_fibrosis.at(-1), 1)} sub="at current habits" tone={tl.adv_fibrosis.at(-1) > 0.2 ? 'rose' : 'butter'} />
      </div>
      <Section title="12-month projection" hint="steady habits assumed" tone="butter">
        <LineChart height={210} yDomain={[0, 1]} yFmt={(v) => `${Math.round(v * 100)}%`} xTickEvery={1} xLabel={(i) => `${i}m`}
          series={[{ name: 'Fat in the liver', y: tl.steatosis, color: '#4d8f6b' }, { name: 'Advanced fibrosis', y: tl.adv_fibrosis, color: '#c4645b' }]} />
        <Evidence>The starting point comes from a model validated on real NHANES FibroScan data. The drift over the year comes from the glucose-habit inputs below, with a 90-day lag; its coefficients are editable assumptions.</Evidence>
      </Section>
      <Section title="Liver labs and measurements">
        <DataTable head={['Test', 'Result', 'Reference', 'Flag']} rows={rows.map(([n, v, u, ref, f]) => [<b key="n">{n}</b>, `${v} ${u}`, ref, <Flag key="f" f={f} />])} />
      </Section>
      <div className="rec-grid2">
        <Section title="What drives the fat risk"><Drivers items={d.explain?.steatosis} title="Largest influences on this patient's estimate" /></Section>
        <Section title="What drives the fibrosis risk"><Drivers items={d.explain?.adv_fibrosis} title="Largest influences on this patient's estimate" /></Section>
      </div>
      <Section title="Glucose habits feeding the 12-month drift" hint={`net shift ${tl.load_shift_logodds >= 0 ? '+' : ''}${tl.load_shift_logodds.toFixed(2)} log-odds`}>
        <Contrib items={load.map(([label, value, ref, contrib]) => ({ label, value: `${value} (${ref})`, contrib }))} unitNote="Positive values push liver risk up, negative values pull it down. These are simulation assumptions, not fitted outcomes." />
      </Section>
    </>
  )
}

function EyesTab({ d }) {
  const f = eyeFactors(d.profile, d.metrics, d.eye.grade)
  const total = f.reduce((a, x) => a + x.contrib, -3.6)
  return (
    <>
      <div className="rec-kpis">
        <Kpi label="Retinopathy grade" value={DR[d.eye.grade]} sub={`grade ${d.eye.grade} of 4 at last exam`} tone={d.eye.grade >= 2 ? 'rose' : d.eye.grade === 1 ? 'butter' : 'mint'} />
        <Kpi label="2-year progression" value={pct(d.eye.progression_2y)} sub="chance of at least one grade worse" tone={d.eye.progression_2y > 0.4 ? 'rose' : d.eye.progression_2y > 0.2 ? 'butter' : 'mint'} />
        <Kpi label="HbA1c" value={`${d.profile.hba1c}%`} sub="target below 7%" tone={labFlag('hba1c', d.profile.hba1c).tone} />
        <Kpi label="Blood pressure" value={`${d.profile.sbp.toFixed(0)}/${d.profile.dbp.toFixed(0)}`} sub="mmHg" tone={labFlag('bp', d.profile.sbp).tone} />
      </div>
      <Section title="Retina photo and where the model looked" tone="rose">
        <div className="rec-grid2">
          <figure style={{ margin: 0 }}><img className="rimg" src={`/eye-img/grade${d.eye.grade}.jpg`} alt={`Example fundus photo, grade ${d.eye.grade}`} /><figcaption>Example fundus photo of grade {d.eye.grade}</figcaption></figure>
          <figure style={{ margin: 0 }}><img className="rimg" src={`/eye-img/grade${d.eye.grade}_cam.jpg`} alt="Grad-CAM heatmap" /><figcaption>Grad-CAM: warm colours show the regions that drove the grade</figcaption></figure>
        </div>
        <Evidence real>The grader is validated on real images (APTOS held-out kappa 0.89; Indian IDRiD test 0.71 after fine-tuning). The photos here are representative IDRiD images (CC BY 4.0) of the recorded grade, because the patients are synthetic.</Evidence>
      </Section>
      <Section title="What drives the 2-year progression risk" hint={`sum of terms ${total >= 0 ? '+' : ''}${total.toFixed(2)} log-odds`}>
        <Contrib items={f} unitNote="Contributions in log-odds relative to a reference patient (HbA1c 7%, BP 120, 50% in range). Directions follow DCCT and UKPDS findings; the sizes are assumptions, so this is a simulation." />
      </Section>
    </>
  )
}

function KidneyTab({ d }) {
  const kp = d.kidney.projection
  const lab = d.profile.labs
  const comp = kidneySlope(d.profile, d.metrics)
  const slopeSum = comp.reduce((a, x) => a + x.contrib, 0)
  const flat = (v) => kp.egfr.map(() => v)
  return (
    <>
      <div className="rec-kpis">
        <Kpi label="eGFR now" value={lab.egfr.toFixed(0)} sub={`stage ${egfrStage(lab.egfr)}`} tone={lab.egfr < 60 ? 'rose' : lab.egfr < 90 ? 'butter' : 'mint'} />
        <Kpi label="In 5 years" value={kp.egfr.at(-1).toFixed(0)} sub={`${kp.slope_per_year.toFixed(1)} a year at current habits`} tone={kp.egfr.at(-1) < 60 ? 'rose' : 'butter'} />
        <Kpi label="Reaches 60" value={lab.egfr < 60 ? 'Already below' : `~${kp.years_to_egfr60} y`} sub="at the current rate" tone={lab.egfr < 60 || kp.years_to_egfr60 < 5 ? 'rose' : 'mint'} />
        <Kpi label="Urine albumin / creatinine" value={`${lab.uacr_mg_g.toFixed(0)}`} sub={labFlag('uacr', lab.uacr_mg_g).text} tone={labFlag('uacr', lab.uacr_mg_g).tone} />
        <Kpi label="Albuminuria risk" value={pct(kp.albuminuria[0])} sub={`${pct(kp.albuminuria.at(-1))} at 12 months`} tone={kp.albuminuria.at(-1) > 0.5 ? 'rose' : 'butter'} />
      </div>
      <Section title="eGFR path over 5 years" hint="current habits" tone="sky">
        <LineChart height={220} yDomain={[Math.min(25, Math.floor(Math.min(...kp.egfr) / 10) * 10 - 5), Math.ceil(Math.max(...kp.egfr, 90) / 10) * 10 + 5]} xTickEvery={2} xLabel={(i) => `${kp.month[i] / 12}y`}
          series={[{ name: 'eGFR at current habits', y: kp.egfr, color: '#4f8196' }, { name: 'Stage G3 boundary (60)', y: flat(60), color: '#d9894a', dash: '5 5' }, { name: 'Stage G4 boundary (30)', y: flat(30), color: '#c4645b', dash: '5 5' }]} />
        <Evidence>A straight-line decline at a patient-specific slope. The slope components are literature-informed assumptions, shown below; they are not fitted to outcome data.</Evidence>
      </Section>
      <div className="rec-grid2">
        <Section title="Albuminuria risk, next 12 months"><LineChart height={190} yDomain={[0, 1]} yFmt={(v) => `${Math.round(v * 100)}%`} xTickEvery={3} xLabel={(i) => `${i}m`}
          series={[{ name: 'Chance of albuminuria', y: kp.albuminuria, color: '#4f8196' }]} /></Section>
        <Section title="Why this slope" hint={`${slopeSum.toFixed(1)} mL/min per year`}>
          <Contrib items={comp} unitNote="Each term adds to the yearly eGFR decline (mL/min/1.73m2 per year)." />
        </Section>
      </div>
      <div className="rec-grid2">
        <Section title="What drives the albuminuria risk"><Drivers items={d.explain?.albuminuria} title="Largest influences on this patient's estimate" /></Section>
        <Section title="What drives the reduced-eGFR risk"><Drivers items={d.explain?.low_egfr} title="Largest influences on this patient's estimate" /></Section>
      </div>
      <Evidence real>Albuminuria and reduced-eGFR risks come from a model validated on real NHANES data (AUROC 0.76 and 0.85). It only slightly outperforms a simple age, BP and HbA1c baseline.</Evidence>
    </>
  )
}

function AlertsTab({ d, series }) {
  const list = [...d.alerts].reverse()
  const perDay = {}
  d.alerts.forEach((a) => { const k = Math.floor(a.t / 288); perDay[k] = (perDay[k] || 0) + 1 })
  const keys = Object.keys(perDay).map(Number).sort((a, b) => a - b)
  return (
    <>
      <div className="rec-kpis">
        <Kpi label="Alerts, last 3 days" value={d.alerts.length} sub="high and low glucose" tone={d.alerts.length > 8 ? 'butter' : 'mint'} />
        <Kpi label="Low-glucose alerts" value={d.alerts.filter((a) => a.type === 'hypo').length} sub="below 70 expected" tone={d.alerts.some((a) => a.type === 'hypo') ? 'rose' : 'mint'} />
        <Kpi label="High-glucose alerts" value={d.alerts.filter((a) => a.type === 'hyper').length} sub="above 180 expected" tone="peach" />
      </div>
      {keys.length > 0 && <Section title="Alerts per day"><Bars values={keys.map((k) => perDay[k])} labels={keys.map((k) => dayLabel(series, k * 288 + series.t0, { weekday: 'short' }).slice(0, 3))} color="#d9894a" fmt={(v) => Math.round(v)} /></Section>}
      <Section title="Alert history" hint="most recent first">
        <DataTable head={['When', 'Alert', 'Probability', 'Why it fired']}
          rows={list.map((a) => [fmtDT(series.start, a.t - series.t0), <b key="t">{a.type === 'hypo' ? 'Low glucose expected' : 'High glucose expected'}</b>, pct(a.prob), explain(series, a.t - series.t0)])} />
        <div className="note">Alerts fire at about one false alert per patient-day on held-out data. Only the last 3 days of alerts are kept in this demo.</div>
      </Section>
    </>
  )
}

function ProfileTab({ d }) {
  const p = d.profile
  const lab = p.labs
  const cl = p.clinic
  const kv = (rows) => <div className="kvgrid">{rows.map(([k, v]) => <div key={k}><span className="muted">{k}</span><b>{v}</b></div>)}</div>
  return (
    <>
      <Section title="Patient">
        {kv([['Name', p.name], ['Record ID', p.id], ['Age', `${p.age} years`], ['Sex', p.sex === 'F' ? 'Female' : 'Male'], ['BMI', p.bmi], ['Waist', `${p.waist_cm} cm`],
          ['Diabetes duration', `${p.duration_yrs} years`], ['HbA1c', `${p.hba1c}%`], ['Blood pressure', `${p.sbp.toFixed(0)}/${p.dbp.toFixed(0)} mmHg`]])}
      </Section>
      <div className="rec-grid2">
        <Section title="Treatment">{kv([['Metformin', p.metformin ? 'Yes' : 'No'], ['Insulin or sulfonylurea', p.on_insulin_or_su ? 'Yes (low-glucose risk)' : 'No']])}</Section>
        <Section title="Genetic markers">{kv([['PNPLA3 G alleles (liver fat)', `${p.pnpla3_g_alleles} of 2`], ['TCF7L2 T alleles (type 2 diabetes)', `${p.tcf7l2_t_alleles} of 2`]])}</Section>
      </div>
      <Section title="Laboratory panel">
        <DataTable head={['Test', 'Result', 'Flag']} rows={[
          ['HbA1c', `${p.hba1c} %`, <Flag key="a" f={labFlag('hba1c', p.hba1c)} />], ['ALT', `${lab.alt} U/L`, <Flag key="b" f={labFlag('alt', lab.alt)} />], ['AST', `${lab.ast} U/L`, <Flag key="c" f={labFlag('ast', lab.ast)} />],
          ['Platelets', `${lab.platelets} x10^3/uL`, <Flag key="d" f={labFlag('platelets', lab.platelets)} />], ['Triglycerides', `${lab.triglycerides} mg/dL`, <Flag key="e" f={labFlag('triglycerides', lab.triglycerides)} />],
          ['HDL', `${lab.hdl} mg/dL`, <Flag key="f" f={labFlag('hdl', lab.hdl, p.sex)} />], ['FIB-4', lab.fib4, <Flag key="g" f={labFlag('fib4', lab.fib4)} />],
          ['eGFR', `${lab.egfr.toFixed(0)} mL/min/1.73m2 (${egfrStage(lab.egfr)})`, <Flag key="h" f={labFlag('egfr', lab.egfr)} />], ['Urine albumin/creatinine', `${lab.uacr_mg_g.toFixed(0)} mg/g`, <Flag key="i" f={labFlag('uacr', lab.uacr_mg_g)} />],
        ]} />
      </Section>
      <Section title="Clinic measurements">
        {kv([['FibroScan stiffness', `${cl.liver_stiffness_kpa} kPa`], ['Liver fat', `${cl.liver_fat_pct}%`], ['Retinopathy grade', `${cl.dr_grade} (${DR[cl.dr_grade]})`], ['Chronic kidney disease', cl.ckd ? 'Yes (eGFR below 60 or albuminuria)' : 'No']])}
        <div className="note">All values are synthetic. They come from the cohort generator, not from real people.</div>
      </Section>
      <Section title="Why this patient is prioritised" hint={`score ${d.summary.score}`}>
        <div className="row wrap" style={{ gap: 8 }}>
          <span className="chip" style={{ background: TONE[tierTone(d.summary.tier)].bg, color: TONE[tierTone(d.summary.tier)].dd }}>{d.summary.tier} priority</span>
          {d.summary.reasons.map((r) => <span key={r} className="chip">{r}</span>)}
        </div>
      </Section>
    </>
  )
}

/* ------------------------------------------------------------------ drawer */
export default function Record({ d, pid, tab, setTab, onClose, changes }) {
  const [series, setSeries] = useState(null)
  useEffect(() => { setSeries(null); getSeries(pid, 14).then(setSeries) }, [pid])
  useEffect(() => {
    const k = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', k)
    document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', k); document.body.style.overflow = '' }
  }, [onClose])
  const days = useMemo(() => (series ? dailyStats(series) : []), [series])
  const p = d.profile
  const t = TONE[tierTone(d.summary.tier)]
  return (
    <div className="rec-back" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <aside className="rec" role="dialog" aria-label={`Full record for ${p.name}`}>
        <header className="rec-h">
          <div className="row" style={{ gap: 14 }}>
            <div className="av" style={{ background: t.bg, color: t.dd, fontSize: 18, width: 52, height: 52 }}>{(p.name || '?').split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase()}</div>
            <div>
              <h1 style={{ fontSize: 24, letterSpacing: '-.02em' }}>{p.name}</h1>
              <div className="muted" style={{ fontSize: 13, fontWeight: 600 }}>Age {p.age} · {p.sex === 'F' ? 'Female' : 'Male'} · ID {p.id} · T2D {p.duration_yrs} y · HbA1c {p.hba1c}%</div>
            </div>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <a className="btn sm" style={{ textDecoration: 'none' }} href={`/api/patients/${p.id}/report.pdf`} target="_blank" rel="noreferrer">📄 PDF summary</a>
            <button className="btn sm go" onClick={onClose}>Close ✕</button>
          </div>
        </header>
        <nav className="rec-tabs" role="tablist">
          {TABS.map(([k, label]) => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{label}</button>)}
        </nav>
        <div className="rec-body">
          {!series ? <div className="muted" style={{ padding: 30 }}>Loading the full history…</div> : (
            tab === 'catchup' ? <CatchUp d={d} days={days} series={series} go={setTab} changes={changes} pid={pid} /> :
            tab === 'overview' ? <Overview d={d} days={days} series={series} go={setTab} changes={changes} /> :
            tab === 'reports' ? <ReportsTab pid={pid} d={d} /> :
            tab === 'glucose' ? <GlucoseTab d={d} series={series} days={days} /> :
            tab === 'liver' ? <LiverTab d={d} /> :
            tab === 'eyes' ? <EyesTab d={d} /> :
            tab === 'kidneys' ? <KidneyTab d={d} /> :
            tab === 'alerts' ? <AlertsTab d={d} series={series} /> : <ProfileTab d={d} />
          )}
        </div>
      </aside>
    </div>
  )
}
