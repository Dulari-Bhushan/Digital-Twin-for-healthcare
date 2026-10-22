# Heart watch: stress tests

Patient-grouped split: 1500 training and 500 test patients (10,019 test mornings). Synthetic data; shows behaviour of the method, not clinical accuracy.

## 1. Does the flag use glucose lows?

| Patients | Events | AUROC with lows | AUROC without lows | Gain (95% CI) |
|---|---|---|---|---|
| everyone | 452 | 0.841 | 0.835 | +0.005 (+0.001 to +0.009) |
| insulin or sulfonylurea | 178 | 0.827 | 0.814 | +0.013 (+0.006 to +0.021) |
| not on insulin or su | 274 | 0.844 | 0.843 | +0.001 (-0.002 to +0.004) |

## 2. Wearable gaps and noise (AUROC on all mornings; alerts with abstaining under 4 usable nights)

| Gap | Noise | Usable nights | Scored | AUROC, trained on clean data | AUROC, trained with gaps | Events caught / false alerts per month: clean-trained | Events caught / false alerts per month: gap-trained |
|---|---|---|---|---|---|---|---|
| 0% | 0 | 7.0 / 7 | 100% | 0.841 | 0.831 | 77% / 1.204 | 69% / 1.006 |
| 10% | 0 | 6.37 / 7 | 100% | 0.815 | 0.824 | 82% / 2.3 | 68% / 0.991 |
| 20% | 0 | 5.72 / 7 | 98% | 0.796 | 0.821 | 83% / 3.066 | 64% / 0.922 |
| 30% | 0 | 5.04 / 7 | 90% | 0.772 | 0.807 | 79% / 3.443 | 55% / 0.832 |
| 50% | 0 | 3.7 / 7 | 56% | 0.723 | 0.779 | 52% / 2.713 | 33% / 0.551 |
| 0% | 1 | 7.0 / 7 | 100% | 0.839 | 0.832 | 77% / 1.261 | 71% / 1.006 |
| 0% | 2 | 7.0 / 7 | 100% | 0.834 | 0.831 | 79% / 1.419 | 68% / 1.045 |

## 3. Thin record

| Record fields missing | Fused AUROC | Wearable-only AUROC | Events caught | False alerts per patient-month |
|---|---|---|---|---|
| 0% | 0.841 | 0.831 | 77% | 1.204 |
| 25% | 0.835 | 0.831 | 78% | 1.153 |
| 50% | 0.833 | 0.831 | 77% | 1.078 |
| 100% | 0.831 | 0.831 | 76% | 0.955 |
