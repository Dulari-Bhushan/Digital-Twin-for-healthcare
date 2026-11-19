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

## Starting clean

Everything a patient logs in the app (walks, medicines, how they feel) is cleared when the server starts, so each demo begins with 0 minutes walked and nothing newly logged. Start the server with `KAYA_KEEP_LOGS=1` to keep the entries between runs. In the quick log, tapping a ticked medicine again un-ticks it. Messages and uploads are kept between runs; delete `data/patient_messages/` or `data/patient_uploads/` to reset those.

## Messaging the patient and sending a prescription

Open a patient's record and choose **✉ Message patient** (or the **Message patient** button at the top of the doctor page). Keep the patient app open in a second window (`?view=patient&p=1688`).

1. **Urgent message.** Pick *Come to the clinic today* or *Go to the emergency room now* and press **Send urgent message**. A red banner appears at the top of the patient app within a few seconds, with the instruction in the patient's language; **I have seen this** clears it, and the doctor's list shows "Seen by the patient".
2. **Advice.** Choose *Walk after meals* (or write your own) and send; the patient sees a blue message card.
3. **Prescription.** In the same tab set a medicine to *Change dose* or *Stop*, or **＋ Add a medicine**, write a note and press **Send prescription to the patient**. The patient app opens a "Your doctor changed your medicines" pop-up; **Got it, show me my reports** takes them to Reports, where the new *Teleconsultation note and prescription* is listed and the medicine list is updated. The doctor's Reports tab and the what-if studio show the new list too.

Messages are stored in `data/patient_messages/` (not committed); delete the folder to reset the demo. The doctor's own text is shown as written; only the labels are translated.

## The IT admin page

Open **Admin** in the header (or `?view=admin`). It shows service health and uptime, request counts with p50 and p95 latency, the model and data inventory, integrations (voice, FHIR, live feed), assistant safety counters, an audit trail of recent actions (diary entries, PDF downloads, assistant outcomes, live sessions) and a hardening checklist. Press **Run self-test** (or open `?view=admin&selftest=1`) to run the main code paths once: artifacts, triage, what-if, the live model, record history, PDF rendering and storage. Start the server with `KAYA_ADMIN_TOKEN=...` to require a token. Counters and the audit trail are in memory and reset when the server restarts; no patient data or keys are shown.

## Heart watch: a second adverse event from a week of sleep, heart-rate and glucose data

Heart watch sits inside the **Doctor** view, next to **Glucose twin** (or open `http://localhost:8000/?view=heart`). It lists **the same 24 patients as the glucose twin**: same names, ages, HbA1c, blood pressure, kidney and lipid values. Pick a patient in one tab and the other opens on them, and **Open this patient's glucose twin** jumps back. Every score comes from a model that never saw that patient, so misses and false alarms are shown too.

The heart data (a month of nights: HRV, resting heart rate, sleep, steps) is simulated for these 24 people, because the glucose twin's own record has no heart data. LDL, smoking and prior cardiovascular disease are also drawn, since the twin does not hold them. Nothing was picked by outcome: what happens to each person is what the held-out model did, so the list contains misses and false alarms alongside the catches. One seed (`KAYA_DEMO_SEED=12`) was chosen so that the month contains at least one miss and one catch.

| Patient | What it shows |
|---|---|
| Harpreet Singh, Ramprasad Mishra, Anil Saxena, Savitri Devi | An event the flag warned about ahead of time. Press **Replay the month**, watch night HRV fall and resting heart rate rise, then the "Review suggested" alert, then the event marker. Anil Saxena is on insulin and had a low in the week before: the **Medicine check** banner appears |
| Sanjay Gupta, Priya Kashyap | A missed event: no alert, and the screen says so. Priya Kashyap is the glucose demo's well-controlled patient: good glucose control does not rule out a heart event |
| Surendra Pratap Singh | A missed event, after an earlier alert on a benign scare |
| Rakesh Bhatt | A benign scare the record calmed: the wearable pattern is unusual but the record risk is low, so no alert |
| Brijmohan Yadav, Prakash Joshi, Arjun Malhotra, Mohammed Rafiq, Vikram Rathore | False alarms. Vikram Rathore is on insulin with two lows |
| Rajesh Sharma, Kamla Devi | A high-risk record with a quiet month: no alert (Rajesh Sharma is the glucose demo's complex case) |
| Neha Chauhan and eight others | A benign episode that did not trigger an alert, or nothing at all |

Under **Edge cases: messy data** are two patients from the 2,000-patient cohort, made messy on purpose (ids 100000 and up, not in the glucose twin):

| Patient | What it shows |
|---|---|
| Radha Nair | **The watch is often off.** On the mornings with fewer than 4 usable nights the card says "Not enough data", shows no score and raises no alert; the charts show gaps |
| Geeta Pillai | **No record on file** (only age, sex, BMI). The record dial reads "n/a", the confidence chip says "lower", and the alert rests on the wearable and glucose sensor alone |

Direct links: `?view=heart&hp=1091&day=12` opens Anil Saxena on his alert morning; `hp` is the patient id and `day` the morning (7 to 27).

The dials show the wearable-and-glucose pattern, the record-risk percentile and the combined 72-hour risk. **Why this score** lists the factors that pushed it up, tagged wearable, glucose sensor or record. The wording is deliberate: "Review suggested" is a prompt to look at a patient, not a diagnosis. Two tables at the bottom give the measured behaviour on held-out patients: **How well does it work?** (use it, not the 24 examples, when asked about accuracy) and **When the data is thin or messy** (glucose lows, the watch off for days, no record). Say plainly that the cohort is synthetic, that cardiovascular events are far more frequent in it than in real life (7 events among 24 people in a month), and that the link between severe lows and heart episodes is an assumption of the simulator.

## Screening tracker: which yearly tests are overdue

In the doctor record's **Overview**, under *What changed since the last visit*, the **Screening tracker** lists four yearly tests for a person with diabetes: the eye (retina) exam, the urine albumin test, kidney function (eGFR) and the foot exam. Each row shows when it was last done, whether it is **up to date**, **due soon** (under 60 days left) or **overdue**, and why the test matters. The patient list also gets a **Screening overdue** flag, so these patients no longer look stable.

| Patient | What to show |
|---|---|
| **Rajesh Sharma (ID 1688)** | The one-patient demo. Eye exam overdue (last photo 14 months ago, which showed moderate retinopathy) and foot exam overdue (14 months); urine albumin and kidney function are up to date. Press **Refer to eye specialist**: the row shows "Referral sent" and the message appears in his patient app. His other stories are unchanged: the changes card still shows retinopathy progressing from mild to moderate, and albumin rising to 231 mg/g |
| Brijmohan Yadav (ID 302) | Eye exam and foot exam overdue (15 and 19 months) |
| Neha Chauhan (ID 496) | Urine albumin test overdue. The Reports tab shows the urine albumin trend with gaps, because only the oldest lab panel had the test |
| Priya Kashyap | Everything up to date |

The history of which tests were done is simulated and seeded by patient id (`src/api/screening.py`); about 30% of the cohort is overdue for the eye exam, 30% for the urine albumin test and 25% for the foot exam. The same schedule decides which reports exist in the record, so the tracker and the Reports tab always agree. A reminder or referral is an ordinary message to the patient; the row clears when a new report for that test is in the record. Sending one writes to `data/patient_messages/` (git-ignored); delete that folder to reset the demo.

## Japanese (日本語)

In the patient app press **日** at the top, or open `http://localhost:8000/?view=patient&p=1688&lang=ja`.

| What | How it works |
|---|---|
| Every patient screen | Japanese text in `dashboard/src/i18n_ja.json` (228 strings, a first draft: **have a native speaker read it before the day**) |
| Ask Kaya (chat) | Answers in Japanese from **Google Gemini** (`src/api/gemini.py`), using the patient's anonymous facts only |
| Doctor's messages and prescriptions | Quick-start messages are pre-translated; free text and prescription notes are translated by Gemini the first time the patient opens them (needs internet) |
| Reading aloud and the microphone | The browser's own Japanese voice (Edge has natural-sounding ones) and Chrome or Edge speech recognition, which needs internet. Sarvam has no Japanese |
| Reports and the doctor's screens | Stay in English, as issued |

**Setup.** Put `GEMINI_API_KEY=...` in `.env` (git-ignored, see `.env.example`). `GEMINI_MODEL` picks a different model first; the default is `gemini-3.1-flash-lite`, with `gemini-3.5-flash-lite` as back-up. `GEMINI_DAILY_BUDGET` (default 1500) caps model calls per day. Without a key, Japanese chat says "I could not answer just now" politely and everything else works.

**Safety and security on every Japanese (and other) chat request**
- **Fixed answers first, in code, before the model:** Japanese emergency words (胸が痛い, 息ができない, 意識がない ...) get the 119 message; medicine and dose words (薬, インスリン, 用量, 何単位 ...) get the "ask your doctor or pharmacist" message. The model never sees them.
- **Input cleaned:** control, zero-width and direction-override characters removed, length capped at 500 characters, earlier turns from the browser re-checked because they could be forged.
- **Rule-change and key requests refused without calling the model:** "ignore your instructions", "show the system prompt", "what is the API key" (English and Japanese).
- **Limits:** 40 requests a minute per client (all voice and chat), 12 model calls a minute per client, a daily budget, and a circuit breaker that stops calling a failing service for a minute. A busy service gets a polite message.
- **Nothing identifying is sent:** the model gets age, sex and the numbers, never a name, id or contact details.
- **Replies checked:** links, e-mail addresses, phone numbers and key-shaped text removed or refused, dose advice replaced by the medicine message, and a reply that is not Japanese is not shown.
- **The key stays on the server:** read from `.env`, sent in a header, scrubbed from every error text, never returned to a browser. The admin page shows only "configured".

Say plainly if asked: the Japanese wording is a machine-assisted first draft awaiting native-speaker review, and the chat assistant is general guidance, not medical advice.

## Appointments: reception, the doctor's calendar and booking from the patient app

Three views share one calendar (`src/api/appointments.py`, stored in `data/appointments.json`, git-ignored; `python scripts/reset_demo.py` clears it and the server creates a fresh sample week on start).

| View | How to open | What it does |
|---|---|---|
| **Reception** | the **Reception** button in the header (a badge shows how many requests wait; red when one is urgent), or `?view=reception` | Requests queue (urgent first) with Confirm, Decline, or Place for an urgent request. The week calendar below: click a person to see their request, move them, cancel them, mark them seen or absent; click an empty slot to book a patient in |
| **Doctor's schedule** | Doctor view, **Schedule** tab, or `?view=schedule` | The same calendar for the doctor and nurse, with the same changes and the two tools below |
| **Patient app** | the **Appointments** card: always in the Reports tab, and on the main Today screen only when it matters (an appointment is coming up, or yearly tests are due or overdue; otherwise Today has no booking card), or `?view=patient&p=1688&book=1` | A four-week month calendar marks open days, full days and closed days, and pins the date a test is due (or lists tests that are overdue). Tapping a day opens its times, with free, taken and "urgent only" slots; the patient picks one and sends a request |

**Rules built in**
- The clinic is open Monday to Friday, 09:00-12:00 and 14:00-17:00, in 20-minute slots. Today is Wednesday 14 January 2026 at 21:50 on the demo clock, so the first bookable day is Thursday 15 January.
- A request **holds its slot at once**, so nobody else can take it, until reception answers. A declined or cancelled slot is free again immediately for other patients.
- **Cancelling:** the patient app says "If you need to cancel, please do it at least 24 hours before, so another patient can take the slot." Cancelling inside 24 hours is allowed but marked as a late cancellation (and the app warns first).
- **Emergencies:** the last slot of each session (11:40 and 16:40) is held back, and patients cannot book it. A patient who ticks **This is urgent** needs no slot: the request goes to the top of reception's queue (the app tells them to call 119 in a real emergency), and reception places them in a held-back slot, or squeezes them into a busy one on purpose.
- A patient can hold at most 3 appointments and send 6 requests a day.

**When the doctor is called away** (Reception or the doctor's Schedule tab, under the calendar)
- **When the doctor is called away:** pick the day, the time away and back, and "move to the next free slots" or "cancel and tell them". **Show who is affected** lists each patient and where they would move; **Apply** moves them, blocks the time for new bookings, and each patient sees a banner in the app with the reason. Patients who no longer fit that day go to the next open day.
- **Running late:** everyone from a chosen time keeps their slot but is told to come about 20 minutes later; the app shows "expected about 10:45".

Every change adds a banner in the patient app (confirmed, moved, cancelled, running late) that stays until the patient presses **I have seen this**.

**A two-minute demo:** in the patient app (Rajesh) book Thursday 09:20, then switch to **Reception** and press Confirm (the patient app shows the confirmation). Tick **This is urgent** as a second patient to show the red queue. Then open **Show who is affected** for Thursday 09:00-12:00 to show the plan for an emergency operation, and apply it. Reset afterwards.

The calendar and the sample requests are synthetic. The reception, doctor and patient screens are separate views of the same data with no sign-in: a real clinic needs staff accounts and roles. The patient screens are translated into Japanese; the reception and doctor screens are in English.

## Suggested flow: one patient, Rajesh Sharma (about 6 minutes)

Before you start: stop the server, run `python scripts/reset_demo.py`, start the server again, and open two windows: the doctor view (`http://localhost:8000/?p=1688`) and the patient app (`http://localhost:8000/?view=patient&p=1688`). The story is the doctor's: *the twin finds the problem, the screening gap shows what is missing, and the doctor acts without the patient having to come in.*

1. **Who needs me today.** In the doctor list, press the **Screening** chip: only patients with an overdue test remain. Rajesh is near the top (high priority). Open him.
2. **Why he is flagged.** The header and the **What changed since the last visit** card: time in range, a night low, albumin up, retinopathy progressing from mild to moderate. Press **Replay last 3 days** to show the forecast fan before the evening spike.
3. **The screening gap.** Scroll to the **Screening tracker**: his eye exam is 14 months overdue even though his last photo already showed moderate retinopathy, and the foot exam is overdue too. Press **Refer to eye specialist**; the row now says "Referral sent". In the patient window, the doctor's message appears within seconds.
4. **Try a medicine before prescribing.** Open the **What-if studio** and change a medicine (stop, change the dose, or add one) to see glucose and low-sugar risk move. Say it is a simulation with editable assumptions.
5. **The patient sends a report from home, no visit needed.** In the patient app open **Reports**, **Add a report**, choose `docs/sample/Rajesh_Sharma_lab_report.pdf`, press **Yes, read it for me** (needs internet for the reading service). In the doctor's **Reports** tab it appears under *Uploaded by the patient*, marked unverified.
6. **The doctor acts.** Open **Message patient**, set a medicine to *Change dose*, write a note, press **Send prescription to the patient**. In the patient window the "Your doctor changed your medicines" pop-up appears; **Got it, show me my reports** shows the new consultation note and the updated medicine list.
7. **Close** with the patient's side if time allows: tap Sun, Mon, Tue and Today, the Mon night low, and the assistant (ask "how much insulin should I take" to show the safety rule).

**Optional extras:** compare with Priya Kashyap (everything green and up to date); **Heart watch** (the second tab in the Doctor view: Anil Saxena, Rakesh Bhatt, Radha Nair; say it is research-only and say the number of false alarms out loud); the clinical summary PDF; the IT admin page.

If the internet is down: skip the automatic report reading in step 5 (the upload and the doctor's view still work) and have the backup screen recording ready.

## How the stories were made

The cohort generator makes statistically similar days, so for these two patients the last 14 days are scripted (`src/ingest/demo_stories.py`): carbohydrate load, walks, steps, late dinners, a night low and a gradual improvement. Everything else about them (labs, organ labels, genetics) comes from the normal synthetic cohort, and the forecasts, alerts and organ risks are computed by the same models as for every other patient. Re-run with `python src/ingest/demo_stories.py` and then `python src/api/build_artifacts.py` on the GPU machine.
