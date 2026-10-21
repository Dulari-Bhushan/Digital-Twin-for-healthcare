"""Patient diary: medicines taken, walks, how the patient feels, and actions ticked off.

The last 14 days are seeded (deterministically, from each patient's own glucose and step data) so the doctor view has
something real-looking to show; anything the patient logs in the app is appended and stored in a small JSON file per
patient (data/patient_logs/, git-ignored). All of it is synthetic.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = Path(os.environ.get("KAYA_LOGS", ROOT / "data" / "patient_logs"))
LOCK = threading.Lock()

MEDS = ("morning", "evening")
FEEL = ("good", "ok", "low")
ACTIONS = ("snack", "walk", "bed_check", "meds_am", "meds_pm", "steady")
ADHERENCE = {1688: (0.92, 0.6), 1636: (0.97, 0.95)}   # scripted for the two demo patients: (morning, evening)


def _day_stats(a: dict) -> list[dict]:
    g = np.asarray(a["series"]["glucose"], dtype=float)
    st = np.asarray(a["series"]["steps"], dtype=float)
    out = []
    for d in range(len(g) // 288):
        x = g[d * 288:(d + 1) * 288]
        night = x[:72]
        out.append({"tir": float(((x >= 70) & (x <= 180)).mean()), "steps": float(st[d * 288:(d + 1) * 288].sum()),
                    "night_low_min": int((night < 70).sum() * 5)})
    return out


def seed(a: dict, today: datetime) -> list[dict]:
    """Fourteen days of history; today only has what a patient would have logged by the current time."""
    pid = a["profile"]["id"]
    days = _day_stats(a)
    n = len(days)
    rng = np.random.default_rng([pid, 404])
    mean_tir = float(np.mean([d["tir"] for d in days]))
    p_pm = float(np.clip(0.5 + 0.4 * mean_tir + rng.normal(0, 0.06), 0.35, 0.98))
    p_am, p_pm = ADHERENCE.get(pid, (min(0.98, p_pm + 0.1), p_pm))
    out = []

    def add(day_idx, hhmm, kind, value, note=""):
        date = (today - timedelta(days=n - 1 - day_idx)).strftime("%Y-%m-%d")
        out.append({"id": f"s{pid}-{day_idx}-{kind}-{hhmm}", "date": date, "time": hhmm, "kind": kind, "value": value, "note": note, "source": "seed"})

    for i, d in enumerate(days):
        last = i == n - 1
        if rng.random() < p_am:
            add(i, "08:10", "med", "morning")
        if not last and rng.random() < p_pm:
            add(i, "20:40", "med", "evening")
        if d["steps"] >= 3500 and not (last and pid == 1688):
            add(i, "18:30", "walk", int(np.clip(round(d["steps"] / 200 / 5) * 5, 10, 45)))
        if not last:
            feel = "good" if d["tir"] > 0.6 else "ok" if d["tir"] > 0.3 else "low"
            if rng.random() < 0.12:
                feel = FEEL[min(2, FEEL.index(feel) + 1)]
            note = ""
            if d["night_low_min"] >= 15:
                feel, note = "low", "Woke up sweaty and shaky in the night."
            elif d["tir"] < 0.1:
                note = "Ate a heavy meal; felt tired and thirsty."
            add(i, "21:15", "feel", feel, note)
    return out


def _load_patient(pid: int) -> list[dict]:
    f = LOG_DIR / f"{pid}.json"
    try:
        return json.loads(f.read_text(encoding="utf8")) if f.exists() else []
    except (OSError, ValueError):
        return []


def effective(items: list[dict]) -> list[dict]:
    """Apply "not taken" markers: a med_off entry cancels every earlier medicine entry for the same day and slot (including the
    pre-filled history), and is then dropped. Everything downstream (the app, the doctor's grid, the summaries) sees the result."""
    out: list[dict] = []
    for x in items:
        if x["kind"] == "med_off":
            out = [y for y in out if not (y["kind"] == "med" and y["date"] == x["date"] and y["value"] == x["value"])]
        else:
            out.append(x)
    return out


def entries(a: dict, today: datetime) -> list[dict]:
    return effective(seed(a, today) + _load_patient(a["profile"]["id"]))


def reset_patient_logs() -> int:
    """Forget everything patients entered in the app (the pre-filled history is regenerated), so a demo starts from zero."""
    n = 0
    with LOCK:
        if LOG_DIR.exists():
            for f in LOG_DIR.glob("*.json"):
                f.unlink()
                n += 1
    return n


def valid(kind: str, value) -> bool:
    if kind in ("med", "med_off"):
        return value in MEDS
    if kind == "feel":
        return value in FEEL
    if kind == "walk":
        return isinstance(value, int) and not isinstance(value, bool) and 5 <= value <= 120
    if kind == "action":
        return value in ACTIONS
    return False


def add(pid: int, today: datetime, kind: str, value, note: str = "") -> dict:
    """Append a patient-entered log item, stamped at the demo clock (the end of the series)."""
    e = {"id": uuid.uuid4().hex[:10], "date": today.strftime("%Y-%m-%d"), "time": today.strftime("%H:%M"), "kind": kind, "value": value, "note": note[:200], "source": "patient"}
    with LOCK:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        cur = _load_patient(pid)
        # one medicine or feeling entry per slot per day: logging again replaces it
        slot = kind in ("med", "med_off")
        cur = [x for x in cur if not (x["date"] == e["date"] and ((slot and x["kind"] in ("med", "med_off") and x["value"] == value)
                                                                  or (kind == "feel" and x["kind"] == "feel")))]
        cur.append(e)
        (LOG_DIR / f"{pid}.json").write_text(json.dumps(cur), encoding="utf8")
    return e


def remove(pid: int, entry_id: str) -> bool:
    with LOCK:
        cur = _load_patient(pid)
        keep = [x for x in cur if x["id"] != entry_id]
        if len(keep) == len(cur):
            return False
        (LOG_DIR / f"{pid}.json").write_text(json.dumps(keep), encoding="utf8")
    return True


def today_state(items: list[dict], today: datetime) -> dict:
    d = today.strftime("%Y-%m-%d")
    t = [x for x in items if x["date"] == d]
    walk = [x for x in t if x["kind"] == "walk"]
    feel = [x for x in t if x["kind"] == "feel"]
    return {"date": d, "med_morning": any(x["kind"] == "med" and x["value"] == "morning" for x in t),
            "med_evening": any(x["kind"] == "med" and x["value"] == "evening" for x in t),
            "walk_min": int(sum(x["value"] for x in walk)), "feel": feel[-1]["value"] if feel else None,
            "actions": sorted({x["value"] for x in t if x["kind"] == "action"}),
            "patient_ids": {x["id"]: x["kind"] + ":" + str(x["value"]) for x in t if x["source"] == "patient"}}


def summary(items: list[dict], today: datetime, days: int = 14) -> dict:
    dates = [(today - timedelta(days=k)).strftime("%Y-%m-%d") for k in range(days)]
    win = [x for x in items if x["date"] in dates]
    today_s = dates[0]
    full = dates[1:]                       # evening medicines and the daily feeling are only counted for finished days

    def taken(slot, ds):
        return sum(1 for d in ds if any(x["date"] == d and x["kind"] == "med" and x["value"] == slot for x in win))

    walk_days = sorted({x["date"] for x in win if x["kind"] == "walk"})
    walks = [x["value"] for x in win if x["kind"] == "walk"]
    feel = {k: sum(1 for x in win if x["kind"] == "feel" and x["value"] == k) for k in FEEL}
    last7 = dates[:7]
    return {
        "window_days": days,
        "morning": {"taken": taken("morning", dates), "of": days},
        "evening": {"taken": taken("evening", full), "of": len(full)},
        "evening_last7": {"taken": taken("evening", [d for d in last7 if d != today_s]), "of": len([d for d in last7 if d != today_s])},
        "walk_days": len(walk_days), "walk_days_last7": len([d for d in walk_days if d in last7]), "walk_min_avg": round(float(np.mean(walks)), 0) if walks else 0,
        "feel": feel,
    }


def attention(summ: dict) -> list[dict]:
    out = []
    e7 = summ["evening_last7"]
    if e7["of"] and e7["taken"] <= e7["of"] - 3:
        out.append({"tone": "butter", "text": f"Evening medicines logged on only {e7['taken']} of the last {e7['of']} days; ask about missed doses."})
    if summ["walk_days_last7"] <= 2:
        out.append({"tone": "butter", "text": f"Walks logged on {summ['walk_days_last7']} of the last 7 days."})
    return out
