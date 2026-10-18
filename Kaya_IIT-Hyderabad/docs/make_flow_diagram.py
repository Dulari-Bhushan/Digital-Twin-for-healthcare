"""Draw the Kaya per-user flow diagram (docs/architecture_flow.svg). Render to PNG with a headless browser."""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).parent / "architecture_flow.svg"
W, H = 1920, 1270
INK, MUTED, LINE = "#14212b", "#5b6b77", "#9aa8b2"
TEAL, BLUE, AMBER, SLATE = "#0f766e", "#1d6fb8", "#b45309", "#475569"
TINT = {TEAL: "#e4f5f2", BLUE: "#e6eefb", AMBER: "#fdf1dc", SLATE: "#eef2f5"}

o: list[str] = []


def add(s: str) -> None:
    o.append(s)


def text(x, y, s, size=14, fill=INK, weight=400, anchor="start", extra=""):
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}" {extra}>{escape(s)}</text>')


def rect(x, y, w, h, fill="#fff", stroke=LINE, r=14, sw=1.6, dash=False, shadow=True):
    d = ' stroke-dasharray="7 5"' if dash else ""
    f = ' filter="url(#sh)"' if shadow else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{f}/>')


def arrow(d, color=LINE, sw=2.4, dash=False, marker=True, start=False):
    ds = ' stroke-dasharray="7 6"' if dash else ""
    m = f'marker-end="url(#a{color[1:]})"' if marker else ""
    ms = f' marker-start="url(#a{color[1:]})"' if start else ""
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{ds} {m}{ms}/>')


def pill(x, y, w, h, s, color, size=14):
    rect(x, y, w, h, fill="#fff", stroke=color, r=h / 2, sw=1.5, shadow=False)
    text(x + w / 2, y + h / 2 + size * 0.35, s, size, color, 600, "middle")


def num(cx, cy, n, color):
    add(f'<circle cx="{cx}" cy="{cy}" r="14" fill="{color}"/>')
    text(cx, cy + 5, str(n), 14, "#fff", 700, "middle")


# ---------------------------------------------------------------- defs
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif">')
add('<defs><filter id="sh" x="-5%" y="-5%" width="110%" height="120%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f2530" flood-opacity="0.10"/></filter>')
add('<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f7fafb"/><stop offset="1" stop-color="#eef3f5"/></linearGradient>')
add('<linearGradient id="core" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e9f7f4"/><stop offset="1" stop-color="#eaf1fc"/></linearGradient>')
for c in (LINE, TEAL, BLUE, AMBER, SLATE):
    add(f'<marker id="a{c[1:]}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
add('</defs>')
add(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')

# ---------------------------------------------------------------- title
text(70, 66, "Kaya: one twin per patient, three ways to use it", 38, INK, 800)
text(70, 100, "A multi-organ digital twin for Type 2 Diabetes. It shows what glucose does to the liver, eyes and kidneys, and lets you test a change before trying it on the real patient.", 17, MUTED)
pill(1490, 38, 360, 34, "Open + synthetic data only  ·  Decision support", TEAL, 14)

# ---------------------------------------------------------------- 1 inputs
text(70, 150, "1   WHAT GOES IN, PER PATIENT", 15, MUTED, 800, extra='letter-spacing="1.5"')
inputs = [
    ("⌚", "Wearable stream", "Glucose every 5 min, heart rate,", "sleep, steps, meals", BLUE),
    ("🧪", "EHR and labs", "HbA1c, eGFR, urine albumin,", "liver enzymes, genetics, history", BLUE),
    ("👁", "Retina scan", "Fundus photo from the", "clinic camera", BLUE),
    ("✍", "Patient quick log", "Medicines, a walk, how I feel", "in five seconds", TEAL),
    ("🎙", "Voice or chat", "A question in English, Hindi,", "Telugu or Kannada", TEAL),
]
CW, CG = 332, 30
for i, (ic, t, l1, l2, col) in enumerate(inputs):
    x = 70 + i * (CW + CG)
    rect(x, 168, CW, 108, "#fff", col, 14, 1.8)
    add(f'<circle cx="{x + 38}" cy="{168 + 54}" r="24" fill="{TINT[col]}"/>')
    text(x + 38, 168 + 63, ic, 24, INK, 400, "middle")
    text(x + 76, 168 + 40, t, 18.5, INK, 700)
    text(x + 76, 168 + 66, l1, 14, MUTED)
    text(x + 76, 168 + 86, l2, 14, MUTED)
    arrow(f"M{x + CW / 2},276 L{x + CW / 2},322", col, 2.6)

# ---------------------------------------------------------------- 2 engine
PX, PY, PW, PH = 70, 324, 1780, 446
rect(PX, PY, PW, PH, "url(#core)", TEAL, 20, 2.2)
text(PX + 28, PY + 36, "2   KAYA TWIN ENGINE", 15, TEAL, 800, extra='letter-spacing="1.5"')
text(PX + PW - 28, PY + 36, "runs on a plain laptop, no GPU needed for the demo", 14, MUTED, 400, "end", 'font-style="italic"')

# encoder
EX, EY, EW, EH = 98, 396, 292, 284
rect(EX, EY, EW, EH, "#fff", TEAL, 16, 2)
text(EX + EW / 2, EY + 36, "Patient state encoder", 20, INK, 800, "middle")
text(EX + EW / 2, EY + 60, "one fused twin per patient", 14, MUTED, 400, "middle")
for k, (hd, sb) in enumerate([("STATIC  ·  EHR", "labs, genetics, history"), ("DYNAMIC  ·  WEARABLES", "glucose, HR, sleep, steps, meals"), ("IMAGING  ·  RETINA", "cropped and normalised")]):
    yy = EY + 80 + k * 66
    rect(EX + 16, yy, EW - 32, 56, TINT[TEAL], "none", 10, 0, shadow=False)
    text(EX + 30, yy + 23, hd, 12.5, TEAL, 800, extra='letter-spacing="0.8"')
    text(EX + 30, yy + 43, sb, 13.5, INK)

# modules
mods = [
    (430, 396, "Glucose", "GRU + LightGBM ensemble", "30 / 60 / 120 min forecast, 80% band", "Catches 72% of lows, 45 min ahead"),
    (780, 396, "Liver", "Trained on 4,745 real NHANES adults", "Steatosis + fibrosis risk, AUROC 0.83", "Liver-fat state driven by recent glucose"),
    (430, 546, "Eye", "EfficientNet-B2 retinopathy grader", "Grad-CAM shows where it looked", "2-year progression risk"),
    (780, 546, "Kidney", "Albuminuria + low-eGFR risk", "AUROC 0.85 on real NHANES", "5-year eGFR path"),
]
for (x, y, t, a, b, c) in mods:
    rect(x, y, 330, 134, "#fff", BLUE, 16, 2)
    add(f'<rect x="{x}" y="{y}" width="8" height="134" rx="4" fill="{BLUE}"/>')
    text(x + 26, y + 34, t, 21, INK, 800)
    text(x + 26, y + 62, a, 14.5, BLUE, 600)
    text(x + 26, y + 87, b, 14, MUTED)
    text(x + 26, y + 109, c, 14, MUTED)
for y in (463, 613):
    arrow(f"M390,{y} L428,{y}", TEAL, 2.4)
arrow(f"M390,538 L410,538 L410,463", TEAL, 2.0, marker=False)
arrow(f"M410,538 L410,613", TEAL, 2.0, marker=False)

# what-if
WX = 1160
rect(WX, 396, 300, 284, "#fff", TEAL, 16, 2.4)
text(WX + 150, 432, "What-if engine", 20, INK, 800, "middle")
text(WX + 150, 456, "ask 'what happens if…'", 14, MUTED, 400, "middle")
for k, s in enumerate(["a meal", "a walk", "better sleep", "a medicine"]):
    pill(WX + 20 + (k % 2) * 136, 476 + (k // 2) * 40, 124, 30, s, TEAL, 13.5)
arrow(f"M{WX + 150},560 L{WX + 150},586", TEAL, 2.4)
rect(WX + 20, 592, 260, 74, TINT[TEAL], "none", 10, 0, shadow=False)
text(WX + 150, 618, "Twin re-runs. You see", 14, INK, 600, "middle")
text(WX + 150, 640, "before vs after: glucose curve", 14, MUTED, 400, "middle")
text(WX + 150, 658, "+ 1-year liver, eye, kidney risk", 14, MUTED, 400, "middle")
for y in (463, 613):
    arrow(f"M1110,{y} L1158,{y}", BLUE, 2.4)

# trust layer
TX = 1490
rect(TX, 396, 332, 284, "#fff", AMBER, 16, 2)
add(f'<rect x="{TX}" y="396" width="332" height="8" rx="4" fill="{AMBER}"/>')
text(TX + 166, 436, "Trust layer", 20, INK, 800, "middle")
trust = [("Explains itself", "SHAP drivers, Grad-CAM, alert reasons"), ("Honest about doubt", "conformal bands, calibrated odds"), ("Safe by design", "dose and emergency rules run in code"), ("Private", "open + synthetic data, key stays server-side")]
for k, (h, s) in enumerate(trust):
    yy = 462 + k * 52
    add(f'<circle cx="{TX + 28}" cy="{yy - 5}" r="5" fill="{AMBER}"/>')
    text(TX + 44, yy, h, 15, INK, 700)
    text(TX + 44, yy + 20, s, 13, MUTED)
arrow("M1460,538 L1488,538", AMBER, 2.4)

# serving strip
text(PX + 28, 730, "SERVED BY", 12.5, MUTED, 800, extra='letter-spacing="1.2"')
for (px, pw, s) in [(200, 150, "FastAPI REST"), (364, 292, "Live mode: numpy GRU, ~1 ms"), (670, 262, "WebSocket wearable feed"), (946, 326, "Sarvam AI voice (server-side)"), (1286, 276, "FHIR R4 + PDF summaries")]:
    pill(px, 713, pw, 34, s, SLATE, 13.5)

# ---------------------------------------------------------------- 3 lanes
text(70, 806, "3   THE FLOW, USER BY USER", 15, MUTED, 800, extra='letter-spacing="1.5"')
add(f'<text x="1850" y="806" font-size="13" fill="{MUTED}" text-anchor="end"><tspan fill="{AMBER}" font-weight="800">- - -</tspan> dashed = on the roadmap, not claimed as built</text>')

lanes = [
    (TEAL, "PATIENT", "plain language, on a phone", [
        ("Open Today", "One next action and why:", "walk, evening dose, sugar check", False),
        ("Quick log", "Medicines, a walk, how I feel,", "done in five seconds", False),
        ("See my body", "Time in range, and how habits", "touch liver, eyes and kidneys", False),
        ("Try a change", "What if I walk tonight?", "The twin shows the new curve", False),
        ("Ask in my language", "Voice or text, read aloud.", "Emergency words say call 108", False),
    ]),
    (BLUE, "DOCTOR", "triage, understand, decide", [
        ("Triage list", "Patients sorted by risk,", "with the reason for each", False),
        ("Open full record", "Glucose, organs, labs, alerts,", "plus the adherence diary", False),
        ("What changed?", "Since last visit: labs, eyes,", "medicines, last 7 days", False),
        ("What-if studio", "Test a change on the twin", "before the real patient", False),
        ("Decide and hand off", "One-click PDF summary and", "reports with trends", False),
    ]),
    (AMBER, "HOSPITAL IT", "plug in and operate", [
        ("Send readings", "POST /api/live or WebSocket", "from any CGM or wearable", False),
        ("Read FHIR R4", "Patient and Observation", "endpoints available today", False),
        ("Deploy", "Docker Compose, clean clone,", "CI tests on every push", False),
        ("Govern", "Consent records, audit log,", "model-health page", True),
        ("Connect to ABDM", "Fuller FHIR coverage", "(DiagnosticReport, Condition)", True),
    ]),
]
LY0, LH, LG = 820, 106, 30
SX0, SW, SG = 310, 292, 20
for li, (col, name, sub, steps) in enumerate(lanes):
    y = LY0 + li * (LH + LG)
    rect(70, y, 220, LH, col, col, 16, 0)
    text(180, y + 46, name, 23, "#fff", 800, "middle", 'letter-spacing="1.5"')
    text(180, y + 72, sub, 13, "#fff", 400, "middle", 'opacity="0.92"')
    for si, (t, l1, l2, plan) in enumerate(steps):
        x = SX0 + si * (SW + SG)
        rect(x, y, SW, LH, "#fff", col, 14, 1.8, dash=plan)
        add(f'<rect x="{x + 1}" y="{y + 1}" width="{SW - 2}" height="{LH - 2}" rx="13" fill="{TINT[col]}" opacity="{0.35 if plan else 0.55}"/>')
        num(x + 28, y + 30, si + 1, col if not plan else "#9aa8b2")
        text(x + 52, y + 36, t, 17.5, INK if not plan else MUTED, 700)
        text(x + 20, y + 66, l1, 14, MUTED)
        text(x + 20, y + 86, l2, 14, MUTED)
        if si < 4:
            arrow(f"M{x + SW + 3},{y + LH / 2} L{x + SW + SG - 3},{y + LH / 2}", col, 2.2)
    # bus branch into the lane
    arrow(f"M40,{y + LH / 2} L68,{y + LH / 2}", SLATE, 2.4)

# left bus from engine
arrow(f"M70,730 L40,730 L40,{LY0 + LH / 2}", SLATE, 2.4, marker=False)
arrow(f"M40,{LY0 + LH / 2} L40,{LY0 + 2 * (LH + LG) + LH / 2}", SLATE, 2.4, marker=False)
add(f'<text transform="translate(26,1010) rotate(-90)" font-size="12" fill="{SLATE}" font-weight="700" text-anchor="middle" letter-spacing="1.2">API  ·  WEBSOCKET  ·  FHIR</text>')

# cross-lane links (same data, two audiences)
for col_i, label in ((1, "log becomes the doctor's adherence diary"), (3, "same twin, same what-if engine")):
    cx = SX0 + col_i * (SW + SG) + SW / 2
    y1 = LY0 + LH
    arrow(f"M{cx},{y1 + 2} L{cx},{y1 + LG - 2}", SLATE, 2.2, start=True)
    text(cx + 14, y1 + 20, label, 12.5, SLATE, 600)

# feedback loop (patient's logs and questions go back into the twin)
py = LY0 + LH / 2
arrow(f"M{SX0 + 5 * SW + 4 * SG + 2},{py} L1888,{py} L1888,222 L1854,222", TEAL, 2.4, dash=True)
add(f'<text transform="translate(1906,520) rotate(-90)" font-size="12.5" fill="{TEAL}" font-weight="700" text-anchor="middle" letter-spacing="1">LOOP: LOGS AND QUESTIONS FEED THE TWIN</text>')

# footer
add(f'<line x1="70" x2="1850" y1="1236" y2="1236" stroke="{LINE}" stroke-width="1"/>')
text(70, 1258, "Kaya is decision support for clinicians, not a diagnostic device. All patients are synthetic; metrics are out-of-sample.", 13.5, MUTED)
text(1850, 1258, "Team Kaya · IIT Hyderabad · Digital Twin Challenge, Phase 1", 13.5, MUTED, 600, "end")

add("</svg>")
OUT.write_text("\n".join(o), encoding="utf-8")
print("wrote", OUT)
