"""Glycemic-core forecaster: GRU with quantile outputs and adverse-event heads, plus baselines.

Outputs per window: glucose change at +30/+60/+120 min as (q10, q50, q90), and onset probabilities for
hyperglycemia (>180) and hypoglycemia (<70) within 2 h.
"""
from __future__ import annotations

import copy

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import average_precision_score, roc_auc_score

from windows import HORIZONS, Windows

QS = (0.1, 0.5, 0.9)
DY = 60.0  # target scale (mg/dL)


class GlucoseGRU(nn.Module):
    def __init__(self, c_in=4, s_in=6, hid=128, layers=2, drop=0.1):
        super().__init__()
        self.gru = nn.GRU(c_in, hid, layers, batch_first=True, dropout=drop)
        self.static = nn.Sequential(nn.Linear(s_in, 32), nn.ReLU())
        self.trunk = nn.Sequential(nn.Linear(hid + 32, 128), nn.ReLU(), nn.Dropout(drop))
        self.q = nn.Linear(128, len(HORIZONS) * len(QS))
        self.ev = nn.Linear(128, 2)

    def forward(self, x, s):
        h = self.gru(x)[0][:, -1]
        z = self.trunk(torch.cat([h, self.static(s)], 1))
        q = self.q(z).view(-1, len(HORIZONS), len(QS))
        # median is free; lower/upper are non-negative offsets, so quantiles never cross
        med = q[..., 1]
        lo = med - nn.functional.softplus(q[..., 0])
        hi = med + nn.functional.softplus(q[..., 2])
        return torch.stack([lo, med, hi], -1), self.ev(z)


def pinball(q_pred, y):
    loss = 0.0
    for i, tau in enumerate(QS):
        e = y - q_pred[..., i]
        loss = loss + torch.maximum(tau * e, (tau - 1) * e).mean()
    return loss / len(QS)


def _tensors(w: Windows, dev):
    return (torch.from_numpy(w.x).to(dev), torch.from_numpy(w.s).to(dev),
            torch.from_numpy(w.y / DY).to(dev), torch.from_numpy(w.ev).to(dev),
            torch.from_numpy(w.ev_mask).to(dev))


def fit(model, train: Windows, val: Windows | None, epochs=10, bs=4096, lr=2e-3, dev="cuda", log=print):
    model.to(dev)
    x, s, y, ev, em = _tensors(train, dev)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    steps = epochs * ((len(x) + bs - 1) // bs)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps)
    bce = nn.BCEWithLogitsLoss(reduction="none")
    best, best_state = 1e9, None
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(len(x), device=dev)
        tot = 0.0
        for i in range(0, len(x), bs):
            b = perm[i:i + bs]
            qp, lg = model(x[b], s[b])
            loss = pinball(qp, y[b]) + 0.3 * (bce(lg, ev[b]) * em[b]).sum() / em[b].sum().clamp(min=1)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            tot += loss.item() * len(b)
        msg = f"epoch {ep + 1}/{epochs} train_loss {tot / len(x):.4f}"
        if val is not None:
            m = evaluate(predict(model, val, dev), val)
            msg += f" val_rmse30/60/120 {m['rmse'][0]:.1f}/{m['rmse'][1]:.1f}/{m['rmse'][2]:.1f}"
            score = float(np.mean(m["rmse"]))
            if score < best:
                best, best_state = score, copy.deepcopy(model.state_dict())
        log(msg)
    if best_state is not None:
        model.load_state_dict(best_state)
    return model


@torch.no_grad()
def predict(model, w: Windows, dev="cuda", bs=16384):
    model.eval().to(dev)
    qs, ps = [], []
    for i in range(0, len(w.x), bs):
        x = torch.from_numpy(w.x[i:i + bs]).to(dev)
        s = torch.from_numpy(w.s[i:i + bs]).to(dev)
        q, lg = model(x, s)
        qs.append(q.cpu().numpy() * DY)
        ps.append(torch.sigmoid(lg).cpu().numpy())
    return np.concatenate(qs), np.concatenate(ps)


def _auc(y, p, m):
    sel = m > 0
    if sel.sum() == 0 or y[sel].min() == y[sel].max() or np.isnan(p[sel]).any():
        return float("nan"), float("nan"), int(y[sel].sum())
    return float(roc_auc_score(y[sel], p[sel])), float(average_precision_score(y[sel], p[sel])), int(y[sel].sum())


def evaluate(pred, w: Windows) -> dict:
    q, p = pred
    med = q[..., 1]
    err = med - w.y
    out = {
        "n_windows": int(len(w.y)),
        "rmse": [float(np.sqrt((err[:, i] ** 2).mean())) for i in range(len(HORIZONS))],
        "mae": [float(np.abs(err[:, i]).mean()) for i in range(len(HORIZONS))],
        "coverage_80": [float(((w.y[:, i] >= q[:, i, 0]) & (w.y[:, i] <= q[:, i, 2])).mean()) for i in range(len(HORIZONS))],
    }
    for j, name in enumerate(("hyper", "hypo")):
        auc, ap, npos = _auc(w.ev[:, j], p[:, j], w.ev_mask[:, j])
        out[name] = {"auroc": auc, "auprc": ap, "positives": npos}
    return out


def persistence(w: Windows):
    z = np.zeros((len(w.y), len(HORIZONS), len(QS)), dtype=np.float32)
    return z, np.zeros((len(w.y), 2), dtype=np.float32) + 0.5
