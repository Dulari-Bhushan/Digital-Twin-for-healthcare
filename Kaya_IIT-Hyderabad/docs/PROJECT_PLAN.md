# Kaya: Project Plan

Multi-organ digital twin for Type 2 Diabetes. Team Kaya, IIT Hyderabad (Dulari Bhushan, Prateek Giddaplavar).

## 1. Concept

Most diabetes twins forecast glucose. Kaya simulates what glucose does to the **liver, eyes and kidneys** and lets a doctor test an intervention on the virtual patient before trying it on the real one. Built as a client-grade product, not a throwaway proof of concept.

Use case: Indian T2D patients on routine follow-up. They are often lean-but-fatty, eat a high-carbohydrate diet, and carry a high burden of silent MASLD and retinopathy that is usually found late.

## 2. Scope and order

1. Glycemic core: glucose forecast 30/60/120 min ahead, hyper/hypoglycemia event flags
2. Liver module: MASLD to MASH fibrosis risk
3. Eye module: diabetic retinopathy grade and progression risk
4. Kidney module: eGFR decline and albuminuria risk (only if time allows)
5. What-if engine: change meals, activity, sleep or medication, see the effect on glucose and organ risk
6. Clinician dashboard (React) and patient-facing view

## 3. Architecture

- **Data layer:** static EHR stream (demographics, labs, genetics, notes) and dynamic wearable stream (CGM, heart rate, HRV, sleep, steps).
- **Patient state encoder:** per-patient latent state fusing both streams, with slow variables (HbA1c trend, liver fat, retinal risk, eGFR) and fast variables (glucose, heart rate, sleep).
- **Model layer:** glucose forecaster, organ modules, counterfactual engine.
- **Experience layer:** FastAPI backend, React dashboard, explanations and uncertainty on every alert.

## 4. Data (open or synthetic only)

| Need | Source | Status |
|---|---|---|
| CGM, meals, wearables | CGMacros (PhysioNet), Shanghai T1DM/T2DM | CGMacros downloaded and checksum verified; Shanghai pending |
| Synthetic CGM | simglucose | installed |
| EHR | Synthea (diabetes module) | pending |
| Liver labels | NHANES 2017-2018 (FibroScan, ALT/AST, lipids, diet) | 14 files downloaded |
| Retina images | APTOS 2019, IDRiD, EyePACS | pending (needs account) |
| Kidney | NHANES eGFR/UACR | downloaded with the above |
| Notes | LLM-generated Indian-context clinical notes | pending |
| Genetics | Synthetic, published allele frequencies (PNPLA3, TCF7L2) | in cohort generator |

**Bridged synthetic cohort.** No dataset links one person's CGM and wearables to liver, eye and kidney outcomes, so `src/ingest/synthetic_cohort.py` simulates one. Its marginals follow Indian T2D epidemiology and its organ labels follow documented risk relationships. Each module is then validated separately on real data. This is stated openly in the README.

## 5. Models

- **Glucose forecaster:** LSTM/TCN or small transformer with static EHR embeddings and quantile outputs, with a LightGBM baseline.
- **Liver:** gradient boosting for steatosis/fibrosis risk from rolling 30-90 day CGM features, diet, labs, plus clinical-text features from synthetic notes.
- **Eye:** EfficientNet DR grader with Grad-CAM, plus a progression model using glycemic variability, time in range, BP and duration, with a concept-bottleneck explanation chain.
- **Kidney:** eGFR slope and albuminuria risk.
- **What-if engine:** edit inputs, re-run simulator and forecaster, report change in glucose and 1-year organ risk.

## 6. Validation

- Split by patient, never by row
- Calibration reported alongside accuracy
- Ablations: EHR-only vs wearable-only vs fused, to prove the fusion claim
- Simulated prospective replay of held-out patients: alert lead time and false-alarm rate
- Limitations and ethics section (DPDP, synthetic-data caveats, decision support not diagnosis)

## 7. Product-grade requirements

- FHIR R4 resources in and out; ABDM-aware design (mocked in demo)
- DPDP-by-design: consent records, data minimisation, access audit log
- Versioned REST API with OpenAPI, authentication, role-based access
- Model cards, drift monitoring, "model health" page
- Tests, CI, Docker Compose one-command start, structured logging, reproducible experiments
- Doctor workspace with triage list, twin view, what-if panel, alert timeline, PDF clinical summary
- Patient view in English, Hindi, Telugu and Kannada; accessible, responsive, light/dark
- Live replay mode as the headline demo moment

## 8. Phases

| Phase | Output |
|---|---|
| 0. Setup | Repo, server environment, architecture sketch (done) |
| 1. Data | Downloads, synthetic cohort, NHANES processing (in progress) |
| 2. Glycemic core | Forecaster, baselines, metrics |
| 3. Liver | Fibrosis model, NLP features, ablations |
| 4. Eye (then kidney) | DR grader, progression risk |
| 5. What-if and API | Counterfactual engine, FastAPI |
| 6. Dashboard | Doctor and patient UI |
| 7. Documentation and media | README, architecture PDF, slides, 20+ minute video |
| 8. Hardening | Docker, tests, cleanup |

## 9. Compute

SSH host `lab-server`: 3x RTX A5000 (24 GB), Python 3.11 venv at `~/kaya/.venv`, torch 2.4.1+cu121. Shared lab machine. PyPI is slow from the server; use `PIP_INDEX` with a mirror (see `scripts/server_bg.sh`). PhysioNet's own file server is throttled; use its S3 mirror (see `scripts/fetch_data.py`).

## 10. Submission checklist

- [ ] README: team and college, title, problem and use case, stack and model details, video link, license, architecture and presentation links
- [ ] Architecture diagram (PDF)
- [ ] Presentation (PDF)
- [ ] Video of at least 20 minutes (unlisted YouTube or slides recording)
- [x] Apache-2.0 license
- [x] Folder named `Kaya_IIT-Hyderabad`
