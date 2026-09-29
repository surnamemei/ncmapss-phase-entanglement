# Adversarial validation plan (post-confirmation, MSSP branch)

**Status: FROZEN before execution (2026-09-28).** This plan is committed before any adversarial metric is computed. Any later change is recorded as a dated deviation in `docs/mssp/FINAL_ADVERSARIAL_REVIEW.md`, together with its reason. The plan is post-confirmation and exploratory. It never qualifies the frozen DS03 verdict (protocol firewall F1–F6).

- **Snapshot at freeze.**
  - Branch `mssp-revision`, HEAD `6b85148`.
  - The 186-file baseline manifest verifies.
  - Stage F run-manifest hashes match: protocol `b4a669cd…`, config `23bb3b04…`, module `2764f271…`, manifest `37c0cef2…`.
  - 39/39 tests pass.
- **Terminology.** C′ is called the **past-only regime arm**. It uses current and past altitude only, so it is non-anticipative in the signal-processing sense, not "causal" in the causal-inference sense. The data identifier `causal_regime` is kept unchanged in frozen and new tables.

## 1. Rules that apply to every part

| Rule | Implementation |
| --- | --- |
| R1 Frozen artefacts are inputs only | Nothing under the manifest, `results/mssp_mitigation/`, `results/confirmation_ds03/`, `results/final_validation/`, `paper/ress/` or `paper/submission/` is written. New outputs go to `results/mssp_adversarial/`, `paper/mssp/evidence/`, `paper/mssp/figures/`, `paper/mssp/tables/` and new `docs/mssp/` files. The manifest is verified before and after each run. |
| R2 No new abnormal-row read | No `hs = 0` sensor or operating row is opened. Abnormal-state information enters only through the committed Stage E flight- and row-count tables. Every row loaded by the new code is checked to be `hs = 1`. Rereading abnormal rows would need a protocol amendment and the author's explicit approval. **It is not part of this plan.** |
| R3 Healthy rescoring is exact | Healthy calibration and audit rows are rescored with the frozen detectors through the unchanged `mssp_mitigation` code path, as in Stage D. The score fingerprints must equal the Stage C fingerprints (G6). The recomputed P/C/C′ healthy count tables must equal the committed Stage D tables exactly, and the recomputed κ must equal the locked κ exactly. |
| R4 No tuning on outcomes | No threshold, phase rule, κ, guardrail, detector parameter or endpoint definition is changed. Every grid, anchor, tolerance and category rule is fixed here. |
| R5 Inferential unit | The engine is the top-level unit, and flights are nested in engines. Calibration and audit are resampled separately. There are no row-level or timestamp-level tests and no p-values. Intervals are reported only through the frozen U1 hierarchy, extended to new metrics. They are seed-specific. Family seed means are descriptive only and carry no interval. |
| R6 Report everything | Every run, target, arm and engine is reported, including exceptions and reversals. |

## 2. The three primary attacks and their validations

| Attack | Validation | Data | New model fitting |
| --- | --- | --- | --- |
| **A.** "Stabilization is manufactured by the max-minus-min spread." | Nominal calibration-quality metrics A1–A7 for P, C and C′ at α ∈ {0.5, 1, 2}%, with an extended U1 bootstrap | Derivation from `stage_d/healthy_phase_fpr_by_scheme.csv`; rescored healthy rows for the bootstrap | None |
| **B.** "Delay comparisons are unfair because operating points differ." | Flight-level operating characteristic over a calibration-only κ grid, and comparisons at matched false-flag rates | Derivation from `stage_e/flight_alarm_fraction_trajectories.csv`; κ candidates from rescored healthy calibration flights | None |
| **C.** "The phase effect is calibration-to-audit operating-support mismatch." | Phase effect inside calibration engines (C0); support distances (C1–C3); engine × phase associations (C4); verdict (C5) | Rescored healthy calibration rows; healthy `W` (alt, Mach, TRA, T2) and finite-history descriptors | None (distances only) |
| **D.** (conditional) "Phase thresholds are too weak a baseline." | One continuous context-aware baseline, quantile regression on operating descriptors | Healthy rows only | One linear quantile regression per run and target, calibration rows only, no tuning |

### 2.1 Validation A: calibration quality, not just phase equality

The phase FPRs are FPR_φ = alarms_φ / n_φ on healthy audit rows, for φ ∈ {climb, cruise, descent}, at the locked row thresholds of each arm.

| ID | Metric | Formula |
| --- | --- | --- |
| A1 | Phase spread (between-phase disparity) | max_φ FPR_φ − min_φ FPR_φ |
| A2 | Maximum absolute nominal calibration error | max_φ \|FPR_φ − α\| |
| A3 | RMS nominal calibration error | sqrt(mean_φ (FPR_φ − α)²) |
| A4 | Mean absolute nominal calibration error | mean_φ \|FPR_φ − α\| |
| A5 | Overall healthy FPR error | \|FPR_overall − α\| |
| A6 | Alarm concentration | alarms_φ / Σ alarms, beside the row share n_φ / Σ n |
| A7 | Phase calibration ratio (descriptive) | FPR_φ / α, always with the count of alarms |

- **Weightings.**
  - Row-pooled over audit engines, the primary weighting and the frozen estimand.
  - Equal-engine-weighted: FPR_φ^EW = mean_e FPR_{e,φ}, with the metrics recomputed from it.
  - Per engine.
  - Seed-specific, with the family arithmetic seed mean as a descriptive summary.
- **Uncertainty.**
  - The frozen U1 plans are reused: seed 20260925, 2,000 replicates, engine → flight resampling of calibration and audit separately, thresholds re-estimated.
  - They are extended to A2–A5 and to the paired differences C − P and C′ − P at all three targets, using the same plans for every target.
  - Self-check: the pooled-arm metrics that already exist at 1% must reproduce the committed `u1_bootstrap_ci.csv` within 1e−12.
- **Category rule.** Applied per dataset × run × target × arm (C or C′ against P) on row-pooled point estimates, where Δ = arm − P:

| Category | Rule |
| --- | --- |
| 1 EQUALITY IMPROVES AND NOMINAL CALIBRATION IMPROVES | ΔA1 < 0, ΔA2 < 0 and ΔA3 < 0 |
| 2 EQUALITY IMPROVES BUT NOMINAL CALIBRATION DOES NOT | ΔA1 < 0, ΔA2 ≥ 0 and ΔA3 ≥ 0 |
| 3 MIXED | Any other combination in which at least one of ΔA1, ΔA2 or ΔA3 is < 0 |
| 4 CONDITIONING WORSENS BOTH | ΔA1 ≥ 0, ΔA2 ≥ 0 and ΔA3 ≥ 0 |

The same rule is applied per engine; the results are descriptive and show transportability.

- **Wording rule (per dataset × arm).**
  - "Improved nominal phase-wise calibration" is allowed only if all three conditions hold:
    - category 1 holds for at least 6 of the 7 runs at 1%;
    - it holds for at least 5 of the 7 runs at each of 0.5% and 2%;
    - it is not contradicted per engine in a majority of the audit engines.
  - Otherwise the text says "reduced between-phase disparity" (when ΔA1 < 0 in a majority of runs), with the calibration-error results stated beside it.
  - "Stability" or "stabilization" is not used for a row-pooled spread reduction alone.
  - An interval claim requires the U1 interval to exclude zero.

### 2.2 Validation B: matched operating points for detection delay

- **Inputs.**
  - For every audit flight f (healthy, or post-onset abnormal with offset k), arm, run and target: r(f) = alarms / rows at the locked row thresholds. This comes from the committed Stage E trajectory table.
  - The healthy calibration-flight fractions are recomputed from rescored healthy calibration rows. **Check:** the 0.95 "higher" quantile of these fractions must equal the locked κ for every arm, run and target, or the part stops.
- **Calibration-only κ grid.**
  - K = {0} ∪ {distinct healthy calibration-flight fractions of that arm, run and target} ∪ G.
  - G has 400 log-spaced values in [1e−4, 1], fixed a priori and data-free.
  - A flight is flagged iff r(f) > κ. No audit or abnormal quantity enters K.
- **Per κ.**
  - Realized healthy-flight false-flag rate (FFR), pooled over healthy audit flights and per engine.
  - Per-engine delay: the first post-onset flight flagged; +∞ if none, i.e. censored.
  - Lower (inverted-CDF) median delay over audit engines, with censored values ranked above observed ones.
  - Number of engines censored.
  - Fraction of engines detected within d ∈ {0, 1, 3, 5, 10} flights.
  - Two-flight persistence delay.
- **Quantities that do not depend on κ** (reported once): mean and median post-onset flight alarm fraction; row alarm rate in the first 10 post-onset flights (`abnormal_alarm_rates.csv`).
- **Anchors.** a ∈ {2.5, 5, 10, 15, 20}% realized pooled audit FFR.
  - **Matching.** For each arm, the candidate κ whose realized FFR is nearest to a. Ties go to the lower FFR, then to the larger κ.
  - **Support.** A matched point is supported iff |FFR − a| ≤ 1/N_h, where N_h is the number of healthy audit flights (76 in DS02, 148 in DS03), i.e. one flight step.
  - **Sensitivity.** The conservative rule: the largest FFR ≤ a.
  - Delays are never interpolated or extrapolated; unsupported anchors are reported as such.
- **Paired comparisons (C against P, C′ against P) at each supported anchor.**
  - Per-engine ΔD_e with the frozen censoring conventions.
  - Earlier/same/later counts.
  - Lower median of ΔD_e.
  - Difference of the median delays.
  - FFR mismatch between the arms.
- **Curve-level summary.**
  - The mean of the median delay over x ∈ [2.5%, 20%] in 0.25-pp steps, using the nearest supported point at each x. An x without a supported point is excluded, and its count is reported.
  - The difference from P.
  - Pareto classification of the locked-κ operating points against P: dominates, dominated, or trade-off.
- **Existing S4 partial AUC.** It is a row-level, threshold-free separability of abnormal versus healthy audit rows, computed on calibration p-values over row FPR ∈ [0, 2%]. It is **not** a flight-level operating characteristic, and it is reported with that definition only.
- **Interpretation rule (per dataset × run × arm).**

| Label | Rule |
| --- | --- |
| "earlier at matched burden" | ΔD < 0 at a majority of supported anchors and > 0 at none |
| "later at matched burden" | The mirror image of "earlier" |
| "equal" | ΔD = 0 at all supported anchors |
| "mixed" | Anything else |

- **Allowed statements.**
  - "Improves detection delay" requires "earlier at matched burden" in at least 5 of 7 runs, with a lower curve-level mean than P.
  - If the locked-κ delay advantage does not survive matching, the text says: "the apparent delay advantage primarily reflected a more aggressive flight-level operating point".
  - There are 3 and 6 audit engines, so no new interval is attached. Per-engine results are shown instead.
- **Stop condition.** If fewer than 3 of the 5 anchors are supported for P and an alternative arm in a dataset at 1%, the matched comparison for that dataset stops and is reported rather than extrapolated.

### 2.3 Validation C: operating support as an organizing variable

- **C0: phase effect with no support mismatch.**
  - The locked pooled τ is applied to the healthy calibration rows themselves, in sample, giving per-phase FPR.
  - Cross-engine version: τ from one calibration engine is applied to the other calibration engine.
  - If descent over-alarming appears inside calibration data, it is not produced by calibration-to-audit mismatch.
- **C1: row-level support distance.**
  - Operating descriptors are standardized with the calibration mean and SD of each dataset.
  - **Primary: d_phase.** Euclidean distance from each healthy audit row, in 4-D `W` (alt, Mach, TRA, T2), to the nearest healthy calibration row of the same retrospective phase (exact KD-tree).
  - **Secondary: d_all.** Same, to any calibration row.
  - **Secondary: d8_phase.** Same-phase distance in 8-D `W` plus the 120-s trailing slope of `W`, the finite-history descriptor already used by the correction.
  - **Reference scale.** The same-phase distance from each calibration engine's rows to the other calibration engine's rows. A row is "beyond calibration support" if d exceeds the 95th percentile of that cross-calibration-engine distance, per phase.
- **C2: engine × phase table.** For each cell:
  - rows;
  - median, p90 and p95 of d_phase, d_all and d8_phase;
  - fraction beyond calibration support;
  - fraction outside the same-phase per-dimension calibration range.
- **C3: flight class.**
  - Which classes occur in calibration and in audit (from `A` field Fc).
  - Distance summaries by class × phase.
  - Whether class-1 engines are measurably farther from support than in-class engines.
- **C4: association, not causation.** The unit is the engine × phase cell (9 in DS02, 18 in DS03), per run, at 1% (with 0.5% and 2% as sensitivity).
  - Spearman ρ between cell median d_phase and |FPR_C − α|.
  - Spearman ρ between d_all and |FPR_P − α|.
  - Spearman ρ between d_phase and the P→C change in |error|.
  - Leave-one-engine-out range of ρ.
  - Engine-level descriptive rank tables for locked-κ FFR and delay.
  - Rows are never treated as independent observations, and no p-values are computed.
- **C5: verdict.**

| Verdict | Rule |
| --- | --- |
| **STRONGLY ORGANIZES** | ρ(d_phase, \|FPR_C − α\|) ≥ 0.6 in at least 6 of 7 runs in both datasets, the sign is unchanged under every leave-one-engine-out, and class-1 cells are the most distant cells |
| **PARTIAL EXPLANATION** | ρ > 0 in at least 5 of 7 runs in at least one dataset, with a median ρ in [0.3, 0.6), or a strong result in one dataset only |
| **LITTLE EVIDENCE** | Median ρ ≤ 0.3, or an inconsistent sign |
| **INDETERMINATE (small engine count)** | Removing one engine flips the sign of the median ρ in either dataset. This verdict overrides the others. |

The organizing story changes to "calibration transport under changing operating support" only for STRONGLY ORGANIZES, or for PARTIAL together with a positive C0. C0 shows whether the pooled phase effect exists without any support mismatch.

### 2.4 Conditional validation D: one continuous context-aware baseline

- **Run condition.** D runs only if, after A–C, C still reduces between-phase disparity (ΔA1 < 0) in at least 5 of 7 runs per dataset at 1%, so that phase conditioning remains a contribution.
- **Specification (fixed now).**
  - Linear quantile regression at level 1 − α, minimizing pinball loss with no penalty and solved exactly by linear programming (HiGHS, through `sklearn.linear_model.QuantileRegressor`).
  - Features: a quadratic response surface in the 4 calibration-standardized `W` variables, i.e. 4 linear, 4 square and 6 interaction terms plus an intercept.
  - Fitted on healthy calibration rows only, separately per run and target.
  - A deterministic systematic subsample of every 5th calibration row is used for tractability; this is a fixed default, not tuned.
  - No phase input.
  - The row threshold is τ(x) = the fitted conditional quantile. κ uses the same 0.95 "higher" rule on calibration-flight fractions.
- **Evaluation.**
  - Healthy audit rows: A1–A6.
  - Healthy-flight FFR at the calibration κ, and the healthy side of the operating characteristic.
  - Per-engine transport.
  - **Abnormal-state endpoints for D need abnormal-row scores, which were not retained. They are deferred pending author approval of a separate abnormal-row read (R2), and reported as not evaluated.**
- **Skip condition.** If the linear programs fail, or the specification would need tuning, D is skipped and the reason documented.

## 3. Operating-target robustness and the denominator audit

- **Targets.** Every major claim is classified across α ∈ {0.5, 1, 2}%, per dataset:

| Classification | Rule |
| --- | --- |
| **invariant** | Same direction in every run at every target |
| **mostly invariant** | Direction holds in at least 80% of run × target cells and in the majority at each target |
| **target-sensitive** | The majority direction holds at 1% but not at another target |
| **reversed** | The opposite majority direction at some target |

  The claims classified are:
  - phase disparity;
  - nominal calibration error;
  - P→C and P→C′ effects;
  - abnormal-state alarm-rate ratio;
  - false-flag burden;
  - the matched delay trade-off.
- **Denominators.**
  - Row-pooled against equal-engine-weighted values for the core healthy metrics.
  - Equal-flight-weighted overall healthy FPR, from the trajectory table.
  - Phase-duration shares.
  - Individual seeds against the family mean.
  - "Healthy flights with any alarm" against the κ false-flag rate.
  - Row abnormal alarm rate against flight-level detection delay.
  - If a conclusion changes with the denominator, both are reported and the targeted estimand is stated.

## 4. Remaining stages

- Prior-art audit: `paper/mssp/reference_audit.csv`, with verified claims only.
- Adversarial claim audit: `paper/mssp/adversarial_claim_audit.md`.
- Story selection: A (strong mitigation), B (calibration transport) or C (cautionary audit), using the criteria in the task brief.
- Title, abstract and contributions.
- Figures, tables and supplement.
- Tests.
- `docs/mssp/FINAL_ADVERSARIAL_REVIEW.md`.

## 5. Stop conditions

Execution stops and is reported if any of the following occurs:
- a frozen hash changes;
- the score fingerprints, the recomputed Stage D count tables, or the recomputed κ differ from the committed values;
- any code path would read an `hs = 0` row or would use abnormal outcomes to build a threshold, grid or baseline;
- the D baseline would need a hyperparameter search on DS03;
- the matched comparison would need extrapolation (the §2.2 rule);
- the input tables are inconsistent with the frozen runs, e.g. the trajectory table's locked-κ delays do not reproduce `detection_delay.csv`;
- any analysis would require changing the frozen DS03 verdict.
