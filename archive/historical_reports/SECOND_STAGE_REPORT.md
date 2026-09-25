# HISTORICAL SCREENING REPORT — NOT AN AUTHORITATIVE MANUSCRIPT SOURCE

# Second-stage falsification audit: operating-condition-corrected PCA

## Decision

**STRONG GO for expanding the investigation to additional detector families.** This is a screening decision under the requested logic, not evidence of causality or publication readiness.

The original phase effect was reduced on one transfer metric but was not largely removed by explicit correction for the four supplied operating descriptors. With the corrected detector, healthy official-test FPR was 0.146% in climb, 0.583% in cruise, and 3.00% in descent. The worst off-diagonal phase-transfer FPR was 14.31%, and phase could be predicted from the corrected anomaly score alone at 50.8% balanced accuracy versus 33.3% chance. The conclusion remained the same under the alternative phase rule. In seven same-flight-class engine-held-out audits, descent had the highest corrected FPR in all seven.

This result falsifies the narrow explanation that the first-stage result was removed by a flexible static correction for `W = [alt, Mach, TRA, T2]`. It does not rule out richer normal-condition explanations such as transient dynamics, direction-dependent hysteresis, omitted operating variables, or a more flexible conditional model.

## Protocol

The data file is `N-CMAPSS/N-CMAPSS_DS02-006.h5`, previously verified byte-for-byte against the DS02 member of NASA's official archive.

- Training engines: development units 2, 5, 10, 16.
- Calibration engines: development units 18, 20.
- Official audit engines: test units 11, 14, 15.
- Healthy rows only: `hs = 1`. The health flag is used only to select rows.
- Detector sensors: the 14 supplied physical measurements in `X_s`.
- Operating model inputs: `alt`, `Mach`, `TRA`, and `T2` only.
- Excluded inputs: health state, unit, cycle, flight class, RUL, fault/health parameters, virtual sensors, and all test-derived quantities.

The operating model standardizes `W` on healthy training engines, expands it to the complete degree-3 polynomial basis including interactions, and fits one multi-output ridge regression with fixed `alpha = 1`. Residuals are observed sensors minus predicted sensors. Their standardization and the 5-component PCA are fitted only on healthy training-engine residuals. The raw detector was recomputed with the same split and float64 precision.

The regression is a static, nonlinear conditional mean model. Across calibration and official-test data, sensor-wise R² ranges from 0.99896 to effectively 1.0. Only 1.39% of official-test `T2` values and at most 0.052% of the other descriptor values fall outside the training min/max ranges. This makes gross regression failure or broad extrapolation an unlikely explanation for the surviving pattern.

## Direct comparison on official test engines

All values below use the pooled healthy-validation 99th-percentile threshold for the corresponding detector. FPR values are row-level and time-weighted.

| Metric | Raw PCA | Condition-corrected PCA |
|---|---:|---:|
| Overall healthy FPR | 1.105% | 1.277% |
| Climb FPR | 0.0035% | 0.146% |
| Cruise FPR | 0.600% | 0.583% |
| Descent FPR | 2.580% | 3.001% |
| Maximum/minimum phase FPR | 739.9× | 20.5× |
| Worst off-diagonal phase-transfer FPR | 22.45% | 14.31% |
| Score-only phase balanced accuracy | 45.0% | 50.8% |

The raw maximum/minimum ratio is inflated by a nearly zero climb rate. The corrected ratio is less extreme but remains large, and correction does not reduce the descent FPR or the phase-prediction result.

![Raw and corrected phase FPR](figures/second_stage/raw_vs_corrected_fpr.png)

## Corrected detector by engine and flight class

The official test mapping is one engine per flight class, so class and engine effects cannot be separated for classes 1 and 2.

| Unit | Fc | Overall | Climb | Cruise | Descent |
|---:|---:|---:|---:|---:|---:|
| 11 | 3 | 1.089% | 0.0876% | 0.469% | 2.558% |
| 14 | 1 | 1.995% | 0.580% | 1.103% | 3.764% |
| 15 | 2 | 1.197% | 0.102% | 0.443% | 3.266% |

All three unseen engines retain the same phase ordering after correction. Unit 11 supplies the clean official matched-class result because every development engine is also Fc 3.

## Cross-phase threshold transfer

Each row uses the 99th percentile of healthy validation scores from only that calibration phase. Cells are corrected-detector FPRs on all healthy official-test rows in the indicated audit phase.

| Calibration phase | Test climb | Test cruise | Test descent |
|---|---:|---:|---:|
| Climb | 1.22% | 2.96% | **14.31%** |
| Cruise | 0.64% | 1.49% | **8.79%** |
| Descent | 0.08% | 0.42% | 1.22% |

For matched-Fc unit 11 alone, the climb-calibrated threshold gives 0.59% in climb, 2.52% in cruise, and **12.61% in descent**. The calibration failure therefore does not depend on pooling classes 1 and 2.

![Corrected threshold transfer](figures/second_stage/corrected_threshold_transfer.png)

## Same-flight-class engine-held-out control

All six development engines and official test unit 11 are Fc 3. For each development audit unit, one different engine was reserved for calibration and the other four were used for model fitting. The official unit-11 audit retained the original four-train/two-calibration split. Thus no audited engine contributed to its model or threshold.

Across the seven corrected-PCA audits:

- Descent had the highest FPR in 7/7 audits.
- Median phase FPRs were 0.0497% climb, 0.469% cruise, and 2.558% descent.
- Corrected descent FPR ranged from 1.85% to 4.07%.
- Median worst off-diagonal transfer FPR was 13.84%, with a range of 12.58% to 35.53%.
- Median score-only phase balanced accuracy was 51.4%, with a range of 48.5% to 53.6%.

These are descriptive engine-level replications. No timestamp-level confidence intervals were computed. The small number of distinct engines does not support precise uncertainty claims, and timestamp resampling would create false precision.

## Temporal dependence and flight-level alarms

A false-alarm event is defined as the start of a contiguous run of above-threshold rows within a flight or phase segment. This prevents a long uninterrupted alarm from being counted once per timestamp, while retaining row-level FPR for comparison with stage one.

For the corrected detector across 76 healthy official-test flights:

| Segment | Flights with ≥1 alarm | Events per healthy flight |
|---|---:|---:|
| Climb | 22.4% | 0.66 |
| Cruise | 65.8% | 5.17 |
| Descent | 98.7% | 16.76 |
| Entire flight | 100.0% | 22.50 |

At whole-flight level, all 18 unit-11 flights, all 35 unit-14 flights, and all 23 unit-15 flights contain at least one corrected-detector alarm. Event counts per flight are 44.8, 12.1, and 20.9, respectively. These high counts show that alarms are not confined to one or two isolated flights, though rapid score crossings fragment some alarm periods into many events. Full per-flight results are retained in `results/second_stage/flight_alarm_detail.csv`.

For comparison, raw PCA produces at least one alarm in 72.4% of healthy test flights and 12.3 contiguous events per flight overall. Condition correction changes the score geometry and raises these temporal metrics; it does not suppress the phase pattern.

## Phase-definition sensitivity

The primary rule is unchanged from stage one: cruise spans the first through last crossing of 90% of each flight's altitude range. The predeclared alternative uses both altitude and altitude rate: cruise spans the first through last row above 85% of the flight altitude range whose centered 60-second altitude rate has magnitude no greater than 2 ft/s. Rows before and after are climb and descent. The dataset is sampled at 1 Hz; no phase threshold was selected from anomaly scores.

The alternative rule changes the total split from 27.1/40.9/32.0% to 29.0/39.0/32.1% climb/cruise/descent. Every flight has nonempty segments under both rules.

| Corrected-detector metric | Primary | Altitude-plus-rate |
|---|---:|---:|
| Climb FPR | 0.146% | 0.164% |
| Cruise FPR | 0.583% | 0.412% |
| Descent FPR | 3.001% | 3.136% |
| Maximum/minimum phase FPR | 20.5× | 19.1× |
| Worst off-diagonal transfer FPR | 14.31% | 15.06% |
| Score-only phase balanced accuracy | 50.8% | 52.9% |

The conclusion does not materially change under the alternative definition.

## Interpretation

The operating correction removes nearly all variance in each raw sensor attributable to a flexible static function of `W`, yet marked phase structure remains in PCA reconstruction scores. The evidence survives a matched-Fc official audit, six additional Fc-3 engine-held-out audits, flight-level aggregation, and the alternative phase definition. Under the requested decision rule, that is a **STRONG GO**.

The strongest remaining falsification target is dynamic operating correction: models that condition on rates, lagged `W`, and direction of travel may explain the residual phase structure without invoking a detector-specific pathology. The present result justifies testing that question and additional detector families later. No LSTM, Transformer, or manuscript was created in this stage.

## Artifacts

The reproducible implementation is `src/second_stage_audit.py`. Outputs are under `results/second_stage/`, including:

- `raw_vs_corrected_comparison.csv`
- `row_false_alarm_rates.csv`
- `score_distributions.csv`
- `threshold_transfer_matrix.csv`
- `score_only_phase_prediction.csv`
- `matched_fc_engine_audits.csv`
- `flight_alarm_detail.csv` and `flight_alarm_summary.csv`
- `per_flight_class_row_fpr.csv` and `per_flight_class_flight_metrics.csv`
- `phase_sensitivity_summary.csv` and `phase_definition_audit.csv`
- `operating_regression_metrics.csv` and `operating_support_audit.csv`
- `run_config.json`
