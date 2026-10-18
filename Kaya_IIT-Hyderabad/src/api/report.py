"""PDF clinical summary for one patient (reportlab, no browser or image dependencies)."""
from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK, MUTED, LINE = colors.HexColor("#2a2742"), colors.HexColor("#77748f"), colors.HexColor("#dcd8ef")
VIOLET, MINT, PEACH, ROSE, SKY, BUTTER = (colors.HexColor(c) for c in ("#7160e6", "#d6f3e5", "#ffe2d2", "#ffd9e5", "#d8eaff", "#fff1bd"))
GRADES = ["No retinopathy", "Mild", "Moderate", "Severe", "Proliferative"]
T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _styles():
    b = getSampleStyleSheet()["Normal"]
    return {
        "h1": ParagraphStyle("h1", parent=b, fontName="Helvetica-Bold", fontSize=20, textColor=INK, leading=24),
        "h2": ParagraphStyle("h2", parent=b, fontName="Helvetica-Bold", fontSize=12.5, textColor=INK, spaceBefore=10, spaceAfter=4),
        "p": ParagraphStyle("p", parent=b, fontName="Helvetica", fontSize=9.2, textColor=INK, leading=12.5, alignment=TA_LEFT),
        "s": ParagraphStyle("s", parent=b, fontName="Helvetica", fontSize=8, textColor=MUTED, leading=10.5),
        "c": ParagraphStyle("c", parent=b, fontName="Helvetica", fontSize=8.6, textColor=INK, leading=11),
        "cb": ParagraphStyle("cb", parent=b, fontName="Helvetica-Bold", fontSize=8.6, textColor=INK, leading=11),
    }


def _pct(x, d=0):
    return f"{x * 100:.{d}f}%"


def _iso(t):
    return (T0 + timedelta(minutes=5 * int(t))).strftime("%a %d %b, %H:%M")


def _explain(sr, idx):
    g, meals = sr["glucose"], sr["meal_carbs"]
    if idx < 6:
        return ""
    slope = (g[idx] - g[idx - 6]) / 30
    meal = next(((meals[k], (idx - k) * 5) for k in range(idx, max(0, idx - 36) - 1, -1) if meals[k] > 0), None)
    trend = "steady" if abs(slope) < 0.4 else (f"rising {slope:.1f} mg/dL per min" if slope > 0 else f"falling {abs(slope):.1f} mg/dL per min")
    m = f", {meal[0]:.0f} g carbs eaten {meal[1]} min earlier" if meal else ", no recent meal logged"
    return f"Glucose {g[idx]:.0f} and {trend}{m}."


def _chart(a, width, height):
    sr, fc = a["series"], a["forecast"]
    end = fc["t"][-1]
    n_show = 3 * 288
    s0 = max(0, end - n_show)
    g = sr["glucose"][s0:end + 1]
    d = Drawing(width, height)
    pl, pr, pt, pb = 34, 40, 8, 18
    iw, ih = width - pl - pr, height - pt - pb
    ymin, ymax = 40, max(260, int(max(g) / 50 + 1) * 50)
    fut = 30
    x = lambda i: pl + i / (len(g) - 1 + fut) * iw
    y = lambda v: pb + (min(max(v, ymin), ymax) - ymin) / (ymax - ymin) * ih
    d.add(Rect(pl, y(70), iw, y(180) - y(70), fillColor=MINT, strokeColor=None))
    for v in (70, 180, 250):
        if v <= ymax:
            d.add(Line(pl, y(v), pl + iw, y(v), strokeColor=LINE, strokeWidth=0.5, strokeDashArray=[2, 3]))
            d.add(String(pl - 4, y(v) - 3, str(v), fontSize=7, fillColor=MUTED, textAnchor="end"))
    pts = []
    for i, v in enumerate(g):
        pts += [x(i), y(v)]
    d.add(PolyLine(pts, strokeColor=VIOLET, strokeWidth=1.1))
    now = g[-1]
    q = fc["q"][-1]
    fan_hi = [(x(len(g) - 1 + s), y(now + q[h][2])) for h, s in enumerate((6, 12, 24))]
    fan_lo = [(x(len(g) - 1 + s), y(now + q[h][0])) for h, s in enumerate((6, 12, 24))]
    poly = [x(len(g) - 1), y(now)] + [c for p in fan_hi for c in p] + [c for p in reversed(fan_lo) for c in p]
    d.add(Polygon(poly, fillColor=colors.Color(0.94, 0.51, 0.31, alpha=0.25), strokeColor=None))
    for h, s in enumerate((6, 12, 24)):
        d.add(Circle(x(len(g) - 1 + s), y(now + q[h][1]), 2.4, fillColor=colors.HexColor("#f0814f"), strokeColor=None))
    for k in range(0, len(g), 144):
        d.add(String(x(k), 4, (T0 + timedelta(minutes=5 * (s0 + k))).strftime("%a %d, %H:%M"), fontSize=6.5, fillColor=MUTED))
    d.add(String(pl + iw, pb + ih + 0, "forecast", fontSize=6.5, fillColor=colors.HexColor("#9c4a1e"), textAnchor="end"))
    return d


def _table(rows, widths, header=True, shade=None):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 5)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ece8ff"))]
    if shade:
        st += shade
    t.setStyle(TableStyle(st))
    return t


def build_report(a: dict, summary: dict, now: dict, scenarios: list[tuple[str, dict]]) -> bytes:
    S = _styles()
    pr, lab, m = a["profile"], a["profile"]["labs"], a["metrics"]
    kp, tl = a["kidney"]["projection"], a["liver"]["timeline"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"Kaya clinical summary, patient {pr['id']}", author="Kaya")
    W = A4[0] - 32 * mm
    P = lambda t, s="c": Paragraph(t, S[s])
    story = []

    head = Table([[Paragraph("Kaya clinical summary", S["h1"]),
                   Paragraph(f"Patient {pr['id']}<br/><font size=8 color='#77748f'>Generated {datetime.now().strftime('%d %b %Y %H:%M')}</font>", S["p"])]],
                 colWidths=[W * 0.62, W * 0.38])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("LINEBELOW", (0, 0), (-1, 0), 1.2, VIOLET)]))
    story += [head, Spacer(1, 3), P("Synthetic patient. Decision support for clinicians; not a diagnostic device and not clinically validated.", "s"), Spacer(1, 6)]

    meds = ("Metformin" if pr["metformin"] else "No metformin") + (", insulin or sulfonylurea (low-glucose risk)" if pr["on_insulin_or_su"] else "")
    prof = [[P("<b>Patient</b>"), P(f"{pr['age']:.0f} y, {'female' if pr['sex'] == 'F' else 'male'}; BMI {pr['bmi']}; waist {pr['waist_cm']:.0f} cm"),
             P("<b>Diabetes</b>"), P(f"{pr['duration_yrs']} years; HbA1c {pr['hba1c']}%; BP {pr['sbp']:.0f}/{pr['dbp']:.0f}")],
            [P("<b>Treatment</b>"), P(meds), P("<b>Genetics</b>"), P(f"PNPLA3 G alleles {pr['pnpla3_g_alleles']}; TCF7L2 T alleles {pr['tcf7l2_t_alleles']}")],
            [P("<b>Priority</b>"), P(f"<b>{summary['tier'].upper()}</b>"), P("<b>Why flagged</b>"), P("; ".join(summary["reasons"]) or "Stable, no flags")]]
    t = Table(prof, colWidths=[W * 0.12, W * 0.38, W * 0.13, W * 0.37])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6f3ff")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story += [t, Paragraph("Glucose now and the next 2 hours", S["h2"])]

    f = now["forecast"]
    fr = [[P("<b>Now</b>"), P("<b>In 30 min</b>"), P("<b>In 60 min</b>"), P("<b>In 120 min</b>"), P("<b>High within 2 h</b>"), P("<b>Low within 2 h</b>")],
          [P(f"<b>{now['glucose']:.0f}</b> mg/dL"), P(f"{f[0]['median']:.0f}  ({f[0]['lo']:.0f}-{f[0]['hi']:.0f})"),
           P(f"{f[1]['median']:.0f}  ({f[1]['lo']:.0f}-{f[1]['hi']:.0f})"), P(f"{f[2]['median']:.0f}  ({f[2]['lo']:.0f}-{f[2]['hi']:.0f})"),
           P(_pct(now["p_hyper_2h"])), P(_pct(now["p_hypo_2h"]))]]
    story += [_table(fr, [W / 6] * 6), Spacer(1, 4), _chart(a, W, 120),
              P("Last 3 days of CGM with the twin's forecast (median and 80% range) from the latest reading. Healthy range 70-180 mg/dL shaded.", "s"),
              Paragraph("14-day glucose profile", S["h2"])]
    mr = [[P("<b>Time in range</b>"), P("<b>Above 180</b>"), P("<b>Below 70</b>"), P("<b>Variability (CV)</b>"), P("<b>Mean glucose</b>"), P("<b>Est. HbA1c</b>")],
          [P(_pct(m["tir"])), P(_pct(m["tar"])), P(_pct(m["tbr"], 1)), P(f"{m['gv_cv']:.0f}%"), P(f"{m['mean']:.0f} mg/dL"), P(f"{m['gmi']:.1f}%")]]
    story += [_table(mr, [W / 6] * 6)]

    story.append(Paragraph("Organ risk", S["h2"]))
    org = [[P("<b>Organ</b>"), P("<b>Finding</b>"), P("<b>Evidence</b>")],
           [P("<b>Liver</b>"), P(f"Steatosis risk {_pct(tl['steatosis'][0])}, {_pct(tl['steatosis'][-1])} at 12 months at current habits.<br/>"
                                f"Advanced fibrosis {_pct(tl['adv_fibrosis'][0], 1)}, {_pct(tl['adv_fibrosis'][-1], 1)} at 12 months. "
                                f"Last FibroScan {a['profile']['clinic']['liver_stiffness_kpa']} kPa; FIB-4 {lab['fib4']}."),
            P("Baseline: model validated on real NHANES FibroScan data (AUROC 0.83). 12-month drift from glucose habits: simulation.")],
           [P("<b>Eyes</b>"), P(f"{GRADES[a['eye']['grade']]} (grade {a['eye']['grade']}). Two-year progression risk {_pct(a['eye']['progression_2y'])}."),
            P("Image grader validated on APTOS (kappa 0.89) and Indian IDRiD (0.71 after fine-tuning). Progression risk: simulation.")],
           [P("<b>Kidneys</b>"), P(f"eGFR {lab['egfr']:.0f}, UACR {lab['uacr_mg_g']:.0f} mg/g. Albuminuria risk {_pct(kp['albuminuria'][0])} now, "
                                  f"{_pct(kp['albuminuria'][-1])} at 12 months. eGFR about {kp['egfr'][-1]:.0f} in 5 years "
                                  f"({kp['slope_per_year']:.1f} per year); "
                                  + ("already below 60." if lab["egfr"] < 60 else f"reaches 60 in about {kp['years_to_egfr60']} years at this rate.")),
            P("Risk model validated on real NHANES data (AUROC 0.76 albuminuria, 0.85 reduced eGFR). eGFR path: simulation.")]]
    story.append(_table(org, [W * 0.1, W * 0.55, W * 0.35]))

    wi = [[P("<b>Scenario (simulation)</b>"), P("<b>Time in range</b>"), P("<b>Liver fat risk, 12 m</b>"), P("<b>eGFR in 5 y</b>"), P("<b>Eye progression, 2 y</b>")],
          [P("Current habits"), P(_pct(m["tir"])), P(_pct(tl["steatosis"][-1])), P(f"{kp['egfr'][-1]:.0f}"), P(_pct(a["eye"]["progression_2y"]))]]
    for name, r in scenarios:
        wi.append([P(name), P(_pct(r["metrics"]["after"]["tir"])), P(_pct(r["liver"]["after"]["steatosis"][-1])),
                   P(f"{r['kidney']['after']['egfr'][-1]:.0f}"), P(_pct(r["eye"]["after"]))])
    story.append(KeepTogether([Paragraph("What the twin suggests", S["h2"]), _table(wi, [W * 0.32, W * 0.15, W * 0.2, W * 0.14, W * 0.19]),
                               P("Effect sizes are literature-informed assumptions shown for transparency; this is a simulation to support a conversation, not a prediction of outcome.", "s")]))

    last_t = a["forecast"]["t"][-1]
    recent = [x for x in a["alerts"] if x["t"] >= last_t - 288][-6:]
    al = [[P("<b>When</b>"), P("<b>Alert</b>"), P("<b>Why</b>")]]
    for x in reversed(recent):
        al.append([P(_iso(x["t"])), P(("Low" if x["type"] == "hypo" else "High") + f" glucose expected ({_pct(x['prob'])})"), P(_explain(a["series"], x["t"]))])
    if len(al) == 1:
        al.append([P("-"), P("No alerts in the last 24 hours"), P("")])
    story.append(KeepTogether([Paragraph("Alerts, last 24 hours", S["h2"]), _table(al, [W * 0.22, W * 0.3, W * 0.48])]))
    story += [Spacer(1, 8), P("Kaya is an open-source research prototype built on open and synthetic data (CGMacros, NHANES, APTOS, IDRiD). "
                              "Forecasts and risks are estimates to support clinical judgement. Simulations are labelled and their assumptions are editable.", "s")]
    doc.build(story)
    return buf.getvalue()
