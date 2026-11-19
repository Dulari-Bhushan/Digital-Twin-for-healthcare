import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

fastapi_testclient = pytest.importorskip("fastapi.testclient")
import app as kaya  # noqa: E402
import reports as rpt  # noqa: E402
import screening  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    kaya.HITS.clear()
    yield


@pytest.fixture(scope="module")
def client():
    with fastapi_testclient.TestClient(kaya.app) as c:
        yield c


def test_schedule_is_deterministic_and_priya_is_up_to_date():
    assert screening.schedule(302) == screening.schedule(302)
    assert screening.RECENT == rpt.LAB_DAY
    for pid in screening.UP_TO_DATE:
        assert screening.overdue(pid) == []
    assert screening.overdue(1688) == ["Eye exam (retina)", "Foot exam"]          # Rajesh is the one-patient demo
    # the cohort has a mix: some patients have gaps, some none
    lates = [bool(screening.overdue(pid)) for pid in range(100, 200)]
    assert 0.2 < sum(lates) / len(lates) < 0.8


def test_status_endpoint_for_a_patient_with_gaps(client):
    sc = client.get("/api/patients/302/screening").json()          # Brijmohan Yadav: eye and foot exams overdue
    state = {t["key"]: t["state"] for t in sc["tests"]}
    assert state["eye"] == "overdue" and state["foot"] == "overdue"
    assert state["uacr"] == "ok" and state["egfr"] == "ok"
    assert sc["overdue"] == 2 and "2 yearly tests overdue" in sc["headline"]
    eye = next(t for t in sc["tests"] if t["key"] == "eye")
    assert eye["days_left"] < 0 and eye["can_refer"] is True
    assert datetime.strptime(eye["last_done"], "%Y-%m-%d") < datetime.strptime(sc["today"], "%Y-%m-%d")


def test_priya_has_nothing_overdue_and_rajesh_has_two_gaps(client):
    sc = client.get("/api/patients/1636/screening").json()
    assert sc["overdue"] == 0 and sc["headline"] == "All yearly tests are up to date"
    sc = client.get("/api/patients/1688/screening").json()
    state = {t["key"]: t["state"] for t in sc["tests"]}
    assert state == {"eye": "overdue", "uacr": "ok", "egfr": "ok", "foot": "overdue"}
    assert sc["overdue"] == 2


def test_rajesh_keeps_his_retinopathy_story_with_old_photos(client):
    rec = client.get("/api/patients/1688/reports").json()
    eyes = sorted([r for r in rec["reports"] if r["code"] == "EYE"], key=lambda r: -r["days_ago"])
    assert [r["days_ago"] for r in eyes] == list(screening.eye_photo_days(1688)) and len(eyes) == 2     # oldest first
    assert [r["grade"] for r in eyes] == [1, 2]                          # mild (oldest), then moderate
    ch = client.get("/api/patients/1688/changes").json()
    dr = next(i for i in ch["items"] if i["key"] == "dr")
    assert dr["direction"] == "worse"
    assert any("Retinopathy progressed" in a["text"] for a in ch["attention"])
    assert "uacr" in [i["key"] for i in ch["items"]]                     # his kidney story is untouched


def test_the_record_agrees_with_the_tracker(client):
    # eye exam gap: no recent retina photo, and the oldest is the one the tracker reports
    rec = client.get("/api/patients/302/reports").json()
    eye_days = [r["days_ago"] for r in rec["reports"] if r["code"] == "EYE"]
    assert eye_days == [screening.schedule(302)["eye"]]
    assert [r["days_ago"] for r in rec["reports"] if r["code"] == "FOOT"] == [screening.schedule(302)["foot"]]
    # urine albumin gap: only the oldest lab panel has the test, and the trend shows gaps, not invented values
    rec = client.get("/api/patients/496/reports").json()
    has = {r["days_ago"]: any(x["key"] == "uacr" for s in r["sections"] for x in s["rows"]) for r in rec["reports"] if r["code"] == "LAB"}
    assert has[548] is True and not any(v for d, v in has.items() if d < 548)
    assert rec["trends"]["uacr"][0] is not None and all(v is None for v in rec["trends"]["uacr"][1:])
    ch = client.get("/api/patients/496/changes").json()
    assert "uacr" not in [i["key"] for i in ch["items"]]               # nothing recent to compare
    # a patient who is up to date keeps the full history
    rec = client.get("/api/patients/1636/reports").json()
    assert len([r for r in rec["reports"] if r["code"] == "EYE"]) == 2
    assert all(v is not None for v in rec["trends"]["uacr"])


def test_triage_flags_overdue_screening(client):
    ps = {p["id"]: p for p in client.get("/api/patients").json()}
    keys = [t["key"] for t in ps[302]["triage"]["triggers"]]
    assert "screening" in keys
    assert "screening" in [t["key"] for t in ps[1688]["triage"]["triggers"]]
    assert "screening" not in [t["key"] for t in ps[1636]["triage"]["triggers"]]


def test_a_reminder_or_referral_is_shown_against_the_test(client, tmp_path, monkeypatch):
    monkeypatch.setattr(kaya.msgs, "MSG_DIR", tmp_path)
    client.post("/api/patients/302/messages", json={"kind": "advice", "title": "Referral: Eye exam (retina)",
                                                      "body": "I am referring you to an eye specialist.", "translate": False})
    client.post("/api/patients/302/messages", json={"kind": "advice", "title": "Screening reminder: Foot exam",
                                                      "body": "Your foot exam is overdue.", "translate": False})
    sc = client.get("/api/patients/302/screening").json()
    follow = {t["key"]: t["follow_up"] for t in sc["tests"]}
    assert follow["eye"]["kind"] == "referral" and follow["foot"]["kind"] == "reminder"
    assert follow["uacr"] is None
    assert sc["followed_up"] == 2 and "2 with a reminder or referral sent" in sc["headline"]
