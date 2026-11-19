"""Screening gaps: which yearly check-up tests a patient is overdue for.

People with diabetes need a few tests every year to catch kidney, eye and nerve damage early: a retina exam, a urine albumin test,
a kidney-function blood test and a foot exam. Many never get them (in Japan about 47% have the eye exam and about 15% the urine albumin
test). The twin can say a patient's kidney or eye risk is rising, but the doctor also needs to know whether the test that would confirm
it has actually been done. This module answers that.

The cohort has one snapshot per patient, so the test history is simulated, seeded by the patient id (like the visit history in
reports.py). The same schedule decides which reports exist in the patient's record, so the tracker and the Reports tab always agree.
Priya Kashyap (1636) is fully up to date. Rajesh Sharma (1688) is scripted to be overdue for the eye and foot exams, so the whole screening
demo can be shown on one patient; his urine albumin test stays up to date because his kidney story (albumin rising to 231 mg/g) needs it.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

RECENT = 3                                   # days since the newest lab panel and retina photo of a patient who is up to date
FOOT_USUAL = 182                             # days since the foot exam of a patient who is up to date (done at the last 6-month visit)
SOON_DAYS = 60                               # "due soon" when fewer than this many days are left
UP_TO_DATE = (1636,)                         # scripted demo patient with nothing overdue
SCRIPTED = {1688: {"eye": 430, "uacr": RECENT, "egfr": RECENT, "foot": 440}}      # Rajesh: eye and foot exams overdue
SCRIPTED_EYE_PHOTOS = {1688: (760, 430)}     # his two retina photos (mild, then moderate), both more than a year old

TESTS = {
    "eye": {"label": "Eye exam (retina)", "why": "Finds diabetic eye damage before sight is affected", "interval": 365,
            "refer": "an eye specialist"},
    "uacr": {"label": "Urine albumin test", "why": "The earliest sign of diabetic kidney damage", "interval": 365},
    "egfr": {"label": "Kidney function (eGFR)", "why": "Shows how well the kidneys filter the blood", "interval": 365},
    "foot": {"label": "Foot exam", "why": "Checks for nerve damage and ulcer risk", "interval": 365},
}
REMINDER_PREFIX = "Screening reminder: "
REFERRAL_PREFIX = "Referral: "


def schedule(pid: int) -> dict[str, int]:
    """Days since each test was last done, for one patient. Deterministic."""
    if pid in SCRIPTED:
        return dict(SCRIPTED[pid])
    if pid in UP_TO_DATE:
        return {"eye": RECENT, "uacr": RECENT, "egfr": RECENT, "foot": FOOT_USUAL}
    r = np.random.default_rng([int(pid), 515])
    eye_gap, eye_days = r.random() < 0.30, int(r.integers(400, 700))
    uacr_gap = r.random() < 0.30
    foot_gap, foot_days = r.random() < 0.25, int(r.integers(400, 600))
    return {"eye": eye_days if eye_gap else RECENT, "uacr": 548 if uacr_gap else RECENT, "egfr": RECENT,
            "foot": foot_days if foot_gap else FOOT_USUAL}


def eye_photo_days(pid: int) -> tuple[int, ...]:
    """Days before today of each retina photo in the record, oldest first. An up-to-date patient has the yearly one and a new one."""
    if pid in SCRIPTED_EYE_PHOTOS:
        return SCRIPTED_EYE_PHOTOS[pid]
    last = schedule(pid)["eye"]
    return (365, RECENT) if last <= 5 else (last,)


def _state(left: int) -> str:
    return "overdue" if left < 0 else "soon" if left <= SOON_DAYS else "ok"


def overdue(pid: int) -> list[str]:
    """Labels of the tests this patient is overdue for."""
    s = schedule(pid)
    return [t["label"] for k, t in TESTS.items() if TESTS[k]["interval"] - s[k] < 0]


def _follow_up(items: list[dict]) -> dict[str, dict]:
    """The doctor's latest reminder or referral for each test, found from the message titles."""
    out: dict[str, dict] = {}
    for m in sorted(items, key=lambda m: m["created"]):            # oldest first, so the newest wins
        title = m.get("title", "")
        for kind, prefix in (("reminder", REMINDER_PREFIX), ("referral", REFERRAL_PREFIX)):
            if title.startswith(prefix):
                label = title[len(prefix):].strip()
                for key, t in TESTS.items():
                    if t["label"] == label:
                        out[key] = {"kind": kind, "date": m["created"][:10]}
    return out


def status(pid: int, today: datetime, messages: list[dict] | None = None) -> dict:
    s = schedule(pid)
    follow = _follow_up(messages or [])
    tests = []
    for key, t in TESTS.items():
        days = s[key]
        left = t["interval"] - days
        tests.append({
            "key": key, "label": t["label"], "why": t["why"], "interval_days": t["interval"], "can_refer": "refer" in t,
            "last_done": (today - timedelta(days=days)).strftime("%Y-%m-%d"), "days_since": days,
            "due_date": (today + timedelta(days=left)).strftime("%Y-%m-%d"), "days_left": left, "state": _state(left),
            "follow_up": follow.get(key),
        })
    n = sum(t["state"] == "overdue" for t in tests)
    sent = sum(1 for t in tests if t["state"] == "overdue" and t["follow_up"])
    return {"patient_id": int(pid), "today": today.strftime("%Y-%m-%d"), "overdue": n, "followed_up": sent, "tests": tests,
            "headline": "All yearly tests are up to date" if not n else f"{n} yearly test{'s' if n > 1 else ''} overdue"
                        + (f", {sent} with a reminder or referral sent" if sent else "")}
