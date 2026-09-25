# Final validation report

> This report is generated from `canonical_results.csv` and executed validation artifacts. DS02 is discovery data, not untouched confirmation.

## Canonical primary results

| Detector | Overall | Climb | Cruise | Descent | D-C climb | D-C cruise | Max/min | Worst transfer | Phase BA |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| isolation_forest | 1.127% | 0.268% | 0.558% | 2.487% | 2.219% | 1.928% | 9.33× | 27.281% | 47.8% |
| lstm_autoencoder | 1.118% | 0.488% | 0.729% | 2.080% | 1.592% | 1.351% | 4.28× | 5.954% | 46.1% |
| pca | 1.363% | 0.125% | 0.428% | 3.459% | 3.335% | 3.031% | 27.75× | 15.555% | 51.0% |

## LSTM convergence

- Seed 0: selected epoch 600; stopped after 600 epochs; best validation loss 0.137448.
- Seed 1: selected epoch 256; stopped after 262 epochs; best validation loss 0.178103.
- Seed 2: selected epoch 451; stopped after 453 epochs; best validation loss 0.149171.

The middle-only sensitivity result retains descent as the highest-FPR phase. Seed-mean middle-only FPRs are climb 0.182%, cruise 0.667%, and descent 1.982%.

## Cluster-aware uncertainty

Intervals use 2,000 hierarchical engine-then-flight bootstrap replicates and re-estimate pooled and phase-specific calibration thresholds in every replicate. With only three audit engines and two calibration engines, intervals remain intrinsically imprecise.

| Detector | Metric | Mean | 95% interval |
|---|---|---:|---:|
| isolation_forest, seed 0 | climb_fpr | 0.367% | 0.084%–1.356% |
| isolation_forest, seed 0 | cruise_fpr | 0.626% | 0.272%–1.361% |
| isolation_forest, seed 0 | descent_fpr | 2.506% | 1.372%–4.670% |
| isolation_forest, seed 0 | descent_minus_climb | 2.138% | 0.850%–4.074% |
| isolation_forest, seed 0 | descent_minus_cruise | 1.880% | 0.678%–3.749% |
| isolation_forest, seed 0 | overall_fpr | 1.186% | 0.670%–2.215% |
| isolation_forest, seed 0 | worst_cross_phase_transfer_fpr | 31.124% | 16.648%–48.823% |
| isolation_forest, seed 1 | climb_fpr | 0.317% | 0.070%–1.219% |
| isolation_forest, seed 1 | cruise_fpr | 0.589% | 0.239%–1.347% |
| isolation_forest, seed 1 | descent_fpr | 2.796% | 1.607%–4.755% |
| isolation_forest, seed 1 | descent_minus_climb | 2.479% | 1.313%–4.166% |
| isolation_forest, seed 1 | descent_minus_cruise | 2.207% | 1.012%–3.943% |
| isolation_forest, seed 1 | overall_fpr | 1.257% | 0.730%–2.277% |
| isolation_forest, seed 1 | worst_cross_phase_transfer_fpr | 26.707% | 14.434%–42.556% |
| isolation_forest, seed 2 | climb_fpr | 0.337% | 0.074%–1.281% |
| isolation_forest, seed 2 | cruise_fpr | 0.638% | 0.267%–1.413% |
| isolation_forest, seed 2 | descent_fpr | 2.596% | 1.482%–4.599% |
| isolation_forest, seed 2 | descent_minus_climb | 2.259% | 1.063%–3.947% |
| isolation_forest, seed 2 | descent_minus_cruise | 1.958% | 0.742%–3.709% |
| isolation_forest, seed 2 | overall_fpr | 1.215% | 0.696%–2.183% |
| isolation_forest, seed 2 | worst_cross_phase_transfer_fpr | 28.242% | 15.104%–44.655% |
| lstm_autoencoder, seed 0 | climb_fpr | 0.561% | 0.171%–1.846% |
| lstm_autoencoder, seed 0 | cruise_fpr | 0.776% | 0.389%–1.558% |
| lstm_autoencoder, seed 0 | descent_fpr | 2.157% | 1.230%–3.420% |
| lstm_autoencoder, seed 0 | descent_minus_climb | 1.596% | 0.317%–2.838% |
| lstm_autoencoder, seed 0 | descent_minus_cruise | 1.381% | 0.528%–2.490% |
| lstm_autoencoder, seed 0 | overall_fpr | 1.180% | 0.673%–1.993% |
| lstm_autoencoder, seed 0 | worst_cross_phase_transfer_fpr | 6.315% | 3.337%–10.419% |
| lstm_autoencoder, seed 1 | climb_fpr | 0.575% | 0.200%–1.881% |
| lstm_autoencoder, seed 1 | cruise_fpr | 0.794% | 0.412%–1.500% |
| lstm_autoencoder, seed 1 | descent_fpr | 2.126% | 1.206%–3.293% |
| lstm_autoencoder, seed 1 | descent_minus_climb | 1.551% | -0.022%–2.817% |
| lstm_autoencoder, seed 1 | descent_minus_cruise | 1.332% | 0.399%–2.454% |
| lstm_autoencoder, seed 1 | overall_fpr | 1.181% | 0.717%–1.887% |
| lstm_autoencoder, seed 1 | worst_cross_phase_transfer_fpr | 7.518% | 3.762%–12.290% |
| lstm_autoencoder, seed 2 | climb_fpr | 0.666% | 0.210%–2.182% |
| lstm_autoencoder, seed 2 | cruise_fpr | 0.809% | 0.413%–1.568% |
| lstm_autoencoder, seed 2 | descent_fpr | 2.122% | 1.174%–3.440% |
| lstm_autoencoder, seed 2 | descent_minus_climb | 1.456% | -0.347%–2.802% |
| lstm_autoencoder, seed 2 | descent_minus_cruise | 1.313% | 0.330%–2.511% |
| lstm_autoencoder, seed 2 | overall_fpr | 1.207% | 0.718%–2.027% |
| lstm_autoencoder, seed 2 | worst_cross_phase_transfer_fpr | 6.378% | 3.358%–11.305% |
| pca | climb_fpr | 0.141% | 0.015%–0.367% |
| pca | cruise_fpr | 0.438% | 0.267%–0.659% |
| pca | descent_fpr | 3.566% | 2.171%–5.837% |
| pca | descent_minus_climb | 3.425% | 2.070%–5.629% |
| pca | descent_minus_cruise | 3.128% | 1.808%–5.261% |
| pca | overall_fpr | 1.409% | 0.899%–2.262% |
| pca | worst_cross_phase_transfer_fpr | 16.449% | 10.796%–24.694% |

## Confirmation status

No non-DS02 N-CMAPSS subset is available locally. No confirmatory outcome was run or claimed. The one-shot external protocol was frozen before this validation in `frozen_protocol.md`. DS02 results must be framed as exploratory/discovery evidence.

## Claim audit

| Supported claim | Unsupported / too-strong claim |
|---|---|
| Phase-dependent healthy false-alarm rates were observed across three tested detector implementations under a common preprocessing and calibration protocol on DS02. | The effect is detector-independent. |
| The tested static, derivative, and finite-history correction specifications did not remove the DS02 phase pattern. | Hysteresis or a causal dynamic mechanism has been established. |
| Pooled healthy-score thresholds transferred unevenly between retrospective phase strata. | Phase-aware thresholds are deployment-ready. |
| Alarm occupancy and event burden differed by phase in this simulated dataset. | The results establish real-aircraft operational validity. |
| The analysis characterizes healthy false alarms. | The detectors have superior anomaly-detection accuracy or fault sensitivity. |

## Final verdict

STRONG GO BUT NEEDS VALIDATION

The internal blockers are resolved if the convergence and boundary outputs above are stable, but external confirmation remains outstanding. An exploratory manuscript is supportable only if DS02 is explicitly presented as discovery evidence and the claim language remains narrow.
