import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

import assistant  # noqa: E402
import messages  # noqa: E402
import voice  # noqa: E402


class FakeClient:
    """Stands in for the Sarvam client: 'translates' by tagging the text, or returns a fixed English sentence."""
    def __init__(self, english=None, fail=False):
        self.english, self.fail, self.calls = english, fail, []

    def translate(self, text, src, tgt):
        self.calls.append((text, src, tgt))
        if self.fail:
            raise voice.VoiceError("down")
        return self.english if (tgt == "en" and self.english) else f"[{tgt}] {text}"


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(messages, "MSG_DIR", tmp_path)


def test_every_language_has_the_fixed_safety_messages():
    assert len(assistant.LANGS) == 23 and "ta" in assistant.LANGS and "sat" in assistant.LANGS
    for lang in assistant.LANGS:
        for table in (assistant.EMERGENCY_MSG, assistant.MEDICINE_MSG, assistant.FALLBACK_MSG, assistant.OPEN_MSG, assistant.TAB_LABEL):
            assert table[lang]
        assert "108" in assistant.EMERGENCY_MSG[lang]                      # the emergency number survives translation


def test_the_voice_covers_fewer_languages_than_translation():
    assert voice.TTS_LANGS < set(voice.LANG_CODES) and "ta" in voice.TTS_LANGS and "sat" not in voice.TTS_LANGS
    assert voice.LANG_CODES["brx"] == "brx-IN"


def test_a_doctors_message_is_translated_on_demand_and_kept():
    m = messages.send(7, "advice", "Walk more", "Walk 20 minutes after dinner", None, "2026-01-14 09:00:00")
    assert messages.needs_language(m, "ta")
    tr = messages.translate_to(FakeClient(), m, "ta")
    assert tr["title"] == "[ta] Walk more" and tr["body"] == "[ta] Walk 20 minutes after dinner"
    messages.add_translation(7, m["id"], "ta", tr)
    saved = messages.list_messages(7)[0]
    assert not messages.needs_language(saved, "ta") and messages.needs_language(saved, "bn")
    messages.set_translations(7, m["id"], {"hi": {"title": "x", "body": "y", "instructions": []}})      # the older Hindi/Telugu/Kannada path keeps the rest
    assert set(messages.list_messages(7)[0]["translations"]) == {"ta", "hi"}


def test_a_failed_translation_leaves_the_original_and_template_texts_are_skipped():
    m = messages.send(7, "advice", "Hi", "Take care", None, "2026-01-14 09:00:00")
    assert messages.translate_to(FakeClient(fail=True), m, "ta") is None
    t = messages.send(7, "advice", "Please walk after meals", messages.TEMPLATE_TEXT["a_walk"][1], None, "2026-01-14 10:00:00", template="a_walk")
    assert not messages.needs_language(t, "ta")                             # quick-start texts are translated inside the app


def test_chest_pain_written_in_another_language_is_caught_through_english(monkeypatch):
    import app
    monkeypatch.setitem(app.VOICE, "client", FakeClient(english="I have chest pain"))
    english = app._english_for_safety("நெஞ்சு வலி", "ta")
    assert assistant.classify(english, "en")["kind"] == "emergency"
    assert app._english_for_safety("chest pain", "en") == "chest pain"       # covered languages are not sent anywhere
    monkeypatch.setitem(app.VOICE, "client", FakeClient(fail=True))
    assert app._english_for_safety("நெஞ்சு வலி", "ta") == "நெஞ்சு வலி"        # if translation fails the text is used as it is
