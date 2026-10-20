"""Medicine-by-medicine what-if: what stopping, changing the dose of, or adding a glucose-lowering drug does to the glucose curve.

Every number below is a documented ASSUMPTION taken from the usual size of each drug's effect (roughly 0.5 to 1.5 percentage
points of HbA1c, and 1 point of HbA1c is about 29 mg/dL of mean glucose). They are shown to the clinician, can be edited here,
and the result is labelled a simulation. They describe an average patient, not this one.

  shift      mean glucose change in mg/dL when the drug is taken (negative = lowers glucose)
  dose_step  fraction of that effect gained or lost for a 25% dose change (flat for metformin and SGLT2 inhibitors, close to
             proportional for insulin and sulfonylureas)
  lows       how much the size of low-glucose dips changes: factor when stopped, dose down, dose up (insulin and sulfonylureas only)
  carb       factor on meal excursions (GLP-1 agonists slow gastric emptying)
"""
from __future__ import annotations

ACTIONS = ("stop", "dose_down", "dose_up", "add")
LABEL = {"stop": "Stop", "dose_down": "Dose -25%", "dose_up": "Dose +25%", "add": "Add"}

CATALOG: dict[str, dict] = {
    "metformin": {"name": "Metformin", "shift": -20.0, "dose_step": 0.10, "can_add": True,
                  "note": "About 0.7 points of HbA1c. The effect is nearly flat across the usual doses."},
    "insulin_glargine": {"name": "Insulin glargine", "shift": -25.0, "dose_step": 0.25, "lows": (0.2, 0.7, 1.4),
                         "note": "Effect follows the dose; lows become rarer with less insulin and more frequent with more."},
    "glimepiride": {"name": "Glimepiride", "shift": -18.0, "dose_step": 0.25, "lows": (0.3, 0.75, 1.35),
                    "note": "Effect follows the dose; a sulfonylurea carries a risk of lows."},
    "dapagliflozin": {"name": "Dapagliflozin", "shift": -14.0, "dose_step": 0.10, "can_add": True,
                      "note": "About 0.5 points of HbA1c; its kidney and heart protection is not modelled here."},
    "sitagliptin": {"name": "Sitagliptin", "shift": -12.0, "dose_step": 0.0, "can_add": True, "add_only": True,
                    "note": "About 0.4 points of HbA1c, with little risk of lows."},
    "semaglutide": {"name": "Semaglutide (weekly)", "shift": -30.0, "dose_step": 0.0, "carb": 0.92, "can_add": True, "add_only": True,
                    "note": "About 1 point of HbA1c and smaller meal rises; may cause nausea."},
    "telmisartan": {"name": "Telmisartan", "note": "Protects the kidneys and lowers blood pressure; no direct effect on glucose."},
    "atorvastatin": {"name": "Atorvastatin", "note": "Lowers cholesterol; no direct effect on glucose."},
}
NAME_TO_KEY = {v["name"]: k for k, v in CATALOG.items()}


def key_of(name: str) -> str | None:
    return NAME_TO_KEY.get(name)


def active(key: str) -> bool:
    return "shift" in CATALOG[key]


def effect(key: str, action: str) -> dict:
    """Baseline shift (mg/dL), low-dip factor and meal factor for one action on one medicine."""
    c = CATALOG[key]
    shift = float(c.get("shift", 0.0))
    lows = c.get("lows")
    if action == "stop":
        return {"baseline_shift": -shift, "low_scale": lows[0] if lows else 1.0, "carb_scale": 1.0 / c.get("carb", 1.0)}
    if action == "dose_down":
        return {"baseline_shift": -shift * c["dose_step"], "low_scale": lows[1] if lows else 1.0, "carb_scale": 1.0}
    if action == "dose_up":
        return {"baseline_shift": shift * c["dose_step"], "low_scale": lows[2] if lows else 1.0, "carb_scale": 1.0}
    if action == "add":
        return {"baseline_shift": shift, "low_scale": 1.0, "carb_scale": c.get("carb", 1.0)}
    raise ValueError(f"unknown action {action!r}")


# Starting points for a medicine the doctor adds by hand. Typical average effects; the doctor can change the number.
SUGGESTIONS = [
    {"name": "Pioglitazone", "shift": -18.0, "lows": False}, {"name": "Gliclazide", "shift": -18.0, "lows": True},
    {"name": "Glipizide", "shift": -18.0, "lows": True}, {"name": "Empagliflozin", "shift": -14.0, "lows": False},
    {"name": "Vildagliptin", "shift": -12.0, "lows": False}, {"name": "Linagliptin", "shift": -12.0, "lows": False},
    {"name": "Liraglutide", "shift": -25.0, "lows": False}, {"name": "Insulin aspart (mealtime)", "shift": -20.0, "lows": True},
    {"name": "Acarbose", "shift": -8.0, "lows": False},
    {"name": "Prednisolone (a steroid raises glucose)", "shift": 25.0, "lows": False},
]
CUSTOM_LOW_FACTOR = 1.25     # a hand-added medicine marked "can cause lows" makes low dips 25% deeper
MAX_CUSTOM = 5


def clean_name(s: str) -> str:
    import re
    return re.sub(r"[\x00-\x1f<>]", "", s or "").strip()[:40]


def custom_effect(name: str, shift: float, lows: bool) -> dict:
    return {"key": "custom:" + name, "name": name, "action": "custom", "label": "Added by the doctor",
            "baseline_shift": round(float(shift), 3), "low_scale": CUSTOM_LOW_FACTOR if lows else 1.0, "carb_scale": 1.0}


def options(current_keys: set[str]) -> dict:
    """What can be changed for a patient who takes `current_keys`: per-medicine actions with their effects, and drugs that could be added."""
    cur = []
    for k in current_keys:
        c = CATALOG[k]
        acts = [] if not active(k) else [{"action": a, "label": LABEL[a], **effect(k, a)} for a in ("stop", "dose_down", "dose_up")]
        cur.append({"key": k, "name": c["name"], "glucose_active": active(k), "note": c["note"], "actions": acts})
    add = [{"key": k, "name": c["name"], "note": c["note"], **effect(k, "add")}
           for k, c in CATALOG.items() if c.get("can_add") and k not in current_keys]
    return {"current": cur, "can_add": add, "suggestions": SUGGESTIONS}


def combine(selected: dict[str, str], current_keys: set[str]) -> tuple[float, float, float, list[dict]]:
    """Sum the effects of the chosen changes. Returns (baseline shift, low-dip factor, meal factor, per-medicine breakdown)."""
    shift, low, carb, rows = 0.0, 1.0, 1.0, []
    for k, a in selected.items():
        if k not in CATALOG:
            raise ValueError(f"unknown medicine {k!r}")
        if a not in ACTIONS:
            raise ValueError(f"unknown action {a!r} for {k}")
        if not active(k):
            raise ValueError(f"{CATALOG[k]['name']} has no glucose effect in this model")
        if (a == "add") == (k in current_keys):
            raise ValueError(f"cannot {a} {CATALOG[k]['name']} for this patient")
        e = effect(k, a)
        shift += e["baseline_shift"]
        low *= e["low_scale"]
        carb *= e["carb_scale"]
        rows.append({"key": k, "name": CATALOG[k]["name"], "action": a, "label": LABEL[a], **{x: round(y, 3) for x, y in e.items()}})
    return shift, low, carb, rows
