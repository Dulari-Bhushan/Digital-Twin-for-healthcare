"""Alert replay: turn per-window event probabilities into clinical alerts and measure lead time.

An alert fires when the (calibrated) probability crosses a threshold; after firing it stays silent for
2 hours (refractory). An episode onset is the first step of a sustained excursion (>= 15 min). An alert
is a true alert if an onset follows within 2 hours (and at least 15 minutes later, so it is actionable).
"""
from __future__ import annotations

import numpy as np

REFRACTORY = 24      # steps (2 h)
MIN_RUN = 3          # steps (15 min) sustained to count as an episode
MIN_LEAD = 3         # steps (15 min) of warning needed for an alert to be actionable
STEP_MIN = 5


def _segments(t: np.ndarray):
    cuts = np.flatnonzero(np.diff(t) != 1) + 1
    return np.split(np.arange(len(t)), cuts)


def onsets(g: np.ndarray, thresh: float, above: bool) -> np.ndarray:
    cond = g > thresh if above else g < thresh
    start = cond & ~np.concatenate([[False], cond[:-1]])
    out, last = [], -10**9
    for i in np.flatnonzero(start):
        if cond[i:i + MIN_RUN].all() and len(cond[i:i + MIN_RUN]) == MIN_RUN and i - last >= REFRACTORY:
            out.append(i)
            last = i
    return np.array(out, dtype=int)


def alert_times(p: np.ndarray, ok: np.ndarray, thr: float) -> np.ndarray:
    fire = (p >= thr) & ok
    out, last = [], -10**9
    for i in np.flatnonzero(fire):
        if i - last >= REFRACTORY:
            out.append(i)
            last = i
    return np.array(out, dtype=int)


def replay(pid, t, g, p, ok, thresh: float, above: bool, thr: float) -> dict:
    """Aggregate over all patients at a single probability threshold."""
    n_on = n_det = n_alert = n_true = 0
    leads, days = [], 0.0
    for q in np.unique(pid):
        sel = np.flatnonzero(pid == q)
        for seg in _segments(t[sel]):
            ix = sel[seg]
            if len(ix) < 3 * REFRACTORY:
                continue
            gs, ps, oks = g[ix], p[ix], ok[ix]
            days += len(ix) * STEP_MIN / 1440.0
            on = onsets(gs, thresh, above)
            al = alert_times(ps, oks, thr)
            n_on += len(on)
            n_alert += len(al)
            for a in al:
                if ((on >= a + MIN_LEAD) & (on <= a + REFRACTORY)).any():
                    n_true += 1
            for o in on:
                prior = al[(al >= o - REFRACTORY) & (al <= o - MIN_LEAD)]
                if len(prior):
                    n_det += 1
                    leads.append((o - prior.min()) * STEP_MIN)
    return {
        "threshold": float(thr), "episodes": n_on, "sensitivity": n_det / max(n_on, 1),
        "alerts": n_alert, "precision": n_true / max(n_alert, 1),
        "false_alerts_per_patient_day": (n_alert - n_true) / max(days, 1e-9),
        "median_lead_min": float(np.median(leads)) if leads else float("nan"),
        "p25_lead_min": float(np.percentile(leads, 25)) if leads else float("nan"),
    }


def sweep(pid, t, g, p, ok, thresh, above, grid=None):
    grid = grid if grid is not None else np.unique(np.round(np.quantile(p[ok > 0], np.linspace(0.5, 0.999, 14)), 4))
    return [replay(pid, t, g, p, ok > 0, thresh, above, thr) for thr in grid]


def pick(rows, max_fa_per_day: float):
    """Highest-sensitivity operating point within a false-alert budget."""
    good = [r for r in rows if r["false_alerts_per_patient_day"] <= max_fa_per_day and r["episodes"] > 0]
    return max(good, key=lambda r: r["sensitivity"]) if good else None
