"""Run a what-if on one synthetic patient: current habits vs a combined lifestyle + medication change."""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "models"))
from liver_dynamic import LiverParams, risk_timeline, static_risk  # noqa: E402
from engine import Scenario, glucose_metrics, run  # noqa: E402


def patient_inputs(pat: pd.DataFrame, ts: pd.DataFrame, pid: int):
    row = pat[pat.patient_id == pid].iloc[0]
    s = ts[ts.patient_id == pid].reset_index(drop=True)
    labs = pd.DataFrame([{"age": row.age, "male": float(row.sex == "M"), "bmi": row.bmi, "waist_cm": row.waist_cm,
                          "alt": row.alt, "ast": row.ast, "platelets": row.platelets, "hba1c": row.hba1c,
                          "hdl": row.hdl, "diabetes": 1}])
    steps_day = float(s.steps.sum() / (len(s) / 288))
    return row, labs, s.glucose.to_numpy(np.float64), s.meal_carbs_g.to_numpy(np.float64), steps_day


def summarize(label, metrics, tl):
    print(f"{label:34s} TIR {metrics['tir']*100:5.1f}%  TAR {metrics['tar']*100:5.1f}%  GV {metrics['gv_cv']:4.1f}%  "
          f"steatosis 12m {tl['steatosis'][-1]*100:5.1f}%  fibrosis 12m {tl['adv_fibrosis'][-1]*100:5.1f}%")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    pat = pd.read_parquet(root / "data/synthetic/patients.parquet")
    ts = pd.read_parquet(root / "data/synthetic/timeseries.parquet")
    bundle = joblib.load(root / "models/liver_twin.joblib")
    params = LiverParams()
    # a patient with moderate time above range, so interventions visibly move the metrics
    pid = int(pat.iloc[(pat.tar - 0.5).abs().argsort().iloc[7]].patient_id)
    row, labs, g, meals, steps_day = patient_inputs(pat, ts, pid)
    p_static = {k: float(v[0]) for k, v in static_risk(bundle, labs).items()}
    print(f"patient {pid}: age {row.age:.0f}, BMI {row.bmi:.1f}, HbA1c {row.hba1c:.1f}, steps/day {steps_day:.0f}, "
          f"static steatosis {p_static['steatosis']*100:.1f}%, fibrosis {p_static['adv_fibrosis']*100:.1f}%")
    base = glucose_metrics(g, steps_day)
    summarize("current habits", base, risk_timeline(p_static, base, 12, params))
    for sc in (Scenario("walk 20 min after meals", walk_after_meals=20, steps_delta=2000),
               Scenario("smaller carb portions (-25%)", carb_scale=0.75),
               Scenario("both + metformin optimised", carb_scale=0.75, walk_after_meals=20, baseline_shift=-12, steps_delta=2000)):
        r = run(g, meals, steps_day, sc)
        summarize(sc.name, r["metrics"], risk_timeline(p_static, r["metrics"], 12, params))
