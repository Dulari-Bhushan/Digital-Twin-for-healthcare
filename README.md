# Kaya

### A Multi-Organ Digital Twin for Type 2 Diabetes

> Other digital twins forecast glucose. **Kaya shows what glucose does to the liver, eyes and kidneys**, and lets a doctor test a change on the virtual patient before trying it on the real one.

*Submission to the Happiest Health "Reimagining and Reforming Healthcare in India" Summit 2026, Digital Twin Challenge, Phase 1.*

![CI](https://github.com/Dulari-Bhushan/Digital-Twin-for-healthcare/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Data](https://img.shields.io/badge/data-open%20%2B%20synthetic%20only-green)
![Tests](https://img.shields.io/badge/tests-116%20passing-brightgreen)

![Kaya doctor workspace](Kaya_IIT-Hyderabad/docs/img/doctor_view.png)

---

## Submission at a glance

| Required item | Where it is |
|---|---|
| Team details | [Team](#team) |
| College / incubator information | [Team](#team) |
| Project title | Above: **Kaya, A Multi-Organ Digital Twin for Type 2 Diabetes** |
| Problem statement | [1. The problem](#1-the-problem) |
| Healthcare use case | [2. Healthcare use case](#2-healthcare-use-case) |
| Phase 1 requirements (two data streams, adverse-event prediction, dashboard, open data) | [Phase 1 requirements and how Kaya meets them](#phase-1-requirements-and-how-kaya-meets-them) |
| Technical stack | [7. Technical stack](#7-technical-stack) |
| AI/ML model or framework details | [6. AI/ML models and results](#6-aiml-models-and-results) and [`MODEL_CARDS.md`](Kaya_IIT-Hyderabad/docs/MODEL_CARDS.md) |
| Demo video (unlisted YouTube) | [12. Demo video and documents](#12-demo-video-and-documents) |
| Open-source license | [14. License](#14-license), file [`LICENSE`](Kaya_IIT-Hyderabad/LICENSE) |
| Architecture diagram (PDF) | [`architecture_2page.pdf`](Kaya_IIT-Hyderabad/docs/architecture_2page.pdf) |
| Presentation (PDF / PPT) | [`Kaya_presentation.pdf`](Kaya_IIT-Hyderabad/docs/Kaya_presentation.pdf), [`Kaya_pitch_deck.pptx`](Kaya_IIT-Hyderabad/docs/Kaya_pitch_deck.pptx) |

---

## Team

| | |
|---|---|
| **Team / product** | Kaya |
| **Members** | Dulari Bhushan, Prateek Giddaplavar |
| **College** | Indian Institute of Technology Hyderabad (IIT Hyderabad) |
| **Incubator** | None; this is a student team project |

---

## What is new in Kaya

| | Novelty | Why it matters |
|---|---|---|
| 1 | **One twin for four organs, not one signal.** The continuous glucose stream feeds a liver, an eye and a kidney module, so the twin shows the organ damage that glucose causes, not just the next spike. | Diabetes harms the organs silently for years; today they are checked once a year, if at all. To our knowledge, no other diabetes twin we reviewed links glucose to organ outcomes. |
| 2 | **Two data streams, fused, for two adverse events.** Glucose is forecast from CGM, heart rate, activity, meals, HRV, sleep and a fuller record (medicines, genetics). A new **Heart watch** reads a week of sleep, heart rate, HRV and glucose lows together with the record and flags a cardiovascular event up to 72 hours ahead, and says "not enough data" instead of guessing when the watch was off. Each input group is switched on and off in an ablation, with confidence intervals. | The brief asks for fusion of the record and the wearable. We measure what each stream adds instead of asserting it: medicines lift low-glucose AUROC from 0.85 to 0.95; a week of wearable data flags 71% of cardiovascular events a median 22 hours ahead at about one false alert per patient-month, and the stress tests show what happens with missing days or no record. Where a stream adds little (HRV and sleep for glucose), we say so. |
| 3 | **A what-if engine that reaches the organs.** Change a meal, add a walk, improve sleep or alter a medicine, and Kaya re-runs the twin and shows the change in the glucose curve *and* in one-year liver, eye and kidney risk. | A doctor can test a plan on the virtual patient first. Outputs are labelled simulations with editable assumptions. |
| 4 | **Every module is validated on real data, and benchmarked against the standard score.** Liver against FIB-4, FLI and HSI on 4,745 NHANES adults; glucose on real CGMacros recordings; retinopathy on the Indian IDRiD set. | Honest numbers with baselines. Where the model adds little (kidney), we say so. |
| 5 | **Trustworthy uncertainty.** Conformal 80% intervals that really cover 80%, and isotonic-calibrated event probabilities (expected calibration error 0.003 to 0.005). | A forecast is only useful if the doctor knows how sure it is. |
| 6 | **Real-time on a laptop.** The glucose model runs on every 5-minute reading in about 1 ms in pure numpy, with no GPU, so live mode works anywhere. | Deployable in a small clinic. |
| 7 | **Explainable by design.** Every alert shows why it fired; SHAP shows what drives each liver and kidney risk; Grad-CAM shows where the retina model looked. | Doctors can check the reasoning instead of trusting a number. |
| 8 | **Built for India.** The retina grader is fine-tuned and tested on Indian IDRiD images; the patient app runs in English, Hindi, Telugu and Kannada with voice (Sarvam AI); lab reports are read in Indian layouts (SGPT/SGOT, lakh/cumm); FHIR R4 endpoints for ABDM-aware integration. | Reach beyond English-speaking, urban users. |
| 9 | **A safe assistant, with the rules in code.** Emergency words get a fixed "call 108" reply; medicine and dose questions are sent to the doctor; any model reply containing dose advice is replaced. These checks run in code, before and after the language model. | Safety does not depend on the model behaving well. |
| 10 | **Patient reports are never read without a yes.** A patient can upload a PDF or photo of a report. The AI reads it only after the patient agrees, shows a summary, and the doctor sees every upload marked "not verified". The parser is rule-based, so every number traces to a line of the document. | Consent and traceability, with nothing invented. |
| 11 | **Run like a product.** Admin page with health, model inventory, latency, audit trail and a one-click self-test; tests and CI; Docker Compose; honest model cards. | Reviewers can see what runs and how it was checked. |

---

## Phase 1 requirements and how Kaya meets them

The Phase 1 brief asks for a working prototype that fuses a static record with a wearable time series, predicts an adverse event ahead of time, shows a doctor dashboard, and uses only open, anonymised or synthetic data. Each requirement below points to the evidence in this repository.

| Requirement | Met? | Evidence in this repository |
|---|---|---|
| **Static / historical stream** (demographics, diagnoses, labs, genetic markers) | Yes | The synthetic cohort generators [`synthetic_cohort.py`](Kaya_IIT-Hyderabad/src/ingest/synthetic_cohort.py) and [`cohort_v2.py`](Kaya_IIT-Hyderabad/src/ingest/cohort_v2.py) create, per patient: age, sex, BMI, waist, diabetes duration, medicines (metformin, insulin or sulfonylurea), HbA1c, blood pressure, HOMA-IR, carbohydrate share of diet, LDL, smoking, prior cardiovascular disease, and the **PNPLA3** and **TCF7L2** genetic markers (allele frequencies set for Indian populations). Organ labels (liver fat and fibrosis, retinopathy grade, eGFR, urine albumin) follow documented risk relationships. The demo patients also carry lab panels, retinal and liver scans, ECG, foot exam and clinic notes ([`reports.py`](Kaya_IIT-Hyderabad/src/api/reports.py)). Real labelled data: NHANES 2017-2018 for liver and kidney. |
| **Dynamic stream** (CGM, HRV, sleep, steps from wearables) | Yes | The same generators produce a 5-minute time series per patient: **glucose, heart rate, HRV (RMSSD), sleep stages, steps and meals**. In the coupled cohort (`cohort_v2.py`, 2,000 patients, 28 days) these streams share one physiology: a hidden autonomic load lowers HRV, raises resting heart rate, shortens sleep, lowers steps and raises glucose; short sleep raises next-day insulin resistance; TCF7L2 risk alleles enlarge post-meal rises; medicines and exercise raise the chance of a low. Cardiovascular events and benign look-alike episodes are layered on top. Real data: **CGMacros** (PhysioNet), 34 subjects with CGM, heart rate, activity and meal records. The live feed accepts new readings through `POST /api/live/{id}/reading` and a WebSocket. The glucose model used in the live demo is fed glucose, heart rate, activity and meal carbohydrates. The two-stream models described next also use HRV, sleep and the wider record. |
| **A working model that ingests both streams** | Yes | [`windows_v2.py`](Kaya_IIT-Hyderabad/src/models/windows_v2.py) builds each glucose input from a 2-hour window of six dynamic channels (glucose, heart rate, activity, meals, HRV, sleep stage), seven slow-context numbers (last night's sleep, HRV and resting heart rate and the 7-night averages) and a 20-number static vector (age, BMI, HbA1c, sex, time of day, duration, HOMA-IR, medicines, PNPLA3, TCF7L2). The GRU in [`glucose.py`](Kaya_IIT-Hyderabad/src/models/glucose.py) takes both streams, and [`ablate_glucose.py`](Kaya_IIT-Hyderabad/src/models/ablate_glucose.py) measures what each input group adds ([results](#fusing-the-two-streams-what-each-stream-adds)). The new [`cardio.py`](Kaya_IIT-Hyderabad/src/models/cardio.py) fuses a week of nightly wearable summaries with the static record. The liver, kidney and eye modules fuse static labs with wearable-derived glucose features. Trained in [`train_glucose.py`](Kaya_IIT-Hyderabad/src/models/train_glucose.py) and [`polish_glucose.py`](Kaya_IIT-Hyderabad/src/models/polish_glucose.py); metrics in [`results/glucose_metrics.json`](Kaya_IIT-Hyderabad/results/glucose_metrics.json) and [`glucose_polish.json`](Kaya_IIT-Hyderabad/results/glucose_polish.json). |
| **Predicts an adverse event in advance** (the brief's example: a glucose spike 2 hours ahead) | Yes | Forecasts glucose **30, 60 and 120 minutes ahead** with an 80% conformal interval, and the probability of a **high (> 180) or low (< 70) glucose event within 2 hours**. On real CGMacros data the ensemble reaches RMSE 12.6 / 21.1 / 28.2 mg/dL (persistence 16.3 / 25.8 / 36.7). Alert replay ([`alerts.py`](Kaya_IIT-Hyderabad/src/models/alerts.py)) streams a patient's week through the model: at about one false alert per patient-day, **72% of hypoglycemia episodes are caught with a median 45 minutes of warning**. Each alert states the reason it fired. **Second adverse event:** the Heart watch flags a **cardiovascular event within 72 hours** from a week of sleep, heart-rate and HRV data plus the record: AUROC 0.82 (95% CI 0.80 to 0.83), **71% of events caught with a median 22 hours of warning at about one false alert per patient-month**, against 41% for a simple clinical rule at the same false-alert rate. |
| **Conceptual UI dashboard for a doctor** | Yes, a working one | React dashboard in [`dashboard/`](Kaya_IIT-Hyderabad/dashboard/): triaged patient list, glucose twin with forecast band and a 3-day replay, liver, eye and kidney panels, what-if studio, what-changed-since-last-visit card, full patient record, alert timeline, PDF clinical summary, plus patient and admin views, and the **Heart watch** view inside the Doctor view (`?view=heart`): a month of nights replayed morning by morning, the wearable and record streams shown as dials that combine into one risk, the factors behind each alert, data-quality and confidence chips, a medicine check for lows on insulin or a sulfonylurea, and what actually happened. See the [screenshots](#3-screenshots). Run it with the steps in [10. Run the demo](#10-run-the-demo). |
| **Open, anonymised or synthetic data only** | Yes | CGMacros, NHANES, APTOS 2019 and IDRiD are open datasets; patients and wearable streams are generated by our own synthetic generator and simglucose. No real patient data is stored or processed. See [8. Data](#8-data). |
| **EHR source** (the brief suggests Synthea or MIMIC-IV, as examples) | Own generator instead | We used our own synthetic cohort generator, tuned to Indian T2D epidemiology, because it is the only way to link one person's glucose stream to organ outcomes. **Synthea is not used yet** and is listed as planned. MIMIC-IV is not used. |
| **Sensor source** (open datasets or synthetic streams) | Yes | Open dataset (CGMacros) plus synthetic streams that mimic consumer wearables and CGMs. |

**Where this is limited, stated plainly.**
- The live demo and the 24 demo patients still run the original four-channel glucose model. The model that also reads HRV, sleep and the wider record is evaluated offline in the ablation and is not yet in the live feed.
- For glucose, HRV and sleep add little in our synthetic data (about 0.3 mg/dL at 2 hours). The record adds more (medicines lift low-glucose AUROC from 0.85 to 0.95). The Heart watch is where the wearable stream matters most.
- The couplings between sleep, HRV, glucose and cardiovascular events in the synthetic cohort are literature-informed assumptions, and cardiovascular events are far more frequent in it than in real life, so precision figures would be lower at real-world rates.
- The links between glucose patterns and organ outcomes are simulated from documented relationships; each module's baseline model is validated on real data wherever real data exists (see [8. Data](#8-data) and [13. Limitations and roadmap](#13-limitations-and-roadmap)).

## 1. The problem

India has over 100 million people with diabetes. The disease is rarely fatal on its own. The damage comes from **complications that build silently for years**: fatty liver progressing to fibrosis, retinopathy that is found only after vision is lost, and declining kidney function.

Today a patient's glucose is tracked, but their organs are checked once a year, if at all. Existing diabetes "digital twins" and apps focus on **managing sugar**: forecasting spikes, coaching diet and lowering HbA1c. None of the products we reviewed connects the continuous glucose signal to the **organ damage it causes**, and none lets a doctor ask *"what happens to this patient's liver and eyes if we change X?"*

## 2. Healthcare use case

**Routine follow-up of Indian adults with Type 2 Diabetes.** These patients are often lean but carry fatty liver, eat a carbohydrate-heavy diet, and have a high burden of silent fatty liver disease and retinopathy that is usually found late.

Kaya builds a living virtual replica of each patient by fusing two data streams:

| Stream | Examples |
|---|---|
| **Static / historical** (EHR) | Demographics, diagnoses, lab results, genetic markers (PNPLA3, TCF7L2), clinical notes |
| **Dynamic / real time** (wearables) | Continuous glucose, heart rate, HRV (RMSSD), sleep window, steps, meals |

From that twin, five modules answer five clinical questions:

| Module | The question it answers | What the doctor gets |
|---|---|---|
| **Glucose** | What will glucose do in the next 2 hours, and is an event coming? | 30 / 60 / 120 minute forecast with an 80% interval; calibrated hypo- and hyperglycemia alerts with lead time |
| **Liver** | Is the liver carrying a heavy metabolic load, and is fibrosis developing? | Steatosis and advanced-fibrosis risk; a rolling liver-fat state driven by recent glucose |
| **Eye** | What is the retinopathy grade, and where is it heading? | DR grade with an explanation heatmap and a 2-year progression risk |
| **Kidney** | Is kidney function declining, and how fast? | Albuminuria and reduced-eGFR risk, plus a 5-year eGFR path |
| **Heart watch** | Is a cardiovascular event coming in the next 72 hours? | A morning risk from a week of sleep, heart rate and HRV read with the record, with an alert and the factors behind it |

On top sits the **what-if engine**, described above.

### Who uses it

| User | Goal | What they see |
|---|---|---|
| **Doctor / diabetologist** | Spot who needs attention today, understand why, and choose an intervention | A triaged patient list sorted by risk. For each patient: the glucose forecast with its uncertainty band, organ-risk panels with trends, an alert timeline with the reason each alert fired, the what-if panel, a what-changed-since-last-visit card and a one-click PDF clinical summary |
| **Patient** | Know what to do next and why it matters | A plain-language phone view in English, Hindi, Telugu and Kannada: one clear next action, today's glucose outlook, and how habits affect their liver and eyes |
| **Clinic administrator / IT** | Run the service safely and responsibly | An admin page with service health, model inventory, traffic, audit trail and a self-test |
| **Hospital IT / integrator** | Plug Kaya into existing systems | A versioned REST API with FHIR R4 read endpoints (Patient, Observation) |

## 3. Screenshots

**Doctor record.** Click any patient for the full record: glucose history, organ projections with their drivers, labs, alerts and reports.

<p>
  <img src="Kaya_IIT-Hyderabad/docs/img/rec_glucose.png" width="32%" alt="Glucose history and forecast" />
  <img src="Kaya_IIT-Hyderabad/docs/img/rec_liver.png" width="32%" alt="Liver projection and drivers" />
  <img src="Kaya_IIT-Hyderabad/docs/img/rec_eyes.png" width="32%" alt="Retinopathy grade and heatmap" />
</p>
<p>
  <img src="Kaya_IIT-Hyderabad/docs/img/rec_kidneys.png" width="32%" alt="Kidney risk and eGFR path" />
  <img src="Kaya_IIT-Hyderabad/docs/img/rec_alerts.png" width="32%" alt="Alert timeline with reasons" />
  <img src="Kaya_IIT-Hyderabad/docs/img/rec_diary.png" width="32%" alt="Adherence diary" />
</p>

**Heart watch.** A month of one patient's nights replayed morning by morning: the wearable pattern and the record risk shown as two dials that combine into one 72-hour risk, with the factors behind each alert.

<p>
  <img src="Kaya_IIT-Hyderabad/docs/img/heart_watch.png" width="70%" alt="Heart watch: alert morning with two dials, a week of nights and the drivers" />
</p>

**Patient app.** A plain-language phone view with today's habits, weekly time in range and a "try a change" simulator.

<p>
  <img src="Kaya_IIT-Hyderabad/docs/img/patient_view.png" width="24%" alt="Patient app: today" />
  <img src="Kaya_IIT-Hyderabad/docs/img/patient_insights.png" width="24%" alt="Patient app: insights" />
  <img src="Kaya_IIT-Hyderabad/docs/img/patient_try.png" width="24%" alt="Patient app: try a change" />
  <img src="Kaya_IIT-Hyderabad/docs/img/assistant_open.png" width="24%" alt="Voice and chat assistant" />
</p>

**Four languages.**

<p>
  <img src="Kaya_IIT-Hyderabad/docs/img/lang_hi.png" width="32%" alt="Hindi" />
  <img src="Kaya_IIT-Hyderabad/docs/img/lang_te.png" width="32%" alt="Telugu" />
  <img src="Kaya_IIT-Hyderabad/docs/img/lang_kn.png" width="32%" alt="Kannada" />
</p>

**Reports and operations.**

<p>
  <img src="Kaya_IIT-Hyderabad/docs/img/doc_changes.png" width="32%" alt="What changed since the last visit" />
  <img src="Kaya_IIT-Hyderabad/docs/img/pat_reports.png" width="32%" alt="Patient reports and uploads" />
  <img src="Kaya_IIT-Hyderabad/docs/img/admin_page.png" width="32%" alt="Admin page" />
</p>

## 4. How it works

```mermaid
flowchart TD
    A[Static EHR<br/>labs, genetics, notes] --> S
    B[Wearables<br/>CGM, heart rate, sleep, steps] --> S
    C[Retina scan<br/>fundus image] --> S
    S[Patient state encoder<br/>one fused twin per patient]
    S --> G[Glucose module]
    S --> L[Liver module]
    S --> E[Eye module]
    S --> K[Kidney module]
    S --> H[Heart watch<br/>cardiovascular flag]
    G --> W[What-if engine]
    L --> W
    E --> W
    K --> W
    H --> D
    W --> D[Doctor dashboard]
    W --> P[Patient view]
    W --> R[FHIR API and PDF report]
```

The full diagrams are in [`architecture_2page.pdf`](Kaya_IIT-Hyderabad/docs/architecture_2page.pdf) (page 1: overview, page 2: detail). Source: [`make_flow_simple.py`](Kaya_IIT-Hyderabad/docs/make_flow_simple.py).

## 5. Product features

| Feature | What it does |
|---|---|
| **Live mode** | The glucose model runs on every incoming 5-minute reading (about 1 ms, pure numpy, no GPU) and the dashboard updates in real time. Press **Go live** in the doctor view, or POST readings to `/api/live/{id}/reading`. A WebSocket feed (`/ws/live/{id}`) simulates a wearable. |
| **Full patient record** | 14-day glucose history, daily time in range, a typical-day profile, meal responses, wearable trends, liver, eye and kidney projections with their drivers, labs with reference flags, and every alert with its reason. |
| **Heart watch** | Replays a patient's month morning by morning. Each morning at 10:00 a cardiovascular flag reads the last seven nights (sleep, HRV, resting heart rate, steps, glucose control) with the static record, shows the wearable pattern and the record risk as two dials that combine into one 72-hour risk, raises an alert above a threshold set for about one false alert per patient-month, and lists the factors that pushed the score up. Six held-out patients show a caught event, a missed event, a benign scare the record calmed, a false alarm and a quiet high-risk patient. |
| **Message the patient** | In the doctor's record, a **Message patient** tab sends an urgent message (come to the clinic, go to the emergency room, call the clinic) or plain advice, with quick templates. It shows at the top of the patient app within seconds, and the doctor sees when it has been seen. The same tab writes a **consultation note and prescription**: stop, start or change the dose of medicines, with a note. It updates the medicine list, adds a "Teleconsultation note and prescription" report to the Reports tab, and pops up in the patient app until the patient acknowledges it. Demonstration only; no real prescribing. |
| **What-if studio** | Meal size, walking after meals, sleep and medicine presets (or medicine by medicine: stop, change the dose, or add a drug), with the change shown in the glucose curve and in one-year organ risk. |
| **Medical reports** | Lab panels, retinal and liver scans, chest X-ray, ECG, foot exam, clinic notes and the wearable summary, each with reference ranges, flags, the previous value, a PDF and trends. The patient sees a plain-language version and a medicine list. All reports are synthetic. |
| **What changed since the last visit** | Compares today with the last clinic visit (HbA1c, eGFR, urine albumin, liver enzymes, blood pressure, weight, eye grade, new medicines) and the last 7 days of wearable data with the week before, and lists what needs attention. |
| **What to do now and quick log** | The patient's Today screen leads with one clear next action and why. A quick log takes five seconds (medicines, a walk, how they feel). The doctor sees an adherence grid in the record. |
| **Patient report uploads** | A patient uploads a PDF or photo of a report (up to 8 MB). Files are checked by content and stored under random ids. The AI reads a report only after the patient says yes, shows a summary, and the doctor sees the file marked "uploaded by the patient, not verified". |
| **Voice and chat assistant (optional)** | A microphone icon opens an assistant: ask by voice or text in your own language, hear any answer or the current screen read aloud, navigate by voice, switch on large text (A+). Uses [Sarvam AI](https://docs.sarvam.ai) from the server, so the key never reaches the browser. Works without a key too (rules, navigation, browser speech). |
| **Four languages** | English, Hindi, Telugu and Kannada with a one-tap switcher. The Indian-language texts are drafts and should be reviewed by a native speaker. |
| **Explanations** | Why an alert fired (trend and recent meal), what drives each liver and kidney risk (SHAP), and where the retina model looked (Grad-CAM). |
| **Clinical summary PDF** | One click from the doctor view (`/api/patients/{id}/report.pdf`): glucose chart with forecast, organ risks with their evidence level, what-if table and recent alerts. |
| **Admin page** | Service health, model and data inventory with how each model was validated, integration status, latency per route, assistant safety counters (outcomes only, never message text), an audit trail, a one-click self-test and an honest hardening list. Set `KAYA_ADMIN_TOKEN` to require a token. |
| **FHIR R4** | Read-only `Patient` and `Observation` endpoints under `/fhir`. |
| **Tests and CI** | 116 tests (data, what-if, live inference against PyTorch, API, assistant safety, uploads, PDF, FHIR, coupled cohort, cardiovascular flag, Heart watch) run on every push with GitHub Actions. |

## 6. AI/ML models and results

All numbers are **out-of-sample**: held-out patients for the synthetic cohort, and subject-level cross-validation on real data. Full details, limits and intended use are in [`MODEL_CARDS.md`](Kaya_IIT-Hyderabad/docs/MODEL_CARDS.md); raw metrics are in [`results/`](Kaya_IIT-Hyderabad/results/).

| Module | Model | Trained / validated on |
|---|---|---|
| Glucose forecast and alerts | GRU with quantile and event heads, blended with LightGBM; conformal intervals; isotonic calibration | Synthetic cohort (2,000 patients), then fine-tuned on real CGMacros (34 subjects) |
| Glucose forecast, two-stream version | Same GRU with six dynamic channels, slow sleep and HRV context and a 20-number record vector | Coupled synthetic cohort (2,000 patients, 28 days); ablation over input groups, 3 seeds |
| Heart watch (cardiovascular flag) | Wearable LightGBM and record logistic model, combined by a logistic stacker (late fusion), which also calibrates the probability | Coupled synthetic cohort, 5-fold patient-grouped cross-validation, 40,216 mornings, 595 events |
| Liver (static) | Regularised LightGBM with SHAP | NHANES 2017-2018, 4,745 adults with FibroScan |
| Liver (dynamic) | Glycemic-load modifier on the log-odds with a 90-day lag | Literature-informed assumptions, shown as a simulation |
| Kidney | Regularised LightGBM with SHAP; CKD-EPI 2021 eGFR; linear eGFR path | NHANES 2017-2018, 4,827 adults |
| Eye | EfficientNet-B2, ordinal regression, Grad-CAM | Trained on APTOS 2019, tested on Indian IDRiD |
| What-if | Splits glucose into baseline and meal excursions, rescales them, feeds the liver and eye modules | Literature-informed effect sizes, labelled as a simulation |
| Assistant | Sarvam AI (speech to text, text to speech, chat) behind rule-based safety | Rules tested in four languages |

### Fusing the two streams: what each stream adds

The brief asks for a record and a wearable stream to be fused. We therefore measure, rather than assume, what each input group adds. Everything below is on **held-out synthetic patients** from the coupled cohort (see [8. Data](#8-data)), so it shows that the fusion works as designed, not clinical accuracy.

**Glucose forecast** ([`ablate_glucose.py`](Kaya_IIT-Hyderabad/src/models/ablate_glucose.py), GRU, mean ± standard deviation over 3 seeds, 381,300 test windows; full table in [`results/glucose_ablation_table.md`](Kaya_IIT-Hyderabad/results/glucose_ablation_table.md)):

| Inputs | RMSE +30 / +60 / +120 min (mg/dL) | Low-glucose AUROC |
|---|---|---|
| CGM and meal log | 17.08 / 28.99 / 34.27 | 0.839 ± 0.001 |
| + heart rate and activity | 16.86 / 28.53 / 33.71 | 0.841 ± 0.001 |
| + age, BMI, HbA1c, sex | 16.43 / 27.53 / 32.37 | 0.847 ± 0.001 |
| + HRV and sleep (nightly and weekly) | 16.39 / 27.53 / 32.32 | 0.852 ± 0.002 |
| + labs, medicines, genetics (all inputs) | **16.21 / 27.23 / 32.24** | **0.953 ± 0.003** |
| all inputs, minus HRV and sleep | 16.24 / 27.42 / 32.56 | 0.953 ± 0.001 |
| all inputs, minus labs, medicines, genetics | 16.39 / 27.53 / 32.32 | 0.852 ± 0.002 |

- The **basic record** and **heart rate with activity** give the largest forecast gains (about 1.3 and 0.6 mg/dL at two hours).
- **Medicines** matter most for lows: with insulin or sulfonylurea use in the record, low-glucose AUROC rises from 0.85 to 0.95 in every seed. In the cohort only these patients can have a treatment-related low, which is also the clinical pattern; the size of the jump is the simulator's. Genetics add nothing measurable.
- **HRV and sleep** add little for glucose: removing them costs about 0.3 mg/dL at two hours (positive in all three seeds, +0.09 to +0.52) and changes event AUROC by less than 0.003. We report it as small.

**Cardiovascular flag** ([`cardio.py`](Kaya_IIT-Hyderabad/src/models/cardio.py), 5-fold cross-validation grouped by patient, 2,000 patients, 40,216 patient-mornings, 595 events, prediction target: an event in the next 72 hours; intervals from resampling patients):

| Input | AUROC (95% CI) | AUPRC (prevalence 0.042) | Events caught | False alerts per patient-month | Median warning |
|---|---|---|---|---|---|
| Record only (logistic risk score) | 0.69 (0.67 to 0.71) | 0.08 | 24% | 1.0 | 33 h |
| Simple clinical rule (HRV falling, resting heart rate rising, sleep shrinking) | 0.69 (0.68 to 0.71) | 0.11 | 44% | 0.9 | 17 h |
| Wearable week only | 0.82 (0.80 to 0.83) | 0.26 | 77% | 1.1 | 23 h |
| **Kaya: record + wearable (late fusion)** | **0.83 (0.82 to 0.84)** | **0.31** | 76% | 1.1 | 23 h |
| One model fed both streams side by side (early fusion) | 0.83 (0.82 to 0.85) | 0.31 | 76% | 1.0 | 26 h |

Honest reading:

- The **wearable week carries most of the early warning**, and the strongest single signal is last night's HRV. A simple clinical rule on the same data is far weaker.
- Fusing the record improves the wearable alone **modestly but reliably**: AUROC +0.015 (95% CI +0.010 to +0.021) and AUPRC 0.26 to 0.31. At the alert level (events caught for a given false-alert rate) the fused and wearable-only flags are the same within noise.
- The record's real job is **triage**: among mornings that are already part of a prodromal episode, the record alone separates a dangerous episode from a benign one with AUROC 0.80, against 0.68 for the wearable alone. The combined score has to find the episode and triage it at once, so it does not beat the record alone on that narrow question (0.74), and we do not claim it does.
- Early and late fusion perform the same. We ship the late-fusion version because its two parts (wearable pattern, record risk) can be shown and explained separately.
- Calibration of the fused probability: Brier 0.034, expected calibration error 0.003.
- False alerts concentrate in patients whose record is already high-risk, which is a property of the design: the same wearable change is taken more seriously in a higher-risk person.

### Glucose forecasting (real CGMacros recordings, 34 subjects)

| Model | RMSE 30 / 60 / 120 min (mg/dL) | 80% interval coverage |
|---|---|---|
| No change (persistence) | 16.3 / 25.8 / 36.7 | n/a |
| GRU fine-tuned | 13.7 / 21.7 / 28.7 | 0.79 / 0.78 / 0.77 |
| LightGBM | 12.4 / 21.6 / 29.3 | 0.72 / 0.68 / 0.62 |
| **Ensemble, calibrated** | **12.6 / 21.1 / 28.2** | **0.80 / 0.80 / 0.80** |

- Intervals are **conformal**, so the stated 80% really is 80%.
- Event probabilities are **isotonic-calibrated** (expected calibration error 0.003 to 0.005).
- **Alert replay** (a patient's week streamed through the model): at about one false alert per patient-day, Kaya catches **72% of hypoglycemia episodes with a median 45 minutes of warning**.

### Liver (real NHANES 2017-2018, 4,745 adults, FibroScan-labelled)

| Target | Kaya (AUROC) | Standard score |
|---|---|---|
| Advanced fibrosis (stiffness ≥ 8 kPa) | **0.83** | FIB-4: 0.63 |
| Steatosis (CAP ≥ 288 dB) | **0.83** | FLI: 0.82, HSI: 0.79 |

Performance is similar in adults with diabetes (0.76 steatosis, 0.80 fibrosis) and in Asian participants.

### Kidney (real NHANES 2017-2018, 4,827 adults)

| Target | Kaya (AUROC) | Simple baseline (age, BP, HbA1c, diabetes) |
|---|---|---|
| Reduced eGFR (< 60) | 0.85 | 0.85 |
| Albuminuria (UACR ≥ 30) | 0.76 | 0.75 |
| Any CKD | 0.79 | 0.78 |

Honest reading: from routine measurements the learned model adds only a small edge over a strong simple baseline. The product value is the eGFR trajectory and what-if, which are labelled simulations.

### Eye (retinopathy grading from fundus photos)

| Evaluation | Quadratic kappa | Referable DR AUROC | Within one grade |
|---|---|---|---|
| APTOS 2019, held-out 15% | 0.89 | 0.98 | 96% |
| IDRiD test (Indian), no fine-tuning | 0.57 | 0.88 | 83% |
| IDRiD test (Indian), after fine-tuning on IDRiD train | 0.71 | 0.92 | 87% |

The drop on IDRiD without fine-tuning is expected camera and population shift; a small amount of local data closes part of the gap. Exact-grade accuracy on IDRiD is 43% after fine-tuning, so Kaya reports grades as decision support alongside Grad-CAM heatmaps. Retinopathy *progression* risk is a simulation with editable assumptions.

## 7. Technical stack

| Layer | Tools |
|---|---|
| Models | PyTorch (GRU with quantile and event heads), LightGBM, scikit-learn, SHAP |
| Uncertainty | Conformal prediction, isotonic calibration |
| Data | pandas, pyarrow, wfdb, simglucose |
| Vision | timm (EfficientNet-B2), Grad-CAM |
| Live inference | NumPy export of the GRU (verified against PyTorch to within 1e-3) |
| Backend | FastAPI, Pydantic, FHIR R4 resources, WebSockets, ReportLab (PDF) |
| Frontend | React, Vite |
| Voice and language | Sarvam AI (speech to text, text to speech, chat), browser speech as fallback |
| Delivery | Docker Compose, GitHub Actions |
| Compute | 3 × NVIDIA RTX A5000 for training; the demo needs no GPU |

## 8. Data

Only open or synthetic data is used, as required by the challenge and the DPDP Act.

| Need | Source | Status |
|---|---|---|
| CGM, meals, wearables | [CGMacros](https://physionet.org/content/cgmacros/1.0.0/) (PhysioNet) | Used |
| Liver and kidney labels | NHANES 2017-2018 (FibroScan, labs) | Used |
| Synthetic patients and streams | Our generators (`src/ingest/synthetic_cohort.py` for the demo cohort, `src/ingest/cohort_v2.py` for the coupled cohort), plus simglucose | Used |
| Retina images | APTOS 2019 (train), IDRiD (Indian test, CC BY 4.0) | Used |
| Synthetic EHR | Synthea | Planned |

### An honest note on the synthetic cohort

A second, **coupled cohort** (`cohort_v2.py`, 2,000 patients, 28 days) was built for the fusion study, because in the first cohort HRV and sleep did not influence anything and a model could gain nothing from them. In the coupled cohort a hidden autonomic load moves HRV, resting heart rate, sleep, steps and glucose together; prodromal episodes of 3 to 5 days end in a cardiovascular event (more often in people with higher age, blood pressure, HbA1c, LDL, smoking or prior disease) or resolve as a benign episode that looks similar; a few events come with no warning. All effect sizes are assumptions. About 32 events occur per 100 patients per month, **far more than in real life**, so the flag's precision at real-world rates would be much lower than reported here.

No public dataset links one person's glucose stream to their liver, eye and kidney outcomes. We therefore simulate a **bridged cohort** whose distributions follow Indian T2D epidemiology and whose organ outcomes follow documented risk relationships:

- **Every module is validated on real data wherever real data exists** (glucose on CGMacros, liver and kidney on NHANES, eye on APTOS and IDRiD).
- The synthetic cohort demonstrates that the **data fusion and the mechanisms work end to end**. It does not establish clinical accuracy of the links between glucose patterns and organ outcomes.
- Kaya is **decision support for clinicians, not a diagnostic device**, and has not been clinically validated.

## 9. Design principles

- **Privacy by design:** synthetic or anonymised data only, consent before AI reads an upload, minimal data, audit log, message text never stored.
- **Explainable:** every prediction can show why it fired and how sure the model is.
- **Interoperable:** FHIR R4, designed to align with India's ABDM.
- **Honest:** metrics reported against standard baselines, simulations labelled as simulations, limitations stated up front.

## 10. Run the demo

The demo runs from a plain clone, with no GPU. Forecasts and risk scores for 24 held-out synthetic patients are precomputed by the validated models and stored in `artifacts/demo/`.

**With Docker**

```bash
cd Kaya_IIT-Hyderabad
docker compose up --build
```

**Without Docker**

```bash
cd Kaya_IIT-Hyderabad
pip install -r requirements-api.txt
uvicorn app:app --app-dir src/api --port 8000
```

Then open `http://localhost:8000` (dashboard) and `http://localhost:8000/docs` (API documentation).

In the dashboard, switch between **Doctor**, **Heart watch**, **Patient** and **Admin** at the top right. In the doctor view, press **Replay last 3 days** to watch the twin forecast glucose ahead of what actually happens, then try the **What-if** presets. [`DEMO_GUIDE.md`](Kaya_IIT-Hyderabad/docs/DEMO_GUIDE.md) describes two ready-made patients (a complex multi-organ case and a well-controlled case), their day-by-day stories and a suggested demo flow.

**Voice assistant (optional).** Copy `.env.example` to `.env` and set `SARVAM_API_KEY`. Without a key the rest of the app works unchanged.

**Tests**

```bash
cd Kaya_IIT-Hyderabad
pip install pytest httpx
python -m pytest -q tests
```

**Reproduce the model results** (needs the data downloads and, for training, a GPU)

```bash
pip install -r requirements.txt
python scripts/fetch_data.py all                 # CGMacros + NHANES
python src/ingest/synthetic_cohort.py --n 2000 --days 14
python src/ingest/nhanes_liver.py
PYTHONPATH=src/models python src/models/train_glucose.py
PYTHONPATH=src/models python src/models/polish_glucose.py
python src/models/liver_static.py
```

To regenerate the demo artifacts from the trained models: `PYTHONPATH=src/models:src/whatif python src/api/build_artifacts.py`.

**Reproduce the two-stream study** (CPU is enough for the cardiovascular flag; the glucose ablation uses a GPU, about 100 seconds per run)

```bash
python src/ingest/cohort_v2.py --n 2000 --days 28 --out data/synthetic_v2
export PYTHONPATH=src/models:src/ingest:src/features
python src/models/cardio.py --root data/synthetic_v2                       # cross-validated flag, writes results/cardio_metrics.json
python src/models/ablate_glucose.py --seeds 3 --out results/glucose_ablation.json
python src/api/build_cardio_artifacts.py                                   # Heart watch demo patients
```

The Heart watch opens at `http://localhost:8000/?view=heart`.

## 11. Repository layout

```
Kaya_IIT-Hyderabad/
├── src/
│   ├── api/         FastAPI app, FHIR, reports, uploads, assistant, admin, Heart watch builder
│   ├── features/    nightly sleep, HRV and heart-rate summaries shared by the models
│   ├── ingest/      synthetic cohorts (demo and coupled), NHANES datasets, demo patient stories
│   ├── models/      glucose (v1 and two-stream), cardiovascular flag, liver, kidney, eye, alerts
│   └── whatif/      what-if engine
├── dashboard/       React doctor, patient and admin views
├── artifacts/       precomputed demo patients, live model, retina images
├── results/         evaluation metrics (JSON)
├── docs/            architecture, presentation, model cards, demo guide, screenshots
├── scripts/         data download and server setup
├── tests/           116 tests
├── Dockerfile, docker-compose.yml
└── requirements.txt, requirements-api.txt
```

## 12. Demo video and documents

| Item | Link |
|---|---|
| Demo video (unlisted YouTube) | [Watch on YouTube](https://youtu.be/SyA4dCjmQi8) |
| Architecture diagram (PDF) | [`architecture_2page.pdf`](Kaya_IIT-Hyderabad/docs/architecture_2page.pdf) |
| Presentation (PDF) | [`Kaya_presentation.pdf`](Kaya_IIT-Hyderabad/docs/Kaya_presentation.pdf) |
| Presentation (PPT) | [`Kaya_pitch_deck.pptx`](Kaya_IIT-Hyderabad/docs/Kaya_pitch_deck.pptx) |
| Model cards | [`MODEL_CARDS.md`](Kaya_IIT-Hyderabad/docs/MODEL_CARDS.md) |
| Demo guide | [`DEMO_GUIDE.md`](Kaya_IIT-Hyderabad/docs/DEMO_GUIDE.md) |
| Project plan and roadmap | [`PROJECT_PLAN.md`](Kaya_IIT-Hyderabad/docs/PROJECT_PLAN.md) |

## 13. Limitations and roadmap

**Limitations, stated plainly**

- Kaya is decision support, not a diagnostic device, and has not been clinically validated.
- The link from glucose patterns to organ outcomes is simulated; each module's baseline model is validated on real data, but the dynamic effects (liver drift, retinopathy progression, eGFR path, what-if effect sizes) use literature-informed assumptions.
- Only 34 real CGM subjects; NHANES is a US population; exact-grade retinopathy accuracy on IDRiD is modest.
- The cardiovascular flag is trained and tested only on synthetic data whose couplings and event rates we chose. It shows that fusing a wearable week with the record works as designed; it is not evidence of clinical accuracy, and no open dataset links a week of wearable data to cardiovascular outcomes for diabetes.
- The Heart watch demo patients were picked to illustrate each outcome (for each, the example with the fewest alerts). The table above, not the demo, is the measure of performance.
- The Hindi, Telugu and Kannada texts and the speech quality need native-speaker review.
- The demo uses synthetic patients and has no authentication; the admin page lists what must be hardened before real patient data.

**Roadmap:** feed HRV and sleep into the live glucose forecast, validate the flag on a real wearable cohort with outcomes, illustrative retina preview (a generated fundus image at the predicted grade, always labelled as a preview), Synthea-based EHR, authentication and role-based access, fuller FHIR and ABDM coverage, and prospective validation with a clinical partner.

## 14. License

Released under the [Apache License 2.0](Kaya_IIT-Hyderabad/LICENSE).
