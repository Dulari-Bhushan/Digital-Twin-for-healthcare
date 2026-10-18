"""Fine-tune the APTOS-trained grader on the IDRiD training set and evaluate on the official IDRiD test set.

Shows how much a small amount of local (Indian) data closes the gap caused by camera and population shift.
Model selection uses a held-out slice of the IDRiD training set; the IDRiD test set is touched once, at the end.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import timm
import torch
import torch.nn as nn
from sklearn.metrics import cohen_kappa_score
from sklearn.model_selection import train_test_split

import eye_data as D
from eye_train import augment, metrics, predict, to_tensor

TH = np.array([0.5, 1.5, 2.5, 3.5])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idrid", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--cache", type=Path, default=Path("data/processed/eye"))
    ap.add_argument("--models", type=Path, default=Path("models"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    a = ap.parse_args()
    dev = "cuda"
    sets = D.idrid(a.idrid)
    Xtr = D.build_cache(sets["train"][0], a.cache / "idrid_train_320.npy")
    Xte = D.build_cache(sets["test"][0], a.cache / "idrid_test_320.npy")
    ytr, yte = sets["train"][1], sets["test"][1]
    itr, iva = train_test_split(np.arange(len(ytr)), test_size=0.2, stratify=ytr, random_state=0)

    model = timm.create_model("efficientnet_b2", pretrained=False, num_classes=1).to(dev)
    model.load_state_dict(torch.load(a.models / "dr_grader.pt", map_location=dev))
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    steps = a.epochs * (len(itr) // a.bs)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=1e-4, total_steps=steps, pct_start=0.2)
    rng = np.random.default_rng(0)
    best, best_state = -1, None
    for ep in range(a.epochs):
        model.train()
        perm = rng.permutation(itr)
        for i in range(0, len(perm) - a.bs + 1, a.bs):
            b = perm[i:i + a.bs]
            x = to_tensor(augment(Xtr[b], rng), dev)
            t = torch.from_numpy(ytr[b].astype(np.float32)).to(dev)
            with torch.autocast("cuda", dtype=torch.float16):
                loss = nn.functional.smooth_l1_loss(model(x).squeeze(1).float(), t)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
        pv = predict(model, Xtr[iva], dev)
        k = cohen_kappa_score(ytr[iva], np.digitize(pv, TH), weights="quadratic")
        print(f"epoch {ep + 1}/{a.epochs} val_qwk {k:.3f}", flush=True)
        if k > best:
            best, best_state = k, {n: v.clone() for n, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    torch.save(best_state, a.models / "dr_grader_idrid_ft.pt")
    res = json.loads((a.out / "dr_grader_metrics.json").read_text())
    res["idrid_finetuned"] = {"test": metrics(predict(model, Xte, dev), yte, TH), "heldout_val_qwk": float(best),
                              "note": "APTOS-trained model fine-tuned on 80% of the IDRiD training set; evaluated once on the IDRiD test set."}
    (a.out / "dr_grader_metrics.json").write_text(json.dumps(res, indent=2))
    print(res["idrid_finetuned"], flush=True)


if __name__ == "__main__":
    main()
