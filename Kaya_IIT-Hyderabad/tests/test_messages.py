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
