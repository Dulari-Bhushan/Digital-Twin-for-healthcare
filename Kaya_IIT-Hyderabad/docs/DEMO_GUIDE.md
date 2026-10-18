# Demo guide: two patients, two very different dashboards

All patients are synthetic and the names are invented. Start the app with `uvicorn app:app --app-dir src/api --port 8000`.

## The two patients

| | **Rajesh Sharma** (ID 1688) | **Priya Kashyap** (ID 1636) |
|---|---|---|
| Who | 51-year-old man, T2D for 22 years, insulin or sulfonylurea | 34-year-old woman, T2D for 3 years, metformin |
| Control | HbA1c 9.1%, 30% time in range over 14 days | HbA1c 7.4%, 81% time in range |
| Liver | Fat risk 37% now, 63% in a year; fibrosis 11% rising to 18% | Fat risk 5%, low |
| Eyes | **Moderate retinopathy**, 53% chance of progressing in 2 years | No retinopathy, 2% |
| Kidneys | **Albuminuria** (UACR 231 mg/g), eGFR 63 heading to about 48 in 5 years | Healthy: eGFR 108, UACR 12 |
| Low-sugar risk | Yes (insulin or sulfonylurea), has a night-time low | None |
| Priority | **High**, near the top of the doctor list | **Low**, further down the list |

Why these two: they show the whole range. Rajesh needs attention on every organ and has treatment-related lows. Priya shows what a well-controlled patient looks like, with the twin mostly reassuring and one bad day to learn from.

## Links

| View | Rajesh | Priya |
|---|---|---|
| Doctor | `http://localhost:8000/?p=1688` | `http://localhost:8000/?p=1636` |
| Patient app | `http://localhost:8000/?view=patient&p=1688` | `http://localhost:8000/?view=patient&p=1636` |
| Hindi / Telugu / Kannada | add `&lang=hi`, `&lang=te` or `&lang=kn` | same |
| Open on a given day | add `&day=3`, `2`, `1` or `0` (0 is today) | same |
| Clinical summary PDF | `http://localhost:8000/api/patients/1688/report.pdf` | `.../1636/report.pdf` |

## The days the patient app shows

Tap the day chips at the top of the patient app. Each day has its own summary, glucose chart and habits.

| Day | Rajesh Sharma | Priya Kashyap |
|---|---|---|
| **Sun 11** | **A tough day, 4% in range.** Festival feast and sweets, no walking. Peaks at 347 after a meal. | **49% in range.** A wedding feast with a late dinner and sweets. Peaks at 266. |
| **Mon 12** | **62% in range, with a low.** Sugar below 70 for 65 minutes at about 3 am (insulin). | **72% in range.** Recovering the day after the feast. |
| **Tue 13** | **A good day, 91%.** Smaller portions and a walk; flat curve. | **A good day, 90%.** |
| **Today** | **46%.** Heavy late dinner with no walk; sugar rising fast, so the twin forecasts a high. | **80%.** An ordinary good day, steady forecast. |

## The full patient record

In the doctor view, **click any card** (the patient header, the glucose twin, next 2 hours, time in range, liver, eyes, kidneys or the alert timeline). A record opens on the right with everything about that patient, opened at the tab that matches the card you clicked:

| Tab | What it shows |
|---|---|
| Overview | Key numbers, a problem list (click a row to jump to it), daily time in range, kidney and liver paths |
| Glucose | Forecast from the latest reading, the full 14-day glucose trace, daily time in range, a typical-day profile, a daily table, steps, carbohydrate, sleep and mean glucose by day, meal responses and the five highest peaks |
| Liver | Labs with reference flags, FibroScan and FIB-4, the 12-month projection, what drives the risk, and the glucose habits feeding the drift |
| Eyes | Retina photo with heatmap, grade, and what drives the 2-year progression risk |
| Kidneys | eGFR path with stage lines, albuminuria drift, why the slope is what it is, and what drives each risk |
| Alerts | Every stored alert with the reason it fired, and alerts per day |
| Profile and labs | Demographics, treatment, genetics, the full lab panel, clinic measurements and why the patient is prioritised |

Press Esc or click outside to close. Link straight to a tab with `?p=1688&record=glucose` (or `liver`, `eyes`, `kidneys`, `alerts`, `profile`, `overview`).

## Reports and what changed since the last visit

**Doctor view.** Right under the patient header there is a **What changed since the last visit** card. For Rajesh it flags the 65-minute night low on Mon 12, urine albumin up 28%, retinopathy progressing from mild to moderate, and HbA1c up from 8.8% to 9.1%; it also notes the new kidney medicine. For Priya it shows 0 worse and her HbA1c improving. Click **All reports** to open the **Reports** tab.

**Reports tab.** Trend chart across lab panels (HbA1c, eGFR, urine albumin, ALT, LDL, blood pressure, weight), a filterable list of 17 reports, and the selected report laid out like the paper copy with a PDF button. Open the retinal photograph to show the image and the Grad-CAM view. Current medicines are listed underneath. Deep links: `?p=1688&record=reports&report=EYE` (codes: `LAB`, `EYE`, `LIV`, `VIS`, `FOOT`, `ECG`, `CXR`, `CGM`).

**Patient app.** The fifth tab, **Reports**, starts with the plain-language "Since your last visit" card, trend charts, the medicine list and the report list. Tapping a report shows an "In simple words" box first. Link: `?view=patient&p=1688&tab=4`.

The history is generated, not recorded: today's values come from each patient's profile and the 14-day glucose series, and earlier values are produced backwards from them with a seeded trend (scripted for the two demo patients), so every report agrees with the dashboard. Code: `src/api/reports.py`.

## What to do now, quick log and the diary

**Patient app, Today.** Rajesh's screen opens with **What to do now**: a 15-minute walk (forecast 228 in 2 hours), and below it a sugar check before bed (he takes insulin) and evening medicines not yet taken. Press **Mark as done** and the card moves on to the next action. **Quick log** below it records medicines (morning or evening), a walk of 10, 20 or 30 minutes, and how he feels. Priya's list is shorter because she already walked and took her morning medicines.

**Doctor view.** The record's Overview has **Patient diary and adherence**: morning and evening medicines taken, days with a walk, days felt unwell, a 14-day grid, and the patient's own notes. Anything logged in the patient app appears here on reload. Rajesh logged evening medicines on about half of the days, and that shows up as a line in the attention list; Priya's diary is consistent. The 14 seeded days are synthetic and generated from each patient's own glucose and step data; entries made live are stored in `data/patient_logs/` (git-ignored). To reset the demo, delete that folder.

## Patient report uploads

In the patient app, Reports tab, **Add a report** lets the patient choose a PDF or take or pick a photo, name it, set its type and date, and upload it. It appears under **Reports I uploaded** (open or remove). In the doctor record, Reports tab, the same file appears under **Uploaded by the patient**, marked not verified. Only PDF, PNG, JPEG and WebP up to 8 MB are accepted, checked by content. Files live in `data/patient_uploads/` (git-ignored); delete the folder to reset. 

**Automatic reading, with a question first.** Upload `docs/sample/Rajesh_Sharma_lab_report.pdf` (a fictional lab report for Rajesh, dated 10 Jan 2026; regenerate with `python docs/make_sample_report.py`). The file is saved, and the app then asks **Should the AI read this report?** with a plain explanation that saying yes sends the file to Sarvam AI. Nothing leaves the server before the patient presses **Yes, read it for me**. After about 5 to 10 seconds a summary card appears: how many results were read, the ones outside the healthy range as chips, and **View the report**. The report is also in the list as an *Unverified* report with values, flags, the previous value from the last panel, the source text and a link to the original. **No, keep the file only** keeps the file; a **Read with AI** button on the file lets the patient change their mind later. A rule-based parser (`src/api/labparse.py`, not a language model) picks out only values it can trace to a line of the document, so a missing value is left out, never guessed. If reading fails, the file is kept. Values read this way are not used by the twin; the history charts and the changes card use the verified panels only. For the demo, upload it for Rajesh (`?view=patient&p=1688&tab=4`), then open the doctor view's Reports tab to show it there too.

## The IT admin page

Open **Admin** in the header (or `?view=admin`). It shows service health and uptime, request counts with p50 and p95 latency, the model and data inventory, integrations (voice, FHIR, live feed), assistant safety counters, an audit trail of recent actions (diary entries, PDF downloads, assistant outcomes, live sessions) and a hardening checklist. Press **Run self-test** (or open `?view=admin&selftest=1`) to run the main code paths once: artifacts, triage, what-if, the live model, record history, PDF rendering and storage. Start the server with `KAYA_ADMIN_TOKEN=...` to require a token. Counters and the audit trail are in memory and reset when the server restarts; no patient data or keys are shown.

## Suggested flow (about 6 minutes)

1. **Doctor view, Rajesh.** Show the triage list (sorted by priority; Priya is further down, pick her by name). Point at why he is flagged (time in range, liver, kidney, retinopathy). Press **Replay last 3 days**: the forecast fan appears before the evening spike.
2. **What-if studio.** Press **All three**: time in range improves, liver and kidney projections move. Say it is a simulation with editable assumptions.
3. **Switch to Priya** in the list. Same screens, very different picture: green rings, low risks, forecasts that stay in range.
4. **Patient app, Rajesh.** Tap Sun, Mon, Tue and Today to show how each day differs. On Mon, point at the low in the chart.
5. **Same app, Priya.** Show the wedding day and the recovery.
6. **Assistant.** Tap the small microphone icon, ask a question in Hindi or Kannada, and try "how much insulin should I take" to show the safety rule.
7. **Reports.** In the doctor view show the changes card, then open Reports and a retinal report; in the patient app tap the Reports tab.
8. **Go live** in the doctor view and the **clinical summary** button, if time allows.

## How the stories were made

The cohort generator makes statistically similar days, so for these two patients the last 14 days are scripted (`src/ingest/demo_stories.py`): carbohydrate load, walks, steps, late dinners, a night low and a gradual improvement. Everything else about them (labs, organ labels, genetics) comes from the normal synthetic cohort, and the forecasts, alerts and organ risks are computed by the same models as for every other patient. Re-run with `python src/ingest/demo_stories.py` and then `python src/api/build_artifacts.py` on the GPU machine.
