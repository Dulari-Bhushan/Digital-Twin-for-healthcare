import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "ingest"))
from cohort_v2 import build_cohort_v2  # noqa: E402
from synthetic_cohort import STEPS_PER_DAY, CohortConfig  # noqa: E402

CFG = CohortConfig(n_patients=120, days=28, seed=11)


def _build(tmp_path):
    build_cohort_v2(CFG, tmp_path)
    return (pd.read_parquet(tmp_path / "patients.parquet"), pd.read_parquet(tmp_path / "timeseries.parquet"),
            pd.read_parquet(tmp_path / "episodes.parquet"))


def test_shapes_and_columns_match_v1(tmp_path):
    pat, ts, eps = _build(tmp_path)
    assert len(pat) == 120 and len(ts) == 120 * 28 * STEPS_PER_DAY
    assert {"glucose", "heart_rate", "rmssd", "steps", "sleep_stage", "meal_carbs_g"} <= set(ts.columns)
    assert {"smoker", "ldl", "prior_cvd"} <= set(pat.columns) and "_cv_logit" not in pat.columns
    assert ts.glucose.between(40, 400).all() and ts.rmssd.between(4, 120).all()
    assert {"event", "benign"} >= set(eps.kind.unique())


def test_events_exist_and_risk_drives_them(tmp_path):
    pat, _, eps = _build(tmp_path)
    assert (eps.kind == "event").sum() >= 10
    assert (eps.kind == "benign").sum() >= 10
    # Higher-risk patients turn more episodes into events (p_event is the hidden risk, monotone in static fields).
    warned = eps[eps.warned]
    assert np.corrcoef(warned.p_event, (warned.kind == "event").astype(float))[0, 1] > 0.1


def test_strain_shows_in_wearables(tmp_path):
    """In the 48 h before a warned event, HRV is lower and heart rate higher than the patient's first week."""
    _, ts, eps = _build(tmp_path)
    ev = eps[(eps.kind == "event") & eps.warned & (eps.event_step > 9 * STEPS_PER_DAY)]
    assert len(ev) >= 5
    d_hrv, d_hr = [], []
    for _, e in ev.iterrows():
        s = ts[ts.patient_id == e.patient_id].reset_index(drop=True)
        base, late = s.iloc[: 5 * STEPS_PER_DAY], s.iloc[e.event_step - 2 * STEPS_PER_DAY: e.event_step]
        d_hrv.append(late.rmssd.mean() / base.rmssd.mean() - 1)
        d_hr.append(late.heart_rate.mean() - base.heart_rate.mean())
    assert np.mean(d_hrv) < -0.15
    assert np.mean(d_hr) > 4.0


def test_short_sleep_raises_next_day_glucose(tmp_path):
    """Nights shorter than 6.5 h are followed by higher mean glucose than nights longer than 8 h."""
    _, ts, _ = _build(tmp_path)
    short, long_ = [], []
    for _, s in ts.groupby("patient_id"):
        asleep = (s.sleep_stage.to_numpy() > 0).reshape(28, STEPS_PER_DAY)
        gl = s.glucose.to_numpy().reshape(28, STEPS_PER_DAY)
        hours = asleep.sum(1) * 5 / 60.0
        dev = gl.mean(1) - gl.mean()
        for d in range(1, 28):
            if hours[d - 1] < 6.5:
                short.append(dev[d])
            elif hours[d - 1] > 8:
                long_.append(dev[d])
    assert len(short) > 30 and len(long_) > 30
    assert np.mean(short) > np.mean(long_)


def test_reproducible(tmp_path):
    cfg = CohortConfig(n_patients=15, days=10, seed=3)
    build_cohort_v2(cfg, tmp_path / "a")
    build_cohort_v2(cfg, tmp_path / "b")
    for f in ("patients", "timeseries", "episodes"):
        pd.testing.assert_frame_equal(pd.read_parquet(tmp_path / "a" / f"{f}.parquet"),
                                      pd.read_parquet(tmp_path / "b" / f"{f}.parquet"))
