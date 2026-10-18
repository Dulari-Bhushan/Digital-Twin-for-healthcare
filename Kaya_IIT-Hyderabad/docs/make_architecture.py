"""Draw the Kaya architecture diagram (docs/architecture.pdf and .png)."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).parent
INK, MUTED = "#14212b", "#5b6b77"
C = {"data": ("#eef2f4", "#8aa0ae"), "core": ("#d9f0ec", "#0f766e"), "model": ("#e3ecfb", "#1d6fb8"),
     "road": ("#ffffff", "#9aa8b2"), "out": ("#fdf0d8", "#b45309")}

fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 160)
ax.set_ylim(0, 90)
ax.axis("off")


def box(x, y, w, h, title, sub, kind, dashed=False):
    face, edge = C[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=face, ec=edge,
                                lw=1.6, ls="--" if dashed else "-"))
    ax.text(x + w / 2, y + h - 3.2, title, ha="center", va="center", fontsize=11.5, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + (h - 6) / 2 - 0.6, sub, ha="center", va="center", fontsize=8.6, color=MUTED, linespacing=1.35)


def arrow(x1, y1, x2, y2, rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14, lw=1.4, color=MUTED,
                                 connectionstyle=f"arc3,rad={rad}"))


def col_title(x, w, text):
    ax.text(x + w / 2, 84.5, text, ha="center", fontsize=11, color=MUTED, fontweight="bold")


ax.text(2, 88, "Kaya: system architecture", fontsize=20, fontweight="bold", color=INK, va="top")
ax.text(2, 83.2, "Multi-organ digital twin for Type 2 Diabetes. Open and synthetic data only.", fontsize=11, color=MUTED, va="top")

# columns
X = [2, 36, 70, 104, 130]
W = [28, 28, 28, 22, 28]
for x, w, t in zip(X, W, ["1  DATA (open / synthetic)", "2  FUSION", "3  MODELS", "4  SIMULATION", "5  SERVE AND USE"]):
    ax.text(x, 77, t, fontsize=10, color=MUTED, fontweight="bold")

# 1 data
box(2, 60, 28, 12, "CGMacros", "Real CGM, meals, Fitbit\nPhysioNet, 34 subjects used", "data")
box(2, 44, 28, 12, "NHANES 2017-2018", "Real labs + FibroScan\n4,745 adults", "data")
box(2, 28, 28, 12, "Synthetic cohort", "2,000 patients, 14 days\nEHR, genetics, CGM, wearables", "data")
box(2, 12, 28, 12, "APTOS 2019 + IDRiD", "Fundus images\nIndian-origin test set", "data")

# 2 fusion
box(36, 30, 28, 36, "Patient state encoder", "Static EHR stream\nlabs, genetics, history\n\n+\n\nDynamic wearable stream\nglucose, heart rate,\nsleep, steps, meals\n\n= one twin per patient", "core")
for y in (66, 50, 34):
    arrow(30, y, 36, 48 if y != 34 else 40)
box(36, 12, 28, 12, "Image pipeline", "Crop, resize, local contrast\nfundus -> tensor", "data")
arrow(30, 18, 36, 18)

# 3 models
box(70, 61, 28, 14, "Glucose core", "GRU + LightGBM ensemble\nconformal intervals,\ncalibrated alerts", "model")
box(70, 46, 28, 12, "Liver", "NHANES-trained risk (AUROC 0.83)\n+ glycemic-load state, 90-day lag", "model")
box(70, 30, 28, 12, "Eye", "EfficientNet DR grader\n+ progression risk, Grad-CAM", "model")
box(70, 14, 28, 12, "Kidney", "NHANES-trained risk + eGFR path", "model")
for y in (68, 52, 36):
    arrow(64, 48, 70, y, rad=0.0)
arrow(64, 48, 70, 20, rad=0.0)

# 4 simulation
box(104, 40, 22, 28, "What-if engine", "Change carbs, walking,\nmedication, steps\n\nre-run glucose metrics,\nliver and eye risk,\nbefore vs after", "core")
for y in (68, 52, 36):
    arrow(98, y, 104, 54, rad=0.0)

# 5 serve
box(130, 58, 28, 14, "FastAPI + FHIR R4", "Patients, twin, series,\nwhat-if, alerts, Observations", "out")
box(130, 38, 28, 16, "Doctor dashboard", "Triage list, glucose twin\nwith forecast replay,\norgan panels, what-if", "out")
box(130, 18, 28, 16, "Patient view", "Plain language outlook,\none nudge, try a change", "out")
arrow(126, 54, 130, 64)
arrow(126, 52, 130, 46)
arrow(126, 48, 130, 26)
arrow(144, 58, 144, 54)

# governance bar
ax.add_patch(FancyBboxPatch((2, 1.5), 156, 7, boxstyle="round,pad=0,rounding_size=1", fc="#f5f7f8", ec="#c9d3d9", lw=1.2))
ax.text(80, 5, "Validation: patient-level splits, real-data checks per module, calibration, ablations     |     "
        "Governance: synthetic or open data only (DPDP-aware), decision support not diagnosis, model cards",
        ha="center", va="center", fontsize=8.6, color=INK)

fig.savefig(OUT / "architecture.pdf", bbox_inches="tight")
fig.savefig(OUT / "architecture.png", dpi=150, bbox_inches="tight")
print("saved")
