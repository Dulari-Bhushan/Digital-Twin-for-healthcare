"""Train and evaluate the glycemic core.

1. Pretrain GRU on the synthetic cohort (patient-level 70/15/15 split).
2. Evaluate on held-out synthetic patients and zero-shot on real CGMacros recordings.
3. Fine-tune on real CGMacros with subject-level 5-fold cross-validation.
Baselines: persistence and LightGBM.
"""
from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import torch
from sklearn.model_selection import GroupKFold

import glucose as G
from windows import HORIZONS, Windows, concat, load_cgmacros, load_synthetic, split_by_patient


def tab_features(w: Windows) -> np.ndarray:
    g = w.x[:, :, 0] * 60 + 150
    hr = w.x[:, :, 1] * 20 + 70
    carbs = w.x[:, :, 3] * 100
    rev = (carbs > 0)[:, ::-1]
    since = np.where(rev.any(1), rev.argmax(1) * 5, 120)
    return np.column_stack([g, g[:, -1] - g[:, -2], g[:, -1] - g[:, -6], g.mean(1), g.std(1), hr[:, -1], hr.mean(1),
                            w.x[:, :, 2].sum(1), carbs.sum(1), since, w.s])


def lgb_fit_predict(train: Windows, test: Windows, n_cap=400_000, seed=0):
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(train.y), min(n_cap, len(train.y)), replace=False)
    Xtr, Xte = tab_features(train.subset(idx)), tab_features(test)
    q = np.zeros((len(test.y), len(HORIZONS), 3), dtype=np.float32)
    for h in range(len(HORIZONS)):
        for qi, alpha in enumerate(G.QS):
            m = lgb.LGBMRegressor(objective="quantile", alpha=alpha, n_estimators=300, learning_rate=0.05,
                                  num_leaves=63, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                                  random_state=seed, verbose=-1)
            m.fit(Xtr, train.y[idx, h])
            q[:, h, qi] = m.predict(Xte)
    return q, np.full((len(test.y), 2), np.nan, dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", type=Path, default=Path("data/synthetic"))
    ap.add_argument("--cgmacros", type=Path, default=Path("data/raw/cgmacros"))
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--ft-epochs", type=int, default=4)
    ap.add_argument("--max-patients", type=int, default=None)
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--models", type=Path, default=Path("models"))
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(0)
    np.random.seed(0)
    a.out.mkdir(exist_ok=True, parents=True)
    a.models.mkdir(exist_ok=True, parents=True)
    res: dict = {}

    t0 = time.time()
    syn = load_synthetic(a.synthetic, stride=6, max_patients=a.max_patients)
    tr, va, te = split_by_patient(syn)
    real = load_cgmacros(a.cgmacros, stride=3)
    print(f"synthetic windows {len(syn.y):,} (train {len(tr.y):,} val {len(va.y):,} test {len(te.y):,}); "
          f"CGMacros windows {len(real.y):,} from {len(np.unique(real.pid))} subjects; load {time.time() - t0:.0f}s", flush=True)

    # ---- Baselines on held-out synthetic patients
    res["synthetic_test"] = {"persistence": G.evaluate(G.persistence(te), te)}
    res["synthetic_test"]["lightgbm"] = G.evaluate(lgb_fit_predict(tr, te), te)

    # ---- GRU pretraining
    model = G.GlucoseGRU()
    G.fit(model, tr, va, epochs=a.epochs, dev=dev, log=lambda m: print(m, flush=True))
    torch.save(model.state_dict(), a.models / "glucose_gru_synthetic.pt")
    res["synthetic_test"]["gru"] = G.evaluate(G.predict(model, te, dev), te)

    # ---- Real data: zero-shot
    res["cgmacros"] = {"persistence": G.evaluate(G.persistence(real), real),
                       "gru_zero_shot": G.evaluate(G.predict(model, real, dev), real)}

    # ---- Real data: subject-level 5-fold CV (fine-tune vs from scratch vs LightGBM)
    folds = GroupKFold(n_splits=5)
    preds = {k: (np.zeros((len(real.y), len(HORIZONS), 3), np.float32), np.zeros((len(real.y), 2), np.float32))
             for k in ("ft", "scratch", "lgb")}
    for f, (itr, ite) in enumerate(folds.split(np.zeros(len(real.y)), groups=real.pid)):
        rtr, rte = real.subset(itr), real.subset(ite)
        ft = copy.deepcopy(model)
        G.fit(ft, rtr, None, epochs=a.ft_epochs, bs=1024, lr=3e-4, dev=dev, log=lambda m: None)
        sc = G.GlucoseGRU()
        G.fit(sc, rtr, None, epochs=a.ft_epochs * 2, bs=1024, lr=2e-3, dev=dev, log=lambda m: None)
        for k, p in (("ft", G.predict(ft, rte, dev)), ("scratch", G.predict(sc, rte, dev)),
                     ("lgb", lgb_fit_predict(rtr, rte, n_cap=100_000))):
            preds[k][0][ite], preds[k][1][ite] = p
        print(f"fold {f + 1}/5 done", flush=True)
    for k, name in (("ft", "gru_pretrained_finetuned"), ("scratch", "gru_from_scratch"), ("lgb", "lightgbm_real_only")):
        res["cgmacros"][name] = G.evaluate(preds[k], real)

    (a.out / "glucose_metrics.json").write_text(json.dumps(res, indent=2))
    print(json.dumps({k: {m: {"rmse": [round(x, 1) for x in v["rmse"]], "cov80": [round(x, 2) for x in v["coverage_80"]],
                              "hyper_auroc": round(v["hyper"]["auroc"], 3), "hypo_auroc": round(v["hypo"]["auroc"], 3)}
                          for m, v in d.items()} for k, d in res.items()}, indent=1))


if __name__ == "__main__":
    main()
