"""Coupled synthetic cohort (v2): sleep, HRV, heart rate, steps, glucose and cardiovascular events share one physiology.

The v1 generator (`synthetic_cohort.py`) produces HRV, sleep and steps that do not influence glucose, so a model cannot
gain anything by reading them. v2 adds the couplings that the wearable literature describes, so that fusing the static
record with the dynamic streams is a measurable advantage rather than decoration.

Mechanisms (all sizes are modest, literature-informed assumptions, not fitted clinical effects):

* A hidden daily **autonomic load** `aut` = slow patient-specific variation + episode strain. High load lowers HRV,
  raises resting heart rate, shortens and fragments sleep, lowers steps and raises glucose (stress hyperglycemia).
* **Short sleep** the night before raises next-day insulin resistance (larger meal excursions) and fasting glucose.
* **TCF7L2** risk alleles enlarge post-meal excursions (incretin effect).
* **Insulin or sulfonylurea users** are more likely to go hypoglycemic after exercise and after a light dinner.
* **Prodromal episodes** build over 3 to 5 days. Some end in a cardiovascular event (probability depends on the static
  risk: age, blood pressure, HbA1c, duration, LDL, smoking, prior cardiovascular disease, sex). Others are benign (illness,
  stress, bad week) and look similar on the wearable but resolve. A few events arrive with no warning at all.

* Optional **hypoglycemia link** (`hypo_link=True`): in insulin or sulfonylurea users, a level-2 low (below 54 mg/dL for
  15 minutes or more) can start a short, fast prodrome (1 to 2 days) that ends in a cardiovascular event or resolves.
  This encodes the reported association between severe hypoglycemia and arrhythmia or cardiovascular events as an
  assumption, so the study can measure whether a model that sees glucose lows uses it. It is off by default, which keeps
  every other result on this cohort reproducible.

So a wearable-only model cannot tell a benign episode from a dangerous one, and a static-only model cannot tell when
risk is turning into an event. Only fusing both gives the full answer; the training script measures exactly that.

Outputs: patients.parquet, timeseries.parquet (same columns as v1), episodes.parquet (ground truth for audit and for
the event labels; never a model input).

Usage:  python src/ingest/cohort_v2.py --n 2000 --days 28 --out data/synthetic_v2
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from synthetic_cohort import (  # noqa: E402
    STEP_MIN, STEPS_PER_DAY, CohortConfig, _fast_wearable_day, _gamma_kernel, add_labs_and_outcomes, cgm_metrics,
    make_patients,
)

RISK_SCALE = 1.7               # how strongly the static record decides whether a prodrome ends in an event (assumption)
TARGET_EVENT_SHARE = 0.35      # average chance that a prodromal episode ends in an event
EPISODES_PER_28D = 1.1         # prodromal episodes (event or benign) per patient per 28 days
UNHERALDED_PER_28D = 0.04      # events with no wearable warning
SLEEP_REF_H = 7.5
HYPO_DEEP_MGDL = 54.0          # level 2 hypoglycemia
HYPO_MIN_STEPS = 3             # for at least 15 minutes
HYPO_EVENT_SHIFT = -0.6        # log-odds shift of the event chance after a level-2 low, relative to an ordinary prodrome (assumption)


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def add_cardio_static(pat: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Add LDL, smoking, prior cardiovascular disease and the hidden event propensity (`_cv_logit`)."""
    rng = np.random.default_rng(seed + 1)          # separate stream: leaves the v1 patient draws untouched
    n = len(pat)
    male = (pat.sex == "M").astype(float).to_numpy()
    pat = pat.copy()
    pat["smoker"] = rng.random(n) < (0.04 + 0.22 * male)
    pat["ldl"] = np.clip(rng.normal(104, 30, n) + 0.8 * (pat.diabetes_duration_yrs.to_numpy() - 8), 40, 260)
    prior_logit = -4.0 + 0.05 * (pat.age.to_numpy() - 50) + 0.03 * pat.diabetes_duration_yrs.to_numpy() + 0.5 * male
    pat["prior_cvd"] = rng.random(n) < _sigmoid(prior_logit)
    z = (0.050 * (pat.age.to_numpy() - 53) + 0.014 * (pat.sbp.to_numpy() - 130) + 0.28 * (pat.hba1c.to_numpy() - 8.3)
         + 0.035 * (pat.diabetes_duration_yrs.to_numpy() - 8) + 0.008 * (pat.ldl.to_numpy() - 104)
         + 0.55 * pat.smoker.to_numpy() + 0.9 * pat.prior_cvd.to_numpy() + 0.35 * male)
    lo, hi = -6.0, 6.0                              # shift so the average episode ends in an event TARGET_EVENT_SHARE of the time
    for _ in range(40):
        mid = (lo + hi) / 2
        if _sigmoid(RISK_SCALE * z + mid).mean() > TARGET_EVENT_SHARE:
            hi = mid
        else:
            lo = mid
    pat["_cv_logit"] = RISK_SCALE * z + (lo + hi) / 2
    return pat


def draw_episodes(cv_logit: float, days: int, rng: np.random.Generator) -> list[dict]:
    """Prodromal episodes (3 to 5 days of build-up) and the occasional unheralded event, in 5-minute steps."""
    n_steps = days * STEPS_PER_DAY
    eps: list[dict] = []
    for _ in range(rng.poisson(EPISODES_PER_28D * days / 28.0)):
        ramp_days = int(rng.integers(3, 6))
        end = int(rng.uniform(6.0, days - 0.2) * STEPS_PER_DAY)
        start = end - ramp_days * STEPS_PER_DAY
        if any(abs(end - e["end_step"]) < (ramp_days + 3) * STEPS_PER_DAY for e in eps):
            continue
        is_event = bool(rng.random() < _sigmoid(cv_logit))
        peak = float(rng.uniform(0.85, 1.15) if is_event else rng.uniform(0.45, 0.95))
        eps.append({"kind": "event" if is_event else "benign", "start_step": start, "end_step": end, "peak": peak,
                    "p_event": float(_sigmoid(cv_logit)), "warned": True})
    if rng.random() < UNHERALDED_PER_28D * days / 28.0:
        end = int(rng.uniform(8.0, days - 0.2) * STEPS_PER_DAY)
        if all(abs(end - e["end_step"]) > 6 * STEPS_PER_DAY for e in eps):
            eps.append({"kind": "event", "start_step": end, "end_step": end, "peak": 0.0,
                        "p_event": float(_sigmoid(cv_logit)), "warned": False})
    return sorted(eps, key=lambda e: e["end_step"])


def strain_curve(eps: list[dict], n_steps: int) -> np.ndarray:
    """Episode strain in [0, ~1.15]: builds up to the event or peak, then recovers (events slowly, benign quickly)."""
    s = np.zeros(n_steps, dtype=np.float64)
    for e in eps:
        if not e["warned"]:
            continue
        a, b = max(e["start_step"], 0), min(e["end_step"], n_steps)
        if b > a:
            u = (np.arange(a, b) - e["start_step"]) / max(e["end_step"] - e["start_step"], 1)
            s[a:b] = np.maximum(s[a:b], e["peak"] * u ** 1.4)
        tau = (2.0 if e["kind"] == "event" else 1.2) * STEPS_PER_DAY
        c = min(e["end_step"], n_steps)
        k = np.arange(0, min(n_steps - c, int(6 * tau)))
        if len(k):
            s[c:c + len(k)] = np.maximum(s[c:c + len(k)], e["peak"] * np.exp(-k / tau))
    return s


def hypo_runs(glucose: np.ndarray) -> list[int]:
    """Start steps of level-2 lows (below 54 mg/dL for at least 15 minutes), at most one per 12 hours."""
    low = glucose < HYPO_DEEP_MGDL
    starts, i, n = [], 0, len(low)
    while i < n:
        if low[i]:
            j = i
            while j < n and low[j]:
                j += 1
            if j - i >= HYPO_MIN_STEPS and (not starts or i - starts[-1] >= 144):
                starts.append(i)
            i = j
        else:
            i += 1
    return starts


def hypo_episodes(starts: list[int], eps: list[dict], cv_logit: float, n_steps: int, rng: np.random.Generator) -> list[dict]:
    """A short prodrome (1 to 2 days) after some level-2 lows; ends in an event with a risk-dependent chance."""
    out: list[dict] = []
    for st in starts:
        ramp = int(rng.integers(1, 3)) * STEPS_PER_DAY
        end = st + ramp
        if end >= n_steps - 1 or any(abs(end - e["end_step"]) < 4 * STEPS_PER_DAY for e in eps + out):
            continue
        if rng.random() > 0.5:                                # not every low upsets the heart
            continue
        p_ev = float(_sigmoid(cv_logit + HYPO_EVENT_SHIFT))
        is_event = bool(rng.random() < p_ev)
        peak = float(rng.uniform(0.85, 1.15) if is_event else rng.uniform(0.45, 0.95))
        out.append({"kind": "event" if is_event else "benign", "start_step": st, "end_step": end, "peak": peak,
                    "p_event": p_ev, "warned": True, "trigger": "hypo"})
    return out


def simulate_patient_v2(p: pd.Series, cfg: CohortConfig, rng: np.random.Generator,
                        hypo_link: bool = False) -> tuple[pd.DataFrame, list[dict]]:
    n_steps = cfg.days * STEPS_PER_DAY
    t = np.arange(n_steps) * STEP_MIN
    hour = (t % (24 * 60)) / 60.0

    # ---- hidden autonomic load: slow patient variation + episode strain
    eps = draw_episodes(float(p._cv_logit), cfg.days, rng)
    strain = strain_curve(eps, n_steps)
    chronic = np.zeros(cfg.days)
    chronic[0] = rng.normal(0, 0.25)
    for d in range(1, cfg.days):
        chronic[d] = 0.6 * chronic[d - 1] + rng.normal(0, 0.2)
    aut = np.repeat(chronic, STEPS_PER_DAY) + strain
    aut_pos = np.clip(aut, 0.0, 1.5)

    # ---- per-day plan, then adjust sleep for load and carry last night's sleep into today's insulin sensitivity
    plan = [_fast_wearable_day(d, p, rng, {}) for d in range(cfg.days)]
    bed_adj, wake_adj, sleep_h = [], [], []
    for d, (_, _, bed, wake) in enumerate(plan):
        a_ev = aut[min(max((d * 1440 + int(bed)) // STEP_MIN, 0), n_steps - 1)]
        b2 = int(bed + 22 * np.clip(a_ev, 0, 1.5))
        w2 = int(wake - 28 * np.clip(a_ev, 0, 1.5))
        bed_adj.append(b2)
        wake_adj.append(w2)
        sleep_h.append((1440 + w2 - b2) / 60.0)

    rise_per_10g = np.clip(6.0 + 5.5 * np.log(p.homa_ir) + 1.2 * (p.hba1c - 7), 3.0, 45.0)
    tcf = 1.0 + 0.06 * p.tcf7l2_t_alleles
    kernel_t = np.arange(0, 6 * 60, STEP_MIN, dtype=float)
    glucose = np.zeros(n_steps)
    steps = np.zeros(n_steps)
    asleep = np.zeros(n_steps, dtype=bool)
    meal_flag = np.zeros(n_steps)
    sleep_shift = np.zeros(n_steps)

    for d in range(cfg.days):
        meals, walks, _, _ = plan[d]
        bed, wake = bed_adj[d], wake_adj[d]
        day0 = d * 1440
        prev_sleep = sleep_h[d - 1] if d > 0 else SLEEP_REF_H
        short = max(0.0, SLEEP_REF_H - prev_sleep)
        a_day = float(np.mean(aut[d * STEPS_PER_DAY:(d + 1) * STEPS_PER_DAY]))
        ir_mult = min(1.0 + 0.10 * short, 1.35) * (1.0 + 0.10 * np.clip(a_day, -0.2, 1.5)) * tcf
        sleep_shift[d * STEPS_PER_DAY:(d + 1) * STEPS_PER_DAY] = 3.0 * short
        for (tm, carbs, peak) in meals:
            i0 = (day0 + tm) // STEP_MIN
            if i0 >= n_steps:
                continue
            blunt = 0.68 if any(0 <= tw - tm <= 45 for (tw, _) in walks) else 1.0
            amp = rise_per_10g * ir_mult * carbs / 10.0 * blunt * rng.lognormal(0, 0.12)
            k = _gamma_kernel(kernel_t, peak) * amp
            j = min(n_steps, i0 + len(k))
            glucose[i0:j] += k[: j - i0]
            meal_flag[i0] = carbs
        walk_end = None
        for (tw, dur) in walks:
            i0 = (day0 + tw) // STEP_MIN
            j = min(n_steps, i0 + dur // STEP_MIN)
            if i0 < n_steps:
                steps[i0:j] += rng.normal(110, 15, j - i0).clip(40) * STEP_MIN
            walk_end = tw + dur
        # Treatment-related hypoglycemia is likelier after exercise and after a light dinner.
        dinner = meals[2][1]
        p_hypo = (0.12 + 0.28 * bool(walks) + 0.10 * (dinner < 60)) if p.on_insulin_or_su else 0.0
        if rng.random() < p_hypo:
            if walk_end is not None and rng.random() < 0.7:
                th = walk_end + rng.normal(150, 50)
            else:
                th = int(rng.choice([rng.normal(3.0 * 60, 60), rng.normal(16.0 * 60, 70), rng.normal(11.0 * 60, 50)]))
            depth = float(rng.uniform(45, 105)) * (1.15 if walks else 1.0)
            i0 = (day0 + int(np.clip(th, 60, 23.5 * 60))) // STEP_MIN
            k = -_gamma_kernel(kernel_t, 55.0) * depth
            j = min(n_steps, i0 + len(k))
            if i0 < n_steps:
                glucose[i0:j] += k[: j - i0]
        b = (day0 + bed) // STEP_MIN
        w = (day0 + 1440 + wake) // STEP_MIN
        asleep[max(0, b):min(n_steps, w)] = True

    dawn = 8.0 * np.exp(-0.5 * ((hour - 6.0) / 1.2) ** 2) * (p.hba1c - 5.5) / 3.0
    shocks = rng.normal(0, 3.0, n_steps)
    ar = np.zeros(n_steps)
    for i in range(1, n_steps):
        ar[i] = 0.93 * ar[i - 1] + shocks[i]
    sensor = rng.normal(0, 2.0, n_steps)
    glucose = glucose + dawn + ar + sensor + sleep_shift + 7.0 * aut
    glucose = glucose + ((28.7 * p.hba1c - 46.7) - glucose.mean())
    glucose = np.clip(glucose, 40, 400)

    if hypo_link and p.on_insulin_or_su:                      # level-2 lows start short prodromes that add to the strain
        hrng = np.random.default_rng(int(p.patient_id) * 7919 + cfg.seed)
        extra = hypo_episodes(hypo_runs(glucose), eps, float(p._cv_logit), n_steps, hrng)
        if extra:
            eps = sorted(eps + extra, key=lambda e: e["end_step"])
            aut = aut + strain_curve(extra, n_steps)

    awake = ~asleep
    steps += awake * rng.gamma(1.2, 20.0, n_steps) * rng.binomial(1, 0.5, n_steps)
    steps *= 1.0 - 0.30 * np.clip(aut, 0.0, 1.2)

    base_hr = 66 + 0.08 * (p.age - 50) + 0.5 * (p.bmi - 26) + 2.0 * np.log(p.homa_ir)
    circadian = 6.0 * np.sin(2 * np.pi * (hour - 9) / 24)
    hr = base_hr + circadian - 8.0 * asleep + steps / 18.0 + 9.0 * aut * (1 + 0.35 * asleep) + rng.normal(0, 2.5, n_steps)
    rmssd_base = np.clip(38 - 0.35 * (p.age - 50) - 4.0 * np.log(p.homa_ir) + rng.normal(0, 4), 8, 80)
    rmssd = np.clip(rmssd_base * (1 + 0.35 * asleep) * np.exp(-0.5 * aut * (1 + 0.4 * asleep))
                    + rng.normal(0, 3, n_steps) - steps / 40, 4, 120)

    stage = np.zeros(n_steps, dtype=np.int8)
    idx = np.flatnonzero(asleep)
    if len(idx):
        phase = ((idx - idx[0]) * STEP_MIN % 90) / 90.0
        deep_cut = 0.35 - 0.12 * np.clip(aut[idx], 0, 1.2)
        pick = np.where(phase < deep_cut, 2, np.where(phase < 0.75, 1, 3))
        pick = np.where(rng.random(len(idx)) < 0.04 + 0.08 * np.clip(aut[idx], 0, 1.5), 0, pick)
        stage[idx] = pick

    ts0 = pd.Timestamp("2026-01-01")
    df = pd.DataFrame({
        "patient_id": p.patient_id, "ts": ts0 + pd.to_timedelta(t, unit="m"),
        "glucose": glucose.astype(np.float32), "heart_rate": hr.astype(np.float32),
        "rmssd": rmssd.astype(np.float32), "steps": steps.astype(np.float32),
        "sleep_stage": stage, "meal_carbs_g": meal_flag.astype(np.float32),
    })
    rows = [{"patient_id": int(p.patient_id), "kind": e["kind"], "warned": e["warned"], "start_step": e["start_step"],
             "event_step": e["end_step"], "event_ts": ts0 + pd.Timedelta(minutes=e["end_step"] * STEP_MIN),
             "peak_strain": e["peak"], "p_event": e["p_event"], "trigger": e.get("trigger", "prodrome")} for e in eps]
    return df, rows


def build_cohort_v2(cfg: CohortConfig, out_dir: Path, hypo_link: bool = False) -> None:
    rng = np.random.default_rng(cfg.seed)
    patients = add_cardio_static(make_patients(cfg, rng), cfg.seed)
    series, metric_rows, episode_rows = [], [], []
    for _, p in patients.iterrows():
        prng = np.random.default_rng(rng.integers(0, 2**32 - 1))
        s, rows = simulate_patient_v2(p, cfg, prng, hypo_link)
        series.append(s)
        episode_rows.extend(rows)
        metric_rows.append({"patient_id": int(p.patient_id), **cgm_metrics(s["glucose"].to_numpy())})
    full = add_labs_and_outcomes(patients.drop(columns="_cv_logit"), pd.DataFrame(metric_rows), rng)
    out_dir.mkdir(parents=True, exist_ok=True)
    full.to_parquet(out_dir / "patients.parquet", index=False)
    pd.concat(series, ignore_index=True).to_parquet(out_dir / "timeseries.parquet", index=False)
    cols = ["patient_id", "kind", "warned", "start_step", "event_step", "event_ts", "peak_strain", "p_event", "trigger"]
    pd.DataFrame(episode_rows, columns=cols).to_parquet(out_dir / "episodes.parquet", index=False)
    ev = sum(r["kind"] == "event" for r in episode_rows)
    print(f"wrote {len(full)} patients, {sum(len(s) for s in series):,} rows, "
          f"{ev} cardiovascular events and {len(episode_rows) - ev} benign episodes to {out_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("data/synthetic_v2"))
    ap.add_argument("--hypo-link", action="store_true", help="level-2 lows in insulin or sulfonylurea users can start a cardiac prodrome")
    a = ap.parse_args()
    build_cohort_v2(CohortConfig(a.n, a.days, a.seed), a.out, a.hypo_link)
