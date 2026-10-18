"""Dynamic liver state: real-data static risk (NHANES) plus a transparent glycemic-load modifier.

baseline  : LightGBM trained on real NHANES labs -> P(steatosis), P(advanced fibrosis).
modifier  : shifts the log-odds by how the patient's last 30-90 days of glucose and activity compare with a
            reference profile (time above range, glycemic variability, daily steps).
dynamics  : the liver responds slowly, so the state moves toward its target with a first-order lag
            (time constant tau, default 90 days), giving a 12-month risk trajectory.

IMPORTANT: the modifier coefficients are literature-informed ASSUMPTIONS, not fitted to outcome data (no open
dataset links CGM patterns to liver outcomes). They are exposed in LiverParams so a clinician can inspect and
change them, and the dashboard labels this component as a simulation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

TWIN_FEATURES = ["age", "male", "bmi", "waist_cm", "alt", "ast", "platelets", "hba1c", "hdl", "diabetes"]


@dataclass
class LiverParams:
    tau_days: float = 90.0
    # log-odds change per unit difference from the reference profile
    beta_tar: float = 2.0          # per +1.0 (100 points) of fraction of time above 180 mg/dL
    beta_gv: float = 0.04          # per +1 percentage point of glucose coefficient of variation
    beta_steps: float = -0.12      # per +1000 steps/day
    ref_tar: float = 0.25
    ref_gv: float = 28.0
    ref_steps: float = 5000.0
    fibrosis_weight: float = 0.5   # fibrosis responds less than steatosis to the same glycemic load
    extra: dict = field(default_factory=dict)


def train_twin_model(nhanes_parquet: Path, out: Path) -> dict:
    import joblib
    import lightgbm as lgb
    import pandas as pd

    df = pd.read_parquet(nhanes_parquet)
    models = {}
    for target in ("steatosis", "adv_fibrosis"):
        models[target] = lgb.LGBMClassifier(n_estimators=250, learning_rate=0.03, num_leaves=8, min_child_samples=30,
                                            subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=2.0,
                                            random_state=0, verbose=-1).fit(df[TWIN_FEATURES], df[target])
    out.parent.mkdir(exist_ok=True, parents=True)
    joblib.dump({"models": models, "features": TWIN_FEATURES}, out)
    return models


def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def _sigmoid(z):
    return 1 / (1 + np.exp(-z))


def static_risk(bundle: dict, labs) -> dict[str, np.ndarray]:
    X = labs[bundle["features"]]
    return {t: m.predict_proba(X)[:, 1] for t, m in bundle["models"].items()}


def load_modifier(metrics: dict, p: LiverParams) -> float:
    """Log-odds shift for steatosis from recent glucose/activity metrics (dict with tar, gv_cv, steps_per_day)."""
    return (p.beta_tar * (metrics["tar"] - p.ref_tar) + p.beta_gv * (metrics["gv_cv"] - p.ref_gv)
            + p.beta_steps * (metrics["steps_per_day"] - p.ref_steps) / 1000.0)


def risk_timeline(p_static: dict[str, float], metrics: dict, months: int = 12, params: LiverParams | None = None) -> dict:
    """Month-by-month risk trajectory when the patient keeps their current profile."""
    params = params or LiverParams()
    shift = load_modifier(metrics, params)
    days = np.arange(0, months * 30 + 1, 30)
    approach = 1 - np.exp(-days / params.tau_days)
    out = {"day": days.tolist()}
    for target, w in (("steatosis", 1.0), ("adv_fibrosis", params.fibrosis_weight)):
        z0 = _logit(p_static[target])
        z = z0 + approach * shift * w
        out[target] = _sigmoid(z).tolist()
    out["load_shift_logodds"] = float(shift)
    return out
