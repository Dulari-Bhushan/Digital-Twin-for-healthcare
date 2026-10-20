import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

fastapi_testclient = pytest.importorskip("fastapi.testclient")
import app as kaya  # noqa: E402

pytestmark = pytest.mark.skipif(not (ROOT / "artifacts" / "cardio" / "index.json").exists(), reason="Heart watch artifacts not built")


@pytest.fixture(scope="module")
def client():
    with fastapi_testclient.TestClient(kaya.app) as c:
        yield c


def test_patient_list_is_ranked_by_peak_risk(client):
    rows = client.get("/api/cardio/patients").json()
    assert len(rows) >= 4
    peaks = [r["peak_p"] for r in rows]
    assert peaks == sorted(peaks, reverse=True)
    assert all(0 <= r["peak_p"] <= 1 and 0 <= r["record_pct"] <= 1 for r in rows)


def test_patient_artifact_is_consistent(client):
    pid = client.get("/api/cardio/patients").json()[0]["id"]
    a = client.get(f"/api/cardio/{pid}").json()
    m = a["mornings"]
    ks = [x["k"] for x in m]
    assert ks == sorted(set(ks))                        # one morning per day, in order (mornings after an event are not scored)
    assert all(0 <= x["p"] <= 1 and 0 <= x["p_wearable"] <= 1 and 0 <= x["record_pct"] <= 1 for x in m)
    assert all(x["p"] >= a["threshold"] for x in m if x["alert"])                       # an alert never fires below the threshold
    assert all(d["push"] > 0 and d["stream"] in ("wearable", "record") for x in m for d in x["drivers"])
    for series in a["nights"].values():
        assert len(series) == a["days"]


def test_demo_covers_the_fusion_story(client):
    """The set includes an event that was caught, and the model's own mistakes are not hidden."""
    stories = []
    for r in client.get("/api/cardio/patients").json():
        a = client.get(f"/api/cardio/{r['id']}").json()
        stories.append(a["profile"]["story"])
    assert "caught" in stories and "quiet_high_risk" in stories
    assert {"missed", "false_alarm"} & set(stories)


def test_evidence_has_every_input_and_confidence_intervals(client):
    ev = client.get("/api/cardio/evidence").json()
    for k in ("static_logistic", "rule", "wearable", "fused"):
        lo, hi = ev["auroc_with_ci"][k]["ci95"]
        assert 0.5 < lo < ev["auroc_with_ci"][k]["auroc"] < hi <= 1
        assert 0 <= ev["alert_replay"][k]["sensitivity"] <= 1
    assert ev["auroc_with_ci"]["fused"]["auroc"] > ev["auroc_with_ci"]["rule"]["auroc"]


def test_unknown_patient_is_404(client):
    assert client.get("/api/cardio/999999").status_code == 404
