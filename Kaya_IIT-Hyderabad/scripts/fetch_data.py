"""Download the open datasets Kaya uses. Raw data is git-ignored; this script is the provenance record.

Usage: python scripts/fetch_data.py [nhanes|cgmacros|all]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

NHANES_BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles"
NHANES_FILES = {
    "DEMO_J": "demographics",
    "BMX_J": "body measures",
    "LUX_J": "liver ultrasound transient elastography (FibroScan)",
    "BIOPRO_J": "standard biochemistry (ALT, AST, GGT, creatinine)",
    "TRIGLY_J": "triglycerides, LDL",
    "HDL_J": "HDL cholesterol",
    "GHB_J": "glycohemoglobin (HbA1c)",
    "GLU_J": "fasting glucose, insulin",
    "ALB_CR_J": "urine albumin/creatinine",
    "BPX_J": "blood pressure",
    "DIQ_J": "diabetes questionnaire",
    "DR1TOT_J": "dietary recall, day 1 totals",
    "SLQ_J": "sleep questionnaire",
    "PAQ_J": "physical activity questionnaire",
}
# PhysioNet's own file server is heavily throttled from many networks; its open S3 mirror is fast.
CGMACROS_URL = "https://physionet-open.s3.amazonaws.com/cgmacros/1.0.0/"
CGMACROS_FILES = ["LICENSE.txt", "SHA256SUMS.txt", "DataDictionary.pdf", "DataDictionary_Bio.csv",
                  "DataDictionary_CGMacros-00X.csv", "CGMacros_dateshifted365.zip"]


def fetch_nhanes() -> None:
    out = RAW / "nhanes_2017_2018"
    out.mkdir(parents=True, exist_ok=True)
    for code, desc in NHANES_FILES.items():
        dest = out / f"{code}.XPT"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"skip {code}")
            continue
        r = requests.get(f"{NHANES_BASE}/{code}.xpt", timeout=120)
        r.raise_for_status()
        if not r.content.startswith(b"HEADER RECORD"):  # SAS transport files start with this marker
            raise ValueError(f"{code}: response is not a SAS XPT file (got {r.content[:40]!r})")
        dest.write_bytes(r.content)
        print(f"ok   {code:9s} {len(r.content) / 1e6:6.2f} MB  {desc}")


def fetch_cgmacros() -> None:
    out = RAW / "cgmacros"
    out.mkdir(parents=True, exist_ok=True)
    for name in CGMACROS_FILES:
        subprocess.run(["wget", "-c", "-q", "--show-progress", "-P", str(out), CGMACROS_URL + name], check=True)
    subprocess.run(["unzip", "-n", "-q", str(out / "CGMacros_dateshifted365.zip"), "-d", str(out)], check=True)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("nhanes", "all"):
        fetch_nhanes()
    if which in ("cgmacros", "all"):
        fetch_cgmacros()
