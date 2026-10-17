import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "ingest"))
from synthetic_cohort import STEPS_PER_DAY, CohortConfig, build_cohort  # noqa: E402


def test_cohort_shapes_and_ranges(tmp_path):
    cfg = CohortConfig(n_patients=40, days=3, seed=7)
    build_cohort(cfg, tmp_path)
    p = pd.read_parquet(tmp_path / "patients.parquet")
    ts = pd.read_parquet(tmp_path / "timeseries.parquet")

    assert len(p) == 40
    assert len(ts) == 40 * 3 * STEPS_PER_DAY
    assert ts.glucose.between(40, 400).all()
    assert p.hba1c.between(5.8, 14).all()
    assert set(p.dr_grade.unique()) <= {0, 1, 2, 3, 4}
    # Mechanistic sanity: higher HbA1c patients have higher mean CGM glucose.
    assert np.corrcoef(p.hba1c, p.mean_glucose)[0, 1] > 0.9


def test_cohort_is_reproducible(tmp_path):
    cfg = CohortConfig(n_patients=10, days=2, seed=3)
    build_cohort(cfg, tmp_path / "a")
    build_cohort(cfg, tmp_path / "b")
    a = pd.read_parquet(tmp_path / "a" / "patients.parquet")
    b = pd.read_parquet(tmp_path / "b" / "patients.parquet")
    pd.testing.assert_frame_equal(a, b)
