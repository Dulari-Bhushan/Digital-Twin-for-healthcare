"""Summarise how reliable the glucose alerts are, from the saved real-data alert replay (results/glucose_polish.json).

Writes artifacts/demo/alert_evidence.json, which the API serves without needing the results folder. For each alert type it keeps
three operating points on the sensitivity / false-alert trade-off, so a doctor can see what a stricter or looser setting costs.

Usage: python src/api/build_alert_evidence.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUDGETS = (("strict", 0.25), ("balanced", 1.0), ("sensitive", 3.0))      # false alerts per patient-day


def pick(sweep: list[dict], budget: float) -> dict:
    ok = [r for r in sweep if r["false_alerts_per_patient_day"] <= budget]
    return max(ok, key=lambda r: r["sensitivity"]) if ok else min(sweep, key=lambda r: r["false_alerts_per_patient_day"])


def main() -> None:
    d = json.loads((ROOT / "results" / "glucose_polish.json").read_text())["alerts_cgmacros"]
    out = {"source": "Real CGMacros recordings, 34 subjects, alert replay on held-out subjects", "unit": "per patient-day", "events": {}}
    for ev in ("hyper", "hypo"):
        sweep = d[ev]["sweep"]
        pts = []
        for name, budget in BUDGETS:
            r = pick(sweep, budget)
            pts.append({"setting": name, "false_alerts_per_day": round(r["false_alerts_per_patient_day"], 2), "caught": round(r["sensitivity"], 3),
                        "right": round(r["precision"], 3), "median_warning_min": r["median_lead_min"], "episodes": r["episodes"]})
        out["events"][ev] = pts
    p = ROOT / "artifacts" / "demo" / "alert_evidence.json"
    p.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
