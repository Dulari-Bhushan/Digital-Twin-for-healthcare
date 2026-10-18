"""Reading lab values out of OCR text: layouts, units, dates, and refusing to guess."""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

import labparse  # noqa: E402

HTML = ("<h2>CITY LAB</h2>Sample collected: 05/01/2026 Reported: 06/01/2026<table><tr><td>Test</td><td>Result</td><td>Unit</td></tr>"
        "<tr><td>Glycosylated Hemoglobin (HbA1c)</td><td>8.7</td><td>%</td></tr><tr><td>Serum Creatinine</td><td>1.3</td><td>mg/dL</td></tr>"
        "<tr><td>eGFR (CKD-EPI 2021)</td><td>61</td><td>mL/min</td></tr><tr><td>Total Cholesterol</td><td>201</td><td>mg/dL</td></tr>"
        "<tr><td>LDL Cholesterol</td><td>122</td><td>mg/dL</td></tr><tr><td>Platelet Count</td><td>1.62</td><td>Lakh/cumm</td></tr></table>")


def _vals(text, sex="M"):
    return {r["key"]: r["value"] for r in labparse.parse(labparse.clean_text(text), sex)}


def test_html_table_one_row_per_line_and_all_tests_found():
    v = _vals(HTML)
    assert v == {"hba1c": 8.7, "creatinine": 1.3, "egfr": 61, "tc": 201, "ldl": 122, "platelets": 162}


def test_markdown_pipe_table_and_plain_lines():
    md = "| Test | Result | Unit |\n|---|---|---|\n| HbA1c | 7.4 | % |\n| SGPT (ALT) | 52 | U/L |\n| SGOT (AST) | 31 | U/L |\nFasting Blood Sugar  118 mg/dL  70-100"
    assert _vals(md) == {"hba1c": 7.4, "alt": 52, "ast": 31, "fpg": 118}


def test_unit_conversions():
    assert _vals("Fasting glucose 7.0 mmol/L")["fpg"] == 126
    assert _vals("Serum Creatinine 88 umol/L")["creatinine"] == 1.0
    assert _vals("Triglycerides 1.7 mmol/L")["tg"] == 151
    assert _vals("Platelet count 165000 /uL")["platelets"] == 165


def test_flags_follow_reference_ranges():
    rows = {r["key"]: r for r in labparse.parse("HbA1c 9.4 %\nALT 31 U/L")}
    assert rows["hba1c"]["tone"] == "rose" and rows["alt"]["tone"] == "mint"


def test_implausible_or_missing_values_are_dropped_not_guessed():
    assert _vals("HbA1c 98 %\nALT: pending\nLDL Cholesterol - see note") == {}
    assert _vals("Albumin / Creatinine Ratio 231 mg/g").keys() == {"uacr"}        # not also read as serum creatinine
    assert "tc" not in _vals("HDL Cholesterol 41 mg/dL")                          # an HDL line is not total cholesterol


def test_date_picks_the_report_label_and_never_the_future():
    latest = datetime(2026, 1, 14)
    assert labparse.parse_date("Collected on 05/01/2026, reported 06/01/2026", latest) == "2026-01-06"
    assert labparse.parse_date("Date: 12 Mar 2025", latest) == "2025-03-12"
    assert labparse.parse_date("Next review 01/06/2027", latest) is None
    assert labparse.parse_date("no date here", latest) is None
