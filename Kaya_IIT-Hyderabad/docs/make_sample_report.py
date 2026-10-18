"""Builds a realistic, fictional lab report for the demo patient Rajesh Sharma (ID 1688) to upload in the patient app.

Run:  python docs/make_sample_report.py      ->  docs/sample/Rajesh_Sharma_lab_report.pdf

The lab, doctor and numbers are invented. The values continue Rajesh's story in the demo data (HbA1c around 9, eGFR just
above 60, albuminuria, mildly raised ALT) and the report is dated between his October 2025 and January 2026 panels.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parent / "sample" / "Rajesh_Sharma_lab_report.pdf"
TEAL, DEEP, AMBER, INK, MUTED, LINE = (colors.HexColor(c) for c in ("#0F6E68", "#0B4F4B", "#E9A23B", "#1c3432", "#667b78", "#cfdcda"))
RED = colors.HexColor("#b3261e")

base = getSampleStyleSheet()["Normal"]
S = {
    "lab": ParagraphStyle("lab", parent=base, fontName="Helvetica-Bold", fontSize=19, textColor=colors.white, leading=22),
    "sub": ParagraphStyle("sub", parent=base, fontName="Helvetica", fontSize=8.5, textColor=colors.HexColor("#d7ecea"), leading=11),
    "c": ParagraphStyle("c", parent=base, fontName="Helvetica", fontSize=9, textColor=INK, leading=12),
    "cb": ParagraphStyle("cb", parent=base, fontName="Helvetica-Bold", fontSize=9, textColor=INK, leading=12),
    "red": ParagraphStyle("red", parent=base, fontName="Helvetica-Bold", fontSize=9, textColor=RED, leading=12),
    "h": ParagraphStyle("h", parent=base, fontName="Helvetica-Bold", fontSize=10.5, textColor=DEEP, spaceBefore=7, spaceAfter=2),
    "small": ParagraphStyle("small", parent=base, fontName="Helvetica", fontSize=7.8, textColor=MUTED, leading=10.5),
    "end": ParagraphStyle("end", parent=base, fontName="Helvetica-Bold", fontSize=9, textColor=MUTED, alignment=TA_CENTER, spaceBefore=10),
    "th": ParagraphStyle("th", parent=base, fontName="Helvetica-Bold", fontSize=8.5, textColor=DEEP, leading=11, alignment=TA_LEFT),
}

# (test, result, unit, biological reference interval, method, flag)
SECTIONS = [
    ("GLYCAEMIC PROFILE", [
        ("Glycosylated Haemoglobin (HbA1c)", "9.0", "%", "Non-diabetic: below 5.7; Diabetic target: below 7.0", "HPLC", "H"),
        ("Estimated Average Glucose (eAG)", "212", "mg/dL", "-", "Calculated", "H"),
        ("Fasting Blood Sugar (FBS)", "186", "mg/dL", "70 - 100", "Hexokinase", "H"),
    ]),
    ("KIDNEY FUNCTION TEST", [
        ("Serum Creatinine", "1.35", "mg/dL", "0.70 - 1.30", "Enzymatic", "H"),
        ("eGFR (CKD-EPI 2021)", "63", "mL/min/1.73 m2", "90 or more", "Calculated", "L"),
        ("Urine Albumin / Creatinine Ratio (UACR)", "226", "mg/g", "Below 30", "Immunoturbidimetry", "H"),
    ]),
    ("LIVER FUNCTION TEST", [
        ("SGPT (ALT)", "27", "U/L", "Up to 40", "IFCC", ""),
        ("SGOT (AST)", "26", "U/L", "Up to 40", "IFCC", ""),
    ]),
    ("LIPID PROFILE", [
        ("Total Cholesterol", "138", "mg/dL", "Below 200", "CHOD-POD", ""),
        ("Triglycerides", "134", "mg/dL", "Below 150", "GPO-POD", ""),
        ("HDL Cholesterol", "44", "mg/dL", "Above 40", "Direct", ""),
        ("LDL Cholesterol", "62", "mg/dL", "Below 100", "Calculated", ""),
    ]),
    ("COMPLETE BLOOD COUNT (EXTRACT)", [
        ("Platelet Count", "1.63", "Lakh/cumm", "1.50 - 4.10", "Impedance", ""),
    ]),
]


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=14 * mm, title="Laboratory Report - Rajesh Sharma",
                            author="Doon Valley Diagnostics (fictional)")
    head = Table([[Paragraph("DOON VALLEY DIAGNOSTICS", S["lab"])], [Paragraph("Pathology and Clinical Laboratory &nbsp;|&nbsp; 14 Rajpur Road, Dehradun, Uttarakhand 248001 &nbsp;|&nbsp; Tel 0135-000 0000", S["sub"])]], colWidths=[182 * mm])
    head.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TEAL), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (0, 0), 9), ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                              ("LINEBELOW", (0, -1), (-1, -1), 3, AMBER)]))

    def kv(a, b, c, d):
        return [Paragraph(f"<b>{a}</b>", S["c"]), Paragraph(b, S["c"]), Paragraph(f"<b>{c}</b>", S["c"]), Paragraph(d, S["c"])]

    pt = Table([
        kv("Patient Name", "Mr. RAJESH SHARMA", "Lab No.", "DVD-26-004127"),
        kv("Age / Sex", "51 Years / Male", "Sample Collected", "10/01/2026 07:55"),
        kv("Patient ID", "1688", "Sample Received", "10/01/2026 08:20"),
        kv("Referred By", "Dr. Anita Kapoor (Diabetologist)", "Report Date", "10/01/2026 15:40"),
    ], colWidths=[28 * mm, 66 * mm, 32 * mm, 56 * mm])
    pt.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f8f7")),
                            ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    el = [head, Spacer(1, 6), pt, Spacer(1, 6),
          Paragraph("<b>DEPARTMENT OF BIOCHEMISTRY</b>", ParagraphStyle("d", parent=base, fontName="Helvetica-Bold", fontSize=11, textColor=INK, alignment=TA_CENTER, spaceAfter=2))]
    for k, (title, rows) in enumerate(SECTIONS):
        el.append(Paragraph(title, S["h"]))
        data = [[Paragraph(h, S["th"]) for h in ("TEST NAME", "RESULT", "UNIT", "BIOLOGICAL REFERENCE INTERVAL", "METHOD")]] if k == 0 else []
        for name, val, unit, ref, method, fl in rows:
            st = S["red"] if fl else S["cb"]
            data.append([Paragraph(name, S["c"]), Paragraph(f"{val} {fl}".strip(), st), Paragraph(unit, S["c"]), Paragraph(ref, S["c"]), Paragraph(method, S["small"])])
        t = Table(data, colWidths=[58 * mm, 22 * mm, 28 * mm, 46 * mm, 28 * mm])
        sty = [("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6)]
        if k == 0:
            sty.append(("LINEBELOW", (0, 0), (-1, 0), 0.8, TEAL))
        t.setStyle(TableStyle(sty))
        el.append(t)
    el += [Spacer(1, 6),
           Paragraph("<b>Clinical notes:</b> HbA1c reflects average glucose over the previous 2 to 3 months. eGFR is calculated with the CKD-EPI 2021 equation. A raised urine albumin / creatinine ratio "
                     "should be confirmed on two of three samples over 3 to 6 months. H = above reference interval, L = below reference interval.", S["small"]),
           Paragraph("*** End of Report ***", S["end"]), Spacer(1, 10)]
    sig = Table([[Paragraph("<b>Dr. Shalini Arora</b><br/>MD (Pathology)<br/>Consultant Pathologist", S["small"]), Paragraph("Results relate only to the sample tested. Please correlate clinically.", S["small"])]], colWidths=[70 * mm, 112 * mm])
    sig.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.5, LINE), ("TOPPADDING", (0, 0), (-1, -1), 6), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    el += [sig, Spacer(1, 8), Paragraph("Fictional laboratory and fictional patient, created only to demonstrate the Kaya software. This is not a medical document.", S["small"])]
    doc.build(el)
    print("saved", OUT)


if __name__ == "__main__":
    build()
