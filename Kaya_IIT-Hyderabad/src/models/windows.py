"""Windowed forecasting datasets for the glycemic core.

Both the synthetic cohort and the real CGMacros recordings are mapped to one schema:
channels = [glucose, heart_rate, activity (0-1), meal carbs (g at meal start)], 5-minute grid.
Static features = [age, BMI, HbA1c, male, sin(time of day), cos(time of day)].
Targets = glucose change at +30/+60/+120 min, plus two adverse-event onsets within the next 2 h
(hyperglycemia >180 mg/dL and hypoglycemia <70 mg/dL) that are only defined when the patient is
not already in that state at the forecast time.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

STEP_MIN = 5
L = 24                          # 2 h of history
HORIZONS = (6, 12, 24)          # steps ahead: 30, 60, 120 min
FUT = 24                        # event look-ahead window (2 h)
HYPER, HYPO = 180.0, 70.0
SCALE = {"g_mu": 150.0, "g_sd": 60.0, "hr_mu": 70.0, "hr_sd": 20.0, "carb": 100.0}


@dataclass
class Windows:
    x: np.ndarray        # (N, L, 4) scaled
    s: np.ndarray        # (N, 6) static, scaled
    y: np.ndarray        # (N, 3) glucose delta in mg/dL at each horizon
    g_last: np.ndarray   # (N,) glucose at forecast time, mg/dL
    ev: np.ndarray       # (N, 2) event onset labels [hyper, hypo]
    ev_mask: np.ndarray  # (N, 2) 1 where the event is defined (not already in state)
    pid: np.ndarray      # (N,) patient id for patient-level splits

    def subset(self, idx: np.ndarray) -> "Windows":
        return Windows(*(getattr(self, f)[idx] for f in self.__dataclass_fields__))


def _scale_channels(a: np.ndarray) -> np.ndarray:
    out = a.astype(np.float32).copy()
    out[..., 0] = (out[..., 0] - SCALE["g_mu"]) / SCALE["g_sd"]
    out[..., 1] = (out[..., 1] - SCALE["hr_mu"]) / SCALE["hr_sd"]
    out[..., 3] = out[..., 3] / SCALE["carb"]
    return out


def _static(age, bmi, a1c, male, minute_of_day) -> np.ndarray:
    ang = 2 * np.pi * minute_of_day / 1440.0
    n = len(minute_of_day)
    base = np.array([(age - 50) / 15, (bmi - 26) / 5, (a1c - 7.5) / 1.5, male], dtype=np.float32)
    return np.concatenate([np.tile(base, (n, 1)), np.sin(ang)[:, None], np.cos(ang)[:, None]], 1).astype(np.float32)


def make_windows(series: np.ndarray, stat: tuple, pid: int, stride: int, start_minute: int = 0) -> Windows | None:
    """series: (T, 4) raw [glucose, hr, act, carbs] on a 5-min grid (NaN allowed)."""
    T = len(series)
    hmax = max(HORIZONS)
    if T < L + FUT + 2:
        return None
    g = series[:, 0]
    ends = np.arange(L - 1, T - FUT - 1, stride)
    idx = ends[:, None] - np.arange(L - 1, -1, -1)[None, :]
    xw = series[idx]                                             # (N, L, 4)
    fut = sliding_window_view(g[1:], FUT)                        # fut[e] = g[e+1 : e+1+FUT]
    f = fut[ends]
    y = np.stack([g[ends + h] - g[ends] for h in HORIZONS], 1)
    ok = ~np.isnan(xw[:, :, :3]).any((1, 2)) & ~np.isnan(y).any(1) & ~np.isnan(f).any(1)
    if not ok.any():
        return None
    xw, y, f, ends = xw[ok], y[ok], f[ok], ends[ok]
    xw = np.nan_to_num(xw, nan=0.0)                              # carbs NaN -> 0
    gl = g[ends]
    ev = np.stack([(f.max(1) > HYPER), (f.min(1) < HYPO)], 1).astype(np.float32)
    mask = np.stack([gl <= HYPER, gl >= HYPO], 1).astype(np.float32)
    mod = (start_minute + ends * STEP_MIN) % 1440
    return Windows(_scale_channels(xw), _static(*stat, mod), y.astype(np.float32), gl.astype(np.float32),
                   ev, mask, np.full(len(ends), pid, dtype=np.int32))


def concat(ws: list[Windows]) -> Windows:
    return Windows(*(np.concatenate([getattr(w, f) for w in ws]) for f in Windows.__dataclass_fields__))


def load_synthetic(root: Path, stride: int = 6, max_patients: int | None = None) -> Windows:
    pat = pd.read_parquet(root / "patients.parquet")
    ts = pd.read_parquet(root / "timeseries.parquet")
    ts["act"] = np.clip(ts["steps"] / 600.0, 0, 1)
    out = []
    ids = pat.patient_id.to_numpy()[:max_patients]
    for pid, grp in ts[ts.patient_id.isin(ids)].groupby("patient_id", sort=True):
        r = pat.loc[pat.patient_id == pid].iloc[0]
        series = grp[["glucose", "heart_rate", "act", "meal_carbs_g"]].to_numpy(np.float32)
        w = make_windows(series, (r.age, r.bmi, r.hba1c, float(r.sex == "M")), int(pid), stride)
        if w is not None:
            out.append(w)
    return concat(out)


def load_cgmacros(root: Path, stride: int = 3) -> Windows:
    base = root / "x" / "CGMacros"
    bio = pd.read_csv(base / "bio.csv")
    bio.columns = [c.strip() for c in bio.columns]
    out = []
    for _, r in bio.iterrows():
        sid = int(r["subject"])
        f = base / f"CGMacros-{sid:03d}" / f"CGMacros-{sid:03d}.csv"
        if not f.exists():
            continue
        d = pd.read_csv(f, parse_dates=["Timestamp"]).set_index("Timestamp")
        g = d[["Libre GL", "Dexcom GL"]].mean(axis=1, skipna=True)
        d.columns = [c.strip() for c in d.columns]
        mets = next((c for c in d.columns if c.lower() == "mets"), None)
        if mets is None or d[mets].notna().sum() == 0:
            print(f"CGMacros-{sid:03d}: no METs, skipped")
            continue
        act = ((d[mets] / 10.0 - 1.0) / 4.0).clip(0, 1)
        res =pd.DataFrame({
            "g": g.resample("5min").mean(), "hr": d["HR"].resample("5min").mean(),
            "act": act.resample("5min").mean(), "carbs": d["Carbs"].resample("5min").sum(min_count=1),
        })
        res[["g", "hr", "act"]] = res[["g", "hr", "act"]].interpolate(limit=3, limit_area="inside")
        start_minute = res.index[0].hour * 60 + res.index[0].minute
        w = make_windows(res[["g", "hr", "act", "carbs"]].to_numpy(np.float32),
                         (float(r["Age"]), float(r["BMI"]), float(r["A1c PDL (Lab)"]), float(r["Gender"] == "M")),
                         sid, stride, start_minute)
        if w is not None:
            out.append(w)
    return concat(out)


def split_by_patient(w: Windows, frac=(0.7, 0.15, 0.15), seed=0):
    ids = np.unique(w.pid)
    rng = np.random.default_rng(seed)
    rng.shuffle(ids)
    n1, n2 = int(len(ids) * frac[0]), int(len(ids) * (frac[0] + frac[1]))
    parts = [ids[:n1], ids[n1:n2], ids[n2:]]
    return [w.subset(np.flatnonzero(np.isin(w.pid, p))) for p in parts]
