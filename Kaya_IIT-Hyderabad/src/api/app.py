"""Kaya API: serves the twin for a cohort of demo patients from precomputed artifacts.

Run:  uvicorn app:app --app-dir src/api --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from urllib.parse import unquote
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "models"))
sys.path.insert(0, str(ROOT / "src" / "whatif"))

from engine import Scenario, glucose_metrics, run as run_whatif  # noqa: E402
import medicines as med  # noqa: E402
from eye_risk import GRADES, progression_risk  # noqa: E402
from kidney_dynamic import KidneyParams, projection  # noqa: E402
import assistant as asst  # noqa: E402
import admin as adm  # noqa: E402
import diary  # noqa: E402
import labparse  # noqa: E402
import uploads as upl  # noqa: E402
import messages as msgs  # noqa: E402
import reports as rpt  # noqa: E402
from live import Calibration, LiveTwin, NumpyGRU  # noqa: E402
from names import DEMO_TAGS, name_of  # noqa: E402
from voice import CHAT_MODEL, LANG_CODES, STT_MODEL, TTS_MODEL, SarvamClient, VoiceError, load_key  # noqa: E402
from liver_dynamic import LiverParams, risk_timeline  # noqa: E402

ART_DIR = Path(os.environ.get("KAYA_ARTIFACTS", ROOT / "artifacts" / "demo"))
CARDIO_DIR = Path(os.environ.get("KAYA_CARDIO", ROOT / "artifacts" / "cardio"))
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STEP_MIN = 5
HORIZONS_MIN = [30, 60, 120]

app = FastAPI(title="Kaya API", version="1.0.0",
              description="Multi-organ digital twin for Type 2 Diabetes. Decision support for clinicians, not a diagnostic device. "
                          "All patients are synthetic.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def _telemetry(request: Request, call_next):
    t = time.perf_counter()
    try:
        resp = await call_next(request)
    except Exception:
        adm.TEL.record(request.method, request.url.path, 500, (time.perf_counter() - t) * 1000)
        raise
    adm.TEL.record(request.method, request.url.path, resp.status_code, (time.perf_counter() - t) * 1000)
    return resp


STORE: dict[int, dict] = {}
CARDIO: dict = {"patients": {}, "evidence": None}
META: dict = {}
MODEL_DIR = Path(os.environ.get("KAYA_MODEL", ROOT / "artifacts" / "model"))
LIVE: dict = {}
SESSIONS: dict[int, LiveTwin] = {}
VOICE: dict = {}
HITS: dict[str, list[float]] = {}


def _tier(score: float) -> str:
    return "high" if score >= 0.6 else "medium" if score >= 0.35 else "low"


def _triage(pid: int, m: dict, recent: list, liver12: float, fib12: float, egfr: float, score: float) -> dict:
    """Who needs the doctor today: hard rules for the critical cases, 'what changed' for the rest.
    The visit history is simulated (seeded by patient id) because the cohort has a single snapshot per patient."""
    rng = np.random.default_rng(7000 + pid)
    jump = float(rng.choice([rng.uniform(-4, 4), rng.uniform(9, 24)], p=[0.82, 0.18]))     # change in worst organ risk since the last visit, points
    no_log_days = int(rng.choice([rng.integers(0, 3), rng.integers(4, 10)], p=[0.8, 0.2]))
    unread = bool(rng.random() < 0.12)
    review_days = int(rng.integers(1, 45))
    trig: list[dict] = []

    def add(key, text, level, event, hours=None):
        trig.append({"key": key, "text": text, "level": level, "event": event, "hours_ago": hours})

    hypo = [x for x in recent if x["type"] == "hypo"]
    if hypo:
        add("hypo", f"{len(hypo)} low-glucose alert(s) in 24 h", "critical", True, int(rng.integers(1, 20)))
    elif m["tbr"] > 0.04:
        add("tbr", f"Time below range {m['tbr'] * 100:.1f}%", "critical", False)
    if jump >= 15:
        add("jump", f"Organ risk up {jump:.0f} pts since last visit", "critical", True, int(rng.integers(6, 72)))
    elif jump >= 8:
        add("jump", f"Organ risk up {jump:.0f} pts since last visit", "warn", True, int(rng.integers(24, 200)))
    if fib12 >= 0.7:
        add("fib", f"Advanced fibrosis risk {fib12 * 100:.0f}%", "critical", False)
    elif fib12 >= 0.1:
        add("fib", f"Advanced fibrosis risk {fib12 * 100:.0f}%", "warn", False)
    if egfr < 45:
        add("egfr", f"eGFR {egfr:.0f}, kidney function low", "critical", False)
    elif egfr < 60:
        add("egfr", f"eGFR {egfr:.0f}", "warn", False)
    if unread:
        add("msg", "Unanswered patient message", "warn", True, int(rng.integers(2, 48)))
    if no_log_days >= 4:
        add("nolog", f"No readings or logs for {no_log_days} days", "warn", True, no_log_days * 24)
    if m["tir"] < 0.5:
        add("tir", f"Time in range {m['tir'] * 100:.0f}%", "warn", False)
    if score >= 0.35 and not trig:
        add("risk", "Elevated overall risk", "warn", False)

    bucket = "today" if any(t["level"] == "critical" for t in trig) else "week" if trig else "stable"
    escalated = False
    if bucket != "today" and review_days >= (30 if bucket == "stable" else 40):          # staleness: not opened for too long moves up a level
        bucket, escalated = ("week" if bucket == "stable" else "today"), True
        add("stale", f"Not reviewed for {review_days} days", "warn", False)
    if bucket != "today" and _tier(score) == "high" and review_days >= 21:                 # high-risk patients never stay out of sight for long
        bucket, escalated = "today", True
        add("overdue", f"High risk, not reviewed for {review_days} days", "critical", False)
    ev = [t["hours_ago"] for t in trig if t["event"] and t["level"] == "critical" and t["hours_ago"] is not None]
    return {"bucket": bucket, "triggers": trig, "event_hours": min(ev) if ev else None, "risk_jump": round(jump, 1),
            "days_since_log": no_log_days, "unread_msgs": int(unread), "days_since_review": review_days, "escalated": escalated,
            "trend": [round(max(0.0, score - jump / 100 * (3 - i) / 3 + float(rng.normal(0, 0.012))), 3) for i in range(4)][:-1] + [round(score, 3)]}


def _summary(a: dict) -> dict:
    m, pr = a["metrics"], a["profile"]
    last_t = a["forecast"]["t"][-1]
    recent = [x for x in a["alerts"] if x["t"] >= last_t - 288]
    liver12 = a["liver"]["timeline"]["steatosis"][-1]
    fib12 = a["liver"]["timeline"]["adv_fibrosis"][-1]
    eye = a["eye"]["progression_2y"]
    kid = a["kidney"]["static"]["ckd"]
    egfr = a["profile"]["labs"]["egfr"]
    glyc = min(1.0, (1 - m["tir"]) * 1.1 + m["tbr"] * 5)
    score = 0.32 * glyc + 0.22 * liver12 + 0.12 * min(1.0, fib12 * 4) + 0.2 * eye + 0.09 * kid + 0.05 * min(len(recent), 4) / 4
    reasons = []
    if m["tir"] < 0.5:
        reasons.append(f"Time in range {m['tir'] * 100:.0f}%")
    if m["tbr"] > 0.01:
        reasons.append(f"Time below range {m['tbr'] * 100:.1f}%")
    if liver12 > 0.5:
        reasons.append(f"Liver steatosis risk {liver12 * 100:.0f}% at 12 months")
    if fib12 > 0.1:
        reasons.append(f"Advanced fibrosis risk {fib12 * 100:.0f}%")
    if eye > 0.35 or a["eye"]["grade"] >= 2:
        reasons.append(f"Retinopathy: {GRADES[a['eye']['grade']]}, 2-year progression {eye * 100:.0f}%")
    if egfr < 60 or a["profile"]["labs"]["uacr_mg_g"] >= 30:
        reasons.append(f"Kidney flag: eGFR {egfr:.0f}, UACR {a['profile']['labs']['uacr_mg_g']:.0f}")
    if recent:
        reasons.append(f"{len(recent)} alert(s) in the last 24 h")
    return {"id": pr["id"], "name": pr.get("name") or f"Patient {pr['id']}", "demo_tag": pr.get("demo_tag"), "age": pr["age"], "sex": pr["sex"], "hba1c": pr["hba1c"], "tir": m["tir"], "tbr": m["tbr"],
            "mean_glucose": m["mean"], "score": round(score, 3), "tier": _tier(score), "reasons": reasons[:3],
            "alerts_24h": len(recent), "steatosis_12m": liver12, "fibrosis_12m": fib12, "eye_progression_2y": eye, "kidney_ckd_risk": kid,
            "dr_grade": a["eye"]["grade"], "last_glucose": a["series"]["glucose"][-1],
            "triage": _triage(pr["id"], m, recent, liver12, fib12, egfr, score)}


@app.on_event("startup")
def load() -> None:
    idx = ART_DIR / "index.json"
    if not idx.exists():
        raise RuntimeError(f"No artifacts at {ART_DIR}. Run src/api/build_artifacts.py first.")
    META.update(json.loads(idx.read_text()))
    for item in META["patients"]:
        STORE[item["id"]] = json.loads((ART_DIR / f"{item['id']}.json").read_text())
        STORE[item["id"]]["profile"]["name"] = name_of(item["id"])
        STORE[item["id"]]["profile"]["demo_tag"] = DEMO_TAGS.get(item["id"])
    if (CARDIO_DIR / "index.json").exists():
        for item in json.loads((CARDIO_DIR / "index.json").read_text())["patients"]:
            CARDIO["patients"][item["id"]] = json.loads((CARDIO_DIR / f"{item['id']}.json").read_text())
        CARDIO["evidence"] = json.loads((CARDIO_DIR / "evidence.json").read_text())
    if os.environ.get("KAYA_KEEP_LOGS") != "1":
        diary.reset_patient_logs()                       # a demo starts with nothing logged today; set KAYA_KEEP_LOGS=1 to keep entries
    key = load_key(ROOT)
    VOICE["client"] = SarvamClient(key) if key else None
    if (MODEL_DIR / "gru_numpy.npz").exists():
        LIVE["net"] = NumpyGRU(MODEL_DIR / "gru_numpy.npz")
        LIVE["cal"] = Calibration(MODEL_DIR / "calibration.json")


def _get(pid: int) -> dict:
    if pid not in STORE:
        raise HTTPException(404, f"patient {pid} not found")
    return STORE[pid]


def _iso(t: int) -> str:
    return (T0 + timedelta(minutes=STEP_MIN * int(t))).isoformat()


@app.get("/api/health")
def health():
    return {"status": "ok", "patients": len(STORE), "alert_thresholds": META.get("alert_thresholds"),
            "disclaimer": "Decision support only. Synthetic data."}


@app.get("/api/patients")
def patients():
    rows = [_summary(a) for a in STORE.values()]
    return sorted(rows, key=lambda r: -r["score"])


@app.get("/api/alerts/evidence")
def alert_evidence():
    """How reliable the glucose alerts are on real recordings: caught, right, false alerts per day and warning time, at three settings."""
    f = ART_DIR / "alert_evidence.json"
    if not f.exists():
        raise HTTPException(404, "alert evidence not built (run src/api/build_alert_evidence.py)")
    return json.loads(f.read_text())


@app.get("/api/patients/{pid}")
def patient(pid: int):
    a = _get(pid)
    s = _summary(a)
    last_t = a["forecast"]["t"][-1]
    fi = len(a["forecast"]["t"]) - 1
    q, p = a["forecast"]["q"][fi], a["forecast"]["p"][fi]
    g_now = a["series"]["glucose"][last_t]
    now = {"time": _iso(last_t), "glucose": g_now,
           "forecast": [{"minutes": m, "lo": round(min(max(g_now + q[i][0], 40), 400), 1),
                         "median": round(min(max(g_now + q[i][1], 40), 400), 1),
                         "hi": round(min(max(g_now + q[i][2], 40), 400), 1)} for i, m in enumerate(HORIZONS_MIN)],
           "p_hyper_2h": p[0], "p_hypo_2h": p[1]}
    return {"summary": s, "profile": a["profile"], "metrics": a["metrics"], "now": now,
            "liver": a["liver"], "kidney": a["kidney"], "explain": a.get("explain", {}), "eye": {**a["eye"], "grade_label": GRADES[a["eye"]["grade"]]},
            "alerts": [{**x, "time": _iso(x["t"])} for x in a["alerts"]][-20:]}


@app.get("/api/patients/{pid}/series")
def series(pid: int, days: float = Query(3, ge=0.25, le=14)):
    a = _get(pid)
    sr, fc = a["series"], a["forecast"]
    end = fc["t"][-1] + 1
    start = max(0, end - int(days * 288))
    ft = np.array(fc["t"])
    keep = np.flatnonzero(ft >= start)
    return {"start": _iso(start), "step_min": STEP_MIN, "t0": start,
            "glucose": sr["glucose"][start:end], "heart_rate": sr["heart_rate"][start:end],
            "steps": sr["steps"][start:end], "meal_carbs": sr["meal_carbs"][start:end],
            "sleep_stage": sr["sleep_stage"][start:end],
            "forecast": {"t": ft[keep].tolist(), "q": [fc["q"][i] for i in keep], "p": [fc["p"][i] for i in keep],
                         "horizons_min": HORIZONS_MIN},
            "alerts": [{**x, "time": _iso(x["t"])} for x in a["alerts"] if x["t"] >= start]}


class CustomMedicine(BaseModel):
    name: str = Field(..., min_length=1, max_length=40, description="a medicine the doctor adds by hand")
    baseline_shift: float = Field(..., ge=-60, le=60, description="assumed change in mean glucose, mg/dL (negative lowers it)")
    causes_lows: bool = False


class WhatIf(BaseModel):
    custom_medicines: list[CustomMedicine] = Field(default_factory=list, max_length=med.MAX_CUSTOM)
    medicines: dict[str, str] = Field(default_factory=dict, description="per-medicine change: {medicine key: stop | dose_down | dose_up | add}")
    carb_scale: float = Field(1.0, ge=0.3, le=1.5, description="1.0 = unchanged; 0.75 = 25% fewer carbs")
    walk_after_meals: int = Field(0, ge=0, le=60, description="minutes of walking after meals")
    baseline_shift: float = Field(0.0, ge=-60, le=60, description="mg/dL shift of the glucose baseline (e.g. medication)")
    steps_delta: float = Field(0.0, ge=-5000, le=10000, description="change in daily steps")


@app.get("/api/patients/{pid}/whatif/medicines")
def whatif_medicines(pid: int):
    """The patient's current medicines, what can be changed for each, and drugs that could be added, with the assumed effect of each."""
    _get(pid)
    meds = _meds_now(pid)
    keys = {k for k in (med.key_of(m["name"]) for m in meds) if k}
    out = med.options(keys)
    dose = {m["name"]: m["dose"] for m in meds}
    for c in out["current"]:
        c["dose"] = dose.get(c["name"], "")
    order = {m["name"]: i for i, m in enumerate(meds)}
    out["current"].sort(key=lambda c: order.get(c["name"], 99))
    out["assumptions"] = "Effect sizes are average, literature-informed assumptions, not this patient's own response. Simulation, not advice on prescribing."
    return out


@app.post("/api/patients/{pid}/whatif")
def whatif(pid: int, body: WhatIf):
    return _whatif_compute(_get(pid), body)


def _meds_now(pid: int) -> list[dict]:
    """The medicine list including any prescriptions the doctor has sent."""
    rx = [m for m in msgs.list_messages(pid) if m["kind"] == "prescription"]
    return msgs.apply_to_medicines(_record(pid)["record"]["medications"], rx)


def _whatif_compute(a: dict, body: WhatIf):
    sr, pr = a["series"], a["profile"]
    g = np.array(sr["glucose"], dtype=float)
    meals = np.array(sr["meal_carbs"], dtype=float)
    steps_day = float(np.sum(sr["steps"]) / (len(g) / 288))
    cur = {k for k in (med.key_of(m["name"]) for m in _meds_now(pr["id"])) if k}
    try:
        m_shift, m_low, m_carb, m_rows = med.combine(body.medicines, cur)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    for c in body.custom_medicines:
        name = med.clean_name(c.name)
        if not name:
            raise HTTPException(422, "a medicine added by hand needs a name")
        e = med.custom_effect(name, c.baseline_shift, c.causes_lows)
        m_shift += e["baseline_shift"]
        m_low *= e["low_scale"]
        m_rows.append(e)
    sc = Scenario(name="what-if", carb_scale=body.carb_scale * m_carb, walk_after_meals=body.walk_after_meals,
                  baseline_shift=body.baseline_shift + m_shift, steps_delta=body.steps_delta, low_scale=m_low)
    res = run_whatif(g, meals, steps_day, sc)
    base_m = glucose_metrics(g, steps_day)
    new_m = res["metrics"]
    p_static = a["liver"]["static"]
    params = LiverParams()
    tl_base = risk_timeline(p_static, base_m, 12, params)
    tl_new = risk_timeline(p_static, new_m, 12, params)
    eye_new = progression_risk(a["eye"]["grade"], pr["hba1c"] + (new_m["mean"] - base_m["mean"]) / 28.7,
                               pr["duration_yrs"], pr["sbp"], new_m["gv_cv"], new_m["tir"])
    kp = KidneyParams()
    lab = pr["labs"]
    hb_new = pr["hba1c"] + (new_m["mean"] - base_m["mean"]) / 28.7
    k_before = projection(lab["egfr"], pr["hba1c"], pr["sbp"], lab["uacr_mg_g"], base_m, a["kidney"]["static"]["albuminuria"], 5, kp)
    k_after = projection(lab["egfr"], hb_new, pr["sbp"], lab["uacr_mg_g"], new_m, a["kidney"]["static"]["albuminuria"], 5, kp)
    last_day = slice(len(g) - 288, len(g))
    return {
        "scenario": sc.describe(),
        "medicine_effects": m_rows,
        "metrics": {"before": base_m, "after": new_m},
        "glucose_last_day": {"t0": len(g) - 288, "start": _iso(len(g) - 288), "step_min": STEP_MIN,
                             "before": np.round(g[last_day], 1).tolist(), "after": np.round(res["glucose"][last_day], 1).tolist(),
                             "meal_carbs": meals[last_day].tolist()},
        "liver": {"before": tl_base, "after": tl_new},
        "eye": {"before": a["eye"]["progression_2y"], "after": round(eye_new, 4)},
        "kidney": {"before": k_before, "after": k_after},
        "assumptions": "Effect sizes are literature-informed assumptions, shown for transparency; this is a simulation, not a prediction.",
    }


@app.get("/api/patients/{pid}/report.pdf")
def report_pdf(pid: int):
    """One-page-per-topic clinical summary for the patient's file."""
    from report import build_report

    a = _get(pid)
    adm.TEL.audit("clinician", "clinical summary PDF", f"patient {pid}")
    presets = [("Walk 20 min after meals", WhatIf(walk_after_meals=20, steps_delta=2000)),
               ("Smaller carb portions (-25%)", WhatIf(carb_scale=0.75)),
               ("Medication optimised (-15 mg/dL)", WhatIf(baseline_shift=-15)),
               ("All three together", WhatIf(carb_scale=0.75, walk_after_meals=20, baseline_shift=-12, steps_delta=2000))]
    results = [(n, _whatif_compute(a, b)) for n, b in presets]
    pdf = build_report(a, _summary(a), patient(pid)["now"], results)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="kaya_patient_{pid}.pdf"'})


# ------------------------------------------------------------------ medical records (reports) and "what changed since the last visit"
RECORDS: dict[int, dict] = {}


def _record(pid: int) -> dict:
    if pid not in RECORDS:
        a = _get(pid)
        today = T0 + timedelta(minutes=STEP_MIN * int(a["forecast"]["t"][-1]))
        rec = rpt.build_record(a, today)
        RECORDS[pid] = {"record": rec, "changes": rpt.build_changes(a, rec)}
    return RECORDS[pid]


@app.get("/api/patients/{pid}/reports")
def reports_list(pid: int):
    """Every report in the patient's history (labs, imaging, clinic notes, device summaries), newest first."""
    rec = _record(pid)["record"]
    out = {k: v for k, v in rec.items() if not k.startswith("_")}
    today = _today(pid)
    extra = [r for r in (rpt.uploaded_report(pid, m, today, rec["reports"]) for m in upl.list_uploads(pid, full=True)) if r]
    rx = [m for m in msgs.list_messages(pid) if m["kind"] == "prescription"]
    for m in rx:                                           # the doctor's virtual consultation notes
        days = max(0, (today.date() - datetime.strptime(m["created"][:10], "%Y-%m-%d").date()).days)
        extra.append(msgs.report_for(pid, m, days))
    if extra:
        out["reports"] = sorted(rec["reports"] + extra, key=lambda r: (r["days_ago"], r["code"]))
    if rx:
        out["medications"] = msgs.apply_to_medicines(out["medications"], rx)   # prescriptions change the medicine list
    return out


# ------------------------------------------------------------------ messages and prescriptions from the doctor to the patient
class MessageReq(BaseModel):
    kind: str = Field(..., description="urgent or advice")
    title: str = Field("", max_length=80)
    body: str = Field(..., min_length=1, max_length=1000)
    action: str | None = Field(None, description="for urgent: come_to_clinic, go_to_er or call_clinic")
    template: str | None = Field(None, description="id of an unedited quick-start text; the app already has it in every language")
    translate: bool = Field(True, description="translate the text into Hindi, Telugu and Kannada with the voice service, in the background")


class RxChange(BaseModel):
    medicine: str = Field(..., min_length=1, max_length=60)
    action: str = Field(..., description="start, stop or change_dose")
    dose: str = Field("", max_length=80)
    instructions: str = Field("", max_length=200)


class RxReq(BaseModel):
    changes: list[RxChange] = Field(default_factory=list, max_length=msgs.MAX_CHANGES)
    note: str = Field("", max_length=1000)
    translate: bool = True


TRANSLATING: set[tuple[int, str]] = set()


def _translate_in_background(pid: int, m: dict) -> None:
    """Translate the doctor's words for the patient without delaying the message: the patient sees the original until it is ready."""
    client = VOICE.get("client")
    if client is None:
        return

    def work():
        try:
            tr = msgs.translate_message(client, m)
            if tr:
                msgs.set_translations(pid, m["id"], tr)
        except Exception:  # noqa: BLE001
            pass
    threading.Thread(target=work, daemon=True).start()


def _stamp(pid: int) -> str:
    return f"{_today(pid).strftime('%Y-%m-%d')} {datetime.now().strftime('%H:%M:%S')}"


@app.get("/api/patients/{pid}/messages")
def messages_list(pid: int):
    _get(pid)
    msgs.adopt_templates(pid)                              # older messages that match a quick-start text get its translations
    items = msgs.list_messages(pid)
    for m in items:                                        # older free-text messages are translated once, in the background
        if msgs.needs_translation(m) and (pid, m["id"]) not in TRANSLATING:
            TRANSLATING.add((pid, m["id"]))
            _translate_in_background(pid, m)
    return {"items": items, "unread": sum(not m["read"] for m in items)}


@app.post("/api/patients/{pid}/messages")
def messages_send(pid: int, body: MessageReq):
    """The doctor sends the patient an urgent message or advice. It appears in the patient app within seconds."""
    _get(pid)
    try:
        m = msgs.send(pid, body.kind, body.title, body.body, body.action, _stamp(pid), body.template)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    if body.translate and not m["template"]:
        _translate_in_background(pid, m)
    adm.TEL.audit("clinician", f"{m['kind']} message sent to patient", f"patient {pid}")
    return m


@app.post("/api/patients/{pid}/prescriptions")
def prescriptions_send(pid: int, body: RxReq):
    """A virtual consultation note with medicine changes. It updates the medicine list, adds a report, and pops up in the patient app."""
    _get(pid)
    try:
        m = msgs.prescribe(pid, [c.model_dump() for c in body.changes], body.note, _stamp(pid))
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    if body.translate:
        _translate_in_background(pid, m)
    adm.TEL.audit("clinician", "prescription and consultation note sent", f"patient {pid}: {len(m['changes'])} medicine change(s)")
    return m


@app.post("/api/patients/{pid}/messages/{mid}/read")
def messages_read(pid: int, mid: str):
    """The patient has seen the message."""
    _get(pid)
    m = msgs.mark_read(pid, mid)
    if m is None:
        raise HTTPException(404, "message not found")
    adm.TEL.audit("patient app", "message acknowledged", f"patient {pid}")
    return m


@app.get("/api/patients/{pid}/changes")
def changes(pid: int):
    ch = dict(_record(pid)["changes"])
    ch["attention"] = (ch["attention"] + diary.attention(_diary_summary(pid)))[:6]
    return ch


# ------------------------------------------------------------------ patient diary: medicines, walks, feelings, actions
def _today(pid: int) -> datetime:
    a = _get(pid)
    return T0.replace(tzinfo=None) + timedelta(minutes=STEP_MIN * int(a["forecast"]["t"][-1]))


def _diary_items(pid: int) -> list[dict]:
    return diary.entries(_get(pid), _today(pid))


def _diary_summary(pid: int) -> dict:
    return diary.summary(_diary_items(pid), _today(pid))


class LogEntry(BaseModel):
    kind: str = Field(..., description="med | med_off | walk | feel | action")
    value: str | int
    note: str = Field("", max_length=200)


@app.get("/api/patients/{pid}/log")
def log_get(pid: int):
    items = _diary_items(pid)
    today = _today(pid)
    recent = sorted([x for x in items if x["date"] >= (today - timedelta(days=13)).strftime("%Y-%m-%d")], key=lambda x: (x["date"], x["time"]), reverse=True)
    return {"today": diary.today_state(items, today), "summary": diary.summary(items, today), "entries": recent}


@app.post("/api/patients/{pid}/log")
def log_add(pid: int, body: LogEntry, request: Request):
    _rate_limit(request, limit=120)
    _get(pid)
    if not diary.valid(body.kind, body.value):
        raise HTTPException(422, "unknown log entry")
    diary.add(pid, _today(pid), body.kind, body.value, body.note)
    adm.TEL.audit("patient app", "diary entry", f"patient {pid}: {body.kind}")
    return log_get(pid)


@app.delete("/api/patients/{pid}/log/{entry_id}")
def log_delete(pid: int, entry_id: str):
    _get(pid)
    if not diary.remove(pid, entry_id):
        raise HTTPException(404, "entry not found")
    adm.TEL.audit("patient app", "diary entry removed", f"patient {pid}")
    return log_get(pid)


@app.get("/api/patients/{pid}/reports/{rid}.pdf")
def report_one_pdf(pid: int, rid: str):
    rec = _record(pid)["record"]
    rep = next((r for r in rec["reports"] if r["id"] == rid), None)
    if rep is None:
        raise HTTPException(404, "report not found")
    adm.TEL.audit("clinician", "report PDF", f"patient {pid}: {rep['code']} {rep['date']}")
    return Response(rpt.report_pdf(_get(pid)["profile"], rep), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{rid}.pdf"'})


# ------------------------------------------------------------------ live mode: the model runs on every new reading
class Reading(BaseModel):
    glucose: float = Field(..., ge=20, le=600)
    heart_rate: float = Field(70, ge=20, le=250)
    steps: float = Field(0, ge=0, le=2000, description="steps in the last 5 minutes")
    meal_carbs: float = Field(0, ge=0, le=300, description="grams of carbohydrate started in this interval")
    minute_of_day: int = Field(0, ge=0, le=1439)


def _new_twin(pid: int) -> LiveTwin:
    if "net" not in LIVE:
        raise HTTPException(503, "live model not available (artifacts/model missing)")
    return LiveTwin(LIVE["net"], LIVE["cal"], _get(pid)["profile"])


@app.post("/api/live/{pid}/reading")
def live_reading(pid: int, body: Reading, reset: bool = False):
    """Ingest one 5-minute reading from a device. Returns the twin's forecast once 2 hours of history exist."""
    if reset or pid not in SESSIONS:
        SESSIONS[pid] = _new_twin(pid)
        adm.TEL.audit("device", "live session started", f"patient {pid}")
    out = SESSIONS[pid].push(body.glucose, body.heart_rate, body.steps, body.meal_carbs, body.minute_of_day)
    return {"ready": out is not None, "readings_buffered": SESSIONS[pid].n, "forecast": out,
            "note": "forecast values are changes in mg/dL from the current glucose: [horizon 30/60/120][low, median, high]"}


@app.websocket("/ws/live/{pid}")
async def ws_live(ws: WebSocket, pid: int, interval: float = 0.5, back_days: float = 3.0, prefill: int = 288):
    """Simulated wearable feed: one 5-minute reading every `interval` seconds, with a live model forecast each time."""
    await ws.accept()
    if pid not in STORE or "net" not in LIVE:
        await ws.close(code=4404)
        return
    a = STORE[pid]
    sr = a["series"]
    n = sr["n"]
    start = max(L_WARM, n - int(back_days * 288))
    twin = _new_twin(pid)
    for i in range(start - L_WARM, start):
        twin.push(sr["glucose"][i], sr["heart_rate"][i], sr["steps"][i], sr["meal_carbs"][i], (i * STEP_MIN) % 1440)
    p0 = max(0, start - prefill)
    try:
        await ws.send_json({"type": "init", "t0": p0, "start": _iso(p0), "step_min": STEP_MIN, "glucose": sr["glucose"][p0:start],
                            "meal_carbs": sr["meal_carbs"][p0:start], "steps": sr["steps"][p0:start],
                            "thresholds": LIVE["cal"].thr})
        for i in range(start, n):
            out = twin.push(sr["glucose"][i], sr["heart_rate"][i], sr["steps"][i], sr["meal_carbs"][i], (i * STEP_MIN) % 1440)
            await ws.send_json({"type": "tick", "t": i, "time": _iso(i), "glucose": sr["glucose"][i], "heart_rate": sr["heart_rate"][i],
                                "steps": sr["steps"][i], "meal_carbs": sr["meal_carbs"][i], "forecast": out})
            await asyncio.sleep(max(0.02, interval))
        await ws.send_json({"type": "end"})
    except WebSocketDisconnect:
        return


L_WARM = 24


# ------------------------------------------------------------------ voice and assistant (Sarvam AI; key stays on the server)
def _rate_limit(request: Request, limit: int = 40, window: float = 60.0) -> None:
    import time

    ip = request.client.host if request.client else "local"
    now = time.time()
    hits = [t for t in HITS.get(ip, []) if now - t < window]
    if len(hits) >= limit:
        raise HTTPException(429, "too many voice requests, please wait a moment")
    HITS[ip] = hits + [now]


def _client() -> SarvamClient:
    c = VOICE.get("client")
    if c is None:
        raise HTTPException(503, "voice is not configured on this server")
    return c


@app.get("/api/voice/status")
def voice_status():
    return {"enabled": VOICE.get("client") is not None, "languages": list(LANG_CODES),
            "stt": STT_MODEL, "tts": TTS_MODEL, "chat": CHAT_MODEL}


class TTSReq(BaseModel):
    text: str = Field(..., min_length=1, max_length=600)
    lang: str = "en"


@app.post("/api/voice/tts")
def voice_tts(body: TTSReq, request: Request):
    _rate_limit(request)
    try:
        wav = _client().tts(body.text, body.lang if body.lang in LANG_CODES else "en")
    except VoiceError as e:
        raise HTTPException(502, str(e)) from None
    return Response(wav, media_type="audio/wav", headers={"Cache-Control": "private, max-age=3600"})


@app.post("/api/voice/stt")
async def voice_stt(request: Request):
    """Raw audio in the request body (audio/wav); returns the transcript and detected language."""
    _rate_limit(request)
    audio = await request.body()
    if not audio or len(audio) > 3_000_000:
        raise HTTPException(413, "audio must be between 1 byte and 3 MB")
    try:
        return _client().stt(audio, content_type=request.headers.get("content-type", "audio/wav").split(";")[0])
    except VoiceError as e:
        raise HTTPException(502, str(e)) from None


class AssistantReq(BaseModel):
    pid: int
    lang: str = "en"
    message: str = Field(..., min_length=1, max_length=400)
    history: list[dict] = Field(default_factory=list)
    tab: int = Field(0, ge=0, le=3)


@app.post("/api/assistant")
def assistant(body: AssistantReq, request: Request):
    out = _assistant_inner(body, request)
    adm.TEL.assistant[out["kind"]] += 1
    adm.TEL.audit("patient app", "assistant", f"{out['kind']} reply, patient {body.pid}, {body.lang}")
    return out


def _assistant_inner(body: AssistantReq, request: Request):
    """Safety rules run first; only an ordinary question reaches the language model."""
    _rate_limit(request)
    a = _get(body.pid)
    lang = body.lang if body.lang in asst.LANGS else "en"
    cls = asst.classify(body.message, lang)
    if cls["kind"] == "navigate":
        return {"kind": "navigate", "reply": cls["reply"], "action": {"type": "navigate", "tab": cls["tab"]}}
    if cls["kind"] in ("emergency", "medicine"):
        return {"kind": cls["kind"], "reply": cls["reply"], "action": None}
    client = VOICE.get("client")
    if client is None:
        return {"kind": "unavailable", "reply": asst.FALLBACK_MSG[lang], "action": None}
    history = [{"role": h["role"], "content": str(h.get("content", ""))[:400]} for h in body.history[-6:] if h.get("role") in ("user", "assistant")]
    messages = [{"role": "system", "content": asst.system_prompt(lang, asst.patient_context(a, body.tab))}] + history + [{"role": "user", "content": body.message}]
    try:
        reply, blocked = asst.clean_reply(client.chat(messages), lang)
    except VoiceError:
        return {"kind": "error", "reply": asst.FALLBACK_MSG[lang], "action": None}
    return {"kind": "medicine" if blocked else "chat", "reply": reply, "action": None}


# ------------------------------------------------------------------ reports uploaded by the patient (PDF or photo)
@app.get("/api/patients/{pid}/uploads")
def uploads_list(pid: int):
    _get(pid)
    return {"items": upl.list_uploads(pid), "reading_available": VOICE.get("client") is not None, "max_mb": upl.MAX_BYTES // (1024 * 1024), "categories": list(upl.CATEGORIES),
            "note": "Uploaded by the patient. Not read automatically; marked verified only when a clinician says so."}


@app.post("/api/patients/{pid}/uploads")
async def uploads_add(pid: int, request: Request):
    """Raw file bytes in the body; x-filename, x-title, x-category and x-date headers carry the label (URL-encoded)."""
    _rate_limit(request, limit=20)
    _get(pid)
    if int(request.headers.get("content-length") or 0) > upl.MAX_BYTES + 4096:
        raise HTTPException(413, f"The file is larger than {upl.MAX_BYTES // (1024 * 1024)} MB.")
    data = await request.body()
    h = request.headers
    try:
        meta = upl.save(pid, data, unquote(h.get("x-filename", "")), unquote(h.get("x-title", "")), unquote(h.get("x-category", "other")), unquote(h.get("x-date", "")), _today(pid),
                          read=h.get("x-ocr") == "1" and VOICE.get("client") is not None)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    adm.TEL.audit("patient app", "report uploaded", f"patient {pid}: {meta['category']}, {meta['ext']}, {meta['size_kb']} KB, reading {'on' if meta['ocr']['state'] == 'pending' else 'off'}")
    if meta["ocr"]["state"] == "pending":
        _start_reading(pid, meta["id"])
    return upl.public(meta)


def _start_reading(pid: int, uid: str) -> None:
    """Read an uploaded document in the background with Sarvam Document AI, then parse any lab values out of the text."""
    client = VOICE.get("client")
    sex = _get(pid)["profile"]["sex"]
    today = _today(pid)

    def job() -> None:
        try:
            upl.set_ocr(pid, uid, state="reading")
            found = upl.get_file(pid, uid)
            if found is None:
                return
            f, meta = found
            text = client.digitise(f.read_bytes(), f"report.{meta['ext']}", meta["media"])
            text = labparse.clean_text(text)
            rows = labparse.parse(text, sex)
            doc_date = labparse.parse_date(text, today)
            if len(text.strip()) < 20 and not rows:
                upl.set_ocr(pid, uid, state="no_text")
            else:
                upl.set_ocr(pid, uid, state="done" if rows else "no_values", results=rows, doc_date=doc_date, text=text[:8000])
            adm.TEL.audit("system", "report read", f"patient {pid}: {len(rows)} values found")
        except Exception as e:  # noqa: BLE001  (a failed reading must never break the upload)
            upl.set_ocr(pid, uid, state="failed", error=str(e)[:100])
            adm.TEL.audit("system", "report reading failed", f"patient {pid}: {str(e)[:80]}")

    threading.Thread(target=job, daemon=True).start()


@app.post("/api/patients/{pid}/uploads/{uid}/read")
def uploads_read(pid: int, uid: str, request: Request):
    """The patient agreed to have a saved upload read by the document service. Nothing leaves the server before this call."""
    _rate_limit(request, limit=20)
    _get(pid)
    if VOICE.get("client") is None:
        raise HTTPException(503, "automatic reading is not set up on this server")
    found = upl.get_file(pid, uid)
    if found is None:
        raise HTTPException(404, "file not found")
    if found[1].get("ocr", {}).get("state") in ("pending", "reading"):
        raise HTTPException(409, "already being read")
    upl.set_ocr(pid, uid, state="pending", error=None, results=[], text="", doc_date=None)
    adm.TEL.audit("patient app", "reading approved by patient", f"patient {pid}")
    _start_reading(pid, uid)
    return upl.public(next(x for x in upl.list_uploads(pid, full=True) if x["id"] == uid))


@app.get("/api/patients/{pid}/uploads/{uid}/file")
def uploads_file(pid: int, uid: str):
    _get(pid)
    found = upl.get_file(pid, uid)
    if found is None:
        raise HTTPException(404, "file not found")
    f, meta = found
    adm.TEL.audit("clinician or patient", "uploaded report opened", f"patient {pid}: {meta['ext']}")
    return FileResponse(f, media_type=meta["media"], headers={"X-Content-Type-Options": "nosniff", "Content-Disposition": f'inline; filename="report-{uid}.{meta["ext"]}"',
                                                               "Cache-Control": "private, max-age=300"})


class VerifyReq(BaseModel):
    verified: bool = True


@app.post("/api/patients/{pid}/uploads/{uid}/verify")
def uploads_verify(pid: int, uid: str, body: VerifyReq):
    """The clinician confirms they checked an uploaded report against the original (or withdraws that)."""
    _get(pid)
    meta = upl.set_verified(pid, uid, body.verified, _today(pid))
    if meta is None:
        raise HTTPException(404, "file not found")
    adm.TEL.audit("clinician", "uploaded report verified" if body.verified else "uploaded report verification withdrawn", f"patient {pid}")
    return meta


@app.delete("/api/patients/{pid}/uploads/{uid}")
def uploads_delete(pid: int, uid: str):
    _get(pid)
    if not upl.delete(pid, uid):
        raise HTTPException(404, "file not found")
    adm.TEL.audit("patient app", "uploaded report removed", f"patient {pid}")
    return uploads_list(pid)


# ------------------------------------------------------------------ IT admin: health, inventory, traffic, audit, self-test
def _admin_guard(request: Request) -> None:
    if not adm.token_ok(request.headers.get("x-admin-token") or request.query_params.get("token")):
        raise HTTPException(401, "admin token required")


def _admin_state() -> dict:
    return {"root": ROOT, "art_dir": ART_DIR, "model_dir": MODEL_DIR, "log_dir": diary.LOG_DIR, "live_loaded": "net" in LIVE, "live_sessions": len(SESSIONS),
            "voice": VOICE.get("client") is not None, "voice_models": f"{STT_MODEL}, {TTS_MODEL}, {CHAT_MODEL}", "patients": len(STORE), "version": app.version, "uploads_dir": upl.UP_DIR}


@app.get("/api/admin/overview")
def admin_overview(request: Request):
    _admin_guard(request)
    return adm.overview(_admin_state())


@app.post("/api/admin/selftest")
def admin_selftest(request: Request):
    """Runs the main code paths once and reports pass or fail with timings. Uses one patient; changes nothing."""
    import tempfile

    _admin_guard(request)
    adm.TEL.audit("admin", "self-test run")
    pid = next(iter(STORE))
    checks = []

    def run(name, fn, warn=False):
        t = time.perf_counter()
        try:
            detail = fn()
            ok = True
        except Exception as e:  # noqa: BLE001
            detail, ok = f"{type(e).__name__}: {e}", False
        checks.append({"name": name, "ok": ok, "warn": warn and not ok, "ms": round((time.perf_counter() - t) * 1000, 1), "detail": str(detail)[:140]})

    def artifacts():
        assert len(STORE) >= 1
        return f"{len(STORE)} patients loaded"

    def triage():
        rows = patients()
        return f"{len(rows)} summaries, top score {rows[0]['score']}"

    def whatif_run():
        r = _whatif_compute(_get(pid), WhatIf(carb_scale=0.75, walk_after_meals=20))
        return f"time in range {r['metrics']['before']['tir']:.2f} to {r['metrics']['after']['tir']:.2f}"

    def live_model():
        twin = _new_twin(pid)
        sr = _get(pid)["series"]
        out = None
        t = time.perf_counter()
        n = L_WARM + 6
        for i in range(n):
            out = twin.push(sr["glucose"][i], sr["heart_rate"][i], sr["steps"][i], sr["meal_carbs"][i], (i * STEP_MIN) % 1440)
        assert out is not None, "no forecast after warm-up"
        return f"{(time.perf_counter() - t) * 1000 / n:.2f} ms per reading"

    def records():
        r = _record(pid)
        return f"{len(r['record']['reports'])} reports, {len(r['changes']['items'])} comparisons"

    def pdf():
        rec = _record(pid)["record"]["reports"][0]
        b = rpt.report_pdf(_get(pid)["profile"], rec)
        assert b[:4] == b"%PDF"
        return f"{len(b) / 1024:.0f} KB"

    def diary_dir():
        d = diary.LOG_DIR
        d.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=d, suffix=".tmp") as f:
            f.write(b"ok")
        return "writable"

    def heart_watch():
        assert CARDIO["patients"], "Heart watch artifacts not built"
        a = next(iter(CARDIO["patients"].values()))
        assert all(0 <= x["p"] <= 1 for x in a["mornings"])
        return f"{len(CARDIO['patients'])} patients, {len(a['mornings'])} mornings each"

    def voice_key():
        assert VOICE.get("client") is not None, "no key configured"
        return "configured"

    def dashboard():
        assert (ROOT / "dashboard" / "dist" / "index.html").exists(), "dashboard not built"
        return "built"

    run("Artifacts loaded", artifacts)
    run("Triage list", triage)
    run("What-if engine", whatif_run)
    run("Live model (numpy GRU)", live_model)
    run("Heart watch artifacts", heart_watch, warn=True)
    run("Medical record history", records)
    run("PDF rendering", pdf)
    run("Diary storage writable", diary_dir)
    run("Voice key present", voice_key, warn=True)
    run("Dashboard build present", dashboard, warn=True)
    return {"ok": all(c["ok"] or c["warn"] for c in checks), "checks": checks}


# ------------------------------------------------------------------ FHIR R4 (read-only, minimal)
def _fhir_patient(a: dict) -> dict:
    pr = a["profile"]
    return {"resourceType": "Patient", "id": str(pr["id"]),
            "identifier": [{"system": "urn:kaya:synthetic", "value": f"KAYA-{pr['id']:05d}"}],
            "gender": "female" if pr["sex"] == "F" else "male",
            "birthDate": str(2026 - int(pr["age"])) + "-01-01",
            "meta": {"tag": [{"system": "urn:kaya", "code": "synthetic", "display": "Synthetic patient"}]}}


def _obs(pid: int, loinc: str, name: str, value: float, unit: str, ucum: str, when: str) -> dict:
    return {"resourceType": "Observation", "status": "final", "subject": {"reference": f"Patient/{pid}"},
            "code": {"coding": [{"system": "http://loinc.org", "code": loinc, "display": name}], "text": name},
            "effectiveDateTime": when,
            "valueQuantity": {"value": value, "unit": unit, "system": "http://unitsofmeasure.org", "code": ucum}}


@app.get("/fhir/Patient/{pid}")
def fhir_patient(pid: int):
    return _fhir_patient(_get(pid))


@app.get("/fhir/Observation")
def fhir_observations(patient: int):
    a = _get(patient)
    pr, lab = a["profile"], a["profile"]["labs"]
    when = _iso(a["forecast"]["t"][-1])
    items = [
        _obs(patient, "2339-0", "Glucose [Mass/volume] in Blood", a["series"]["glucose"][a["forecast"]["t"][-1]], "mg/dL", "mg/dL", when),
        _obs(patient, "4548-4", "Hemoglobin A1c", pr["hba1c"], "%", "%", when),
        _obs(patient, "1742-6", "ALT", lab["alt"], "U/L", "U/L", when),
        _obs(patient, "1920-8", "AST", lab["ast"], "U/L", "U/L", when),
        _obs(patient, "777-3", "Platelets", lab["platelets"], "10*3/uL", "10*3/uL", when),
        _obs(patient, "33914-3", "eGFR", lab["egfr"], "mL/min/1.73m2", "mL/min/{1.73_m2}", when),
    ]
    return {"resourceType": "Bundle", "type": "searchset", "total": len(items),
            "entry": [{"resource": o} for o in items]}


# ------------------------------------------------------------------ Heart watch: cardiovascular flag on a coupled synthetic cohort
@app.get("/api/cardio/patients")
def cardio_patients():
    """Heart watch patients. Scores were produced by a model that never saw the patient (patient-grouped cross-validation)."""
    out = []
    for pid, a in CARDIO["patients"].items():
        pr, m = a["profile"], a["mornings"]
        out.append({"id": pid, "name": pr["name"], "age": pr["age"], "sex": pr["sex"], "prior_cvd": pr["prior_cvd"],
                    "smoker": pr["smoker"], "sbp": pr["sbp"], "alerts": sum(x["alert"] for x in m),
                    "peak_p": max(x["p"] for x in m), "record_pct": round(sum(x["record_pct"] for x in m) / len(m), 3)})
    return sorted(out, key=lambda r: -r["peak_p"])


@app.get("/api/cardio/evidence")
def cardio_evidence():
    if CARDIO["evidence"] is None:
        raise HTTPException(404, "Heart watch artifacts not built (run src/api/build_cardio_artifacts.py)")
    return CARDIO["evidence"]


@app.get("/api/cardio/{pid}")
def cardio_patient(pid: int):
    if pid not in CARDIO["patients"]:
        raise HTTPException(404, f"Heart watch patient {pid} not found")
    return CARDIO["patients"][pid]


# ------------------------------------------------------------------ example retina images with Grad-CAM (IDRiD, CC BY 4.0)
EYE_DIR = ROOT / "artifacts" / "eye"
if EYE_DIR.exists():
    app.mount("/eye-img", StaticFiles(directory=EYE_DIR), name="eye-img")


@app.get("/api/eye/examples")
def eye_examples():
    idx = EYE_DIR / "index.json"
    return json.loads(idx.read_text()) if idx.exists() else {"items": []}


# ------------------------------------------------------------------ dashboard (built React app), if present
DIST = ROOT / "dashboard" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if f.is_file() else DIST / "index.html")
