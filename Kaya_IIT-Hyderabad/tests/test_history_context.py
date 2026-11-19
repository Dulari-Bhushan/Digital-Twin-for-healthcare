import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

fastapi_testclient = pytest.importorskip("fastapi.testclient")
import app as kaya  # noqa: E402
import assistant as asst  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with fastapi_testclient.TestClient(kaya.app) as c:
        yield c


def test_the_helper_knows_the_readings_from_the_glucose_table(client):
    a = kaya._get(1688)
    now = int(a["forecast"]["t"][-1])
    g = a["series"]["glucose"]
    ctx = asst.patient_context(a, 0)
    # "my sugar two hours ago" is in the facts, and it is the table's value 24 steps back
    m = re.search(r"2 h ago \([A-Za-z]{3} (\d\d:\d\d)\) (\d+)", ctx)
    assert m and int(m.group(2)) == round(g[now - 24])
    assert re.search(r"now \([A-Za-z]{3} 21:50\) " + str(round(g[now])), ctx)               # the demo clock reads 21:50
    for part in ("Day by day", "today so far", "yesterday", "highest", "lowest", "steps", "meals (carbohydrate)"):
        assert part in ctx
    assert "never invent a number" in ctx


def test_the_context_has_no_identity_and_stays_small(client):
    a = kaya._get(1688)
    ctx = asst.patient_context(a, 0, kaya._patient_extra(1688))
    assert a["profile"]["name"] not in ctx and len(ctx) < 4500
    assert "Eye exam" in ctx                                                                  # Rajesh's overdue tests are known to the helper


def test_the_prompt_tells_the_model_to_use_the_readings(client):
    a = kaya._get(1688)
    p = asst.system_prompt("en", asst.patient_context(a, 0))
    assert "recent sugar readings" in p and "past readings" in p


def test_every_demo_patient_has_a_history_that_matches_the_table(client):
    for pid in (1688, 1636, 302):
        a = kaya._get(pid)
        now = int(a["forecast"]["t"][-1])
        ctx = asst.history_context(a)
        assert str(round(a["series"]["glucose"][now - 12])) in ctx                           # one hour ago
        assert ctx.count("|") >= 5                                                           # a week of days
