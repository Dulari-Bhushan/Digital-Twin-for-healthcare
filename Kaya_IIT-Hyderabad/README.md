# Kaya: A Multi-Organ Digital Twin for Type 2 Diabetes

> Other digital twins forecast glucose. Kaya simulates what glucose does to the liver, eyes and kidneys, and lets a doctor test an intervention on the virtual patient before trying it on the real one.

*Submission to the Happiest Health "Reimagining and Reforming Healthcare in India" Summit 2026, Digital Twin Challenge (Phase 1).*

## Team

| Name | Role |
|---|---|
| Dulari Bhushan | _TBD_ |
| Prateek Giddaplavar | _TBD_ |

**Institution:** Indian Institute of Technology Hyderabad (IIT Hyderabad)
**Team / product name:** Kaya

## Problem statement and healthcare use case

_To be written: India's T2D burden, silent MASLD and retinopathy, late detection, the gap in current twins that stop at glucose._

## What Kaya does

1. **Glycemic core**: forecasts glucose 30/60/120 minutes ahead and flags hyper/hypoglycemic events.
2. **Liver module**: rolling MASLD to MASH fibrosis risk.
3. **Eye module**: diabetic retinopathy grade and progression risk, with an explainable pathway.
4. **Kidney module** (roadmap): eGFR decline and albuminuria risk.
5. **What-if engine**: change meals, activity, sleep or medication and see the effect on glucose and organ risk.
6. **Clinician dashboard**: triaged patient list, twin view, alert timeline, explanations and uncertainty.

## Data (all open or synthetic)

_To be written: CGMacros, Shanghai T1DM/T2DM, Synthea, NHANES, APTOS/IDRiD, simglucose, synthetic notes and genetics. No real patient data is used (DPDP Act / HIPAA)._

## Architecture

_Diagram to be added in `docs/` (PDF)._

## Technical stack

_To be finalised: Python, PyTorch, LightGBM, FastAPI, React, Docker._

## Quick start

_To be written: one-command demo via Docker Compose._

## Demo video and presentation

_Links to be added._

## Limitations and ethics

_To be written: synthetic bridged cohort, decision support not diagnosis, subgroup performance._

## License

Apache License 2.0. See [LICENSE](LICENSE).
