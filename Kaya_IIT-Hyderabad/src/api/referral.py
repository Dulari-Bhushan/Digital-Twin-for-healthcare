"""Referral letter (紹介状 / 診療情報提供書) for one patient, in Japanese or English, as a PDF.

In Japan a patient is usually seen by a small clinic first and goes to a hospital specialist only with a letter from the clinic; without
one, large hospitals charge extra. The tracker's "Refer" button tells the patient; this makes the letter the doctor would hand over: who the
patient is, why they are referred, the key results and the current medicines, taken from the same data the doctor sees.

Everything in the letter is synthetic and says so. The doctor must read and sign it; Kaya only prepares it. Japanese text uses the
standard CID font HeiseiKakuGo-W5 (no font file is needed: PDF viewers supply a Japanese font).
"""
from __future__ import annotations

import io
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK, MUTED, LINE, TINT = colors.HexColor("#1d2b29"), colors.HexColor("#56635f"), colors.HexColor("#c9d6d3"), colors.HexColor("#eaf4f0")
DESTINATIONS = ("eye", "kidney", "hospital")
DEST = {  # destination: (English, Japanese)
    "eye": ("Ophthalmology", "眼科"),
    "kidney": ("Nephrology", "腎臓内科"),
    "hospital": ("Hospital, diabetes and endocrinology", "病院 糖尿病内科"),
}
GRADE_EN = ["No retinopathy", "Mild non-proliferative", "Moderate non-proliferative", "Severe non-proliferative", "Proliferative"]
GRADE_JA = ["網膜症なし", "軽症非増殖糖尿病網膜症", "中等症非増殖糖尿病網膜症", "重症非増殖糖尿病網膜症", "増殖糖尿病網膜症"]       # the international severity scale as Japanese ophthalmology writes it
CLINIC_JA = "Kayaデモクリニック（架空）"
DOCTOR_JA = {"Dr. Keiko Mori": "森 恵子", "Dr. Anita Kapoor": "アニタ・カプール"}
MED_JA = {"Metformin": "メトホルミン", "Insulin glargine": "インスリン グラルギン", "Glimepiride": "グリメピリド", "Telmisartan": "テルミサルタン",
          "Dapagliflozin": "ダパグリフロジン", "Atorvastatin": "アトルバスタチン", "Sitagliptin": "シタグリプチン", "Empagliflozin": "エンパグリフロジン",
          "Liraglutide": "リラグルチド", "Pioglitazone": "ピオグリタゾン", "Gliclazide": "グリクラジド", "Glipizide": "グリピジド",
          "Vildagliptin": "ビルダグリプチン", "Linagliptin": "リナグリプチン", "Semaglutide (weekly)": "セマグルチド（週1回）"}
DOSE_JA = {"500 mg, one tablet twice a day with meals": "500 mg 1回1錠 1日2回 食事とともに", "16 units at bedtime": "16単位 就寝前",
           "2 mg once a day before breakfast": "2 mg 1日1回 朝食前", "40 mg once a day": "40 mg 1日1回", "10 mg once a day in the morning": "10 mg 1日1回 朝",
           "10 mg at night": "10 mg 就寝前"}


def clean(s: str, n: int = 300) -> str:
    return re.sub(r"[\x00-\x08\x0b-\x1f<>&]", "", s or "").strip()[:n]


def _reiwa(d: datetime) -> str:
    return f"令和{d.year - 2018}年（{d.year}年）{d.month}月{d.day}日" if d.year >= 2019 else f"{d.year}年{d.month}月{d.day}日"


def _jdate(iso: str) -> str:
    """2024-11-10 as 2024年11月10日."""
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d")
        return f"{d.year}年{d.month}月{d.day}日"
    except ValueError:
        return iso


def _months(days: int) -> int:
    return max(1, round(days / 30.4))


def _fonts(ja: bool) -> tuple[str, str]:
    if ja:
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
        return "HeiseiKakuGo-W5", "HeiseiKakuGo-W5"
    return "Helvetica", "Helvetica-Bold"


def build_referral(a: dict, meds: list[dict], eye: dict | None, screening: dict, dest: str, lang: str, note: str, today: datetime, clinician: str,
                   clinic: str = "Kaya Demo Clinic (synthetic)") -> bytes:
    """a: the patient's artifact (profile, metrics). meds: the current medicine list. eye: the latest retina report of the record, if any.
    screening: screening.status(...) for this patient."""
    ja = lang == "ja"
    if ja:
        clinician = DOCTOR_JA.get(clinician, clinician)
        clinic = CLINIC_JA if clinic == "Kaya Demo Clinic (synthetic)" else clinic
    dest = dest if dest in DESTINATIONS else "hospital"
    reg, bold = _fonts(ja)
    pr, m = a["profile"], a["metrics"]
    lab, cl = pr["labs"], pr["clinic"]
    note = clean(note)
    base = getSampleStyleSheet()["Normal"]
    st = {
        "title": ParagraphStyle("t", parent=base, fontName=bold, fontSize=16, leading=21, textColor=INK),
        "h": ParagraphStyle("h", parent=base, fontName=bold, fontSize=10, leading=13, textColor=INK, spaceBefore=6, spaceAfter=2),
        "p": ParagraphStyle("p", parent=base, fontName=reg, fontSize=9.4, leading=14 if ja else 12.5, textColor=INK, alignment=TA_LEFT),
        "s": ParagraphStyle("s", parent=base, fontName=reg, fontSize=8, leading=11.5 if ja else 10.5, textColor=MUTED),
        "r": ParagraphStyle("r", parent=base, fontName=reg, fontSize=10, leading=14, textColor=INK, alignment=TA_RIGHT),
        "c": ParagraphStyle("c", parent=base, fontName=reg, fontSize=9, leading=12.5 if ja else 11.5, textColor=INK),
        "cb": ParagraphStyle("cb", parent=base, fontName=bold, fontSize=9, leading=12.5 if ja else 11.5, textColor=INK),
    }
    for style in st.values():
        style.wordWrap = "CJK" if ja else None
    P = lambda text, k="p": Paragraph(text, st[k])

    name_en, name_ja = pr.get("name") or f"Patient {pr['id']}", pr.get("name_ja")
    sex = ("男性" if pr["sex"] == "M" else "女性") if ja else ("male" if pr["sex"] == "M" else "female")
    age = round(pr["age"])
    grade = eye["grade"] if eye and "grade" in eye else None
    eye_tracker = next((t for t in screening["tests"] if t["key"] == "eye"), None)
    last_eye_months = _months(eye_tracker["days_since"]) if eye_tracker else None
    egfr, uacr = lab["egfr"], lab["uacr_mg_g"]
    albu = "A3" if uacr >= 300 else "A2" if uacr >= 30 else "A1"
    albu_ja = {"A1": "正常アルブミン尿（A1）", "A2": "微量アルブミン尿（A2）", "A3": "顕性アルブミン尿（A3）"}[albu]
    albu_en = {"A1": "normal albuminuria (A1)", "A2": "moderately increased albuminuria (A2)", "A3": "severely increased albuminuria (A3)"}[albu]
    last_eye = eye["date"] if eye else None

    # ---- purpose, per destination
    if ja:
        purpose = {
            "eye": f"糖尿病網膜症の評価と管理をお願いいたします。" + (f"最終の眼科検査から約{last_eye_months}か月が経過しており、" if last_eye_months and last_eye_months >= 12 else "")
                   + (f"直近の眼底写真（{_jdate(last_eye)}）では{GRADE_JA[grade]}でした。" if grade is not None else "眼底検査の記録がありません。"),
            "kidney": f"尿アルブミンおよび腎機能の精査と管理をお願いいたします。尿アルブミン/クレアチニン比 {uacr:.0f} mg/gCr、eGFR {egfr:.0f} mL/min/1.73m²です。",
            "hospital": "糖尿病の合併症評価と今後の治療方針について、ご高診をお願いいたします。",
        }[dest]
    else:
        purpose = {
            "eye": "Please assess and manage diabetic retinopathy. " + (f"The last eye examination was about {last_eye_months} months ago, " if last_eye_months and last_eye_months >= 12 else "")
                   + (f"and the most recent retinal photograph ({last_eye}) showed {GRADE_EN[grade].lower()} retinopathy." if grade is not None else "no retinal examination is on record."),
            "kidney": f"Please investigate and manage the albuminuria and kidney function: urine albumin/creatinine ratio {uacr:.0f} mg/g, eGFR {egfr:.0f} mL/min/1.73m².",
            "hospital": "Please assess diabetic complications and advise on further management.",
        }[dest]
    if note:
        purpose += ("　補足：" if ja else " Note: ") + note

    story = []
    title = "診療情報提供書（紹介状）" if ja else "Referral letter"
    story += [P(title, "title"), P(("紹介元医療機関：" if ja else "From: ") + f"{clinic}", "s"), Spacer(1, 4)]
    head = [
        [P("日付" if ja else "Date", "cb"), P(_reiwa(today) if ja else today.strftime("%d %B %Y"), "c")],
        [P("紹介先" if ja else "To", "cb"), P((f"{DEST[dest][1]} ご担当医 先生 御侍史" if ja else f"Department of {DEST[dest][0]}, to the doctor in charge"), "c")],
        [P("紹介元" if ja else "From", "cb"), P((f"{clinic}　担当医：{clinician}" if ja else f"{clinic}, Dr in charge: {clinician}"), "c")],
        [P("患者氏名" if ja else "Patient", "cb"), P((f"{name_ja} 殿" if name_ja else f"{name_en} 殿") if ja else f"{name_en}", "c")],
        [P("年齢・性別" if ja else "Age and sex", "cb"), P((f"{age}歳 {sex}") if ja else f"{age} years, {sex}", "c")],
        [P("患者ID（架空）" if ja else "Patient ID (synthetic)", "cb"), P(str(pr["id"]), "c")],
    ]
    t = Table(head, colWidths=[34 * mm, 136 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), TINT), ("GRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    story += [t, Spacer(1, 4)]
    story.append(P("いつもお世話になっております。下記の患者さんのご高診をお願い申し上げます。" if ja else "Dear colleague, thank you for seeing this patient, whom I am referring for the reason below."))

    story += [P("傷病名" if ja else "Diagnosis", "h")]
    diag = [(f"2型糖尿病（罹病期間 約{pr['duration_yrs']:.0f}年）" if ja else f"Type 2 diabetes mellitus, for about {pr['duration_yrs']:.0f} years")]
    story.append(P("<br/>".join("・" + d if ja else "• " + d for d in diag)))
    story += [P("紹介目的" if ja else "Reason for referral", "h"), P(purpose)]

    story += [P("主な所見・検査結果" if ja else "Key findings and results", "h")]
    rows = [[P("項目" if ja else "Item", "cb"), P("結果" if ja else "Result", "cb"), P("備考" if ja else "Comment", "cb")]]

    def add(item, value, comment=""):
        rows.append([P(item, "c"), P(value, "c"), P(comment, "c")])

    add("HbA1c", f"{pr['hba1c']:.1f} %", "")
    add("eGFR", f"{egfr:.0f} mL/min/1.73m²", "")
    add("尿アルブミン/クレアチニン比" if ja else "Urine albumin/creatinine ratio", f"{uacr:.0f} mg/gCr" if ja else f"{uacr:.0f} mg/g", albu_ja if ja else albu_en)
    add("血圧" if ja else "Blood pressure", f"{pr['sbp']:.0f}/{pr['dbp']:.0f} mmHg", "")
    add("BMI", f"{pr['bmi']:.1f}", "")
    add("糖尿病網膜症" if ja else "Diabetic retinopathy", (GRADE_JA[grade] if ja else GRADE_EN[grade]) if grade is not None else ("記録なし" if ja else "no record"),
        (f"最終眼底写真 {_jdate(last_eye)}" if ja else f"last retinal photograph {last_eye}") if last_eye else "")
    add("血糖（直近14日間・持続血糖測定）" if ja else "Glucose, last 14 days (sensor)", (f"平均 {m['mean']:.0f} mg/dL、目標範囲内 {m['tir'] * 100:.0f} %、70 mg/dL未満 {m['tbr'] * 100:.1f} %" if ja
        else f"mean {m['mean']:.0f} mg/dL, {m['tir'] * 100:.0f}% in range (70-180), {m['tbr'] * 100:.1f}% below 70"), "")
    tbl = Table(rows, colWidths=[52 * mm, 62 * mm, 56 * mm], repeatRows=1)
    tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), TINT), ("GRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    story.append(tbl)

    story += [P("現在の処方" if ja else "Current medicines", "h")]
    if meds:
        mrows = [[P("薬剤" if ja else "Medicine", "cb"), P("用法・用量" if ja else "Dose", "cb")]]
        for md in meds:
            nm = f"{MED_JA[md['name']]}（{md['name']}）" if ja and md["name"] in MED_JA else md["name"]
            ds = DOSE_JA.get(md["dose"], md["dose"]) if ja else md["dose"]
            mrows.append([P(clean(nm, 80), "c"), P(clean(ds, 120), "c")])
        mt = Table(mrows, colWidths=[70 * mm, 100 * mm])
        mt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), TINT), ("GRID", (0, 0), (-1, -1), 0.5, LINE), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        story.append(mt)
    else:
        story.append(P("なし" if ja else "None"))

    over = [t for t in screening["tests"] if t["state"] == "overdue"]
    if over:
        names_ja = {"eye": "眼科検査", "uacr": "尿アルブミン検査", "egfr": "腎機能検査", "foot": "足の診察"}
        story += [P("年1回の検査の状況" if ja else "Yearly tests", "h"),
                  P(("期限を過ぎている検査：" + "、".join(names_ja[t["key"]] for t in over) + "。") if ja else "Overdue: " + ", ".join(t["label"] for t in over) + ".")]

    story += [Spacer(1, 6), P("ご多忙のところ恐れ入りますが、よろしくお願い申し上げます。" if ja else "Thank you for your help. Please contact me if you need anything further."),
              Spacer(1, 12)]
    sig = Table([[P("紹介元医師　署名・押印" if ja else "Referring physician, signature and seal", "s"), P(clinician, "r")]], colWidths=[85 * mm, 85 * mm])
    sig.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.6, INK), ("TOPPADDING", (0, 0), (-1, -1), 6)]))
    story += [sig, Spacer(1, 5),
              P("これはデモ用の架空のデータから作成した文書で、実際の紹介状ではありません。内容は担当医が確認のうえ署名してください。Kayaは診断を行いません。" if ja
                else "Prepared from synthetic demo data by Kaya, a decision-support tool: not a real referral and not a diagnosis. The doctor must check the content and sign.", "s")]

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=12 * mm, bottomMargin=10 * mm,
                      title=title, author=clinic).build(story)
    return buf.getvalue()
