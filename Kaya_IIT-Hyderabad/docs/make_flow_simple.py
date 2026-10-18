"""Kaya architecture, two clean pages: the flow (page 1) and the technical detail (page 2).

Writes docs/architecture_overview.svg and docs/architecture_detail.svg. Render with a headless browser.
"""
from pathlib import Path
from xml.sax.saxutils import escape

D = Path(__file__).parent
INK, MUTED, LINE = "#14212b", "#5b6b77", "#9aa8b2"
TEAL, BLUE, AMBER, SLATE = "#0f766e", "#1d6fb8", "#b45309", "#475569"
TINT = {TEAL: "#e4f5f2", BLUE: "#e6eefb", AMBER: "#fdf1dc", SLATE: "#eef2f5"}


class Page:
    def __init__(self, w, h):
        self.w, self.h, self.o = w, h, []
        self.add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
                 f'font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif">')
        self.add('<defs><filter id="sh" x="-5%" y="-5%" width="110%" height="120%"><feDropShadow dx="0" dy="2" stdDeviation="3" '
                 'flood-color="#0f2530" flood-opacity="0.10"/></filter>'
                 '<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f7fafb"/><stop offset="1" stop-color="#eef3f5"/></linearGradient>'
                 '<linearGradient id="core" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e9f7f4"/><stop offset="1" stop-color="#eaf1fc"/></linearGradient>')
        for c in (LINE, TEAL, BLUE, AMBER, SLATE):
            self.add(f'<marker id="a{c[1:]}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                     f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
        self.add('</defs>')
        self.add(f'<rect width="{w}" height="{h}" fill="url(#bg)"/>')

    def add(self, s):
        self.o.append(s)

    def text(self, x, y, s, size=14, fill=INK, weight=400, anchor="start", extra=""):
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" {extra}>{escape(s)}</text>')

    def rect(self, x, y, w, h, fill="#fff", stroke=LINE, r=14, sw=1.6, dash=False, shadow=True):
        d = ' stroke-dasharray="7 5"' if dash else ""
        f = ' filter="url(#sh)"' if shadow else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{f}/>')

    def arrow(self, d, color=LINE, sw=2.4, dash=False, marker=True, start=False):
        ds = ' stroke-dasharray="7 6"' if dash else ""
        m = f'marker-end="url(#a{color[1:]})"' if marker else ""
        ms = f' marker-start="url(#a{color[1:]})"' if start else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{ds} {m}{ms}/>')

    def label(self, x, y, s, color=MUTED):
        self.text(x, y, s, 14, color, 800, extra='letter-spacing="1.6"')

    def pill(self, x, y, w, h, s, color, size=14):
        self.rect(x, y, w, h, "#fff", color, h / 2, 1.5, shadow=False)
        self.text(x + w / 2, y + h / 2 + size * 0.35, s, size, color, 600, "middle")

    def num(self, cx, cy, n, color):
        self.add(f'<circle cx="{cx}" cy="{cy}" r="15" fill="{color}"/>')
        self.text(cx, cy + 5.5, str(n), 15, "#fff", 700, "middle")

    def save(self, name):
        self.add("</svg>")
        (D / name).write_text("\n".join(self.o), encoding="utf-8")
        print("wrote", name)


def header(p, title, sub):
    p.text(70, 68, title, 38, INK, 800)
    p.text(70, 102, sub, 18, MUTED)
    p.pill(1500, 40, 350, 34, "Open + synthetic data only  ·  Decision support", TEAL, 14)


def footer(p, left, y):
    p.add(f'<line x1="70" x2="1850" y1="{y - 24}" y2="{y - 24}" stroke="{LINE}" stroke-width="1"/>')
    p.text(70, y, left, 14, MUTED)
    p.text(1850, y, "Team Kaya · IIT Hyderabad · Digital Twin Challenge, Phase 1", 14, MUTED, 600, "end")


# ===================================================================== page 1
def overview():
    p = Page(1920, 1010)
    header(p, "Kaya: one twin per patient", "It shows what glucose does to the liver, eyes and kidneys, and lets you test a change before trying it on the real patient.")

    p.label(70, 150, "1   WHAT GOES IN")
    inputs = [("⌚", "Wearable stream", BLUE), ("🧪", "EHR and labs", BLUE), ("👁", "Retina scan", BLUE),
              ("✍", "Patient quick log", TEAL), ("🎙", "Voice or chat", TEAL)]
    for i, (ic, t, col) in enumerate(inputs):
        x = 70 + i * 362
        p.rect(x, 166, 332, 70, "#fff", col, 14, 1.8)
        p.add(f'<circle cx="{x + 44}" cy="201" r="24" fill="{TINT[col]}"/>')
        p.text(x + 44, 210, ic, 24, INK, 400, "middle")
        p.text(x + 82, 209, t, 20, INK, 700)
        p.arrow(f"M{x + 166},236 L{x + 166},284", col, 2.6)

    # twin engine
    p.rect(70, 288, 1780, 216, "url(#core)", TEAL, 20, 2.2)
    p.label(98, 320, "2   THE KAYA TWIN")
    p.rect(98, 336, 276, 118, "#fff", TEAL, 16, 2)
    p.text(236, 378, "Patient state", 21, INK, 800, "middle")
    p.text(236, 404, "encoder", 21, INK, 800, "middle")
    p.text(236, 432, "one fused twin", 15, MUTED, 400, "middle")
    p.arrow("M374,395 L408,395", TEAL, 2.6)
    organs = [("Glucose", "2-hour forecast and alerts"), ("Liver", "fat and fibrosis risk"), ("Eye", "retinopathy grade and path"), ("Kidney", "eGFR path and risk")]
    for i, (t, s) in enumerate(organs):
        x = 412 + i * 244
        p.rect(x, 336, 226, 118, "#fff", BLUE, 16, 2)
        p.add(f'<rect x="{x}" y="336" width="8" height="118" rx="4" fill="{BLUE}"/>')
        p.text(x + 28, 380, t, 24, INK, 800)
        p.text(x + 28, 410, s, 15, MUTED)
    p.arrow("M1388,395 L1426,395", TEAL, 2.6)
    p.rect(1430, 336, 392, 118, "#fff", TEAL, 16, 2.6)
    p.text(1626, 378, "What-if engine", 22, INK, 800, "middle")
    p.text(1626, 406, "change a meal, walk, sleep or medicine", 15, MUTED, 400, "middle")
    p.text(1626, 430, "see the new glucose curve and organ risk", 15, MUTED, 400, "middle")
    p.text(960, 486, "Explainable   ·   calibrated uncertainty   ·   safety rules in code   ·   served by one REST API", 15, TEAL, 600, "middle")

    # users
    p.label(70, 552, "3   WHO USES IT, AND HOW")
    lanes = [
        (TEAL, "PATIENT", "on a phone, in 4 languages", [("Today", "one next action, and why"), ("Quick log", "medicines, walk, mood"), ("Try a change", "see tonight's curve"), ("Ask", "by voice or text")]),
        (BLUE, "DOCTOR", "triage, understand, decide", [("Triage", "sorted by risk, with reasons"), ("Full record", "glucose, organs, labs"), ("What-if studio", "test before the real patient"), ("PDF summary", "reports with trends")]),
    ]
    LY, LH, LG = 570, 118, 40
    for li, (col, name, sub, steps) in enumerate(lanes):
        y = LY + li * (LH + LG)
        p.rect(70, y, 220, LH, col, col, 16, 0)
        p.text(180, y + 54, name, 25, "#fff", 800, "middle", 'letter-spacing="1.5"')
        p.text(180, y + 80, sub, 13.5, "#fff", 400, "middle")
        for si, (t, s) in enumerate(steps):
            x = 314 + si * 390
            p.rect(x, y, 366, LH, "#fff", col, 14, 1.8)
            p.add(f'<rect x="{x + 1}" y="{y + 1}" width="364" height="{LH - 2}" rx="13" fill="{TINT[col]}" opacity="0.55"/>')
            p.num(x + 34, y + 42, si + 1, col)
            p.text(x + 62, y + 50, t, 22, INK, 700)
            p.text(x + 62, y + 82, s, 16, MUTED)
            if si < 3:
                p.arrow(f"M{x + 369},{y + LH / 2} L{x + 387},{y + LH / 2}", col, 2.4)
        p.arrow(f"M42,{y + LH / 2} L68,{y + LH / 2}", SLATE, 2.4)
    p.arrow(f"M70,500 L42,500 L42,{LY + LH + LG + LH / 2}", SLATE, 2.4, marker=False)
    # cross links
    for si, lab in ((1, "the log becomes the doctor's adherence diary"), (2, "same twin, same what-if engine")):
        cx = 314 + si * 390 + 186
        y1 = LY + LH
        p.arrow(f"M{cx},{y1 + 3} L{cx},{y1 + LG - 3}", SLATE, 2.2, start=True)
        p.text(cx + 14, y1 + 26, lab, 13.5, SLATE, 600)
    # loop
    py = LY + LH / 2
    p.arrow(f"M{314 + 3 * 390 + 366},{py} L1888,{py} L1888,201 L1854,201", TEAL, 2.4, dash=True)

    # hospital IT
    hy = LY + 2 * (LH + LG) - 14
    p.rect(70, hy, 1780, 54, "#fff", AMBER, 14, 1.8)
    p.add(f'<rect x="70" y="{hy}" width="220" height="54" rx="14" fill="{AMBER}"/>')
    p.text(180, hy + 34, "HOSPITAL IT", 19, "#fff", 800, "middle", 'letter-spacing="1.5"')
    p.text(314, hy + 34, "Plugs in through the REST API:  live readings in  ·  FHIR R4 out  ·  Docker deploy.   Governance and ABDM are on the roadmap.", 16.5, INK, 500)

    footer(p, "Kaya is decision support for clinicians, not a diagnostic device. All patients are synthetic.     Models, metrics and frameworks are on the next page.", 986)
    p.save("architecture_overview.svg")


# ===================================================================== page 2
def detail():
    p = Page(1920, 860)
    header(p, "Under the hood", "The models, what they were trained and tested on, and the software around them.")
    p.label(70, 150, "MODELS AND EVIDENCE")
    cards = [
        ("Glucose", "GRU (PyTorch) + LightGBM ensemble", ["Quantile + adverse-event heads", "Conformal 80% bands, isotonic-calibrated alerts", "Trained on real CGMacros + synthetic cohort", "RMSE 12.6 / 21.1 / 28.2 mg/dL at 30 / 60 / 120 min", "Catches 72% of lows, median 45 min ahead"]),
        ("Liver", "LightGBM + logistic regression, SHAP", ["NHANES 2017-18, 4,745 adults, FibroScan labels", "Advanced fibrosis AUROC 0.83 (FIB-4: 0.63)", "Steatosis AUROC 0.83 (FLI: 0.82)", "Liver-fat state: mechanistic, driven by glucose"]),
        ("Eye", "EfficientNet-B2 (timm) + Grad-CAM", ["Ordinal regression on APTOS 2019", "Kappa 0.89 on APTOS; 0.71 on Indian IDRiD", "after fine-tuning (0.57 without)", "2-year progression risk: simulation"]),
        ("Kidney", "LightGBM + logistic regression, SHAP", ["NHANES 2017-18, 4,827 adults", "Low eGFR AUROC 0.85, albuminuria 0.76", "Modest gain over a simple baseline, stated openly", "5-year eGFR path: simulation"]),
    ]
    for i, (t, m, lines) in enumerate(cards):
        x, y = 70 + (i % 2) * 455, 168 + (i // 2) * 268
        p.rect(x, y, 435, 248, "#fff", BLUE, 16, 2)
        p.add(f'<rect x="{x}" y="{y}" width="8" height="248" rx="4" fill="{BLUE}"/>')
        p.text(x + 28, y + 40, t, 24, INK, 800)
        p.text(x + 28, y + 68, m, 15.5, BLUE, 600)
        for k, l in enumerate(lines):
            p.text(x + 28, y + 100 + k * 25, l, 14.5, MUTED)

    right = [
        (TEAL, "LANGUAGE AND VOICE AI", False, ["Sarvam AI, called from the server only (the key never reaches the browser)",
                                               "saaras:v4 speech-to-text  ·  sarvam-105b-conversations chat  ·  bulbul:v4-flash text-to-speech",
                                               "English, Hindi, Telugu, Kannada. Emergency and dose rules run in code, before and after the model"]),
        (AMBER, "FRAMEWORKS AND DELIVERY", False, ["FastAPI, Pydantic, WebSocket, FHIR R4, ReportLab PDFs   ·   React 18 + Vite",
                                                  "Live mode runs the GRU in pure NumPy, about 1 ms per reading, no GPU",
                                                  "pandas, scikit-learn, SHAP, simglucose   ·   Docker Compose, GitHub Actions CI   ·   trained on 3x RTX A5000"]),
        (AMBER, "HOSPITAL IT: TODAY AND ROADMAP", True, ["Today: REST API, live readings, FHIR Patient and Observation, Docker deploy",
                                                        "Roadmap, not built: consent records, access audit log, model-health page,",
                                                        "ABDM alignment, FHIR DiagnosticReport and Condition"]),
    ]
    for i, (col, hd, dash, lines) in enumerate(right):
        y = 168 + i * 180
        p.rect(1000, y, 850, 164, "#fff", col, 16, 1.8, dash=dash)
        p.add(f'<rect x="1000" y="{y}" width="8" height="164" rx="4" fill="{col}"/>')
        p.text(1030, y + 36, hd, 14, col, 800, extra='letter-spacing="1.4"')
        for k, l in enumerate(lines):
            p.text(1030, y + 70 + k * 30, l, 15, INK if k == 0 else MUTED, 600 if k == 0 else 400)

    p.rect(70, 718, 1780, 60, TINT[SLATE], "none", 12, 0, shadow=False)
    p.text(960, 754, "All metrics are out-of-sample. The links from glucose patterns to organ outcomes are simulated on a synthetic cohort and are not clinically validated.", 16, SLATE, 600, "middle")
    footer(p, "Kaya is decision support for clinicians, not a diagnostic device.", 836)
    p.save("architecture_detail.svg")


overview()
detail()
