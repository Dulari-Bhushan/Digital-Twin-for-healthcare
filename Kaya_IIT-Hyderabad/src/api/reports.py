"""Synthetic medical-record history for each demo patient: lab panels, imaging, clinic notes, device reports,
and the "what changed since the last visit" summary.

Everything here is invented. The *current* values come from the patient's profile and the 14-day glucose series; the
*earlier* values are generated backwards from them with a seeded random walk (a worsening or improving trend per patient),
so the history is deterministic and consistent with today's numbers. The two demo patients have scripted trajectories.
"""
from __future__ import annotations

import io
import math
from datetime import datetime, timedelta, timezone

import numpy as np

LAB = "Kaya Demo Diagnostics (synthetic)"
HOSP = "Kaya Demo Hospital (synthetic)"
DOCS = {"diab": "Dr. Anita Kapoor, Diabetologist", "eye": "Dr. Vivek Bansal, Ophthalmologist", "liver": "Dr. Shalini Arora, Hepatologist",
        "rad": "Dr. Nitin Saluja, Radiologist", "card": "Dr. Rohit Khanna, Cardiologist", "pod": "Dr. Meera Chopra, Diabetes Foot Clinic"}
GRADES = ["No retinopathy", "Mild", "Moderate", "Severe", "Proliferative"]
VISIT_DAYS = [548, 365, 182, 91]          # clinic visits, in days before "today"
LAB_DAY = 3                                # newest lab panel, reported a few days ago and not yet reviewed

# Scripted trajectories for the two demo patients (rates are per year, positive = rising towards today).
SCRIPT = {
    1688: {"hb_rate": 0.8, "uacr_g": 0.9, "egfr_rate": -5.0, "alt_rate": 0.18, "grade_old": 1, "sbp_rate": 4.0},
    1636: {"hb_rate": -0.7, "uacr_g": 0.0, "egfr_rate": -0.4, "alt_rate": -0.05, "grade_old": 0, "sbp_rate": -2.0},
}


# ---------------------------------------------------------------- reference ranges and flags
def flag(name: str, v: float, sex: str = "M") -> tuple[str, str]:
    """(label, tone) with tone in mint / butter / rose."""
    f = {
        "hba1c": lambda: ("Well above target", "rose") if v >= 9 else ("Above 7% target", "butter") if v >= 7 else ("At target", "mint"),
        "fpg": lambda: ("High", "rose") if v > 180 else ("Above target", "butter") if v > 130 else ("In target", "mint"),
        "creatinine": lambda: ("High", "butter") if v > (1.1 if sex == "F" else 1.3) else ("Normal", "mint"),
        "egfr": lambda: ("Severely reduced", "rose") if v < 30 else ("Reduced", "rose") if v < 60 else ("Mildly reduced", "butter") if v < 90 else ("Normal", "mint"),
        "uacr": lambda: ("Severely increased (A3)", "rose") if v >= 300 else ("Moderately increased (A2)", "rose") if v >= 30 else ("Normal (A1)", "mint"),
        "alt": lambda: ("High", "butter") if v > 40 else ("Normal", "mint"),
        "ast": lambda: ("High", "butter") if v > 40 else ("Normal", "mint"),
        "platelets": lambda: ("Low", "rose") if v < 150 else ("High", "butter") if v > 400 else ("Normal", "mint"),
        "fib4": lambda: ("High risk", "rose") if v >= 2.67 else ("Indeterminate", "butter") if v >= 1.3 else ("Low risk", "mint"),
        "tg": lambda: ("High", "rose") if v >= 200 else ("Borderline", "butter") if v >= 150 else ("Normal", "mint"),
        "hdl": lambda: ("Low", "butter") if v < (50 if sex == "F" else 40) else ("Normal", "mint"),
        "ldl": lambda: ("High", "rose") if v >= 130 else ("Above 100 target", "butter") if v >= 100 else ("At target", "mint"),
        "tc": lambda: ("High", "butter") if v >= 200 else ("Normal", "mint"),
        "stiffness": lambda: ("Cirrhosis range", "rose") if v >= 13 else ("Fibrosis likely (F2+)", "butter") if v >= 8 else ("Below 8 kPa", "mint"),
        "fat": lambda: ("Steatosis", "butter") if v >= 5.5 else ("Normal", "mint"),
        "bp": lambda: ("High", "rose") if v >= 140 else ("Elevated", "butter") if v >= 130 else ("Normal", "mint"),
    }
    return f.get(name, lambda: ("", "mint"))()


def _creatinine(egfr: float, age: float, sex: str) -> float:
    """Inverse of CKD-EPI 2021 by bisection."""
    k, a = (0.7, -0.241) if sex == "F" else (0.9, -0.302)
    sf = 1.012 if sex == "F" else 1.0

    def f(scr):
        return 142 * min(scr / k, 1) ** a * max(scr / k, 1) ** -1.2 * 0.9938 ** age * sf

    lo, hi = 0.3, 9.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) > egfr else (lo, mid)
    return (lo + hi) / 2


def _row(test, value, unit, ref, flagname=None, sex="M", dec=1, prev=None):
    r = {"test": test, "value": round(float(value), dec) if dec else int(round(float(value))), "unit": unit, "ref": ref, "key": flagname or test}
    if flagname:
        r["flag"], r["tone"] = flag(flagname, float(value), sex)
    else:
        r["flag"], r["tone"] = "", "mint"
    return r


# ---------------------------------------------------------------- the patient's past, generated backwards from today
def _trend(a: dict) -> dict:
    p = a["profile"]
    lab = p["labs"]
    pid = p["id"]
    r = np.random.default_rng([pid, 7919])
    hb = p["hba1c"]
    kp = a["kidney"]["projection"]
    t = {
        "hb_rate": float(r.normal(0.25 if hb >= 8.5 else 0.0, 0.35)),
        "egfr_rate": float(kp["slope_per_year"] + r.normal(0, 0.5)),
        "uacr_g": float(r.uniform(0.1, 0.35)) if lab["uacr_mg_g"] >= 30 else 0.0,
        "alt_rate": float(r.normal(0.04, 0.06)),
        "sbp_rate": float(r.normal(1.5, 3.0)),
        "grade_old": max(0, p["clinic"]["dr_grade"] - (1 if p["clinic"]["dr_grade"] >= 1 and r.random() < 0.5 else 0)),
    }
    t.update(SCRIPT.get(pid, {}))
    t["ldl_now"] = float(np.clip(r.normal(108, 24) - (18 if p["age"] >= 40 else 0), 64, 190))
    return t


def _vals(a: dict, days_before: int, tr: dict) -> dict:
    """Laboratory and clinic values on a given date (exactly today's profile when the date is recent)."""
    p = a["profile"]
    lab = p["labs"]
    cl = p["clinic"]
    sex = p["sex"]
    yrs = days_before / 365.0
    old = days_before > 5
    r = np.random.default_rng([p["id"], 91, int(days_before)])

    def nz(s):
        return float(r.normal(0, s)) if old else 0.0

    hb = float(np.clip(p["hba1c"] - tr["hb_rate"] * yrs + nz(0.12), 5.0, 13.5)) if old else p["hba1c"]
    egfr = lab["egfr"] - tr["egfr_rate"] * yrs + nz(0.9) if old else lab["egfr"]
    uacr = lab["uacr_mg_g"] * math.exp(-tr["uacr_g"] * yrs + nz(0.08)) if old else lab["uacr_mg_g"]
    alt = lab["alt"] * math.exp(-tr["alt_rate"] * yrs + nz(0.06)) if old else lab["alt"]
    ast = lab["ast"] * math.exp(-tr["alt_rate"] * 0.8 * yrs + nz(0.06)) if old else lab["ast"]
    plt = lab["platelets"] * (1 + 0.012 * yrs + nz(0.02)) if old else lab["platelets"]
    tg = lab["triglycerides"] * math.exp(-0.15 * tr["hb_rate"] * yrs + nz(0.08)) if old else lab["triglycerides"]
    hdl = lab["hdl"] * (1 + nz(0.04)) if old else lab["hdl"]
    age = p["age"] - yrs
    fib4 = age * ast / (plt * math.sqrt(max(alt, 5))) if old else lab["fib4"]
    ldl = tr["ldl_now"] * (1 + 0.04 * yrs) + nz(5) if old else tr["ldl_now"]
    sbp = p["sbp"] - tr["sbp_rate"] * yrs + nz(2.5) if old else p["sbp"]
    dbp = p["dbp"] - tr["sbp_rate"] * 0.5 * yrs + nz(2) if old else p["dbp"]
    height = 1.58 if sex == "F" else 1.70
    bmi = p["bmi"] - float(np.random.default_rng([p["id"], 5]).normal(0.3, 0.4)) * yrs + nz(0.2) if old else p["bmi"]
    eag = 28.7 * hb - 46.7
    fpg = eag * 0.85 + nz(5) if old else eag * 0.85 + float(np.random.default_rng([p["id"], 6]).normal(0, 5))
    grade = tr["grade_old"] if days_before >= 300 else cl["dr_grade"]
    stiff = cl["liver_stiffness_kpa"] * math.exp(-0.05 * yrs + nz(0.03)) if old else cl["liver_stiffness_kpa"]
    fat = cl["liver_fat_pct"] * math.exp(-0.06 * yrs + nz(0.03)) if old else cl["liver_fat_pct"]
    return {"hba1c": hb, "fpg": fpg, "egfr": max(egfr, 8), "uacr": max(uacr, 1.0), "alt": max(alt, 8), "ast": max(ast, 8), "platelets": plt,
            "tg": max(tg, 40), "hdl": hdl, "ldl": max(ldl, 40), "fib4": fib4, "sbp": sbp, "dbp": dbp, "bmi": bmi, "weight": bmi * height * height,
            "creatinine": _creatinine(max(egfr, 8), age, sex), "grade": int(grade), "stiffness": stiff, "fat": fat, "age": age}


def _date(today: datetime, days_before: int) -> str:
    return (today - timedelta(days=days_before)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- medicines in force at a given time
def _meds(a: dict, today: datetime) -> list[dict]:
    p = a["profile"]
    lab = p["labs"]
    out = []
    if p["metformin"]:
        out.append({"name": "Metformin", "dose": "500 mg, one tablet twice a day with meals", "since": "At diagnosis", "start_days": 9999, "purpose": "Lowers sugar"})
    if p["on_insulin_or_su"]:
        if p["age"] >= 45 and p["duration_yrs"] >= 12:
            out.append({"name": "Insulin glargine", "dose": "16 units at bedtime", "since": "Several years", "start_days": 9999, "purpose": "Lowers sugar; can cause night-time lows"})
        else:
            out.append({"name": "Glimepiride", "dose": "2 mg once a day before breakfast", "since": "Several years", "start_days": 9999, "purpose": "Lowers sugar; can cause lows"})
    kidney = lab["uacr_mg_g"] >= 30 or lab["egfr"] < 60
    if kidney or p["sbp"] >= 135:
        out.append({"name": "Telmisartan", "dose": "40 mg once a day", "since": _date(today, 365), "start_days": 365, "purpose": "Protects kidneys, lowers blood pressure"})
    if kidney:
        out.append({"name": "Dapagliflozin", "dose": "10 mg once a day in the morning", "since": _date(today, 91), "start_days": 91, "purpose": "Protects kidneys and heart; also lowers sugar"})
    if p["age"] >= 40:
        out.append({"name": "Atorvastatin", "dose": "10 mg at night", "since": _date(today, 548), "start_days": 548, "purpose": "Lowers cholesterol, protects the heart"})
    return out


# ---------------------------------------------------------------- report builders
def _lab_report(a: dict, v: dict, date: str, days_before: int, new: bool) -> dict:
    sex = a["profile"]["sex"]
    ref_f = "50 or more" if sex == "F" else "40 or more"
    return {
        "type": "lab", "code": "LAB", "name": "Diabetes, kidney, liver and lipid panel", "facility": LAB, "clinician": "Ordered by " + DOCS["diab"], "date": date, "days_ago": days_before,
        "status": "Awaiting doctor review" if new else "Final", "new": new,
        "sections": [
            {"title": "Diabetes control", "rows": [_row("HbA1c", v["hba1c"], "%", "below 7 for most adults with T2D", "hba1c"),
                                                   _row("Fasting plasma glucose", v["fpg"], "mg/dL", "80 - 130", "fpg", dec=0)]},
            {"title": "Kidney function", "rows": [_row("Serum creatinine", v["creatinine"], "mg/dL", "0.6 - 1.1" if sex == "F" else "0.7 - 1.3", "creatinine", sex, dec=2),
                                                  _row("eGFR (CKD-EPI 2021)", v["egfr"], "mL/min/1.73m2", "90 or more", "egfr", dec=0),
                                                  _row("Urine albumin / creatinine ratio", v["uacr"], "mg/g", "below 30", "uacr", dec=0)]},
            {"title": "Liver function", "rows": [_row("ALT (SGPT)", v["alt"], "U/L", "up to 40", "alt", dec=0), _row("AST (SGOT)", v["ast"], "U/L", "up to 40", "ast", dec=0),
                                                 _row("Platelet count", v["platelets"], "x10^3/uL", "150 - 400", "platelets", dec=0), _row("FIB-4 index", v["fib4"], "", "below 1.3", "fib4", dec=2)]},
            {"title": "Lipid profile", "rows": [_row("Total cholesterol", v["ldl"] + v["hdl"] + v["tg"] / 5, "mg/dL", "below 200", "tc", dec=0),
                                                _row("LDL cholesterol (calculated)", v["ldl"], "mg/dL", "below 100", "ldl", dec=0),
                                                _row("HDL cholesterol", v["hdl"], "mg/dL", ref_f, "hdl", sex, dec=0), _row("Triglycerides", v["tg"], "mg/dL", "below 150", "tg", dec=0)]},
        ],
        "findings": [], "impression": "", "plain": "", "recommendations": [],
    }


def _lab_text(rep: dict, v: dict) -> None:
    f, bad = [], []
    if v["hba1c"] >= 7:
        bad.append(f"HbA1c {v['hba1c']:.1f}% is above the 7% target")
    if v["egfr"] < 60:
        bad.append(f"eGFR {v['egfr']:.0f} is reduced")
    if v["uacr"] >= 30:
        bad.append(f"urine albumin {v['uacr']:.0f} mg/g shows albuminuria")
    if v["alt"] > 40:
        bad.append(f"ALT {v['alt']:.0f} U/L is raised")
    if v["fib4"] >= 1.3:
        bad.append(f"FIB-4 {v['fib4']:.2f} is not in the low-risk range")
    if v["ldl"] >= 100:
        bad.append(f"LDL {v['ldl']:.0f} mg/dL is above target")
    f.append("Results are listed with reference ranges; values outside target are marked.")
    rep["findings"] = f
    rep["impression"] = ("Out of range: " + "; ".join(bad) + ".") if bad else "All measured values are within target."
    rep["plain"] = (("Some of your results are outside the healthy range: " + "; ".join(bad) + ". This does not mean something new is wrong today; your doctor will look at the pattern across your last few reports and explain what to change.")
                    if bad else "All your blood and urine results are in the healthy or target range. Keep doing what you are doing.")
    rep["recommendations"] = ["Review the trend against the previous report", "Repeat in 3 months" if v["hba1c"] >= 7 else "Repeat in 6 months"]


def _fundus_report(a: dict, v: dict, date: str, days_before: int, tr: dict) -> dict:
    g = v["grade"]
    r = np.random.default_rng([a["profile"]["id"], 33, days_before])
    left = max(0, g - 1) if g >= 1 and r.random() < 0.4 else g
    desc = {
        0: "No microaneurysms, haemorrhages or exudates in either eye. Optic discs healthy. Macula flat.",
        1: "A few microaneurysms only. No haemorrhages or exudates. Macula flat.",
        2: "Microaneurysms, dot-and-blot haemorrhages and a few hard exudates, more than mild but less than severe. No new vessels. No macular thickening.",
        3: "Extensive haemorrhages in all four quadrants, venous beading. No new vessels yet.",
        4: "New vessels on the disc or elsewhere. High risk of bleeding into the eye.",
    }
    rec = {0: ["Annual retinal screening"], 1: ["Repeat retinal photograph in 12 months", "Keep HbA1c and blood pressure on target"],
           2: ["Ophthalmology review within 3 to 6 months", "Repeat retinal photograph in 6 months", "Tighten HbA1c and blood pressure"],
           3: ["Urgent ophthalmology referral within 2 weeks"], 4: ["Urgent ophthalmology referral for laser or injections"]}
    return {
        "type": "imaging", "code": "EYE", "name": "Retinal photograph (fundus) screening", "facility": HOSP + ", Eye Clinic", "clinician": DOCS["eye"], "date": date, "days_ago": days_before, "status": "Final",
        "new": days_before <= 5,
        "sections": [{"title": "Grading", "rows": [{"test": "Right eye", "value": GRADES[g], "unit": "", "ref": "No retinopathy", "key": "dr", "flag": "Normal" if g == 0 else "Mild change" if g == 1 else "Needs follow-up", "tone": "mint" if g == 0 else "butter" if g == 1 else "rose"},
                                                    {"test": "Left eye", "value": GRADES[left], "unit": "", "ref": "No retinopathy", "key": "dr_l", "flag": "Normal" if left == 0 else "Mild change" if left == 1 else "Needs follow-up", "tone": "mint" if left == 0 else "butter" if left == 1 else "rose"}]}],
        "findings": [desc[g], "Image quality adequate in both eyes."],
        "impression": f"Diabetic retinopathy: {GRADES[g].lower()}" + (" (worst eye)." if g else "."),
        "plain": {0: "Your eye scan shows no signs of diabetes damage in the back of your eyes.", 1: "There are very early, mild changes in the back of your eyes. These are common and usually do not affect sight now. Keeping sugar and blood pressure in check slows them.",
                  2: "The scan shows moderate changes caused by diabetes in the back of your eyes. Sight is usually normal at this stage, but you need an eye specialist to review it and a repeat scan in about six months.",
                  3: "The scan shows serious changes. You need to see an eye specialist soon.", 4: "The scan shows advanced changes. You need to see an eye specialist urgently."}[g],
        "recommendations": rec[g], "image": f"/eye-img/grade{g}.jpg", "image_cam": f"/eye-img/grade{g}_cam.jpg", "grade": g,
    }


def _liver_scan(a: dict, v: dict, date: str, days_before: int) -> dict:
    fat, stiff = v["fat"], v["stiffness"]
    us = "Normal echotexture" if fat < 5.5 else "Mild (grade 1) fatty change" if fat < 12 else "Moderate (grade 2) fatty change" if fat < 22 else "Severe (grade 3) fatty change"
    return {
        "type": "imaging", "code": "LIV", "name": "Liver elastography (FibroScan) and ultrasound", "facility": HOSP + ", Radiology", "clinician": DOCS["liver"], "date": date, "days_ago": days_before, "status": "Final",
        "new": days_before <= 5,
        "sections": [{"title": "Measurements", "rows": [_row("Liver stiffness (median)", stiff, "kPa", "below 8", "stiffness"), _row("Liver fat fraction", fat, "%", "below 5.5", "fat")]}],
        "findings": [f"Ultrasound: {us}.", "No focal lesion. Spleen and portal vein normal size." if stiff < 13 else "Features suggesting advanced fibrosis; correlate clinically."],
        "impression": ("Fat in the liver" if fat >= 5.5 else "No significant fat in the liver") + (f"; stiffness {stiff:.1f} kPa" + (" suggests significant scarring (F2 or higher)." if stiff >= 8 else " is in the normal range.")),
        "plain": (("Your liver scan shows fat in the liver" + (" and a stiffness reading that can mean some scarring. " if stiff >= 8 else ", with no sign of scarring. ")) if fat >= 5.5
                  else "Your liver scan looks healthy. ") + "Fat in the liver is common with diabetes and can improve with steady sugar levels, walking and weight loss.",
        "recommendations": ["Repeat elastography in 12 months" if stiff < 8 else "Repeat elastography in 6 months", "Lifestyle: daily walking, fewer sweet drinks and fried food"],
    }


def _cxr(a: dict, date: str, days_before: int) -> dict:
    old = a["profile"]["age"] >= 60
    return {
        "type": "imaging", "code": "CXR", "name": "Chest X-ray (PA view)", "facility": HOSP + ", Radiology", "clinician": DOCS["rad"], "date": date, "days_ago": days_before, "status": "Final", "new": False,
        "sections": [],
        "findings": ["Both lungs are clear. No consolidation, effusion or pneumothorax.", "Heart size within normal limits." + (" Mild unfolding of the aorta." if old else ""), "Bony thorax and diaphragm normal."],
        "impression": "Normal chest X-ray" + (" for age." if old else "."),
        "plain": "Your chest X-ray is normal. The lungs and heart look healthy.", "recommendations": ["No follow-up needed"],
    }


def _ecg(a: dict, date: str, days_before: int) -> dict:
    r = np.random.default_rng([a["profile"]["id"], 77])
    hr = int(np.clip(np.mean(a["series"]["heart_rate"][:2000]) - 4 + r.normal(0, 3), 56, 96))
    lvh = a["profile"]["sbp"] >= 140 or (a["profile"]["age"] >= 55 and r.random() < 0.25)
    return {
        "type": "cardiac", "code": "ECG", "name": "12-lead electrocardiogram (ECG)", "facility": HOSP + ", Cardiology", "clinician": DOCS["card"], "date": date, "days_ago": days_before, "status": "Final", "new": False,
        "sections": [{"title": "Measurements", "rows": [_row("Heart rate", hr, "bpm", "60 - 100", dec=0), _row("PR interval", 156 + int(r.integers(-10, 12)), "ms", "120 - 200", dec=0),
                                                         _row("QRS duration", 88 + int(r.integers(-6, 8)), "ms", "below 120", dec=0), _row("QTc", 418 + int(r.integers(-14, 16)), "ms", "below 450", dec=0)]}],
        "findings": ["Normal sinus rhythm. Normal axis.", "Voltage criteria for left ventricular hypertrophy; non-specific ST-T changes." if lvh else "No ST-segment or T-wave abnormality. No evidence of old infarction."],
        "impression": "Left ventricular hypertrophy pattern; correlate with blood pressure." if lvh else "Normal ECG.",
        "plain": "Your heart tracing shows some thickening of the heart muscle, which is common with higher blood pressure. Keeping blood pressure down helps." if lvh else "Your heart tracing is normal.",
        "recommendations": ["Blood pressure control and review"] if lvh else ["Repeat in 12 months"],
    }


def _foot(a: dict, date: str, days_before: int, tr: dict) -> dict:
    p = a["profile"]
    r = np.random.default_rng([p["id"], 55])
    neuro = p["duration_yrs"] > 15 and p["hba1c"] > 8 or (p["duration_yrs"] > 10 and r.random() < 0.3)
    return {
        "type": "clinic", "code": "FOOT", "name": "Diabetic foot examination", "facility": HOSP + ", Diabetes Foot Clinic", "clinician": DOCS["pod"], "date": date, "days_ago": days_before, "status": "Final", "new": False,
        "sections": [{"title": "Tests", "rows": [
            {"test": "10 g monofilament (both feet)", "value": "Reduced at left great toe" if neuro else "Felt at all sites", "unit": "", "ref": "Felt at all sites", "key": "mono", "flag": "", "tone": "butter" if neuro else "mint"},
            {"test": "Vibration (128 Hz tuning fork)", "value": "Reduced" if neuro else "Normal", "unit": "", "ref": "Normal", "key": "vib", "flag": "", "tone": "butter" if neuro else "mint"},
            {"test": "Foot pulses (dorsalis pedis, posterior tibial)", "value": "Palpable", "unit": "", "ref": "Palpable", "key": "pulse", "flag": "", "tone": "mint"},
            {"test": "Skin, nails, ulcers", "value": "Dry skin, no ulcer", "unit": "", "ref": "Intact", "key": "skin", "flag": "", "tone": "mint"}]}],
        "findings": ["Early loss of protective sensation in the left foot." if neuro else "Protective sensation intact. No deformity or ulcer."],
        "impression": "Early peripheral neuropathy; moderate foot-care risk." if neuro else "Low risk of foot ulcer.",
        "plain": "Your feet have lost a little feeling, so small cuts can go unnoticed. Check your feet every day and wear closed, soft footwear." if neuro else "Your feet are healthy and you can feel normally. Keep checking them daily.",
        "recommendations": ["Daily foot check and moisturiser", "Review every 6 months" if neuro else "Review every 12 months"],
    }


def _visit(a: dict, v: dict, date: str, days_before: int, meds: list[dict], idx: int) -> dict:
    p = a["profile"]
    r = np.random.default_rng([p["id"], 12, idx])
    complaints = ["No new complaints.", "Some tiredness in the afternoons.", "Occasional tingling in the feet.", "Skipped some evening walks over the festival season."]
    if p["on_insulin_or_su"] and v["hba1c"] >= 8.5:
        complaints = ["Occasional dizziness and sweating in the early morning.", "Feels tired and thirsty through the day."]
    if v["hba1c"] >= 9:
        complaints = complaints + ["Increased thirst and passing urine more often."]
    assess, plan = [], []
    assess.append(f"HbA1c {v['hba1c']:.1f}%: " + ("at target." if v["hba1c"] < 7 else "above target." if v["hba1c"] < 9 else "well above target."))
    plan.append("Continue current diabetes medicines." if v["hba1c"] < 7 else "Review diabetes medicines and diet; repeat HbA1c in 3 months.")
    if v["uacr"] >= 30 or v["egfr"] < 60:
        assess.append(f"Kidney: eGFR {v['egfr']:.0f}, urine albumin {v['uacr']:.0f} mg/g (albuminuria).")
        plan.append("Continue telmisartan; avoid anti-inflammatory painkillers; repeat kidney tests in 3 months.")
    if v["sbp"] >= 140:
        assess.append(f"Blood pressure {v['sbp']:.0f}/{v['dbp']:.0f} is above the 130/80 target.")
    if v["grade"] >= 1:
        assess.append(f"Retinopathy {GRADES[v['grade']].lower()} at last screening.")
        plan.append("Retinal photograph due." if v["grade"] < 2 else "Ophthalmology follow-up arranged.")
    if v["alt"] > 40 or v["fib4"] >= 1.3:
        assess.append(f"Liver: ALT {v['alt']:.0f}, FIB-4 {v['fib4']:.2f}; likely fatty liver.")
        plan.append("Walking 30 minutes a day, fewer sweets and fried food.")
    if p["on_insulin_or_su"]:
        plan.append("Counselled on recognising and treating low sugar.")
    nxt = 90 if v["hba1c"] >= 7 else 180
    return {
        "type": "clinic", "code": "VIS", "name": "Clinic consultation note", "facility": HOSP + ", Diabetes Clinic", "clinician": DOCS["diab"], "date": date, "days_ago": days_before, "status": "Final", "new": False, "visit": True,
        "sections": [{"title": "Vitals", "rows": [_row("Blood pressure", v["sbp"], f"/{v['dbp']:.0f} mmHg", "below 130/80", "bp", dec=0), _row("Weight", v["weight"], "kg", "", dec=1),
                                                    _row("BMI", v["bmi"], "kg/m2", "18.5 - 24.9", dec=1), _row("Pulse", 72 + int(r.integers(-6, 8)), "bpm", "60 - 100", dec=0)]}],
        "meds": [m for m in meds if m["start_days"] >= days_before],
        "findings": [f"Complaints: {complaints[int(r.integers(0, len(complaints)))]}"] + assess,
        "impression": "Type 2 diabetes with " + ("kidney involvement, " if (v["uacr"] >= 30 or v["egfr"] < 60) else "") + ("retinopathy, " if v["grade"] else "") + ("fatty liver; " if v["alt"] > 40 else "") + ("good control." if v["hba1c"] < 7 else "suboptimal control."),
        "plain": "A summary of your visit: " + " ".join(assess[:2]) + " Your doctor planned: " + " ".join(plan[:2]),
        "recommendations": plan + [f"Next review in {nxt // 30} months."],
    }


def _cgm_report(a: dict, date: str) -> dict:
    m = a["metrics"]
    g = np.asarray(a["series"]["glucose"], dtype=float)
    n = len(g)
    lows = []
    for d in range(n // 288):
        day = g[d * 288:(d + 1) * 288]
        night = day[:72]
        mins = int((night < 70).sum() * 5)
        if mins >= 15:
            lows.append((d, mins, float(night.min())))
    findings = [f"{m['tir'] * 100:.0f}% of readings in range (70-180), {m['tar'] * 100:.0f}% above 180, {m['tbr'] * 100:.1f}% below 70.",
                f"Average glucose {m['mean']:.0f} mg/dL; glucose management indicator {m['gmi']:.1f}%; variability {m['gv_cv']:.0f}% (target below 36%)."]
    if lows:
        findings.append(f"{len(lows)} night-time low episode(s) below 70 mg/dL, lowest {min(x[2] for x in lows):.0f} mg/dL.")
    return {
        "type": "device", "code": "CGM", "name": "14-day continuous glucose monitor (CGM) report", "facility": "Wearable sensor, summarised by Kaya", "clinician": "Automatically generated", "date": date, "days_ago": 0,
        "status": "Latest", "new": True,
        "sections": [{"title": "Glucose metrics", "rows": [_row("Time in range 70-180", m["tir"] * 100, "%", "70 or more", dec=0), _row("Time above 180", m["tar"] * 100, "%", "below 25", dec=0),
                                                            _row("Time below 70", m["tbr"] * 100, "%", "below 4", dec=1), _row("Mean glucose", m["mean"], "mg/dL", "below 154", dec=0),
                                                            _row("Glucose management indicator", m["gmi"], "%", "below 7", dec=1), _row("Variability (CV)", m["gv_cv"], "%", "36 or less", dec=0)]}],
        "findings": findings,
        "impression": "Glucose control " + ("meets" if m["tir"] >= 0.7 else "is below") + " the 70% time-in-range target.",
        "plain": f"Over the last two weeks your sugar was in the healthy range {m['tir'] * 100:.0f}% of the time. The goal is above 70%." + (" There were also some low readings at night." if lows else ""),
        "recommendations": ["See the Glucose tab for daily detail"],
    }


# ---------------------------------------------------------------- the full record
def build_record(a: dict, today: datetime) -> dict:
    p = a["profile"]
    tr = _trend(a)
    meds = _meds(a, today)
    reports = []
    for i, d in enumerate(VISIT_DAYS):
        v = _vals(a, d, tr)
        reports.append(_visit(a, v, _date(today, d), d, meds, i))
    for d in VISIT_DAYS + [LAB_DAY]:
        v = _vals(a, d, tr)
        rep = _lab_report(a, v, _date(today, d), d, new=d == LAB_DAY)
        _lab_text(rep, v)
        rep["vals"] = {k: v[k] for k in ("hba1c", "egfr", "uacr", "alt", "fib4", "tg", "ldl", "sbp", "dbp", "weight", "bmi")}
        reports.append(rep)
    for d in (365, LAB_DAY):
        reports.append(_fundus_report(a, _vals(a, d, tr), _date(today, d), d, tr))
        reports.append(_liver_scan(a, _vals(a, d, tr), _date(today, d), d))
    reports.append(_cxr(a, _date(today, 548), 548))
    reports.append(_ecg(a, _date(today, 365), 365))
    reports.append(_foot(a, _date(today, 182), 182, tr))
    reports.append(_cgm_report(a, _date(today, 0)))
    for r in reports:
        r["id"] = f"{p['id']}-{r['date']}-{r['code']}"
    reports.sort(key=lambda r: (r["days_ago"], r["code"]))
    # previous value of each lab row
    labs = sorted([r for r in reports if r["code"] == "LAB"], key=lambda r: -r["days_ago"])
    for k, r in enumerate(labs):
        if k == 0:
            continue
        before = {row["key"]: row for s in labs[k - 1]["sections"] for row in s["rows"]}
        for s in r["sections"]:
            for row in s["rows"]:
                b = before.get(row["key"])
                if b:
                    row["prev"] = {"value": b["value"], "date": labs[k - 1]["date"]}
    # trends for charts (oldest first)
    trends = {"dates": [r["date"] for r in labs]}
    for key in ("hba1c", "egfr", "uacr", "alt", "tg", "ldl"):
        trends[key] = [next(x["value"] for s in r["sections"] for x in s["rows"] if x["key"] == key) for r in labs]
    trends["sbp"] = [round(r["vals"]["sbp"], 0) for r in labs]
    trends["weight"] = [round(r["vals"]["weight"], 1) for r in labs]
    for r in reports:
        r.pop("vals", None) if r["code"] != "LAB" else None
    return {"patient_id": p["id"], "today": today.strftime("%Y-%m-%d"), "reports": reports, "trends": trends, "medications": meds,
            "_vals": {d: _vals(a, d, tr) for d in VISIT_DAYS + [LAB_DAY]}, "_tr": tr,
            "note": "All reports are synthetic. Earlier values are generated backwards from today's values with a seeded trend."}


# ---------------------------------------------------------------- what changed since the last visit
SPEC = {  # key: (label, plain label, group, unit, decimals, lower_is_better, material change)
    "hba1c": ("HbA1c", "Your 3-month sugar average (HbA1c)", "glucose", "%", 1, True, 0.2),
    "egfr": ("eGFR", "How well your kidneys filter (eGFR)", "kidney", "", 0, False, 1.0),
    "uacr": ("Urine albumin / creatinine", "Protein leaking into urine (UACR)", "kidney", "mg/g", 0, True, 0.1),
    "alt": ("ALT", "Liver enzyme (ALT)", "liver", "U/L", 0, True, 0.1),
    "fib4": ("FIB-4", "Liver scarring score (FIB-4)", "liver", "", 2, True, 0.1),
    "ldl": ("LDL cholesterol", "Bad cholesterol (LDL)", "heart", "mg/dL", 0, True, 8),
    "tg": ("Triglycerides", "Blood fat (triglycerides)", "heart", "mg/dL", 0, True, 0.1),
    "sbp": ("Systolic blood pressure", "Blood pressure (top number)", "heart", "mmHg", 0, True, 5),
    "weight": ("Weight", "Your weight", "lifestyle", "kg", 1, True, 1.5),
}


def _item(key, label, plain, group, unit, dec, lower_better, thr, before, after, when_before, rel=False):
    delta = after - before
    mat = abs(delta) / max(abs(before), 1e-9) if rel else abs(delta)
    same = mat < thr
    direction = "same" if same else ("better" if (delta < 0) == lower_better else "worse")
    return {"key": key, "label": label, "plain_label": plain, "group": group, "unit": unit, "dec": dec, "before": round(before, dec), "after": round(after, dec), "delta": round(delta, dec),
            "delta_pct": round(100 * delta / before, 0) if before else 0, "direction": direction, "when_before": when_before, "severity": 0.0 if same else round(mat / thr, 2)}


def build_changes(a: dict, rec: dict) -> dict:
    p = a["profile"]
    last_days = VISIT_DAYS[-1]
    when = _date(datetime.strptime(rec["today"], "%Y-%m-%d"), last_days)
    v0, v1 = rec["_vals"][last_days], rec["_vals"][LAB_DAY]
    items = []
    for key, (label, plain, group, unit, dec, lb, thr) in SPEC.items():
        rel = key in ("uacr", "alt", "fib4", "tg")
        items.append(_item(key, label, plain, group, unit, dec, lb, thr, v0[key], v1[key], when, rel=rel))
    # imaging: latest against the previous scan of the same kind
    fund = sorted([r for r in rec["reports"] if r["code"] == "EYE"], key=lambda r: -r["days_ago"])
    if len(fund) >= 2:
        items.append(_item("dr", "Retinopathy grade", "Eye check (retina)", "eye", "", 0, True, 1, fund[-2]["grade"], fund[-1]["grade"], fund[-2]["date"]))
    liv = sorted([r for r in rec["reports"] if r["code"] == "LIV"], key=lambda r: -r["days_ago"])
    if len(liv) >= 2:
        s = lambda r: r["sections"][0]["rows"][0]["value"]
        items.append(_item("stiffness", "Liver stiffness", "Liver stiffness scan", "liver", "kPa", 1, True, 0.1, s(liv[-2]), s(liv[-1]), liv[-2]["date"], rel=True))
    # glucose: the last 7 days against the 7 days before them (the wearable only keeps 14 days)
    g = np.asarray(a["series"]["glucose"], dtype=float)
    st = np.asarray(a["series"]["steps"], dtype=float)
    n = len(g)
    h = 7 * 288
    cur, prv = slice(n - h, n), slice(n - 2 * h, n - h)

    def stat(sl):
        x = g[sl]
        return {"tir": float(((x >= 70) & (x <= 180)).mean() * 100), "mean": float(x.mean()), "low": float((x < 70).mean() * 100), "steps": float(st[sl].sum() / 7)}

    c, b = stat(cur), stat(prv)
    wk = _date(datetime.strptime(rec["today"], "%Y-%m-%d"), 7)
    glu = [
        _item("tir", "Time in range (70-180)", "Time with sugar in the healthy range", "glucose", "%", 0, False, 5, b["tir"], c["tir"], wk),
        _item("mean", "Mean glucose", "Your average sugar", "glucose", "mg/dL", 0, True, 8, b["mean"], c["mean"], wk),
        _item("low", "Time below 70", "Time with low sugar", "glucose", "%", 1, True, 0.5, b["low"], c["low"], wk),
        _item("steps", "Steps a day", "Your daily steps", "lifestyle", "", 0, False, 600, b["steps"], c["steps"], wk),
    ]
    # attention list for the clinician
    attn = []
    for d in range(n // 288):
        night = g[d * 288:d * 288 + 72]
        mins = int((night < 70).sum() * 5)
        if mins >= 15:
            day = (datetime.strptime(rec["today"], "%Y-%m-%d") - timedelta(days=n // 288 - 1 - d)).strftime("%a %d %b")
            attn.append({"tone": "rose", "text": f"Night-time low on {day}: below 70 mg/dL for {mins} minutes (lowest {night.min():.0f})." + (" Patient is on insulin or a sulfonylurea; consider reviewing the dose." if p["on_insulin_or_su"] else "")})
    byk = {i["key"]: i for i in items + glu}
    if byk["tir"]["direction"] == "worse":
        attn.append({"tone": "butter", "text": f"Time in range fell from {byk['tir']['before']:.0f}% to {byk['tir']['after']:.0f}% week on week."})
    if byk["egfr"]["direction"] == "worse" and v1["egfr"] < 60:
        attn.append({"tone": "rose", "text": f"eGFR down from {v0['egfr']:.0f} to {v1['egfr']:.0f}; already below 60."})
    if byk["uacr"]["direction"] == "worse" and v1["uacr"] >= 30:
        attn.append({"tone": "rose", "text": f"Urine albumin up {byk['uacr']['delta_pct']:.0f}% to {v1['uacr']:.0f} mg/g since the last visit."})
    if byk.get("dr", {}).get("direction") == "worse":
        attn.append({"tone": "rose", "text": f"Retinopathy progressed from {GRADES[int(byk['dr']['before'])].lower()} to {GRADES[int(byk['dr']['after'])].lower()}; arrange ophthalmology review."})
    if byk["hba1c"]["direction"] == "worse" and v1["hba1c"] >= 8:
        attn.append({"tone": "butter", "text": f"HbA1c rose from {v0['hba1c']:.1f}% to {v1['hba1c']:.1f}% despite the current plan."})
    attn = attn[:5]
    for i in items:
        i["scope"] = "visit"
    for i in glu:
        i["scope"] = "week"
    allitems = items + glu
    cnt = {k: sum(1 for i in items if i["direction"] == k) for k in ("better", "worse", "same")}
    worst = sorted([i for i in items if i["direction"] == "worse"], key=lambda i: -i["severity"])[:2]
    best = sorted([i for i in items if i["direction"] == "better"], key=lambda i: -i["severity"])[:1]
    months = round(last_days / 30)
    head = f"Since the last visit ({months} months ago): {cnt['worse']} worse, {cnt['better']} better, {cnt['same']} unchanged."
    new_meds = [m for m in rec["medications"] if m["start_days"] == last_days]
    return {"patient_id": p["id"], "last_visit": when, "months_ago": months, "headline": head, "counts": cnt, "items": allitems, "attention": attn,
            "worst": [i["key"] for i in worst], "best": [i["key"] for i in best], "new_medicines": [m["name"] + " " + m["dose"] for m in new_meds], "week_from": wk}


# ---------------------------------------------------------------- PDF of one report
def report_pdf(profile: dict, rep: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from report import INK, LINE, MUTED, _styles

    S = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm, title=rep["name"])
    tone = {"mint": colors.HexColor("#1a6a4b"), "butter": colors.HexColor("#7d5c05"), "rose": colors.HexColor("#94284f")}
    el = [Paragraph(rep["facility"], S["s"]), Paragraph(rep["name"], S["h1"]), Spacer(1, 4)]
    meta = Table([[Paragraph("<b>Patient</b>", S["c"]), Paragraph(f"{profile.get('name', '')} (ID {profile['id']}), {profile['age']:.0f} y, {'female' if profile['sex'] == 'F' else 'male'}", S["c"]),
                   Paragraph("<b>Date</b>", S["c"]), Paragraph(rep["date"], S["c"])],
                  [Paragraph("<b>Clinician</b>", S["c"]), Paragraph(rep["clinician"], S["c"]), Paragraph("<b>Status</b>", S["c"]), Paragraph(rep["status"], S["c"])]], colWidths=[24 * mm, 80 * mm, 18 * mm, 48 * mm])
    meta.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    el += [meta, Spacer(1, 6)]
    for sec in rep["sections"]:
        el.append(Paragraph(sec["title"], S["h2"]))
        rows = [[Paragraph("<b>Test</b>", S["c"]), Paragraph("<b>Result</b>", S["c"]), Paragraph("<b>Reference</b>", S["c"]), Paragraph("<b>Flag</b>", S["c"])]]
        sty = [("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1eefc")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        for i, r in enumerate(sec["rows"], start=1):
            rows.append([Paragraph(r["test"], S["c"]), Paragraph(f"<b>{r['value']}</b> {r['unit']}", S["c"]), Paragraph(r.get("ref", ""), S["c"]), Paragraph(r.get("flag", ""), S["c"])])
            sty.append(("TEXTCOLOR", (3, i), (3, i), tone.get(r["tone"], INK)))
        t = Table(rows, colWidths=[62 * mm, 40 * mm, 46 * mm, 26 * mm])
        t.setStyle(TableStyle(sty))
        el.append(t)
    if rep.get("image"):
        try:
            from pathlib import Path

            img = Path(__file__).resolve().parents[2] / "artifacts" / "eye" / Path(rep["image"]).name
            if img.exists():
                el += [Spacer(1, 8), Image(str(img), width=70 * mm, height=70 * mm, kind="proportional"), Paragraph("Representative fundus photograph of this grade (IDRiD, CC BY 4.0), shown because the patient is synthetic.", S["s"])]
        except Exception:
            pass
    if rep["meds"] if rep.get("meds") else False:
        el.append(Paragraph("Medicines in force", S["h2"]))
        for m in rep["meds"]:
            el.append(Paragraph(f"<b>{m['name']}</b> {m['dose']} - {m['purpose']}", S["p"]))
    el.append(Paragraph("Findings", S["h2"]))
    for f in rep["findings"]:
        el.append(Paragraph("&bull; " + f, S["p"]))
    el += [Paragraph("Impression", S["h2"]), Paragraph(rep["impression"], S["p"])]
    if rep["recommendations"]:
        el.append(Paragraph("Recommendations", S["h2"]))
        for f in rep["recommendations"]:
            el.append(Paragraph("&bull; " + f, S["p"]))
    el += [Spacer(1, 14), Paragraph("SYNTHETIC REPORT generated by Kaya for a demonstration. It describes an invented person and has no clinical meaning. Decision support only.", S["s"])]
    doc.build(el)
    return buf.getvalue()
