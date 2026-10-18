"""Retinopathy progression risk (tabular).

Combines the current DR grade with glycemic exposure, blood pressure and diabetes duration into a 2-year
progression risk. The coefficients are literature-informed ASSUMPTIONS (direction and rough size follow
DCCT/UKPDS findings), not fitted to outcome data, and the dashboard labels the result as a simulation.
The image-based DR grader (APTOS/IDRiD) supplies the current grade when a fundus photo is available.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

GRADES = ["No DR", "Mild NPDR", "Moderate NPDR", "Severe NPDR", "Proliferative DR"]


@dataclass
class EyeParams:
    intercept: float = -3.6
    b_hba1c: float = 0.40       # per HbA1c percentage point above 7
    b_duration: float = 0.07    # per year of diabetes
    b_sbp: float = 0.018        # per mmHg above 120
    b_gv: float = 0.035         # per percentage point of glucose CV above 25
    b_tir: float = -0.014       # per percentage point of time in range above 50
    b_grade: float = 0.55       # per DR grade


def progression_risk(grade: int, hba1c: float, duration: float, sbp: float, gv_cv: float, tir: float,
                     p: EyeParams | None = None) -> float:
    """Probability of progressing by at least one DR grade within 2 years (tir as a fraction 0-1)."""
    p = p or EyeParams()
    z = (p.intercept + p.b_hba1c * (hba1c - 7) + p.b_duration * duration + p.b_sbp * (sbp - 120)
         + p.b_gv * (gv_cv - 25) + p.b_tir * (tir * 100 - 50) + p.b_grade * grade)
    return 1 / (1 + math.exp(-z))


def implied_hba1c(mean_glucose: float) -> float:
    """HbA1c implied by a mean glucose (ADAG): eAG = 28.7 * A1c - 46.7."""
    return (mean_glucose + 46.7) / 28.7
