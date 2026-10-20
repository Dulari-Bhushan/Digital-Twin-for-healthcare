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


def test_medicine_effects_have_the_right_direction():
    import medicines as med

    assert med.effect("metformin", "stop")["baseline_shift"] > 0 > med.effect("metformin", "add")["baseline_shift"]
    ins = [med.effect("insulin_glargine", a) for a in ("stop", "dose_down", "dose_up")]
    assert ins[0]["low_scale"] < ins[1]["low_scale"] < 1.0 < ins[2]["low_scale"]          # less insulin, fewer lows
    assert ins[0]["baseline_shift"] > ins[1]["baseline_shift"] > 0 > ins[2]["baseline_shift"]
    assert med.effect("semaglutide", "add")["carb_scale"] < 1.0


def test_medicine_choices_are_validated_and_combined():
    import pytest

    import medicines as med

    cur = {"metformin", "insulin_glargine", "telmisartan"}
    shift, low, carb, rows = med.combine({"metformin": "stop", "insulin_glargine": "dose_down", "sitagliptin": "add"}, cur)
    assert len(rows) == 3 and shift == pytest.approx(20 + 25 * 0.25 - 12)
    for bad in ({"telmisartan": "stop"}, {"metformin": "add"}, {"sitagliptin": "stop"}, {"nonsense": "stop"}, {"metformin": "explode"}):
        with pytest.raises(ValueError):
            med.combine(bad, cur)


def test_hand_added_medicine_effect():
    import medicines as med

    e = med.custom_effect("Glipizide", -15, True)
    assert e["baseline_shift"] == -15 and e["low_scale"] > 1.0 and e["action"] == "custom"
    assert med.custom_effect("Prednisolone", 20, False)["low_scale"] == 1.0
    assert med.clean_name("  <b>Drug</b>\x00 ") == "bDrug/b"


def test_fewer_lows_when_insulin_is_reduced():
    g, meals = _toy_day()
    g = g - 55 * np.exp(-0.5 * ((np.arange(len(g)) % 288 - 40) / 8) ** 2)                 # a night-time dip each day
    base = apply_scenario(g, meals, Scenario())
    less = apply_scenario(g, meals, Scenario(low_scale=0.5))
    assert less.min() > base.min()
