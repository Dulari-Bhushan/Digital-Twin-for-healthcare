"""Train the diabetic retinopathy grader on APTOS 2019 and test it on the Indian IDRiD dataset.

Ordinal regression (predict a continuous severity, then threshold) with an EfficientNet backbone, evaluated with
quadratic weighted kappa and referable-DR (grade >= 2) AUROC. Grad-CAM overlays are exported for a few images.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import timm
import torch
import torch.nn as nn
from scipy.optimize import minimize
from sklearn.metrics import accuracy_score, cohen_kappa_score, roc_auc_score
from sklearn.model_selection import train_test_split

import eye_data as D

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def to_tensor(batch: np.ndarray, dev) -> torch.Tensor:
    x = (batch.astype(np.float32) / 255.0 - MEAN) / STD
    return torch.from_numpy(x).permute(0, 3, 1, 2).to(dev)


def augment(batch: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = np.empty_like(batch)
    for i, im in enumerate(batch):
        if rng.random() < 0.5:
            im = im[:, ::-1]
        if rng.random() < 0.5:
            im = im[::-1]
        k = rng.integers(0, 4)
        im = np.rot90(im, k)
        ang = rng.uniform(-25, 25)
        M = cv2.getRotationMatrix2D((im.shape[1] / 2, im.shape[0] / 2), ang, rng.uniform(0.92, 1.08))
        im = cv2.warpAffine(np.ascontiguousarray(im), M, (im.shape[1], im.shape[0]), borderValue=(128, 128, 128))
        out[i] = im
    return out


def thresholds(pred, y):
    """Optimise the three cut points between grades to maximise quadratic weighted kappa."""
    def cut(p, t):
        return np.digitize(p, np.sort(t))
    f = lambda t: -cohen_kappa_score(y, cut(pred, t), weights="quadratic")
    r = minimize(f, [0.5, 1.5, 2.5, 3.5], method="Nelder-Mead")
    return np.sort(r.x)


@torch.no_grad()
def predict(model, arr, dev, bs=64):
    model.eval()
    out = []
    for i in range(0, len(arr), bs):
        x = to_tensor(arr[i:i + bs], dev)
        out.append(((model(x) + model(x.flip(3))) / 2).squeeze(1).float().cpu().numpy())   # flip TTA
    return np.concatenate(out)


def metrics(pred, y, th):
    cls = np.digitize(pred, th)
    ref = (y >= 2).astype(int)
    return {"n": int(len(y)), "qwk": float(cohen_kappa_score(y, cls, weights="quadratic")),
            "accuracy": float(accuracy_score(y, cls)),
            "referable_auroc": float(roc_auc_score(ref, pred)) if ref.min() != ref.max() else None,
            "within_one_grade": float(np.mean(np.abs(cls - y) <= 1))}


def gradcam(model, x, dev):
    """Grad-CAM on the last convolutional features; returns an (H, W) map in [0, 1] per image."""
    feats, grads = [], []
    layer = model.conv_head if hasattr(model, "conv_head") else list(model.children())[-3]
    h1 = layer.register_forward_hook(lambda m, i, o: feats.append(o))
    h2 = layer.register_full_backward_hook(lambda m, gi, go: grads.append(go[0]))
    model.eval()
    x = x.clone().requires_grad_(True)
    out = model(x).sum()
    model.zero_grad()
    out.backward()
    h1.remove(); h2.remove()
    w = grads[0].mean((2, 3), keepdim=True)
    cam = torch.relu((w * feats[0]).sum(1))
    cam = nn.functional.interpolate(cam[:, None], size=x.shape[2:], mode="bilinear", align_corners=False)[:, 0]
    cam = cam - cam.amin((1, 2), keepdim=True)
    cam = cam / (cam.amax((1, 2), keepdim=True) + 1e-8)
    return cam.detach().cpu().numpy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aptos", type=Path, required=True)
    ap.add_argument("--idrid", type=Path, default=None)
    ap.add_argument("--arch", default="efficientnet_b2")
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--skip-train", action="store_true", help="reuse models/dr_grader.pt and the saved thresholds")
    ap.add_argument("--cache", type=Path, default=Path("data/processed/eye"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--models", type=Path, default=Path("models"))
    a = ap.parse_args()
    dev = "cuda"
    a.cache.mkdir(parents=True, exist_ok=True)
    a.out.mkdir(exist_ok=True, parents=True)
    a.models.mkdir(exist_ok=True, parents=True)

    paths, y = D.aptos(a.aptos)
    X = D.build_cache(paths, a.cache / "aptos_320.npy")
    print("APTOS cached", X.shape, flush=True)
    itr, iva = train_test_split(np.arange(len(y)), test_size=0.15, stratify=y, random_state=0)

    model = timm.create_model(a.arch, pretrained=not a.skip_train, num_classes=1).to(dev)
    if a.skip_train:
        model.load_state_dict(torch.load(a.models / "dr_grader.pt", map_location=dev))
        res = json.loads((a.out / "dr_grader_metrics.json").read_text())
        th = np.array(res["thresholds"])
    else:
        opt = torch.optim.AdamW(model.parameters(), lr=4e-4, weight_decay=1e-4)
        steps = a.epochs * (len(itr) // a.bs)
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=4e-4, total_steps=steps, pct_start=0.15)
        scaler = torch.cuda.amp.GradScaler()
        rng = np.random.default_rng(0)
        best, best_state = -1, None
        for ep in range(a.epochs):
            model.train()
            perm = rng.permutation(itr)
            t0, tot = time.time(), 0.0
            for i in range(0, len(perm) - a.bs + 1, a.bs):
                b = perm[i:i + a.bs]
                x = to_tensor(augment(X[b], rng), dev)
                t = torch.from_numpy(y[b].astype(np.float32)).to(dev)
                with torch.autocast("cuda", dtype=torch.float16):
                    loss = nn.functional.smooth_l1_loss(model(x).squeeze(1).float(), t)
                opt.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.step(opt)
                scaler.update()
                sched.step()
                tot += loss.item()
            pv = predict(model, X[iva], dev)
            k = cohen_kappa_score(y[iva], np.digitize(pv, [0.5, 1.5, 2.5, 3.5]), weights="quadratic")
            print(f"epoch {ep + 1}/{a.epochs} loss {tot / (len(perm) // a.bs):.3f} val_qwk {k:.3f} ({time.time() - t0:.0f}s)", flush=True)
            if k > best:
                best, best_state = k, {n: v.clone() for n, v in model.state_dict().items()}
        model.load_state_dict(best_state)
        torch.save(best_state, a.models / "dr_grader.pt")

        pv = predict(model, X[iva], dev)
        th = thresholds(pv, y[iva])
        res = {"arch": a.arch, "thresholds": th.tolist(), "aptos_validation": metrics(pv, y[iva], th)}
        print(res, flush=True)

    if a.idrid is not None:
        sets = D.idrid(a.idrid)
        res["idrid"] = {}
        keep = {}
        for split, (p, g, dme) in sets.items():
            Xi = D.build_cache(p, a.cache / f"idrid_{split}_320.npy")
            pr = predict(model, Xi, dev)
            res["idrid"][split] = metrics(pr, g, th)
            keep[split] = (Xi, pr, g, p)
        print(res["idrid"], flush=True)
        # Grad-CAM exports: one test image per grade
        out_dir = Path("artifacts/eye")
        out_dir.mkdir(parents=True, exist_ok=True)
        Xi, pr, g, p = keep["test"]
        cls = np.digitize(pr, th)
        info = []
        for grade in range(5):
            idx = np.flatnonzero((g == grade) & (cls == grade))
            idx = idx if len(idx) else np.flatnonzero(g == grade)
            if not len(idx):
                continue
            i = int(idx[0])
            x = to_tensor(Xi[i:i + 1], dev)
            cam = gradcam(model, x, dev)[0]
            base = cv2.cvtColor(cv2.imread(p[i]), cv2.COLOR_BGR2RGB)
            side = 480
            h, w = base.shape[:2]
            s = max(h, w)
            sq = np.zeros((s, s, 3), np.uint8)
            sq[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = base
            sq = cv2.resize(sq, (side, side), interpolation=cv2.INTER_AREA)
            heat = cv2.applyColorMap((cv2.resize(cam, (side, side)) * 255).astype(np.uint8), cv2.COLORMAP_JET)
            heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
            over = cv2.addWeighted(sq, 0.6, heat, 0.4, 0)
            cv2.imwrite(str(out_dir / f"grade{grade}.jpg"), cv2.cvtColor(sq, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
            cv2.imwrite(str(out_dir / f"grade{grade}_cam.jpg"), cv2.cvtColor(over, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
            info.append({"grade": grade, "image": Path(p[i]).name, "predicted_severity": float(pr[i]),
                         "predicted_grade": int(cls[i])})
        (out_dir / "index.json").write_text(json.dumps({"source": "IDRiD test set (CC BY 4.0)", "items": info}, indent=1))
    (a.out / "dr_grader_metrics.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
