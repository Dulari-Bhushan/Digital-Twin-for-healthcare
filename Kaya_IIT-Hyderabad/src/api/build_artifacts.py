"""Precompute twin artifacts for a demo cohort of held-out synthetic patients.

Runs the validated glucose ensemble (GRU + LightGBM, conformal intervals, isotonic-calibrated events) over
each patient's last 3 days at 5-minute resolution, replays alerts, and stores everything the API needs as
compact JSON. The API then runs anywhere (no GPU, no model files) and the demo is reproducible from a clone.

Usage (on the GPU box):  PYTHONPATH=src/models:src/whatif python src/api/build_artifacts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import shap
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "models"))
sys.path.insert(0, str(ROOT / "src" / "whatif"))

import alerts as A  # noqa: E402
from names import DEMO_TAGS, name_of  # noqa: E402
import glucose as G  # noqa: E402
from engine import glucose_metrics  # noqa: E402
from eye_risk import implied_hba1c, progression_risk  # noqa: E402
from kidney_dynamic import KIDNEY_FEATURES, projection  # noqa: E402
from liver_dynamic import LiverParams, risk_timeline, static_risk  # noqa: E402
from polish_glucose import LGBBundle, apply_iso, apply_offsets, blend, conformal_offsets, fit_iso  # noqa: E402
from windows import load_synthetic, split_by_patient  # noqa: E402

N_DEMO = 24
SHOW_STEPS = 3 * 288


def r(a, n=1):
    return np.round(np.asarray(a, dtype=float), n).tolist()


def pick_demo(pat: pd.DataFrame, test_ids: np.ndarray) -> list[int]:
    """Spread across risk: sort held-out patients by a composite and take evenly spaced ones."""
    d = pat[pat.patient_id.isin(test_ids)].copy()
    d["score"] = d.hba1c.rank(pct=True) + d.liver_stiffness_kpa.rank(pct=True) + d.dr_grade.rank(pct=True)
    d = d.sort_values("score")
    idx = np.linspace(0, len(d) - 1, N_DEMO).round().astype(int)
    return d.iloc[idx].patient_id.astype(int).tolist()


def main():
    out_dir = ROOT / "artifacts" / "demo"
    out_dir.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    pat = pd.read_parquet(ROOT / "data/synthetic/patients.parquet")
    ts = pd.read_parquet(ROOT / "data/synthetic/timeseries.parquet")
    pol = json.loads((ROOT / "results/glucose_polish.json").read_text())
    wq = pol["synthetic_test"]["blend_weight_gru_quantiles"]
    wp = pol["synthetic_test"]["blend_weight_gru_events"]
    thr = {"hyper": pol["alerts_synthetic"]["hyper"]["chosen"]["<= 1.0 false alerts/patient-day"]["threshold"],
           "hypo": pol["alerts_synthetic"]["hypo"]["chosen"]["<= 1.0 false alerts/patient-day"]["threshold"]}

    syn = load_synthetic(ROOT / "data/synthetic", stride=6)
    tr, va, te = split_by_patient(syn)
    gru = G.GlucoseGRU()
    gru.load_state_dict(torch.load(ROOT / "models/glucose_gru_synthetic.pt", map_location=dev))
    print("fitting LightGBM bundle ...", flush=True)
    bundle = LGBBundle().fit(tr)
    pv = blend(G.predict(gru, va, dev), bundle.predict(va), wq, wp)
    off, isos = conformal_offsets(pv[0], va.y), fit_iso(pv[1], va.ev, va.ev_mask)

    demo = pick_demo(pat, np.unique(te.pid))
    win = load_synthetic(ROOT / "data/synthetic", stride=1, ids=np.array(demo))
    q, p = blend(G.predict(gru, win, dev), bundle.predict(win), wq, wp)
    q, p = apply_offsets(q, off), apply_iso(isos, p)
    print("predictions done", flush=True)

    liver_bundle = joblib.load(ROOT / "models/liver_twin.joblib")
    kidney_bundle = joblib.load(ROOT / "models/kidney_twin.joblib")
    explainers = {("liver", t): shap.TreeExplainer(m) for t, m in liver_bundle["models"].items()}
    explainers.update({("kidney", t): shap.TreeExplainer(m) for t, m in kidney_bundle["models"].items()})

    def drivers(kind, target, X, k=8):
        sv = explainers[(kind, target)].shap_values(X)
        sv = sv[1] if isinstance(sv, list) else sv
        row = np.asarray(sv)[0]
        feats = list(X.columns)
        return [{"feature": feats[i], "value": round(float(X.iloc[0][feats[i]]), 2), "shap": round(float(row[i]), 3)}
                for i in np.argsort(-np.abs(row))[:k]]
    index = []
    for pid in demo:
        row = pat[pat.patient_id == pid].iloc[0]
        s = ts[ts.patient_id == pid].reset_index(drop=True)
        g = s.glucose.to_numpy(np.float64)
        steps_day = float(s.steps.sum() / (len(s) / 288))
        m = glucose_metrics(g, steps_day)
        sel = np.flatnonzero(win.pid == pid)
        t_idx, qs, ps = win.t[sel], q[sel], p[sel]
        keep = t_idx >= len(g) - SHOW_STEPS - 30
        t_idx, qs, ps, sel = t_idx[keep], qs[keep], ps[keep], sel[keep]
        ok = win.ev_mask[sel] > 0
        al = []
        for j, name in enumerate(("hyper", "hypo")):
            for a in A.alert_times(ps[:, j], ok[:, j], thr[name]):
                al.append({"i": int(a), "t": int(t_idx[a]), "type": name, "prob": round(float(ps[a, j]), 3)})
        al.sort(key=lambda x: x["t"])

        labs = pd.DataFrame([{"age": row.age, "male": float(row.sex == "M"), "bmi": row.bmi, "waist_cm": row.waist_cm,
                              "alt": row.alt, "ast": row.ast, "platelets": row.platelets, "hba1c": row.hba1c,
                              "hdl": row.hdl, "diabetes": 1}])
        p_static = {k: float(v[0]) for k, v in static_risk(liver_bundle, labs).items()}
        tl = risk_timeline(p_static, m, 12, LiverParams())
        klabs = pd.DataFrame([{"age": row.age, "male": float(row.sex == "M"), "bmi": row.bmi, "waist_cm": row.waist_cm,
                               "hba1c": row.hba1c, "sbp": row.sbp, "dbp": row.dbp, "hdl": row.hdl, "diabetes": 1}])[KIDNEY_FEATURES]
        k_static = {k: float(v[0]) for k, v in static_risk(kidney_bundle, klabs).items()}
        explain = {"steatosis": drivers("liver", "steatosis", labs[liver_bundle["features"]]),
                   "adv_fibrosis": drivers("liver", "adv_fibrosis", labs[liver_bundle["features"]]),
                   "albuminuria": drivers("kidney", "albuminuria", klabs), "low_egfr": drivers("kidney", "low_egfr", klabs)}
        k_proj = projection(float(row.egfr), float(row.hba1c), float(row.sbp), float(row.uacr_mg_g), m, k_static["albuminuria"])
        eye_now = progression_risk(int(row.dr_grade), row.hba1c, row.diabetes_duration_yrs, row.sbp, m["gv_cv"], m["tir"])

        art = {
            "profile": {"id": int(pid), "name": name_of(pid), "demo_tag": DEMO_TAGS.get(int(pid)), "age": round(float(row.age), 0), "sex": row.sex, "bmi": round(float(row.bmi), 1),
                        "waist_cm": round(float(row.waist_cm), 0), "duration_yrs": round(float(row.diabetes_duration_yrs), 1),
                        "hba1c": round(float(row.hba1c), 1), "sbp": round(float(row.sbp), 0), "dbp": round(float(row.dbp), 0),
                        "on_insulin_or_su": bool(row.on_insulin_or_su), "metformin": bool(row.metformin),
                        "pnpla3_g_alleles": int(row.pnpla3_g_alleles), "tcf7l2_t_alleles": int(row.tcf7l2_t_alleles),
                        "labs": {k: round(float(row[k]), 1) for k in ("alt", "ast", "platelets", "hdl", "triglycerides", "egfr", "uacr_mg_g", "fib4")},
                        "clinic": {"liver_stiffness_kpa": round(float(row.liver_stiffness_kpa), 1),
                                   "liver_fat_pct": round(float(row.liver_fat_pct), 1), "dr_grade": int(row.dr_grade),
                                   "ckd": bool(row.ckd)}},
            "metrics": {k: round(float(v), 4) for k, v in m.items()},
            "liver": {"static": p_static, "timeline": tl},
            "eye": {"grade": int(row.dr_grade), "progression_2y": round(eye_now, 4)},
            "kidney": {"static": k_static, "projection": k_proj},
            "explain": explain,
            "series": {"n": int(len(g)), "glucose": r(g), "heart_rate": r(s.heart_rate, 0), "steps": r(s.steps, 0),
                       "meal_carbs": r(s.meal_carbs_g, 0), "sleep_stage": s.sleep_stage.astype(int).tolist()},
            "forecast": {"t": t_idx.astype(int).tolist(), "q": r(qs, 1), "p": r(ps, 3)},
            "alerts": al,
            "thresholds": thr,
        }
        (out_dir / f"{pid}.json").write_text(json.dumps(art, separators=(",", ":")))
        index.append({"id": int(pid), "age": art["profile"]["age"], "sex": row.sex, "hba1c": art["profile"]["hba1c"],
                      "tir": round(m["tir"], 3), "n_alerts": len(al)})
        print("wrote", pid, flush=True)
    (out_dir / "index.json").write_text(json.dumps({"patients": index, "alert_thresholds": thr,
                                                    "conformal_offsets_mgdl": off.tolist()}, indent=1))


if __name__ == "__main__":
    main()
