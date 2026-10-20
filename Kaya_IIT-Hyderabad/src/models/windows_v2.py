"""Two-stream windows for the glucose forecaster (v2).

v1 (`windows.py`) fed the model four channels and six static numbers. v2 widens both streams:

  dynamic channels  glucose, heart rate, activity, meal carbs, HRV (RMSSD), sleep stage        (2 h at 5 minutes)
  slow context      last night's sleep length and efficiency, last night and 7-night mean HRV,
                    last night and 7-night mean resting heart rate, 7-night mean steps          (7 numbers)
  static record     v1: age, BMI, HbA1c, sex, time of day (sin, cos)
                    new: diabetes duration, log HOMA-IR, metformin, insulin or sulfonylurea,
                         PNPLA3 and TCF7L2 risk alleles                                         (6 numbers)

Column groups are named so that the ablation can switch each one on or off. Real CGMacros recordings have no HRV, sleep
or genetics: those inputs are set to the training mean and `has_aux` is 0, so one model serves both cases.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "features"))
import nightly as N  # noqa: E402
from windows import FUT, HORIZONS, HYPER, HYPO, L, SCALE, STEP_MIN, Windows, concat  # noqa: E402

CHANNELS = ["glucose", "heart_rate", "activity", "carbs", "hrv", "sleep_stage"]
CH_GROUPS = {"cgm_meals": [0, 3], "hr_activity": [1, 2], "hrv_sleep": [4, 5]}
STATIC_NAMES = (["age", "bmi", "hba1c", "male", "tod_sin", "tod_cos"]
                + ["duration", "log_homa", "metformin", "insulin_su", "pnpla3", "tcf7l2"]
                + list(N.SLOW_NAMES) + ["has_aux"])
ST_GROUPS = {
    "time_of_day": [4, 5],
    "basic_record": [0, 1, 2, 3],
    "full_record": [6, 7, 8, 9],
    "genetics": [10, 11],
    "slow_sleep_hrv": list(range(12, 19)),
    "has_aux": [19],
}
HRV_MU, HRV_SD = 30.0, 15.0


def scale_channels(a: np.ndarray) -> np.ndarray:
    out = a.astype(np.float32).copy()
    out[..., 0] = (out[..., 0] - SCALE["g_mu"]) / SCALE["g_sd"]
    out[..., 1] = (out[..., 1] - SCALE["hr_mu"]) / SCALE["hr_sd"]
    out[..., 3] = out[..., 3] / SCALE["carb"]
    out[..., 4] = (out[..., 4] - HRV_MU) / HRV_SD
    out[..., 5] = out[..., 5] / 3.0
    return out


def static_vector(rec: dict, minute_of_day: np.ndarray, slow: np.ndarray, has_aux: float) -> np.ndarray:
    """(n, 20) static input. `rec` holds scalar record fields; `slow` is (n, 7) already scaled (0 where unknown)."""
    n = len(minute_of_day)
    ang = 2 * np.pi * minute_of_day / 1440.0
    base = np.array([(rec["age"] - 50) / 15, (rec["bmi"] - 26) / 5, (rec["hba1c"] - 7.5) / 1.5, rec["male"]], dtype=np.float32)
    new = np.array([(rec["duration"] - 8) / 6, (rec["log_homa"] - 1.2) / 0.6, rec["metformin"], rec["insulin_su"],
                    rec["pnpla3"] - 0.9, rec["tcf7l2"] - 0.6], dtype=np.float32)
    return np.concatenate([np.tile(base, (n, 1)), np.sin(ang)[:, None], np.cos(ang)[:, None], np.tile(new, (n, 1)),
                           slow.astype(np.float32), np.full((n, 1), has_aux, dtype=np.float32)], 1).astype(np.float32)


def make_windows_v2(series: np.ndarray, rec: dict, slow_by_cycle: np.ndarray | None, pid: int, stride: int,
                    start_minute: int = 0, has_aux: float = 1.0) -> Windows | None:
    """series: (T, 6) raw channels on a 5-minute grid. slow_by_cycle: (days, 7) raw slow context, or None."""
    T = len(series)
    if T < L + FUT + 2:
        return None
    g = series[:, 0]
    ends = np.arange(L - 1, T - FUT - 1, stride)
    if slow_by_cycle is not None:                      # windows need a complete night behind them
        k = (ends - N.CYCLE_OFFSET) // N.STEPS_PER_DAY
        ends = ends[(k >= 1) & (k < len(slow_by_cycle))]
        k = (ends - N.CYCLE_OFFSET) // N.STEPS_PER_DAY
        slow_raw = slow_by_cycle[k]
        keep = np.isfinite(slow_raw).all(1)
        ends, slow_raw = ends[keep], slow_raw[keep]
        slow = (slow_raw - N.SLOW_CENTER) / N.SLOW_SCALE
    else:
        slow = np.zeros((len(ends), len(N.SLOW_NAMES)), dtype=np.float32)
    if len(ends) == 0:
        return None
    idx = ends[:, None] - np.arange(L - 1, -1, -1)[None, :]
    xw = series[idx]
    fut = sliding_window_view(g[1:], FUT)
    f = fut[ends]
    y = np.stack([g[ends + h] - g[ends] for h in HORIZONS], 1)
    ok = ~np.isnan(xw[:, :, :3]).any((1, 2)) & ~np.isnan(y).any(1) & ~np.isnan(f).any(1)
    if not ok.any():
        return None
    xw, y, f, ends, slow = xw[ok], y[ok], f[ok], ends[ok], slow[ok]
    xw = np.nan_to_num(xw, nan=0.0)
    if slow_by_cycle is None:                          # unknown channels sit at their scaling mean (0 after scaling)
        xw[:, :, 4] = HRV_MU
        xw[:, :, 5] = 0.0
    gl = g[ends]
    ev = np.stack([(f.max(1) > HYPER), (f.min(1) < HYPO)], 1).astype(np.float32)
    mask = np.stack([gl <= HYPER, gl >= HYPO], 1).astype(np.float32)
    mod = (start_minute + ends * STEP_MIN) % 1440
    return Windows(scale_channels(xw), static_vector(rec, mod, slow, has_aux), y.astype(np.float32), gl.astype(np.float32),
                   ev, mask, np.full(len(ends), pid, dtype=np.int32), ends.astype(np.int32))


def load_synthetic_v2(root: Path, stride: int = 6, max_patients: int | None = None) -> Windows:
    pat = pd.read_parquet(root / "patients.parquet")
    ts = pd.read_parquet(root / "timeseries.parquet")
    ts["act"] = np.clip(ts["steps"] / 600.0, 0, 1)
    out = []
    ids = pat.patient_id.to_numpy()[:max_patients]
    for pid, grp in ts[ts.patient_id.isin(ids)].groupby("patient_id", sort=True):
        r = pat.loc[pat.patient_id == pid].iloc[0]
        days = len(grp) // N.STEPS_PER_DAY
        cyc = N.cycle_table(grp.glucose.to_numpy(), grp.heart_rate.to_numpy(), grp.rmssd.to_numpy(),
                            grp.steps.to_numpy(), grp.sleep_stage.to_numpy(), days)
        slow = N.slow_context(cyc)
        series = grp[["glucose", "heart_rate", "act", "meal_carbs_g", "rmssd", "sleep_stage"]].to_numpy(np.float32)
        rec = {"age": r.age, "bmi": r.bmi, "hba1c": r.hba1c, "male": float(r.sex == "M"), "duration": r.diabetes_duration_yrs,
               "log_homa": float(np.log(r.homa_ir)), "metformin": float(r.metformin), "insulin_su": float(r.on_insulin_or_su),
               "pnpla3": float(r.pnpla3_g_alleles), "tcf7l2": float(r.tcf7l2_t_alleles)}
        w = make_windows_v2(series, rec, slow, int(pid), stride)
        if w is not None:
            out.append(w)
    return concat(out)


def select(w: Windows, channels: list[int], static: list[int]) -> Windows:
    """A view of the windows with only some channels and static columns, for the ablation."""
    return Windows(np.ascontiguousarray(w.x[:, :, channels]), np.ascontiguousarray(w.s[:, static]), w.y, w.g_last, w.ev,
                   w.ev_mask, w.pid, w.t)


# Ablation ladder: each rung adds one input group to the one before it.
def rung(name: str) -> tuple[list[int], list[int]]:
    ch = lambda *g: sorted(sum((CH_GROUPS[x] for x in g), []))      # noqa: E731
    st = lambda *g: sorted(sum((ST_GROUPS[x] for x in g), []))      # noqa: E731
    table = {
        "cgm_meals": (ch("cgm_meals"), st("time_of_day")),
        "plus_hr_activity": (ch("cgm_meals", "hr_activity"), st("time_of_day")),
        "plus_basic_record": (ch("cgm_meals", "hr_activity"), st("time_of_day", "basic_record")),
        "plus_hrv_sleep": (ch("cgm_meals", "hr_activity", "hrv_sleep"), st("time_of_day", "basic_record", "slow_sleep_hrv")),
        "full_fusion": (ch("cgm_meals", "hr_activity", "hrv_sleep"),
                        st("time_of_day", "basic_record", "full_record", "genetics", "slow_sleep_hrv")),
        "full_minus_hrv_sleep": (ch("cgm_meals", "hr_activity"),
                                 st("time_of_day", "basic_record", "full_record", "genetics")),
        "full_minus_record": (ch("cgm_meals", "hr_activity", "hrv_sleep"),
                              st("time_of_day", "basic_record", "slow_sleep_hrv")),
        "full_minus_genetics": (ch("cgm_meals", "hr_activity", "hrv_sleep"),
                                st("time_of_day", "basic_record", "full_record", "slow_sleep_hrv")),
    }
    return table[name]


RUNGS = ("cgm_meals", "plus_hr_activity", "plus_basic_record", "plus_hrv_sleep", "full_fusion",
         "full_minus_hrv_sleep", "full_minus_record", "full_minus_genetics")
