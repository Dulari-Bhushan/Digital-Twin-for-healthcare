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
