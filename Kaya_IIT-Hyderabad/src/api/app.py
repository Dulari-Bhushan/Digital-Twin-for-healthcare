"""Kaya API: serves the twin for a cohort of demo patients from precomputed artifacts.

Run:  uvicorn app:app --app-dir src/api --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "models"))
sys.path.insert(0, str(ROOT / "src" / "whatif"))

from engine import Scenario, glucose_metrics, run as run_whatif  # noqa: E402
from eye_risk import GRADES, progression_risk  # noqa: E402
from kidney_dynamic import KidneyParams, projection  # noqa: E402
from live import Calibration, LiveTwin, NumpyGRU  # noqa: E402
from liver_dynamic import LiverParams, risk_timeline  # noqa: E402

ART_DIR = Path(os.environ.get("KAYA_ARTIFACTS", ROOT / "artifacts" / "demo"))
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
STEP_MIN = 5
HORIZONS_MIN = [30, 60, 120]

app = FastAPI(title="Kaya API", version="1.0.0",
              description="Multi-organ digital twin for Type 2 Diabetes. Decision support for clinicians, not a diagnostic device. "
                          "All patients are synthetic.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STORE: dict[int, dict] = {}
META: dict = {}
MODEL_DIR = Path(os.environ.get("KAYA_MODEL", ROOT / "artifacts" / "model"))
LIVE: dict = {}
SESSIONS: dict[int, LiveTwin] = {}


def _tier(score: float) -> str:
    return "high" if score >= 0.6 else "medium" if score >= 0.35 else "low"


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
    return {"id": pr["id"], "age": pr["age"], "sex": pr["sex"], "hba1c": pr["hba1c"], "tir": m["tir"], "tbr": m["tbr"],
            "mean_glucose": m["mean"], "score": round(score, 3), "tier": _tier(score), "reasons": reasons[:3],
            "alerts_24h": len(recent), "steatosis_12m": liver12, "fibrosis_12m": fib12, "eye_progression_2y": eye, "kidney_ckd_risk": kid,
            "dr_grade": a["eye"]["grade"], "last_glucose": a["series"]["glucose"][-1]}


@app.on_event("startup")
def load() -> None:
    idx = ART_DIR / "index.json"
    if not idx.exists():
        raise RuntimeError(f"No artifacts at {ART_DIR}. Run src/api/build_artifacts.py first.")
    META.update(json.loads(idx.read_text()))
    for item in META["patients"]:
        STORE[item["id"]] = json.loads((ART_DIR / f"{item['id']}.json").read_text())
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
            "liver": a["liver"], "kidney": a["kidney"], "eye": {**a["eye"], "grade_label": GRADES[a["eye"]["grade"]]},
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


class WhatIf(BaseModel):
    carb_scale: float = Field(1.0, ge=0.3, le=1.5, description="1.0 = unchanged; 0.75 = 25% fewer carbs")
    walk_after_meals: int = Field(0, ge=0, le=60, description="minutes of walking after meals")
    baseline_shift: float = Field(0.0, ge=-60, le=60, description="mg/dL shift of the glucose baseline (e.g. medication)")
    steps_delta: float = Field(0.0, ge=-5000, le=10000, description="change in daily steps")


@app.post("/api/patients/{pid}/whatif")
def whatif(pid: int, body: WhatIf):
    a = _get(pid)
    sr, pr = a["series"], a["profile"]
    g = np.array(sr["glucose"], dtype=float)
    meals = np.array(sr["meal_carbs"], dtype=float)
    steps_day = float(np.sum(sr["steps"]) / (len(g) / 288))
    sc = Scenario(name="what-if", carb_scale=body.carb_scale, walk_after_meals=body.walk_after_meals,
                  baseline_shift=body.baseline_shift, steps_delta=body.steps_delta)
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
        "metrics": {"before": base_m, "after": new_m},
        "glucose_last_day": {"t0": len(g) - 288, "start": _iso(len(g) - 288), "step_min": STEP_MIN,
                             "before": np.round(g[last_day], 1).tolist(), "after": np.round(res["glucose"][last_day], 1).tolist(),
                             "meal_carbs": meals[last_day].tolist()},
        "liver": {"before": tl_base, "after": tl_new},
        "eye": {"before": a["eye"]["progression_2y"], "after": round(eye_new, 4)},
        "kidney": {"before": k_before, "after": k_after},
        "assumptions": "Effect sizes are literature-informed assumptions, shown for transparency; this is a simulation, not a prediction.",
    }


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
