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
| Liver labels | NHANES 2017-2018 (FibroScan, ALT/AST, lipids, diet) | 16 files downloaded; liver dataset built (4,745 adults, 901 with diabetes) |
| Retina images | APTOS 2019, IDRiD, EyePACS | pending (needs account) |
| Kidney | NHANES eGFR/UACR | downloaded with the above |
| Notes | LLM-generated Indian-context clinical notes | pending |
| Genetics | Synthetic, published allele frequencies (PNPLA3, TCF7L2) | in cohort generator |

**Bridged synthetic cohort.** No dataset links one person's CGM and wearables to liver, eye and kidney outcomes, so `src/ingest/synthetic_cohort.py` simulates one. Its marginals follow Indian T2D epidemiology and its organ labels follow documented risk relationships. Each module is then validated separately on real data. This is stated openly in the README.

## 5. Models

- **Glucose forecaster:** LSTM/TCN or small transformer with static EHR embeddings and quantile outputs, with a LightGBM baseline.
- **Liver:** gradient boosting for steatosis/fibrosis risk from rolling 30-90 day CGM features, diet, labs, plus clinical-text features from synthetic notes.
- **Eye:** EfficientNet DR grader with Grad-CAM, plus a progression model using glycemic variability, time in range, BP and duration, with a concept-bottleneck explanation chain. **Illustrative retina preview (committed feature):** the progression model predicts the patient's likely DR grade at 2 years; a grade-conditioned generative model (ordinal diffusion or conditional image-to-image, trained on APTOS/IDRiD) renders a fundus image at that grade for a baseline scan. It is always labelled "illustrative preview, not a clinical prediction". We make no physical shear-stress claims, because no open data supports them.
- **Kidney:** eGFR slope and albuminuria risk.
- **What-if engine:** edit inputs, re-run simulator and forecaster, report change in glucose and 1-year organ risk.

## 5a. Results so far

- **Glycemic core** (`results/glucose_metrics.json`, `results/glucose_polish.json`): on held-out real CGMacros subjects the ensemble reaches 12.6/21.1/28.2 mg/dL RMSE at 30/60/120 min (persistence 16.3/25.8/36.7), with conformal 80% intervals and calibrated event heads. Alert replay at about 1 false alert per patient-day catches 72% of hypoglycemia episodes with a 45 minute median lead.
- **Static liver model** (`results/liver_static_metrics.json`): on real NHANES 2017-2018, advanced fibrosis (LSM >= 8 kPa) AUROC 0.83 versus 0.63 for FIB-4; steatosis (CAP >= 288 dB) AUROC 0.83 versus 0.82 for FLI and 0.79 for HSI. Similar performance in adults with diabetes (0.76 steatosis, 0.80 fibrosis) and in Asian participants.

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

## 11. Workflow and what each module tells the doctor

Data in (static EHR, wearables, retina scan) -> patient state encoder -> glucose, liver, eye and kidney modules -> what-if engine -> doctor dashboard, patient view, FHIR API and PDF report.

| Module | Question it answers | Output |
|---|---|---|
| Glucose | What will glucose do in the next 2 hours, and is an event coming? | 30/60/120 min forecast with 80% interval; calibrated hypo/hyper alerts with lead time |
| Liver | How much metabolic load is the liver carrying, and is fibrosis developing? | Steatosis and advanced-fibrosis risk; rolling 30-90 day liver-fat state driven by CGM (dynamic part: next) |
| Eye | What is the retinopathy grade, and where is it heading? | DR grade with Grad-CAM; 2-year progression risk; illustrative retina preview |
| Kidney | Is kidney function declining? | eGFR slope and albuminuria risk (stretch) |
| What-if | If this patient changes X, what happens? | Before/after glucose curve and 1-year organ risk change |

## 12. Progress snapshot (2026-10-18)

| Workstream | Weight | Done | Notes |
|---|---|---|---|
| Setup, repo, server | 5% | 100% | venv, GPU stack, license, scaffold |
| Data layer | 8% | 55% | CGMacros, NHANES, synthetic cohort done; Synthea EHR, synthetic notes, retina images pending |
| Glucose core | 14% | 90% | ensemble, calibration, alert replay done; only polish left |
| Liver | 14% | 45% | static NHANES model done; dynamic state, NLP features, what-if hooks pending |
| Eye | 14% | 0% | blocked on Kaggle token and IDRiD download |
| Kidney | 4% | 0% | stretch |
| What-if engine | 8% | 0% | |
| Patient state, API, FHIR | 9% | 0% | |
| Dashboard | 12% | 0% | |
| Docs and media | 8% | 15% | plan and README skeleton |
| Hardening (CI, Docker, tests) | 4% | 10% | two tests |
| **Overall** | 100% | **about 30%** | model work is further along than product work |

## 13. V1 scope (6-hour build) and V2 backlog

Anything in V2 is deliberately deferred so V1 ships complete. If time remains after V1, take V2 items in the order listed.

### V1: must ship

| Item | Status |
|---|---|
| Glucose forecaster, calibrated alerts, lead-time analysis | Done |
| Static liver model (NHANES) and dynamic liver state | Done |
| What-if engine (carbs, walking, baseline shift) | Done |
| FastAPI backend: patient list, twin state, forecast, what-if, replay | Next |
| React dashboard: doctor view (triage list, twin view, what-if panel, alert timeline) | Next |
| Patient view in English: outlook, one nudge, simple organ visuals | Next |
| Eye module: EfficientNet DR grader trained on APTOS, tested on IDRiD, Grad-CAM, tabular progression risk | After data download |
| Docker Compose one-command demo | V1 end |
| README, architecture diagram (PDF), presentation (PDF), video script | V1 end |

### V2 backlog: add if time allows, in priority order

1. Illustrative generative retina preview (grade-conditioned image generation, clearly labelled illustrative)
2. (done) Kidney module: NHANES risk model, eGFR path, what-if
3. PDF clinical summary export from the doctor view
4. Patient view in Hindi, Telugu and Kannada
5. Model-health page (drift, performance) and access audit log
6. Authentication and role-based access (doctor, patient, admin)
7. Fuller FHIR R4 coverage (DiagnosticReport, Condition) and a mocked ABDM consent flow
8. Synthea EHR and synthetic clinical notes with a clinical-text encoder for the liver module
9. SHAP explanations surfaced in the dashboard
10. Use the Shanghai T2DM dataset for an extra external check of the glucose model
11. Finer alert-threshold tuning for rare hypoglycemia on the synthetic cohort
12. GitHub Actions CI
13. Subgroup performance analysis (age, sex, ethnicity) in model cards
14. Real-data validation of the CGM-to-liver link, if a suitable dataset becomes available

The README marks V1 versus later items so nothing is claimed that is not built.
