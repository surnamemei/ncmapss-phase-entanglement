# Methods traceability — ncmapss-phase-entanglement (MSSP extended manuscript)

Each item gives four locations: manuscript (section, page) → frozen protocol or config → code → result artifact.
- "Protocol §" means `docs/extension/GENERALIZATION_PROTOCOL.md` v1.0 (frozen at `d298623`).
- "Amend." means `docs/extension/AMENDMENTS.md`.
- Code paths are relative to the repository root.
- Constants were read from the code on 2026-09-29 (`main` = `v1.1.0` = `3a4de78`).

**Configs.** The YAML files in `configs/` are *audited snapshots* of the frozen DS02/DS03 constants. They are **not parsed**
by the scientific code (`docs/ENVIRONMENT.md`). The operative constants are the Python module constants cited below.

## 1. Data, cohort, splits

| Method item | Manuscript | Protocol / config | Code | Artifact |
|---|---|---|---|---|
| Subset screening (9 criteria, metadata-only) | §3.1 p. 4; Table S1 | `docs/extension/SUBSET_SELECTION_LOCK.md` (C1–C9; locked `7152b92`) | `src/ext_subset_metadata.py` (`audit_file`, `engine_checks`, `phase_feasibility`, `cohort`; `MIN_TEST_PHASE_ROWS=1000`, `MIN_ENGINES=3`, `PHASE_COMPLETE_SHARE=0.99`) | `docs/extension/subset_metadata_audit.{json,csv}`, `subset_engine_metadata.csv` |
| DS08d exclusion (file 32 bytes short) | §3.1 | Selection lock C1 | `src/ext_subset_metadata.py:unopenable_record` | `subset_metadata_audit.json` |
| Fleet families F1–F5 | §3.1 p. 4; Fig. 1 | Protocol §2; lock Part 2 | `src/ext_common.py:FAMILIES` | `docs/extension/profile_sharing_by_dataset.csv` |
| Duplicate-digest check (F3) | §3.1 (shared flights) | Protocol §2 | `src/ext_pipeline.py:duplicate_digests` | `*/lock/calibration_lock.json` (`duplicate_digests_development`) |
| Engine roles (fit / calibration / validation / audit) | §3.3 p. 5; Table 1 | Protocol §3 (R-ALLOC) | `src/ext_common.py:allocate`; DS02/DS03 `FROZEN_ROLES` (= `configs/ds0{2,3}_*.yaml`) | Table 1 CSV; locks (`roles`) |
| Engine-disjointness and leakage guards | §3.2–3.3 | Protocol §19 | `src/ext_common.py:guard_path`, `write_new_bytes`; `tests/test_leakage_guards.py`, `tests/test_extension_pipeline.py` | `docs/extension/OUTCOME_ACCESS_LOG.md`; `*/audit/official_test_opened.json` |
| Health label use (hs = 1 fit/cal/eval; hs = 0 onset) | §3.3 p. 5 | Protocol §6 | `src/ext_models.py:load_development_healthy`, `load_audit_rows` | — |
| Input integrity | §3.11 | Locks record `input_sha256` | `src/ext_common.py:verify_input`, `expected_sha256` | `N-CMAPSS/official_verification.json` (not re-hashed in this audit) |

## 2. Features, preprocessing, phases

| Method item | Manuscript | Protocol / config | Code | Artifact |
|---|---|---|---|---|
| Finite-history operating-condition correction: 14 sensors regressed on 32 past-only descriptors (current state, first differences, trailing mean/std/slope over 30 s and 120 s, reset at flight boundaries); ridge | §3.4 p. 5 | `configs/ds03_confirmation.yaml` (`correction_history_windows_seconds: [30, 120]`, `correction_ridge_alpha: 1.0`) | `src/phase3_dynamic.py` (`WINDOWS=(30,120)`, history features; `ResidualPCADetector`, line 118); used as `ResidualPCADetector("history", alpha=1.0)` in `src/ext_models.py` lines 105, 209 | `*/models/correction.pkl` (git-ignored; hash in lock) |
| Standardization of residuals | §3.4 | Frozen DS02/DS03 | `src/phase3_dynamic.py`; `src/ext_models.py:fit_models` | — |
| Flight phases (climb / cruise / descent): 90% within-flight altitude rule, needs the complete flight | §3.5 p. 6 | Protocol §5; `configs/*.yaml` `phase_primary_altitude_fraction: 0.90` | `src/confirm_frozen_ds03.py:primary_phase` (lines 48–60); original `src/pca_pilot.py` (`ALT_FRACTION=0.90`) | `phase_primary` column; `results/extension/metadata/healthy_flight_phase_segments.csv` |
| Operating descriptors W (altitude, Mach, TRA, T2) | §3.1, §3.5 | Protocol §5 | `src/ext_calibration.py:q_scale`, `q_features` | `*/lock/calibration_lock.json` (`q_scale`) |

## 3. Detectors (model definitions, hyperparameters, stopping rules, seeds)

| Method item | Manuscript | Protocol / config | Code | Artifact |
|---|---|---|---|---|
| Residual PCA, 5 components, SPE score | §3.4 p. 5 | `configs/*.yaml` `pca_components: 5` | `src/phase3_dynamic.py:ResidualPCADetector` | `*/models/` |
| Isolation Forest, 200 trees, max_samples 8192, seeds 0–2 | §3.4 | `isolation_forest_trees: 200`, `isolation_forest_max_samples: 8192` | `src/ext_models.py` (`IF_TREES, IF_MAX_SAMPLES = 200, 8192`; line 211) | `*/models/isolation_forest_seed_{0,1,2}.pkl` |
| Past-only LSTM sequence reconstruction (enc 16, bottleneck 8, dec 16, sequence 256, batch 256) | §3.4 | `configs/ds03_confirmation.yaml` | `src/final_validation.py:LSTMAutoencoder` (line 228), `LSTM_LENGTH=256` | `*/models/`; DS02/DS03 frozen checkpoints `results/final_validation/checkpoints/`, `results/confirmation_ds03/checkpoints/` |
| LSTM epoch selection: ≤ 600 epochs, patience 6, min_delta 1e-4, on the validation engine; then refit on all fit engines | §3.4 | Same YAML (`lstm_max_epochs: 600`, `lstm_patience: 6`) | `src/final_validation.py` (`MAX_EPOCHS=600`, `PATIENCE=6`, `MIN_DELTA=1e-4`); `src/ext_models.py:select_lstm_epochs`, `refit_lstm` | `*/lock/training_history.csv`; Table S4 |
| CVAE: condition on the 32 descriptors; 2×128 hidden (enc/dec); 4-D latent; heteroscedastic Gaussian decoder; score = conditional NLL at the posterior mean (no KL term) | §3.4 p. 5; §5.5 | `docs/extension/CVAE_SPECIFICATION.md` (frozen `1b3ca60`) | `src/ext_cvae.py` (`HIDDEN=128`, `LATENT=4`, `MIN_LOGVAR=log 1e-4`, `MAX_LOGVAR=log 1e2`, `BATCH=4096`, `LEARNING_RATE=1e-3`, `MAX_EPOCHS=600`, `PATIENCE=6`; `ConditionalVAE`, `score`) | `*/models/cvae_seed_{0,1,2}_final.pt` |
| CVAE numerical safeguards (encoder log-variance soft bound [log 1e-8, log 1e2]; gradient-norm clip 1.0) | §3.2 ("adding numerical safeguards … after a stop rule fired") | Amend. 2 (`27a6346`) | `src/ext_cvae.py` (`ENC_MIN_LOGVAR`, `ENC_MAX_LOGVAR`, `GRAD_CLIP`) | Locks `cvae_precision_audit`, `cvae_variance_bound_share`; Table S3 |
| GPU only; no CPU fallback | §3.11 | `docs/ENVIRONMENT.md`; `AGENTS.md` | `src/ext_cvae.py` and `src/final_validation.py` (`DEVICE=torch.device("cuda")`) | — |
| Separate scoring calls for healthy and post-onset rows (float32 batch-composition dependence) | §3.2 p. 4 | Amend. 3 | `src/ext_pipeline.py:score_audit` | `results/extension/_shakedown_attempt1/` (pre-amendment attempt, archived) |
| Model seeds | §3.4 | `ext_common.SEEDS=(0,1,2)` | `src/ext_models.py`, `src/ext_cvae.py:build_cvae(seed…)` | Locks (`models.files`) |

## 4. Calibration arms, thresholds, flight rule, persistence

| Method item | Manuscript | Protocol / config | Code | Artifact |
|---|---|---|---|---|
| Nominal targets 0.5/1/2% (1% primary) | §3.5 p. 6 | Protocol §5 | `src/ext_common.py:TARGETS`, `PRIMARY_TARGET` | All `*_alpha_0.01.csv` |
| P: upper 1 − α quantile of calibration scores (`method="higher"`) | §3.5 | Protocol §5 table | `src/ext_calibration.py:quantile_taus` → `src/mssp_mitigation.py:q_higher` (line 978) | `*/lock/calibration_lock.json` (`arms`) |
| C: per-phase quantiles applied by row phase (retrospective) | §3.5 | Protocol §5 | Same function | Same |
| Q: linear quantile regression on the quadratic surface of the 4 standardized W (14 terms + intercept), `QuantileRegressor(alpha=0, solver="highs")`, every 5th calibration row | §3.5 | Protocol §5 (frozen adversarial Part D) | `src/ext_qfit.py:fit_quantile_threshold` (`QR_STRIDE=5`); `src/ext_calibration.py:fit_q_thresholds`, `predict_q` | Locks (`arms`); runtime about 1 h per subset (`docs/extension/FREEZE_RECORD.md`) |
| Flight rule: κ = 0.95 `higher` quantile of healthy calibration-flight alarm fractions; flag if r(f) > κ | §3.5 p. 6 | Protocol §5 "Flight rule" (frozen D-3) | `src/ext_calibration.py:kappa`, `flight_fraction`; `FLIGHT_FALSE_FLAG_TARGET=0.05` (`src/mssp_mitigation.py:80`) | `*/audit/locked_operating_points.csv` |
| Persistence rules R0 / R1 (3 consecutive) / R2 (3 of 5), within flight | §3.7 p. 7 | Protocol §5 table, §8 | `src/ext_calibration.py:apply_rule`, `flight_events` | `*/audit/persistence_calibration.csv`, `flight_false_flags.csv` |

## 5. Endpoints and metrics

| Method item | Manuscript | Protocol | Code | Artifact |
|---|---|---|---|---|
| A1 (max − min phase FPR), A2 (max \|FPR_φ − α\|), pooled and per engine; ME-A2, WE-A2, n_worse | §3.6 p. 6 | Protocol §6 | `src/ext_endpoints.py:errors`, `quality_from_counts`, `healthy_tables` | `*/audit/transport_summary.csv`, `paired_transport.csv`, `paired_transport_engines.csv`, `phase_fpr.csv` |
| Material miscalibration line A2 ≥ 0.5α | §3.6 | Protocol §13.1 | `src/ext_summary.py:MATERIAL = 0.5 * ALPHA` | `decisions.json` |
| Healthy-flight false-flag rate (FFR) and worst engine (WE-FFR) | §3.6 | Protocol §6, §8 | `src/ext_endpoints.py:persistence_and_flight_tables`; `src/ext_summary.py:we_ffr_table` | `summary/we_ffr.csv` |
| Persistence calibration error PA2 | §3.7 | Protocol §8 | `src/ext_endpoints.py:calibration_reference`; `ext_summary.we_pa2_table` | `summary/we_pa2.csv` |
| Detection delay (flights from labelled onset to first flagged post-onset flight) | §3.6 | Protocol §6 | `src/ext_endpoints.py:persistence_and_flight_tables` | `*/audit/detection_delay.csv` |
| Matched-burden delay (κ swept on a calibration-only grid; anchors 2.5–20% FFR matched within one healthy-flight step; labels earlier/later/equal/mixed) | §3.6 p. 6–7 | Protocol §9 (frozen adversarial Part B) | `src/ext_endpoints.py:matched_tables` | `*/audit/matched_operating_points.csv`, `matched_comparisons.csv`, `matched_labels.csv` → `summary/matched_labels_alpha_0.01.csv` |
| Abnormal-state row alarm rates (early window of 10 flights) | §4.9; Table S16 | Protocol §6 | `src/ext_endpoints.py` (`EARLY = mm.EARLY_WINDOW_FLIGHTS = 10`) | `*/audit/abnormal_alarm_rates.csv` |

## 6. Composition intervention

| Method item | Manuscript | Protocol | Code | Artifact |
|---|---|---|---|---|
| Fixed volume N = largest multiple of 6,000 rows ≤ half of the smallest calibration-pool engine | §3.8 p. 7; Table 1 | Protocol §7 | `src/ext_common.py:composition_volume` (`VOLUME_QUANTUM=6000`), `composition_eligible` | Table 1; locks (`composition`) |
| Designs (single engine, same-class, two-class, leave-one-class-out, class-balanced, full) | §3.8 | Protocol §7 | `src/ext_calibration.py:build_designs`, `_balanced`, `_split`, `design_rows`, `design_thresholds` | `*/audit/composition_metrics.csv` |
| Five nested subsamples, from calibration data only | §3.8 | Protocol §7 | `src/ext_calibration.py:engine_permutations` (`COMPOSITION_BASE_SEED=20260930`, `COMPOSITION_DRAWS=(0..4)`) | — |
| Within-engine coverage effect CE1 (primary); volume contrast CE5; balance check CE2; CE4 | §3.8; §4.5 | Protocol §7, §13.4 | `src/ext_summary.py:composition_analysis`, `h4` | `summary/composition_engine_effects.csv`, `composition_run_summary.csv`, `composition_ce4.csv` |

## 7. Statistics, uncertainty, decision rules

| Method item | Manuscript | Protocol | Code | Artifact |
|---|---|---|---|---|
| Inferential unit = engine; flights nested; families top level | §3.9 p. 7 | Protocol §11 | — | — |
| U-EXT1: engine → flight bootstrap, 2,000 replicates, P and C thresholds re-estimated per replicate. Calibration engines are resampled **without** class stratification | §3.9; Table S8 | Protocol §11.1 | `src/ext_endpoints.py:bootstrap_uext1`, `BootstrapRun` (`UEXT1_SEED=20260929`, `BOOTSTRAP_REPLICATES=2000`) | `*/audit/bootstrap_uext1_ci.csv`, `bootstrap_uext1_replicates_alpha_0.01.csv` |
| U-EXT2: family → subset → U-EXT1 replicate, 2,000; median family-level effect | §3.9; §4.7; Table S9 | Protocol §11.2 | `src/ext_summary.py:uext2`, `subset_family_replicates`, `family_statistic` (`UEXT2_SEED=20261002`) | `summary/uext2_cross_dataset.csv` |
| Composition bootstrap (family → subset → audit engine) | §4.5; Table S12 | Protocol §11.3 | `src/ext_summary.py:composition_bootstrap` (`COMPOSITION_BOOT_SEED=20261001`) | `summary/composition_bootstrap.csv` |
| No p-values; count rules on point estimates; subset/family strict majorities | §3.9 | Protocol §12–13 | `src/ext_summary.py:family_holds`, `count_families` | `decisions.json` |
| H1–H7 decision rules | §3.9; Table 4 | Protocol §13.1–13.7 (+ Amend. 1) | `src/ext_summary.py:h1`…`h7` | `decisions.json` |
| Interpretation matrix and original-story classification; rescope flags | §3.9, §4.7 | Protocol §14–16 (+ Amend. 1) | `src/ext_summary.py:stories`, `original_story`, `rescope_flags` | `decisions.json` |
| Primary vs secondary endpoints and multiplicity | §3.6 (primary transport summaries) | Protocol §12 (endpoint hierarchy) | Ledger `tier` column (primary / secondary / robustness / baseline / design) | `docs/extension/EXTENSION_EVIDENCE_LEDGER.csv` |
| Stop rules | §3.2 (CVAE stop rule fired) | Protocol §18 | `src/ext_pipeline.py` (fail-closed runners); `src/ext_cvae.py` (non-finite check) | Amend. 2 record |

## 8. Staging, freezes, one-shot access

| Method item | Manuscript | Record | Code | Artifact |
|---|---|---|---|---|
| Locks committed before any official-test read; one-shot marker per subset | §3.2 p. 4 | Protocol §10; `docs/extension/FREEZE_RECORD.md` | `src/ext_pipeline.py:phase_lock`, `phase_audit`; `src/ext_common.py:append_access_log` | `*/lock/*`, `*/audit/official_test_opened.json`; `OUTCOME_ACCESS_LOG.md` |
| Reference reproduction gates (DS02/DS03 cell by cell before the new audits) | §3.2; Table S17 | Protocol §10; Amend. 3 | `src/ext_pipeline.py:reference_work`, `_frozen_trajectory_check`, `_frozen_q_check` | `results/extension/{DS02,DS03}/audit/audit_record.json`; `results/extension/shakedown/` |
| 186-file frozen-baseline manifest verified before and after runs | §3.11 | `docs/mssp/frozen_baseline.sha256` | `src/ext_common.py:verify_baseline` | — |
| Internal (not external) freeze | §3.2, §5.5 | Protocol preamble | — | Commit history on branch `mssp-extended` (local) |

## 9. Post hoc analyses (not pre-specified)

| Method item | Manuscript | Plan / record | Code | Artifact |
|---|---|---|---|---|
| Approximate sampling reference for A2 (flight-clustered design effect scaled to phases) | §4.9 p. 14; Fig. 3 ticks; Table S19 | `docs/extension/EXTENSION_HOSTILE_REVIEW.md` §3 | `paper/mssp_extended/post_hoc_checks.py:a2_noise` (`SEED=20260930`) | `evidence/post_hoc_checks.json`, `post_hoc_engine_noise.csv` |
| WE-FFR perfect-calibration null | §4.9; Fig. 6a bands; Table S18 | Same | `post_hoc_checks.py:we_ffr_null` | `post_hoc_checks.json` |
| Two-flight confirmation, direction of errors, coin-flip reading, DS08a flight decomposition, profile sharing, balanced vs best single, class-omission probability, early sensitivity | §4.9 | Same | `post_hoc_checks.py:main` | `post_hoc_checks.json` |
| Focused validation: 5-fold cross-fit × 200 (NF50/NF95; "clearly exceeds" = > NF95 in ≥ 4/7 residual runs) | §3.10 p. 8; §4.8 | `docs/extension/FOCUSED_VALIDATION_PLAN.md` (frozen `d85aa10`) | `src/ext_focused_validation.py:crossfit_draws`, `majority_exceeds` (`FOLDS=5`, `R_CROSSFIT=200`, `SEED_CROSSFIT=20261004`) | `results/extension/focused_validation/*/engine_noise_floor.csv`, `noise_floor_draws.csv`; `summary/engine_summary.csv` |
| Class-preserving bootstrap | §3.10; §4.8 | Same | `class_preserving_plans` (`SEED_CLASS_BOOT=20261003`), `uext2_with` | `focused_validation/*/bootstrap_class_preserving_*.csv`; `summary/bootstrap_width_comparison.csv` |
| Local recalibration on the first 5 healthy flights, against 200 random 5-flight subsets | §3.10; §4.8 | Same | `local_recalibration`, `k_matched_draws` (`K_LOCAL=5`, `R_LOCAL=200`, `SEED_LOCAL=20261005`) | `focused_validation/*/local_recalibration.csv`; `summary/local_engine_summary.csv` |
| Reproduction gates of the focused validation | §4.8 ("All reproduction gates passed") | Plan | `gate_plan_and_code`, `gate_healthy_counts`, `gate_original_replicates` | `focused_validation/*/validation_record.json` |

## 10. Baselines, ablations, robustness (what exists)

- **Baselines.**
  - Threshold arm baselines: P (pooled), C (oracle-phase) and Q (continuous context).
  - Representation baseline: the CVAE.
  - There is no per-unit recalibration baseline except the post hoc k = 5 local recalibration, and no class-conditional
    threshold baseline.
- **Robustness checks.**
  - Targets 0.5/1/2% (Table S10).
  - Persistence rules R0/R1/R2.
  - Class-preserving bootstrap.
  - Post hoc two-flight confirmation.
- **Ablations.** None in the ML sense. The composition intervention is the design ablation of the calibration fleet.
- **Alternative phase definition.** `phase_alt_rate` exists in the frozen DS02/DS03 stages (`src/final_validation.py:PHASE_DEFINITIONS`) but is **not** used in the extension.

## Items not traced to a single location

- **"32 past-only operating descriptors"**: the count comes from 4 W × (current + difference + 2 windows × 3 statistics) = 4 × 8 = 32.
  This is consistent with `src/phase3_dynamic.py` (means, stds and slopes for each window) but was not confirmed by running
  the code.
- **The quantile regression fit** (every 5th row, deterministic HiGHS): its determinism is asserted in the protocol and
  `FREEZE_RECORD.md`, not re-run here.
