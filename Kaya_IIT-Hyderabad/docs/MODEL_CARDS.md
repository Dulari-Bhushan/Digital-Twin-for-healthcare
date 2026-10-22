# Model cards

Kaya is clinical decision support built on open and synthetic data. It is not a diagnostic device and has not been clinically validated. Numbers are from `results/`.

## 1. Glucose forecaster

| | |
|---|---|
| **Purpose** | Forecast glucose 30, 60 and 120 minutes ahead with an 80% interval, and the probability of a high (>180) or low (<70) glucose event within 2 hours |
| **Inputs** | Last 2 hours of glucose, heart rate, activity and meal carbohydrates; age, BMI, HbA1c, sex; time of day |
| **Model** | GRU with quantile and event heads, blended with LightGBM quantile and event models; conformal interval widening; isotonic calibration of event probabilities |
| **Training data** | Synthetic cohort (2,000 patients, 14 days), then fine-tuned on real CGMacros recordings |
| **Evaluation** | Subject-level 5-fold cross-validation on 34 real CGMacros subjects; patient-level split on the synthetic cohort |
| **Results (real data)** | RMSE 12.6 / 21.1 / 28.2 mg/dL at 30 / 60 / 120 min (persistence 16.3 / 25.8 / 36.7); 80% interval coverage 0.80; event ECE 0.003 to 0.005 |
| **Alerts** | At about one false alert per patient-day: 72% of hypoglycemia episodes caught, median 45 minutes of warning |
| **Limits** | Only 34 real subjects, mostly without diabetes complications; CGMacros has few hypoglycemia events; activity channels are mapped between sources with a simple scaling; hypoglycemia alert thresholds on the synthetic cohort are coarse |
| **Not for** | Insulin dosing or automated treatment decisions |
| **Live inference** | The dashboard's live mode and the ingest endpoint run the GRU alone (exported to numpy, verified against PyTorch to within 1e-3), with conformal offsets and isotonic calibration fitted for the GRU alone. The offline results above use the GRU + LightGBM ensemble |

**Two-stream version (offline study).** [`ablate_glucose.py`](../src/models/ablate_glucose.py) trains the same GRU on six dynamic channels (glucose, heart rate, activity, meals, HRV, sleep stage), seven slow-context numbers (last night's sleep length and efficiency, last night and 7-night mean HRV and resting heart rate, 7-night mean steps) and a 20-number static vector (adds diabetes duration, HOMA-IR, medicines, PNPLA3, TCF7L2), on the coupled synthetic cohort. Switching input groups on and off, 3 seeds each, on 381,300 held-out windows (full table in [`results/glucose_ablation_table.md`](../results/glucose_ablation_table.md)): basic record and heart rate with activity give the largest forecast gains (about 1.3 and 0.6 mg/dL at +120 min); medicines raise low-glucose AUROC from 0.85 to 0.95; HRV and sleep add about 0.3 mg/dL at +120 min; genetics add nothing measurable. This model is not in the live demo, which runs the four-channel model above. Real CGMacros recordings have no HRV, sleep or genetics, so the two-stream model has not been tested on real data.

## 2. Liver risk

| | |
|---|---|
| **Purpose** | Probability of hepatic steatosis (CAP >= 288 dB) and advanced fibrosis (stiffness >= 8 kPa) from routine labs |
| **Inputs** | Age, sex, BMI, waist, ALT, AST, platelets, HbA1c, HDL, diabetes status (the validated model also uses GGT) |
| **Model** | Regularised LightGBM |
| **Data** | NHANES 2017-2018, 4,745 adults with a complete FibroScan exam |
| **Results** | Advanced fibrosis AUROC 0.83 (FIB-4: 0.63); steatosis AUROC 0.83 (FLI: 0.82, HSI: 0.79); adults with diabetes 0.76 and 0.80; Asian participants 0.83 |
| **Dynamic component** | A glycemic-load modifier (time above range, variability, daily steps) shifts the log-odds with a 90-day lag. Its coefficients are literature-informed **assumptions**, exposed in `LiverParams`, and shown in the product as a simulation |
| **Limits** | NHANES is a US population; stiffness thresholds are a proxy for biopsy-proven fibrosis; no open dataset links CGM patterns to liver outcomes, so the dynamic component is not validated |

## 3. Retinopathy grader

| | |
|---|---|
| **Purpose** | Grade diabetic retinopathy (0 to 4) from a fundus photo, with a Grad-CAM heatmap |
| **Model** | EfficientNet-B2, ordinal regression, flip test-time augmentation, thresholds tuned for kappa |
| **Data** | Trained on APTOS 2019 (Aravind Eye Hospital); tested on IDRiD (Indian) |
| **Results** | APTOS held-out: kappa 0.89, referable AUROC 0.98. IDRiD test without fine-tuning: kappa 0.57, AUROC 0.88. After fine-tuning on IDRiD train: kappa 0.71, AUROC 0.92, 87% within one grade, 43% exact |
| **Limits** | Camera and population shift is substantial; exact-grade accuracy on IDRiD is modest; small test set (103 images) |
| **Progression risk** | A tabular 2-year progression score from HbA1c, duration, BP, glycemic variability and time in range. Coefficients are **assumptions**, not fitted, and it is shown as a simulation |
| **Images in the dashboard** | Representative IDRiD photos (CC BY 4.0) matched to the patient's recorded grade; the demo patients are synthetic |

## 4. Kidney risk and eGFR path

| | |
|---|---|
| **Purpose** | Probability of albuminuria (UACR >= 30 mg/g) and reduced eGFR (< 60), plus a 5-year eGFR path and the albuminuria drift over 12 months |
| **Inputs** | Age, sex, BMI, waist, HbA1c, systolic and diastolic BP, HDL, diabetes status (creatinine is deliberately not an input) |
| **Model** | Regularised LightGBM |
| **Data** | NHANES 2017-2018, 4,827 adults with serum creatinine and urine albumin/creatinine; eGFR by CKD-EPI 2021 |
| **Results** | AUROC 0.76 (albuminuria), 0.85 (reduced eGFR), 0.79 (any CKD); adults with diabetes 0.70, 0.77, 0.71. Only a small edge over a simple age, BP, HbA1c and diabetes baseline (0.75, 0.85, 0.78) |
| **Trajectory** | eGFR declines linearly at a patient-specific slope: about 0.9 mL/min/1.73m2 per year for aging plus terms for HbA1c above 7, systolic BP above 120, existing albuminuria and glucose variability. These coefficients are literature-informed **assumptions**, exposed in `KidneyParams`, and shown as a simulation. Blood pressure is not changed by the what-if engine |
| **Limits** | US population; single time point labels; the baseline is already strong, so the learned model adds little; the path is not fitted to longitudinal outcomes |

## 5. What-if engine

Splits a patient's glucose into a slow baseline and meal-driven excursions, rescales excursions after meals (portion size, walking after meals) and shifts the baseline (medication), then recomputes glucose metrics and feeds them to the liver and eye modules. Effect sizes (a walk after a meal blunts the excursion by about a third; a 25% carbohydrate reduction scales excursions by 0.75) are literature-informed assumptions. Output is a simulation to support a conversation, not a prediction.

**Medicine by medicine.** Besides the single "all medicines together" slider, each of the patient's glucose-lowering medicines can be stopped, changed by 25% either way, or a new one added ([`medicines.py`](../src/whatif/medicines.py)). Each drug has its own assumed effect on mean glucose (for example metformin about -20 mg/dL, insulin glargine -25, glimepiride -18, dapagliflozin -14, sitagliptin -12, semaglutide -30), and insulin and glimepiride also make low-glucose dips rarer or more frequent. These are average, literature-informed assumptions, not the patient's own response. Medicines with no glucose effect in the model (telmisartan, atorvastatin) are listed but cannot be changed, and changes that do not apply (adding a drug already taken) are rejected. The doctor can also add a medicine the list does not cover (up to five): a free-text name, an estimated change in average glucose, and whether it can cause lows; typical values are suggested (for example a steroid raises glucose) but the number is the doctor's own estimate.

## 6. Cardiovascular flag (Heart watch)

| | |
|---|---|
| **Purpose** | Every morning at 10:00, the probability of a cardiovascular event in the next 72 hours, with a "review suggested" alert above a threshold and the factors behind the score. Shown to the doctor inside the Doctor view |
| **Inputs** | Wearable and glucose sensor: seven nightly cycles of sleep length, efficiency, deep and REM share, bed and wake time, night HRV (RMSSD), resting and night heart rate, daytime HRV and heart rate, daily steps, glucose mean, variability, time in range, night glucose, minutes below 70 and below 54 mg/dL and lowest glucose, summarised as last night, 7-night mean, change over the week and the last two days against the two before (76 features). Record: age, sex, BMI, systolic and diastolic BP, HbA1c, diabetes duration, LDL, HDL, triglycerides, smoking, prior cardiovascular disease, eGFR, urine albumin, insulin or sulfonylurea use (15 features) |
| **Model** | Late fusion. A LightGBM classifier on the wearable and glucose features and a logistic model on the record give two log-odds; a three-parameter logistic stacker, fitted on out-of-fold scores of every training patient, combines them. Explanations are per-feature contributions from both parts on one log-odds scale, tagged record, wearable or glucose sensor. Trained on the clean data plus two copies with whole days of wearable data removed and extra sensor noise, so a missing night is something it has seen |
| **Thin data** | A missing record field is filled with the training median, so a patient with no record is scored as an average patient and the card says the record is not on file. With fewer than 4 usable nights in the last seven the flag abstains: no score, no alert, and the card says "Not enough data" |
| **Data** | Coupled synthetic cohort (`src/ingest/cohort_v2.py --hypo-link`): 2,000 patients, 28 days, 676 events and 1,275 benign look-alike episodes. In insulin or sulfonylurea users a level-2 low (below 54 mg/dL for 15 minutes) can start a short prodrome; this link is an assumption of the simulator. Mornings in the 72 hours after an event are not scored (the patient would be in care) |
| **Evaluation** | 5-fold cross-validation grouped by patient; thresholds chosen on the training patients for about one false alert per patient-month; intervals from resampling patients. Stress tests (`src/models/cardio_robust.py`, `results/cardio_robustness.md`) on 500 held-out patients |
| **Results** | AUROC 0.82 (95% CI 0.80 to 0.83), AUPRC 0.29 (prevalence 0.044), Brier 0.036, calibration error 0.002. 71% of 622 events caught, median warning 22 hours, 1.0 false alerts per patient-month. Wearable and glucose alone: AUROC 0.80; record alone: 0.69; simple clinical rule: 0.68 (41% caught). The gain over the wearable alone is +0.018 AUROC (95% CI +0.012 to +0.025). Among mornings already inside a prodromal episode, the record alone separates dangerous from benign (AUROC 0.80) better than the wearable (0.69) or the fused score (0.75) |
| **Stress tests** | Glucose lows add +0.005 AUROC overall (95% CI +0.001 to +0.009) and +0.013 in insulin or sulfonylurea users (+0.006 to +0.021), and nothing in others. With 30% of days missing the AUROC falls from 0.83 to 0.81 (a flag trained only on clean data falls to 0.77 and raises 3.4 false alerts per patient-month instead of 0.8); with half the days missing only 56% of mornings can be scored and 33% of events are caught. With no record at all the AUROC is 0.83, the same as the wearable alone, because the simulated wearable carries nearly all of the signal |
| **Limits** | Trained and tested on synthetic data whose couplings and event rate we chose; about 32 events per 100 patients per month, far above real life, so precision would be lower at real rates. The simulated wearable was built with a prodrome in it and real devices are noisier, so the no-record and missing-data results are an upper bound. False alerts concentrate in patients with a high-risk record. No real wearable cohort with cardiovascular outcomes was available to validate it |
| **Not for** | Diagnosis, or deciding on treatment. It is a prompt to review a patient |
| **Demo** | `artifacts/cardio/`: eight patients scored by the cross-validation model that never saw them: a caught event (two), a missed event, a benign scare the record calmed, a false alarm, a quiet high-risk patient, a patient whose watch was often off and a patient with no record. Rebuild with `src/api/build_cardio_artifacts.py` |

## Voice and chat assistant

| | |
|---|---|
| **Purpose** | Help older patients understand their screens and numbers, and navigate the app, by voice or text in English, Hindi, Telugu and Kannada |
| **Models** | Sarvam AI: Saaras v4 (speech to text), Bulbul v4 Flash (text to speech), Sarvam-105B conversations (chat). Called from the server; the key never reaches the browser |
| **Grounding** | The model sees only a compact summary of this patient's twin (glucose now and forecast, 14-day time in range, organ risks), a glossary and a description of the app. It is told to use only those facts |
| **Safety (in code, before and after the model)** | Emergency words in four languages return a fixed "call 108 or go to the nearest hospital" message and never reach the model. Medicine, insulin and dose questions return a fixed referral to the doctor. Navigation requests are handled by rules. Any model reply containing dose advice is replaced, and replies are stripped of formatting and length-limited |
| **Tests** | 21 tests cover emergency, medicine and navigation rules in four languages, the reply filter (including that "mg/dL" is not treated as a dose), that rule-handled messages never call the model, and graceful behaviour without a key |
| **Limits** | The language model can still be wrong or too cheerful; the Hindi, Telugu and Kannada wording and speech quality need native-speaker review; it gives general guidance, not medical advice; the demo uses synthetic data only, and a real deployment needs patient consent and a data-processing agreement with the provider |

## Explanations

Liver and kidney risk drivers are SHAP values from the same LightGBM models (log-odds contributions). They describe the model's behaviour for one patient and are not causal claims. Alert reasons are rule-based summaries of the inputs the model saw (glucose trend and recent meal). Retina heatmaps are Grad-CAM.

## Data and privacy

Only open or synthetic data is used: CGMacros (PhysioNet), NHANES, APTOS 2019, IDRiD, and synthetic cohorts generated by `src/ingest/synthetic_cohort.py` and `src/ingest/cohort_v2.py`. No real patient data is stored or processed by the demo.
