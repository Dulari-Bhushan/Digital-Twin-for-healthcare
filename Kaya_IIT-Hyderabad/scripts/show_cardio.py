"""Print the headline numbers of results/cardio_metrics.json."""
import json
import sys

d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "results/cardio_metrics.json"))
print(d["n_mornings"], "mornings,", d["n_patients"], "patients, positive rate", round(d["positive_rate"], 4), "horizon", d["horizon_h"], "h")
print("AUROC     ", {k: round(v["auroc"], 3) for k, v in d["overall"].items()})
print("AUPRC     ", {k: round(v["auprc"], 3) for k, v in d["overall"].items()})
print("CI95      ", {k: [round(x, 3) for x in v["ci95"]] for k, v in d["auroc_with_ci"].items()})
print("fused gain", {k: (round(v["fused_minus_this"]["mean"], 3), [round(x, 3) for x in v["fused_minus_this"]["ci95"]])
                     for k, v in d["auroc_with_ci"].items() if "fused_minus_this" in v})
print("prodrome  ", {k: round(v, 3) if isinstance(v, float) else v for k, v in d["prodrome_event_vs_benign"].items()})
for k, v in d["alert_replay"].items():
    if isinstance(v, dict):
        print("alerts", k, {m: round(v[m], 3) for m in ("sensitivity", "precision", "false_alerts_per_patient_month", "median_lead_h", "events")})
print("stack     ", d["stack_weights"])
for ex in d["example_explanations"][:1]:
    print("example   ", round(ex["probability"], 3), [(x["label"], x["stream"], round(x["push"], 2)) for x in ex["drivers"]])
