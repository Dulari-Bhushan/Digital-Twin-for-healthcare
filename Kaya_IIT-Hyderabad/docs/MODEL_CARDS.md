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

## Explanations

Liver and kidney risk drivers are SHAP values from the same LightGBM models (log-odds contributions). They describe the model's behaviour for one patient and are not causal claims. Alert reasons are rule-based summaries of the inputs the model saw (glucose trend and recent meal). Retina heatmaps are Grad-CAM.

## Data and privacy

Only open or synthetic data is used: CGMacros (PhysioNet), NHANES, APTOS 2019, IDRiD, and a synthetic cohort generated by `src/ingest/synthetic_cohort.py`. No real patient data is stored or processed by the demo.
