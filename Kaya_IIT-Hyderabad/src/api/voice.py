"""Sarvam AI client for speech-to-text, text-to-speech and chat. The API key stays on the server."""
from __future__ import annotations

import os
from collections import OrderedDict
from pathlib import Path

import httpx

BASE = "https://api.sarvam.ai"
STT_MODEL, TTS_MODEL, CHAT_MODEL = "saaras:v4", "bulbul:v4-flash", "sarvam-105b-conversations"
TTS_SPEAKER = "simran_en_customer"
LANG_CODES = {"en": "en-IN", "hi": "hi-IN", "te": "te-IN", "kn": "kn-IN"}
LANG_NAMES = {"en": "English", "hi": "Hindi", "te": "Telugu", "kn": "Kannada"}


class VoiceError(Exception):
    pass


def load_key(root: Path) -> str | None:
    """SARVAM_API_KEY from the environment, or from a .env file in the project root (never committed)."""
    key = os.environ.get("SARVAM_API_KEY")
    if key:
        return key.strip()
    env = root / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("SARVAM_API_KEY=") and line.split("=", 1)[1].strip():
                return line.split("=", 1)[1].strip()
    return None


class SarvamClient:
    def __init__(self, key: str, timeout: float = 25.0):
        self.h = {"api-subscription-key": key}
        self.timeout = timeout
        self._tts_cache: OrderedDict[tuple[str, str], bytes] = OrderedDict()

    def _post(self, path: str, ok: tuple = (200,), **kw) -> httpx.Response:
        try:
            r = httpx.post(f"{BASE}{path}", headers=self.h, timeout=self.timeout, **kw)
        except httpx.HTTPError as e:  # network problems must not leak the key or crash the API
            raise VoiceError(f"voice service unreachable ({type(e).__name__})") from None
        if r.status_code not in ok:
            raise VoiceError(f"voice service returned {r.status_code}")
        return r

    def tts(self, text: str, lang: str) -> bytes:
        """WAV audio for `text`. Repeated phrases (the app's fixed texts) are served from a small cache."""
        k = (lang, text)
        if k in self._tts_cache:
            self._tts_cache.move_to_end(k)
            return self._tts_cache[k]
        import base64

        r = self._post("/text-to-speech", json={"text": text, "language_code": LANG_CODES.get(lang, "en-IN"),
                                                 "model": TTS_MODEL, "speaker": TTS_SPEAKER})
        audios = r.json().get("audios") or []
        if not audios:
            raise VoiceError("no audio returned")
        wav = base64.b64decode(audios[0])
        self._tts_cache[k] = wav
        if len(self._tts_cache) > 200:
            self._tts_cache.popitem(last=False)
        return wav

    def stt(self, audio: bytes, filename: str = "speech.wav", content_type: str = "audio/wav") -> dict:
        r = self._post("/speech-to-text", data={"model": STT_MODEL, "mode": "transcribe"}, files={"file": (filename, audio, content_type)})
        j = r.json()
        return {"transcript": (j.get("transcript") or "").strip(), "language_code": j.get("language_code")}

    def chat(self, messages: list[dict], max_tokens: int = 260) -> str:
        r = self._post("/v1/chat/completions", json={"model": CHAT_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.3})
        content = ((r.json().get("choices") or [{}])[0].get("message") or {}).get("content")
        if not content:
            raise VoiceError("empty reply")
        return content.strip()


    def digitise(self, data: bytes, filename: str, media: str, lang: str = "en-IN", wait_s: float = 90.0) -> str:
        """Text of a PDF or image via Sarvam Document AI (job, poll, download, unzip). Raises VoiceError on any problem."""
        import io
        import time
        import zipfile

        r = self._post("/doc-ai/v1/job/digitise", ok=(200, 201, 202), files={"file": (filename, data, media)}, data={"language": lang, "output_format": "md"})
        job = r.json().get("job_id")
        if not job:
            raise VoiceError("document service returned no job")
        end = time.time() + wait_s
        state = "pending"
        while time.time() < end:
            try:
                st = httpx.get(f"{BASE}/doc-ai/v1/job/{job}/status", headers=self.h, timeout=20).json()
            except (httpx.HTTPError, ValueError):
                raise VoiceError("document service unreachable") from None
            state = st.get("status", "pending")
            if state in ("completed", "partially_completed"):
                break
            if state in ("failed", "rejected"):
                raise VoiceError(f"document could not be read ({state})")
            time.sleep(1.5)
        else:
            raise VoiceError("document reading timed out")
        try:
            link = httpx.get(f"{BASE}/doc-ai/v1/job/{job}/download-url", headers=self.h, timeout=20).json().get("url")
            if not link:
                raise VoiceError("no download link")
            blob = httpx.get(link, timeout=60, follow_redirects=True).content          # pre-signed link: the API key is not sent
            z = zipfile.ZipFile(io.BytesIO(blob))
        except (httpx.HTTPError, ValueError, zipfile.BadZipFile):
            raise VoiceError("could not download the result") from None
        names = sorted(n for n in z.namelist() if n.lower().endswith((".md", ".markdown", ".txt")) and not n.startswith("metadata/"))
        if not names:
            raise VoiceError("no text in the result")
        return "\n\n".join(z.read(n).decode("utf-8", "replace") for n in names)
