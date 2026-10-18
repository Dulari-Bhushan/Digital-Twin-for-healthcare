// Voice helpers for the patient app: speak (TTS), listen (STT) and the assistant call. All Sarvam calls go through
// the Kaya API, so the key never reaches the browser. If voice is not configured we fall back to the browser's own
// speech where it exists.

const LOCALE = { en: 'en-IN', hi: 'hi-IN', te: 'te-IN', kn: 'kn-IN' }
const cache = new Map()
let current = null

export async function getVoiceStatus() {
  try {
    const r = await fetch('/api/voice/status')
    return r.ok ? await r.json() : { enabled: false }
  } catch (e) {
    return { enabled: false }
  }
}

export function stopSpeaking() {
  if (current) { current.pause(); current = null }
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}

/** Read text aloud. Uses the Sarvam voice when available and the browser voice otherwise. Resolves when playback starts. */
export async function speak(text, lang, enabled) {
  stopSpeaking()
  if (enabled) {
    try {
      const key = `${lang}|${text}`
      let url = cache.get(key)
      if (!url) {
        const r = await fetch('/api/voice/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: text.slice(0, 600), lang }) })
        if (!r.ok) throw new Error(String(r.status))
        url = URL.createObjectURL(await r.blob())
        cache.set(key, url)
      }
      const a = new Audio(url)
      current = a
      await a.play()
      return true
    } catch (e) { /* fall through to the browser voice */ }
  }
  if ('speechSynthesis' in window) {
    const u = new SpeechSynthesisUtterance(text)
    u.lang = LOCALE[lang] || 'en-IN'
    window.speechSynthesis.speak(u)
    return true
  }
  return false
}

function writeWav(pcm, rate) {
  const buf = new ArrayBuffer(44 + pcm.length * 2)
  const v = new DataView(buf)
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)) }
  w(0, 'RIFF'); v.setUint32(4, 36 + pcm.length * 2, true); w(8, 'WAVE'); w(12, 'fmt ')
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true)
  v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, 'data'); v.setUint32(40, pcm.length * 2, true)
  for (let i = 0; i < pcm.length; i++) {
    const s = Math.max(-1, Math.min(1, pcm[i]))
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return new Blob([buf], { type: 'audio/wav' })
}

/** Convert whatever the browser recorded (webm, mp4, ogg) to 16 kHz mono WAV, which the speech API accepts. */
async function toWav16k(blob) {
  const Ctx = window.AudioContext || window.webkitAudioContext
  const ctx = new Ctx()
  const audio = await ctx.decodeAudioData(await blob.arrayBuffer())
  ctx.close()
  const off = new OfflineAudioContext(1, Math.max(1, Math.ceil(audio.duration * 16000)), 16000)
  const src = off.createBufferSource()
  src.buffer = audio
  src.connect(off.destination)
  src.start()
  return writeWav((await off.startRendering()).getChannelData(0), 16000)
}

export const canRecord = () => !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder)

/** Start recording. Returns { stop(): Promise<{ transcript }> }. */
export async function startListening(lang, serverVoice) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const rec = new MediaRecorder(stream)
  const chunks = []
  rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
  rec.start()
  return {
    stop: () => new Promise((resolve, reject) => {
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        try {
          const wav = await toWav16k(new Blob(chunks, { type: rec.mimeType }))
          const r = await fetch('/api/voice/stt', { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: wav })
          if (!r.ok) throw new Error(String(r.status))
          resolve(await r.json())
        } catch (e) { reject(e) }
      }
      rec.stop()
    }),
    serverVoice,
    lang,
  }
}

/** Browser speech recognition fallback (Chrome and Edge). Resolves with { transcript }. */
export function listenWithBrowser(lang) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  return new Promise((resolve, reject) => {
    if (!SR) return reject(new Error('unsupported'))
    const r = new SR()
    r.lang = LOCALE[lang] || 'en-IN'
    r.onresult = (e) => resolve({ transcript: e.results[0][0].transcript })
    r.onerror = (e) => reject(new Error(e.error))
    r.start()
  })
}
export const browserCanListen = () => !!(window.SpeechRecognition || window.webkitSpeechRecognition)

export async function askAssistant({ pid, lang, message, history, tab }) {
  const r = await fetch('/api/assistant', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pid, lang, message, history, tab }) })
  if (!r.ok) throw new Error(String(r.status))
  return r.json()
}
