import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

fastapi_testclient = pytest.importorskip("fastapi.testclient")
import app as kaya  # noqa: E402
import assistant as asst  # noqa: E402
import messages as msgs  # noqa: E402
import names  # noqa: E402
import region  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with fastapi_testclient.TestClient(kaya.app) as c:
        yield c


def test_japan_is_the_default_and_swaps_only_fixed_texts():
    assert region.REGION == "JP" and region.EMERGENCY_NUMBER == "119"
    assert region.number("Please call 108 straight away.") == "Please call 119 straight away."
    assert region.number("कृपया 108 पर कॉल करें") == "कृपया 119 पर कॉल करें"
    assert region.localize("smaller portions of rice and roti, and add more vegetables and dal.") == "smaller portions of rice and bread, and add more vegetables and protein."
    assert region.number("sugar 1080 and 2108") == "sugar 1080 and 2108"                         # whole numbers only


def test_india_mode_gives_108_and_keeps_the_indian_foods(monkeypatch):
    monkeypatch.setattr(region, "REGION", "IN")
    monkeypatch.setattr(region, "EMERGENCY_NUMBER", "108")
    assert region.number("call 119 now") == "call 108 now"
    assert region.localize("rice and roti") == "rice and roti"


def test_every_emergency_message_uses_the_local_number():
    for lang, text in asst.EMERGENCY_MSG.items():
        assert "119" in text and not re.search(r"\b108\b", text), lang


def test_the_quick_start_messages_are_local():
    u_er = " ".join(msgs.TEMPLATE_TEXT["u_er"])
    assert "119" in u_er and "108" not in u_er
    assert "rice and bread" in " ".join(msgs.TEMPLATE_TEXT["a_portions"]) and "roti" not in " ".join(msgs.TEMPLATE_TEXT["a_portions"])


def test_demo_patients_have_japanese_names_in_both_scripts(client):
    ps = {p["id"]: p for p in client.get("/api/patients").json()}
    assert len(ps) == 24 and ps[1688]["name"] == "Hiroshi Tanaka" and ps[1636]["name"] == "Yui Sato"
    for pid, p in ps.items():
        assert p["name"] == names.NAMES_JP[pid][0] and names.name_ja_of(pid) == names.NAMES_JP[pid][1]
        assert re.search(r"[一-鿿]", names.NAMES_JP[pid][1])
    assert len({v[0] for v in names.NAMES_JP.values()}) == 24                                       # no two patients share a name
    assert kaya._get(1688)["profile"]["name_ja"] == "田中 浩"


def test_no_indian_names_are_left_anywhere_in_japan_mode(client):
    indian = set(names.NAMES_IN.values()) | {"Radha Nair", "Geeta Pillai"}
    seen = {p["name"] for p in client.get("/api/patients").json()} | {p["name"] for p in client.get("/api/cardio/patients").json()}
    assert not (seen & indian), seen & indian
    assert any(n in seen for n in ("Haruka Sasaki", "Chieko Endo"))                                  # the two messy-data examples were renamed too


def test_the_reports_use_japanese_doctors_and_the_clinic_reports_the_region(client):
    import reports as rpt
    assert rpt.DOCS["diab"].startswith("Dr. Keiko Mori")
    info = client.get("/api/clinic").json()
    assert info["region"] == "JP" and info["emergency_number"] == "119"


def test_the_seeded_patient_messages_are_found_by_patient_id_and_local(client, tmp_path, monkeypatch):
    monkeypatch.setattr(msgs, "MSG_DIR", tmp_path)
    kaya._seed_patient_messages()
    text = {m["body"] for m in msgs.list_messages(800)}
    assert any("bread instead of rice" in t for t in text)
    assert msgs.list_messages(302) and msgs.list_messages(814)
