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
    p.pill(1400, 40, 350, 34, "Open + synthetic data only  ·  Decision support", TEAL, 14)
    # Kaya logo mark: amber and teal circles with the glucose wave
    p.add('<clipPath id="lmk"><circle cx="1809" cy="57" r="25"/></clipPath>')
    p.add('<circle cx="1830" cy="57" r="25" fill="#E8A03C"/><circle cx="1809" cy="57" r="25" fill="#0F7068"/>')
    p.add('<circle cx="1830" cy="57" r="25" fill="#1C4E48" clip-path="url(#lmk)"/>')
    p.add('<path d="M1796,63 C1803,55 1810,60 1817,62 C1824,64 1829,52 1841,53" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round"/>')


def footer(p, left, y):
    p.add(f'<line x1="70" x2="1850" y1="{y - 24}" y2="{y - 24}" stroke="{LINE}" stroke-width="1"/>')
    p.text(70, y, left, 14, MUTED)
    p.text(1850, y, "Team Kaya · IIT Hyderabad · Digital Twin Challenge, Phase 1", 14, MUTED, 600, "end")


# ===================================================================== page 1
def overview():
    p = Page(1920, 1080)
    header(p, "Kaya: one twin per patient", "It shows what glucose does to the liver, eyes and kidneys, and lets you test a change before trying it on the real patient.")

    p.label(70, 150, "1   WHAT GOES IN")
    inputs = [("⌚", "Wearable stream", BLUE), ("🧪", "EHR and labs", BLUE), ("👁️", "Retina scan", BLUE),
              ("✍", "Patient quick log", TEAL), ("🎙️", "Voice or chat", TEAL)]
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
        (AMBER, "ADMIN", "run it safely", [("Service health", "uptime, requests, latency"), ("Models and data", "what is running, validated how"), ("Audit trail", "who did what, safety stops"), ("Self-test", "checks, hardening list, FHIR API")]),
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
    p.arrow(f"M70,500 L42,500 L42,{LY + 2 * (LH + LG) + LH / 2}", SLATE, 2.4, marker=False)
    # cross links
    for li2, si, lab in ((0, 1, "the log becomes the doctor's adherence diary"), (0, 2, "same twin, same what-if engine"), (1, 2, "every action is written to the audit trail")):
        cx = 314 + si * 390 + 183
        y1 = LY + li2 * (LH + LG) + LH
        p.arrow(f"M{cx},{y1 + 3} L{cx},{y1 + LG - 3}", SLATE, 2.2, start=True)
        p.text(cx + 14, y1 + 26, lab, 13.5, SLATE, 600)
    # loop
    py = LY + LH / 2
    p.arrow(f"M{314 + 3 * 390 + 366},{py} L1888,{py} L1888,201 L1854,201", TEAL, 2.4, dash=True)

    footer(p, "Kaya is decision support for clinicians, not a diagnostic device. All patients are synthetic.     Models, metrics and frameworks are on the next page.", 1056)
    p.save("architecture_overview.svg")


# ===================================================================== page 2
LIVER = "M2,10 C2,4 12,2 22,5 C30,7 36,10 38,14 C30,22 18,24 10,20 C5,18 2,14 2,10 Z"


def tile(p, x, y, w, h, icon, title, sub, col, liver=False):
    p.rect(x, y, w, h, "#fff", col, 16, 1.8)
    cx, cy = x + 52, y + h / 2
    p.add(f'<circle cx="{cx}" cy="{cy}" r="32" fill="{TINT[col]}"/>')
    if liver:
        p.add(f'<g transform="translate({cx - 21},{cy - 12}) scale(1.05)"><path d="{LIVER}" fill="#b4513a"/>'
              f'<path d="M14,8 C20,10 26,12 33,14" stroke="#8a3a29" stroke-width="1.6" fill="none"/></g>')
    else:
        p.text(cx, cy + 12, icon, 34, INK, 400, "middle")
    p.text(x + 100, y + h / 2 - 4, title, 20, INK, 800)
    p.text(x + 100, y + h / 2 + 22, sub, 15, MUTED)


def detail():
    p = Page(1920, 1130)
    header(p, "How Kaya works, at a glance", "Learn from open data, build four AI models, make them trustworthy, then put them in people's hands.")

    cols = [
        (BLUE, "1   LEARNED FROM", [
            ("📈", "Glucose recordings", "real people wearing sensors  ¹", False),
            ("🩺", "Health survey data", "real labs and liver scans  ²", False),
            ("👁️", "Retina photos", "including Indian patients  ³", False),
            ("🧬", "Synthetic patients", "2,000 made-up, privacy-safe  ⁴", False),
        ]),
        (TEAL, "2   FOUR AI MODELS", [
            ("🩸", "Glucose", "predicts the next 2 hours  ⁵", False),
            ("", "Liver", "fat and scarring risk  ⁶", True),
            ("👁️", "Eye", "grades diabetic eye damage  ⁷", False),
            ("🫘", "Kidney", "risk and 5-year decline  ⁶", False),
        ]),
        (AMBER, "3   MADE TRUSTWORTHY", [
            ("🎯", "Says how sure it is", "honest uncertainty bands", False),
            ("🔍", "Shows why", "reasons and heat-maps", False),
            ("🛡️", "Safety rules", "emergency and dose checks  ⁸", False),
            ("🔒", "Private by design", "no real patient data", False),
        ]),
        (SLATE, "4   WHAT PEOPLE GET", [
            ("🧑‍⚕️", "Doctor dashboard", "who needs help, and why", False),
            ("📱", "Patient app", "plain words, 4 languages, voice  ⁸", False),
            ("🖥️", "Admin page", "health, models, audit trail", False),
            ("🔄", "What-if testing", "try a change on the twin first", False),
        ]),
    ]
    CWID, CGAP, TY, TH, TG = 424, 28, 196, 112, 14
    for ci, (col, head, tiles) in enumerate(cols):
        x = 70 + ci * (CWID + CGAP)
        p.rect(x, 140, CWID, 40, col, col, 12, 0, shadow=False)
        p.text(x + 20, 167, head, 16, "#fff", 800, extra='letter-spacing="1.4"')
        for ti, (ic, t, sub, liver) in enumerate(tiles):
            tile(p, x, TY + ti * (TH + TG), CWID, TH, ic, t, sub, col, liver)
        if ci < 3:
            ax = x + CWID + CGAP / 2
            p.add(f'<circle cx="{ax}" cy="{TY + 2 * TH + TG}" r="12" fill="#fff" stroke="{LINE}" stroke-width="1.4"/>')
            p.arrow(f"M{ax - 4},{TY + 2 * TH + TG} L{ax + 4},{TY + 2 * TH + TG}", SLATE, 2.4)

    # built with
    by = TY + 4 * TH + 3 * TG + 30
    p.label(70, by, "BUILT WITH")
    chips = [("🔥", "PyTorch"), ("🌳", "LightGBM"), ("🖼️", "EfficientNet"), ("🔦", "SHAP, Grad-CAM"),
             ("🗣️", "Sarvam AI"), ("⚡", "FastAPI"), ("⚛️", "React"), ("🐳", "Docker")]
    for i, (ic, t) in enumerate(chips):
        x = 70 + i * 225
        p.rect(x, by + 14, 205, 54, "#fff", SLATE, 27, 1.5)
        p.text(x + 30, by + 50, ic, 24, INK, 400, "middle")
        p.text(x + 54, by + 47, t, 16, INK, 700)

    # footnotes: two aligned columns, number badge + bold name + wrapped text
    fy = by + 96
    left = [
        (1, BLUE, "CGMacros (PhysioNet)", ["Real glucose, meals and Fitbit data from 34 people."]),
        (2, BLUE, "NHANES 2017-18", ["4,745 adults with FibroScan liver labels; 4,827 for kidney."]),
        (3, BLUE, "APTOS 2019 + IDRiD", ["Retina photographs: APTOS for training, Indian IDRiD for testing."]),
        (4, BLUE, "Synthetic cohort", ["Our generator + simglucose: 2,000 patients, 14 days each."]),
        (5, TEAL, "Glucose model", ["GRU (PyTorch) + LightGBM ensemble, conformal 80% bands, isotonic-calibrated alerts.",
                                    "RMSE 12.6 / 21.1 / 28.2 mg/dL at 30 / 60 / 120 min; catches 72% of lows, 45 min ahead."]),
    ]
    right = [
        (6, TEAL, "Liver and kidney models", ["LightGBM + logistic regression, explained with SHAP.",
                                              "AUROC: liver 0.83 (standard FIB-4: 0.63), kidney 0.85. 1.0 is perfect, 0.5 a coin flip."]),
        (7, TEAL, "Eye model", ["EfficientNet-B2 (timm), grades 0-4, Grad-CAM heat-maps. Kappa 0.89 on APTOS, 0.71 on IDRiD.",
                                "Eye progression and the 5-year kidney path are simulations."]),
        (8, AMBER, "Voice and documents (Sarvam AI, server-side only)", ["saaras:v4 speech-to-text, sarvam-105b-conversations chat, bulbul:v4-flash text-to-speech.",
                                                                    "Sarvam Document AI reads uploaded reports. Emergency and dose rules run in code, before the model."]),
    ]
    PH = 368
    p.rect(70, fy, 1780, PH, "#fff", LINE, 18, 1.4)
    p.text(98, fy + 36, "FOOTNOTES", 14.5, SLATE, 800, extra='letter-spacing="1.6"')
    p.text(1822, fy + 36, "the detail behind each icon above", 14, MUTED, 400, "end", 'font-style="italic"')

    def column(x0, items):
        y = fy + 74
        for n, col, name, lines in items:
            p.add(f'<circle cx="{x0 + 11}" cy="{y - 5}" r="11" fill="{col}"/>')
            p.text(x0 + 11, y - 0.5, str(n), 12.5, "#fff", 800, "middle")
            p.text(x0 + 32, y, name, 15, INK, 700)
            for k, l in enumerate(lines):
                p.text(x0 + 32, y + 22 + k * 19, l, 13.5, MUTED)
            y += 22 + len(lines) * 19 + 16

    column(98, left)
    p.add(f'<line x1="960" x2="960" y1="{fy + 56}" y2="{fy + PH - 22}" stroke="{LINE}" stroke-width="1"/>')
    column(990, right)
    ny = fy + 74 + 3 * (22 + 2 * 19 + 16) + 4
    p.add(f'<circle cx="1001" cy="{ny - 5}" r="11" fill="{SLATE}"/>')
    p.text(1001, ny + 0.5, "i", 14, "#fff", 800, "middle")
    p.text(1022, ny, "Good to know", 15, INK, 700)
    for k, l in enumerate(["Live mode runs the GRU in pure NumPy: about 1 ms per reading, no GPU.",
                           "Not built yet: consent records, a persistent audit log, ABDM. Not clinically validated."]):
        p.text(1022, ny + 22 + k * 19, l, 13.5, MUTED)

    end = fy + PH + 56
    footer(p, "Kaya is decision support for clinicians, not a diagnostic device.", end)
    p.h = end + 24
    p.o[0] = p.o[0].replace('viewBox="0 0 1920 1130"', f'viewBox="0 0 1920 {p.h}"').replace('height="1130"', f'height="{p.h}"')
    p.o = [o.replace('height="1130"', f'height="{p.h}"') for o in p.o]
    p.save("architecture_detail.svg")
    print("height", p.h)


overview()
detail()
