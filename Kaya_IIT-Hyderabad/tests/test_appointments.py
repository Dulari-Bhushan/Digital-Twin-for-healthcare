import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

fastapi_testclient = pytest.importorskip("fastapi.testclient")
import app as kaya  # noqa: E402
import appointments as appt  # noqa: E402

NOW = datetime(2026, 1, 14, 21, 50)          # the demo's clock: a Wednesday evening, so the next open day is Thursday 15 January
THU, FRI, MON = "2026-01-15", "2026-01-16", "2026-01-19"


@pytest.fixture(autouse=True)
def calendar(tmp_path, monkeypatch):
    monkeypatch.setattr(appt, "FILE", tmp_path / "appointments.json")
    kaya.HITS.clear()
    yield


@pytest.fixture(scope="module")
def client():
    with fastapi_testclient.TestClient(kaya.app) as c:
        yield c


def names(pid):
    return f"Patient {pid}"


# ---------------------------------------------------------------- the clinic's day
def test_open_days_and_slots():
    slots = appt.day_slots(datetime(2026, 1, 15).date())
    assert slots[0] == "09:00" and slots[-1] == "16:40" and "12:00" not in slots and "13:40" not in slots and len(slots) == 18
    assert appt.day_slots(datetime(2026, 1, 17).date()) == [] and appt.day_slots(datetime(2026, 1, 18).date()) == []     # the weekend is closed
    assert appt.reserved_slots(datetime(2026, 1, 15).date()) == {"11:40", "16:40"}
    assert appt.first_open_day(NOW).isoformat() == THU
    assert appt.first_open_day(datetime(2026, 1, 16, 18, 0)).isoformat() == MON                                             # Friday evening: Monday


def test_availability_hides_a_finished_day_and_marks_reserved_slots():
    av = appt.availability(NOW)
    assert av[0]["date"] == THU and all(d["date"] != "2026-01-14" for d in av)
    assert not any(d["date"] in ("2026-01-17", "2026-01-18") for d in av)
    states = {s["time"]: s["state"] for s in av[0]["slots"]}
    assert states["09:00"] == "free" and states["11:40"] == "reserved" and states["16:40"] == "reserved"


# ---------------------------------------------------------------- requests, holds and cancellations
def test_a_request_holds_the_slot_and_nobody_else_can_take_it():
    a = appt.request(1, f"{THU} 09:00", "routine", "", False, NOW)
    assert a["status"] == "requested" and a["slot"] == f"{THU} 09:00"
    with pytest.raises(appt.ApptError) as e:
        appt.request(2, f"{THU} 09:00", "routine", "", False, NOW)
    assert e.value.code == 409
    assert {s["time"]: s["state"] for s in appt.availability(NOW)[0]["slots"]}["09:00"] == "taken"


def test_patients_cannot_book_reserved_closed_past_or_far_away_slots():
    for slot, why in ((f"{THU} 11:40", "urgent"), ("2026-01-17 10:00", "closed"), ("2026-01-14 10:00", "passed"), ("2026-03-02 10:00", "ahead"),
                      (f"{THU} 09:05", "closed")):
        with pytest.raises(appt.ApptError):
            appt.request(1, slot, "routine", "", False, NOW)


def test_cancelling_frees_the_slot_and_a_late_cancellation_is_recorded():
    a = appt.request(1, f"{THU} 10:00", "routine", "", False, NOW)             # 12 hours away from the demo clock
    out = appt.patient_cancel(1, a["id"], NOW)
    assert out["status"] == "cancelled" and out["late_cancel"] is True
    assert {s["time"]: s["state"] for s in appt.availability(NOW)[0]["slots"]}["10:00"] == "free"
    b = appt.request(1, f"{FRI} 10:00", "routine", "", False, NOW)             # more than 24 hours away
    assert appt.patient_cancel(1, b["id"], NOW)["late_cancel"] is False
    with pytest.raises(appt.ApptError):
        appt.patient_cancel(1, b["id"], NOW)                                  # already closed


def test_a_patient_cannot_cancel_someone_elses_appointment_or_exceed_the_limit():
    a = appt.request(1, f"{FRI} 09:00", "routine", "", False, NOW)
    with pytest.raises(appt.ApptError) as e:
        appt.patient_cancel(2, a["id"], NOW)
    assert e.value.code == 404
    appt.request(1, f"{FRI} 09:20", "routine", "", False, NOW)
    appt.request(1, f"{FRI} 09:40", "routine", "", False, NOW)
    with pytest.raises(appt.ApptError) as e:
        appt.request(1, f"{FRI} 10:00", "routine", "", False, NOW)
    assert e.value.code == 409


def test_an_urgent_request_needs_no_slot_and_waits_at_the_top_of_the_queue():
    appt.request(1, f"{FRI} 09:00", "routine", "", False, NOW)
    u = appt.request(2, None, "other", "dizzy and shaky", True, NOW + timedelta(minutes=5))
    assert u["slot"] is None and u["urgent"] is True
    q = appt.queue(names)
    assert [x["pid"] for x in q] == [2, 1] and appt.summary() == {"pending": 2, "urgent": 1}
    with pytest.raises(appt.ApptError):                                       # reception must choose a time for it
        appt.confirm(u["id"], NOW, "reception")
    out = appt.confirm(u["id"], NOW, "reception", slot=f"{THU} 11:40")        # the reserved urgent slot
    assert out["status"] == "confirmed" and out["slot"] == f"{THU} 11:40"


def test_reception_confirms_declines_and_the_patient_is_told():
    a = appt.request(1, f"{FRI} 09:00", "routine", "", False, NOW)
    appt.confirm(a["id"], NOW, "reception")
    got = appt.for_patient(1, NOW)
    assert got["upcoming"][0]["status"] == "confirmed" and [n["kind"] for n in got["notices"]] == ["confirmed"]
    appt.mark_seen(1, a["id"])
    assert appt.for_patient(1, NOW)["notices"] == []
    b = appt.request(2, f"{FRI} 09:20", "routine", "", False, NOW)
    appt.decline(b["id"], NOW, "reception", "doctor is away that morning")
    assert appt.for_patient(2, NOW)["notices"][0]["reason"] == "doctor is away that morning"
    assert {s["time"]: s["state"] for s in appt.availability(NOW)[1]["slots"]}["09:20"] == "free"      # a declined request frees the slot


def test_reception_can_squeeze_an_urgent_patient_into_a_busy_slot_but_only_on_purpose():
    appt.request(1, f"{THU} 09:00", "routine", "", False, NOW)
    with pytest.raises(appt.ApptError):
        appt.request(2, f"{THU} 09:00", "routine", "", True, NOW, actor="reception", confirmed=True)
    out = appt.request(2, f"{THU} 09:00", "routine", "", True, NOW, actor="reception", confirmed=True, override=True)
    assert out["status"] == "confirmed"
    sched = appt.schedule(NOW, THU, 1, names)["days"][0]["slots"][0]
    assert len(sched["appts"]) == 2


def test_moving_an_appointment_tells_the_patient_and_needs_a_free_slot():
    a = appt.request(1, f"{FRI} 09:00", "routine", "", False, NOW)
    appt.confirm(a["id"], NOW, "reception")
    appt.request(2, f"{FRI} 10:00", "routine", "", False, NOW)
    with pytest.raises(appt.ApptError):
        appt.move(a["id"], f"{FRI} 10:00", NOW, "reception")
    out = appt.move(a["id"], f"{FRI} 10:20", NOW, "reception", "doctor asked to see you later")
    assert out["slot"] == f"{FRI} 10:20"
    n = appt.for_patient(1, NOW)["notices"][-1]
    assert n["kind"] == "moved" and n["old"] == f"{FRI} 09:00" and n["slot"] == f"{FRI} 10:20"


# ---------------------------------------------------------------- the doctor is called away
def _day(pids_slots):
    out = {}
    for pid, slot in pids_slots:
        a = appt.request(pid, slot, "routine", "", False, NOW)
        appt.confirm(a["id"], NOW, "reception")
        out[pid] = a["id"]
    return out


def test_unavailable_moves_the_affected_patients_to_the_next_free_slots_and_tells_them():
    ids = _day([(1, f"{THU} 09:00"), (2, f"{THU} 09:20"), (3, f"{THU} 09:40"), (4, f"{THU} 10:20")])
    plan = appt.plan_unavailable(THU, "09:00", "10:00", "move", NOW, names)
    assert [r["pid"] for r in plan["affected"]] == [1, 2, 3] and plan["unplaced"] == 0
    assert [r["new"] for r in plan["affected"]] == [f"{THU} 10:00", f"{THU} 10:40", f"{THU} 11:00"]      # 10:20 is already someone's
    assert appt.for_patient(1, NOW)["upcoming"][0]["slot"] == f"{THU} 09:00"                              # planning changes nothing
    appt.apply_unavailable(THU, "09:00", "10:00", "move", "emergency operation", NOW, "doctor", names)
    for pid in (1, 2, 3):
        got = appt.for_patient(pid, NOW)
        assert got["upcoming"][0]["slot"] != f"{THU} 09:00" and got["notices"][-1]["kind"] == "moved" and got["notices"][-1]["reason"] == "emergency operation"
    assert appt.for_patient(4, NOW)["notices"][-1]["kind"] == "confirmed"                                # the one outside the window was not touched
    with pytest.raises(appt.ApptError):                                                                   # the window is blocked for new bookings
        appt.request(5, f"{THU} 09:20", "routine", "", False, NOW)
    states = {s["time"]: s["state"] for s in appt.availability(NOW)[0]["slots"]}
    assert states["09:20"] == "blocked"


def test_unavailable_can_cancel_instead_and_a_block_can_be_removed():
    _day([(1, f"{THU} 09:00"), (2, f"{THU} 09:20")])
    out = appt.apply_unavailable(THU, "09:00", "10:00", "cancel", "", NOW, "doctor", names)
    assert all(r["new"] is None for r in out["affected"])
    assert [appt.for_patient(p, NOW)["notices"][-1]["kind"] for p in (1, 2)] == ["cancelled", "cancelled"]
    bid = appt.schedule(NOW, THU, 1, names)["blocks"][0]["id"]
    appt.remove_block(bid)
    assert {s["time"]: s["state"] for s in appt.availability(NOW)[0]["slots"]}["09:20"] == "free"


def test_a_day_with_no_room_moves_people_to_the_next_open_day():
    ids = _day([(i, f"{FRI} {t}") for i, t in enumerate(("14:00", "14:20", "14:40"), start=1)])
    plan = appt.plan_unavailable(FRI, "14:00", "17:00", "move", NOW, names)
    assert all(r["new"] and r["new"] >= f"{MON} 09:00" for r in plan["affected"])


def test_running_late_tells_the_rest_of_the_day_to_expect_a_delay():
    _day([(1, f"{THU} 09:00"), (2, f"{THU} 10:00"), (3, f"{THU} 10:20"), (4, f"{FRI} 10:20")])
    out = appt.delay_day(THU, "10:00", 25, "operation overran", NOW, "doctor")
    assert out["informed"] == 2 and out["patients"] == [2, 3]
    n = appt.for_patient(3, NOW)["notices"][-1]
    assert n["kind"] == "delayed" and n["expected"] == "10:45" and n["minutes"] == 25
    assert appt.for_patient(1, NOW)["notices"][-1]["kind"] == "confirmed" and appt.for_patient(4, NOW)["notices"][-1]["kind"] == "confirmed"
    with pytest.raises(appt.ApptError):
        appt.delay_day(THU, "10:00", 2, "", NOW, "doctor")


def test_the_sample_week_is_created_once_and_leaves_the_demo_patient_free():
    assert appt.seed(NOW, [1688, 1636] + list(range(100, 122))) is True            # 24 patients, like the demo
    assert appt.seed(NOW, [7, 62]) is False
    q = appt.queue(names)
    assert q and q[0]["urgent"] is True
    assert appt.for_patient(1688, NOW)["upcoming"] == []


# ---------------------------------------------------------------- the API
def test_api_round_trip_from_request_to_confirmation_and_cancellation(client):
    av = client.get("/api/availability").json()
    day = av["days"][0]["date"]
    free = next(s["time"] for s in av["days"][0]["slots"] if s["state"] == "free")
    pid = 1688
    r = client.post(f"/api/patients/{pid}/appointments", json={"slot": f"{day} {free}", "reason": "screening", "note": "eye exam"})
    assert r.status_code == 200 and r.json()["status"] == "requested"
    aid = r.json()["id"]
    assert client.post(f"/api/patients/{pid}/appointments", json={"slot": f"{day} {free}", "reason": "routine"}).status_code == 409
    assert any(x["id"] == aid and x["name"] for x in client.get("/api/appointments/queue").json()["items"])
    assert client.post(f"/api/appointments/{aid}/confirm", json={"actor": "reception"}).json()["status"] == "confirmed"
    mine = client.get(f"/api/patients/{pid}/appointments").json()
    assert mine["upcoming"][0]["id"] == aid and mine["notices"][0]["kind"] == "confirmed" and mine["cancel_notice_hours"] == 24
    client.post(f"/api/patients/{pid}/appointments/{aid}/seen")
    assert client.get(f"/api/patients/{pid}/appointments").json()["notices"] == []
    assert client.post(f"/api/patients/{pid}/appointments/{aid}/cancel").json()["status"] == "cancelled"
    sched = client.get("/api/schedule", params={"start": day, "days": 1}).json()
    row = next(s for s in sched["days"][0]["slots"] if s["time"] == free)
    assert row["appts"] == []                                                                              # the cancelled slot is free again


def test_api_errors_and_validation(client):
    assert client.post("/api/patients/1688/appointments", json={"slot": "tomorrow", "reason": "routine"}).status_code == 422
    assert client.post("/api/patients/1688/appointments", json={"slot": "2026-01-15 09:00", "reason": "nonsense"}).status_code == 422
    assert client.post("/api/appointments/nope/confirm", json={}).status_code == 404
    assert client.post("/api/patients/999999/appointments", json={"slot": "2026-01-15 09:00", "reason": "routine"}).status_code == 404
    assert client.post("/api/appointments/x/confirm", json={"actor": "stranger"}).status_code == 422
    assert client.get("/api/clinic").json()["cancel_notice_hours"] == 24


def test_api_doctor_unavailable_preview_then_apply(client):
    ids = []
    for pid, t in ((1688, "09:00"), (1636, "09:20")):
        a = client.post(f"/api/patients/{pid}/appointments", json={"slot": f"{FRI} {t}", "reason": "routine"}).json()
        client.post(f"/api/appointments/{a['id']}/confirm", json={})
        ids.append(a["id"])
    body = {"date": FRI, "start": "09:00", "end": "10:00", "mode": "move", "reason": "emergency surgery"}
    prev = client.post("/api/schedule/unavailable", json={**body, "preview": True}).json()
    assert len(prev["affected"]) == 2 and all(r["new"] for r in prev["affected"])
    done = client.post("/api/schedule/unavailable", json={**body, "preview": False, "actor": "doctor"}).json()
    assert done["blocked"] is True
    n = client.get("/api/patients/1688/appointments").json()["notices"]
    assert n[-1]["kind"] == "moved" and n[-1]["reason"] == "emergency surgery"
    late = client.post("/api/schedule/delay", json={"date": FRI, "from_time": "10:00", "minutes": 15, "actor": "nurse"}).json()
    assert late["informed"] >= 2
