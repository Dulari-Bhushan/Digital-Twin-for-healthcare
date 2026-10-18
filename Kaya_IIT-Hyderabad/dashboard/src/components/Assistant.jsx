import { useEffect, useRef, useState } from 'react'
import { askAssistant, browserCanListen, canRecord, listenWithBrowser, speak, startListening, stopSpeaking } from '../voice'

export function SpeakButton({ text, lang, voice, label }) {
  const [on, setOn] = useState(false)
  const toggle = async () => {
    if (on) { stopSpeaking(); setOn(false); return }
    setOn(true)
    await speak(text, lang, voice.enabled)
    setTimeout(() => setOn(false), Math.min(12000, 800 + text.length * 70))
  }
  return <button className={`speak ${on ? 'on' : ''}`} onClick={toggle} aria-label={label} title={label}>{on ? '■' : '🔊'}</button>
}

/** Chat sheet inside the phone: type or speak, hear the answer, and navigate by voice. */
export default function Assistant({ t, lang, pid, tab, voice, onNavigate, onClose }) {
  const [msgs, setMsgs] = useState([{ role: 'assistant', content: t('ask_hello') }])
  const [text, setText] = useState('')
  const [phase, setPhase] = useState('idle') // idle | recording | transcribing | thinking
  const [err, setErr] = useState('')
  const rec = useRef(null)
  const end = useRef(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, phase])
  useEffect(() => () => stopSpeaking(), [])

  const send = async (message, spoken = false) => {
    const m = message.trim()
    if (!m) return
    setErr('')
    setText('')
    const history = msgs.slice(1).map(({ role, content }) => ({ role, content }))
    setMsgs((x) => [...x, { role: 'user', content: m }])
    setPhase('thinking')
    try {
      const r = await askAssistant({ pid, lang, message: m, history, tab })
      setMsgs((x) => [...x, { role: 'assistant', content: r.reply, kind: r.kind }])
      if (spoken || r.kind === 'emergency') speak(r.reply, lang, voice.enabled)
      if (r.action && r.action.type === 'navigate') setTimeout(() => { onNavigate(r.action.tab); onClose() }, spoken ? 1800 : 600)
    } catch (e) {
      setMsgs((x) => [...x, { role: 'assistant', content: t('ask_error') }])
    }
    setPhase('idle')
  }

  const mic = async () => {
    setErr('')
    if (phase === 'recording') {
      setPhase('transcribing')
      try {
        const { transcript } = await rec.current.stop()
        setPhase('idle')
        if (transcript) await send(transcript, true)
        else setErr(t('ask_nothing'))
      } catch (e) { setPhase('idle'); setErr(t('ask_mic_error')) }
      return
    }
    stopSpeaking()
    try {
      if (voice.enabled && canRecord()) {
        rec.current = await startListening(lang, true)
        setPhase('recording')
      } else if (browserCanListen()) {
        setPhase('recording')
        const { transcript } = await listenWithBrowser(lang)
        setPhase('idle')
        await send(transcript, true)
      } else {
        setErr(t('ask_no_mic'))
      }
    } catch (e) { setPhase('idle'); setErr(t('ask_mic_denied')) }
  }

  const canMic = (voice.enabled && canRecord()) || browserCanListen()
  const chips = ['ask_s1', 'ask_s2', 'ask_s3', 'ask_s4']
  return (
    <div className="sheet" role="dialog" aria-label={t('ask_title')}>
      <div className="sheet-h">
        <div style={{ fontWeight: 800, fontSize: 18 }}>💬 {t('ask_title')}</div>
        <button className="x" onClick={() => { stopSpeaking(); onClose() }} aria-label={t('close')}>✕</button>
      </div>
      <div className="chat">
        {msgs.map((m, i) => (
          <div key={i} className={`bubble-row ${m.role}`}>
            <div className={`msg ${m.role} ${m.kind === 'emergency' ? 'alert' : ''}`}>
              {m.content}
              {m.role === 'assistant' && <SpeakButton text={m.content} lang={lang} voice={voice} label={t('read_aloud')} />}
            </div>
          </div>
        ))}
        {phase === 'thinking' && <div className="bubble-row assistant"><div className="msg assistant muted">{t('ask_thinking')}</div></div>}
        <div ref={end} />
      </div>
      {msgs.length < 3 && (
        <div className="chips">{chips.map((k) => <button key={k} onClick={() => send(t(k))}>{t(k)}</button>)}</div>
      )}
      {err && <div className="note" style={{ margin: '0 16px 6px', color: 'var(--rose-dd)' }}>{err}</div>}
      <div className="composer">
        {canMic && (
          <button className={`mic ${phase === 'recording' ? 'rec' : ''}`} onClick={mic} disabled={phase === 'thinking' || phase === 'transcribing'} aria-label={phase === 'recording' ? t('ask_stop') : t('ask_speak')}>
            {phase === 'recording' ? '■' : phase === 'transcribing' ? '…' : '🎤'}
          </button>
        )}
        <input value={phase === 'recording' ? '' : text} onChange={(e) => setText(e.target.value)} placeholder={phase === 'recording' ? t('ask_listening') : t('ask_placeholder')}
          onKeyDown={(e) => { if (e.key === 'Enter') send(text) }} disabled={phase === 'recording'} maxLength={400} aria-label={t('ask_placeholder')} />
        <button className="sendbtn" onClick={() => send(text)} disabled={!text.trim() || phase !== 'idle'} aria-label={t('send')}>➤</button>
      </div>
      <div className="note" style={{ margin: '6px 16px 12px', textAlign: 'center' }}>{t('ask_note')}{voice.enabled ? ' · Sarvam AI' : ''}</div>
    </div>
  )
}
