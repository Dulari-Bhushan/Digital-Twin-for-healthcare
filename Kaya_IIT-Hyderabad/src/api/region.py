"""Which country the demo is set in: Japan (default) or India.

The same app serves both. The region changes what is local: the emergency number (119 in Japan, 108 in India), a few food examples in
the English texts (rice and bread instead of rice and roti), the demo patients' names and the doctors' names in the reports.
Set it with KAYA_REGION=JP or KAYA_REGION=IN before starting the server. Languages are chosen separately by the patient.

Only fixed texts are rewritten, never numbers that come from the patient's data.
"""
from __future__ import annotations

import os
import re

REGION = os.environ.get("KAYA_REGION", "JP").strip().upper()
if REGION not in ("JP", "IN"):
    REGION = "JP"

EMERGENCY_NUMBER = {"JP": "119", "IN": "108"}[REGION]
_NUMBER_RE = re.compile(r"(?<!\d)(108|119)(?!\d)")        # not a digit on either side; \b would fail before Telugu and Kannada letters
_FOOD_SWAPS = {
    "JP": [("rice and roti", "rice and bread"), ("vegetables and dal", "vegetables and protein"), ("chapati instead of rice", "bread instead of rice"),
           ("for a wedding", "for a family wedding")],
    "IN": [],
}


def number(text: str) -> str:
    """The local emergency number in a fixed text (any language)."""
    return _NUMBER_RE.sub(EMERGENCY_NUMBER, text)


def localize(text: str) -> str:
    """A fixed English text with the local emergency number and food examples."""
    out = number(text)
    for a, b in _FOOD_SWAPS[REGION]:
        out = out.replace(a, b)
    return out
