"""Build the NHANES 2017-2018 liver dataset (adults with a complete FibroScan exam).

Labels follow common NHANES MASLD practice:
  steatosis          CAP >= 288 dB (controlled attenuation parameter)
  advanced fibrosis  liver stiffness >= 8.0 kPa (approximately F2 or higher)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

CAP_CUTOFF = 288.0
LSM_CUTOFF = 8.0

FILES = {
    "DEMO_J": ["SEQN", "RIAGENDR", "RIDAGEYR", "RIDRETH3"],
    "BMX_J": ["SEQN", "BMXBMI", "BMXWAIST"],
    "LUX_J": ["SEQN", "LUAXSTAT", "LUXSMED", "LUXCAPM"],
    "BIOPRO_J": ["SEQN", "LBXSATSI", "LBXSASSI", "LBXSGTSI"],
    "CBC_J": ["SEQN", "LBXPLTSI"],
    "GHB_J": ["SEQN", "LBXGH"],
    "HDL_J": ["SEQN", "LBDHDD"],
    "TRIGLY_J": ["SEQN", "LBXTR"],
    "GLU_J": ["SEQN", "LBXGLU"],
    "INS_J": ["SEQN", "LBXIN"],
    "DIQ_J": ["SEQN", "DIQ010"],
}
RENAME = {
    "RIAGENDR": "sex_code", "RIDAGEYR": "age", "RIDRETH3": "ethnicity", "BMXBMI": "bmi", "BMXWAIST": "waist_cm",
    "LUXSMED": "lsm_kpa", "LUXCAPM": "cap_db", "LBXSATSI": "alt", "LBXSASSI": "ast", "LBXSGTSI": "ggt",
    "LBXPLTSI": "platelets", "LBXGH": "hba1c", "LBDHDD": "hdl", "LBXTR": "triglycerides", "LBXGLU": "glucose",
    "LBXIN": "insulin",
}


def build(raw: Path) -> pd.DataFrame:
    df = None
    for f, cols in FILES.items():
        d = pd.read_sas(raw / f"{f}.XPT")[cols]
        df = d if df is None else df.merge(d, on="SEQN", how="left")
    df = df.rename(columns=RENAME)
    df = df[(df.age >= 18) & (df.LUAXSTAT == 1) & df.lsm_kpa.notna() & df.cap_db.notna()].copy()
    df["male"] = (df.sex_code == 1).astype(float)
    df["homa_ir"] = df.glucose * df.insulin / 405.0
    df["diabetes"] = ((df.DIQ010 == 1) | (df.hba1c >= 6.5) | (df.glucose >= 126)).astype(int)
    df["steatosis"] = (df.cap_db >= CAP_CUTOFF).astype(int)
    df["adv_fibrosis"] = (df.lsm_kpa >= LSM_CUTOFF).astype(int)
    df["asian"] = (df.ethnicity == 6).astype(int)            # Non-Hispanic Asian (NHANES does not isolate Indians)
    # Established non-invasive scores, used as baselines.
    df["fib4"] = df.age * df.ast / (df.platelets * np.sqrt(df.alt))
    df["fli"] = _fli(df)
    df["hsi"] = 8 * df.alt / df.ast + df.bmi + 2 * (1 - df.male) + 2 * df.diabetes
    return df.drop(columns=["LUAXSTAT", "DIQ010", "sex_code"]).reset_index(drop=True)


def _fli(d: pd.DataFrame) -> pd.Series:
    """Fatty Liver Index (Bedogni 2006), 0-100."""
    z = (0.953 * np.log(d.triglycerides) + 0.139 * d.bmi + 0.718 * np.log(d.ggt) + 0.053 * d.waist_cm - 15.745)
    return 100 * np.exp(z) / (1 + np.exp(z))


if __name__ == "__main__":
    import sys
    raw = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/nhanes_2017_2018")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "data/processed/nhanes_liver.parquet")
    df = build(raw)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"{len(df)} adults; diabetes {int(df.diabetes.sum())}; asian {int(df.asian.sum())}; "
          f"steatosis {df.steatosis.mean():.2f}; advanced fibrosis {df.adv_fibrosis.mean():.3f}")
