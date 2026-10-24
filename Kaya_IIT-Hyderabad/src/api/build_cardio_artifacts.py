"""Precompute the Heart watch demo: a month of one patient's nights, with the cardiovascular flag run every morning.

Every score comes from a cross-validation model that never saw the patient (models/cardio_folds.joblib), so the demo
shows held-out behaviour, including missed events and false alarms. Two groups of patients:

  the 24 demo patients  the same people as the glucose twin (same ids, names, age, HbA1c, blood pressure, kidney and
                        lipid values from artifacts/demo). Their heart data is simulated for this build by the coupled
                        cohort simulator for 28 days; nothing is picked by outcome, so what happens to each person
                        (an event the flag caught or missed, a benign scare, a false alarm, a quiet month) is simply
                        what the held-out model did. KAYA_DEMO_SEED chooses the simulation seed.
  two edge cases        patients from the 2,000-patient cohort, made messy on purpose to show what a real clinic meets
                        and the simulation otherwise hides (ids 100000 and up):
      patchy_data       an event patient with the watch off on about a third of the days: the flag abstains on mornings
                        with too few usable nights and says so
      new_patient       an event patient with no clinical record on file (only age, sex and BMI): the flag leans on the
                        wearable and glucose sensor, and the card says the record is missing

Usage (on the box that holds data/synthetic_v2h and models/):
    PYTHONPATH=src/models:src/features python src/api/build_cardio_artifacts.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "models"))
sys.path.insert(0, str(ROOT / "src" / "features"))
sys.path.insert(0, str(ROOT / "src" / "ingest"))
sys.path.insert(0, str(ROOT / "src" / "api"))
import cardio as C  # noqa: E402
import cohort_v2 as V  # noqa: E402
import nightly as N  # noqa: E402
from names import DEMO_TAGS, name_of  # noqa: E402
from synthetic_cohort import CohortConfig  # noqa: E402

DATA = Path(os.environ.get("KAYA_CARDIO_DATA", ROOT / "data" / "synthetic_v2h"))
DEMO_DIR = ROOT / "artifacts" / "demo"
DEMO_SEED = int(os.environ.get("KAYA_DEMO_SEED", "12"))
OUT = ROOT / "artifacts" / "cardio"
EDGE_ID = 100000                                     # edge-case ids are offset so they never collide with a demo patient
EDGE_NAMES = {"patchy_data": {"M": "Dinesh Patel", "F": "Radha Nair"}, "new_patient": {"M": "Sudhir Kulkarni", "F": "Geeta Pillai"}}
SHOW = ("sleep_h", "sleep_eff", "rmssd_night", "rhr", "steps24", "glu_mean", "glu_tir", "hypo_min")
PATCHY_GAP = 0.35                                    # share of days with the watch off for the patchy-data patient
KNOWN_FIELDS = ("age", "male", "bmi")                # what a newly diagnosed patient has on file
REFRACTORY = 3
N_FOLDS = 5


def clean(a, nd=2):
    return [None if not np.isfinite(x) else round(float(x), nd) for x in a]


def alert_days(p: np.ndarray, ks: np.ndarray, thr: float) -> list[int]:
    out, last = [], -99
    for k, pr in zip(ks, p):
        if pr >= thr and k - last >= REFRACTORY:
            out.append(int(k))
            last = k
    return out


def demo_people() -> pd.DataFrame:
    """The glucose twin's demo patients, as a patients table. Heart-only fields (LDL, smoking, prior cardiovascular
    disease, insulin resistance, carbohydrate habit) are not in the twin's record, so they are drawn here."""
    rows = []
    for f in sorted(DEMO_DIR.glob("[0-9]*.json")):
        p = json.loads(f.read_text())["profile"]
        rows.append({"patient_id": p["id"], "age": p["age"], "sex": p["sex"], "bmi": p["bmi"], "waist_cm": p["waist_cm"],
                     "diabetes_duration_yrs": p["duration_yrs"], "hba1c": p["hba1c"], "sbp": p["sbp"], "dbp": p["dbp"],
                     "on_insulin_or_su": p["on_insulin_or_su"], "metformin": p["metformin"],
                     "tcf7l2_t_alleles": p["tcf7l2_t_alleles"], "hdl": p["labs"]["hdl"], "triglycerides": p["labs"]["triglycerides"],
                     "egfr": p["labs"]["egfr"], "uacr_mg_g": p["labs"]["uacr_mg_g"]})
    return pd.DataFrame(rows)


def simulate_demo(seed: int, big: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """28 days of wearable and glucose data, and the cardiovascular episodes, for each demo patient."""
    pat = demo_people()
    cols = ["age", "bmi", "hba1c", "diabetes_duration_yrs"]
    z = (pat[cols] - big[cols].mean()) / big[cols].std()
    zb = (big[cols] - big[cols].mean()) / big[cols].std()
    nn = [int(((zb - z.iloc[i]) ** 2).sum(axis=1).to_numpy().argmin()) for i in range(len(pat))]
    for c in ("homa_ir", "carb_fraction"):               # from the most similar cohort patient
        pat[c] = big[c].to_numpy()[nn]
    pat = V.add_cardio_static(pat, seed)
    pat["_cv_logit"] = V.RISK_SCALE * V.risk_z(pat) + V.cv_offset(V.risk_z(big))   # same calibration as the cohort
    cfg = CohortConfig(len(pat), 28, seed)
    rng = np.random.default_rng(seed)
    series, rows = [], []
    for _, p in pat.iterrows():
        s, r = V.simulate_patient_v2(p, cfg, np.random.default_rng(rng.integers(0, 2**32 - 1)), hypo_link=True)
        series.append(s)
        rows.extend(r)
    cols_e = ["patient_id", "kind", "warned", "start_step", "event_step", "event_ts", "peak_strain", "p_event", "trigger"]
    return pat.drop(columns="_cv_logit"), pd.concat(series, ignore_index=True), pd.DataFrame(rows, columns=cols_e)


def score(df: pd.DataFrame, folds: dict, fold_of) -> pd.DataFrame:
    """Held-out scores and explanations inputs for every morning in `df`. `fold_of(pid)` names the fold whose model scores it."""
    parts = []
    for f in range(N_FOLDS):
        sub = df[df.patient_id.map(fold_of) == f].copy()
        if sub.empty:
            continue
        s = folds["flags"][f].scores(sub)
        sub["p_fused"], sub["p_wear"], sub["p_record"] = folds["flags"][f].predict(sub), s["wearable"], s["static_logistic"]
        sub["thr"] = folds["thresholds"][f]
        parts.append(sub)
    return pd.concat(parts).sort_values(["patient_id", "k"]).reset_index(drop=True)


def lead_hours(alerts, event_step) -> float:
    """Hours between the first alert inside the horizon and the event; -1 when the event was not warned about."""
    t = event_step / 12.0
    a = [k * 24 + 10 for k in alerts if 0 < t - (k * 24 + 10) <= C.HORIZON_H]
    return t - min(a) if a else -1.0


def story_of(g: pd.DataFrame, events: pd.DataFrame, benign: pd.DataFrame, alerts: list[int], thr: float) -> str:
    """What the held-out flag did for this patient, in one word."""
    rec = float(g.record_pct.mean())
    if len(events):
        return "caught" if lead_hours(alerts, events.event_step.iloc[0]) >= 0 else "missed"
    if len(benign):
        if alerts:
            return "false_alarm"
        pk = benign.event_step.iloc[0] / 288.0
        near = g[(g.k >= pk - 3) & (g.k <= pk + 0.5)]
        return "reassured" if len(near) and near.p_wear.max() >= thr and rec < 0.5 else "benign_quiet"
    if alerts:
        return "false_alarm"
    return "quiet_high_risk" if rec > 0.75 else "quiet"


def main():
    folds = joblib.load(ROOT / "models" / "cardio_folds.joblib")
    df = C.build_dataset(DATA)
    big = pd.read_parquet(DATA / "patients.parquet")
    pat = big.set_index("patient_id")
    eps = pd.read_parquet(DATA / "episodes.parquet")
    ts = pd.read_parquet(DATA / "timeseries.parquet")

    sc = score(df, folds, folds["fold_of"])
    all_logit = np.sort(np.log(sc.p_record / (1 - sc.p_record)).to_numpy())
    sc["record_pct"] = np.searchsorted(all_logit, np.log(sc.p_record / (1 - sc.p_record)).to_numpy()) / len(all_logit)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    index = []

    def make(art_id, row, name, story, group, g, ts_p, thr, flag, events, benign, record_missing=0):
        """Write one patient's artifact. `g` holds the model inputs and scores per morning (from the held-out `flag`)."""
        g = g.reset_index(drop=True)
        cyc = N.cycle_table(ts_p.glucose.to_numpy(), ts_p.heart_rate.to_numpy(), ts_p.rmssd.to_numpy(), ts_p.steps.to_numpy(),
                            ts_p.sleep_stage.to_numpy(), len(ts_p) // 288)
        abstain = g.n_nights.to_numpy() < C.MIN_NIGHTS                  # too few worn nights: no score, no alert
        alerts = alert_days(np.where(abstain, 0.0, g.p_fused.to_numpy()), g.k.to_numpy(), thr)
        expl = flag.explain(g, top=4)
        hypo = cyc[:, N.METRICS.index("hypo_min")]
        off = bool(record_missing)

        def on_file(v, f=lambda x: x):
            return None if off else f(v)

        art = {
            "profile": {"id": int(art_id), "name": name, "story": story, "group": group, "demo_tag": DEMO_TAGS.get(int(art_id)),
                        "age": round(float(row.age)), "sex": row.sex,
                        "bmi": round(float(row.bmi), 1), "record_missing": record_missing,
                        "duration_yrs": on_file(row.diabetes_duration_yrs, lambda v: round(float(v), 1)),
                        "hba1c": on_file(row.hba1c, lambda v: round(float(v), 1)), "sbp": on_file(row.sbp, lambda v: round(float(v))),
                        "ldl": on_file(row.ldl, lambda v: round(float(v))), "smoker": on_file(row.smoker, bool),
                        "prior_cvd": on_file(row.prior_cvd, bool), "egfr": on_file(row.egfr, lambda v: round(float(v))),
                        "on_insulin_or_su": on_file(row.on_insulin_or_su, bool), "metformin": on_file(row.metformin, bool)},
            "days": int(len(ts_p) // 288), "threshold": round(float(thr), 4), "horizon_h": C.HORIZON_H, "min_nights": C.MIN_NIGHTS,
            "nights": {m: clean(cyc[:, N.METRICS.index(m)], 2) for m in SHOW},
            "mornings": [
                {"k": int(r.k), "p": round(float(r.p_fused), 4), "p_wearable": round(float(r.p_wear), 4), "p_record": round(float(r.p_record), 4),
                 "record_pct": round(float(r.record_pct), 3), "alert": bool(r.k in alerts), "abstain": bool(ab), "n_nights": int(r.n_nights),
                 "lows_7d": int(np.nansum(hypo[max(1, r.k - 6):r.k + 1] > 0)),
                 "low_min_7d": round(float(np.nansum(hypo[max(1, r.k - 6):r.k + 1])), 0),
                 "drivers": [{"label": d["label"], "stream": d["stream"], "push": round(d["push"], 2), "value": round(d["value"], 2)} for d in e if np.isfinite(d["value"])]}   # a missing input is not a reason to raise the score
                for r, e, ab in zip(g.itertuples(), expl, abstain)],
            "outcome": {"events": events, "benign_episodes": benign},
        }
        (OUT / f"{art_id}.json").write_text(json.dumps(art, separators=(",", ":")))
        index.append({"id": int(art_id), "name": name, "age": art["profile"]["age"], "sex": row.sex, "story": story, "group": group,
                      "n_alerts": len(alerts), "has_event": bool(events)})

    def days_of(steps):
        return [{"day": round(float(x) / 288.0, 2)} for x in steps]

    def after_warmup(e, kind):
        return e[(e.kind == kind) & (e.event_step > (C.FIRST_K + 1) * 288)]

    # ---- the glucose twin's own patients
    dpat, dts, deps = simulate_demo(DEMO_SEED, big)
    ddf = C.dataset_from(dpat, dts, deps)
    dsc = score(ddf, folds, lambda pid: int(pid) % N_FOLDS)
    dsc["record_pct"] = np.searchsorted(all_logit, np.log(dsc.p_record / (1 - dsc.p_record)).to_numpy()) / len(all_logit)
    dpat = dpat.set_index("patient_id")
    for pid, g in dsc.groupby("patient_id"):
        f = int(pid) % N_FOLDS
        thr = float(folds["thresholds"][f])
        ev, bn = after_warmup(deps[deps.patient_id == pid], "event"), after_warmup(deps[deps.patient_id == pid], "benign")
        al = alert_days(g.p_fused.to_numpy(), g.k.to_numpy(), thr)
        story = story_of(g, ev, bn, al, thr)
        make(pid, dpat.loc[pid], name_of(pid), story, "demo", g, dts[dts.patient_id == pid], thr, folds["flags"][f],
             days_of(ev.event_step), days_of(bn.event_step))
    print("demo patients:", pd.Series([x["story"] for x in index]).value_counts().to_dict(), flush=True)

    # ---- two edge cases from the cohort: the same held-out flag, but degraded inputs
    info = {}
    for pid, g in sc.groupby("patient_id"):
        e = eps[eps.patient_id == pid]
        info[pid] = {"thr": float(g.thr.iloc[0]), "events": after_warmup(e, "event"), "benign": after_warmup(e, "benign")}
    spare = [pid for pid, i in info.items() if len(i["events"]) == 1 and len(i["benign"]) == 0
             and 12 <= i["events"].event_step.iloc[0] / 288.0 <= 27 and i["thr"] > 0]
    rng = np.random.default_rng(3)
    for story in ("patchy_data", "new_patient"):
        done = None
        for cand in (int(c) for c in rng.permutation(spare)):
            i, flag = info[cand], folds["flags"][folds["fold_of"][cand]]
            e_p, ts_p = eps[eps.patient_id == cand], ts[ts.patient_id == cand].copy()
            rec = 0
            if story == "patchy_data":
                mask = np.repeat(np.random.default_rng(cand).random(len(ts_p) // 288) < PATCHY_GAP, 288)
                for c in ("heart_rate", "rmssd", "steps", "sleep_stage"):
                    ts_p[c] = ts_p[c].astype(np.float32)
                    ts_p.loc[mask, c] = np.nan
            g = C.dataset_from(big[big.patient_id == cand], ts_p, e_p)
            if story == "patchy_data":
                if not 2 <= int((g.n_nights < C.MIN_NIGHTS).sum()) <= 12:
                    continue
            else:
                for c in C.STATIC:
                    if c not in KNOWN_FIELDS:
                        g[c] = np.nan
                rec = len([c for c in C.STATIC if c not in KNOWN_FIELDS])
            s_ = flag.scores(g)
            g["p_fused"], g["p_wear"], g["p_record"] = flag.predict(g), s_["wearable"], s_["static_logistic"]
            lg = np.log(g.p_record / (1 - g.p_record)).to_numpy()
            g["record_pct"] = np.searchsorted(all_logit, lg) / len(all_logit)
            row = pat.loc[cand]
            make(EDGE_ID + cand, row, EDGE_NAMES[story][row.sex], story, "edge", g, ts_p, i["thr"], flag,
                 days_of(i["events"].event_step), [], rec)
            spare = [x for x in spare if x != cand]
            done = cand
            break
        print(story, "->", done, flush=True)
    res = json.loads((ROOT / "results" / "cardio_metrics.json").read_text())
    keep = {k: res[k] for k in ("n_mornings", "n_patients", "positive_rate", "horizon_h", "folds", "overall", "auroc_with_ci",
                                "prodrome_event_vs_benign", "alert_replay", "stack_weights", "top_wearable_features_gain")}
    rob = ROOT / "results" / "cardio_robustness.json"
    if rob.exists():
        keep["robustness"] = json.loads(rob.read_text())
    (OUT / "evidence.json").write_text(json.dumps(keep, indent=1))
    (OUT / "index.json").write_text(json.dumps({"patients": index}, indent=1))
    print("wrote", len(index), "patients to", OUT)


if __name__ == "__main__":
    main()
