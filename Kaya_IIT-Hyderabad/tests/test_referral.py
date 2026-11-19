import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

fastapi_testclient = pytest.importorskip("fastapi.testclient")
pymupdf = pytest.importorskip("pymupdf")
import app as kaya  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with fastapi_testclient.TestClient(kaya.app) as c:
        yield c


def _text(pdf: bytes) -> tuple[int, str]:
    d = pymupdf.open(stream=pdf, filetype="pdf")
    return len(d), "".join(p.get_text() for p in d)


def test_the_japanese_eye_letter_is_one_page_and_has_what_a_clinic_expects(client):
    r = client.get("/api/patients/1688/referral.pdf", params={"to": "eye", "lang": "ja", "note": "急ぎでお願いします"})
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    pages, text = _text(r.content)
    assert pages == 1
    for part in ("診療情報提供書", "眼科", "御侍史", "田中 浩", "2型糖尿病", "紹介目的", "糖尿病網膜症", "現在の処方", "急ぎでお願いします", "架空"):
        assert part in text, part
    assert "令和8年" in text                                           # the date in the era used on Japanese forms


def test_the_english_letter_and_the_other_destinations(client):
    pages, text = _text(client.get("/api/patients/1688/referral.pdf", params={"to": "eye", "lang": "en"}).content)
    assert pages == 1 and "Referral letter" in text and "Hiroshi Tanaka" in text and "Ophthalmology" in text and "retinopathy" in text
    pages, text = _text(client.get("/api/patients/1688/referral.pdf", params={"to": "kidney", "lang": "ja"}).content)
    assert pages == 1 and "腎臓内科" in text and "eGFR" in text and "尿アルブミン" in text
    pages, text = _text(client.get("/api/patients/1636/referral.pdf", params={"to": "hospital", "lang": "en"}).content)
    assert pages == 1 and "Yui Sato" in text and "diabetes and endocrinology" in text


def test_the_letter_uses_the_patients_own_numbers(client):
    a = kaya._get(1688)
    _, text = _text(client.get("/api/patients/1688/referral.pdf", params={"to": "kidney", "lang": "en"}).content)
    assert f"{a['profile']['hba1c']:.1f} %" in text and f"{a['profile']['labs']['egfr']:.0f} mL/min" in text


def test_bad_requests_and_markup_are_refused_or_neutralised(client):
    assert client.get("/api/patients/1688/referral.pdf", params={"to": "dentist"}).status_code == 422
    assert client.get("/api/patients/999999/referral.pdf").status_code == 404
    r = client.get("/api/patients/1688/referral.pdf", params={"to": "eye", "lang": "en", "note": "<b>x</b> & <script>alert(1)</script>"})
    assert r.status_code == 200 and "<script>" not in _text(r.content)[1]
