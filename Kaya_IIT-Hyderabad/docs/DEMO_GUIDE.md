# Demo guide: two patients, two very different dashboards

All patients are synthetic and the names are invented. Start the app with `uvicorn app:app --app-dir src/api --port 8000`.

## The two patients

| | **Venkatesh Rao** (ID 1688) | **Kavya Gowda** (ID 1636) |
|---|---|---|
| Who | 51-year-old man, T2D for 22 years, insulin or sulfonylurea | 34-year-old woman, T2D for 3 years, metformin |
| Control | HbA1c 9.1%, 30% time in range over 14 days | HbA1c 7.4%, 81% time in range |
| Liver | Fat risk 37% now, 63% in a year; fibrosis 11% rising to 18% | Fat risk 5%, low |
| Eyes | **Moderate retinopathy**, 53% chance of progressing in 2 years | No retinopathy, 2% |
| Kidneys | **Albuminuria** (UACR 231 mg/g), eGFR 63 heading to about 48 in 5 years | Healthy: eGFR 108, UACR 12 |
| Low-sugar risk | Yes (insulin or sulfonylurea), has a night-time low | None |
| Priority | **High**, pinned first in the doctor list | **Low**, pinned second |

Why these two: they show the whole range. Venkatesh needs attention on every organ and has treatment-related lows. Kavya shows what a well-controlled patient looks like, with the twin mostly reassuring and one bad day to learn from.

## Links

| View | Venkatesh | Kavya |
|---|---|---|
| Doctor | `http://localhost:8000/?p=1688` | `http://localhost:8000/?p=1636` |
| Patient app | `http://localhost:8000/?view=patient&p=1688` | `http://localhost:8000/?view=patient&p=1636` |
| Hindi / Telugu / Kannada | add `&lang=hi`, `&lang=te` or `&lang=kn` | same |
| Open on a given day | add `&day=3`, `2`, `1` or `0` (0 is today) | same |
| Clinical summary PDF | `http://localhost:8000/api/patients/1688/report.pdf` | `.../1636/report.pdf` |

## The days the patient app shows

Tap the day chips at the top of the patient app. Each day has its own summary, glucose chart and habits.

| Day | Venkatesh Rao | Kavya Gowda |
|---|---|---|
| **Sun 11** | **A tough day, 4% in range.** Festival feast and sweets, no walking. Peaks at 347 after a meal. | **49% in range.** A wedding feast with a late dinner and sweets. Peaks at 266. |
| **Mon 12** | **62% in range, with a low.** Sugar below 70 for 65 minutes at about 3 am (insulin). | **72% in range.** Recovering the day after the feast. |
| **Tue 13** | **A good day, 91%.** Smaller portions and a walk; flat curve. | **A good day, 90%.** |
| **Today** | **46%.** Heavy late dinner with no walk; sugar rising fast, so the twin forecasts a high. | **80%.** An ordinary good day, steady forecast. |

## Suggested flow (about 6 minutes)

1. **Doctor view, Venkatesh.** Show the triage list with the two demo cases pinned. Point at why he is flagged (time in range, liver, kidney, retinopathy). Press **Replay last 3 days**: the forecast fan appears before the evening spike.
2. **What-if studio.** Press **All three**: time in range improves, liver and kidney projections move. Say it is a simulation with editable assumptions.
3. **Switch to Kavya** in the list. Same screens, very different picture: green rings, low risks, forecasts that stay in range.
4. **Patient app, Venkatesh.** Tap Sun, Mon, Tue and Today to show how each day differs. On Mon, point at the low in the chart.
5. **Same app, Kavya.** Show the wedding day and the recovery.
6. **Assistant.** Tap the small microphone icon, ask a question in Hindi or Kannada, and try "how much insulin should I take" to show the safety rule.
7. **Go live** in the doctor view and the **clinical summary** button, if time allows.

## How the stories were made

The cohort generator makes statistically similar days, so for these two patients the last 14 days are scripted (`src/ingest/demo_stories.py`): carbohydrate load, walks, steps, late dinners, a night low and a gradual improvement. Everything else about them (labs, organ labels, genetics) comes from the normal synthetic cohort, and the forecasts, alerts and organ risks are computed by the same models as for every other patient. Re-run with `python src/ingest/demo_stories.py` and then `python src/api/build_artifacts.py` on the GPU machine.
