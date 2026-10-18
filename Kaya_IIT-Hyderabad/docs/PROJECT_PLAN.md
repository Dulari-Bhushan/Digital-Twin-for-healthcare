# Kaya: Project Plan and Status

Multi-organ digital twin for Type 2 Diabetes. Team Kaya, IIT Hyderabad (Dulari Bhushan, Prateek Giddaplavar). The main README is at the repository root.

## 1. Concept

Most diabetes twins forecast glucose. Kaya simulates what glucose does to the **liver, eyes and kidneys** and lets a doctor test an intervention on the virtual patient before trying it on the real one.

Use case: Indian T2D patients on routine follow-up, who often carry silent fatty liver and retinopathy that is usually found late.

## 2. Architecture

- **Data layer:** static EHR stream (demographics, labs, genetics, notes) and dynamic wearable stream (CGM, heart rate, HRV, sleep, steps).
- **Patient state:** per-patient state fusing both streams, with slow variables (HbA1c trend, liver fat, retinal risk, eGFR) and fast variables (glucose, heart rate, sleep).
- **Model layer:** glucose forecaster, liver, eye and kidney modules, what-if engine.
- **Experience layer:** FastAPI backend, React dashboard (doctor, patient, admin), FHIR read endpoints, PDF reports, optional voice assistant.

Diagrams: `architecture_2page.pdf`, `architecture_overview.svg`, `architecture_detail.svg`.

## 3. Status

| Component | Status |
|---|---|
| Data pipelines and synthetic cohort | Built |
| Glucose forecaster, calibrated alerts, lead-time analysis | Built |
| Liver module (static NHANES model and dynamic state) | Built |
| Kidney module (risk and eGFR path) | Built |
| Eye module (grader, Grad-CAM, progression risk) | Built |
| What-if engine | Built |
| REST API, FHIR read endpoints, PDF reports | Built |
| Doctor, patient and admin dashboards | Built |
| Four-language patient app and voice assistant | Built (language review pending) |
| Patient report uploads with consent before AI reading | Built |
| Tests (84), CI, Docker Compose | Built |
| Illustrative retina preview | Planned |
| Synthea-based EHR and generated clinical notes | Planned |
| Authentication, role-based access | Planned |
| Fuller FHIR and ABDM coverage | Planned |

## 4. Validation approach

- Split by patient, never by row
- Calibration reported alongside accuracy
- Every module compared with a standard score or simple baseline (FIB-4, FLI, HSI, persistence, age/BP/HbA1c)
- Simulated prospective replay of held-out patients: alert lead time and false-alarm rate
- Limitations and ethics stated up front (DPDP, synthetic-data caveats, decision support not diagnosis)

Results are in `results/` and summarised in the README and `MODEL_CARDS.md`.

## 5. Roadmap

1. **Illustrative retina preview.** The progression model predicts the likely grade at 2 years; a grade-conditioned generative model renders a fundus image for the baseline scan. Always labelled "illustrative preview, not a clinical prediction". No physical shear-stress claims, because no open data supports them.
2. **Safer access.** Authentication, role-based access, and an audit log that survives restarts.
3. **Wider data.** Synthea EHR, Shanghai T1DM/T2DM CGM, EyePACS; native-speaker review of the Hindi, Telugu and Kannada text.
4. **Interoperability.** Fuller FHIR coverage (Condition, DiagnosticReport) and ABDM integration.
5. **Prospective validation** with a clinical partner.

## 6. Compute

Training ran on a shared lab server with 3 × RTX A5000 (24 GB), Python 3.11, PyTorch 2.4.1 with CUDA 12.1. See `scripts/setup_server.sh` and `scripts/server_bg.sh`. PhysioNet's own file server is throttled, so `scripts/fetch_data.py` uses its S3 mirror. The demo needs no GPU.
