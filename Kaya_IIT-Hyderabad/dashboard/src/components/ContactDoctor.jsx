import { useState } from 'react'
import { checkContact, sendPatientMessage } from '../api'

/** Writing to the doctor goes through the helper first: small questions are answered here, the doctor only gets what needs them.
 *  The patient can always insist, because a real problem must never be blocked. */
export default function ContactDoctor({ t, lang, pid, inbox, onClose }) {
  const [text, setText] = useState('')
  const [step, setStep] = useState('write')     // write | checking | result | sent
  const [res, setRes] = useState(null)          // { verdict: self | doctor | emergency | unsure, reason, reply }
  const [insist, setInsist] = useState(false)
  const [err, setErr] = useState(null)
  const mine = inbox.items.filter((m) => m.kind === 'patient').slice(0, 3)

  const check = () => {
    setStep('checking'); setErr(null); setInsist(false)
    checkContact(pid, { message: text, lang })
      .then((r) => { setRes(r); setStep('result') })
      .catch(() => { setRes({ verdict: 'unsure', reason: 'unavailable', reply: '' }); setStep('result') })
  }
  const send = (checkLabel) => {
    setErr(null)
    sendPatientMessage(pid, text, checkLabel)
      .then(() => { setStep('sent'); inbox.reload() })
      .catch((e) => setErr(e.message === 'limit' ? t('cd_limit') : e.message))
  }

  const v = res && res.verdict
  const canSend = v === 'doctor' || v === 'unsure' || v === 'emergency' || insist
  const label = v === 'emergency' ? 'emergency' : v === 'doctor' ? 'doctor' : v === 'self' ? 'self_insisted' : 'unsure'

  return (
    <div className="sheet" role="dialog" aria-label={t('cd_title')}>
      <div className="sheet-h">
        <div style={{ fontWeight: 800, fontSize: 18 }}>✉ {t('cd_title')}</div>
        <button className="x" onClick={onClose} aria-label={t('close')}>✕</button>
      </div>
      <div className="cd-body">
        {step === 'sent' ? (
          <div className="cd-ok">✓ {t('ask_dr_sent')}<button className="cd-primary" onClick={onClose}>{t('close')}</button></div>
        ) : (
          <>
            <p className="cd-notice">{t('cd_notice')}</p>
            <textarea rows={4} maxLength={600} value={text} placeholder={t('ask_dr_ph')} aria-label={t('cd_title')}
              disabled={step === 'checking'} onChange={(e) => { setText(e.target.value); if (step === 'result') { setStep('write'); setRes(null) } }} />
            {step !== 'result' && <button className="cd-primary" disabled={!text.trim() || step === 'checking'} onClick={check}>{step === 'checking' ? t('cd_checking') : t('cd_check')}</button>}

            {step === 'result' && res && (
              <div className={`cd-res ${v}`}>
                {v === 'emergency' && <><b>🚨 {res.reply}</b></>}
                {v === 'self' && <><div className="cd-h">💬 {t('cd_self_h')}</div><p>{res.reply}</p></>}
                {v === 'doctor' && <><div className="cd-h">👩‍⚕️ {t('cd_doc_h')}</div><p>{res.reason === 'medicine' ? t('cd_doc_med') : res.reply}</p></>}
                {v === 'unsure' && <p>{t('cd_unsure')}</p>}
                {canSend ? (
                  <button className="cd-primary" onClick={() => send(insist && v === 'self' ? 'self_insisted' : label)}>{v === 'emergency' ? t('cd_emerg_send') : t('ask_dr_send')}</button>
                ) : (
                  <div className="cd-two">
                    <button className="cd-primary" onClick={onClose}>{t('cd_thanks')}</button>
                    <button className="cd-link" onClick={() => setInsist(true)}>{t('cd_more')}</button>
                  </div>
                )}
                {err && <div className="cd-err">{err}</div>}
              </div>
            )}
          </>
        )}
        {mine.length > 0 && step !== 'sent' && (
          <div className="ask-past">
            <small>{t('ask_dr_yours')}</small>
            {mine.map((m) => <div key={m.id}><p>{m.body}</p><small>{m.created.slice(0, 16)} · {m.read ? t('ask_dr_seen') : t('ask_dr_wait')}</small></div>)}
          </div>
        )}
      </div>
    </div>
  )
}
