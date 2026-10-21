import { TONE } from '../ui'

const STEPS_GOAL = 6000

/** The next things worth doing, most important first. Pure rules from the patient's own data, never medicine dosing. */
export function nextActions({ status, at, hour, stepsToday, onRiskyDrugs, today }) {
  const out = []
  if (status.k === 'st_low') out.push({ key: 'snack', e: '🍎', text: 'st_low_nudge', reason: 'r_low', vars: { v: Math.round(at.glucose) }, prio: 100, log: ['action', 'snack'] })
  if (status.k === 'st_high' && today.walk_min < 15) out.push({ key: 'walk_high', e: '🚶', text: 'st_high_nudge', reason: 'r_high', vars: { v: Math.round(at.forecast[2].median) }, prio: 90, log: ['walk', 15] })
  if (hour >= 21 && onRiskyDrugs && !today.actions.includes('bed_check')) out.push({ key: 'bed_check', e: '🌙', text: 'a_bed', reason: 'r_bed', vars: {}, prio: 70, log: ['action', 'bed_check'] })
  if (hour >= 18 && !today.med_evening) out.push({ key: 'meds_pm', e: '💊', text: 'a_meds_pm', reason: 'r_meds', vars: {}, prio: 65, log: ['med', 'evening'] })
  if (hour >= 6 && hour < 12 && !today.med_morning) out.push({ key: 'meds_am', e: '💊', text: 'a_meds_am', reason: 'r_meds', vars: {}, prio: 64, log: ['med', 'morning'] })
  if (hour >= 7 && hour < 21 && today.walk_min === 0 && stepsToday < 3000) out.push({ key: 'walk', e: '👟', text: 'a_walk', reason: 'r_walk', vars: { n: Math.round(stepsToday).toLocaleString() }, prio: 50, log: ['walk', 10] })
  out.sort((a, b) => b.prio - a.prio)
  return out
}

export function NowCard({ t, status, at, hour, stepsToday, onRiskyDrugs, log, logIt }) {
  const today = log ? log.today : { med_morning: false, med_evening: false, walk_min: 0, actions: [] }
  const list = nextActions({ status, at, hour, stepsToday, onRiskyDrugs, today })
  const tn = TONE.butter
  if (!list.length) {
    return (
      <div className="p-card" style={{ background: 'var(--mint)' }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--mint-dd)' }}>{t('now_title')}</div>
        <div style={{ fontWeight: 800, fontSize: 19, margin: '6px 0 0', color: 'var(--mint-dd)', lineHeight: 1.3 }}>🎉 {t('all_done')}</div>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--mint-dd)', opacity: 0.85, marginTop: 4 }}>{t(`${status.k}_title`)}</div>
      </div>
    )
  }
  const [main, ...rest] = list
  const done = (a) => logIt(a.log[0], a.log[1])
  return (
    <div className="p-card" style={{ background: tn.bg }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: tn.dd }}>{t('now_title')}</div>
      <div style={{ fontWeight: 800, fontSize: 21, margin: '4px 0 2px', color: tn.dd, lineHeight: 1.3 }}>{main.e} {t(main.text)}</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: tn.dd, opacity: 0.85 }}>{t(main.reason, main.vars)}</div>
      <button className="big-btn" onClick={() => done(main)}>{t('mark_done')}</button>
      {rest.length > 0 && (
        <>
          <div style={{ fontSize: 12, fontWeight: 800, color: tn.dd, margin: '14px 0 6px' }}>{t('also_today')}</div>
          {rest.slice(0, 2).map((a) => (
            <div key={a.key} className="alsorow">
              <span style={{ fontSize: 20 }}>{a.e}</span>
              <span style={{ flex: 1, minWidth: 0 }}><b>{t(a.text)}</b><small>{t(a.reason, a.vars)}</small></span>
              <button className="mini" onClick={() => done(a)}>✓</button>
            </div>
          ))}
        </>
      )}
    </div>
  )
}

export function QuickLog({ t, log, logIt }) {
  if (!log) return null
  const td = log.today
  const faces = [['good', '😊', 'f_good'], ['ok', '😐', 'f_ok'], ['low', '😟', 'f_low']]
  return (
    <div className="p-card" style={{ background: '#f0f5f4' }}>
      <div style={{ fontWeight: 800, fontSize: 16 }}>{t('log_title')}</div>
      <div className="muted" style={{ fontSize: 12, fontWeight: 600, marginBottom: 10 }}>{t('log_sub')}</div>
      <div className="logrow">
        <span className="lbl">💊 {t('log_meds')}</span>
        <span className="opts">
          {[['morning', td.med_morning], ['evening', td.med_evening]].map(([k, on]) => (
            <button key={k} className={`opt ${on ? 'on' : ''}`} onClick={() => logIt(on ? 'med_off' : 'med', k)} aria-pressed={on}>{on ? '✓ ' : ''}{t(k)}</button>
          ))}
        </span>
      </div>
      <div className="logrow">
        <span className="lbl">🚶 {t('log_walk')}</span>
        <span className="opts">{[10, 20, 30].map((m) => <button key={m} className="opt" onClick={() => logIt('walk', m)}>+{m} {t('min')}</button>)}</span>
      </div>
      {td.walk_min > 0 && <div className="note" style={{ margin: '-4px 0 6px', textAlign: 'right' }}>{t('walked_today', { n: td.walk_min })}</div>}
      <div className="logrow">
        <span className="lbl">🙂 {t('log_feel')}</span>
        <span className="opts">{faces.map(([k, e, lab]) => <button key={k} className={`opt face ${td.feel === k ? 'on' : ''}`} title={t(lab)} aria-label={t(lab)} aria-pressed={td.feel === k} onClick={() => logIt('feel', k)}>{e}</button>)}</span>
      </div>
    </div>
  )
}
