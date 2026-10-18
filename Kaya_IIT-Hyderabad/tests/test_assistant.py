import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))
import assistant as asst  # noqa: E402

fastapi_testclient = pytest.importorskip("fastapi.testclient")
import app as kaya  # noqa: E402


@pytest.mark.parametrize("msg,lang", [
    ("I have chest pain", "en"), ("I feel like I will faint", "en"), ("मेरे सीने में दर्द है", "hi"), ("मुझे चक्कर आ रहे हैं", "hi"),
    ("నాకు ఛాతీ నొప్పి ఉంది", "te"), ("ಎದೆ ನೋವು ಇದೆ", "kn"),
])
def test_emergency_words_never_reach_the_model(msg, lang):
    r = asst.classify(msg, lang)
    assert r["kind"] == "emergency" and "108" in r["reply"]


@pytest.mark.parametrize("msg,lang", [
    ("how much insulin should I take", "en"), ("can I stop my metformin tablet", "en"), ("मुझे कितनी खुराक लेनी चाहिए", "hi"),
    ("ఇన్సులిన్ మోతాదు ఎంత", "te"), ("ಔಷಧ ಬದಲಿಸಲೇ", "kn"),
])
def test_medicine_questions_are_deflected_to_the_doctor(msg, lang):
    assert asst.classify(msg, lang)["kind"] == "medicine"


@pytest.mark.parametrize("msg,lang,tab", [
    ("show my kidneys", "en", 2), ("open insights", "en", 1), ("take me to try a change", "en", 3), ("मेरा शरीर दिखाओ", "hi", 2), ("ನನ್ನ ಕಿಡ್ನಿ ತೋರಿಸಿ", "kn", 2),
])
def test_navigation_is_handled_without_the_model(msg, lang, tab):
    r = asst.classify(msg, lang)
    assert r["kind"] == "navigate" and r["tab"] == tab


def test_ordinary_questions_go_to_the_model():
    assert asst.classify("what does time in range mean?", "en")["kind"] == "chat"
    assert asst.classify("मेरी शुगर क्यों ज़्यादा है?", "hi")["kind"] == "chat"


def test_reply_filter_blocks_dose_advice_but_allows_glucose_units():
    ok, blocked = asst.clean_reply("Your sugar is between 70 and 180 mg/dL most of the day.", "en")
    assert not blocked and "mg/dL" in ok
    bad, blocked = asst.clean_reply("You could take 10 units of insulin before dinner.", "en")
    assert blocked and "doctor" in bad.lower()
    bad, blocked = asst.clean_reply("Try to reduce your insulin a little.", "en")
    assert blocked
    clean, _ = asst.clean_reply("**Hello** _there_", "en")
    assert "*" not in clean and "_" not in clean


class FakeVoice:
    def __init__(self):
        self.calls = []

    def chat(self, messages, max_tokens=260):
        self.calls.append(messages)
        return "Time in range is the share of the day your sugar is healthy."

    def tts(self, text, lang):
        return b"RIFFfakewav"

    def stt(self, audio, filename="x.wav", content_type="audio/wav"):
        return {"transcript": "show my body", "language_code": "en-IN"}


@pytest.fixture()
def client():
    with fastapi_testclient.TestClient(kaya.app) as c:
        saved = kaya.VOICE.get("client")
        yield c
        kaya.VOICE["client"] = saved
        kaya.HITS.clear()


def test_assistant_endpoint_only_calls_the_model_for_ordinary_questions(client):
    fake = FakeVoice()
    kaya.VOICE["client"] = fake
    pid = client.get("/api/patients").json()[0]["id"]
    r = client.post("/api/assistant", json={"pid": pid, "lang": "en", "message": "what does time in range mean?"}).json()
    assert r["kind"] == "chat" and len(fake.calls) == 1
    system = fake.calls[0][0]["content"]
    assert "PATIENT FACTS" in system and "never give medicine names" in system
    for msg in ("I have chest pain", "how much insulin do I take", "show my body"):
        client.post("/api/assistant", json={"pid": pid, "lang": "en", "message": msg})
    assert len(fake.calls) == 1, "emergency, medicine and navigation messages must not reach the model"


def test_assistant_degrades_gracefully_without_a_key_and_voice_endpoints_report_it(client):
    kaya.VOICE["client"] = None
    pid = client.get("/api/patients").json()[0]["id"]
    r = client.post("/api/assistant", json={"pid": pid, "lang": "hi", "message": "what does time in range mean?"}).json()
    assert r["kind"] == "unavailable"
    assert client.get("/api/voice/status").json()["enabled"] is False
    assert client.post("/api/voice/tts", json={"text": "hi", "lang": "en"}).status_code == 503


def test_tts_and_stt_endpoints_with_a_fake_provider(client):
    kaya.VOICE["client"] = FakeVoice()
    r = client.post("/api/voice/tts", json={"text": "hello", "lang": "en"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
    s = client.post("/api/voice/stt", content=b"RIFF....", headers={"content-type": "audio/wav"})
    assert s.json()["transcript"] == "show my body"
    assert client.post("/api/voice/tts", json={"text": "", "lang": "en"}).status_code == 422
