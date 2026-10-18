# Demo video script (target 22 to 24 minutes)

Record the screen with the dashboard open (`uvicorn app:app --app-dir src/api --port 8000`), with the slides (`docs/Kaya_presentation.pdf`) ready. Speak slowly. Two presenters can alternate by section. Times are cumulative.

| Time | Section | On screen | Say |
|---|---|---|---|
| 0:00 | Hook | Slide 1 | Introduce the team. "Existing diabetes twins forecast sugar. Kaya shows what sugar does to the liver and eyes, and lets a doctor test a change first." |
| 1:30 | Problem | Slide 2 | India has over 100 million people with diabetes. Complications build silently. Glucose is tracked daily; organs are checked once a year. |
| 3:30 | Landscape | Slide 3 | Walk the table: Twin Health, Fitterfly, Dexcom, Remidio, ARTEMIs. Each covers one slice. The gap is glucose-to-organ in one open system. |
| 5:30 | What Kaya does | Slides 4 and 5 | Two streams fused into one twin. Four questions. The what-if engine. Walk the architecture left to right. |
| 8:00 | Data honesty | Slide 6 | Real versus simulated. Why a bridged synthetic cohort is needed, and what it does and does not prove. |
| 9:30 | Glucose results | Slide 7 | RMSE versus persistence, interval coverage, alert sensitivity, lead time, false alerts. Explain conformal and calibration in one sentence each. |
| 11:30 | Liver results | Slide 8 | AUROC versus FIB-4, FLI, HSI on real FibroScan data. Be clear the 12-month drift is a simulation. |
| 13:00 | Eye results | Slide 9 | APTOS result, then IDRiD zero-shot and fine-tuned. Explain domain shift. Show Grad-CAM. |
| 14:30 | Live demo: doctor | Dashboard, doctor view | Show the triage list and why patients are flagged. Pick a patient. Press **Replay last 3 days** and talk through the forecast fan, the alerts, and the faded actual future. Show an alert's "why". |
| 18:00 | Live demo: what-if | What-if panel | Press the presets one at a time, then **All three**. Read the before and after: time in range, liver, eye. State that these are assumptions shown as a simulation. |
| 20:00 | Live demo: patient | Patient view | One sugar status, one nudge, organ lights, "try a change". |
| 21:00 | Product depth | API docs at /docs, FHIR | Show `/docs`, `/fhir/Patient/{id}`, and mention Docker. |
| 22:00 | Limits and roadmap | Slide 12 | State limitations plainly. Roadmap: kidney, retina preview, multilingual, consent and audit. |
| 23:30 | Close | Slide 13 | Repeat the one-line message. Thank the organisers. |

Tips: keep the replay running while you speak so the forecast fan is visible; do not claim clinical validation; say "simulation" every time you show a what-if number.
