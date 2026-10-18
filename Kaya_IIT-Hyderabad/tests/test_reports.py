"""Medical-record history and the 'what changed since the last visit' summary."""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))
sys.path.insert(0, str(ROOT / "src" / "whatif"))
sys.path.insert(0, str(ROOT / "src" / "models"))

import reports as rpt  # noqa: E402

DEMO = ROOT / "artifacts" / "demo"
PIDS = [1688, 1636, 62]


def _load(pid):
    a = json.loads((DEMO / f"{pid}.json").read_text())
    a["profile"]["name"] = "Test Patient"
    today = datetime(2026, 1, 1) + timedelta(minutes=5 * a["forecast"]["t"][-1])
    return a, today


@pytest.mark.parametrize("pid", PIDS)
def test_record_is_complete_and_consistent_with_today(pid):
    a, today = _load(pid)
    rec = rpt.build_record(a, today)
    codes = {r["code"] for r in rec["reports"]}
    assert {"LAB", "VIS", "EYE", "LIV", "ECG", "CXR", "FOOT", "CGM"} <= codes
    assert len({r["id"] for r in rec["reports"]}) == len(rec["reports"])
    latest = next(r for r in rec["reports"] if r["code"] == "LAB" and r["days_ago"] == rpt.LAB_DAY)
    row = {x["key"]: x["value"] for s in latest["sections"] for x in s["rows"]}
    assert row["hba1c"] == round(a["profile"]["hba1c"], 1)
    assert row["uacr"] == round(a["profile"]["labs"]["uacr_mg_g"])
    fundus = next(r for r in rec["reports"] if r["code"] == "EYE" and r["days_ago"] == rpt.LAB_DAY)
    assert fundus["grade"] == a["profile"]["clinic"]["dr_grade"]


def test_record_is_deterministic():
    a, today = _load(1688)
    one = [r["id"] for r in rpt.build_record(a, today)["reports"]]
    two = [r["id"] for r in rpt.build_record(a, today)["reports"]]
    assert one == two
    assert rpt.build_record(a, today)["trends"] == rpt.build_record(a, today)["trends"]


def test_demo_stories_differ():
    ra, ta = _load(1688)
    rb, tb = _load(1636)
    ca = rpt.build_changes(ra, rpt.build_record(ra, ta))
    cb = rpt.build_changes(rb, rpt.build_record(rb, tb))
    assert ca["counts"]["worse"] >= 3 and cb["counts"]["worse"] == 0
    assert any("Retinopathy progressed" in x["text"] for x in ca["attention"])
    assert any("Night-time low" in x["text"] for x in ca["attention"])
    assert "Dapagliflozin" in " ".join(ca["new_medicines"])


def test_changes_directions_and_scopes():
    a, today = _load(1688)
    ch = rpt.build_changes(a, rpt.build_record(a, today))
    by = {i["key"]: i for i in ch["items"]}
    assert by["uacr"]["direction"] == "worse" and by["uacr"]["delta"] > 0
    assert by["tir"]["scope"] == "week" and by["hba1c"]["scope"] == "visit"
    assert sum(ch["counts"].values()) == sum(1 for i in ch["items"] if i["scope"] == "visit")


def test_creatinine_inverse_roundtrip():
    scr = rpt._creatinine(60.0, 50, "M")
    assert 1.1 < scr < 1.6


def test_report_pdf_is_valid():
    a, today = _load(1688)
    rec = rpt.build_record(a, today)
    for r in rec["reports"][:6]:
        assert rpt.report_pdf(a["profile"], r)[:4] == b"%PDF"
