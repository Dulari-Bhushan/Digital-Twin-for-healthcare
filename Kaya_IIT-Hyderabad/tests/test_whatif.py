import sys
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(root / "whatif"))
sys.path.insert(0, str(root / "models"))
from engine import Scenario, apply_scenario, glucose_metrics  # noqa: E402
from liver_dynamic import risk_timeline  # noqa: E402


def _toy_day():
    t = np.arange(288 * 3)
    g = 110 + 60 * np.exp(-0.5 * ((t % 288 - 100) / 12) ** 2)   # one meal excursion per day
    meals = np.zeros(len(t))
    meals[[90, 90 + 288, 90 + 576]] = 60
    return g, meals


def test_smaller_carbs_lower_excursions():
    g, meals = _toy_day()
    g2 = apply_scenario(g, meals, Scenario(carb_scale=0.5))
    assert g2.max() < g.max() and g2.mean() < g.mean()


def test_baseline_shift_and_noop():
    g, meals = _toy_day()
    assert np.allclose(apply_scenario(g, meals, Scenario()), g, atol=1e-6)
    assert apply_scenario(g, meals, Scenario(baseline_shift=-10)).mean() < g.mean()


def test_risk_timeline_moves_toward_target_and_orders_by_load():
    p = {"steatosis": 0.3, "adv_fibrosis": 0.05}
    hi = risk_timeline(p, {"tar": 0.6, "gv_cv": 35, "steps_per_day": 3000})
    lo = risk_timeline(p, {"tar": 0.1, "gv_cv": 20, "steps_per_day": 9000})
    assert hi["steatosis"][-1] > hi["steatosis"][0] > lo["steatosis"][-1]
    assert glucose_metrics(np.full(100, 120.0), 5000)["tir"] == 1.0


def test_kidney_projection_orders_by_risk_factors():
    from kidney_dynamic import projection

    good = projection(80, 6.8, 118, 10, {"tar": 0.1, "gv_cv": 22}, 0.1)
    bad = projection(80, 10.0, 150, 80, {"tar": 0.7, "gv_cv": 38}, 0.1)
    assert bad["slope_per_year"] > good["slope_per_year"]
    assert bad["egfr"][-1] < good["egfr"][-1] < 80
    assert bad["albuminuria"][-1] > good["albuminuria"][-1]
