"""Polish the glycemic core: GRU + LightGBM ensemble, conformal intervals, calibrated event heads,
and alert-replay lead-time analysis.

Synthetic: models fit on train patients, ensemble weights and calibrators fit on val patients, reported on
held-out test patients. Real (CGMacros): subject-level 5-fold CV; calibrators are cross-fitted on the
out-of-fold predictions of the *other* folds, so no subject is ever calibrated on itself.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import torch
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import GroupKFold

import alerts as A
import glucose as G
from train_glucose import tab_features
from windows import HORIZONS, Windows, load_cgmacros, load_synthetic, split_by_patient


class LGBBundle:
    """Quantile regressors (3 horizons x 3 quantiles) and 2 event classifiers on tabular window features."""

    def __init__(self, n_cap=400_000, trees=300, seed=0):
        self.n_cap, self.trees, self.seed = n_cap, trees, seed

    def fit(self, w: Windows):
        rng = np.random.default_rng(self.seed)
        idx = rng.choice(len(w.y), min(self.n_cap, len(w.y)), replace=False)
        sub = w.subset(idx)
        X = tab_features(sub)
        common = dict(n_estimators=self.trees, learning_rate=0.05, num_leaves=63, subsample=0.8, subsample_freq=1,
                      colsample_bytree=0.8, random_state=self.seed, verbose=-1)
        self.reg = [[lgb.LGBMRegressor(objective="quantile", alpha=a, **common).fit(X, sub.y[:, h])
                     for a in G.QS] for h in range(len(HORIZONS))]
        self.clf = []
        for j in range(2):
            m = sub.ev_mask[:, j] > 0
            self.clf.append(lgb.LGBMClassifier(**common).fit(X[m], sub.ev[m, j]) if sub.ev[m, j].min() != sub.ev[m, j].max() else None)
        return self

    def predict(self, w: Windows):
        X = tab_features(w)
        q = np.stack([np.stack([m.predict(X) for m in row], -1) for row in self.reg], 1).astype(np.float32)
        q = np.sort(q, -1)
        p = np.stack([c.predict_proba(X)[:, 1] if c is not None else np.zeros(len(X)) for c in self.clf], 1)
        return q, p.astype(np.float32)


def blend(a, b, wq, wp):
    return wq * a[0] + (1 - wq) * b[0], wp * a[1] + (1 - wp) * b[1]


def conformal_offsets(q, y, target=0.8):
    """CQR: how far to widen [lo, hi] per horizon so that `target` of held-out outcomes are covered."""
    out = []
    for h in range(y.shape[1]):
        e = np.maximum(q[:, h, 0] - y[:, h], y[:, h] - q[:, h, 2])
        out.append(float(np.quantile(e, target)))
    return np.array(out, dtype=np.float32)


def apply_offsets(q, c):
    q = q.copy()
    q[..., 0] -= c
    q[..., 2] += c
    return q


def fit_iso(p, y, m):
    out = []
    for j in range(2):
        sel = m[:, j] > 0
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        out.append(iso.fit(p[sel, j], y[sel, j]) if sel.sum() > 20 and y[sel, j].min() != y[sel, j].max() else None)
    return out


def apply_iso(isos, p):
    return np.stack([isos[j].predict(p[:, j]) if isos[j] is not None else p[:, j] for j in range(2)], 1).astype(np.float32)


def cal_metrics(p, w: Windows) -> dict:
    out = {}
    for j, name in enumerate(("hyper", "hypo")):
        sel = w.ev_mask[:, j] > 0
        pj, yj = p[sel, j], w.ev[sel, j]
        if sel.sum() == 0 or np.isnan(pj).any():
            out[name] = {"brier": float("nan"), "ece": float("nan")}
            continue
        bins = np.quantile(pj, np.linspace(0, 1, 11))
        bi = np.clip(np.searchsorted(bins, pj, side="right") - 1, 0, 9)
        ece = sum(abs(pj[bi == b].mean() - yj[bi == b].mean()) * (bi == b).mean() for b in range(10) if (bi == b).any())
        rel = [[float(pj[bi == b].mean()), float(yj[bi == b].mean())] for b in range(10) if (bi == b).any()]
        out[name] = {"brier": float(((pj - yj) ** 2).mean()), "ece": float(ece), "reliability": rel}
    return out


def full_eval(pred, w):
    m = G.evaluate(pred, w)
    m.update({"calibration": cal_metrics(pred[1], w)})
    return m


def alert_tables(p, w: Windows, budgets=(0.25, 1.0)):
    out = {}
    for j, (name, thresh, above) in enumerate((("hyper", 180.0, True), ("hypo", 70.0, False))):
        rows = A.sweep(w.pid, w.t, w.g_last, p[:, j], w.ev_mask[:, j], thresh, above)
        out[name] = {"sweep": rows, "chosen": {f"<= {b} false alerts/patient-day": A.pick(rows, b) for b in budgets}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", type=Path, default=Path("data/synthetic"))
    ap.add_argument("--cgmacros", type=Path, default=Path("data/raw/cgmacros"))
    ap.add_argument("--weights", type=Path, default=Path("models/glucose_gru_synthetic.pt"))
    ap.add_argument("--ft-epochs", type=int, default=4)
    ap.add_argument("--out", type=Path, default=Path("results"))
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(0)
    res: dict = {}
    log = lambda *m: print(*m, flush=True)

    # ---------------- synthetic ----------------
    syn = load_synthetic(a.synthetic, stride=6)
    tr, va, te6 = split_by_patient(syn)
    te = load_synthetic(a.synthetic, stride=1, ids=np.unique(te6.pid))
    log(f"synthetic train {len(tr.y):,} val {len(va.y):,} test(stride1) {len(te.y):,}")
    gru = G.GlucoseGRU()
    gru.load_state_dict(torch.load(a.weights, map_location=dev))
    log("fitting LightGBM bundle on synthetic train ...")
    bundle = LGBBundle().fit(tr)
    pv_g, pv_l = G.predict(gru, va, dev), bundle.predict(va)
    # pick blend weights on val
    wq = min(np.linspace(0, 1, 5), key=lambda w_: np.mean(G.evaluate(blend(pv_g, pv_l, w_, 0.5), va)["rmse"]))
    wp = max(np.linspace(0, 1, 5), key=lambda w_: np.nanmean([G.evaluate(blend(pv_g, pv_l, 0.5, w_), va)[k]["auprc"] for k in ("hyper", "hypo")]))
    pv = blend(pv_g, pv_l, wq, wp)
    off, isos = conformal_offsets(pv[0], va.y), fit_iso(pv[1], va.ev, va.ev_mask)
    pt_g, pt_l = G.predict(gru, te, dev), bundle.predict(te)
    pt = blend(pt_g, pt_l, wq, wp)
    pt_cal = (apply_offsets(pt[0], off), apply_iso(isos, pt[1]))
    res["synthetic_test"] = {"blend_weight_gru_quantiles": float(wq), "blend_weight_gru_events": float(wp),
                             "conformal_offsets_mgdl": off.tolist(),
                             "gru": full_eval(pt_g, te), "lightgbm": full_eval(pt_l, te),
                             "ensemble": full_eval(pt, te), "ensemble_calibrated": full_eval(pt_cal, te)}
    res["alerts_synthetic"] = alert_tables(pt_cal[1], te)
    log("synthetic done", json.dumps({k: [round(x, 1) for x in v["rmse"]] for k, v in res["synthetic_test"].items() if isinstance(v, dict) and "rmse" in v}))

    # ---------------- real (CGMacros, subject-level CV) ----------------
    real = load_cgmacros(a.cgmacros, stride=1)
    log(f"CGMacros windows {len(real.y):,} from {len(np.unique(real.pid))} subjects")
    folds = list(GroupKFold(n_splits=5).split(np.zeros(len(real.y)), groups=real.pid))
    P = {k: (np.zeros((len(real.y), 3, 3), np.float32), np.zeros((len(real.y), 2), np.float32)) for k in ("gru", "lgb")}
    for f, (itr, ite) in enumerate(folds):
        rtr, rte = real.subset(itr), real.subset(ite)
        ft = copy.deepcopy(gru)
        G.fit(ft, rtr, None, epochs=a.ft_epochs, bs=1024, lr=3e-4, dev=dev, log=lambda m: None)
        lb = LGBBundle(n_cap=100_000).fit(rtr)
        for k, p in (("gru", G.predict(ft, rte, dev)), ("lgb", lb.predict(rte))):
            P[k][0][ite], P[k][1][ite] = p
        log(f"fold {f + 1}/5")
    ens = blend(P["gru"], P["lgb"], 0.5, 0.5)
    q_cal, p_cal = ens[0].copy(), ens[1].copy()
    for itr, ite in folds:   # cross-fit calibrators on the other folds' out-of-fold predictions
        c = conformal_offsets(ens[0][itr], real.y[itr])
        q_cal[ite] = apply_offsets(ens[0][ite], c)
        p_cal[ite] = apply_iso(fit_iso(ens[1][itr], real.ev[itr], real.ev_mask[itr]), ens[1][ite])
    res["cgmacros"] = {"gru_finetuned": full_eval(P["gru"], real), "lightgbm": full_eval(P["lgb"], real),
                       "ensemble": full_eval(ens, real), "ensemble_calibrated": full_eval((q_cal, p_cal), real)}
    res["alerts_cgmacros"] = alert_tables(p_cal, real)

    a.out.mkdir(exist_ok=True, parents=True)
    (a.out / "glucose_polish.json").write_text(json.dumps(res, indent=2, default=float))
    log("saved")


if __name__ == "__main__":
    main()
