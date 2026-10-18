"""Live inference: the glucose GRU in pure numpy, so the API can run the model on every incoming reading.

LiveTwin keeps a rolling 2-hour window for one patient. Each new 5-minute reading is scaled exactly as in training
(src/models/windows.py), pushed through the GRU, widened with the conformal offsets and calibrated with isotonic
maps. Alerts use the same thresholds and 2-hour refractory rule as the offline replay.
"""
from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path

import numpy as np

L = 24
STEP_MIN = 5
DY = 60.0
SCALE = {"g_mu": 150.0, "g_sd": 60.0, "hr_mu": 70.0, "hr_sd": 20.0, "carb": 100.0}
REFRACTORY = 24


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _softplus(x):
    return np.log1p(np.exp(-np.abs(x))) + np.maximum(x, 0.0)


class NumpyGRU:
    """Forward pass of GlucoseGRU (2-layer GRU, static branch, trunk, quantile and event heads)."""

    def __init__(self, npz_path: Path):
        w = np.load(npz_path)
        self.w = {k: w[k].astype(np.float64) for k in w.files}
        self.H = self.w["gru.weight_hh_l0"].shape[1]
        self.layers = 1 + max(int(k.split("_l")[-1]) for k in self.w if k.startswith("gru.weight_ih_l"))

    def _gru_layer(self, x, layer):
        wi, wh = self.w[f"gru.weight_ih_l{layer}"], self.w[f"gru.weight_hh_l{layer}"]
        bi, bh = self.w[f"gru.bias_ih_l{layer}"], self.w[f"gru.bias_hh_l{layer}"]
        H = self.H
        h = np.zeros(H)
        out = []
        for t in range(x.shape[0]):
            gi = wi @ x[t] + bi
            gh = wh @ h + bh
            r = _sigmoid(gi[:H] + gh[:H])
            z = _sigmoid(gi[H:2 * H] + gh[H:2 * H])
            n = np.tanh(gi[2 * H:] + r * gh[2 * H:])
            h = (1 - z) * n + z * h
            out.append(h)
        return np.stack(out)

    def forward(self, x, s):
        """x: (L, 4) scaled channels; s: (6,) scaled static. Returns (q (3,3) in scaled units, logits (2,))."""
        seq = x.astype(np.float64)
        for layer in range(self.layers):
            seq = self._gru_layer(seq, layer)
        h = seq[-1]
        st = np.maximum(self.w["static.0.weight"] @ s + self.w["static.0.bias"], 0.0)
        z = np.maximum(self.w["trunk.0.weight"] @ np.concatenate([h, st]) + self.w["trunk.0.bias"], 0.0)
        q = (self.w["q.weight"] @ z + self.w["q.bias"]).reshape(3, 3)
        med = q[:, 1]
        lo = med - _softplus(q[:, 0])
        hi = med + _softplus(q[:, 2])
        return np.stack([lo, med, hi], -1), self.w["ev.weight"] @ z + self.w["ev.bias"]


class Calibration:
    def __init__(self, path: Path):
        c = json.loads(path.read_text())
        self.offsets = np.array(c["conformal_offsets"])
        self.thr = c["alert_thresholds"]
        self.iso = [(np.array(i["x"]), np.array(i["y"])) for i in c["isotonic"]]

    def event_prob(self, j, p):
        x, y = self.iso[j]
        return float(np.interp(p, x, y))


class LiveTwin:
    def __init__(self, model: NumpyGRU, cal: Calibration, profile: dict):
        self.model, self.cal = model, cal
        p = profile
        self.static_base = np.array([(p["age"] - 50) / 15, (p["bmi"] - 26) / 5, (p["hba1c"] - 7.5) / 1.5,
                                     1.0 if p["sex"] == "M" else 0.0], dtype=np.float64)
        self.buf: deque = deque(maxlen=L)
        self.last_alert = {"hyper": -10**9, "hypo": -10**9}
        self.n = 0

    def push(self, glucose: float, heart_rate: float, steps: float, carbs: float, minute_of_day: int) -> dict | None:
        act = float(np.clip(steps / 600.0, 0, 1))
        self.buf.append((glucose, heart_rate, act, carbs))
        self.n += 1
        if len(self.buf) < L:
            return None
        t0 = time.perf_counter()
        a = np.array(self.buf, dtype=np.float64)
        x = a.copy()
        x[:, 0] = (x[:, 0] - SCALE["g_mu"]) / SCALE["g_sd"]
        x[:, 1] = (x[:, 1] - SCALE["hr_mu"]) / SCALE["hr_sd"]
        x[:, 3] = x[:, 3] / SCALE["carb"]
        ang = 2 * np.pi * minute_of_day / 1440.0
        s = np.concatenate([self.static_base, [np.sin(ang), np.cos(ang)]])
        q, logits = self.model.forward(x, s)
        q = q * DY
        q[:, 0] -= self.cal.offsets
        q[:, 2] += self.cal.offsets
        pr = _sigmoid(logits)
        p_hyper, p_hypo = self.cal.event_prob(0, pr[0]), self.cal.event_prob(1, pr[1])
        g = glucose
        alerts = []
        for name, p, ok in (("hyper", p_hyper, g <= 180), ("hypo", p_hypo, g >= 70)):
            if ok and p >= self.cal.thr[name] and self.n - self.last_alert[name] >= REFRACTORY:
                self.last_alert[name] = self.n
                alerts.append({"type": name, "prob": round(float(p), 3)})
        return {"q": np.round(q, 1).tolist(), "p_hyper": round(p_hyper, 4), "p_hypo": round(p_hypo, 4),
                "alerts": alerts, "inference_ms": round((time.perf_counter() - t0) * 1000, 2)}
