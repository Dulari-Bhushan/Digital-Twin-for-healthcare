"""Dynamic kidney state: eGFR trajectory and albuminuria drift.

baseline  : real-data NHANES model gives P(albuminuria) and P(reduced eGFR) from routine measurements.
trajectory: eGFR declines linearly at a patient-specific slope. The slope starts from age-related decline and adds
            terms for glycemic control (HbA1c), blood pressure, existing albuminuria and glucose variability.
drift     : albuminuria risk moves toward a glycemic-load target with a 180-day lag (as the liver module does).

IMPORTANT: slope coefficients are literature-informed ASSUMPTIONS (typical decline is about 1 mL/min/1.73m2/year with
aging and 2 to 4 with diabetic kidney disease), not fitted to outcome data. They are exposed in KidneyParams and shown
in the product as a simulation. Blood pressure is not changed by what-if scenarios.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

KIDNEY_FEATURES = ["age", "male", "bmi", "waist_cm", "hba1c", "sbp", "dbp", "hdl", "diabetes"]


@dataclass
class KidneyParams:
    base_decline: float = 0.9      # mL/min/1.73m2 per year (aging)
    b_hba1c: float = 0.40          # per HbA1c percentage point above 7
    b_sbp: float = 0.03            # per mmHg above 120
    albuminuria_extra: float = 1.2 # if UACR >= 30 mg/g
    b_gv: float = 0.02             # per glucose CV point above 28
    min_slope: float = 0.3
    max_slope: float = 8.0
    tau_days: float = 180.0
    beta_tar: float = 1.2          # albuminuria log-odds per +1.0 of time above range
    beta_gv: float = 0.025         # albuminuria log-odds per CV point
    ref_tar: float = 0.25
    ref_gv: float = 28.0


def decline_slope(hba1c: float, sbp: float, uacr: float, gv_cv: float, p: KidneyParams) -> float:
    s = (p.base_decline + p.b_hba1c * max(hba1c - 7.0, 0.0) + p.b_sbp * max(sbp - 120.0, 0.0)
         + (p.albuminuria_extra if uacr >= 30 else 0.0) + p.b_gv * max(gv_cv - p.ref_gv, 0.0))
    return float(np.clip(s, p.min_slope, p.max_slope))


def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def projection(egfr0: float, hba1c: float, sbp: float, uacr: float, metrics: dict, p_alb: float,
               years: int = 5, p: KidneyParams | None = None) -> dict:
    """metrics: dict with tar and gv_cv (current 14-day glucose profile)."""
    p = p or KidneyParams()
    slope = decline_slope(hba1c, sbp, uacr, metrics["gv_cv"], p)
    months = np.arange(0, years * 12 + 1, 6)
    egfr = np.maximum(egfr0 - slope * months / 12.0, 5.0)
    y60 = float((egfr0 - 60.0) / slope) if egfr0 > 60 else 0.0
    days = np.arange(0, 12 * 30 + 1, 30)
    shift = p.beta_tar * (metrics["tar"] - p.ref_tar) + p.beta_gv * (metrics["gv_cv"] - p.ref_gv)
    alb = 1 / (1 + np.exp(-(_logit(p_alb) + (1 - np.exp(-days / p.tau_days)) * shift)))
    return {"slope_per_year": slope, "month": months.tolist(), "egfr": np.round(egfr, 1).tolist(),
            "years_to_egfr60": round(y60, 1), "albuminuria_month": (days // 30).tolist(), "albuminuria": np.round(alb, 4).tolist()}
