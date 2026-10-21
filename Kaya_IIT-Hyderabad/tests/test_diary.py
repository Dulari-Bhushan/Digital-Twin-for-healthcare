"""Patient diary: seeded history, validation, adding and removing entries, and the 'what to do now' inputs."""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

import diary  # noqa: E402


def _load(pid):
    a = json.loads((ROOT / "artifacts" / "demo" / f"{pid}.json").read_text())
    return a, datetime(2026, 1, 1) + timedelta(minutes=5 * a["forecast"]["t"][-1])


def test_seed_is_deterministic_and_covers_14_days():
    a, today = _load(1688)
    one, two = diary.seed(a, today), diary.seed(a, today)
    assert one == two
    assert len({e["date"] for e in one}) == 14
    assert all(diary.valid(e["kind"], e["value"]) for e in one)


def test_demo_patients_differ_in_adherence():
    out = {}
    for pid in (1688, 1636):
        a, today = _load(pid)
        out[pid] = diary.summary(diary.seed(a, today), today)
    assert out[1636]["evening"]["taken"] / out[1636]["evening"]["of"] > 0.8
    assert out[1688]["evening"]["taken"] / out[1688]["evening"]["of"] < 0.7
    assert out[1636]["walk_days"] > out[1688]["walk_days"]
    assert out[1688]["feel"]["low"] > out[1636]["feel"]["low"]


def test_today_starts_without_evening_medicines():
    a, today = _load(1688)
    st = diary.today_state(diary.seed(a, today), today)
    assert st["med_evening"] is False and st["feel"] is None


@pytest.mark.parametrize("kind,value,ok", [("med", "evening", True), ("med", "noon", False), ("walk", 20, True), ("walk", 500, False),
                                           ("walk", True, False), ("feel", "good", True), ("action", "bed_check", True), ("action", "x", False), ("zzz", 1, False)])
def test_validation(kind, value, ok):
    assert diary.valid(kind, value) is ok


def test_add_replace_and_remove(tmp_path, monkeypatch):
    monkeypatch.setattr(diary, "LOG_DIR", tmp_path)
    a, today = _load(1688)
    diary.add(1688, today, "med", "evening")
    diary.add(1688, today, "med", "evening")           # logging the same slot twice keeps one entry
    diary.add(1688, today, "feel", "ok")
    e = diary.add(1688, today, "feel", "low")          # a new feeling replaces the earlier one
    items = diary.entries(a, today)
    st = diary.today_state(items, today)
    assert st["med_evening"] and st["feel"] == "low"
    assert sum(1 for x in items if x["source"] == "patient") == 2
    assert diary.remove(1688, e["id"]) and not diary.remove(1688, e["id"])


def test_attention_flags_poor_adherence():
    a, today = _load(1688)
    msgs = [x["text"] for x in diary.attention(diary.summary(diary.seed(a, today), today))]
    assert any("Evening medicines" in m for m in msgs)
    a, today = _load(1636)
    assert diary.attention(diary.summary(diary.seed(a, today), today)) == []


def test_a_medicine_can_be_unticked_even_when_it_was_pre_filled(tmp_path, monkeypatch):
    monkeypatch.setattr(diary, "LOG_DIR", tmp_path)
    items = [{"id": "s1", "date": "2026-01-14", "time": "08:10", "kind": "med", "value": "morning", "note": "", "source": "seed"}]
    stored = {"id": "p1", "date": "2026-01-14", "time": "09:00", "kind": "med_off", "value": "morning", "note": "", "source": "patient"}
    assert diary.effective(items + [stored]) == []                                  # the pre-filled morning dose is cancelled
    again = {**stored, "id": "p2", "kind": "med"}
    assert [x["id"] for x in diary.effective(items + [stored, again])] == ["p2"]    # ticking again brings it back
    assert diary.valid("med_off", "evening") and not diary.valid("med_off", "noon")


def test_logging_a_slot_again_replaces_the_marker(tmp_path, monkeypatch):
    from datetime import datetime
    monkeypatch.setattr(diary, "LOG_DIR", tmp_path)
    today = datetime(2026, 1, 14, 21, 0)
    diary.add(9, today, "med", "evening")
    diary.add(9, today, "med_off", "evening")
    assert [x["kind"] for x in diary._load_patient(9)] == ["med_off"]
    diary.add(9, today, "med", "evening")
    assert [x["kind"] for x in diary._load_patient(9)] == ["med"]


def test_demo_reset_clears_patient_entries(tmp_path, monkeypatch):
    from datetime import datetime
    monkeypatch.setattr(diary, "LOG_DIR", tmp_path)
    diary.add(9, datetime(2026, 1, 14, 21, 0), "walk", 30)
    assert diary.reset_patient_logs() == 1 and diary._load_patient(9) == []
