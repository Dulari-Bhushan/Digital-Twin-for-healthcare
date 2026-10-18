"""Build the Kaya presentation (docs/Kaya_presentation.pdf) from the saved results and screenshots."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
DOCS = Path(__file__).parent
INK, MUTED, TEAL, BLUE, AMBER, RED, LINE = "#14212b", "#5b6b77", "#0f766e", "#1d6fb8", "#b45309", "#b42318", "#dfe4e7"
plt.rcParams["font.family"] = "DejaVu Sans"

glu = json.loads((ROOT / "results/glucose_polish.json").read_text())
base = json.loads((ROOT / "results/glucose_metrics.json").read_text())
liv = json.loads((ROOT / "results/liver_static_metrics.json").read_text())
eye_p = ROOT / "results/dr_grader_metrics.json"
eye = json.loads(eye_p.read_text()) if eye_p.exists() else None

pages = []


def new(title: str, sub: str | None = None):
    fig = plt.figure(figsize=(13.33, 7.5))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56.25)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 100, 56.25, fc="white", ec="none"))
    ax.add_patch(plt.Rectangle((0, 52.2), 100, 0.5, fc=TEAL, ec="none"))
    ax.text(5, 49, title, fontsize=26, fontweight="bold", color=INK, va="center")
    if sub:
        ax.text(5, 44.8, sub, fontsize=14, color=MUTED, va="center")
    ax.text(5, 2.2, "Kaya · IIT Hyderabad · Happiest Health Digital Twin Challenge", fontsize=9, color=MUTED)
    ax.text(95, 2.2, str(len(pages) + 1), fontsize=9, color=MUTED, ha="right")
    pages.append(fig)
    return fig, ax


def card(ax, x, y, w, h, big, small, color=TEAL):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1", fc="#f5f7f8", ec=LINE, lw=1.2))
    ax.text(x + w / 2, y + h * 0.62, big, ha="center", va="center", fontsize=30, fontweight="bold", color=color)
    ax.text(x + w / 2, y + h * 0.22, small, ha="center", va="center", fontsize=11, color=MUTED, linespacing=1.4)


def bullets(ax, x, y, items, size=15, gap=4.4, color=INK):
    for i, t in enumerate(items):
        ax.text(x, y - i * gap, "•  " + t, fontsize=size, color=color, va="top", linespacing=1.4)


# 1 ---------------------------------------------------------------- title
fig = plt.figure(figsize=(13.33, 7.5))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100); ax.set_ylim(0, 56.25); ax.axis("off")
ax.add_patch(plt.Rectangle((0, 0), 100, 56.25, fc=TEAL, ec="none"))
ax.text(8, 33, "Kaya", fontsize=84, fontweight="bold", color="white", va="center")
ax.text(8, 22, "A multi-organ digital twin for Type 2 Diabetes", fontsize=26, color="white", va="center")
ax.text(8, 16, "It shows what glucose does to the liver, eyes and kidneys, and lets a doctor test a change first.", fontsize=15, color="#d9f0ec", va="center")
ax.text(8, 7, "Team Kaya · IIT Hyderabad · Dulari Bhushan, Prateek Giddaplavar", fontsize=14, color="white", va="center")
ax.text(8, 3.6, "Happiest Health Reimagining and Reforming Healthcare in India Summit 2026 · Digital Twin Challenge, Phase 1", fontsize=10.5, color="#d9f0ec", va="center")
pages.append(fig)

# 2 ---------------------------------------------------------------- problem
fig, ax = new("The damage from diabetes is silent", "Glucose is tracked. The organs it harms are checked once a year, if at all.")
card(ax, 5, 22, 28, 18, "100M+", "people with diabetes in India\n(ICMR-INDIAB)")
card(ax, 36, 22, 28, 18, "21.7%", "of Indians with diabetes had\nretinopathy (AIOS screening)")
card(ax, 67, 22, 28, 18, "22%", "of US adults with diabetes have\nadvanced liver stiffness (NHANES)", AMBER)
bullets(ax, 5, 17, ["Fatty liver, retinopathy and kidney disease build for years before symptoms.",
                    "Existing twins and apps forecast sugar and coach diet. None we reviewed links it to organ damage."], 14.5, 5)

# 3 ---------------------------------------------------------------- landscape
fig, ax = new("What exists, and the gap", "Reviewed from public sources")
rows = [("Twin Health", "Remission program: CGM, wearables, care team", "Reports liver and weight benefit; closed program"),
        ("Fitterfly, sugar.fit, Ultrahuman", "CGM plus coaching and scores for Indian users", "Glucose and lifestyle; no organ outcomes"),
        ("Dexcom, Roche SmartGuide", "Predictive low-glucose alerts 20-30 min ahead", "Glucose only"),
        ("Remidio + RetinaRisk", "Offline smartphone DR screening, risk-based interval", "Eye only; no wearable link"),
        ("ARTEMIs, HEPATWIN (EU)", "Virtual organ twins for liver disease", "Research stage; liver only"),
        ("Kaya", "One twin: glucose to liver and eye, plus what-if", "Open; validated per module")]
y = 38
ax.text(5, y + 3, "Who", fontsize=11, color=MUTED, fontweight="bold")
ax.text(30, y + 3, "What it does", fontsize=11, color=MUTED, fontweight="bold")
ax.text(68, y + 3, "Gap", fontsize=11, color=MUTED, fontweight="bold")
for i, (a, b, c) in enumerate(rows):
    yy = y - i * 5.6
    last = i == len(rows) - 1
    if last:
        ax.add_patch(FancyBboxPatch((3.5, yy - 2.2), 93, 5, boxstyle="round,pad=0,rounding_size=0.8", fc="#d9f0ec", ec=TEAL, lw=1.3))
    ax.text(5, yy, a, fontsize=12.5, fontweight="bold", color=INK, va="center")
    ax.text(30, yy, b, fontsize=11.5, color=INK, va="center")
    ax.text(68, yy, c, fontsize=11.5, color=TEAL if last else MUTED, va="center", fontweight="bold" if last else None)
    if not last:
        ax.plot([4, 96], [yy - 2.8, yy - 2.8], color=LINE, lw=0.8)

# 4 ---------------------------------------------------------------- what Kaya does
fig, ax = new("What Kaya does", "Two data streams fused into one twin, four questions answered, one place to test a change")
mods = [("Glucose", "What will glucose do in the\nnext 2 hours? Is an event coming?", TEAL),
        ("Liver", "Is fat building up?\nIs fibrosis developing?", BLUE),
        ("Eye", "What is the retinopathy grade\nand where is it heading?", BLUE),
        ("Kidney (next)", "Is kidney function\ndeclining?", MUTED)]
for i, (t, s, c) in enumerate(mods):
    x = 5 + i * 23.3
    ax.add_patch(FancyBboxPatch((x, 20), 21.5, 17, boxstyle="round,pad=0,rounding_size=1", fc="#f5f7f8", ec=c, lw=1.8, ls="--" if i == 3 else "-"))
    ax.text(x + 10.75, 33.5, t, ha="center", fontsize=16, fontweight="bold", color=c)
    ax.text(x + 10.75, 26.5, s, ha="center", va="center", fontsize=11, color=INK, linespacing=1.4)
ax.add_patch(FancyBboxPatch((5, 8), 90, 9, boxstyle="round,pad=0,rounding_size=1", fc="#d9f0ec", ec=TEAL, lw=1.5))
ax.text(50, 13.8, "What-if engine", ha="center", fontsize=16, fontweight="bold", color=TEAL)
ax.text(50, 10.4, "Change carbohydrates, walking, medication or steps, and see the glucose curve and one-year organ risk move", ha="center", fontsize=12, color=INK)
ax.text(5, 41.5, "Static: labs, genetics, history     +     Dynamic: CGM, heart rate, sleep, steps, meals", fontsize=12.5, color=MUTED)

# 5 ---------------------------------------------------------------- architecture
fig, ax = new("")
img = mpimg.imread(DOCS / "architecture.png")
ih, iw = img.shape[:2]
hh = 47.5
ww = hh * iw / ih
ax.imshow(img, extent=[50 - ww / 2, 50 + ww / 2, 4, 4 + hh], aspect="auto", zorder=2)

# 6 ---------------------------------------------------------------- data
fig, ax = new("Data: open or synthetic only", "What is real, what is simulated, and how we validate")
tbl = [("CGMacros (PhysioNet)", "Real", "Glucose forecaster: 34 subjects, subject-level cross-validation", TEAL),
       ("NHANES 2017-2018", "Real", "Liver model: 4,745 adults with FibroScan labels", TEAL),
       ("APTOS 2019 + IDRiD", "Real", "Retina grader: train on APTOS, test on Indian IDRiD", TEAL),
       ("Synthetic cohort", "Simulated", "2,000 patients: links glucose patterns to organs for the twin and what-if", AMBER)]
for i, (a, b, c, col) in enumerate(tbl):
    yy = 38 - i * 6.2
    ax.text(5, yy, a, fontsize=14, fontweight="bold", color=INK, va="center")
    ax.add_patch(FancyBboxPatch((33, yy - 1.5), 9, 3, boxstyle="round,pad=0,rounding_size=1.2", fc=col, ec="none"))
    ax.text(37.5, yy, b, color="white", fontsize=11, fontweight="bold", ha="center", va="center")
    ax.text(45, yy, c, fontsize=12, color=INK, va="center")
ax.add_patch(FancyBboxPatch((5, 6), 90, 9.5, boxstyle="round,pad=0,rounding_size=1", fc="#fdf0d8", ec=AMBER, lw=1.3))
ax.text(7, 12.5, "Why this is honest", fontsize=13, fontweight="bold", color=AMBER)
ax.text(7, 8.6, "No public dataset links one person's glucose to liver, eye and kidney outcomes. Each module is checked on real data where it exists.\n"
        "The glucose-to-organ links and what-if effect sizes are editable, literature-informed assumptions, labelled as simulation in the product.", fontsize=11, color=INK, va="center", linespacing=1.5)

# 7 ---------------------------------------------------------------- glucose
fig, ax = new("Glucose forecasting on real, held-out subjects", "CGMacros, 34 subjects, subject-level 5-fold cross-validation")
cg = glu["cgmacros"]
ens = cg["ensemble_calibrated"]
pers = base["cgmacros"]["persistence"]
ax2 = fig.add_axes([0.07, 0.18, 0.42, 0.52])
hz = ["30 min", "60 min", "120 min"]
xs = range(3)
ax2.bar([i - 0.2 for i in xs], pers["rmse"], 0.38, color="#b4bcc2", label="No change (persistence)")
ax2.bar([i + 0.2 for i in xs], ens["rmse"], 0.38, color=TEAL, label="Kaya ensemble")
for i in xs:
    ax2.text(i - 0.2, pers["rmse"][i] + 0.6, f"{pers['rmse'][i]:.1f}", ha="center", fontsize=10)
    ax2.text(i + 0.2, ens["rmse"][i] + 0.6, f"{ens['rmse'][i]:.1f}", ha="center", fontsize=10, color=TEAL, fontweight="bold")
ax2.set_xticks(list(xs)); ax2.set_xticklabels(hz); ax2.set_ylabel("RMSE (mg/dL), lower is better")
ax2.spines[["top", "right"]].set_visible(False); ax2.legend(frameon=False, fontsize=10, loc="upper left")
al = glu["alerts_cgmacros"]["hypo"]["chosen"]["<= 1.0 false alerts/patient-day"]
card(ax, 55, 26, 18, 16, f"{al['sensitivity'] * 100:.0f}%", "of low-glucose episodes\ncaught", TEAL)
card(ax, 76, 26, 18, 16, f"{al['median_lead_min']:.0f} min", "median warning\nbefore the low", TEAL)
card(ax, 55, 7, 18, 16, "80%", "interval coverage\n(conformal, exact)", BLUE)
card(ax, 76, 7, 18, 16, "~1/day", "false alerts per patient\nat that operating point", AMBER)

# 8 ---------------------------------------------------------------- liver
fig, ax = new("Liver: validated on real FibroScan data", "NHANES 2017-2018, 4,745 adults, 5-fold cross-validation, 95% CIs in the repository")
a_ = liv["adv_fibrosis"]; s_ = liv["steatosis"]
ax2 = fig.add_axes([0.07, 0.17, 0.52, 0.53])
labels = ["Advanced fibrosis\n(stiffness >= 8 kPa)", "Steatosis\n(CAP >= 288 dB)"]
kaya = [a_["lightgbm_routine"]["all_adults"]["auroc"], s_["lightgbm_routine"]["all_adults"]["auroc"]]
b1 = [a_["baseline_fib4"]["all_adults"]["auroc"], s_["baseline_fli"]["all_adults"]["auroc"]]
b2 = [None, s_["baseline_hsi"]["all_adults"]["auroc"]]
ax2.bar([-0.27, 0.73], kaya, 0.25, color=TEAL, label="Kaya")
ax2.bar([0, 1], b1, 0.25, color="#b4bcc2", label="FIB-4 / FLI")
ax2.bar([1.27], [b2[1]], 0.25, color="#d3d9dd", label="HSI")
for xx, v in zip([-0.27, 0.73, 0, 1, 1.27], [kaya[0], kaya[1], b1[0], b1[1], b2[1]]):
    ax2.text(xx, v + 0.01, f"{v:.2f}", ha="center", fontsize=10)
ax2.set_xticks([0, 1]); ax2.set_xticklabels(labels); ax2.set_ylim(0.5, 0.9); ax2.set_ylabel("AUROC")
ax2.spines[["top", "right"]].set_visible(False); ax2.legend(frameon=False, fontsize=10, loc="upper right")
bullets(ax, 66, 40, ["Fibrosis: 0.83 vs 0.63 for FIB-4", "Steatosis: 0.83 vs FLI 0.82, HSI 0.79",
                     "Holds in adults with diabetes (0.76 / 0.80) and in Asian participants",
                     "On top: a transparent glycemic-load state that moves risk over 12 months (simulation)"], 12.5, 6.2)

# 9 ---------------------------------------------------------------- eye
fig, ax = new("Eye: retinopathy grading, tested on Indian images", "EfficientNet-B2 trained on APTOS 2019, tested on IDRiD (Indian), ordinal grading")
if eye:
    v = eye["aptos_validation"]
    card(ax, 5, 26, 20, 16, f"{v['qwk']:.2f}", "quadratic kappa\nAPTOS held-out", TEAL)
    card(ax, 28, 26, 20, 16, f"{v['referable_auroc']:.2f}", "referable DR AUROC\nAPTOS held-out", TEAL)
    if "idrid" in eye:
        t = eye["idrid"]["test"]
        card(ax, 5, 7, 20, 16, f"{t['qwk']:.2f}", "quadratic kappa\nIDRiD test (Indian)", BLUE)
        card(ax, 28, 7, 20, 16, f"{t['referable_auroc']:.2f}", "referable DR AUROC\nIDRiD test", BLUE)
    imgs = [(ROOT / "artifacts/eye" / f"grade{g}.jpg", ROOT / "artifacts/eye" / f"grade{g}_cam.jpg") for g in (0, 2, 4)]
    for k, (raw, cam) in enumerate(imgs):
        if raw.exists():
            ax.imshow(mpimg.imread(raw), extent=[53 + k * 15, 66 + k * 15, 27.5, 40.5], aspect="auto", zorder=2)
            ax.imshow(mpimg.imread(cam), extent=[53 + k * 15, 66 + k * 15, 12, 25], aspect="auto", zorder=2)
            ax.text(59.5 + k * 15, 41.5, ["No DR", "Moderate", "Proliferative"][k], ha="center", fontsize=11, fontweight="bold", color=INK)
    ax.text(74, 9.4, "Top: IDRiD fundus.  Bottom: Grad-CAM, where the model looked.", ha="center", fontsize=10, color=MUTED)
else:
    ax.text(5, 30, "Results pending", fontsize=16, color=MUTED)

# 10 --------------------------------------------------------------- what-if
fig, ax = new("What-if: test the change on the virtual patient", "Patient 1705, last 14 days replayed with three changes together")
sys.path.insert(0, str(ROOT / "src" / "api"))
from fastapi.testclient import TestClient  # noqa: E402
import app as api  # noqa: E402

with TestClient(api.app) as c:
    r = c.post("/api/patients/1705/whatif", json={"carb_scale": 0.75, "walk_after_meals": 20, "baseline_shift": -12, "steps_delta": 2000}).json()
m = r["metrics"]
items = [("Time in range", f"{m['before']['tir'] * 100:.0f}%", f"{m['after']['tir'] * 100:.0f}%"),
         ("Time above 180", f"{m['before']['tar'] * 100:.0f}%", f"{m['after']['tar'] * 100:.0f}%"),
         ("Liver steatosis risk, 12 months", f"{r['liver']['before']['steatosis'][-1] * 100:.0f}%", f"{r['liver']['after']['steatosis'][-1] * 100:.0f}%"),
         ("Advanced fibrosis, 12 months", f"{r['liver']['before']['adv_fibrosis'][-1] * 100:.1f}%", f"{r['liver']['after']['adv_fibrosis'][-1] * 100:.1f}%"),
         ("Retinopathy progression, 2 years", f"{r['eye']['before'] * 100:.0f}%", f"{r['eye']['after'] * 100:.0f}%")]
ax.text(60, 38.5, "Today", fontsize=12, color=MUTED, fontweight="bold", ha="center")
ax.text(82, 38.5, "With the change", fontsize=12, color=TEAL, fontweight="bold", ha="center")
for i, (a, b, c2) in enumerate(items):
    yy = 34 - i * 5.3
    ax.text(5, yy, a, fontsize=15, color=INK, va="center")
    ax.text(60, yy, b, fontsize=20, color=MUTED, va="center", ha="center")
    ax.text(82, yy, c2, fontsize=20, color=TEAL, va="center", ha="center", fontweight="bold")
    ax.plot([4, 96], [yy - 3, yy - 3], color=LINE, lw=0.8)
ax.text(5, 9, "Walk 20 min after meals, 25% smaller carbohydrate portions, medication optimised. Effect sizes are editable, literature-informed\nassumptions and shown to the clinician as a simulation, not a prediction.", fontsize=11, color=MUTED, linespacing=1.5, va="top")

# 11 --------------------------------------------------------------- product
fig, ax = new("The product", "Doctor workspace and patient view. Replay shows the forecast against what actually happened.")
H = 35.0
for path, x0, crop in ((DOCS / "img/doctor_view.png", 14, (0, 1360)), (DOCS / "img/patient_view.png", 58, (0, 1230))):
    if path.exists():
        im = mpimg.imread(path)[crop[0]:crop[1]]
        w_ = H * im.shape[1] / im.shape[0]
        ax.imshow(im, extent=[x0, x0 + w_, 6.5, 6.5 + H], aspect="auto", zorder=2)
        ax.add_patch(plt.Rectangle((x0, 6.5), w_, H, fc="none", ec=LINE, lw=1.2, zorder=3))
ax.text(33, 4.6, "Doctor view", ha="center", fontsize=11, color=MUTED)
ax.text(71, 4.6, "Patient view", ha="center", fontsize=11, color=MUTED)

# 12 --------------------------------------------------------------- limits and roadmap
fig, ax = new("Limitations, ethics and what is next")
ax.text(5, 44, "Limitations we state openly", fontsize=15, fontweight="bold", color=AMBER)
bullets(ax, 5, 40.5, ["Glucose-to-organ links and what-if effect sizes are assumptions, not clinical findings",
                      "Glucose model validated on 34 real subjects; patients in the demo are synthetic",
                      "Decision support for clinicians, not a diagnostic device; not clinically validated"], 12.5, 4.6)
ax.text(5, 24.5, "Roadmap", fontsize=15, fontweight="bold", color=TEAL)
bullets(ax, 5, 21, ["Kidney risk module and an illustrative, clearly labelled retina progression preview",
                    "Hindi, Telugu and Kannada patient view; PDF clinical summary",
                    "Consent records, audit log, role-based access, fuller FHIR and ABDM alignment",
                    "Validate the glucose-to-organ links on real longitudinal data when available"], 12.5, 4.6)

# 13 --------------------------------------------------------------- close
fig = plt.figure(figsize=(13.33, 7.5))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100); ax.set_ylim(0, 56.25); ax.axis("off")
ax.add_patch(plt.Rectangle((0, 0), 100, 56.25, fc=TEAL, ec="none"))
ax.text(8, 34, "Existing twins manage sugar.", fontsize=34, color="white", va="center")
ax.text(8, 26, "Kaya shows what sugar does to the organs, and lets a doctor test the fix first.", fontsize=22, color="#d9f0ec", va="center")
ax.text(8, 12, "Open source, Apache-2.0 · open and synthetic data only · github: see README", fontsize=14, color="white", va="center")
ax.text(8, 7.5, "Team Kaya · IIT Hyderabad · Dulari Bhushan, Prateek Giddaplavar", fontsize=14, color="white", va="center")
pages.append(fig)

with PdfPages(DOCS / "Kaya_presentation.pdf") as pdf:
    for f in pages:
        pdf.savefig(f)
for i, f in enumerate(pages):
    f.savefig(DOCS / "img" / f"slide_{i + 1:02d}.png", dpi=70)
print("saved", len(pages), "slides")
