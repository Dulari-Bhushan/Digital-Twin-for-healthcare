"""Turn the text of an uploaded lab report (as read by OCR) into structured results.

Deliberately rule-based, not a language model: every number it returns can be traced to a line of the document, nothing is
invented, and a value outside a plausible range is dropped instead of guessed. The patient and doctor see the source text next
to the result. Handles the common Indian lab layouts (markdown tables or "Test  Result  Unit  Range" lines, SGPT/SGOT names,
lakh/cumm platelet counts, mmol/L and umol/L units).
"""
from __future__ import annotations

import re
from datetime import datetime

from reports import flag

# key, display name, unit, aliases (regex), plausible range, reference text, flag name
SPECS = [
    ("hba1c", "HbA1c", "%", r"hb\s*a1c|a1c|gly[ck]?(?:o|a)?sylated\s+h(?:a)?emoglobin|glycated\s+h(?:a)?emoglobin", (3, 20), "below 7 for most adults with T2D", "hba1c"),
    ("fpg", "Fasting plasma glucose", "mg/dL", r"fasting\s+(?:plasma\s+|blood\s+)?(?:glucose|sugar)|\bf\.?b\.?s\b|\bf\.?p\.?g\b", (40, 600), "80 - 130", "fpg"),
    ("creatinine", "Serum creatinine", "mg/dL", r"(?:serum\s+|s\.?\s*)?creatinine", (0.2, 15), "0.7 - 1.3", "creatinine"),
    ("egfr", "eGFR", "mL/min/1.73m2", r"e\.?\s?gfr|estimated\s+gfr|glomerular\s+filtration", (5, 200), "90 or more", "egfr"),
    ("uacr", "Urine albumin / creatinine ratio", "mg/g", r"albumin\s*[/\-]?\s*creatinine\s+ratio|\bu?acr\b|\bmicro\s*albumin.{0,20}creatinine", (0, 6000), "below 30", "uacr"),
    ("alt", "ALT (SGPT)", "U/L", r"\balt\b|sgpt|alanine\s+(?:amino)?transferase", (3, 2000), "up to 40", "alt"),
    ("ast", "AST (SGOT)", "U/L", r"\bast\b|sgot|aspartate\s+(?:amino)?transferase", (3, 2000), "up to 40", "ast"),
    ("platelets", "Platelet count", "x10^3/uL", r"platelet", (10, 1500), "150 - 400", "platelets"),
    ("tc", "Total cholesterol", "mg/dL", r"total\s+cholesterol|cholesterol[,\s]+total|\bt\.?\s*chol", (60, 600), "below 200", "tc"),
    ("ldl", "LDL cholesterol", "mg/dL", r"\bldl\b|low\s+density", (10, 400), "below 100", "ldl"),
    ("hdl", "HDL cholesterol", "mg/dL", r"\bhdl\b|high\s+density", (10, 150), "40 or more", "hdl"),
    ("tg", "Triglycerides", "mg/dL", r"triglycerides?|\btg\b", (20, 3000), "below 150", "tg"),
]
NUM = re.compile(r"(?<![\w.])(\d{1,6}(?:[.,]\d+)?)(?![\w])")
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _numbers_after(line: str, start: int) -> list[tuple[float, str]]:
    """Numbers after position `start` with the text that follows each (to read its unit)."""
    out = []
    for m in NUM.finditer(line, start):
        try:
            v = float(m.group(1).replace(",", "."))
        except ValueError:
            continue
        out.append((v, line[m.end():m.end() + 22].lower()))
    return out


def _convert(key: str, v: float, tail: str, line: str) -> float:
    unit = (tail + " " + line).lower()
    if key in ("fpg",) and "mmol" in unit:
        return v * 18.0
    if key in ("tc", "ldl", "hdl") and "mmol" in unit:
        return v * 38.67
    if key == "tg" and "mmol" in unit:
        return v * 88.57
    if key == "creatinine" and ("umol" in unit or "µmol" in unit or "μmol" in unit):
        return v / 88.4
    if key == "platelets":
        if "lakh" in unit or "lac" in unit:
            return v * 100
        if v >= 1500:           # reported per microlitre (for example 165000)
            return v / 1000
    return v


def _plausible(v: float, lo: float, hi: float) -> bool:
    return lo <= v <= hi


def parse_date(text: str, latest: datetime) -> str | None:
    """The most likely report date: one near a date-like label if present, otherwise the first full date. Never in the future."""
    cands: list[tuple[int, datetime]] = []
    pats = [
        (r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", lambda g: (int(g[2]), int(g[1]), int(g[0]))),
        (r"(\d{4})-(\d{2})-(\d{2})", lambda g: (int(g[0]), int(g[1]), int(g[2]))),
        (r"(\d{1,2})[ \-]([A-Za-z]{3})[a-z]*[ \-,]+(\d{4})", lambda g: (int(g[2]), MONTHS.get(g[1].lower()[:3], 0), int(g[0]))),
    ]
    for pat, conv in pats:
        for m in re.finditer(pat, text):
            y, mo, d = conv(m.groups())
            try:
                dt = datetime(y, mo, d)
            except ValueError:
                continue
            if dt > latest or dt.year < 2000:
                continue
            ctx = text[max(0, m.start() - 40):m.start()].lower()
            cands.append((0 if re.search(r"collect|sample|report|date|reported|drawn", ctx) else 1, dt))
    if not cands:
        return None
    cands.sort(key=lambda c: (c[0], -c[1].timestamp()))
    return cands[0][1].strftime("%Y-%m-%d")


def clean_text(text: str) -> str:
    """OCR output may contain HTML tables; turn each table row into one plain line and decode entities."""
    import html

    t = re.sub(r"(?i)</tr\s*>", "\n", text)
    t = re.sub(r"(?i)</t[dh]\s*>", "   ", t)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()



def parse(text: str, sex: str = "M") -> list[dict]:
    """Result rows for the tests found in `text`, in the same shape the report viewer already uses."""
    rows: dict[str, dict] = {}
    lines = [re.sub(r"[*_`#]", "", ln).replace("|", "  ") for ln in text.splitlines()]
    for ln in lines:
        low = ln.lower()
        if len(low.strip()) < 3:
            continue
        for key, name, unit, alias, (lo, hi), ref, fl in SPECS:
            if key in rows:
                continue
            if key in ("tc",) and re.search(r"hdl|ldl|vldl|non[\s-]?hdl|ratio", low):
                continue
            if key in ("ldl", "hdl") and ("vldl" in low and key == "ldl"):
                continue
            if key == "creatinine" and re.search(r"albumin|ratio|clearance|egfr|gfr", low):
                continue
            if key == "hba1c" and "estimated average" in low:
                continue
            m = re.search(alias, low)
            if not m:
                continue
            for v, tail in _numbers_after(ln, m.end()):
                v = _convert(key, v, tail, low)
                if key == "egfr" and re.match(r"\s*(?:ml|ml/min)", tail) is None and v > 200:
                    continue
                if _plausible(v, lo, hi):
                    dec = 2 if key in ("creatinine",) else 1 if key in ("hba1c",) else 0
                    val = round(v, dec) if dec else int(round(v))
                    label, tone = flag(fl, float(val), sex)
                    rows[key] = {"test": name, "value": val, "unit": unit, "ref": ref, "key": key, "flag": label, "tone": tone, "from": ln.strip()[:120]}
                    break
    return list(rows.values())
