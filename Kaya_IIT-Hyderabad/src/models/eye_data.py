"""Fundus image preprocessing and caching for the diabetic retinopathy grader.

Ben Graham preprocessing: crop the black border, resize, then subtract the local average colour so lesions
stand out under uneven illumination. Images are cached as uint8 arrays so training is fast.
"""
from __future__ import annotations

from multiprocessing import Pool
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

SIZE = 320


def preprocess(path: str, size: int = SIZE) -> np.ndarray:
    img = cv2.imread(str(path))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    ys, xs = np.where(gray > 7)
    if len(ys) > 100:
        img = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = img.shape[:2]
    s = max(h, w)
    canvas = np.zeros((s, s, 3), dtype=np.uint8)           # pad to square, centred
    canvas[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = img
    canvas = cv2.resize(canvas, (size, size), interpolation=cv2.INTER_AREA)
    blur = cv2.GaussianBlur(canvas, (0, 0), size / 30)
    return cv2.addWeighted(canvas, 4, blur, -4, 128)


def build_cache(paths: list[str], out: Path, workers: int = 24) -> np.ndarray:
    if out.exists():
        return np.load(out)
    with Pool(workers) as p:
        arr = np.stack(p.map(preprocess, paths, chunksize=16))
    np.save(out, arr)
    return arr


def aptos(root: Path):
    df = pd.read_csv(root / "train.csv")
    paths = [str(root / "train_images" / f"{i}.png") for i in df.id_code]
    return paths, df.diagnosis.to_numpy()


def idrid(root: Path):
    """IDRiD 'B. Disease Grading': returns (paths, grades, dme) for the official training and testing sets."""
    base = next(root.glob("**/B. Disease Grading"))
    out = {}
    for split, folder, csv in (("train", "a. Training Set", "a. IDRiD_Disease Grading_Training Labels.csv"),
                               ("test", "b. Testing Set", "b. IDRiD_Disease Grading_Testing Labels.csv")):
        lab = pd.read_csv(base / "2. Groundtruths" / csv)
        lab.columns = [c.strip() for c in lab.columns]
        paths = [str(base / "1. Original Images" / folder / f"{n}.jpg") for n in lab["Image name"]]
        out[split] = (paths, lab["Retinopathy grade"].to_numpy(), lab["Risk of macular edema"].to_numpy())
    return out
