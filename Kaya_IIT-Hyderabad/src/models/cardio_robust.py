"""Stress tests for the cardiovascular flag: does it use glucose lows, and how does it behave on thin or messy data?

Four questions, each on patients the models never saw (one patient-grouped split, 75 % train / 25 % test):

1. Glucose lows. The cohort links level-2 hypoglycemia in insulin or sulfonylurea users to cardiac episodes (an
   assumption of the simulator, see `cohort_v2.py`). Does a flag that sees minutes-below-70 and below-54 beat one that
   does not, overall and in those users?
2. Wearable gaps and noise. Whole days with no wrist-wearable data (watch off, charging) and extra sensor noise are added
   to the test patients. Compared: a flag trained on clean data and one trained with gaps.
3. Thin record. Record fields are blanked (filled with the training median) down to "no record at all", the case of a
   newly diagnosed patient. How much does the flag lean on the wearable then?
4. Abstaining. With fewer than MIN_NIGHTS usable nights in the last seven the flag says "not enough data" instead of
   scoring. Reported with the share of mornings that is scored and the alerts that remain.

Usage:  PYTHONPATH=src/models:src/features python src/models/cardio_robust.py --root data/synthetic_v2h
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import cardio as C

GAPS = (0.0, 0.1, 0.2, 0.3, 0.5)
NOISE = (0.0, 1.0, 2.0)                       # extra noise in units of 4 bpm (heart rate) and 5 ms (HRV)
RECORD_MISSING = (0.0, 0.25, 0.5, 1.0)


def blank_record(df: pd.DataFrame, frac: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = df.copy()
    if frac > 0:
        mask = rng.random((len(out), len(C.STATIC))) < frac if frac < 1 else np.ones((len(out), len(C.STATIC)), bool)
        vals = out[C.STATIC].to_numpy(dtype=float).copy()
        vals[mask] = np.nan
        out[C.STATIC] = vals
    return out


def auc(y, p):
    return float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else float("nan")


def replay_row(df, p, thr):
    r = C.alert_replay(df, p, thr)
    return {k: round(float(r[k]), 3) for k in ("sensitivity", "precision", "false_alerts_per_patient_month", "median_lead_h")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("data/synthetic_v2h"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--budget", type=float, default=1.0)
    a = ap.parse_args()
    a.out.mkdir(exist_ok=True, parents=True)

    pat = pd.read_parquet(a.root / "patients.parquet")
    ts = pd.read_parquet(a.root / "timeseries.parquet")
    eps = pd.read_parquet(a.root / "episodes.parquet")
    df = C.dataset_from(pat, ts, eps)
    ids = np.array(sorted(df.patient_id.unique()))
    np.random.default_rng(0).shuffle(ids)
    n_te = len(ids) // 4
    te_ids, tr_ids = ids[:n_te], ids[n_te:]
    tr, te = df[df.patient_id.isin(tr_ids)].reset_index(drop=True), df[df.patient_id.isin(te_ids)].reset_index(drop=True)
    insulin = te.on_insulin_or_su.to_numpy() == 1
    y, pid = te.y.to_numpy(), te.patient_id.to_numpy()
    print(f"train {len(tr):,} mornings / {len(tr_ids)} patients, test {len(te):,} / {len(te_ids)}, "
          f"insulin or SU in test {insulin.mean():.2f}", flush=True)

    res: dict = {"n_train_patients": int(len(tr_ids)), "n_test_patients": int(len(te_ids)), "n_test_mornings": int(len(te)),
                 "min_nights": C.MIN_NIGHTS}

    # ---- 1. glucose lows
    all_wear = C.wearable_columns(df)
    no_hypo = [c for c in all_wear if c.rsplit("_", 1)[0] not in C.HYPO_METRICS and not c.startswith("glu_min")
               and not c.startswith("hypo_")]
    full = C.CardioFlag().fit(tr)
    blind = C.CardioFlag(wear=no_hypo).fit(tr)
    pf, pb = full.predict(te), blind.predict(te)
    ab = {}
    for name, m in (("everyone", np.ones(len(te), bool)), ("insulin_or_sulfonylurea", insulin), ("not_on_insulin_or_su", ~insulin)):
        sc = {"fused": pf[m], "without_glucose_lows": pb[m]}
        b = C.bootstrap_auc(y[m], sc, pid[m], reps=200)
        ab[name] = {"n_mornings": int(m.sum()), "events": int(y[m].sum()), "auroc_with_lows": b["fused"],
                    "auroc_without_lows": b["without_glucose_lows"]}
    res["glucose_lows_ablation"] = ab
    thr = C.operating_point(tr, full.oof_, a.budget)["threshold"]
    res["threshold"] = float(thr)
    print("1 glucose lows done", json.dumps({k: (round(v["auroc_with_lows"]["auroc"], 3), round(v["auroc_without_lows"]["auroc"], 3)) for k, v in ab.items()}), flush=True)

    # ---- 2. wearable gaps and noise: flag trained on clean data vs trained with gaps
    tr_ts = ts[ts.patient_id.isin(tr_ids)]
    aug_df = C.gap_augmented(pat, tr_ts, eps, tr)
    robust = C.CardioFlag().fit(aug_df)
    thr_r = C.operating_point(tr, robust.oof_[:len(tr)], a.budget)["threshold"]       # clean rows only: no duplicated days
    res["threshold_trained_with_gaps"] = float(thr_r)
    te_ts = ts[ts.patient_id.isin(te_ids)]
    rows = []
    for gap, noise in [(g, 0.0) for g in GAPS] + [(0.0, nz) for nz in NOISE if nz > 0]:
        d = C.dataset_from(pat, C.degrade(te_ts, gap, noise, 7), eps).reset_index(drop=True)
        assert len(d) == len(te) and (d.patient_id.to_numpy() == pid).all()
        scored = (d.n_nights.to_numpy() >= C.MIN_NIGHTS)
        row = {"gap": gap, "noise": noise, "mean_usable_nights": round(float(d.n_nights.mean()), 2),
               "share_scored": round(float(scored.mean()), 3),
               "share_events_in_unscored_mornings": round(float(y[~scored].sum() / max(y.sum(), 1)), 3)}
        for tag, flag, th in (("trained_clean", full, thr), ("trained_with_gaps", robust, thr_r)):
            p = flag.predict(d)
            p_abs = np.where(scored, p, 0.0)               # abstain: no score, so no alert
            row[tag] = {"auroc_all_mornings": round(auc(y, p), 3), "auroc_scored_mornings": round(auc(y[scored], p[scored]), 3),
                        "alerts_with_abstain": replay_row(d, p_abs, th)}
        rows.append(row)
        print("2", gap, noise, row["trained_clean"]["auroc_all_mornings"], row["trained_with_gaps"]["auroc_all_mornings"], flush=True)
    res["wearable_gaps_and_noise"] = rows

    # ---- 3. thin record
    thin = []
    for frac in RECORD_MISSING:
        d = blank_record(te, frac, 11)
        s = full.scores(d)
        thin.append({"record_fields_missing": frac, "fused_auroc": round(auc(y, full.predict(d)), 3),
                     "wearable_only_auroc": round(auc(y, s["wearable"]), 3),
                     "alerts": replay_row(d, full.predict(d), thr)})
    res["thin_record"] = thin
    print("3 thin record", [(t["record_fields_missing"], t["fused_auroc"]) for t in thin], flush=True)

    (a.out / "cardio_robustness.json").write_text(json.dumps(res, indent=2))
    (a.out / "cardio_robustness.md").write_text(table(res))
    print(table(res))


def table(r: dict) -> str:
    L = ["# Heart watch: stress tests", "",
         f"Patient-grouped split: {r['n_train_patients']} training and {r['n_test_patients']} test patients "
         f"({r['n_test_mornings']:,} test mornings). Synthetic data; shows behaviour of the method, not clinical accuracy.", "",
         "## 1. Does the flag use glucose lows?", "", "| Patients | Events | AUROC with lows | AUROC without lows | Gain (95% CI) |", "|---|---|---|---|---|"]
    for k, v in r["glucose_lows_ablation"].items():
        w, o = v["auroc_with_lows"], v["auroc_without_lows"]
        g = o["fused_minus_this"] if "fused_minus_this" in o else None
        gs = f"{g['mean']:+.3f} ({g['ci95'][0]:+.3f} to {g['ci95'][1]:+.3f})" if g else ""
        L.append(f"| {k.replace('_', ' ')} | {v['events']} | {w['auroc']:.3f} | {o['auroc']:.3f} | {gs} |")
    L += ["", "## 2. Wearable gaps and noise (AUROC on all mornings; alerts with abstaining under 4 usable nights)", "",
          "| Gap | Noise | Usable nights | Scored | AUROC, trained on clean data | AUROC, trained with gaps | Events caught / false alerts per month: clean-trained | Events caught / false alerts per month: gap-trained |",
          "|---|---|---|---|---|---|---|---|"]
    for x in r["wearable_gaps_and_noise"]:
        c, g = x["trained_clean"], x["trained_with_gaps"]
        L.append(f"| {x['gap']:.0%} | {x['noise']:g} | {x['mean_usable_nights']} / 7 | {x['share_scored']:.0%} | {c['auroc_all_mornings']} | "
                 f"{g['auroc_all_mornings']} | {c['alerts_with_abstain']['sensitivity']:.0%} / {c['alerts_with_abstain']['false_alerts_per_patient_month']} | "
                 f"{g['alerts_with_abstain']['sensitivity']:.0%} / {g['alerts_with_abstain']['false_alerts_per_patient_month']} |")
    L += ["", "## 3. Thin record", "", "| Record fields missing | Fused AUROC | Wearable-only AUROC | Events caught | False alerts per patient-month |", "|---|---|---|---|---|"]
    for x in r["thin_record"]:
        L.append(f"| {x['record_fields_missing']:.0%} | {x['fused_auroc']} | {x['wearable_only_auroc']} | {x['alerts']['sensitivity']:.0%} | {x['alerts']['false_alerts_per_patient_month']} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    import cardio_robust                       # real module name so saved objects unpickle anywhere

    cardio_robust.main()
