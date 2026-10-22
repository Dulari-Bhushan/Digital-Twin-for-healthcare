"""Per-night wearable summaries, shared by the glucose forecaster and the cardiovascular flag.

A "cycle" is the 24 hours that end at 10:00 on day k (k >= 1): the afternoon and evening of day k-1, the night, and
the early morning of day k. Cycle k is complete at 10:00, which is also the decision time of the cardiovascular flag, so
every feature uses only data that already exists when the prediction is made.

All inputs are on the 5-minute grid. NaN is allowed and ignored.
"""
from __future__ import annotations

import warnings

import numpy as np

STEPS_PER_DAY = 288
CYCLE_OFFSET = 120          # 10:00 in 5-minute steps
NIGHT_START = 120           # night = cycle steps 120..287 (20:00 to 10:00)

METRICS = (
    "sleep_h", "sleep_eff", "deep_frac", "rem_frac", "bed_min", "wake_min",
    "rmssd_night", "rhr", "hr_night_p90", "rmssd_day", "hr_day", "steps24",
    "glu_mean", "glu_cv", "glu_tir", "glu_night",
    "hypo_min", "hypo_deep_min", "glu_min",
)
MIN_SLEEP_STEPS = 24        # a night counts as "worn" when at least two hours of sleep were detected


def cycle_table(glucose, hr, rmssd, steps, stage, days: int) -> np.ndarray:
    """Return (days, len(METRICS)); row 0 is NaN (no full cycle yet), row k is the cycle ending at 10:00 on day k."""
    n = days * STEPS_PER_DAY
    out = np.full((days, len(METRICS)), np.nan, dtype=np.float64)

    def cyc(x):
        return np.asarray(x[CYCLE_OFFSET:CYCLE_OFFSET + (days - 1) * STEPS_PER_DAY], dtype=np.float64).reshape(days - 1, STEPS_PER_DAY)

    g, h, r, st, sg = cyc(glucose[:n]), cyc(hr[:n]), cyc(rmssd[:n]), cyc(steps[:n]), cyc(stage[:n])
    for j in range(days - 1):
        night = np.arange(NIGHT_START, STEPS_PER_DAY)
        sl = sg[j, night] > 0
        n_sl = int(sl.sum())
        row = np.full(len(METRICS), np.nan)
        if n_sl >= MIN_SLEEP_STEPS:                            # at least two hours of detected sleep
            idx = np.flatnonzero(sl)
            span = idx[-1] - idx[0] + 1
            sgn = sg[j, night][sl]
            row[0] = n_sl * 5 / 60.0
            row[1] = n_sl / span
            row[2] = float((sgn == 2).mean())
            row[3] = float((sgn == 3).mean())
            row[4] = (NIGHT_START + idx[0]) * 5 + CYCLE_OFFSET * 5 - 20 * 60         # minutes after 20:00 at which sleep starts
            row[5] = (NIGHT_START + idx[-1]) * 5 + CYCLE_OFFSET * 5 - 20 * 60
            row[6] = float(np.nanmean(r[j, night][sl]))
            row[7] = float(np.nanpercentile(h[j, night][sl], 10))
            row[8] = float(np.nanpercentile(h[j, night][sl], 90))
            row[15] = float(np.nanmean(g[j, night][sl]))
        awake_day = np.arange(0, NIGHT_START)
        row[9] = float(np.nanmean(r[j, awake_day])) if np.isfinite(r[j, awake_day]).any() else np.nan
        row[10] = float(np.nanmean(h[j, awake_day])) if np.isfinite(h[j, awake_day]).any() else np.nan
        row[11] = float(np.nansum(st[j])) if np.isfinite(st[j]).any() else np.nan
        gj = g[j][np.isfinite(g[j])]
        if len(gj) > 100:
            row[12] = gj.mean()
            row[13] = gj.std() / gj.mean() * 100
            row[14] = float(((gj >= 70) & (gj <= 180)).mean())
            row[16] = float((gj < 70).sum() * 5)                   # minutes below 70 mg/dL in the 24 h cycle
            row[17] = float((gj < 54).sum() * 5)                   # minutes below 54 mg/dL (level 2 hypoglycemia)
            row[18] = float(gj.min())
        out[j + 1] = row
    return out


def valid_nights(cycles: np.ndarray, k: int, width: int = 7) -> int:
    """How many of the last `width` cycles ending at k have a usable night (watch worn, sleep detected)."""
    w = cycles[k - width + 1:k + 1, METRICS.index("rmssd_night")]
    return int(np.isfinite(w).sum())


def week_features(cycles: np.ndarray, k: int, width: int = 7) -> tuple[np.ndarray, list[str]]:
    """Seven-cycle summary at decision cycle k: last value, 7-cycle mean, the week's change (last 3 minus first 4) and
    the recent trend (last 2 minus the 2 before), which tells a rising prodrome from a recovering one."""
    w = cycles[k - width + 1:k + 1]
    last = w[-1]
    with warnings.catch_warnings():                            # all-NaN columns (watch not worn) stay NaN
        warnings.simplefilter("ignore", RuntimeWarning)
        mean = np.nanmean(w, axis=0)
        delta = np.nanmean(w[-3:], axis=0) - np.nanmean(w[:-3], axis=0)
        trend = np.nanmean(w[-2:], axis=0) - np.nanmean(w[-4:-2], axis=0)
    names = ([f"{m}_last" for m in METRICS] + [f"{m}_mean7" for m in METRICS] + [f"{m}_delta" for m in METRICS]
             + [f"{m}_trend" for m in METRICS])
    return np.concatenate([last, mean, delta, trend]), names


# Slow context for the glucose forecaster: what the last night and the last week looked like.
SLOW_NAMES = ("sleep_h_last", "sleep_eff_last", "rmssd_night_last", "rmssd_night_mean7", "rhr_last", "rhr_mean7", "steps24_mean7")
SLOW_SRC = (("sleep_h", "last"), ("sleep_eff", "last"), ("rmssd_night", "last"), ("rmssd_night", "mean"),
            ("rhr", "last"), ("rhr", "mean"), ("steps24", "mean"))
SLOW_CENTER = np.array([7.0, 0.95, 43.5, 43.5, 53.0, 53.0, 3450.0], dtype=np.float32)
SLOW_SCALE = np.array([1.0, 0.03, 11.5, 11.5, 5.0, 5.0, 1100.0], dtype=np.float32)


def slow_context(cycles: np.ndarray) -> np.ndarray:
    """(days, 7) slow-context features for every cycle k, using up to the last 7 cycles ending at k. Row 0 is NaN."""
    days = len(cycles)
    out = np.full((days, len(SLOW_SRC)), np.nan, dtype=np.float32)
    ix = {m: i for i, m in enumerate(METRICS)}
    for k in range(1, days):
        w = cycles[max(1, k - 6):k + 1]
        for c, (m, how) in enumerate(SLOW_SRC):
            col = w[:, ix[m]]
            if how == "last":
                out[k, c] = col[-1]
            elif np.isfinite(col).any():
                out[k, c] = np.nanmean(col)
    return out
