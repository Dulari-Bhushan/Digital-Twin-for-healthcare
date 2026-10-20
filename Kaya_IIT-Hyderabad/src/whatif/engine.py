"""What-if engine: re-run a patient's glucose profile under a hypothetical change.

A patient's CGM series is split into a slow baseline and meal-driven excursions. A scenario rescales the
excursions after meals and shifts the baseline, then glucose metrics are recomputed. The effect sizes are
documented ASSUMPTIONS taken from the literature range and from the cohort generator; they are shown to the
clinician, can be edited, and are labelled as simulation.

Scenario fields:
  carb_scale         multiply carbohydrate-driven excursions (e.g. 0.75 = swap part of rice/roti for millets/protein)
  walk_after_meals   minutes of walking after meals (>= 15 min blunts the excursion by walk_blunt)
  baseline_shift     mg/dL shift of the glucose baseline (e.g. -15 for starting/optimising metformin)
  steps_delta        change in daily steps (used by the liver/eye risk models, not by the glucose curve)
  low_scale          multiply the dips below the baseline (insulin or sulfonylurea dose changes make lows rarer or more frequent)
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

STEP_MIN = 5
POST_MEAL_STEPS = 36        # 3 h window after a meal start


@dataclass
class Scenario:
    name: str = "scenario"
    carb_scale: float = 1.0
    walk_after_meals: int = 0
    walk_blunt: float = 0.68
    baseline_shift: float = 0.0
    steps_delta: float = 0.0
    low_scale: float = 1.0

    def describe(self) -> dict:
        return asdict(self)


def decompose(glucose: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """baseline (rolling low quantile over 6 h), positive excursion above it, and negative residual below it."""
    s = pd.Series(glucose)
    base = s.rolling(72, center=True, min_periods=12).quantile(0.25).to_numpy()
    exc = np.maximum(glucose - base, 0.0)
    neg = np.minimum(glucose - base, 0.0)
    return base, exc, neg


def apply_scenario(glucose: np.ndarray, meal_carbs: np.ndarray, sc: Scenario) -> np.ndarray:
    base, exc, neg = decompose(glucose)
    factor = np.ones(len(glucose))
    meal_idx = np.flatnonzero(meal_carbs > 0)
    walk = sc.walk_blunt if sc.walk_after_meals >= 15 else 1.0
    for i in meal_idx:
        factor[i:i + POST_MEAL_STEPS] = sc.carb_scale * walk
    return np.clip(base + sc.baseline_shift + exc * factor + neg * sc.low_scale, 40, 400)


def glucose_metrics(g: np.ndarray, steps_per_day: float) -> dict:
    return {"mean": float(np.mean(g)), "tir": float(np.mean((g >= 70) & (g <= 180))), "tar": float(np.mean(g > 180)),
            "tbr": float(np.mean(g < 70)), "gv_cv": float(np.std(g) / np.mean(g) * 100),
            "gmi": float(3.31 + 0.02392 * np.mean(g)), "steps_per_day": float(steps_per_day)}


def run(glucose: np.ndarray, meal_carbs: np.ndarray, steps_per_day: float, sc: Scenario) -> dict:
    g2 = apply_scenario(glucose, meal_carbs, sc)
    return {"scenario": sc.describe(), "glucose": g2,
            "metrics": glucose_metrics(g2, steps_per_day + sc.steps_delta)}
