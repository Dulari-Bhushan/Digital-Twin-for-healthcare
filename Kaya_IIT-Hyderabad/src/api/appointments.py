"""Appointments: the clinic's calendar, patient requests, reception's confirmations and the doctor's changes.

How it works
  * The clinic has two sessions a day (09:00-12:00 and 14:00-17:00, Monday to Friday) in 20-minute slots. The last slot of each session
    is held back for urgent cases: patients cannot book it, reception can place an urgent patient in it (or squeeze one in).
  * A patient picks a free slot and sends a request. The slot is held at once so nobody else can take it. Reception confirms or declines.
    A patient who cancels frees the slot immediately; the app asks for at least 24 hours' notice so someone else can use it.
  * An urgent request needs no slot: it goes to the top of reception's queue and reception places it.
  * When the doctor is called away (an emergency operation, say) reception or the doctor blocks a time range: the patients in it move to
    the next free slots, or are cancelled, and each is told. "Running late" tells the rest of the day's patients to expect a delay.
  * Every change to a patient adds a notice that the patient app shows until the patient has seen it.

Everything is synthetic. The calendar is stored in one small JSON file (data/appointments.json, git-ignored); delete it to reset.
Times are the clinic's local time written "YYYY-MM-DD HH:MM". "Now" is the demo's simulated clock, passed in by the caller.
"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import atomic

ROOT = Path(__file__).resolve().parents[2]
FILE = Path(os.environ.get("KAYA_APPOINTMENTS", ROOT / "data" / "appointments.json"))
LOCK = threading.RLock()

SLOT_MIN = 20
SESSIONS = (("09:00", "12:00"), ("14:00", "17:00"))
OPEN_WEEKDAYS = (0, 1, 2, 3, 4)               # Monday to Friday
HORIZON_DAYS = 28
CANCEL_NOTICE_H = 24
MAX_ACTIVE_PER_PATIENT = 3
MAX_REQUESTS_PER_DAY = 6
REASONS = ("routine", "follow_up", "screening", "results", "other")
HOLDING = ("requested", "confirmed")          # statuses that occupy a slot
STATUSES = ("requested", "confirmed", "declined", "cancelled", "completed", "no_show")
CLINIC = {"name": "Kaya Demo Clinic (synthetic)", "slot_minutes": SLOT_MIN, "sessions": [list(s) for s in SESSIONS],
          "open_weekdays": list(OPEN_WEEKDAYS), "horizon_days": HORIZON_DAYS, "cancel_notice_hours": CANCEL_NOTICE_H}


class ApptError(Exception):
    """A request the calendar cannot honour. .code is an HTTP-style status: 404 not found, 409 conflict, 422 invalid."""

    def __init__(self, msg: str, code: int = 422):
        super().__init__(msg)
        self.code = code


# ------------------------------------------------------------------ time helpers
def _dt(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        raise ApptError("slot must look like 2026-01-15 09:00") from None


def _fmt(d: datetime) -> str:
    return d.strftime("%Y-%m-%d %H:%M")


def day_slots(day: date) -> list[str]:
    """Every slot start time (HH:MM) of an open day; empty on a closed day."""
    if day.weekday() not in OPEN_WEEKDAYS:
        return []
    out = []
    for a, b in SESSIONS:
        t, end = datetime.combine(day, datetime.strptime(a, "%H:%M").time()), datetime.combine(day, datetime.strptime(b, "%H:%M").time())
        while t + timedelta(minutes=SLOT_MIN) <= end:
            out.append(t.strftime("%H:%M"))
            t += timedelta(minutes=SLOT_MIN)
    return out


def reserved_slots(day: date) -> set[str]:
    """The last slot of each session is held back for urgent cases."""
    out = set()
    for _, b in SESSIONS:
        end = datetime.combine(day, datetime.strptime(b, "%H:%M").time())
        if day.weekday() in OPEN_WEEKDAYS:
            out.add((end - timedelta(minutes=SLOT_MIN)).strftime("%H:%M"))
    return out


def first_open_day(after: datetime) -> date:
    d = after.date() + timedelta(days=1) if after.time() > datetime.strptime("17:00", "%H:%M").time() else after.date()
    while d.weekday() not in OPEN_WEEKDAYS:
        d += timedelta(days=1)
    return d


# ------------------------------------------------------------------ storage
def _load() -> dict:
    d = atomic.read_json(FILE, None)
    return d if isinstance(d, dict) and "items" in d else {"items": [], "blocks": [], "seeded": False}


def _save(d: dict) -> None:
    atomic.write_text(FILE, json.dumps(d))


def _id() -> str:
    return uuid.uuid4().hex[:10]


def _event(a: dict, actor: str, event: str, detail: str, now: datetime) -> None:
    a.setdefault("history", []).append({"at": _fmt(now), "actor": actor, "event": event, "detail": detail})


def _notice(a: dict, kind: str, now: datetime, **info) -> None:
    a.setdefault("notices", []).append({"id": _id(), "kind": kind, "at": _fmt(now), "seen": False, **info})


def _holding(d: dict, slot: str, skip: str | None = None) -> list[dict]:
    return [x for x in d["items"] if x["status"] in HOLDING and x.get("slot") == slot and x["id"] != skip]


def _blocked(d: dict, slot: str) -> dict | None:
    dt = _dt(slot)
    for b in d["blocks"]:
        if b["date"] == dt.strftime("%Y-%m-%d") and b["start"] <= dt.strftime("%H:%M") < b["end"]:
            return b
    return None


def _check_slot(d: dict, slot: str, now: datetime, *, allow_reserved: bool, skip: str | None = None, allow_busy: bool = False) -> datetime:
    dt = _dt(slot)
    if dt.strftime("%H:%M") not in day_slots(dt.date()):
        raise ApptError("the clinic is closed at that time")
    if dt <= now:
        raise ApptError("that time has already passed")
    if dt.date() > now.date() + timedelta(days=HORIZON_DAYS):
        raise ApptError(f"appointments can be booked up to {HORIZON_DAYS} days ahead")
    if not allow_reserved and dt.strftime("%H:%M") in reserved_slots(dt.date()):
        raise ApptError("that slot is kept for urgent cases")
    if not allow_busy:
        if _blocked(d, slot):
            raise ApptError("the doctor is not available then", 409)
        if _holding(d, slot, skip):
            raise ApptError("that slot has just been taken", 409)
    return dt


def _get(d: dict, aid: str) -> dict:
    for x in d["items"]:
        if x["id"] == aid:
            return x
    raise ApptError("no such appointment", 404)


def _view(a: dict, name: str | None = None) -> dict:
    out = {k: v for k, v in a.items() if k != "history"}
    out["history"] = a.get("history", [])
    if name is not None:
        out["name"] = name
    if a.get("slot"):
        end = _dt(a["slot"]) + timedelta(minutes=SLOT_MIN)
        out["ends"] = end.strftime("%H:%M")
        out["expected"] = (_dt(a["slot"]) + timedelta(minutes=a.get("delay_min", 0))).strftime("%H:%M") if a.get("delay_min") else None
    return out


# ------------------------------------------------------------------ availability
def availability(now: datetime, days: int = HORIZON_DAYS) -> list[dict]:
    """What a patient sees: per open day, every slot as free, taken, reserved (urgent only), blocked or past. No names."""
    with LOCK:
        d = _load()
        taken = {x["slot"] for x in d["items"] if x["status"] in HOLDING and x.get("slot")}
        out = []
        day = now.date()
        for _ in range(days + 1):
            slots = day_slots(day)
            if slots:
                res = reserved_slots(day)
                rows = []
                for hhmm in slots:
                    s = f"{day.isoformat()} {hhmm}"
                    state = "past" if _dt(s) <= now else "reserved" if hhmm in res else "blocked" if _blocked(d, s) else "taken" if s in taken else "free"
                    rows.append({"time": hhmm, "state": state})
                if not all(r["state"] == "past" for r in rows):                  # a day that is already over is not offered
                    out.append({"date": day.isoformat(), "slots": rows, "free": sum(r["state"] == "free" for r in rows)})
            day += timedelta(days=1)
        return out


def schedule(now: datetime, start: str | None, days: int, names) -> dict:
    """What reception and the doctor see: every slot with the people in it, plus blocks, for `days` calendar days from `start`."""
    with LOCK:
        d = _load()
        first = datetime.strptime(start, "%Y-%m-%d").date() if start else first_open_day(now)
        out = []
        for i in range(max(1, min(days, 21))):
            day = first + timedelta(days=i)
            slots = day_slots(day)
            if not slots:
                out.append({"date": day.isoformat(), "closed": True, "slots": []})
                continue
            res = reserved_slots(day)
            rows = []
            for hhmm in slots:
                s = f"{day.isoformat()} {hhmm}"
                rows.append({"time": hhmm, "reserved": hhmm in res, "past": _dt(s) <= now, "block": _blocked(d, s),
                             "appts": [_view(x, names(x["pid"])) for x in d["items"] if x["status"] in HOLDING + ("completed", "no_show") and x.get("slot") == s]})
            out.append({"date": day.isoformat(), "closed": False, "slots": rows})
        return {"days": out, "blocks": d["blocks"], "first_open_day": first_open_day(now).isoformat()}


def queue(names) -> list[dict]:
    """Requests waiting for reception, urgent first, then oldest first."""
    with LOCK:
        d = _load()
        rows = [_view(x, names(x["pid"])) for x in d["items"] if x["status"] == "requested"]
        return sorted(rows, key=lambda r: (not r["urgent"], r["created"]))


def summary() -> dict:
    with LOCK:
        d = _load()
        pend = [x for x in d["items"] if x["status"] == "requested"]
        return {"pending": len(pend), "urgent": sum(1 for x in pend if x["urgent"])}


def for_patient(pid: int, now: datetime) -> dict:
    with LOCK:
        d = _load()
        mine = [x for x in d["items"] if x["pid"] == int(pid)]
        mine.sort(key=lambda x: (x.get("slot") or "9999", x["created"]))
        upcoming = [x for x in mine if x["status"] in HOLDING and (not x.get("slot") or _dt(x["slot"]) > now - timedelta(hours=1))]
        past = [x for x in mine if x not in upcoming][-5:]
        notices = [{**n, "appointment_id": x["id"], "slot": x.get("slot")} for x in mine for n in x.get("notices", []) if not n["seen"]]
        return {"upcoming": [_view(x) for x in upcoming], "past": [_view(x) for x in past], "notices": notices,
                "cancel_notice_hours": CANCEL_NOTICE_H, "now": _fmt(now)}


# ------------------------------------------------------------------ patients and reception create and change appointments
def request(pid: int, slot: str | None, reason: str, note: str, urgent: bool, now: datetime, *, actor: str = "patient", confirmed: bool = False,
            override: bool = False) -> dict:
    """A patient's request (status requested) or, when reception books for a patient, a confirmed appointment."""
    if reason not in REASONS:
        raise ApptError("unknown reason")
    note = re.sub(r"[\x00-\x08\x0b-\x1f<>]", "", note or "").strip()[:300]
    with LOCK:
        d = _load()
        mine = [x for x in d["items"] if x["pid"] == int(pid)]
        active = [x for x in mine if x["status"] in HOLDING and (not x.get("slot") or _dt(x["slot"]) > now)]
        if actor == "patient":
            if len(active) >= MAX_ACTIVE_PER_PATIENT:
                raise ApptError(f"you already have {MAX_ACTIVE_PER_PATIENT} appointments waiting; cancel one first", 409)
            if sum(1 for x in mine if x["created"][:10] == now.strftime("%Y-%m-%d")) >= MAX_REQUESTS_PER_DAY:
                raise ApptError("too many requests today", 429)
        if urgent and not slot and actor == "patient":
            dt = None
        else:
            if not slot:
                raise ApptError("choose a time")
            dt = _check_slot(d, slot, now, allow_reserved=(actor != "patient"), allow_busy=override)
            if actor == "patient" and any(x.get("slot") == slot for x in active):
                raise ApptError("you already have that time", 409)
        a = {"id": _id(), "pid": int(pid), "slot": _fmt(dt) if dt else None, "reason": reason, "urgent": bool(urgent), "note": note,
             "status": "confirmed" if confirmed else "requested", "created": _fmt(now), "updated": _fmt(now), "by": actor, "delay_min": 0,
             "notices": [], "history": []}
        _event(a, actor, "booked" if confirmed else "requested", (a["slot"] or "as soon as possible") + (" (urgent)" if urgent else ""), now)
        if confirmed and actor != "patient":
            _notice(a, "confirmed", now, slot=a["slot"])
        d["items"].append(a)
        _save(d)
        return _view(a)


def patient_cancel(pid: int, aid: str, now: datetime) -> dict:
    with LOCK:
        d = _load()
        a = _get(d, aid)
        if a["pid"] != int(pid):
            raise ApptError("no such appointment", 404)
        if a["status"] not in HOLDING:
            raise ApptError("that appointment is already closed", 409)
        late = bool(a.get("slot")) and _dt(a["slot"]) - now < timedelta(hours=CANCEL_NOTICE_H)
        a["status"], a["updated"], a["late_cancel"] = "cancelled", _fmt(now), late
        _event(a, "patient", "cancelled", "late (less than 24 hours' notice)" if late else "with notice", now)
        _save(d)
        return _view(a)


def confirm(aid: str, now: datetime, actor: str, slot: str | None = None, override: bool = False) -> dict:
    with LOCK:
        d = _load()
        a = _get(d, aid)
        if a["status"] != "requested":
            raise ApptError("only a waiting request can be confirmed", 409)
        target = slot or a.get("slot")
        if not target:
            raise ApptError("an urgent request needs a time: choose one")
        _check_slot(d, target, now, allow_reserved=True, skip=aid, allow_busy=override)
        placed = a.get("slot") != target
        a["slot"], a["status"], a["updated"] = target, "confirmed", _fmt(now)
        _event(a, actor, "confirmed", target + (" (squeezed in)" if override and _holding(d, target, aid) else ""), now)
        _notice(a, "confirmed", now, slot=target, urgent=a["urgent"], placed=placed)
        _save(d)
        return _view(a)


def decline(aid: str, now: datetime, actor: str, reason: str = "") -> dict:
    with LOCK:
        d = _load()
        a = _get(d, aid)
        if a["status"] != "requested":
            raise ApptError("only a waiting request can be declined", 409)
        reason = re.sub(r"[\x00-\x08\x0b-\x1f<>]", "", reason or "").strip()[:200]
        a["status"], a["updated"] = "declined", _fmt(now)
        _event(a, actor, "declined", reason, now)
        _notice(a, "declined", now, slot=a.get("slot"), reason=reason)
        _save(d)
        return _view(a)


def move(aid: str, new_slot: str, now: datetime, actor: str, reason: str = "", override: bool = False) -> dict:
    with LOCK:
        d = _load()
        a = _get(d, aid)
        if a["status"] not in HOLDING:
            raise ApptError("that appointment is closed", 409)
        _check_slot(d, new_slot, now, allow_reserved=True, skip=aid, allow_busy=override)
        old = a.get("slot")
        a["slot"], a["updated"], a["delay_min"] = new_slot, _fmt(now), 0
        reason = re.sub(r"[\x00-\x08\x0b-\x1f<>]", "", reason or "").strip()[:200]
        _event(a, actor, "moved", f"{old} to {new_slot}. {reason}".strip(), now)
        _notice(a, "moved", now, old=old, slot=new_slot, reason=reason)
        _save(d)
        return _view(a)


def clinic_cancel(aid: str, now: datetime, actor: str, reason: str = "") -> dict:
    with LOCK:
        d = _load()
        a = _get(d, aid)
        if a["status"] not in HOLDING:
            raise ApptError("that appointment is closed", 409)
        reason = re.sub(r"[\x00-\x08\x0b-\x1f<>]", "", reason or "").strip()[:200]
        a["status"], a["updated"] = "cancelled", _fmt(now)
        a["cancelled_by"] = "clinic"
        _event(a, actor, "cancelled", reason, now)
        _notice(a, "cancelled", now, slot=a.get("slot"), reason=reason)
        _save(d)
        return _view(a)


def close(aid: str, now: datetime, actor: str, status: str) -> dict:
    if status not in ("completed", "no_show"):
        raise ApptError("status must be completed or no_show")
    with LOCK:
        d = _load()
        a = _get(d, aid)
        if a["status"] != "confirmed":
            raise ApptError("only a confirmed appointment can be closed", 409)
        a["status"], a["updated"] = status, _fmt(now)
        _event(a, actor, status, "", now)
        _save(d)
        return _view(a)


def mark_seen(pid: int, aid: str) -> dict:
    with LOCK:
        d = _load()
        a = _get(d, aid)
        if a["pid"] != int(pid):
            raise ApptError("no such appointment", 404)
        for n in a.get("notices", []):
            n["seen"] = True
        _save(d)
        return _view(a)


# ------------------------------------------------------------------ when the doctor is called away
def _free_after(d: dict, start: datetime, taken: set[str], now: datetime, horizon: date) -> str | None:
    """The earliest free, non-reserved slot at or after `start`, skipping `taken` (slots promised during this plan)."""
    day = start.date()
    while day <= horizon:
        res = reserved_slots(day)
        for hhmm in day_slots(day):
            s = f"{day.isoformat()} {hhmm}"
            if _dt(s) < start or _dt(s) <= now or hhmm in res or s in taken:
                continue
            if _blocked(d, s) or _holding(d, s):
                continue
            return s
        day += timedelta(days=1)
    return None


def plan_unavailable(day: str, start: str, end: str, mode: str, now: datetime, names) -> dict:
    """Who is affected if the doctor is away from `start` to `end` on `day`, and where each would move. Changes nothing."""
    if mode not in ("move", "cancel"):
        raise ApptError("mode must be move or cancel")
    try:
        s, e = datetime.strptime(f"{day} {start}", "%Y-%m-%d %H:%M"), datetime.strptime(f"{day} {end}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise ApptError("use a date like 2026-01-15 and times like 10:00") from None
    if e <= s:
        raise ApptError("the end must be after the start")
    if e <= now:
        raise ApptError("that time has already passed")
    with LOCK:
        d = _load()
        hit = sorted([x for x in d["items"] if x["status"] in HOLDING and x.get("slot") and s <= _dt(x["slot"]) < e], key=lambda x: (not x["urgent"], x["slot"]))
        taken: set[str] = set()
        horizon = now.date() + timedelta(days=HORIZON_DAYS + 7)
        rows = []
        for x in hit:
            target = None
            if mode == "move":
                target = _free_after(d, e, taken, now, horizon)
                if target:
                    taken.add(target)
            rows.append({"id": x["id"], "pid": x["pid"], "name": names(x["pid"]), "old": x["slot"], "new": target, "urgent": x["urgent"], "status": x["status"]})
        rows.sort(key=lambda r: r["old"])
        return {"date": day, "start": start, "end": end, "mode": mode, "affected": rows, "unplaced": sum(1 for r in rows if mode == "move" and not r["new"])}


def apply_unavailable(day: str, start: str, end: str, mode: str, reason: str, now: datetime, actor: str, names) -> dict:
    reason = re.sub(r"[\x00-\x08\x0b-\x1f<>]", "", reason or "").strip()[:200]
    with LOCK:
        plan = plan_unavailable(day, start, end, mode, now, names)
        d = _load()
        d["blocks"].append({"id": _id(), "date": day, "start": start, "end": end, "reason": reason, "by": actor, "created": _fmt(now)})
        for r in plan["affected"]:
            a = _get(d, r["id"])
            if mode == "move" and r["new"]:
                a["slot"], a["updated"], a["delay_min"] = r["new"], _fmt(now), 0
                _event(a, actor, "moved", f"{r['old']} to {r['new']}: doctor unavailable. {reason}".strip(), now)
                _notice(a, "moved", now, old=r["old"], slot=r["new"], reason=reason)
            else:
                a["status"], a["updated"], a["cancelled_by"] = "cancelled", _fmt(now), "clinic"
                _event(a, actor, "cancelled", f"doctor unavailable. {reason}".strip(), now)
                _notice(a, "cancelled", now, slot=r["old"], reason=reason)
        _save(d)
        return {**plan, "blocked": True}


def remove_block(block_id: str) -> dict:
    with LOCK:
        d = _load()
        n = len(d["blocks"])
        d["blocks"] = [b for b in d["blocks"] if b["id"] != block_id]
        if len(d["blocks"]) == n:
            raise ApptError("no such block", 404)
        _save(d)
        return {"removed": block_id}


def delay_day(day: str, from_time: str, minutes: int, reason: str, now: datetime, actor: str) -> dict:
    """The doctor is running late: everyone from `from_time` on that day is told to expect a delay (their slot stays theirs)."""
    if not 5 <= int(minutes) <= 240:
        raise ApptError("the delay must be between 5 and 240 minutes")
    reason = re.sub(r"[\x00-\x08\x0b-\x1f<>]", "", reason or "").strip()[:200]
    try:
        start = datetime.strptime(f"{day} {from_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise ApptError("use a date like 2026-01-15 and a time like 10:00") from None
    with LOCK:
        d = _load()
        hit = [x for x in d["items"] if x["status"] in HOLDING and x.get("slot") and x["slot"][:10] == day and _dt(x["slot"]) >= start]
        for a in hit:
            a["delay_min"] = a.get("delay_min", 0) + int(minutes)
            a["updated"] = _fmt(now)
            expected = (_dt(a["slot"]) + timedelta(minutes=a["delay_min"])).strftime("%H:%M")
            _event(a, actor, "delayed", f"{minutes} min. {reason}".strip(), now)
            _notice(a, "delayed", now, slot=a["slot"], minutes=int(minutes), expected=expected, reason=reason)
        _save(d)
        return {"date": day, "from": from_time, "minutes": int(minutes), "informed": len(hit), "patients": sorted({x["pid"] for x in hit})}


# ------------------------------------------------------------------ demo data
def seed(now: datetime, pids: list[int], force: bool = False) -> bool:
    """A believable week: mostly confirmed appointments, a few waiting requests (one urgent), so reception has something to work on.
    Does nothing when a calendar already exists, unless force."""
    with LOCK:
        d = _load()
        if d.get("seeded") and not force:
            return False
        d = {"items": [], "blocks": [], "seeded": True}
        days, day = [], first_open_day(now)
        while len(days) < 5:
            if day.weekday() in OPEN_WEEKDAYS:
                days.append(day)
            day += timedelta(days=1)
        pool = [p for p in sorted(pids) if p not in (1688, 1636)]
        plan = [(0, "09:00", "routine"), (0, "09:40", "follow_up"), (0, "10:20", "screening"), (0, "14:00", "routine"), (1, "09:20", "results"),
                (1, "10:40", "routine"), (1, "14:40", "follow_up"), (2, "09:00", "routine"), (2, "11:00", "screening"), (2, "15:20", "routine"),
                (3, "09:40", "follow_up"), (3, "14:20", "routine"), (4, "10:00", "routine"), (4, "15:00", "results")]
        for i, (di, hhmm, reason) in enumerate(plan):
            if not pool:
                break
            pid = pool[(i * 5) % len(pool)]
            slot = f"{days[di].isoformat()} {hhmm}"
            if any(x["slot"] == slot for x in d["items"]) or any(x["pid"] == pid and x["slot"][:10] == slot[:10] for x in d["items"]):
                continue
            a = {"id": _id(), "pid": pid, "slot": slot, "reason": reason, "urgent": False, "note": "", "status": "confirmed", "created": _fmt(now - timedelta(days=2)),
                 "updated": _fmt(now - timedelta(days=1)), "by": "patient", "delay_min": 0, "notices": [], "history": []}
            _event(a, "patient", "requested", slot, now - timedelta(days=2))
            _event(a, "reception", "confirmed", slot, now - timedelta(days=1))
            d["items"].append(a)
        waiting = [(1, "11:20", "routine", False), (2, "14:00", "follow_up", False), (None, None, "other", True)]
        spare = [p for p in pool if not any(x["pid"] == p for x in d["items"])]
        for j, (di, hhmm, reason, urgent) in enumerate(waiting):
            if j >= len(spare):
                break
            pid = spare[(j * 3) % len(spare)] if len(spare) > 3 else spare[j]
            slot = f"{days[di].isoformat()} {hhmm}" if di is not None else None
            if slot and any(x["slot"] == slot for x in d["items"]):
                continue
            a = {"id": _id(), "pid": pid, "slot": slot, "reason": reason, "urgent": urgent,
                 "note": "I feel dizzy in the mornings and my sugar is high." if urgent else "", "status": "requested", "created": _fmt(now - timedelta(hours=3 + j)),
                 "updated": _fmt(now), "by": "patient", "delay_min": 0, "notices": [], "history": []}
            _event(a, "patient", "requested", slot or "as soon as possible", now - timedelta(hours=3 + j))
            d["items"].append(a)
        _save(d)
        return True
