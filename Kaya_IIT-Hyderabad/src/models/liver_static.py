"""Static liver model: steatosis (CAP >= 288 dB) and advanced fibrosis (LSM >= 8 kPa) from routine labs.

Validated on real NHANES 2017-2018 with repeated stratified 5-fold CV, against FIB-4, FLI and HSI.
This is the real-data anchor of the liver module; the dynamic CGM-driven part builds on top of it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROUTINE = ["age", "male", "bmi", "waist_cm", "alt", "ast", "ggt", "platelets", "hba1c", "hdl", "diabetes"]
FASTING = ROUTINE + ["triglycerides", "glucose", "homa_ir"]
TARGETS = {"steatosis": ["fli", "hsi"], "adv_fibrosis": ["fib4"]}


def make_models():
    return {
        "logistic": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.5, max_iter=3000)),
        "lightgbm": lgb.LGBMClassifier(n_estimators=250, learning_rate=0.03, num_leaves=8, min_child_samples=30,
                                       subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=2.0,
                                       random_state=0, verbose=-1),
    }


def oof_predict(df: pd.DataFrame, feats: list[str], target: str, name: str, repeats=3, seed=0) -> np.ndarray:
    X, y = df[feats], df[target].to_numpy()
    p, cnt = np.zeros(len(df)), np.zeros(len(df))
    for tr, te in RepeatedStratifiedKFold(n_splits=5, n_repeats=repeats, random_state=seed).split(X, y):
        m = make_models()[name].fit(X.iloc[tr], y[tr])
        p[te] += m.predict_proba(X.iloc[te])[:, 1]
        cnt[te] += 1
    return p / cnt


def auc_ci(y, s, n=400, seed=0):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() != y[i].max():
            vals.append(roc_auc_score(y[i], s[i]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def score(y, s):
    ok = ~np.isnan(s)
    y, s = y[ok], s[ok]
    if len(y) < 30 or y.min() == y.max():
        return None
    lo, hi = auc_ci(y, s)
    return {"n": int(len(y)), "prevalence": float(y.mean()), "auroc": float(roc_auc_score(y, s)),
            "auroc_ci95": [lo, hi], "auprc": float(average_precision_score(y, s))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("data/processed/nhanes_liver.parquet"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--models", type=Path, default=Path("models"))
    a = ap.parse_args()
    df = pd.read_parquet(a.data)
    a.out.mkdir(exist_ok=True, parents=True)
    a.models.mkdir(exist_ok=True, parents=True)
    res: dict = {"n_adults": int(len(df)), "n_diabetes": int(df.diabetes.sum()), "n_asian": int(df.asian.sum())}
    final = {}

    for target, baselines in TARGETS.items():
        y = df[target].to_numpy()
        res[target] = {}
        for fset_name, feats in (("routine", ROUTINE), ("fasting", FASTING)):
            sub = df if fset_name == "routine" else df[df.triglycerides.notna() & df.homa_ir.notna()].reset_index(drop=True)
            ys = sub[target].to_numpy()
            for mname in ("logistic", "lightgbm"):
                p = oof_predict(sub, feats, target, mname)
                res[target][f"{mname}_{fset_name}"] = {
                    "all_adults": score(ys, p),
                    "diabetes": score(ys[sub.diabetes == 1], p[sub.diabetes == 1]),
                    "asian": score(ys[sub.asian == 1], p[sub.asian == 1]),
                }
            if fset_name == "routine":
                for b in baselines:
                    s = df[b].to_numpy(dtype=float)
                    res[target][f"baseline_{b}"] = {"all_adults": score(y, s), "diabetes": score(y[df.diabetes == 1], s[df.diabetes == 1]),
                                                    "asian": score(y[df.asian == 1], s[df.asian == 1])}
        # final model on all data (LightGBM, routine features) + SHAP importance
        m = make_models()["lightgbm"].fit(df[ROUTINE], y)
        sv = shap.TreeExplainer(m).shap_values(df[ROUTINE])
        sv = sv[1] if isinstance(sv, list) else sv
        imp = pd.Series(np.abs(sv).mean(0), index=ROUTINE).sort_values(ascending=False)
        res[target]["shap_importance"] = {k: float(v) for k, v in imp.items()}
        final[target] = m
    joblib.dump({"models": final, "features": ROUTINE}, a.models / "liver_static.joblib")
    (a.out / "liver_static_metrics.json").write_text(json.dumps(res, indent=2))

    for t in TARGETS:
        print(t)
        for k, v in res[t].items():
            if k == "shap_importance":
                print("  top SHAP:", list(v)[:5])
                continue
            r = {g: (None if x is None else f"{x['auroc']:.3f} [{x['auroc_ci95'][0]:.3f},{x['auroc_ci95'][1]:.3f}] n={x['n']}")
                 for g, x in v.items()}
            print(f"  {k:24s} all {r['all_adults']} | diabetes {r['diabetes']} | asian {r['asian']}")


if __name__ == "__main__":
    main()
