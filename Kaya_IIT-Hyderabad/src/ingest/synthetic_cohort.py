"""Bridged synthetic cohort for Kaya.

No open dataset links one person's CGM/wearables to liver, eye and kidney outcomes, so we simulate a
cohort whose marginal distributions follow published Indian T2D epidemiology and whose organ labels
follow documented risk relationships (HbA1c, glycemic variability, duration, BP for retinopathy;
insulin resistance, adiposity, PNPLA3 for hepatic fat; FIB-4 for fibrosis; eGFR/UACR for kidney).
Every module is then validated separately on real data (NHANES, CGMacros, APTOS/IDRiD).

This is synthetic: it demonstrates fusion and the mechanisms, not clinical accuracy.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

STEP_MIN = 5
STEPS_PER_DAY = 24 * 60 // STEP_MIN  # 288

# Published allele frequencies used for static genetic markers (South Asian, approximate).
PNPLA3_G_FREQ = 0.45   # rs738409 G, hepatic fat risk allele (higher in Indians)
TCF7L2_T_FREQ = 0.30   # rs7903146 T, T2D risk allele


@dataclass
class CohortConfig:
    n_patients: int = 2000
    days: int = 14
    seed: int = 42


def _gamma_kernel(minutes: np.ndarray, peak_min: float) -> np.ndarray:
    """Glucose excursion shape after a meal, normalised to peak 1 (gamma, shape 3)."""
    shape = 3.0
    scale = peak_min / (shape - 1)
    k = (minutes / scale) ** (shape - 1) * np.exp(-minutes / scale)
    k[minutes < 0] = 0.0
    return k / k.max()


def make_patients(cfg: CohortConfig, rng: np.random.Generator) -> pd.DataFrame:
    n = cfg.n_patients
    age = np.clip(rng.normal(53, 11, n), 25, 85)
    sex = rng.choice(["F", "M"], n, p=[0.45, 0.55])
    male = (sex == "M").astype(float)
    # Asian-Indian phenotype: lower BMI for the same adiposity ("thin-fat"), high waist.
    bmi = np.clip(rng.normal(26.5, 4.2, n), 17.5, 45)
    waist = np.clip(76 + 2.1 * (bmi - 22) + 4 * male + rng.normal(0, 5, n), 60, 140)
    duration = np.clip(rng.gamma(2.0, 4.0, n), 0.2, 35)
    pnpla3 = rng.binomial(2, PNPLA3_G_FREQ, n)
    tcf7l2 = rng.binomial(2, TCF7L2_T_FREQ, n)
    # Insulin resistance (HOMA-IR scale), driven by adiposity, duration, genetics.
    homa_ir = np.exp(
        0.9 + 0.05 * (bmi - 26) + 0.02 * (waist - 90) + 0.12 * tcf7l2 + 0.012 * duration
        + rng.normal(0, 0.35, n)
    )
    metformin = rng.random(n) < 0.78
    hba1c = np.clip(
        7.5 + 0.45 * np.log(homa_ir) + 0.05 * duration + 0.15 * tcf7l2 - 0.5 * metformin
        + rng.normal(0, 1.25, n), 5.8, 14.0,
    )
    sbp = np.clip(118 + 0.35 * (age - 50) + 0.9 * (bmi - 26) + 0.8 * duration / 5 + rng.normal(0, 11, n), 95, 200)
    dbp = np.clip(0.55 * sbp + 12 + rng.normal(0, 6, n), 55, 120)
    # Insulin / sulfonylurea users are the ones exposed to treatment-related hypoglycemia.
    hypo_risk_drug = rng.random(n) < np.clip(0.12 + 0.025 * duration, 0, 0.6)
    carb_frac = np.clip(rng.normal(0.62, 0.07, n), 0.45, 0.8)  # Indian diet: high carbohydrate share
    return pd.DataFrame({
        "patient_id": np.arange(n), "age": age, "sex": sex, "bmi": bmi, "waist_cm": waist,
        "diabetes_duration_yrs": duration, "pnpla3_g_alleles": pnpla3, "tcf7l2_t_alleles": tcf7l2,
        "homa_ir": homa_ir, "metformin": metformin, "hba1c": hba1c, "sbp": sbp, "dbp": dbp,
        "carb_fraction": carb_frac, "on_insulin_or_su": hypo_risk_drug,
    })


def _fast_wearable_day(day_idx: int, p: pd.Series, rng: np.random.Generator):
    """Return (meals, walks, sleep window) for one day. Times are minutes from midnight."""
    meals = []
    for base, sd, carbs in ((8 * 60, 35, 70), (13.5 * 60, 40, 95), (20.5 * 60, 45, 90)):
        t = int(np.clip(rng.normal(base, sd), 5 * 60, 23 * 60))
        c = float(np.clip(rng.normal(carbs * (p.carb_fraction / 0.62), carbs * 0.25), 15, 220))
        meals.append((t, c, float(rng.choice([35.0, 50.0, 65.0], p=[0.3, 0.4, 0.3]))))  # peak minutes
    if rng.random() < 0.5:
        meals.append((int(rng.normal(16.5 * 60, 40)), float(np.clip(rng.normal(30, 12), 8, 70)), 45.0))
    walks = []
    if rng.random() < 0.55:
        walks.append((int(np.clip(rng.normal(18 * 60 + 30, 90), 6 * 60, 22 * 60)), 20))
    bed = int(np.clip(rng.normal(23 * 60, 50), 21 * 60, 26 * 60))   # may roll past midnight
    wake = int(np.clip(rng.normal(6.5 * 60, 40), 4.5 * 60, 9 * 60))
    return meals, walks, bed, wake


def simulate_patient_series(p: pd.Series, cfg: CohortConfig, rng: np.random.Generator) -> pd.DataFrame:
    n_steps = cfg.days * STEPS_PER_DAY
    t = np.arange(n_steps) * STEP_MIN
    glucose = np.zeros(n_steps)
    steps = np.zeros(n_steps)
    asleep = np.zeros(n_steps, dtype=bool)
    meal_flag = np.zeros(n_steps)

    # Insulin sensitivity falls with HOMA-IR; mg/dL rise per 10 g carbohydrate at peak.
    rise_per_10g = np.clip(6.0 + 5.5 * np.log(p.homa_ir) + 1.2 * (p.hba1c - 7), 3.0, 45.0)
    kernel_t = np.arange(0, 6 * 60, STEP_MIN, dtype=float)

    walk_events = []
    for d in range(cfg.days):
        meals, walks, bed, wake = _fast_wearable_day(d, p, rng)
        day0 = d * 24 * 60
        for (tm, carbs, peak) in meals:
            i0 = (day0 + tm) // STEP_MIN
            if i0 >= n_steps:
                continue
            # A walk within 45 min after the meal blunts the excursion (muscle glucose uptake).
            blunt = 1.0
            for (tw, dur) in walks:
                if 0 <= tw - tm <= 45:
                    blunt = 0.68
            amp = rise_per_10g * carbs / 10.0 * blunt * rng.lognormal(0, 0.12)
            k = _gamma_kernel(kernel_t, peak) * amp
            j = min(n_steps, i0 + len(k))
            glucose[i0:j] += k[: j - i0]
            meal_flag[i0] = carbs
        for (tw, dur) in walks:
            i0 = (day0 + tw) // STEP_MIN
            j = min(n_steps, i0 + dur // STEP_MIN)
            if i0 < n_steps:
                steps[i0:j] += rng.normal(110, 15, j - i0).clip(40) * STEP_MIN
                walk_events.append(i0)
        # Treatment-related hypoglycemia: negative excursion on insulin/sulfonylurea (e.g. missed or delayed meal).
        if p.on_insulin_or_su and rng.random() < 0.35:
            th = int(rng.choice([rng.normal(3.0 * 60, 60), rng.normal(16.0 * 60, 70), rng.normal(11.0 * 60, 50)]))
            i0 = (day0 + int(np.clip(th, 60, 23 * 60))) // STEP_MIN
            depth = float(rng.uniform(45, 105))
            k = -_gamma_kernel(kernel_t, 55.0) * depth
            j = min(n_steps, i0 + len(k))
            if i0 < n_steps:
                glucose[i0:j] += k[: j - i0]
        # Sleep window (wraps past midnight)
        b = (day0 + bed) // STEP_MIN
        w = (day0 + 24 * 60 + wake) // STEP_MIN
        asleep[max(0, b):min(n_steps, w)] = True

    # Dawn phenomenon + overnight drift, baseline set so the series mean matches HbA1c-derived mean glucose.
    hour = (t % (24 * 60)) / 60.0
    dawn = 8.0 * np.exp(-0.5 * ((hour - 6.0) / 1.2) ** 2) * (p.hba1c - 5.5) / 3.0
    ar = np.zeros(n_steps)
    eps = rng.normal(0, 3.0, n_steps)
    for i in range(1, n_steps):
        ar[i] = 0.93 * ar[i - 1] + eps[i]
    sensor = rng.normal(0, 2.0, n_steps)
    glucose = glucose + dawn + ar + sensor
    target_mean = 28.7 * p.hba1c - 46.7              # ADAG relation, eAG in mg/dL
    glucose = glucose + (target_mean - glucose.mean())
    glucose = np.clip(glucose, 40, 400)

    # Background daytime steps
    awake = ~asleep
    steps += awake * rng.gamma(1.2, 20.0, n_steps) * rng.binomial(1, 0.5, n_steps)

    # Heart rate / HRV (RMSSD): circadian, lower HRV with high IR, activity raises HR.
    base_hr = 66 + 0.08 * (p.age - 50) + 0.5 * (p.bmi - 26) + 2.0 * np.log(p.homa_ir)
    circadian = 6.0 * np.sin(2 * np.pi * (hour - 9) / 24)
    hr = base_hr + circadian - 8.0 * asleep + steps / 18.0 + rng.normal(0, 2.5, n_steps)
    rmssd_base = np.clip(38 - 0.35 * (p.age - 50) - 4.0 * np.log(p.homa_ir) + rng.normal(0, 4), 8, 80)
    rmssd = np.clip(rmssd_base * (1 + 0.35 * asleep) + rng.normal(0, 3, n_steps) - steps / 40, 4, 120)

    # Sleep stage per step while asleep: 0 awake, 1 light, 2 deep, 3 REM (simple cycle structure)
    stage = np.zeros(n_steps, dtype=np.int8)
    idx = np.flatnonzero(asleep)
    if len(idx):
        phase = ((idx - idx[0]) * STEP_MIN % 90) / 90.0
        pick = np.where(phase < 0.35, 2, np.where(phase < 0.75, 1, 3))
        pick = np.where(rng.random(len(idx)) < 0.04, 0, pick)
        stage[idx] = pick

    ts0 = pd.Timestamp("2026-01-01")
    return pd.DataFrame({
        "patient_id": p.patient_id, "ts": ts0 + pd.to_timedelta(t, unit="m"),
        "glucose": glucose.astype(np.float32), "heart_rate": hr.astype(np.float32),
        "rmssd": rmssd.astype(np.float32), "steps": steps.astype(np.float32),
        "sleep_stage": stage, "meal_carbs_g": meal_flag.astype(np.float32),
    })


def cgm_metrics(g: np.ndarray) -> dict[str, float]:
    return {
        "mean_glucose": float(np.mean(g)),
        "tir": float(np.mean((g >= 70) & (g <= 180))),
        "tbr": float(np.mean(g < 70)),
        "tar": float(np.mean(g > 180)),
        "gv_cv": float(np.std(g) / np.mean(g) * 100),
        "gmi": float(3.31 + 0.02392 * np.mean(g)),
    }


def add_labs_and_outcomes(patients: pd.DataFrame, metrics: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    df = patients.merge(metrics, on="patient_id")
    n = len(df)
    male = (df.sex == "M").astype(float)

    # --- Liver: hepatic fat fraction (%), driven by IR, waist, PNPLA3, post-meal load.
    liver_fat = np.clip(
        np.exp(1.0 + 0.45 * np.log(df.homa_ir) + 0.012 * (df.waist_cm - 90) + 0.22 * df.pnpla3_g_alleles
               + 0.004 * (df.tar * 100) + rng.normal(0, 0.45, n)), 0.5, 45)
    df["liver_fat_pct"] = liver_fat
    df["steatosis"] = liver_fat > 5.5
    tg = np.clip(110 + 35 * np.log(df.homa_ir) + 1.4 * liver_fat + rng.normal(0, 30, n), 40, 700)
    hdl = np.clip(52 - 6 * np.log(df.homa_ir) - 0.15 * (df.waist_cm - 90) + 4 * (1 - male) + rng.normal(0, 7, n), 20, 95)
    alt = np.clip(18 + 1.6 * liver_fat + rng.normal(0, 9, n), 8, 250)
    ast = np.clip(17 + 0.9 * liver_fat + rng.normal(0, 6, n), 8, 200)
    plt_ = np.clip(260 - 1.2 * (df.age - 50) - 2.0 * np.maximum(liver_fat - 15, 0) + rng.normal(0, 40, n), 60, 480)
    df["triglycerides"], df["hdl"], df["alt"], df["ast"], df["platelets"] = tg, hdl, alt, ast, plt_
    df["fib4"] = df.age * df.ast / (df.platelets * np.sqrt(df.alt))
    # Liver stiffness (kPa) rises with cumulative metabolic load; advanced fibrosis label ~ >=8 kPa.
    stiff = np.clip(np.exp(1.55 + 0.018 * (df.age - 50) + 0.035 * (liver_fat - 5) + 0.05 * df.diabetes_duration_yrs / 5
                           + 0.01 * (df.gv_cv - 25) + rng.normal(0, 0.28, n)), 2.5, 60)
    df["liver_stiffness_kpa"] = stiff
    df["advanced_fibrosis"] = stiff >= 8.0

    # --- Eye: diabetic retinopathy grade 0-4 (none, mild, moderate, severe, proliferative).
    z = (-7.4 + 0.42 * (df.hba1c - 7) + 0.11 * df.diabetes_duration_yrs + 0.018 * (df.sbp - 120)
         + 0.03 * (df.gv_cv - 25) - 0.012 * (df.tir * 100 - 50) + rng.normal(0, 0.6, n))
    sev = 1.0 / (1.0 + np.exp(-(z + 4.0)))
    u = rng.random(n)
    grade = np.zeros(n, dtype=int)
    for thr in (0.18, 0.40, 0.65, 0.85):
        grade += (sev > thr * (0.6 + 0.8 * u)).astype(int)
    df["dr_grade"] = np.clip(grade, 0, 4)
    df["dr_any"] = df.dr_grade > 0

    # --- Kidney: eGFR (CKD-EPI 2021), UACR.
    scr = np.clip(0.76 + 0.004 * (df.age - 50) + 0.15 * male + 0.02 * df.diabetes_duration_yrs / 2 + rng.normal(0, 0.12, n), 0.4, 3.5)
    kappa, alpha = np.where(male == 1, 0.9, 0.7), np.where(male == 1, -0.302, -0.241)
    ratio = scr / kappa
    egfr = 142 * np.minimum(ratio, 1) ** alpha * np.maximum(ratio, 1) ** -1.2 * 0.9938 ** df.age * np.where(male == 1, 1.0, 1.012)
    df["egfr"] = egfr
    df["uacr_mg_g"] = np.clip(np.exp(2.6 + 0.35 * (df.hba1c - 7) + 0.012 * (df.sbp - 120) + 0.03 * df.diabetes_duration_yrs + rng.normal(0, 0.9, n)), 2, 3000)
    df["ckd"] = (df.egfr < 60) | (df.uacr_mg_g >= 30)

    # Static EHR fields written for the NLP step later (symptom flags that clinicians would note).
    df["note_fatigue"] = rng.random(n) < (0.12 + 0.35 * df.steatosis * (df.liver_fat_pct > 12))
    df["note_ruq_pain"] = rng.random(n) < (0.03 + 0.18 * (df.liver_stiffness_kpa > 9))
    df["note_blurred_vision"] = rng.random(n) < (0.03 + 0.12 * df.dr_grade)
    return df


def build_cohort(cfg: CohortConfig, out_dir: Path) -> None:
    rng = np.random.default_rng(cfg.seed)
    patients = make_patients(cfg, rng)
    series, metric_rows = [], []
    for _, p in patients.iterrows():
        prng = np.random.default_rng(rng.integers(0, 2**32 - 1))
        s = simulate_patient_series(p, cfg, prng)
        series.append(s)
        metric_rows.append({"patient_id": int(p.patient_id), **cgm_metrics(s["glucose"].to_numpy())})
    full = add_labs_and_outcomes(patients, pd.DataFrame(metric_rows), rng)
    out_dir.mkdir(parents=True, exist_ok=True)
    full.to_parquet(out_dir / "patients.parquet", index=False)
    pd.concat(series, ignore_index=True).to_parquet(out_dir / "timeseries.parquet", index=False)
    print(f"wrote {len(full)} patients, {sum(len(s) for s in series):,} timeseries rows to {out_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("data/synthetic"))
    a = ap.parse_args()
    build_cohort(CohortConfig(a.n, a.days, a.seed), a.out)
