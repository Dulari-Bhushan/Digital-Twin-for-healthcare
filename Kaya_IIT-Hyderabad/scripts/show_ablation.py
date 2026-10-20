"""Merge the glucose ablation result files and print one table (mean and standard deviation over seeds).

Usage: python scripts/show_ablation.py results/glucose_ablation_gru_*.json [--md results/glucose_ablation_table.md]
"""
import argparse
import json

import numpy as np

LABEL = {
    "cgm_meals": "CGM + meal log",
    "plus_hr_activity": "+ heart rate and activity",
    "plus_basic_record": "+ age, BMI, HbA1c, sex",
    "plus_hrv_sleep": "+ HRV and sleep (nightly and weekly)",
    "full_fusion": "+ full record and genetics (all inputs)",
    "full_minus_hrv_sleep": "all inputs minus HRV and sleep",
    "full_minus_record": "all inputs minus labs, medicines, genetics",
    "full_minus_genetics": "all inputs minus genetics",
}
ORDER = list(LABEL)


def cell(vals, nd=2):
    return f"{np.mean(vals):.{nd}f} ± {np.std(vals):.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--md")
    a = ap.parse_args()
    rungs = {}
    for f in a.files:
        d = json.load(open(f, encoding="utf-8"))
        rungs.update(d["rungs"])
        n_test = d["n_test_windows"]
    lines = [f"Held-out synthetic patients, {n_test:,} windows. Mean ± standard deviation over seeds.", "",
             "| Inputs | RMSE +30 min | RMSE +60 min | RMSE +120 min | High-glucose AUROC | Low-glucose AUROC | Low-glucose AUPRC |",
             "|---|---|---|---|---|---|---|"]
    for name in ORDER:
        if name not in rungs:
            continue
        r = rungs[name]["runs"]
        lines.append(f"| {LABEL[name]} | " + " | ".join([
            cell([x["rmse"][0] for x in r]), cell([x["rmse"][1] for x in r]), cell([x["rmse"][2] for x in r]),
            cell([x["hyper"]["auroc"] for x in r], 3), cell([x["hypo"]["auroc"] for x in r], 3), cell([x["hypo"]["auprc"] for x in r], 3)]) + " |")
    out = "\n".join(lines)
    print(out)
    # paired-by-seed differences for the two questions that matter
    for hi, lo, what in (("full_fusion", "full_minus_hrv_sleep", "Adding HRV and sleep to the full model"),
                         ("full_fusion", "full_minus_record", "Adding labs, medicines and genetics to the full model")):
        if hi in rungs and lo in rungs:
            for i, h in enumerate(("+30", "+60", "+120")):
                d = [lo_r["rmse"][i] - hi_r["rmse"][i] for hi_r, lo_r in zip(rungs[hi]["runs"], rungs[lo]["runs"])]
                print(f"{what}: RMSE {h} min improves by {np.mean(d):+.2f} mg/dL (seed range {min(d):+.2f} to {max(d):+.2f})")
            d = [h_["hypo"]["auroc"] - l_["hypo"]["auroc"] for h_, l_ in zip(rungs[hi]["runs"], rungs[lo]["runs"])]
            print(f"{what}: low-glucose AUROC changes by {np.mean(d):+.3f} (seed range {min(d):+.3f} to {max(d):+.3f})")
    if a.md:
        open(a.md, "w", encoding="utf-8").write(out + "\n")


if __name__ == "__main__":
    main()
