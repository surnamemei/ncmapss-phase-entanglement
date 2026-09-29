# CVAE specification: the single condition-aware representation baseline

**Status.** FROZEN before any real training. Amendment 2 (`AMENDMENTS.md`) added two numerical safeguards after a stop-rule halt, before any outcome existed. The code is `src/ext_cvae.py`, and data-free tests are in `tests/test_extension_cvae.py`. Changes after the freeze follow `GENERALIZATION_PROTOCOL.md` §22 (amendments).

## 1. Purpose and scope

The brief (§4) asks whether explicit conditioning of the anomaly representation on operating context removes the calibration-transport problem.

**What this model is.** Exactly one modest conditional variational autoencoder (CVAE). It is fixed before audit outcomes exist, and it is calibrated and evaluated with the same arms and endpoints as residual PCA, Isolation Forest and the past-only LSTM.

**What it is not:**
- It is not a reproduction of the SA-CVAE of Chen et al. (2026, RESS 267:111894). From the full text, that model:
  - feeds operating-condition (OC) variables as conditional inputs to the encoder and decoder;
  - adds self-attention layers;
  - uses the logarithmic reconstruction probability averaged over L latent samples as its health indicator;
  - sets a kernel-density 95% threshold on validation data.
- It enters no architecture competition. There is no self-attention, no hyperparameter search and no tuning on any official-test or abnormal-state quantity.

## 2. Inputs

| Input | Definition | Standardization |
| --- | --- | --- |
| x (14) | The frozen `SENSORS` channels of `X_s` | Mean and SD of the model's own training rows (selection-fit rows for the selection model, all fit-pool rows for the refit) |
| c (32) | `phase3_dynamic.causal_descriptors(W, meta)`: `W` (alt, Mach, TRA, T2), the first difference, and the trailing 30-s and 120-s means, SDs and slopes. All of these reset at flight boundaries and use current and past samples only. These are the operating descriptors of the frozen residual correction | Same rule |

**Never inputs:** phase labels, `hs`, flight class (Fc), unit or engine ID, cycle number, `X_v`, `T`, `Y`, or any official-test statistic.

**Training rows.** Training uses `hs = 1` rows of the dataset's fit pool only. This is the same disclosed oracle healthy-row restriction as the other detectors: `hs` selects rows but is never a feature.

## 3. Architecture

| Part | Specification |
| --- | --- |
| Encoder q(z \| x, c) | [x; c] (46) → Linear 128 → ReLU → Linear 128 → ReLU → Linear 8, giving μ_z (4) and log σ²_z (4). **Amendment 2:** log σ²_z is soft-bounded to [log 10⁻⁸, log 10²] |
| Prior | p(z) = N(0, I₄) |
| Decoder p(x \| z, c) | [z; c] (36) → Linear 128 → ReLU → Linear 128 → ReLU → Linear 28, giving μ_x (14) and a raw log-variance (14) |
| Decoder variance | Heteroscedastic diagonal Gaussian. The log-variance is softly bounded to [log 10⁻⁴, log 10²] by `max − softplus(max − raw)` followed by `min + softplus(· − min)`. The lower bound (SD 0.01 on the standardized scale) is a fixed numerical safeguard, not a tuned value. The share of decoder outputs within 1% of the bound is reported (§7) |
| Parameters | 48,420 |

## 4. Objective and optimization

- **Loss.** The negative ELBO per row: the Gaussian NLL of x under p(x \| z, c), with one reparameterized sample z, plus KL(q ‖ p), with β = 1 and averaged over the batch.
- **Optimizer.** Adam with learning rate 10⁻³ and batch size 4,096. **Amendment 2:** the global gradient norm is clipped at 1.0 before every step.
- **Arithmetic.** float32 on CUDA with `torch.use_deterministic_algorithms(True)`.
- **Randomness.** The row order comes from a CPU generator seeded `seed·1,000,003 + epoch`, and the latent noise from a CUDA generator with the same seed.
- **Epoch selection.** This follows the frozen LSTM rule (`final_validation`: at most 600 epochs, patience 6, minimum improvement 10⁻⁴):
  - the model trains on the dataset's *selection-fit* engines;
  - after each epoch, it is evaluated on the *validation* engine, a fit-pool engine that is never used for calibration or audit;
  - the validation loss is the deterministic surrogate "NLL at the posterior mean plus KL";
  - the selected epoch count is the argmin of the validation loss.
- **Refit.** Refitting runs on all fit-pool engines for the selected number of epochs, with no validation data, and freshly estimated standardization.
- **Seeds.** 0, 1 and 2. Each seed's selected epoch count is its own.
- **Isolation.** Calibration and audit engines never influence the standardization, the epoch selection or the weights.

## 5. Anomaly score

s(x, c) = −log N(x; μ_θ(μ_φ(x, c), c), diag σ²_θ(μ_φ(x, c), c)).

This is the conditional Gaussian negative log-likelihood of the standardized sensor vector at the posterior-mean latent code, i.e. a deterministic single-point form of the reconstruction probability.

- It is computed row by row in evaluation mode. There is no dropout or batch normalization, so a row's score does not depend on the other rows scored with it.
- It is computed in float32 and stored as float64.
- Higher values are more anomalous.

## 6. Calibration and evaluation: identical in concept to the other detectors

The chain is: representation score → healthy calibration threshold → audit.

- **Arms.**
  - **P**: pooled quantile.
  - **C**: retrospective phase-conditioned quantile.
  - **Q**: the existing quadratic-in-W linear quantile regression.
- **No new arm** is created for the CVAE.
- **Thresholds.** Each model receives its own healthy calibration thresholds.
- **Comparisons.** Only calibrated downstream quantities at the same nominal α are compared: phase FPR, nominal calibration error, transfer error, matched false-flag burden and matched delay. Raw score magnitudes are never compared or rescaled.

## 7. Numerical audit (reported per dataset and seed)

- **Losses.** The training- and validation-loss curves, the selected epoch, whether the 600-epoch ceiling was reached, and any non-finite loss. A non-finite loss halts the run; it is not retried with other settings.
- **Seeds.** Seed variability of the selected epoch and of the calibration thresholds.
- **Score reproducibility.** Calibration scores are recomputed from the saved checkpoint, and their SHA-256 fingerprint must match the lock.
- **Precision sensitivity.** On the first 100,000 calibration rows: the maximum relative difference and Spearman rank correlation between float32 and float64 scoring, and the change in the 1% pooled threshold's exceedance count. This is diagnostic only.
- **Variance floor.** The share of decoder log-variances within 1% of either bound, on calibration rows.
- **Leakage guards** (tested data-free):
  - the condition matrix equals `causal_descriptors` output;
  - scores are invariant to changes in phase, `hs`, Fc and unit metadata;
  - there is no cross-flight dependence, because descriptors reset per flight;
  - fit rows come only from fit engines;
  - validation rows come only from the validation engine.

## 8. Synthetic benchmark (data-free, 2026-09-28)

The synthetic set had 1.2 M rows, 32 descriptors computed by the frozen `causal_descriptors` on synthetic flight profiles, and 14 heteroscedastic channels.
- **Training.** A median of 0.47 s per epoch on 900,000 training rows (RTX 5090). The worst-case selection run of 600 epochs is ≈ 5 min per seed.
- **Scoring.** ≈ 2.7 M rows s⁻¹, with a peak GPU allocation of 363 MiB.
- **Determinism.** Scores were bit-identical across repeated scoring.

The CVAE is therefore computationally viable for every eligible subset. The staged DS02/DS03/first-subset viability pass of brief §19 is not needed.
