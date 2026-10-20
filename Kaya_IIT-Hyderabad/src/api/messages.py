"""Doctor-to-patient messages and virtual prescriptions.

A doctor can send the patient an urgent message (come to the clinic, go to the emergency room), plain advice (walk more, review
your medicines), or a consultation note with a prescription. Prescriptions change the patient's medicine list and appear as a new
report in the Reports tab; the patient app pops them up until the patient acknowledges them. Stored as one small JSON file per
patient in data/patient_messages/ (git-ignored). Everything is synthetic; this is a demonstration, not a way to prescribe.
"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MSG_DIR = Path(os.environ.get("KAYA_MESSAGES", ROOT / "data" / "patient_messages"))
LOCK = threading.Lock()
KINDS = ("urgent", "advice")
URGENT_ACTIONS = ("come_to_clinic", "go_to_er", "call_clinic")
RX_ACTIONS = ("start", "stop", "change_dose")
MAX_MESSAGES = 200
MAX_CHANGES = 12


def clean(s: str, n: int) -> str:
    return re.sub(r"[\x00-\x08\x0b-\x1f<>]", "", s or "").strip()[:n]


def _path(pid: int) -> Path:
    return MSG_DIR / f"{int(pid)}.json"


def _read(pid: int) -> list[dict]:
    p = _path(pid)
    try:
        return json.loads(p.read_text(encoding="utf8")) if p.exists() else []
    except (OSError, ValueError):
        return []


def _write(pid: int, items: list[dict]) -> None:
    MSG_DIR.mkdir(parents=True, exist_ok=True)
    _path(pid).write_text(json.dumps(items), encoding="utf8")


def list_messages(pid: int) -> list[dict]:
    return sorted(_read(pid), key=lambda m: m["created"], reverse=True)


def send(pid: int, kind: str, title: str, body: str, action: str | None, created: str) -> dict:
    if kind not in KINDS:
        raise ValueError("kind must be urgent or advice")
    title, body = clean(title, 80), clean(body, 1000)
    if not body:
        raise ValueError("write a message first")
    if kind == "urgent" and action not in URGENT_ACTIONS:
        raise ValueError("an urgent message needs an action: come to the clinic, go to the emergency room, or call the clinic")
    msg = {"id": uuid.uuid4().hex[:12], "kind": kind, "title": title or ("Urgent message" if kind == "urgent" else "Message from your doctor"),
           "body": body, "action": action if kind == "urgent" else None, "created": created, "read": False}
    with LOCK:
        items = _read(pid)
        if len(items) >= MAX_MESSAGES:
            raise ValueError("too many messages for this patient")
        _write(pid, items + [msg])
    return msg


def prescribe(pid: int, changes: list[dict], note: str, created: str) -> dict:
    """A consultation note with medicine changes: [{medicine, action: start|stop|change_dose, dose, instructions}]."""
    rows = []
    for c in changes[:MAX_CHANGES]:
        name, action = clean(c.get("medicine", ""), 60), c.get("action")
        if not name:
            raise ValueError("every medicine change needs a medicine name")
        if action not in RX_ACTIONS:
            raise ValueError(f"unknown change {action!r} for {name}")
        dose = clean(c.get("dose", ""), 80)
        if action in ("start", "change_dose") and not dose:
            raise ValueError(f"give the dose for {name}")
        rows.append({"medicine": name, "action": action, "dose": dose, "instructions": clean(c.get("instructions", ""), 200)})
    note = clean(note, 1000)
    if not rows and not note:
        raise ValueError("add a medicine change or a note")
    msg = {"id": uuid.uuid4().hex[:12], "kind": "prescription", "title": "Your doctor updated your medicines" if rows else "Consultation note from your doctor",
           "body": note, "changes": rows, "action": None, "created": created, "read": False}
    with LOCK:
        items = _read(pid)
        if len(items) >= MAX_MESSAGES:
            raise ValueError("too many messages for this patient")
        _write(pid, items + [msg])
    return msg


def mark_read(pid: int, mid: str) -> dict | None:
    with LOCK:
        items = _read(pid)
        m = next((x for x in items if x["id"] == mid), None)
        if m is None:
            return None
        m["read"] = True
        _write(pid, items)
    return m


def apply_to_medicines(meds: list[dict], prescriptions: list[dict]) -> list[dict]:
    """The medicine list after the doctor's prescriptions, oldest first. Stopped medicines leave the list."""
    out = [dict(m) for m in meds]
    for rx in sorted(prescriptions, key=lambda m: m["created"]):
        date = rx["created"][:10]
        for c in rx.get("changes", []):
            key = c["medicine"].lower()
            hit = next((m for m in out if m["name"].lower() == key), None)
            if c["action"] == "stop":
                out = [m for m in out if m is not hit]
            elif c["action"] == "change_dose" and hit is not None:
                hit["dose"] = c["dose"]
                hit["purpose"] = (c["instructions"] or hit.get("purpose", "")) + f" (dose changed {date})"
                hit["start_days"] = 0
            else:                                                   # start, or change_dose of a medicine not on the list
                out = [m for m in out if m is not hit]
                out.append({"name": c["medicine"], "dose": c["dose"], "since": date, "start_days": 0,
                            "purpose": c["instructions"] or "Prescribed by your doctor", "new": True})
    return out


VERB = {"start": "Start", "stop": "Stop", "change_dose": "Change the dose of"}


def report_for(pid: int, rx: dict, days_ago: int) -> dict:
    """The consultation note as an entry for the Reports tab."""
    rows = rx.get("changes", [])
    lines = [f"{VERB[c['action']]} {c['medicine']}" + (f": {c['dose']}" if c["dose"] else "") + (f". {c['instructions']}" if c["instructions"] else "") + "." for c in rows]
    return {
        "id": f"{pid}-{rx['created'][:10]}-RX-{rx['id']}", "code": "RX", "type": "clinic", "name": "Teleconsultation note and prescription",
        "facility": "Virtual consultation (Kaya)", "clinician": "Your doctor", "date": rx["created"][:10], "days_ago": days_ago,
        "status": "Prescribed", "new": not rx.get("read"), "virtual": True, "rx_id": rx["id"],
        "sections": [], "meds": [{"name": c["medicine"], "dose": c["dose"] or "stopped", "purpose": ("Stopped. " if c["action"] == "stop" else "") + (c["instructions"] or "")}
                                 for c in rows],
        "findings": ([f"Doctor's note: {rx['body']}"] if rx.get("body") else []) + lines,
        "impression": "Medicines changed after reviewing your glucose and wearable data." if rows else "Advice after reviewing your data.",
        "plain": " ".join(lines) + (f" Your doctor wrote: {rx['body']}" if rx.get("body") else ""),
        "recommendations": lines + ["Take medicines as written and call the clinic if you feel unwell."],
    }
