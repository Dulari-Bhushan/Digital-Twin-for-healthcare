"""Does fusing the two streams help the glucose forecast? An ablation on held-out synthetic patients.

Each rung adds one input group (wearable HR and activity, basic record, HRV and sleep, full record with genetics). For each
rung a GRU is trained with the same recipe and seeds, then scored on the same held-out patients: RMSE at +30/+60/+120
min, 80% interval coverage, and AUROC and AUPRC for hyperglycemia and hypoglycemia within 2 hours.

`--quick` swaps the GRU for LightGBM on summary features so the design can be checked on a laptop.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np

import glucose as G
from windows import HORIZONS, split_by_patient
from windows_v2 import RUNGS, load_synthetic_v2, rung, select


def summary_features(w) -> np.ndarray:
    x = w.x
    g = x[:, :, 0] * 60 + 150
    cols = [g, g[:, -1:] - g[:, -2:-1], g[:, -1:] - g[:, -6:-5], g.mean(1, keepdims=True), g.std(1, keepdims=True)]
    for c in range(1, x.shape[2]):
        cols += [x[:, -1:, c], x[:, :, c].mean(1, keepdims=True)]
    cols.append(w.s)
    return np.concatenate(cols, 1)


def quick_fit_predict(tr, te, n_cap=250_000, seed=0):
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(tr.y), min(n_cap, len(tr.y)), replace=False)
    Xtr, Xte = summary_features(tr.subset(idx)), summary_features(te)
    q = np.zeros((len(te.y), len(HORIZONS), 3), dtype=np.float32)
    for h in range(len(HORIZONS)):
        for qi, alpha in enumerate(G.QS):
            m = lgb.LGBMRegressor(objective="quantile", alpha=alpha, n_estimators=200, learning_rate=0.06, num_leaves=63,
                                  subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=seed, verbose=-1)
            m.fit(Xtr, tr.y[idx, h])
            q[:, h, qi] = m.predict(Xte)
    p = np.zeros((len(te.y), 2), dtype=np.float32)
    for j in range(2):
        ok = tr.ev_mask[idx, j] > 0
        m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.06, num_leaves=31, subsample=0.8, subsample_freq=1,
                               colsample_bytree=0.8, random_state=seed, verbose=-1)
        m.fit(Xtr[ok], tr.ev[idx, j][ok])
        p[:, j] = m.predict_proba(Xte)[:, 1]
    return q, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", type=Path, default=Path("data/synthetic_v2"))
    ap.add_argument("--max-patients", type=int, default=None)
    ap.add_argument("--stride", type=int, default=6)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--rungs", nargs="*", default=list(RUNGS))
    ap.add_argument("--out", type=Path, default=Path("results/glucose_ablation.json"))
    a = ap.parse_args()
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    t0 = time.time()
    full = load_synthetic_v2(a.synthetic, stride=a.stride, max_patients=a.max_patients)
    tr, va, te = split_by_patient(full)
    print(f"windows {len(full.y):,} (train {len(tr.y):,} val {len(va.y):,} test {len(te.y):,}), "
          f"{len(np.unique(full.pid))} patients, load {time.time() - t0:.0f}s", flush=True)
    res: dict = {"n_test_windows": int(len(te.y)), "n_patients": int(len(np.unique(full.pid))), "quick": a.quick, "rungs": {}}
    for name in a.rungs:
        ch, st = rung(name)
        trs, vas, tes = (select(d, ch, st) for d in (tr, va, te))
        runs = []
        for seed in range(a.seeds):
            t1 = time.time()
            if a.quick:
                runs.append(G.evaluate(quick_fit_predict(trs, tes, seed=seed), tes))
            else:
                torch.manual_seed(seed)
                model = G.GlucoseGRU(c_in=len(ch), s_in=len(st))
                G.fit(model, trs, vas, epochs=a.epochs, dev=dev, log=lambda m: None)
                runs.append(G.evaluate(G.predict(model, tes, dev), tes))
            r = runs[-1]
            print(f"{name:24s} seed {seed} rmse {r['rmse'][0]:.2f}/{r['rmse'][1]:.2f}/{r['rmse'][2]:.2f} "
                  f"hyper {r['hyper']['auroc']:.3f}/{r['hyper']['auprc']:.3f} hypo {r['hypo']['auroc']:.3f}/{r['hypo']['auprc']:.3f} "
                  f"({time.time() - t1:.0f}s)", flush=True)
        res["rungs"][name] = {"channels": [int(c) for c in ch], "static": [int(c) for c in st], "runs": runs}
    a.out.parent.mkdir(exist_ok=True, parents=True)
    a.out.write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
