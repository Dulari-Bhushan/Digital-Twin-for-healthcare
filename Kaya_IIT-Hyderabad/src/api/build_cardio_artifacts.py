"""Precompute the Heart watch demo: a month of one patient's nights, with the cardiovascular flag run every morning.

Every score comes from the cross-validation model that never saw the patient (models/cardio_folds.joblib), so the demo
shows held-out behaviour, including a missed event and a false alarm. Picks six patients that tell the fusion story (for each outcome, the example with the fewest alerts; the evidence card
gives the overall performance, and alert burden is higher for patients whose record is already high-risk):

  caught            an event the flag warned about at least a day ahead (two of these)
  missed            an event it did not warn about
  reassured         a benign episode that alarmed the wearable model but not the combined model, because the record is low-risk
  false alarm       a benign episode that still triggered an alert
  quiet high risk   a high-risk record with no episode: the flag stays quiet

Usage (on the box that holds data/synthetic_v2 and models/):
    PYTHONPATH=src/models:src/features python src/api/build_cardio_artifacts.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "models"))
sys.path.insert(0, str(ROOT / "src" / "features"))
import cardio as C  # noqa: E402
import nightly as N  # noqa: E402

DATA = ROOT / "data" / "synthetic_v2"
OUT = ROOT / "artifacts" / "cardio"
NAMES_F = ["Sarla Iyer", "Fatima Sheikh", "Kavita Reddy", "Radha Nair", "Geeta Pillai", "Zainab Khan"]
NAMES_M = ["Harish Menon", "Abdul Rahman", "Venkat Rao", "Dinesh Patel", "Sudhir Kulkarni", "Gurpreet Gill"]
SHOW = ("sleep_h", "sleep_eff", "rmssd_night", "rhr", "steps24", "glu_mean", "glu_tir")
REFRACTORY = 3


def clean(a, nd=2):
    return [None if not np.isfinite(x) else round(float(x), nd) for x in a]


def alert_days(p: np.ndarray, ks: np.ndarray, thr: float) -> list[int]:
    out, last = [], -99
    for k, pr in zip(ks, p):
        if pr >= thr and k - last >= REFRACTORY:
            out.append(int(k))
            last = k
    return out


def main():
    folds = joblib.load(ROOT / "models" / "cardio_folds.joblib")
    df = C.build_dataset(DATA)
    pat = pd.read_parquet(DATA / "patients.parquet").set_index("patient_id")
    eps = pd.read_parquet(DATA / "episodes.parquet")
    ts = pd.read_parquet(DATA / "timeseries.parquet")

    # held-out scores and explanations for every morning
    parts = []
    for f, (flag, thr) in enumerate(zip(folds["flags"], folds["thresholds"])):
        sub = df[df.patient_id.map(folds["fold_of"]) == f].copy()
        s = flag.scores(sub)
        sub["p_fused"], sub["p_wear"], sub["p_record"] = flag.predict(sub), s["wearable"], s["static_logistic"]
        sub["thr"] = thr
        parts.append(sub)
    sc = pd.concat(parts).sort_values(["patient_id", "k"]).reset_index(drop=True)
    static_logit = np.log(sc.p_record / (1 - sc.p_record))
    sc["record_pct"] = static_logit.rank(pct=True)

    # classify patients
    info = {}
    for pid, g in sc.groupby("patient_id"):
        thr = float(g.thr.iloc[0])
        al = alert_days(g.p_fused.to_numpy(), g.k.to_numpy(), thr)
        e = eps[eps.patient_id == pid]
        ev = e[(e.kind == "event") & (e.event_step > (C.FIRST_K + 1) * 288)]
        bn = e[(e.kind == "benign") & (e.event_step > (C.FIRST_K + 1) * 288)]
        info[pid] = {"thr": thr, "alerts": al, "events": ev, "benign": bn, "g": g, "rec": float(g.record_pct.mean())}

    def pick(cond, key, n=1, used=()):
        c = [(pid, key(i)) for pid, i in info.items() if pid not in used and cond(i)]
        return [p for p, _ in sorted(c, key=lambda x: x[1])[:n]]

    def lead(i):                                      # hours between the first alert and the event
        t = i["events"].event_step.iloc[0] / 12.0
        a = [k * 24 + 10 for k in i["alerts"] if 0 < t - (k * 24 + 10) <= C.HORIZON_H]
        return t - min(a) if a else -1

    def ev_day(i):
        return i["events"].event_step.iloc[0] / 288.0

    caught = pick(lambda i: len(i["events"]) == 1 and len(i["benign"]) == 0 and lead(i) >= 24 and i["thr"] > 0,
                  lambda i: (len(i["alerts"]), -i["rec"]), 2)
    used = set(caught)
    missed = pick(lambda i: len(i["events"]) == 1 and len(i["benign"]) == 0 and lead(i) < 0 and 12 <= ev_day(i) <= 27,
                  lambda i: (len(i["alerts"]), -i["rec"]), 1, used)
    used |= set(missed)

    def reassured_ok(i):
        if len(i["benign"]) != 1 or len(i["events"]) or i["alerts"]:
            return False
        pk = i["benign"].event_step.iloc[0] / 288.0
        g = i["g"]
        near = g[(g.k >= pk - 3) & (g.k <= pk + 0.5)]
        return len(near) > 0 and near.p_wear.max() >= i["thr"] and i["rec"] < 0.5
    reassured = pick(reassured_ok, lambda i: i["rec"], 1, used)
    used |= set(reassured)
    false_alarm = pick(lambda i: len(i["benign"]) == 1 and not len(i["events"]) and len(i["alerts"]) >= 1 and i["rec"] > 0.6,
                       lambda i: (len(i["alerts"]), -i["rec"]), 1, used)
    used |= set(false_alarm)
    quiet = pick(lambda i: not len(i["events"]) and not len(i["benign"]) and not i["alerts"] and i["rec"] > 0.9, lambda i: -i["rec"], 1, used)
    chosen = [(p, "caught") for p in caught] + [(p, "missed") for p in missed] + [(p, "reassured") for p in reassured] \
        + [(p, "false_alarm") for p in false_alarm] + [(p, "quiet_high_risk") for p in quiet]
    print("chosen", chosen, flush=True)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    index = []
    nf, nm = list(NAMES_F), list(NAMES_M)
    for pid, story in chosen:
        i = info[pid]
        g = i["g"].reset_index(drop=True)
        row = pat.loc[pid]
        flag = folds["flags"][folds["fold_of"][pid]]
        expl = flag.explain(g, top=4)
        s = ts[ts.patient_id == pid]
        cyc = N.cycle_table(s.glucose.to_numpy(), s.heart_rate.to_numpy(), s.rmssd.to_numpy(), s.steps.to_numpy(),
                            s.sleep_stage.to_numpy(), len(s) // 288)
        sex = row.sex
        name = (nm if sex == "M" else nf).pop(0)
        events = [{"day": round(float(x) / 288.0, 2)} for x in i["events"].event_step]
        benign = [{"day": round(float(x) / 288.0, 2)} for x in i["benign"].event_step]
        art = {
            "profile": {"id": int(pid), "name": name, "story": story, "age": round(float(row.age)), "sex": sex, "bmi": round(float(row.bmi), 1),
                        "duration_yrs": round(float(row.diabetes_duration_yrs), 1), "hba1c": round(float(row.hba1c), 1),
                        "sbp": round(float(row.sbp)), "ldl": round(float(row.ldl)), "smoker": bool(row.smoker),
                        "prior_cvd": bool(row.prior_cvd), "egfr": round(float(row.egfr)),
                        "on_insulin_or_su": bool(row.on_insulin_or_su), "metformin": bool(row.metformin)},
            "days": int(len(s) // 288),
            "threshold": round(float(i["thr"]), 4),
            "horizon_h": C.HORIZON_H,
            "nights": {m: clean(cyc[:, N.METRICS.index(m)], 2) for m in SHOW},
            "mornings": [
                {"k": int(r.k), "p": round(float(r.p_fused), 4), "p_wearable": round(float(r.p_wear), 4), "p_record": round(float(r.p_record), 4),
                 "record_pct": round(float(r.record_pct), 3), "alert": bool(r.k in i["alerts"]),
                 "drivers": [{"label": d["label"], "stream": d["stream"], "push": round(d["push"], 2), "value": round(d["value"], 2)} for d in e]}
                for r, e in zip(g.itertuples(), expl)],
            "outcome": {"events": events, "benign_episodes": benign},
        }
        (OUT / f"{pid}.json").write_text(json.dumps(art, separators=(",", ":")))
        index.append({"id": int(pid), "name": name, "age": art["profile"]["age"], "sex": sex, "story": story,
                      "n_alerts": len(i["alerts"]), "has_event": bool(events)})
    res = json.loads((ROOT / "results" / "cardio_metrics.json").read_text())
    keep = {k: res[k] for k in ("n_mornings", "n_patients", "positive_rate", "horizon_h", "folds", "overall", "auroc_with_ci",
                                "prodrome_event_vs_benign", "alert_replay", "stack_weights", "top_wearable_features_gain")}
    (OUT / "evidence.json").write_text(json.dumps(keep, indent=1))
    (OUT / "index.json").write_text(json.dumps({"patients": index}, indent=1))
    print("wrote", len(index), "patients to", OUT)


if __name__ == "__main__":
    main()
