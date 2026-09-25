# One-shot DS03 confirmation

Source: official NASA N-CMAPSS DS03. Healthy-state (`hs = 1`) rows only; this is an oracle restriction. The phase rule uses each complete flight's altitude trace retrospectively.

The official test arrays were opened once, after all model fitting and calibration thresholds were locked.

## Frozen split and LSTM selection

Model-fitting units: [1, 2, 3, 5, 6, 7, 9]; threshold-calibration units: [4, 8].
LSTM epoch-selection fit units: [1, 2, 3, 5, 6, 7]; validation unit: 9.
Selected epochs: {0: 170, 1: 200, 2: 230}.

## Primary 1% pooled result

| Detector | Seed | Overall | Climb | Cruise | Descent | Descent−climb | Descent−cruise |
|---|---:|---:|---:|---:|---:|---:|---:|
| pca | -1 | 1.341% | 0.877% | 0.912% | 1.977% | 1.100% | 1.066% |
| isolation_forest | 0 | 1.364% | 0.417% | 1.095% | 2.166% | 1.749% | 1.071% |
| isolation_forest | 1 | 1.332% | 0.399% | 1.060% | 2.127% | 1.728% | 1.067% |
| isolation_forest | 2 | 1.370% | 0.412% | 1.157% | 2.134% | 1.722% | 0.976% |
| lstm_autoencoder | 0 | 1.713% | 0.759% | 1.795% | 2.231% | 1.472% | 0.436% |
| lstm_autoencoder | 1 | 1.730% | 0.719% | 1.890% | 2.220% | 1.501% | 0.330% |
| lstm_autoencoder | 2 | 1.764% | 0.774% | 1.982% | 2.193% | 1.419% | 0.210% |

## Frozen directional interpretation

REPRODUCED

The rule requires positive pooled descent−climb and descent−cruise for PCA and for seed means of Isolation Forest and LSTM.

No hyperparameter was changed after opening the official test arrays.

- pca: descent−climb 1.100%; descent−cruise 1.066%.
- isolation_forest: descent−climb 1.733%; descent−cruise 1.038%.
- lstm_autoencoder: descent−climb 1.464%; descent−cruise 0.325%.

## Per-engine heterogeneity at the primary target

| Detector | Seed | Engine | Climb | Cruise | Descent | Descent−climb | Descent−cruise |
|---|---:|---|---:|---:|---:|---:|---:|
| pca | -1 | engine_10 | 1.258% | 1.247% | 2.448% | 1.190% | 1.201% |
| pca | -1 | engine_11 | 0.383% | 0.878% | 2.173% | 1.790% | 1.294% |
| pca | -1 | engine_12 | 0.322% | 1.039% | 1.061% | 0.739% | 0.022% |
| pca | -1 | engine_13 | 1.120% | 0.744% | 2.249% | 1.129% | 1.505% |
| pca | -1 | engine_14 | 0.744% | 0.587% | 1.431% | 0.686% | 0.843% |
| pca | -1 | engine_15 | 1.112% | 0.846% | 2.153% | 1.041% | 1.307% |
| isolation_forest | 0 | engine_10 | 0.374% | 1.197% | 3.113% | 2.739% | 1.917% |
| isolation_forest | 0 | engine_11 | 0.288% | 1.158% | 2.281% | 1.993% | 1.123% |
| isolation_forest | 0 | engine_12 | 0.847% | 0.617% | 1.845% | 0.998% | 1.229% |
| isolation_forest | 0 | engine_13 | 0.453% | 1.274% | 2.665% | 2.212% | 1.390% |
| isolation_forest | 0 | engine_14 | 0.288% | 1.095% | 1.282% | 0.994% | 0.187% |
| isolation_forest | 0 | engine_15 | 0.378% | 0.971% | 1.495% | 1.117% | 0.524% |
| isolation_forest | 1 | engine_10 | 0.335% | 1.171% | 3.155% | 2.820% | 1.984% |
| isolation_forest | 1 | engine_11 | 0.307% | 1.117% | 2.318% | 2.011% | 1.201% |
| isolation_forest | 1 | engine_12 | 0.839% | 0.550% | 1.696% | 0.857% | 1.146% |
| isolation_forest | 1 | engine_13 | 0.419% | 1.378% | 2.604% | 2.185% | 1.226% |
| isolation_forest | 1 | engine_14 | 0.276% | 0.910% | 1.105% | 0.829% | 0.196% |
| isolation_forest | 1 | engine_15 | 0.355% | 0.901% | 1.516% | 1.161% | 0.615% |
| isolation_forest | 2 | engine_10 | 0.389% | 1.314% | 3.232% | 2.844% | 1.918% |
| isolation_forest | 2 | engine_11 | 0.296% | 1.213% | 2.290% | 1.994% | 1.077% |
| isolation_forest | 2 | engine_12 | 0.808% | 0.573% | 1.689% | 0.881% | 1.116% |
| isolation_forest | 2 | engine_13 | 0.450% | 1.428% | 2.619% | 2.169% | 1.190% |
| isolation_forest | 2 | engine_14 | 0.258% | 1.089% | 1.169% | 0.911% | 0.080% |
| isolation_forest | 2 | engine_15 | 0.372% | 0.981% | 1.446% | 1.074% | 0.466% |
| lstm_autoencoder | 0 | engine_10 | 0.703% | 2.519% | 3.696% | 2.992% | 1.176% |
| lstm_autoencoder | 0 | engine_11 | 0.545% | 1.956% | 2.671% | 2.126% | 0.714% |
| lstm_autoencoder | 0 | engine_12 | 1.141% | 0.585% | 1.237% | 0.097% | 0.652% |
| lstm_autoencoder | 0 | engine_13 | 0.913% | 2.397% | 2.690% | 1.777% | 0.292% |
| lstm_autoencoder | 0 | engine_14 | 0.693% | 0.904% | 0.992% | 0.299% | 0.088% |
| lstm_autoencoder | 0 | engine_15 | 0.693% | 1.323% | 1.556% | 0.863% | 0.233% |
| lstm_autoencoder | 1 | engine_10 | 0.705% | 2.793% | 3.906% | 3.201% | 1.113% |
| lstm_autoencoder | 1 | engine_11 | 0.504% | 2.041% | 2.619% | 2.115% | 0.579% |
| lstm_autoencoder | 1 | engine_12 | 1.093% | 0.614% | 1.210% | 0.117% | 0.595% |
| lstm_autoencoder | 1 | engine_13 | 0.842% | 2.412% | 2.667% | 1.825% | 0.254% |
| lstm_autoencoder | 1 | engine_14 | 0.681% | 0.849% | 0.918% | 0.237% | 0.070% |
| lstm_autoencoder | 1 | engine_15 | 0.634% | 1.445% | 1.449% | 0.815% | 0.004% |
| lstm_autoencoder | 2 | engine_10 | 0.713% | 2.934% | 4.083% | 3.370% | 1.149% |
| lstm_autoencoder | 2 | engine_11 | 0.550% | 2.141% | 2.652% | 2.102% | 0.510% |
| lstm_autoencoder | 2 | engine_12 | 1.036% | 0.487% | 0.950% | -0.086% | 0.463% |
| lstm_autoencoder | 2 | engine_13 | 0.951% | 2.810% | 2.705% | 1.754% | -0.105% |
| lstm_autoencoder | 2 | engine_14 | 0.651% | 0.746% | 0.784% | 0.133% | 0.039% |
| lstm_autoencoder | 2 | engine_15 | 0.792% | 1.378% | 1.344% | 0.552% | -0.034% |

Per-engine directional exceptions: 3 of 42 detector/seed/engine rows. Every exception is visible in the table above.

## Hierarchical uncertainty

Intervals resample engines, then flights within engines, with calibration thresholds re-estimated in each of 2,000 replicates.

| Detector | Seed | Difference | Bootstrap mean | 95% interval |
|---|---:|---|---:|---:|
| isolation_forest | 0 | descent_minus_climb | 1.777% | 0.901%–2.847% |
| isolation_forest | 0 | descent_minus_cruise | 1.108% | 0.404%–1.994% |
| pca | -1 | descent_minus_climb | 1.119% | 0.434%–1.785% |
| pca | -1 | descent_minus_cruise | 1.071% | 0.560%–1.573% |
| isolation_forest | 1 | descent_minus_climb | 1.759% | 0.891%–2.833% |
| isolation_forest | 1 | descent_minus_cruise | 1.099% | 0.426%–1.976% |
| isolation_forest | 2 | descent_minus_climb | 1.740% | 0.871%–2.772% |
| isolation_forest | 2 | descent_minus_cruise | 1.008% | 0.347%–1.862% |
| lstm_autoencoder | 0 | descent_minus_climb | 1.528% | 0.536%–2.870% |
| lstm_autoencoder | 0 | descent_minus_cruise | 0.491% | -0.222%–1.201% |
| lstm_autoencoder | 1 | descent_minus_climb | 1.588% | 0.512%–3.022% |
| lstm_autoencoder | 1 | descent_minus_cruise | 0.408% | -0.270%–1.158% |
| lstm_autoencoder | 2 | descent_minus_climb | 1.493% | 0.379%–3.059% |
| lstm_autoencoder | 2 | descent_minus_cruise | 0.262% | -0.582%–1.025% |

All targets, the full cross-phase transfer matrix, and flight alarm burden are in the accompanying CSV files.
