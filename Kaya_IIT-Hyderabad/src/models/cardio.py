"""Cardiovascular anomaly flag: a week of sleep, heart-rate and HRV data fused with the static record.

Every morning at 10:00 the flag looks at the last seven wearable cycles (sleep length and efficiency, deep and REM
share, night HRV, resting heart rate, steps, glucose control) and at the static EHR (age, blood pressure, HbA1c,
duration, LDL, smoking, prior cardiovascular disease, kidney function), and returns the probability of a cardiovascular
event within the next 48 hours, with the features that pushed the score up.

Fusion is explicit. A wearable model says whether a prodrome (falling HRV, rising resting heart rate, shrinking sleep)
is under way; a static-record model says how dangerous that is for this person; a small logistic stacker combines the
two log-odds. The training script compares static only, wearable only, a simple clinical rule, a single model fed both
streams side by side (early fusion) and the stacked model (late fusion), with patient-grouped cross-validation, so the
value of fusing the two streams is measured, not assumed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "features"))
import nightly as N  # noqa: E402

STEPS_PER_DAY = N.STEPS_PER_DAY
HORIZON_H = 72
CARE_H = 72                                            # mornings in the 72 h after an event are excluded
FIRST_K = 7                                            # first decision cycle: needs seven complete cycles
STATIC = ["age", "male", "bmi", "sbp", "dbp", "hba1c", "diabetes_duration_yrs", "ldl", "hdl", "triglycerides",
          "smoker", "prior_cvd", "egfr", "log_uacr"]
HUMAN = {
    "sleep_h": "sleep duration", "sleep_eff": "sleep efficiency", "deep_frac": "deep-sleep share", "rem_frac": "REM share",
    "bed_min": "bedtime", "wake_min": "wake time", "rmssd_night": "night HRV (RMSSD)", "rhr": "resting heart rate",
    "hr_night_p90": "night heart rate (90th pct)", "rmssd_day": "daytime HRV", "hr_day": "daytime heart rate",
    "steps24": "daily steps", "glu_mean": "mean glucose", "glu_cv": "glucose variability", "glu_tir": "time in range",
    "glu_night": "night glucose",
    "age": "age", "male": "sex", "bmi": "BMI", "sbp": "systolic blood pressure", "dbp": "diastolic blood pressure",
    "hba1c": "HbA1c", "diabetes_duration_yrs": "diabetes duration", "ldl": "LDL cholesterol", "hdl": "HDL cholesterol",
    "triglycerides": "triglycerides", "smoker": "smoking", "prior_cvd": "prior cardiovascular disease", "egfr": "eGFR",
    "log_uacr": "urine albumin",
}


def static_frame(pat: pd.DataFrame) -> pd.DataFrame:
    """Static model inputs from a patients table (v2 cohort columns)."""
    s = pd.DataFrame({"patient_id": pat.patient_id.to_numpy()})
    s["male"] = (pat.sex == "M").astype(float).to_numpy()
    s["log_uacr"] = np.log(pat.uacr_mg_g.to_numpy())
    for c in STATIC:
        if c not in s:
            s[c] = pat[c].astype(float).to_numpy()
    return s


def describe(feature: str) -> str:
    """Plain-language name of a model feature such as 'rmssd_night_delta'."""
    for suffix, text in (("_last", "last night"), ("_mean7", "7-day average"), ("_delta", "change over the week"),
                         ("_trend", "last two days vs the two before")):
        if feature.endswith(suffix):
            return f"{HUMAN.get(feature[: -len(suffix)], feature)} ({text})"
    return HUMAN.get(feature, feature)


def build_dataset(root: Path, horizon_h: int = HORIZON_H) -> pd.DataFrame:
    """One row per patient-morning: week features, static record, label and (for analysis only) the episode kind."""
    pat = pd.read_parquet(root / "patients.parquet")
    ts = pd.read_parquet(root / "timeseries.parquet")
    eps = pd.read_parquet(root / "episodes.parquet")
    stat = static_frame(pat).set_index("patient_id")
    rows, names = [], []
    h_steps, care_steps = horizon_h * 12, CARE_H * 12
    for pid, s in ts.groupby("patient_id", sort=True):
        days = len(s) // STEPS_PER_DAY
        cyc = N.cycle_table(s.glucose.to_numpy(), s.heart_rate.to_numpy(), s.rmssd.to_numpy(), s.steps.to_numpy(),
                            s.sleep_stage.to_numpy(), days)
        e = eps[eps.patient_id == pid]
        ev_steps = e.event_step[e.kind == "event"].to_numpy()
        for k in range(FIRST_K, days):
            t_dec = k * STEPS_PER_DAY + N.CYCLE_OFFSET
            if ((t_dec - ev_steps > 0) & (t_dec - ev_steps <= care_steps)).any():
                continue                                    # just after an event the patient is in care: not scored
            f, names = N.week_features(cyc, k)
            nxt = ev_steps[(ev_steps > t_dec) & (ev_steps <= t_dec + h_steps)]
            win = e[(e.event_step > t_dec) & (e.event_step <= t_dec + h_steps) & e.warned]
            kind = "none" if win.empty else ("event" if (win.kind == "event").any() else "benign")
            rows.append([pid, k, t_dec, int(len(nxt) > 0), (nxt[0] - t_dec) * 5 / 60.0 if len(nxt) else np.nan, kind, *f])
    cols = ["patient_id", "k", "t_dec", "y", "hours_to_event", "episode_kind"] + names
    df = pd.DataFrame(rows, columns=cols)
    return pd.concat([df, stat.loc[df.patient_id].reset_index(drop=True)[STATIC]], axis=1)


def wearable_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.endswith(("_last", "_mean7", "_delta", "_trend"))]


def rule_score(df: pd.DataFrame) -> np.ndarray:
    """A transparent clinician-style rule: HRV falling, resting heart rate rising, sleep shrinking over the week."""
    hrv = np.clip(-df.rmssd_night_delta / df.rmssd_night_mean7 / 0.15, 0, None)
    hr = np.clip(df.rhr_delta / 4.0, 0, None)
    sl = np.clip(-df.sleep_h_delta / 0.8, 0, None)
    return (hrv + hr + sl).fillna(0).to_numpy()


def fit_gbm(Xtr, ytr, Xva=None, yva=None, seed=0, n_estimators=800):
    """LightGBM classifier; early-stopped on (Xva, yva) when given, otherwise a fixed number of trees."""
    m = lgb.LGBMClassifier(n_estimators=n_estimators, learning_rate=0.03, num_leaves=15, min_child_samples=40,
                           subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5.0, random_state=seed,
                           verbose=-1)
    if Xva is None:
        return m.fit(Xtr, ytr)
    m.fit(Xtr, ytr, eval_set=[(Xva, yva)], eval_metric="auc", callbacks=[lgb.early_stopping(60, verbose=False)])
    return m


def _logit(p):
    p = np.clip(p, 1e-5, 1 - 1e-5)
    return np.log(p / (1 - p))


class CardioFlag:
    """Late-fusion cardiovascular flag: wearable GBM + static logistic + logistic stacker."""

    def __init__(self, seed: int = 0):
        self.seed = seed

    def fit(self, df: pd.DataFrame, inner_folds: int = 4) -> "CardioFlag":
        """Fit both base models on all of `df` and the stacker on out-of-fold scores, so it sees every training patient."""
        self.wear = wearable_columns(df)
        ids = np.array(sorted(df.patient_id.unique()))
        np.random.default_rng(self.seed).shuffle(ids)
        oof, iters = np.zeros((len(df), 2)), []
        for chunk in np.array_split(ids, inner_folds):
            test = df.patient_id.isin(chunk).to_numpy()
            a, b = df[~test], df[test]
            a_ids = np.array(sorted(a.patient_id.unique()))
            stop = a.patient_id.isin(a_ids[: int(0.15 * len(a_ids))]).to_numpy()
            g = fit_gbm(a[~stop][self.wear], a[~stop].y, a[stop][self.wear], a[stop].y, self.seed)
            iters.append(g.best_iteration_)
            sc, lr = self._static_fit(a)
            oof[test] = np.column_stack([_logit(g.predict_proba(b[self.wear])[:, 1]), lr.decision_function(sc.transform(b[STATIC]))])
        self.stack = LogisticRegression(C=100.0, max_iter=1000).fit(oof, df.y)
        self.oof_ = self.stack.predict_proba(oof)[:, 1]
        self.scaler, self.static_lr = self._static_fit(df)
        self.gbm = fit_gbm(df[self.wear], df.y, seed=self.seed, n_estimators=max(int(np.median(iters) * 1.15), 50))
        return self

    @staticmethod
    def _static_fit(d: pd.DataFrame):
        sc = StandardScaler().fit(d[STATIC])
        return sc, LogisticRegression(C=0.5, max_iter=2000).fit(sc.transform(d[STATIC]), d.y)

    def _parts(self, df: pd.DataFrame) -> np.ndarray:
        wear = _logit(self.gbm.predict_proba(df[self.wear])[:, 1])
        static = self.static_lr.decision_function(self.scaler.transform(df[STATIC]))
        return np.column_stack([wear, static])

    def scores(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        parts = self._parts(df)
        return {"wearable": 1 / (1 + np.exp(-parts[:, 0])), "static_logistic": 1 / (1 + np.exp(-parts[:, 1])),
                "fused": self.stack.predict_proba(parts)[:, 1]}

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return self.stack.predict_proba(self._parts(df))[:, 1]

    def explain(self, df: pd.DataFrame, top: int = 3) -> list[list[dict]]:
        """Features that pushed each score up, in log-odds, from both streams on one scale."""
        a, b = self.stack.coef_[0]
        wear = a * self.gbm.booster_.predict(df[self.wear], pred_contrib=True)[:, :-1]
        z = self.scaler.transform(df[STATIC])
        stat = b * z * self.static_lr.coef_[0]
        names = self.wear + STATIC
        raw = np.concatenate([df[self.wear].to_numpy(), df[STATIC].to_numpy()], 1)
        push = np.concatenate([wear, stat], 1)
        out = []
        for i in range(len(df)):
            order = np.argsort(-push[i])[:top]
            out.append([{"feature": names[j], "label": describe(names[j]), "value": float(raw[i, j]),
                         "push": float(push[i, j]), "stream": "wearable" if j < len(self.wear) else "record"}
                        for j in order if push[i, j] > 0])
        return out


def save_flag(flag: CardioFlag, threshold: float, path: Path) -> None:
    joblib.dump({"flag": flag, "threshold": float(threshold), "horizon_h": HORIZON_H, "static": STATIC}, path)


def load_flag(path: Path) -> tuple[CardioFlag, float]:
    d = joblib.load(path)
    return d["flag"], d["threshold"]


def ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    return float(sum(abs(y[idx == b].mean() - p[idx == b].mean()) * (idx == b).mean() for b in range(bins) if (idx == b).any()))


def score_metrics(y, p) -> dict:
    return {"auroc": float(roc_auc_score(y, p)), "auprc": float(average_precision_score(y, p)),
            "prevalence": float(y.mean())}


def summarise_replay(thr, n_ev, caught, n_alert, n_true, days, leads) -> dict:
    return {"threshold": float(thr), "events": int(n_ev), "caught": int(caught), "sensitivity": caught / max(n_ev, 1),
            "alerts": int(n_alert), "true_alerts": int(n_true), "precision": n_true / max(n_alert, 1),
            "patient_days": int(days), "false_alerts_per_patient_month": (n_alert - n_true) / max(days / 30.0, 1e-9),
            "median_lead_h": float(np.median(leads)) if leads else float("nan"), "_leads": [float(x) for x in leads]}


def alert_replay(df: pd.DataFrame, p: np.ndarray, thr: float, refractory_days: int = 3) -> dict:
    """Stream each patient's mornings through the flag. An event is caught if an alert fired in the 48 h before it."""
    n_ev = caught = n_alert = n_true = 0
    leads = []
    for pid, g in df.assign(p=p).groupby("patient_id"):
        g = g.sort_values("k")
        fire_k, last = [], -99
        for k, pr in zip(g.k.to_numpy(), g.p.to_numpy()):
            if pr >= thr and k - last >= refractory_days:
                fire_k.append(k)
                last = k
        n_alert += len(fire_k)
        ev_t = np.unique((g.t_dec.to_numpy() + g.hours_to_event.to_numpy() * 12)[g.y.to_numpy() == 1].round())
        n_ev += len(ev_t)
        t_of = dict(zip(g.k.to_numpy(), g.t_dec.to_numpy()))
        for e in ev_t:
            hits = [t_of[k] for k in fire_k if 0 < e - t_of[k] <= HORIZON_H * 12]
            if hits:
                caught += 1
                leads.append((e - min(hits)) * 5 / 60.0)
        n_true += sum(any(0 < e - t_of[k] <= HORIZON_H * 12 for e in ev_t) for k in fire_k)
    days = int(df.groupby("patient_id").k.count().sum())
    return summarise_replay(float(thr), n_ev, caught, n_alert, n_true, days, leads)


def operating_point(df: pd.DataFrame, p: np.ndarray, budget: float) -> dict:
    """Highest-sensitivity threshold that stays within a false-alert budget (per patient-month)."""
    grid = np.unique(np.quantile(p, np.linspace(0.5, 0.999, 60)))
    best = None
    for thr in grid:
        r = alert_replay(df, p, thr)
        if r["false_alerts_per_patient_month"] <= budget and (best is None or r["sensitivity"] > best["sensitivity"]):
            best = r
    return best or alert_replay(df, p, float(grid[-1]))


def pooled_replay(parts: list[dict]) -> dict:
    leads = [x for r in parts for x in r["_leads"]]
    out = summarise_replay(float(np.mean([r["threshold"] for r in parts])), sum(r["events"] for r in parts),
                           sum(r["caught"] for r in parts), sum(r["alerts"] for r in parts),
                           sum(r["true_alerts"] for r in parts), sum(r["patient_days"] for r in parts), leads)
    out["lead_h_p25"] = float(np.percentile(leads, 25)) if leads else float("nan")
    out.pop("_leads")
    return out


def bootstrap_auc(y, scores: dict, pid, reps=300, seed=0) -> dict:
    """95% intervals from resampling patients, and the paired gain of the fused model over each alternative."""
    rng = np.random.default_rng(seed)
    ids = np.unique(pid)
    by = {i: np.flatnonzero(pid == i) for i in ids}
    draws = {k: [] for k in scores}
    for _ in range(reps):
        ix = np.concatenate([by[i] for i in rng.choice(ids, len(ids))])
        if y[ix].min() == y[ix].max():
            continue
        for k, v in scores.items():
            draws[k].append(roc_auc_score(y[ix], v[ix]))
    out = {k: {"auroc": float(roc_auc_score(y, scores[k])),
               "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]} for k, d in draws.items()}
    for k in scores:
        if k != "fused":
            diff = np.array(draws["fused"]) - np.array(draws[k])
            out[k]["fused_minus_this"] = {"mean": float(diff.mean()),
                                          "ci95": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("data/synthetic_v2"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--models", type=Path, default=Path("models"))
    ap.add_argument("--budget", type=float, default=1.0, help="false alerts per patient-month for the operating point")
    ap.add_argument("--folds", type=int, default=5)
    a = ap.parse_args()
    a.out.mkdir(exist_ok=True, parents=True)
    a.models.mkdir(exist_ok=True, parents=True)

    df = build_dataset(a.root)
    print(f"{len(df):,} patient-mornings, {df.patient_id.nunique()} patients, positive rate {df.y.mean():.3f}", flush=True)
    wear = wearable_columns(df)
    names = ("static_logistic", "static", "rule", "wearable", "fused_early", "fused")
    oof = {n: np.zeros(len(df)) for n in names}
    replay_parts = {n: [] for n in ("static_logistic", "rule", "wearable", "fused_early", "fused")}
    ids = np.array(sorted(df.patient_id.unique()))
    np.random.default_rng(0).shuffle(ids)
    fold_flags, fold_of = [], {}
    for f, te_ids in enumerate(np.array_split(ids, a.folds)):
        rest = np.setdiff1d(ids, te_ids)
        va_ids, tr_ids = rest[: int(0.15 * len(rest))], rest[int(0.15 * len(rest)):]
        tr, va, te = (df[df.patient_id.isin(i)] for i in (tr_ids, va_ids, te_ids))
        te_ix = np.flatnonzero(df.patient_id.isin(te_ids))
        trva = pd.concat([tr, va])
        flag = CardioFlag(seed=f).fit(trva)                         # base models and stacker use every training patient
        thr_fused = operating_point(trva, flag.oof_, a.budget)["threshold"]   # from out-of-fold scores of the training patients
        fold_flags.append((flag, thr_fused))
        fold_of.update({int(i): f for i in te_ids})                 # the model that never saw these patients
        sv, st = {}, flag.scores(te)
        st["fused"] = flag.predict(te)
        sv["static_logistic"], sv["wearable"] = flag.scores(va)["static_logistic"], flag.scores(va)["wearable"]
        sv["fused"] = flag.predict(va)
        sv["rule"], st["rule"] = rule_score(va), rule_score(te)
        for name, cols in (("static", STATIC), ("fused_early", wear + STATIC)):     # one model, both streams side by side
            m = fit_gbm(tr[cols], tr.y, va[cols], va.y, seed=f)
            sv[name], st[name] = m.predict_proba(va[cols])[:, 1], m.predict_proba(te[cols])[:, 1]
        for n in names:
            oof[n][te_ix] = st[n]
        for n in replay_parts:
            thr = thr_fused if n == "fused" else operating_point(va, sv[n], a.budget)["threshold"]
            replay_parts[n].append(alert_replay(te, st[n], thr))
        print(f"fold {f + 1}/{a.folds} done", flush=True)

    y, pid = df.y.to_numpy(), df.patient_id.to_numpy()
    res: dict = {"n_mornings": len(df), "n_patients": int(len(ids)), "positive_rate": float(y.mean()),
                 "horizon_h": HORIZON_H, "folds": a.folds}
    res["overall"] = {n: score_metrics(y, oof[n]) for n in names}
    res["overall"]["fused"].update({"brier": float(brier_score_loss(y, oof["fused"])), "ece": ece(y, oof["fused"])})
    res["auroc_with_ci"] = bootstrap_auc(y, {n: oof[n] for n in names}, pid)
    sub = df.episode_kind.isin(["event", "benign"]).to_numpy()
    y_sub = (df.episode_kind[sub] == "event").astype(int).to_numpy()
    res["prodrome_event_vs_benign"] = {"n": int(sub.sum()), "events": int(y_sub.sum()),
                                       **{n: float(roc_auc_score(y_sub, oof[n][sub])) for n in names}}
    res["alert_replay"] = {"budget_false_alerts_per_patient_month": a.budget,
                           **{n: pooled_replay(p) for n, p in replay_parts.items()}}

    # final model on all patients, saved for the API
    flag = CardioFlag().fit(df)
    thr = operating_point(df, flag.oof_, a.budget)["threshold"]       # out-of-fold scores, so the threshold is not optimistic
    pos = df[df.y == 1].copy()
    pos["p"] = flag.oof_[df.y.to_numpy() == 1]
    pos = pos.sort_values("p", ascending=False).head(3)
    res["example_explanations"] = [
        {"patient_id": int(r.patient_id), "morning": int(r.k), "probability": float(r.p),
         "hours_to_event": float(r.hours_to_event), "drivers": ex} for (_, r), ex in zip(pos.iterrows(), flag.explain(pos))]
    res["stack_weights"] = {"wearable_logit": float(flag.stack.coef_[0][0]), "static_logit": float(flag.stack.coef_[0][1]),
                            "intercept": float(flag.stack.intercept_[0])}
    imp = pd.Series(flag.gbm.booster_.feature_importance("gain"), index=flag.wear).sort_values(ascending=False)
    res["top_wearable_features_gain"] = {describe(k): float(v / imp.sum()) for k, v in imp.head(10).items()}
    res["final_operating_threshold"] = float(thr)

    (a.out / "cardio_metrics.json").write_text(json.dumps(res, indent=2))
    save_flag(flag, thr, a.models / "cardio_flag.joblib")
    joblib.dump({"flags": [x[0] for x in fold_flags], "thresholds": [x[1] for x in fold_flags], "fold_of": fold_of},
                a.models / "cardio_folds.joblib")
    brief = {"overall_auroc": {k: round(v["auroc"], 3) for k, v in res["overall"].items()},
             "ci": {k: [round(x, 3) for x in v["ci95"]] for k, v in res["auroc_with_ci"].items()},
             "fused_gain": {k: [round(v["fused_minus_this"]["mean"], 3), [round(x, 3) for x in v["fused_minus_this"]["ci95"]]]
                            for k, v in res["auroc_with_ci"].items() if "fused_minus_this" in v},
             "prodrome": {k: round(v, 3) for k, v in res["prodrome_event_vs_benign"].items()},
             "alerts": {k: {m_: round(v[m_], 3) for m_ in ("sensitivity", "precision", "false_alerts_per_patient_month", "median_lead_h")}
                        for k, v in res["alert_replay"].items() if k != "budget_false_alerts_per_patient_month"}}
    print(json.dumps(brief, indent=1, default=float))


if __name__ == "__main__":
    import cardio                  # run through the real module name so saved models unpickle as cardio.CardioFlag anywhere

    cardio.main()
