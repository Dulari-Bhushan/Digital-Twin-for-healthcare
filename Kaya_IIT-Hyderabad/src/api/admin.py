"""Operations view for an IT administrator: service health, model and data inventory, traffic, audit trail, self-test.

Everything is held in memory for this demo (it resets when the server restarts). In a hospital deployment the same events
would go to the hospital's own logging and monitoring stack. No patient data and no secrets are ever returned here.
"""
from __future__ import annotations

import os
import platform
import re
import sys
import threading
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

STARTED = time.time()
LOCK = threading.Lock()
TOKEN_ENV = "KAYA_ADMIN_TOKEN"


class Telemetry:
    def __init__(self) -> None:
        self.routes: dict[str, dict] = {}
        self.audit_log: deque = deque(maxlen=200)
        self.assistant: Counter = Counter()
        self.total = 0
        self.errors = 0

    def record(self, method: str, path: str, status: int, ms: float) -> None:
        if path.startswith(("/assets", "/eye-img", "/favicon")) or not path.startswith(("/api", "/fhir", "/ws")):
            return
        key = f"{method} " + re.sub(r"/\d+", "/{id}", re.sub(r"/R?[0-9]+-\d{4}-\d{2}-\d{2}-[A-Z]+", "/{report}", path))
        with LOCK:
            r = self.routes.setdefault(key, {"n": 0, "err": 0, "ms": deque(maxlen=400)})
            r["n"] += 1
            r["ms"].append(ms)
            self.total += 1
            if status >= 500:
                r["err"] += 1
                self.errors += 1

    def audit(self, actor: str, action: str, detail: str = "") -> None:
        with LOCK:
            self.audit_log.appendleft({"time": datetime.now(timezone.utc).strftime("%H:%M:%S"), "actor": actor, "action": action, "detail": detail[:160]})

    def traffic(self) -> list[dict]:
        rows = []
        with LOCK:
            for k, r in self.routes.items():
                ms = sorted(r["ms"])
                p = lambda q: round(ms[min(len(ms) - 1, int(q * len(ms)))], 1) if ms else 0
                rows.append({"route": k, "count": r["n"], "errors": r["err"], "p50_ms": p(0.5), "p95_ms": p(0.95)})
        return sorted(rows, key=lambda x: -x["count"])


TEL = Telemetry()


def token_ok(supplied: str | None) -> bool:
    want = os.environ.get(TOKEN_ENV)
    return True if not want else supplied == want


def auth_mode() -> str:
    return "token" if os.environ.get(TOKEN_ENV) else "open"


MODELS = [
    {"name": "Glucose forecaster", "what": "GRU with quantile and event heads, blended with LightGBM, conformal 80% ranges", "serves": "Forecast, alerts, live mode",
     "validation": "CGMacros (real): 30 / 60 / 120 min error 12.6 / 21.1 / 28.2 mg/dL", "files": ["gru_numpy.npz", "calibration.json", "reference.json"], "dir": "model"},
    {"name": "Liver risk", "what": "Steatosis and advanced fibrosis from NHANES (with SHAP)", "serves": "Liver cards, 12-month projection",
     "validation": "NHANES (real): fibrosis AUROC 0.83, steatosis 0.83", "files": [], "dir": "demo"},
    {"name": "Kidney risk", "what": "Albuminuria and reduced eGFR from NHANES (with SHAP)", "serves": "Kidney cards, eGFR path",
     "validation": "NHANES (real): AUROC 0.76 and 0.85, small edge over a simple baseline", "files": [], "dir": "demo"},
    {"name": "Retina grader", "what": "EfficientNet-B2 ordinal grader with Grad-CAM", "serves": "Eye cards, retina photos",
     "validation": "APTOS kappa 0.89; Indian IDRiD kappa 0.71 after fine-tuning", "files": ["index.json"], "dir": "eye"},
    {"name": "What-if engine", "what": "Editable-assumption simulation (liver drift, eye progression, eGFR path)", "serves": "What-if studio, patient Try tab",
     "validation": "Simulation, labelled as such; not validated outcomes", "files": [], "dir": None},
]


def _size(p: Path) -> int:
    return p.stat().st_size if p.exists() else 0


def overview(state: dict) -> dict:
    root: Path = state["root"]
    art: Path = state["art_dir"]
    model_dir: Path = state["model_dir"]
    files = list(art.glob("*.json"))
    built = max((f.stat().st_mtime for f in files), default=0)
    dirs = {"model": model_dir, "demo": art, "eye": root / "artifacts" / "eye"}
    models = []
    for m in MODELS:
        d = dirs.get(m["dir"]) if m["dir"] else None
        have = [f for f in m["files"] if d and (d / f).exists()]
        if m["name"] == "Glucose forecaster":
            status = "loaded" if state["live_loaded"] else "missing"
        elif m["dir"] == "demo":
            status = "precomputed" if files else "missing"
        elif m["dir"] == "eye":
            status = "precomputed" if have else "missing"
        else:
            status = "in process"
        models.append({**{k: v for k, v in m.items() if k not in ("files", "dir")}, "status": status, "size_kb": round(sum(_size(d / f) for f in have) / 1024) if d else 0})
    log_dir: Path = state["log_dir"]
    n_logs = len(list(log_dir.glob("*.json"))) if log_dir.exists() else 0
    token = auth_mode()
    checks = [
        {"item": "Admin page requires a token", "ok": token == "token", "note": f"Set {TOKEN_ENV} to require one. Currently {'on' if token == 'token' else 'off (demo mode)'}."},
        {"item": "Voice key kept on the server only", "ok": True, "note": "Read from .env or the environment, never sent to a browser, .env is git-ignored."},
        {"item": "Patient endpoints require sign-in", "ok": False, "note": "Open in this demo. A deployment needs hospital single sign-on and role checks before real data is used."},
        {"item": "Cross-origin access restricted", "ok": False, "note": "CORS allows any origin for the demo; restrict it to the hospital's domain."},
        {"item": "Data is synthetic", "ok": True, "note": "24 invented patients; no real health records are stored."},
        {"item": "Voice requests rate limited", "ok": True, "note": "40 per minute per address, 120 per minute for the diary."},
        {"item": "Medicine and emergency questions handled in code", "ok": True, "note": "The language model never sees them; see the assistant counters below."},
        {"item": "Uploaded files are scanned for malware", "ok": False, "note": "Files are type-checked by content and size-limited, but not virus scanned or read; add scanning and encryption at rest in production."},
        {"item": "Audit trail kept in memory only", "ok": False, "note": "Resets on restart; send events to the hospital logging system in production."},
    ]
    return {
        "auth": token,
        "service": {"status": "ok", "uptime_s": int(time.time() - STARTED), "started": datetime.fromtimestamp(STARTED, timezone.utc).strftime("%d %b %Y %H:%M UTC"), "python": sys.version.split()[0],
                    "platform": platform.platform(terse=True), "api_version": state["version"]},
        "data": {"patients": state["patients"], "artifact_dir": str(art.relative_to(root)) if art.is_relative_to(root) else art.name, "artifact_files": len(files),
                 "artifact_mb": round(sum(_size(f) for f in files) / 1e6, 1), "built": datetime.fromtimestamp(built, timezone.utc).strftime("%d %b %Y %H:%M UTC") if built else "n/a",
                 "synthetic": True, "diary_files": n_logs, "uploaded_files": (len([f for f in state["uploads_dir"].rglob("*") if f.is_file() and f.name != "index.json"]) if state["uploads_dir"].exists() else 0), "eye_images": len(list((root / "artifacts" / "eye").glob("*.jpg"))), "dashboard_build": (root / "dashboard" / "dist" / "index.html").exists()},
        "integrations": [
            {"name": "Sarvam voice and chat", "status": "configured" if state["voice"] else "not configured", "detail": state["voice_models"]},
            {"name": "FHIR R4 read API", "status": "enabled", "detail": "Patient, Observation (read only)"},
            {"name": "Live feed (WebSocket)", "status": "enabled" if state["live_loaded"] else "unavailable", "detail": f"{state['live_sessions']} active session(s)"},
            {"name": "PDF reports", "status": "enabled", "detail": "Clinical summary and per-report PDFs (reportlab)"},
        ],
        "models": models,
        "traffic": {"total": TEL.total, "errors": TEL.errors, "routes": TEL.traffic()[:14]},
        "assistant": dict(TEL.assistant),
        "audit": list(TEL.audit_log)[:30],
        "hardening": checks,
    }
