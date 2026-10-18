"""Scripted two-week stories for the two demo patients, so that every day on the dashboard looks different.

The cohort generator produces statistically similar days. For the demo we want a believable week with a bad day, a
recovery, a good day and an ordinary day, for two patients with very different conditions:

  1688  51-year-old man, 22 years of T2D, insulin/sulfonylurea, moderate retinopathy, albuminuria (UACR 231).
        Story: festival feast, night-time low, a very good day, then a late heavy dinner today.
  1636  34-year-old woman, 3 years of T2D, well controlled, healthy organs.
        Story: a wedding feast, a recovery day, a great day, then an ordinary day today.

Days are indexed 0..13 oldest to newest; day 13 is today. Only these two patients' series are replaced; everything else
in the cohort is untouched. Run on the machine that holds data/synthetic (it keeps a backup of the original series).

Usage:  python src/ingest/demo_stories.py [root]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from synthetic_cohort import CohortConfig, simulate_patient_series  # noqa: E402

D = 14


def _base(n_shift):
    return [{"base_shift": s} for s in n_shift]


def story_a() -> list[dict]:
    """1688: insulin-treated, long-standing diabetes with kidney and eye involvement.

    Two weeks ago control was poor; treatment was intensified last week, so the recent week is better but now brings
    night-time lows. The 14-day mean still matches HbA1c 9.1.
    """
    days = _base([34, 30, 38, 28, 36, 32, 34, -16, -16, -12, 8, -26, -30, -4])
    for i in range(0, 7):
        days[i].update(carb_mult=1.2, walk=False, step_mult=0.6)
    days[9].update(carb_mult=1.25, walk=False, step_mult=0.7)
    days[10] = {"base_shift": 10, "carb_mult": 1.55, "lunch_mult": 1.3, "snacks": [(16 * 60 + 30, 60), (21 * 60 + 40, 45)], "walk": False, "step_mult": 0.45, "hypo": "none"}
    days[11] = {"base_shift": -28, "carb_mult": 1.0, "walk": True, "step_mult": 1.0, "hypo": "night"}
    days[12] = {"base_shift": -32, "carb_mult": 0.75, "walk": True, "step_mult": 1.7, "hypo": "none"}
    days[13] = {"base_shift": -2, "carb_mult": 1.05, "dinner_mult": 1.45, "late_dinner": 70, "walk": False, "step_mult": 0.9, "hypo": "none"}
    return days


def story_b() -> list[dict]:
    """1636: young woman, well controlled."""
    days = _base([2, -3, 4, 0, 6, -2, 3, -4, 2, 0, 0, 0, 0, 0])
    for i in (0, 2, 4, 6, 8):
        days[i].update(walk=True)
    for i in (1, 5, 7):
        days[i].update(walk=False, step_mult=0.8)
    days[9].update(carb_mult=1.15, walk=True)
    days[10] = {"base_shift": 22, "carb_mult": 1.7, "late_dinner": 90, "snacks": [(21 * 60 + 40, 70)], "walk": False, "step_mult": 0.7}
    days[11] = {"base_shift": 6, "carb_mult": 0.9, "walk": True, "step_mult": 1.1}
    days[12] = {"base_shift": -4, "carb_mult": 0.85, "walk": True, "step_mult": 1.7}
    days[13] = {"base_shift": 0, "carb_mult": 0.95, "walk": True, "step_mult": 1.15}
    return days


def run(root: Path) -> None:
    syn = root / "data" / "synthetic"
    pat = pd.read_parquet(syn / "patients.parquet")
    ts_path = syn / "timeseries.parquet"
    ts = pd.read_parquet(ts_path)
    backup = syn / "timeseries_original.parquet"
    if not backup.exists():
        ts.to_parquet(backup, index=False)
    cfg = CohortConfig(n_patients=1, days=D)
    new = []
    for pid, story, seed in ((1688, story_a(), 1688), (1636, story_b(), 1636)):
        row = pat[pat.patient_id == pid].iloc[0]
        new.append(simulate_patient_series(row, cfg, np.random.default_rng(seed), day_cfg=story))
    keep = ts[~ts.patient_id.isin([1688, 1636])]
    pd.concat([keep, *new], ignore_index=True).sort_values(["patient_id", "ts"]).to_parquet(ts_path, index=False)
    for df in new:
        g = df.glucose.to_numpy()
        days = g.reshape(D, 288)
        tir = ((days >= 70) & (days <= 180)).mean(1)
        print(int(df.patient_id.iloc[0]), "TIR by day:", np.round(tir * 100).astype(int).tolist(),
              "lows:", (days < 70).sum(1).tolist())


if __name__ == "__main__":
    run(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("."))
