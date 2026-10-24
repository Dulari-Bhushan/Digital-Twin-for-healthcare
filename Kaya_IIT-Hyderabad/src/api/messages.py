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


def send(pid: int, kind: str, title: str, body: str, action: str | None, created: str, template: str | None = None) -> dict:
    if kind not in KINDS:
        raise ValueError("kind must be urgent or advice")
    title, body = clean(title, 80), clean(body, 1000)
    if not body:
        raise ValueError("write a message first")
    if kind == "urgent" and action not in URGENT_ACTIONS:
        raise ValueError("an urgent message needs an action: come to the clinic, go to the emergency room, or call the clinic")
    msg = {"id": uuid.uuid4().hex[:12], "kind": kind, "title": title or ("Urgent message" if kind == "urgent" else "Message from your doctor"),
           "body": body, "action": action if kind == "urgent" else None, "created": created, "read": False,
           "template": template if template in TEMPLATES else None}
    with LOCK:
        items = _read(pid)
        if len(items) >= MAX_MESSAGES:
            raise ValueError("too many messages for this patient")
        _write(pid, items + [msg])
    return msg


CHECKS = ("none", "doctor", "self_insisted", "emergency", "unsure")     # what the helper said before the patient wrote
MAX_PER_DAY = 3


def sent_today(pid: int, day: str) -> int:
    """How many messages the patient wrote on this day (demo seeds do not count)."""
    return sum(1 for m in _read(pid) if m["kind"] == "patient" and not m.get("seed") and m["created"][:10] == day)


def from_patient(pid: int, body: str, created: str, seed: bool = False, check: str = "none") -> dict:
    """A message the patient writes to the doctor. It stays 'unanswered' (read False) until the doctor replies or marks it handled."""
    body = clean(body, 600)
    if not body:
        raise ValueError("write a message first")
    msg = {"id": uuid.uuid4().hex[:12], "kind": "patient", "title": "", "body": body, "action": None, "created": created, "read": False,
           "check": check if check in CHECKS else "none"}
    if seed:
        msg["seed"] = True
    with LOCK:
        items = _read(pid)
        if len(items) >= MAX_MESSAGES:
            raise ValueError("too many messages for this patient")
        _write(pid, items + [msg])
    return msg


def pending_from_patient(pid: int) -> list[dict]:
    return [m for m in _read(pid) if m["kind"] == "patient" and not m["read"]]


def answer_patient(pid: int) -> int:
    """The doctor replied or marked the patient's messages as handled."""
    with LOCK:
        items = _read(pid)
        n = 0
        for m in items:
            if m["kind"] == "patient" and not m["read"]:
                m["read"] = True
                n += 1
        if n:
            _write(pid, items)
    return n


def replace_seed(pid: int, body: str, created: str, check: str = "none") -> None:
    """Demo data: a fresh unanswered patient message at every start, replacing the one seeded last time."""
    with LOCK:
        items = [m for m in _read(pid) if not m.get("seed")]
        _write(pid, items)
    from_patient(pid, body, created, seed=True, check=check)


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


# ---------------------------------------------------------------- automatic translation of the doctor's own words
LANG_NAME = {"hi": "Hindi", "te": "Telugu", "kn": "Kannada"}
TEMPLATES = ("u_clinic", "u_er", "u_call", "a_walk", "a_bed", "a_portions", "a_meds")    # quick-start texts, translated by hand in the app


def _json_object(text: str) -> dict | None:
    """The first JSON object in a model reply, or None."""
    i, j = (text or "").find("{"), (text or "").rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        d = json.loads(text[i:j + 1])
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def translate_message(client, msg: dict, langs=("hi", "te", "kn")) -> dict:
    """Translate title, body and prescription instructions into each language with the voice service's chat model.
    Returns {lang: {"title", "body", "instructions": [...]}} for the languages that worked; any failure leaves that language out,
    and the patient then sees the doctor's original words."""
    instr = [c.get("instructions", "") for c in msg.get("changes", [])]
    payload = {"title": msg["title"] if msg["kind"] != "prescription" else "", "body": msg.get("body", ""), "instructions": instr}
    if not any([payload["title"], payload["body"], *instr]):
        return {}
    out = {}
    for lang in langs:
        system = (f"You translate a short message from a doctor to a patient in India into {LANG_NAME[lang]}. Use simple, polite everyday words. "
                  "Keep numbers, units, medicine names and doses exactly as written. Do not add or remove advice. "
                  "Reply with one JSON object only, with the same keys as the input: title, body, instructions (a list of the same length). Empty strings stay empty.")
        try:
            reply = client.chat([{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}], max_tokens=700)
        except Exception:  # noqa: BLE001  (a failed translation must never break a message)
            continue
        d = _json_object(reply)
        if not d or not isinstance(d.get("instructions", []), list) or len(d.get("instructions", [])) != len(instr):
            continue
        out[lang] = {"title": clean(str(d.get("title", "")), 160), "body": clean(str(d.get("body", "")), 2000),
                     "instructions": [clean(str(x), 400) if src else "" for x, src in zip(d.get("instructions", []), instr)]}
    return out


def needs_language(m: dict, lang: str) -> bool:
    """A doctor's message with free text that has no translation into `lang` yet (quick-start texts are translated in the app)."""
    return (m["kind"] != "patient" and not m.get("template") and lang not in (m.get("translations") or {})
            and bool(m.get("body") or m.get("title") or m.get("changes")))


def translate_to(client, msg: dict, lang: str) -> dict | None:
    """Title, body and prescription instructions in one language with Sarvam-Translate. None if any piece fails (the patient then sees the original)."""
    def one(text: str) -> str:
        return clean(client.translate(text, "en", lang), 2000) if text else ""
    try:
        return {"title": one(msg["title"] if msg["kind"] != "prescription" else ""), "body": one(msg.get("body", "")),
                "instructions": [one(c.get("instructions", "")) for c in msg.get("changes", [])]}
    except Exception:  # noqa: BLE001  (a failed translation must never break a message)
        return None


def add_translation(pid: int, mid: str, lang: str, tr: dict) -> None:
    with LOCK:
        items = _read(pid)
        for m in items:
            if m["id"] == mid:
                m.setdefault("translations", {})[lang] = tr
        _write(pid, items)


def set_translations(pid: int, mid: str, translations: dict) -> None:
    with LOCK:
        items = _read(pid)
        for m in items:
            if m["id"] == mid:
                m.setdefault("translations", {}).update(translations)
        _write(pid, items)


TEMPLATE_TEXT = {
    "u_clinic": ("Please come to the clinic today", "I have looked at your recent readings and I would like to see you at the clinic today. Please come as soon as you can and bring your medicines."),
    "u_er": ("Please go to the emergency room now", "Your readings are a serious concern. Please go to the nearest emergency room now. If you feel very unwell, call 108 straight away."),
    "u_call": ("Please call the clinic", "I would like to speak to you about your readings. Please call the clinic as soon as you see this message."),
    "a_walk": ("Please walk after meals", "Looking at your data, a 15 to 20 minute walk after dinner will help your sugar. Please try it every day this week."),
    "a_bed": ("Check your sugar before bed", "Your data shows dips at night. Please check your sugar before bed and have a small snack if it is below 110."),
    "a_portions": ("Try smaller portions of rice and roti", "Your sugar rises a lot after meals. Please try smaller portions of rice and roti, and add more vegetables and dal."),
    "a_meds": ("I want to review your medicines", "After looking at your data I would like to change your medicines. I will send you a new prescription shortly. Please do not change anything until then."),
}
_TEXT_TO_TEMPLATE = {v: k for k, v in TEMPLATE_TEXT.items()}


def adopt_templates(pid: int) -> None:
    """Messages sent before templates existed: if the text is exactly a quick-start text, mark it so the app shows the hand translation."""
    with LOCK:
        items = _read(pid)
        changed = False
        for m in items:
            if m["kind"] in KINDS and not m.get("template"):
                t = _TEXT_TO_TEMPLATE.get((m["title"], m["body"]))
                if t:
                    m["template"] = t
                    changed = True
        if changed:
            _write(pid, items)


def needs_translation(m: dict) -> bool:
    return m["kind"] != "patient" and not m.get("template") and not m.get("translations") and bool(m.get("body") or m.get("title") or m.get("changes"))
