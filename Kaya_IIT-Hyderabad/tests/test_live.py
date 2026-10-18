import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))
from live import Calibration, LiveTwin, NumpyGRU  # noqa: E402

MODEL = ROOT / "artifacts" / "model"


def test_numpy_gru_matches_torch_reference():
    ref = json.loads((MODEL / "reference.json").read_text())
    net = NumpyGRU(MODEL / "gru_numpy.npz")
    for x, s, q, lg in zip(ref["x"], ref["s"], ref["q"], ref["logits"]):
        qn, ln = net.forward(np.array(x), np.array(s))
        # torch runs in float32, numpy in float64: agreement to about 1e-3 is exact for our purposes
        assert np.allclose(qn, np.array(q), atol=1e-3)
        assert np.allclose(ln, np.array(lg), atol=2e-3)


def test_live_twin_needs_a_full_window_then_forecasts():
    twin = LiveTwin(NumpyGRU(MODEL / "gru_numpy.npz"), Calibration(MODEL / "calibration.json"),
                    {"age": 55, "bmi": 27, "hba1c": 8.0, "sex": "F"})
    out = None
    for i in range(30):
        out = twin.push(150 + 20 * np.sin(i / 4), 72, 0, 0, (i * 5) % 1440)
        if i < 23:
            assert out is None
    assert out is not None and np.array(out["q"]).shape == (3, 3)
    lo, md, hi = np.array(out["q"])[:, 0], np.array(out["q"])[:, 1], np.array(out["q"])[:, 2]
    assert (lo <= md).all() and (md <= hi).all()
    assert 0.0 <= out["p_hyper"] <= 1.0 and out["inference_ms"] < 100
