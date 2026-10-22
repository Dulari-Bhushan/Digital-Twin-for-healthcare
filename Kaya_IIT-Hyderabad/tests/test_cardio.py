import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("lightgbm")
ROOT = Path(__file__).resolve().parents[1]
for sub in ("src/ingest", "src/models", "src/features"):
    sys.path.insert(0, str(ROOT / sub))
import cardio as C  # noqa: E402
import nightly as N  # noqa: E402
from cohort_v2 import build_cohort_v2  # noqa: E402
from synthetic_cohort import STEPS_PER_DAY, CohortConfig  # noqa: E402


@pytest.fixture(scope="module")
def cohort(tmp_path_factory):
    root = tmp_path_factory.mktemp("v2")
    build_cohort_v2(CohortConfig(n_patients=260, days=28, seed=21), root)
    return root


@pytest.fixture(scope="module")
def dataset(cohort):
    return C.build_dataset(cohort)


def test_cycle_table_uses_only_past_data():
    """Cycle k ends at 10:00 on day k, so changing later data cannot change it."""
    rng = np.random.default_rng(0)
    n = 10 * STEPS_PER_DAY
    arrs = [rng.normal(m, 3, n) for m in (150, 70, 40, 100)] + [rng.integers(0, 4, n)]
    a = N.cycle_table(*arrs, days=10)
    arrs2 = [x.copy() for x in arrs]
    for x in arrs2:
        x[6 * STEPS_PER_DAY + N.CYCLE_OFFSET + 1:] = 0
    b = N.cycle_table(*arrs2, days=10)
    assert np.allclose(a[:6], b[:6], equal_nan=True)
    assert np.isnan(a[0]).all()


def test_dataset_labels_and_censoring(dataset):
    assert dataset.y.mean() > 0.01
    assert dataset.k.min() >= C.FIRST_K
    assert {"rmssd_night_last", "rhr_delta", "sleep_h_trend", "age", "prior_cvd"} <= set(dataset.columns)
    pos = dataset[dataset.y == 1]
    assert (pos.hours_to_event > 0).all() and (pos.hours_to_event <= C.HORIZON_H).all()
    assert not dataset[C.wearable_columns(dataset)].isna().all().any()


def test_flag_beats_chance_and_clinical_rule(dataset):
    ids = np.array(sorted(dataset.patient_id.unique()))
    te_ids, tr_ids = ids[:60], ids[60:]
    tr, te = dataset[dataset.patient_id.isin(tr_ids)], dataset[dataset.patient_id.isin(te_ids)]
    flag = C.CardioFlag().fit(tr, inner_folds=3)
    p = flag.predict(te)
    from sklearn.metrics import roc_auc_score
    auc = roc_auc_score(te.y, p)
    assert auc > 0.7
    assert auc > roc_auc_score(te.y, C.rule_score(te)) - 0.02
    assert ((p > 0) & (p < 1)).all()


def test_explanations_name_both_streams(dataset):
    ids = np.array(sorted(dataset.patient_id.unique()))
    tr = dataset[dataset.patient_id.isin(ids[40:])]
    flag = C.CardioFlag().fit(tr, inner_folds=3)
    pos = dataset[(dataset.y == 1) & dataset.patient_id.isin(ids[:40])].head(20)
    ex = flag.explain(pos, top=5)
    assert len(ex) == len(pos)
    assert all(d["push"] > 0 and d["label"] and d["stream"] in ("wearable", "record", "glucose") for e in ex for d in e)
    assert any(d["stream"] == "wearable" for e in ex for d in e)


def test_save_and_load_roundtrip(dataset, tmp_path):
    ids = np.array(sorted(dataset.patient_id.unique()))
    flag = C.CardioFlag().fit(dataset[dataset.patient_id.isin(ids[30:])], inner_folds=3)
    C.save_flag(flag, 0.2, tmp_path / "f.joblib")
    flag2, thr = C.load_flag(tmp_path / "f.joblib")
    te = dataset[dataset.patient_id.isin(ids[:30])]
    assert thr == 0.2
    assert np.allclose(flag.predict(te), flag2.predict(te))


def test_alert_replay_counts(dataset):
    te = dataset[dataset.patient_id.isin(sorted(dataset.patient_id.unique())[:80])]
    perfect = te.y.to_numpy().astype(float)                         # an oracle must catch every event
    r = C.alert_replay(te, perfect, 0.5)
    assert r["events"] > 0 and r["sensitivity"] > 0.95
    never = C.alert_replay(te, np.zeros(len(te)), 0.5)
    assert never["sensitivity"] == 0 and never["alerts"] == 0


def test_describe_is_plain_language():
    assert describe_ok("rmssd_night_delta") and describe_ok("steps24_trend") and describe_ok("age")


def describe_ok(name: str) -> bool:
    text = C.describe(name)
    return bool(text) and "_" not in text


def test_stream_of_names_the_glucose_sensor():
    assert C.stream_of("hypo_min_last", True) == "glucose" and C.stream_of("glu_cv_mean7", True) == "glucose"
    assert C.stream_of("rmssd_night_delta", True) == "wearable" and C.stream_of("age", False) == "record"


def test_hypoglycemia_features_and_usable_nights(dataset):
    assert {"hypo_min_last", "hypo_deep_min_mean7", "glu_min_delta", "n_nights"} <= set(dataset.columns)
    assert (dataset.n_nights == 7).all()                         # a clean cohort has every night
    assert (dataset.hypo_deep_min_last.fillna(0) <= dataset.hypo_min_last.fillna(0)).all()   # below 54 is inside below 70


def test_degrade_blanks_days_and_keeps_the_glucose_sensor(cohort):
    import pandas as pd
    ts = pd.read_parquet(cohort / "timeseries.parquet")
    ts = ts[ts.patient_id.isin(ts.patient_id.unique()[:20])]
    d = C.degrade(ts, 0.4, 0.0, seed=1)
    assert d.glucose.notna().all() and d.heart_rate.isna().mean() > 0.2
    assert len(d) == len(ts)
    pat = pd.read_parquet(cohort / "patients.parquet")
    eps = pd.read_parquet(cohort / "episodes.parquet")
    ds = C.dataset_from(pat, d, eps)
    assert ds.n_nights.min() < 7 and ds.n_nights.max() <= 7      # the dataset still builds, with fewer usable nights


def test_thin_record_is_filled_with_the_average_patient(dataset):
    ids = np.array(sorted(dataset.patient_id.unique()))
    flag = C.CardioFlag().fit(dataset[dataset.patient_id.isin(ids[40:])], inner_folds=3)
    te = dataset[dataset.patient_id.isin(ids[:40])].copy()
    blank = te.copy()
    blank[C.STATIC] = np.nan
    p = flag.predict(blank)
    assert np.isfinite(p).all() and ((p > 0) & (p < 1)).all()
    avg = te.copy()
    avg[C.STATIC] = flag.static_med.to_numpy()
    assert np.allclose(p, flag.predict(avg))                     # blank = the median patient, nothing more


def test_gap_augmented_puts_clean_rows_first(cohort, dataset):
    import pandas as pd
    pat, eps = pd.read_parquet(cohort / "patients.parquet"), pd.read_parquet(cohort / "episodes.parquet")
    ts = pd.read_parquet(cohort / "timeseries.parquet")
    ts = ts[ts.patient_id.isin(sorted(ts.patient_id.unique())[:15])]
    clean = C.dataset_from(pat, ts, eps)
    aug = C.gap_augmented(pat, ts, eps, clean)
    assert len(aug) == len(clean) * (1 + len(C.AUGMENT))
    assert (aug.iloc[:len(clean)].y.to_numpy() == clean.y.to_numpy()).all()
    assert (aug.iloc[len(clean):].groupby("patient_id").n_nights.mean() < 7).any()
