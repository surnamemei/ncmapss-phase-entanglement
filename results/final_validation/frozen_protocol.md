# Frozen external-confirmation protocol

Frozen on 2026-09-25 before inspecting any non-DS02 N-CMAPSS outcomes. The LSTM ceiling was amended from 60 to 300 and then 600 epochs after DS02 training-only validation loss was still decreasing at each earlier ceiling; no phase-FPR or external-confirmation outcome had been evaluated. The stopping rule and all detector/calibration choices were unchanged.

## Status

No N-CMAPSS subset other than `N-CMAPSS_DS02-006.h5` is available locally. DS02 has been repeatedly inspected and is discovery data only. This protocol is therefore frozen for a later one-shot confirmation; no confirmatory result is claimed in the current project.

## Confirmation dataset and split

- Use `N-CMAPSS_DS03-012.h5` obtained from the official NASA N-CMAPSS distribution. If DS03 is unavailable or lacks the required full-flight variables, use the lexicographically first complete non-DS02 N-CMAPSS HDF5 subset with `A`, `W`, and `X_s` schemas matching DS02, and record the substitution before loading outcome arrays.
- Preserve the dataset's official development/test division. Official-test engines are audit engines and must not be examined until every model and threshold-calibration step is complete.
- From the sorted development-engine IDs, assign every fourth engine (positions 4, 8, 12, ...) to threshold calibration and all other development engines to model fitting. If this yields fewer than two calibration engines, use the final two sorted development engines for calibration. This assignment uses engine IDs only.
- Use only rows with `hs = 1` for model fitting, threshold calibration, and healthy false-alarm evaluation. Report this oracle healthy-state restriction explicitly.

## Frozen variables and phase rule

- Detector variables: the 14 measured `X_s` channels used in DS02.
- Operating descriptors: `alt`, `Mach`, `TRA`, and `T2`.
- Primary phase definition only: within each complete flight, cruise is the first through last row at or above `min(alt) + 0.90 * (max(alt) - min(alt))`; earlier rows are climb and later rows are descent.
- This is retrospective phase stratification because it uses the complete altitude trace. It is not an online phase detector.

## Frozen correction and detectors

- Correction: the DS02 Phase-3 history correction with instantaneous operating descriptors, first differences, and causal 30 s and 120 s means, standard deviations, and endpoint slopes. Use cubic instantaneous terms, linear and squared dynamic terms, instantaneous-state-by-derivative interactions, and ridge `alpha = 1.0`.
- Fit the operating regression and residual standardization on model-fitting engines only.
- PCA: five components, full SVD, mean squared standardized-residual reconstruction error.
- Isolation Forest: 200 trees, `max_samples = 8192`, `contamination = "auto"`, seeds 0, 1, and 2; score is negative `score_samples`.
- LSTM sequence reconstruction: LSTM(16)-Dense(8,tanh)-LSTM(16)-Dense(14), sequence length 256, batch size 256, Adam learning rate 0.001, seeds 0, 1, and 2. Select epoch count with engine-disjoint validation drawn only from model-fitting engines, maximum 600 epochs, early-stopping patience 6 and minimum improvement 0.0001. Threshold-calibration and official-test engines must not influence epoch selection.
- Do not add detectors or change hyperparameters after inspecting confirmation outcomes.

## Frozen calibration and endpoints

- Nominal pooled healthy row-FPR targets: 0.5%, 1%, and 2%; 1% is primary.
- For each detector/seed, use the empirical `higher` quantile of pooled healthy calibration-row scores.
- Cross-phase transfer uses the same quantile separately within each calibration phase and applies it to each audit phase.
- Primary outputs: pooled and per-engine overall/climb/cruise/descent healthy row-FPR; descent-minus-climb; descent-minus-cruise; cross-phase transfer matrix; fraction of healthy flights with at least one alarm; and contiguous alarm events per healthy flight.
- Use hierarchical engine/flight bootstrap intervals and re-estimate calibration thresholds inside replicates. Do not use timestamp-level p-values.

## Frozen interpretation rule

The DS02 directional pattern is considered reproduced only if, at the primary 1% target, descent-minus-climb and descent-minus-cruise are positive in the pooled audit result for PCA and for the seed-mean results of both stochastic detector implementations. Report all exceptions and per-engine heterogeneity. Failure of this rule is a negative confirmation and must not trigger retuning.
