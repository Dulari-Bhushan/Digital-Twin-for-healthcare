import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

fastapi_testclient = pytest.importorskip("fastapi.testclient")
import app as kaya  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with fastapi_testclient.TestClient(kaya.app) as c:
        yield c


def test_health_and_triage_order(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["patients"] == 24
    scores = [p["score"] for p in client.get("/api/patients").json()]
    assert scores == sorted(scores, reverse=True)


def test_patient_detail_has_every_organ(client):
    pid = client.get("/api/patients").json()[0]["id"]
    d = client.get(f"/api/patients/{pid}").json()
    assert {"liver", "eye", "kidney", "now"} <= d.keys()
    assert len(d["now"]["forecast"]) == 3
    assert 0 <= d["now"]["p_hyper_2h"] <= 1


def test_series_shapes_line_up(client):
    pid = client.get("/api/patients").json()[0]["id"]
    s = client.get(f"/api/patients/{pid}/series?days=1").json()
    assert len(s["glucose"]) == len(s["meal_carbs"]) == 288
    assert len(s["forecast"]["t"]) == len(s["forecast"]["q"]) == len(s["forecast"]["p"])


def test_whatif_changes_the_right_way(client):
    pid = client.get("/api/patients").json()[0]["id"]
    r = client.post(f"/api/patients/{pid}/whatif", json={"carb_scale": 0.7, "walk_after_meals": 20, "baseline_shift": -10, "steps_delta": 2000}).json()
    assert r["metrics"]["after"]["tar"] <= r["metrics"]["before"]["tar"]
    assert r["liver"]["after"]["steatosis"][-1] <= r["liver"]["before"]["steatosis"][-1]
    assert r["kidney"]["after"]["egfr"][-1] >= r["kidney"]["before"]["egfr"][-1]
    assert client.post(f"/api/patients/{pid}/whatif", json={"carb_scale": 5}).status_code == 422


def test_live_ingest_needs_two_hours_then_forecasts(client):
    pid = client.get("/api/patients").json()[0]["id"]
    out = None
    for i in range(30):
        out = client.post(f"/api/live/{pid}/reading", params={"reset": i == 0},
                          json={"glucose": 140 + i, "heart_rate": 70, "steps": 0, "meal_carbs": 0, "minute_of_day": i * 5}).json()
        if i < 23:
            assert out["ready"] is False
    assert out["ready"] is True and len(out["forecast"]["q"]) == 3


def test_live_websocket_streams_forecasts(client):
    pid = client.get("/api/patients").json()[0]["id"]
    with client.websocket_connect(f"/ws/live/{pid}?interval=0.02&back_days=0.2") as ws:
        assert ws.receive_json()["type"] == "init"
        tick = ws.receive_json()
        assert tick["type"] == "tick" and tick["forecast"] is not None


def test_pdf_report_and_fhir(client):
    pid = client.get("/api/patients").json()[0]["id"]
    r = client.get(f"/api/patients/{pid}/report.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF")
    assert client.get(f"/fhir/Patient/{pid}").json()["resourceType"] == "Patient"
    assert client.get(f"/fhir/Observation?patient={pid}").json()["total"] >= 5
    assert client.get("/api/patients/999999").status_code == 404


def test_reports_changes_and_pdf_endpoints(client):
    rep = client.get("/api/patients/1688/reports").json()
    assert len(rep["reports"]) >= 15 and rep["medications"] and "_vals" not in rep
    ch = client.get("/api/patients/1688/changes").json()
    assert ch["headline"].startswith("Since the last visit") and ch["items"]
    pdf = client.get(f"/api/patients/1688/reports/{rep['reports'][0]['id']}.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert client.get("/api/patients/1688/reports/nope.pdf").status_code == 404
    assert client.get("/api/patients/99999/reports").status_code == 404


def test_log_api_round_trip(client, tmp_path, monkeypatch):
    import diary

    monkeypatch.setattr(diary, "LOG_DIR", tmp_path)
    before = client.get("/api/patients/1636/log").json()
    assert before["today"]["med_evening"] is False and len(before["entries"]) > 10
    after = client.post("/api/patients/1636/log", json={"kind": "med", "value": "evening"}).json()
    assert after["today"]["med_evening"] is True
    assert client.post("/api/patients/1636/log", json={"kind": "walk", "value": 9999}).status_code == 422
    eid = after["today"]["patient_ids"] and next(iter(after["today"]["patient_ids"]))
    assert client.delete(f"/api/patients/1636/log/{eid}").json()["today"]["med_evening"] is False
    assert client.delete("/api/patients/1636/log/nope").status_code == 404
    assert any("Evening medicines" in a["text"] for a in client.get("/api/patients/1688/changes").json()["attention"])


def test_admin_overview_and_selftest(client, monkeypatch):
    client.get("/api/patients")
    o = client.get("/api/admin/overview").json()
    assert o["service"]["status"] == "ok" and o["data"]["patients"] == 24 and o["data"]["synthetic"] is True
    assert any(m["name"] == "Glucose forecaster" for m in o["models"]) and o["traffic"]["total"] >= 1
    assert not any("sk_" in str(v) for v in o["integrations"])
    st = client.post("/api/admin/selftest").json()
    required = [c for c in st["checks"] if not c["warn"]]
    assert required and all(c["ok"] for c in required)


def test_admin_token_is_enforced_when_set(client, monkeypatch):
    monkeypatch.setenv("KAYA_ADMIN_TOKEN", "s3cret")
    assert client.get("/api/admin/overview").status_code == 401
    assert client.get("/api/admin/overview", headers={"x-admin-token": "wrong"}).status_code == 401
    assert client.get("/api/admin/overview", headers={"x-admin-token": "s3cret"}).json()["auth"] == "token"
    assert client.post("/api/admin/selftest").status_code == 401


def test_assistant_outcomes_are_counted_without_message_text(client):
    import admin

    before = admin.TEL.assistant["medicine"]
    client.post("/api/assistant", json={"pid": 1688, "message": "how much insulin should I take tonight"})
    assert admin.TEL.assistant["medicine"] == before + 1
    assert "insulin" not in str(list(admin.TEL.audit_log)).lower()


def test_upload_api_round_trip(client, tmp_path, monkeypatch):
    import uploads

    monkeypatch.setattr(uploads, "UP_DIR", tmp_path)
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    h = {"x-filename": "lipid%20photo.png", "x-title": "Lipid%20profile", "x-category": "blood%20test", "x-date": "2026-01-05"}
    r = client.post("/api/patients/1636/uploads", content=png, headers=h)
    assert r.status_code == 200 and r.json()["title"] == "Lipid profile"
    uid = r.json()["id"]
    got = client.get(f"/api/patients/1636/uploads/{uid}/file")
    assert got.status_code == 200 and got.headers["content-type"] == "image/png" and got.headers["x-content-type-options"] == "nosniff"
    assert client.post("/api/patients/1636/uploads", content=b"<html>", headers=h).status_code == 422
    assert client.get("/api/patients/1636/uploads").json()["items"][0]["id"] == uid
    assert client.get("/api/patients/1688/uploads").json()["items"] == []          # one patient's files are not listed for another
    assert client.get(f"/api/patients/1688/uploads/{uid}/file").status_code == 404
    assert client.delete(f"/api/patients/1636/uploads/{uid}").json()["items"] == []
    assert client.get("/api/patients/99999/uploads").status_code == 404


def test_uploaded_document_is_read_and_added_to_the_reports(client, tmp_path, monkeypatch):
    import time

    import uploads

    class FakeSarvam:
        def digitise(self, data, filename, media, lang="en-IN", wait_s=90):
            return "Collected 05/01/2026<table><tr><td>HbA1c</td><td>9.2</td><td>%</td></tr><tr><td>SGPT (ALT)</td><td>61</td><td>U/L</td></tr></table>"

    monkeypatch.setattr(uploads, "UP_DIR", tmp_path)
    monkeypatch.setitem(kaya.VOICE, "client", FakeSarvam())
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    h = {"x-filename": "lab.png", "x-title": "My%20lab", "x-category": "blood%20test", "x-date": "2026-01-06"}
    off = client.post("/api/patients/1636/uploads", content=png, headers=h).json()          # no x-ocr header: never sent for reading
    assert off["ocr"]["state"] == "off"
    on = client.post("/api/patients/1636/uploads", content=png, headers={**h, "x-ocr": "1"}).json()
    assert on["ocr"]["state"] == "pending"
    for _ in range(40):
        item = next(i for i in client.get("/api/patients/1636/uploads").json()["items"] if i["id"] == on["id"])
        if item["ocr"]["state"] not in ("pending", "reading"):
            break
        time.sleep(0.1)
    assert item["ocr"]["state"] == "done" and item["ocr"]["results"] == 2 and "text" not in item["ocr"]
    reps = [r for r in client.get("/api/patients/1636/reports").json()["reports"] if r["code"] == "UPL"]
    assert len(reps) == 1 and reps[0]["status"] == "Unverified" and reps[0]["date"] == "2026-01-05"
    rows = {r["key"]: r for r in reps[0]["sections"][0]["rows"]}
    assert rows["hba1c"]["value"] == 9.2 and rows["hba1c"]["tone"] == "rose" and "prev" in rows["hba1c"]
    assert reps[0]["file_url"].endswith(f"/uploads/{on['id']}/file") and reps[0]["source_text"]
    assert client.get(f"/api/patients/1636/reports/{reps[0]['id']}.pdf").status_code == 404     # the original file is the source of truth


def test_failed_reading_keeps_the_file(client, tmp_path, monkeypatch):
    import time

    import uploads
    from voice import VoiceError

    class Broken:
        def digitise(self, *a, **k):
            raise VoiceError("document service unreachable")

    monkeypatch.setattr(uploads, "UP_DIR", tmp_path)
    monkeypatch.setitem(kaya.VOICE, "client", Broken())
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    u = client.post("/api/patients/1636/uploads", content=png, headers={"x-ocr": "1", "x-filename": "a.png"}).json()
    for _ in range(40):
        item = client.get("/api/patients/1636/uploads").json()["items"][0]
        if item["ocr"]["state"] not in ("pending", "reading"):
            break
        time.sleep(0.1)
    assert item["ocr"]["state"] == "failed"
    assert client.get(f"/api/patients/1636/uploads/{u['id']}/file").status_code == 200
