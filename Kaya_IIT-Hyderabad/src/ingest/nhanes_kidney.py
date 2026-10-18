"""Build the NHANES 2017-2018 kidney dataset (adults with serum creatinine and urine albumin/creatinine).

Targets follow KDIGO: reduced kidney function (eGFR < 60, CKD-EPI 2021 race-free equation) and albuminuria
(urine albumin/creatinine ratio >= 30 mg/g). CKD = either.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

FILES = {
    "DEMO_J": ["SEQN", "RIAGENDR", "RIDAGEYR", "RIDRETH3"],
    "BMX_J": ["SEQN", "BMXBMI", "BMXWAIST"],
    "BPX_J": ["SEQN", "BPXSY1", "BPXSY2", "BPXDI1", "BPXDI2"],
    "BIOPRO_J": ["SEQN", "LBXSCR"],
    "ALB_CR_J": ["SEQN", "URDACT"],
    "GHB_J": ["SEQN", "LBXGH"],
    "HDL_J": ["SEQN", "LBDHDD"],
    "GLU_J": ["SEQN", "LBXGLU"],
    "DIQ_J": ["SEQN", "DIQ010"],
}
RENAME = {"RIAGENDR": "sex_code", "RIDAGEYR": "age", "RIDRETH3": "ethnicity", "BMXBMI": "bmi", "BMXWAIST": "waist_cm",
          "LBXSCR": "creatinine", "URDACT": "uacr", "LBXGH": "hba1c", "LBDHDD": "hdl", "LBXGLU": "glucose"}


def egfr_ckdepi_2021(scr, age, male):
    kappa = np.where(male == 1, 0.9, 0.7)
    alpha = np.where(male == 1, -0.302, -0.241)
    ratio = scr / kappa
    return 142 * np.minimum(ratio, 1) ** alpha * np.maximum(ratio, 1) ** -1.2 * 0.9938 ** age * np.where(male == 1, 1.0, 1.012)


def build(raw: Path) -> pd.DataFrame:
    df = None
    for f, cols in FILES.items():
        d = pd.read_sas(raw / f"{f}.XPT")[cols]
        df = d if df is None else df.merge(d, on="SEQN", how="left")
    df = df.rename(columns=RENAME)
    df["sbp"] = df[["BPXSY1", "BPXSY2"]].mean(axis=1)
    df["dbp"] = df[["BPXDI1", "BPXDI2"]].mean(axis=1)
    df = df[(df.age >= 20) & df.creatinine.notna() & df.uacr.notna()].copy()
    df["male"] = (df.sex_code == 1).astype(float)
    df["egfr"] = egfr_ckdepi_2021(df.creatinine.to_numpy(), df.age.to_numpy(), df.male.to_numpy())
    df["diabetes"] = ((df.DIQ010 == 1) | (df.hba1c >= 6.5) | (df.glucose >= 126)).astype(int)
    df["low_egfr"] = (df.egfr < 60).astype(int)
    df["albuminuria"] = (df.uacr >= 30).astype(int)
    df["ckd"] = ((df.low_egfr == 1) | (df.albuminuria == 1)).astype(int)
    df["asian"] = (df.ethnicity == 6).astype(int)
    return df.drop(columns=["sex_code", "BPXSY1", "BPXSY2", "BPXDI1", "BPXDI2", "DIQ010"]).reset_index(drop=True)


if __name__ == "__main__":
    import sys
    raw = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/nhanes_2017_2018")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "data/processed/nhanes_kidney.parquet")
    df = build(raw)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"{len(df)} adults; diabetes {int(df.diabetes.sum())}; asian {int(df.asian.sum())}; low eGFR {df.low_egfr.mean():.3f}; "
          f"albuminuria {df.albuminuria.mean():.3f}; CKD {df.ckd.mean():.3f}")
    print("diabetes subgroup:", df[df.diabetes == 1][["low_egfr", "albuminuria", "ckd"]].mean().round(3).to_dict())
