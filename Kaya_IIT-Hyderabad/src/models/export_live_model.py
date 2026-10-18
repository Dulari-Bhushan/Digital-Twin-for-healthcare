"""Export the glucose GRU for dependency-free live inference.

Writes artifacts/model/gru_numpy.npz (weights), calibration.json (conformal offsets, isotonic knots, alert
thresholds for the GRU alone) and reference.json (a few torch outputs the numpy implementation must reproduce).

Usage (GPU box):  PYTHONPATH=src/models python src/models/export_live_model.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch

import glucose as G
from polish_glucose import conformal_offsets, fit_iso
from windows import load_synthetic, split_by_patient

ROOT = Path(__file__).resolve().parents[2]


def main():
    out = ROOT / "artifacts" / "model"
    out.mkdir(parents=True, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    gru = G.GlucoseGRU()
    gru.load_state_dict(torch.load(ROOT / "models/glucose_gru_synthetic.pt", map_location=dev))
    gru.to(dev).eval()
    np.savez(out / "gru_numpy.npz", **{k: v.detach().cpu().numpy().astype(np.float32) for k, v in gru.state_dict().items()})

    syn = load_synthetic(ROOT / "data/synthetic", stride=6)
    _, va, _ = split_by_patient(syn)
    q, p = G.predict(gru, va, dev)
    off = conformal_offsets(q, va.y)
    isos = fit_iso(p, va.ev, va.ev_mask)
    pol = json.loads((ROOT / "results/glucose_polish.json").read_text())
    thr = {"hyper": pol["alerts_synthetic"]["hyper"]["chosen"]["<= 1.0 false alerts/patient-day"]["threshold"],
           "hypo": pol["alerts_synthetic"]["hypo"]["chosen"]["<= 1.0 false alerts/patient-day"]["threshold"]}
    cal = {"conformal_offsets": off.tolist(), "alert_thresholds": thr,
           "isotonic": [{"x": iso.X_thresholds_.tolist(), "y": iso.y_thresholds_.tolist()} for iso in isos]}
    (out / "calibration.json").write_text(json.dumps(cal))

    # reference vectors for the numpy implementation (raw torch outputs, before scaling or calibration)
    idx = np.random.default_rng(0).choice(len(va.y), 6, replace=False)
    with torch.no_grad():
        x = torch.from_numpy(va.x[idx]).to(dev)
        s = torch.from_numpy(va.s[idx]).to(dev)
        qt, lt = gru(x, s)
    ref = {"x": va.x[idx].tolist(), "s": va.s[idx].tolist(), "q": qt.cpu().numpy().tolist(), "logits": lt.cpu().numpy().tolist()}
    (out / "reference.json").write_text(json.dumps(ref))
    print("exported", sorted(p.name for p in out.iterdir()))


if __name__ == "__main__":
    main()
