import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

import messages  # noqa: E402

NOW = "2026-01-14 21:50:00"


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(messages, "MSG_DIR", tmp_path)


def test_urgent_needs_an_action_and_advice_does_not():
    with pytest.raises(ValueError):
        messages.send(7, "urgent", "", "Please come in", None, NOW)
    m = messages.send(7, "urgent", "", "Please come in today", "come_to_clinic", NOW)
    assert m["action"] == "come_to_clinic" and m["title"] and not m["read"]
    a = messages.send(7, "advice", "Walk more", "Walk 20 minutes after dinner", "go_to_er", NOW)
    assert a["action"] is None                         # advice never carries an urgent action
    with pytest.raises(ValueError):
        messages.send(7, "advice", "", "   ", None, NOW)
    with pytest.raises(ValueError):
        messages.send(7, "shout", "", "x", None, NOW)


def test_messages_are_listed_newest_first_and_can_be_acknowledged():
    a = messages.send(7, "advice", "", "first", None, "2026-01-14 09:00:00")
    b = messages.send(7, "advice", "", "second", None, "2026-01-14 10:00:00")
    assert [m["id"] for m in messages.list_messages(7)] == [b["id"], a["id"]]
    assert messages.mark_read(7, a["id"])["read"] is True
    assert [m["read"] for m in messages.list_messages(7)] == [False, True]
    assert messages.mark_read(7, "nope") is None


def test_text_is_cleaned():
    m = messages.send(7, "advice", "<b>Hi</b>", "<script>alert(1)</script> walk", None, NOW)
    assert "<" not in m["title"] and "<" not in m["body"]


def test_prescription_validation():
    with pytest.raises(ValueError):
        messages.prescribe(7, [], "", NOW)                                          # nothing to send
    with pytest.raises(ValueError):
        messages.prescribe(7, [{"medicine": "Metformin", "action": "change_dose", "dose": ""}], "", NOW)
    with pytest.raises(ValueError):
        messages.prescribe(7, [{"medicine": "Metformin", "action": "explode", "dose": "x"}], "", NOW)
    ok = messages.prescribe(7, [{"medicine": "Metformin", "action": "stop"}], "Stop it, kidneys", NOW)
    assert ok["kind"] == "prescription" and ok["changes"][0]["action"] == "stop"


def test_prescriptions_change_the_medicine_list_in_order():
    meds = [{"name": "Metformin", "dose": "500 mg twice a day", "since": "At diagnosis", "start_days": 9999, "purpose": "Lowers sugar"},
            {"name": "Glimepiride", "dose": "2 mg", "since": "Years", "start_days": 9999, "purpose": "Lowers sugar"}]
    rx1 = messages.prescribe(7, [{"medicine": "glimepiride", "action": "stop"}, {"medicine": "Sitagliptin", "action": "start", "dose": "100 mg once a day"},
                                 {"medicine": "Metformin", "action": "change_dose", "dose": "1000 mg twice a day", "instructions": "With meals"}], "", "2026-01-14 09:00:00")
    out = {m["name"]: m for m in messages.apply_to_medicines(meds, [rx1])}
    assert set(out) == {"Metformin", "Sitagliptin"}                               # glimepiride stopped, sitagliptin started
    assert out["Metformin"]["dose"] == "1000 mg twice a day" and out["Sitagliptin"]["since"] == "2026-01-14"
    assert meds[1]["name"] == "Glimepiride"                                      # the original list is not modified


def test_consultation_note_becomes_a_report_entry():
    rx = messages.prescribe(7, [{"medicine": "Metformin", "action": "stop", "instructions": "Kidney function is low"}], "Reviewed your data", NOW)
    r = messages.report_for(7, rx, 0)
    assert r["code"] == "RX" and r["status"] == "Prescribed" and r["new"] and r["virtual"]
    assert "Stop Metformin" in r["plain"] and r["meds"][0]["name"] == "Metformin"


class FakeTranslator:
    """Stands in for the voice service: returns the input JSON with a language tag, or fails for Telugu."""
    def __init__(self):
        self.calls = []

    def chat(self, messages, max_tokens=260):
        import json
        lang = messages[0]["content"].split("into ")[1].split(".")[0]
        self.calls.append(lang)
        if lang == "Telugu":
            raise RuntimeError("service down")
        d = json.loads(messages[1]["content"])
        return "Sure! " + json.dumps({"title": f"[{lang}] {d['title']}", "body": f"[{lang}] {d['body']}", "instructions": [f"[{lang}] {x}" for x in d["instructions"]]})


def test_translation_keeps_going_when_one_language_fails():
    m = messages.send(7, "advice", "Walk", "Walk after dinner", None, NOW)
    tr = messages.translate_message(FakeTranslator(), m)
    assert set(tr) == {"hi", "kn"}                                                # telugu failed, the others are kept
    assert tr["hi"]["title"] == "[Hindi] Walk" and tr["kn"]["body"] == "[Kannada] Walk after dinner"


def test_prescription_instructions_are_translated_in_order():
    rx = messages.prescribe(7, [{"medicine": "A", "action": "start", "dose": "1 mg", "instructions": "after food"},
                                {"medicine": "B", "action": "stop", "instructions": ""}], "Note", NOW)
    tr = messages.translate_message(FakeTranslator(), rx, langs=("hi",))
    assert tr["hi"]["instructions"] == ["[Hindi] after food", ""] and tr["hi"]["body"] == "[Hindi] Note"


def test_bad_replies_are_ignored_and_translations_are_stored():
    class Bad:
        def chat(self, *a, **k):
            return "I cannot do that"
    m = messages.send(7, "advice", "Hi", "Hello", None, NOW)
    assert messages.translate_message(Bad(), m) == {}
    messages.set_translations(7, m["id"], {"hi": {"title": "x", "body": "y", "instructions": []}})
    assert messages.list_messages(7)[0]["translations"]["hi"]["body"] == "y"


def test_known_templates_are_not_sent_for_translation():
    assert messages.send(7, "advice", "t", "b", None, NOW, template="a_walk")["template"] == "a_walk"
    assert messages.send(7, "advice", "t", "b", None, NOW, template="made_up")["template"] is None


def test_older_messages_matching_a_template_are_adopted():
    title, body = messages.TEMPLATE_TEXT["u_clinic"]
    m = messages.send(7, "urgent", title, body, "come_to_clinic", NOW)
    assert m["template"] is None
    messages.adopt_templates(7)
    got = messages.list_messages(7)[0]
    assert got["template"] == "u_clinic" and not messages.needs_translation(got)
    other = messages.send(7, "advice", "Rest", "Rest tomorrow", None, NOW)
    assert messages.needs_translation(other)


def test_a_patient_message_stays_unanswered_until_the_doctor_replies():
    assert messages.pending_from_patient(7) == []
    m = messages.from_patient(7, "I felt dizzy this morning", NOW)
    assert m["kind"] == "patient" and not m["read"]
    assert [x["id"] for x in messages.pending_from_patient(7)] == [m["id"]]
    assert messages.answer_patient(7) == 1
    assert messages.pending_from_patient(7) == [] and messages.answer_patient(7) == 0
    with pytest.raises(ValueError):
        messages.from_patient(7, "   ", NOW)


def test_patient_messages_are_never_sent_for_translation():
    m = messages.from_patient(7, "Can I take my tablet after lunch?", NOW)
    assert not messages.needs_translation(m)


def test_demo_seed_is_replaced_not_duplicated_and_keeps_real_messages():
    real = messages.from_patient(7, "a real question", NOW)
    messages.replace_seed(7, "seeded one", NOW)
    messages.replace_seed(7, "seeded two", NOW)
    bodies = sorted(m["body"] for m in messages.list_messages(7))
    assert bodies == ["a real question", "seeded two"] and real["id"] in {m["id"] for m in messages.list_messages(7)}


def test_the_daily_limit_counts_real_messages_only():
    messages.replace_seed(7, "seeded", "2026-01-14 08:00:00")
    for i in range(3):
        messages.from_patient(7, f"question {i}", f"2026-01-14 1{i}:00:00")
    messages.from_patient(7, "yesterday", "2026-01-13 10:00:00")
    assert messages.sent_today(7, "2026-01-14") == 3          # the seed and yesterday's message do not count
    assert messages.sent_today(7, "2026-01-15") == 0


def test_what_the_helper_said_is_kept_and_unknown_values_are_ignored():
    assert messages.from_patient(7, "dizzy", NOW, check="emergency")["check"] == "emergency"
    assert messages.from_patient(7, "hello", NOW, check="made-up")["check"] == "none"
