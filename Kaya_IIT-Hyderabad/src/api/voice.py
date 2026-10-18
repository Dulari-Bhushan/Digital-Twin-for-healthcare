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

    def _post(self, path: str, **kw) -> httpx.Response:
        try:
            r = httpx.post(f"{BASE}{path}", headers=self.h, timeout=self.timeout, **kw)
        except httpx.HTTPError as e:  # network problems must not leak the key or crash the API
            raise VoiceError(f"voice service unreachable ({type(e).__name__})") from None
        if r.status_code != 200:
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
