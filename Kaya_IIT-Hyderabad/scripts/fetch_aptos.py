"""Download the APTOS 2019 diabetic retinopathy dataset (3,662 labelled fundus images, Aravind Eye Hospital).

Needs Kaggle credentials and the competition rules accepted in a browser first:
  https://www.kaggle.com/competitions/aptos2019-blindness-detection
Credentials: ~/.kaggle/kaggle.json, or KAGGLE_USERNAME and KAGGLE_KEY in the environment.
"""
from pathlib import Path

import kagglehub

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

if __name__ == "__main__":
    src = Path(kagglehub.competition_download("aptos2019-blindness-detection"))
    RAW.mkdir(parents=True, exist_ok=True)
    link = RAW / "aptos"
    if not link.exists():
        link.symlink_to(src, target_is_directory=True)
    print("APTOS at", src, "->", link)
