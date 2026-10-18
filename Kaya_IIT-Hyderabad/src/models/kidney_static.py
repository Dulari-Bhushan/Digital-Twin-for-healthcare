"""Static kidney model: reduced eGFR (<60) and albuminuria (UACR >= 30 mg/g) from routine measurements.

Validated on real NHANES 2017-2018 with repeated stratified 5-fold CV against a simple clinical baseline
(age, systolic BP, HbA1c, diabetes). Creatinine is not a feature, so this estimates risk the way a screening
tool would, before kidney labs are drawn.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from liver_static import make_models, score

FEATS = ["age", "male", "bmi", "waist_cm", "hba1c", "sbp", "dbp", "hdl", "diabetes"]
BASE = ["age", "sbp", "hba1c", "diabetes"]
TARGETS = ["albuminuria", "low_egfr", "ckd"]


def oof(df, feats, target, model, repeats=3):
    X, y = df[feats], df[target].to_numpy()
    p, c = np.zeros(len(df)), np.zeros(len(df))
    for tr, te in RepeatedStratifiedKFold(n_splits=5, n_repeats=repeats, random_state=0).split(X, y):
        m = model().fit(X.iloc[tr], y[tr])
        p[te] += m.predict_proba(X.iloc[te])[:, 1]
        c[te] += 1
    return p / c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("data/processed/nhanes_kidney.parquet"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--models", type=Path, default=Path("models"))
    a = ap.parse_args()
    df = pd.read_parquet(a.data)
    a.out.mkdir(exist_ok=True, parents=True)
    a.models.mkdir(exist_ok=True, parents=True)
    res = {"n_adults": int(len(df)), "n_diabetes": int(df.diabetes.sum()), "n_asian": int(df.asian.sum()),
           "prevalence": {t: float(df[t].mean()) for t in TARGETS},
           "prevalence_diabetes": {t: float(df[df.diabetes == 1][t].mean()) for t in TARGETS}}
    lr = lambda: make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.5, max_iter=3000))
    final = {}
    for t in TARGETS:
        y = df[t].to_numpy()
        res[t] = {}
        for name, feats, mk in (("baseline_logistic_age_bp_hba1c_dm", BASE, lr), ("logistic", FEATS, lr),
                                ("lightgbm", FEATS, lambda: make_models()["lightgbm"])):
            p = oof(df, feats, t, mk)
            res[t][name] = {"all_adults": score(y, p), "diabetes": score(y[df.diabetes == 1], p[df.diabetes == 1]),
                            "asian": score(y[df.asian == 1], p[df.asian == 1])}
        m = make_models()["lightgbm"].fit(df[FEATS], y)
        sv = shap.TreeExplainer(m).shap_values(df[FEATS])
        sv = sv[1] if isinstance(sv, list) else sv
        res[t]["shap_importance"] = {k: float(v) for k, v in pd.Series(np.abs(sv).mean(0), index=FEATS).sort_values(ascending=False).items()}
        final[t] = m
    joblib.dump({"models": final, "features": FEATS}, a.models / "kidney_twin.joblib")
    (a.out / "kidney_static_metrics.json").write_text(json.dumps(res, indent=2))
    for t in TARGETS:
        print(t, f"(prevalence {res['prevalence'][t]:.3f}, diabetes {res['prevalence_diabetes'][t]:.3f})")
        for k, v in res[t].items():
            if k == "shap_importance":
                print("  top SHAP:", list(v)[:5])
                continue
            r = {g: (None if x is None else f"{x['auroc']:.3f} [{x['auroc_ci95'][0]:.3f},{x['auroc_ci95'][1]:.3f}] n={x['n']}") for g, x in v.items()}
            print(f"  {k:36s} all {r['all_adults']} | diabetes {r['diabetes']} | asian {r['asian']}")


if __name__ == "__main__":
    main()
