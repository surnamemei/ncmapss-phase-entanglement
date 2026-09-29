# Generalization protocol: final scientific extension (multi-subset calibration transport)

**Status.** FROZEN v1.0. It was committed before any new outcome was computed and before any sensor value of a new subset was read.
**Parents:**
- `docs/extension/EXTENSION_CHARTER.md`;
- `docs/extension/SUBSET_SELECTION_LOCK.md` (cohort locked at `7152b92`);
- `docs/extension/CVAE_SPECIFICATION.md`.

**Relation to earlier protocols.**
- The frozen DS02 discovery, the frozen DS03 confirmation, the post-confirmation protocol (`docs/mssp/post_confirmation_mitigation_protocol.md`, v1.0) and the adversarial plan (`docs/mssp/adversarial_validation_plan.md`) stay untouched and canonical for their own claims.
- This protocol reuses their definitions wherever they exist, and marks every new element.
- Nothing here re-labels, re-tests or qualifies the frozen DS03 confirmation.
- The words "pre-specified" and "frozen" in this document mean *internally* frozen, not externally preregistered.

---

## 1. Questions and hypotheses (frozen; no hypothesis says a method "wins")

| ID | Hypothesis (brief §2) | Operational decision rule (§13) |
| --- | --- | --- |
| **H1** Conditional calibration | A pooled nominal healthy-FPR calibration will not guarantee equal phase-conditional FPR on every new subset. It is directional, and it does not require the same phase ordering | §13.1 |
| **H2** Phase-conditioned correction | Retrospective phase-conditioned thresholds will usually reduce pooled between-phase disparity relative to pooled calibration, but will not necessarily reduce nominal calibration error for every engine | §13.2 |
| **H3** Transport | No context-specific calibration method tested here is expected to improve nominal calibration error uniformly across all held-out engines | §13.3 |
| **H4** Calibration composition | Calibration transport depends more strongly on coverage of engine/flight operating classes than on raw calibration-row count alone | §13.4 |
| **H5** Condition-aware representation | A detector that conditions its representation on operating descriptors may reduce phase dependence, but representation-level conditioning alone is not assumed to guarantee threshold-calibration transport across engines | §13.5 |
| **H6** Alarm persistence | Transport failures that remain under standard persistence rules cannot be attributed solely to isolated single-row threshold crossings | §13.6 |
| **H7** Matched operating point | Any detection-delay comparison is interpreted at matched realized healthy-flight false-flag burden | A rule (§9), not a test |

**Positive organizing hypothesis (brief §12).** Calibration transport depends on the calibration population's coverage of latent engine and mission operating regimes. Flight class is an observable, coarse descriptor of those regimes.
- It is tested **only** through the composition intervention (§7).
- No further distance metrics are introduced.
- Flight class is never called causal.

## 2. Datasets, cohorts and fleet families

| Level | Members | Role |
| --- | --- | --- |
| New primary cohort | DS01, DS04, DS05, DS06, DS07, DS08a, DS08c | All hypothesis decisions (§13) |
| Excluded | DS08d (C1, HDF5 integrity) | Never opened |
| Historical reference subsets | DS02, DS03 | Frozen study data, already opened. Extension outputs on them (CVAE, persistence, the abnormal side of Q, DS03 composition) are reported separately as "post-confirmation reference results". They enter comparisons with the new cohort (§15, brief §11) but no hypothesis decision |

**Fleet families** (fixed from metadata; `SUBSET_SELECTION_LOCK.md` Part 2):
- F1 = {DS01};
- F2 = {DS04};
- F3 = {DS05, DS06, DS07};
- F4 = {DS08a};
- F5 = {DS08c};
- historical: F0a = {DS02} and F0b = {DS03}.

The rules for families are:
- A family *holds* a statement if a strict majority of its subsets hold it (F3 needs 2 of 3).
- Every directional count is reported at the family level (primary; 5 new families) and at the subset level (7 new subsets).
- Families are the top-level resampling unit of cross-dataset intervals (§11.2).
- Cross-family engine identities (DS01 test 7 ≡ DS03 dev 9; DS08a test 15 ≡ DS03 dev 5; DS01 dev 2 ≡ DS08a test 14) are disclosed. They do not change the families.

**Duplicate check at data opening (F3 only).** For every unit, the SHA-256 of its healthy `X_s` rows (float64 bytes, in file order, over the healthy cycles common to DS05, DS06 and DS07) is recorded per subset. Only digests are compared; no values are displayed.
- The result, identical or not, is reported as a data-structure fact.
- It changes no analysis, because F3 already counts once.

## 3. Engine roles

**Rule R-ALLOC.** It is metadata-only, deterministic and applied to the development engines of each new subset. Here "class" is the flight class Fc.
1. For each class present (ascending), the **lowest-ID** engine of that class goes to the **fit pool**.
2. For each class with ≥ 2 development engines, the **highest-ID** engine of that class goes to the **calibration(-composition) pool**.
3. The remaining engines, in ascending ID order, go to the fit pool until it has 3 engines; any further ones go to the calibration pool.
4. The epoch-selection **validation engine** is the highest-ID fit engine. The other fit engines are the **selection-fit** engines.
5. The **audit pool** is every official test engine.

**Rationale.** The fit pool sees every class present, so that model transport is not confounded with calibration composition. The calibration pool covers as many classes as possible (brief §8). No audit engine is involved.

| Subset | Fit pool (unit:class) | Validation | Calibration pool (unit:class, healthy rows) | Pool classes | Audit (unit:class) | Composition-eligible |
| --- | --- | --- | --- | --- | --- | --- |
| DS01 | 1:1, 2:3, 3:2 | 3 | 4:1 (164,934), 5:3 (256,879), 6:2 (226,749) | 1, 2, 3 | 7:1, 8:2, 9:1, 10:3 | yes (N = 78,000) |
| DS04 | 1:2, 2:3, 4:3 | 4 | 3:2 (194,688), 5:3 (229,766), 6:3 (224,547) | 2, 3 | 7:2, 8:2, 9:2, 10:3 | yes (N = 96,000) |
| DS05 | 1:2, 2:3, 4:1 | 4 | 3:2 (204,729), 5:1 (157,174), 6:3 (238,954) | 1, 2, 3 | 7:2, 8:1, 9:3, 10:1 | yes (N = 78,000) |
| DS06 | 1:2, 2:3, 4:1 | 4 | 3:2 (187,197), 5:1 (143,643), 6:3 (228,666) | 1, 2, 3 | 7:2, 8:1, 9:3, 10:1 | yes (N = 66,000) |
| DS07 | 1:2, 2:3, 4:1 | 4 | 3:2 (204,729), 5:1 (157,174), 6:3 (250,867) | 1, 2, 3 | 7:2, 8:1, 9:3, 10:1 | yes (N = 78,000) |
| DS08a | 1:1, 2:3, 4:2 | 4 | 3:1 (127,687), 5:2 (162,661), 6:3 (199,948), 7:2 (177,978), 8:2 (191,358), 9:1 (124,923) | 1, 2, 3 | 10:1, 11:2, 12:3, 13:3, 14:3, 15:1 | yes (N = 60,000) |
| DS08c | 1:3, 2:3, 6:2 | 6 | 3:3, 4:3, 5:3 | 3 | 7:2, 8:2, 9:2, 10:2 | **no**: one pool class. All four audit engines belong to a class that is absent from calibration and present in fit (engine 6) |
| DS02 (ref.) | 2, 5, 10, 16 (frozen) | 16 | 18:3, 20:3 (frozen) | 3 | 11:3, 14:1, 15:2 | no (one class; volume designs only, descriptive) |
| DS03 (ref.) | 1, 2, 3, 5, 6, 7, 9 (frozen) | 9 | 4:2 (206,884), 8:3 (251,221) (frozen) | 2, 3 | 10:3, 11:3, 12:1, 13:3, 14:1, 15:2 | reference only (N = 102,000) |

**Additional rules:**
- The frozen DS03 rule `choose_units` is **not** reused for new subsets (brief §8). For six development engines it would give a two-engine, often single-class calibration pool.
- The DS02 and DS03 roles are the frozen ones.
- **Row use.** Only `hs = 1` rows of fit and calibration engines are ever loaded; their abnormal rows are never read. For audit engines, both healthy and post-onset rows are read, and only in the one-shot audit step (§10).

## 4. Detectors

| Detector (runs) | Specification | New subsets | DS02 / DS03 |
| --- | --- | --- | --- |
| Residual PCA (1) | Frozen history correction: ridge with α = 1 on the 32 causal descriptors, cubic static plus dynamic basis; standardized residuals; PCA with 5 components; squared prediction error | Fitted on fit-pool healthy rows | Deterministic refit. The calibration and healthy-audit score fingerprints must equal the Stage C fingerprints |
| Isolation Forest (seeds 0, 1, 2) | 200 trees, `max_samples` 8,192, on the correction's standardized residuals | As above | As above |
| Past-only LSTM autoencoder (seeds 0, 1, 2) | Frozen architecture, 256-row non-overlapping within-flight chunks. Epoch selection follows the frozen rule (≤ 600 epochs, patience 6, Δ ≥ 10⁻⁴): train on selection-fit engines, monitor the validation engine, then refit on the full fit pool for the selected epochs. The correction used for selection is fitted on selection-fit engines only | New training. It is reimplemented in the extension module without the frozen writers, which write into frozen directories; equality with the frozen loop is tested on synthetic data | Frozen final checkpoints loaded (no training) |
| CVAE (seeds 0, 1, 2) | `CVAE_SPECIFICATION.md` | New training | New training, with the frozen fit, selection-fit and validation roles |

**Model storage.** All fitted models and checkpoints are saved under `results/extension/<subset>/models/`, which is git-ignored for binaries; SHA-256 hashes are recorded in the lock. Calibration scores recomputed from the saved models must reproduce the lock fingerprints before any audit step.

**Runs per subset.** 10 runs: PCA; IF seeds 0–2; LSTM seeds 0–2; CVAE seeds 0–2. The seven residual-pipeline runs are the "residual runs"; the three CVAE runs are the "CVAE runs".

## 5. Calibration arms, flight rule and alarm-persistence rules

**Targets.** α ∈ {0.005, 0.01, 0.02}, with 0.01 primary.

**Notation.** 𝒞 is the healthy rows of the calibration pool, and 𝒞_φ its subset in phase φ. The phase φ is the frozen primary retrospective phase (`confirm_frozen_ds03.primary_phase`, 90% within-flight altitude rule).

| Arm | Threshold | Notes |
| --- | --- | --- |
| **P** (pooled) | τ = Q↑₁₋α{s(i): i ∈ 𝒞}, the `method="higher"` quantile | Frozen definition |
| **C** (retrospective phase-conditioned) | τ_φ = Q↑₁₋α{s(i): i ∈ 𝒞_φ}, applied by the row's phase | Frozen definition. An oracle-regime diagnostic, not implementable in flight |
| **Q** (continuous context; adversarial control) | Linear quantile regression at level 1 − α on the quadratic response surface of the 4 calibration-standardized `W` variables: 14 terms plus an intercept, `QuantileRegressor(alpha=0, solver="highs")`, fitted on every 5th calibration row. The row threshold is the fitted conditional quantile | The frozen adversarial-plan specification (Part D). Fits run in parallel processes; the solution is deterministic |

- **C′ (past-only regime) is not carried into the extension.** The brief limits the arms to P, C and Q, and C′'s role (feasibility) is already reported. No other arm is created.
- **Abnormal side of Q.** It is evaluated on every subset. For DS02 and DS03 this closes the disclosed gap; it is a new, post-confirmation evaluation there.

**Row exceedance.** e_t = 𝟙[s_t > τ_t] under the arm's threshold.

**Alarm-persistence rules** (fixed, never tuned). They are evaluated within each flight, and the history resets at the flight's first row.

| Rule | Row alarm a_t |
| --- | --- |
| **R0** | a_t = e_t (single-row exceedance; the frozen convention) |
| **R1** | a_t = e_t ∧ e_{t−1} ∧ e_{t−2}, i.e. 3 consecutive exceedances. The first two rows of a flight cannot alarm |
| **R2** | a_t = 𝟙[Σ_{k=0}^{4} e_{t−k} ≥ 3], i.e. 3 of the last 5 exceedances. The window is truncated at the flight start, and rows before the start count as 0 |

No clearing condition is used. An **alarm event** is a maximal run of consecutive a_t = 1 rows within a flight.

**Flight rule** (frozen D-3, applied per arm × rule × run × α):
- r(f) = the mean of a_t over flight f.
- κ = Q↑₀.₉₅{r(f): f a healthy calibration-pool flight}, a nominal 5% healthy-flight false-flag target.
- A flight is flagged iff r(f) > κ.
- κ is locked before any audit row is read.

## 6. Endpoints (for every detector run, arm, rule where applicable, target, subset and audit engine)

Healthy audit rows are indexed by engine e and phase φ, with FPR_{e,φ} = alarms/rows. "Row-pooled" pools the audit engines' rows, which is the frozen estimand. Everything below is computed on the **full calibration pool** unless §7 says otherwise.

| Brief | ID | Definition |
| --- | --- | --- |
| A | A | Overall healthy FPR, pooled and per engine |
| B | B | Phase-conditional healthy FPR FPR_φ and FPR_{e,φ} |
| C | A1 | Between-phase disparity max_φ FPR_φ − min_φ FPR_φ, pooled and per engine |
| D | A2 | Maximum nominal calibration error max_φ \|FPR_φ − α\|, pooled and per engine. **Never replaced by disparity** |
| E | A3 | RMS nominal calibration error sqrt(mean_φ (FPR_φ − α)²), pooled and per engine |
| F | ME-A2, ME-A3 | **Equal-engine-weighted calibration error**: the mean over audit engines of per-engine A2 (A3). **ME-A2 is the primary transport summary.** Continuity quantities (MSSP "equal-engine weighting") are also reported: EW-A1, EW-A2 and EW-A3, the metrics of the equal-engine average of FPR_{e,φ} |
| G | WE-A2 | Worst-engine nominal calibration error max_e A2_e |
| H | T | Cross-context threshold-transfer FPR. The threshold is calibrated on calibration phase i and applied to audit phase j (i ≠ j), pooled and per engine. The worst off-diagonal cell is also reported |
| I | FFR | κ-based healthy-flight false-flag rate at locked κ, pooled and per engine. Reported **separately** from the any-alarm healthy-flight fraction (share of healthy flights with ≥ 1 alarm row) and from events per healthy flight |
| J | TPR | Abnormal-state (`hs = 0`) row alarm rate over post-onset rows of delay-eligible audit engines, for all post-onset flights and for the first 10 post-onset flights, pooled and per engine |
| K | D | Matched-false-flag detection delay (§9) |

**Paired comparisons S − P for S ∈ {C, Q}:**
- ΔA1, ΔA2 and ΔA3 (pooled), ΔME-A2, ΔWE-A2 and ΔEW-A2;
- per engine, ΔA2_e;
- **n_worse** = #{e: A2_e(S) > A2_e(P)} and n_better = #{e: A2_e(S) < A2_e(P)};
- the frozen category rule (1–4) applied pooled and per engine.

**Material miscalibration.** A phase FPR outside [0.5α, 1.5α], i.e. an A2 ≥ 0.5α (≥ 0.5 pp at the primary 1%). It is used by the decision rules only; every value is reported regardless.

**Label-support rules.** LS-1 to LS-5 of the post-confirmation protocol apply. Every new-cohort audit engine already satisfies LS-1 to LS-3 (metadata audit), and is delay-eligible (≥ 1 healthy and ≥ 1 post-onset flight). The first-10-flight window needs ≥ 10 post-onset flights, which every new audit engine has.

## 7. Calibration-fleet composition intervention (mechanistic/design; brief §5–6)

**Fixed detector.** The fitted models do not change. Only the calibration rows used to set thresholds change.

**Composition eligibility.** The pool covers ≥ 2 classes: DS01, DS04, DS05, DS06, DS07 and DS08a, plus DS03 as a reference. DS08c and DS02 are not eligible.

**Fixed volume.** N = the largest multiple of 6,000 not exceeding half of the smallest calibration-pool engine's healthy rows (§3 table). Every design below uses exactly N rows unless marked *full*.

**Subsampling** (depends on calibration data only):
- For each pool engine g and draw r ∈ {0, 1, 2, 3, 4}, a permutation π_{g,r} of g's healthy calibration rows is drawn with `numpy.random.default_rng([20260930, r, g])`.
- A design that takes n_g rows from g uses the first n_g rows of π_{g,r*}. The draws are therefore nested and common across designs.
- n_g = N / (number of design classes) / (number of design engines of g's class). Any rounding remainder goes to the lowest-ID engines.
- The 5 draws are fixed now and are never chosen by outcome.

**Designs** (the *representative* engine of class k is the lowest-ID pool engine of class k):

| Code | Design | Members |
| --- | --- | --- |
| A | Single engine | Each pool engine alone |
| B | Same class, multi-engine | For each class with ≥ 2 pool engines, all of them. This covers DS04 class 3 (5, 6); DS08a class 1 (3, 9) and class 2 (5, 7, 8); DS03 has none |
| C | Mixed class | Each pair of classes, using representative engines |
| D | Leave one class out | For 3-class pools, identical to the C designs; for 2-class pools, identical to the single-class representative designs. Tagged, not duplicated |
| E | Class balanced | All pool classes, using representative engines |
| E+ | Class balanced, all engines | All pool engines, with N/(number of classes) per class split equally within a class (DS04, DS08a) |
| F | Row-count matched | All designs above are at N by construction |
| V | Volume (secondary) | Each pool engine at its *full* healthy volume, and the full pool (the primary calibration) |

**Arms and outputs:**
- **Arms.** P and C only. Q is excluded for cost: one linear program per design × draw × run × target.
- **Targets.** 0.5%, 1% and 2%.
- **Endpoints per design × draw × run × arm × target:**
  - the per-engine FPR_{e,φ}, A1_e, A2_e and A3_e;
  - pooled A1, A2 and A3;
  - ME-A2, WE-A2 and EW-A2;
  - the worst off-diagonal transfer FPR (arm C thresholds).
- **Reported values.** Draw means, with the range across draws.

**Composition endpoints** (all at fixed N; α = 1% primary):
- **CE1: within-engine coverage effect (primary composition endpoint).** For an audit engine e whose class k_e is represented in the pool, and a pool that also contains another class:
  - Δ_cov(e) = mean_{g: class(g) ≠ k_e} A2_e({g}) − mean_{g: class(g) = k_e} A2_e({g}), using single-engine designs (A) and draw means.
  - Δ_cov > 0 means that calibrating on the engine's own class transports better.
  - Using single-engine designs only removes the engine-count confound.
- **CE2: class-balanced versus single-class.** ME-A2(E) − mean_{g} ME-A2({g}), and ME-A2(E) − min_{g} ME-A2({g}); the same for WE-A2.
- **CE3: leave one class out** (3-class pools). For audit engines of class k: A2_e(E without class k) − A2_e(E).
- **CE4: engine count versus class coverage** (DS04, DS08a). ME-A2 of each 2-engine same-class design (B) against 2-engine mixed designs (C) that contain one of its engines.
- **CE5: volume.** For each audit engine e and each pool engine g of another class: Δ_vol(e, g) = A2_e({g}) − A2_e({g, full}). This is the benefit of more same-class volume for an uncovered engine, compared with the Δ_cov(e) of CE1.

## 8. Alarm-persistence robustness endpoints (robustness tier; brief §7)

These are computed for R0, R1 and R2 × arms P, C and Q × all runs × targets, at the arm's locked κ for that rule.

| ID | Endpoint |
| --- | --- |
| P1 | Healthy-flight false-flag rate FFR (κ-based), pooled and per engine; **WE-FFR** = max_e FFR_e |
| P2 | Any-alarm healthy-flight fraction, and alarm events per healthy flight (pooled, per engine) |
| P3 | Abnormal-state delay per engine at locked κ, and the fraction of engines detected within 0, 1, 3, 5 and 10 post-onset flights |
| P4 | Matched-false-flag delay curves per rule (§9) |
| P5 | Persistence calibration error, row level. The reference is r_cal = the pooled persistent-alarm row rate a_t on calibration rows (the calibration-set operating point). PA2_e = max_φ \|a_{e,φ} − r_cal\| / r_cal, with WE-PA2 and ME-PA2; n_worse for C and Q versus P on PA2_e. Under R0 with arm P, this is A2_e/α up to quantile ties |

The words "persistence improves calibration" are forbidden unless P5 improves. **The question is whether the cross-engine transport problem remains after a realistic persistence layer.**

## 9. Matched operating-point analysis (H7; frozen adversarial Part B, per rule)

This is Part B of the adversarial plan applied unchanged to every arm, rule, run and target.
- **Candidate κ grid.** {0} ∪ the healthy calibration-flight fractions of that arm, rule, run and target ∪ 400 log-spaced values in [10⁻⁴, 1]. It is calibration-only and data-free.
- **Anchors.** 2.5%, 5%, 10%, 15% and 20% realized pooled healthy audit FFR.
- **Matching.** The nearest rule (ties to the lower FFR, then to the larger κ), with the not-exceeding rule as a sensitivity.
- **Support.** A matched point is supported iff \|FFR − a\| ≤ 1/N_h, where N_h is the healthy audit flights of the subset.
- **Paired quantities.** Per-engine ΔD with the frozen censoring conventions; lower medians; earlier, same and later counts.
- **Curve-level mean.** The median delay averaged over realized FFR ∈ [2.5%, 20%] in 0.25-pp steps (71 points), excluding unsupported points.
- **Labels.** "Earlier at matched burden", "later at matched burden", "equal" and "mixed", as frozen.

**Comparisons:**
- C versus P and Q versus P, within each detector run and rule;
- across detectors, at matched anchors, as descriptive medians only. No raw scores are compared (brief §13).

**No extrapolation or interpolation.** An anchor without support is reported as unsupported. If fewer than 3 of the 5 anchors are supported for P and the compared arm at 1% in a subset, that comparison is reported as *not evaluable*. This is the frozen rule. It stops that comparison only, never the extension, because nothing is extrapolated.

## 10. Execution order, locks, one-shot markers and the access log

**Order (frozen).** Numeric then letter, for both locks and audits: DS01, DS04, DS05, DS06, DS07, DS08a, DS08c.

The reference work on DS02 and DS03 runs **after all seven new-cohort locks are committed and before any new-cohort audit**. It follows the same lock-then-evaluate code path; its data were opened long ago, so it has no one-shot gating.
- **Shakedown.** It is the engineering shakedown of the audit code: the endpoints, persistence, composition evaluation, matched delay and bootstrap. This is the same role DS02 Stage E played before.
- **After the shakedown.** Any code change that alters a number requires an amendment (§22) and a rerun of the reference work before the first new-cohort audit.
- **No influence on locks.** New-cohort locks cannot be influenced, because they are committed first.

**Phase L (per new subset; no official-test array is read):**
1. **Verify inputs.** Check the SHA-256 of the HDF5 against the extraction record, then run the CUDA check.
2. **Load data.** Load `hs = 1` rows of the fit and calibration pools as contiguous blocks. Assert that every value is finite (otherwise STOP, §18) and that no audit engine is present. Compute the F3 duplicate-check digests.
3. **Fit models.** Fit the correction and PCA and the Isolation Forests. Run the LSTM and CVAE epoch selection (selection-fit versus validation engine) and their refits. Save all models and record their hashes.
4. **Score calibration.** Score the calibration-pool rows for all 10 runs and fingerprint each score vector (SHA-256).
5. **Compute thresholds.** τ for P and C; the Q fits; κ for every arm × rule × run × α; and the composition-design thresholds for every design × draw × run × arm × α.
6. **Write the lock.** Write `results/extension/<subset>/lock/calibration_lock.json` by exclusive create. It holds the roles, row counts, model hashes, fingerprints, thresholds, κ values, composition definitions and code SHA. Hash the file and record the UTC time in `lock_record.json`, then append to `docs/extension/OUTCOME_ACCESS_LOG.md`.

All seven locks are committed to git **before** any audit (commit "Lock new-subset calibration plans").

**Phase A (per new subset, once, in frozen order, after all locks are committed):**
1. **Verify the lock.** Check the lock SHA-256 against the committed record. Reload the models, rescore the calibration rows, and require the fingerprints to be identical (otherwise STOP).
2. **Create the marker.** Create `results/extension/<subset>/audit/official_test_opened.json` by exclusive create **before** reading. If it already exists, the program refuses unless `--reproduction-only`, which recomputes into a new directory and never changes committed results.
3. **Read the audit rows.** Read `X_s` and `W` of all official-test rows (healthy and post-onset) and assert that the values are finite.
4. **Score and compute.** Score all runs and compute §6–§9 and §11.1. Composition designs are evaluated with the locked thresholds only.
5. **Write outputs.** Write all outputs by exclusive create with hashes, and append to the access log.

**The access log** records, for every subset:
- the metadata opening;
- the first healthy fit read, the first healthy calibration read, the first official-test sensor read and the first abnormal-row read (dates);
- the lock hash at first opening;
- the commit SHA and the run command;
- the output hashes.

## 11. Statistical units and uncertainty

- **Units.** The engine is the inferential unit, with flights nested. Rows are never treated as independent. The subset (dataset), within its family, is the visible top level.
- **Separate resampling.** Calibration and audit sampling are resampled separately. There are no timestamp-level tests and no p-values.
- **Seeds.** Stochastic detectors are reported seed by seed. Family seed means are descriptive, and the "seed population" is not bootstrapped.
- **Interval endpoints.** They are never averaged.
- **Significance.** No interval that includes zero is called significant.

### 11.1 Per-subset hierarchical bootstrap (U-EXT1)

- **Plans.** `numpy.random.default_rng(20260929)`, with frozen-style engine → flight plans (`final_validation.bootstrap_plans`) on the healthy calibration flights and then on the healthy audit flights, for 2,000 replicates.
- **Per run and target.** τ for P and C is re-estimated in each replicate (flight-weighted higher quantile). The recorded quantities are:
  - pooled A1, A2, A3 and overall FPR;
  - ME-A2 and WE-A2 over the drawn engines, with each engine's draw count as its weight;
  - EW-A2;
  - their C − P differences.
- **Intervals.** Percentile 95% intervals using `np.quantile` with the default linear method.
- **Coverage.** All new subsets and both reference subsets, all 10 runs, and all three targets.
- **Q.** It is point estimates only, because refitting the linear program per replicate is infeasible. This is stated wherever Q appears.

### 11.2 Cross-dataset hierarchical bootstrap (U-EXT2)

This two-stage hierarchy is family → subset → (engine → flight):
- In each of 2,000 replicates (`default_rng(20261002)`), families are resampled with replacement from the 5 new families. Within each sampled family, subsets are resampled with replacement.
- Each sampled subset contributes the value of one U-EXT1 replicate drawn uniformly at random, which carries the engine → flight level.
- **Statistic.** The median over sampled families of the family-mean subset effect, where a subset effect is the detector-family value: PCA, or the seed mean of IF, LSTM or CVAE.
- **Quantities.** ΔA1(C − P), ΔA2(C − P) and ΔME-A2(C − P), and the CVAE-minus-best-residual ME-A2(P), at α = 1%.
- **Caveat.** With 5 top-level units the interval is crude. It is reported with that statement and never as a population estimate.

### 11.3 Composition uncertainty

The unit is the per-engine CE1 value (the median over the 10 runs), per arm at 1%. A hierarchical bootstrap resamples family → subset → audit engine, with 2,000 replicates and `default_rng(20261001)`, and reports the family-median Δ_cov. Threshold sampling variability enters through the 5 fixed draws. There are no row- or flight-level composition intervals.

### 11.4 Persistence

These are point estimates with engine-level heterogeneity. There are no intervals.

## 12. Endpoint hierarchy and multiplicity control (brief §16)

| Tier | Content |
| --- | --- |
| PRIMARY | Nominal calibration transport across audit engines: ME-A2, WE-A2 and n_worse (C versus P; Q versus P; CVAE versus residual detectors) at 1% on the full calibration pool (H1, H3, H5) |
| SECONDARY | Between-phase disparity (H2) |
| SECONDARY | Matched false-flag detection delay (H7) |
| MECHANISTIC/DESIGN | Calibration composition (H4, CE1–CE5) |
| ROBUSTNESS | Alarm persistence (H6, P1–P5); targets 0.5% and 2%; EW metrics |
| BASELINE | The CVAE and the continuous contextual calibration Q (they are evaluated through the primary endpoints but are baselines, not proposed methods) |

**Multiplicity rules:**
- A secondary or design-level positive result is never elevated when the primary transport result fails. For example, "C reduces disparity" never becomes "C improves calibration" unless A2, ME-A2 and n_worse agree.
- Nothing is called significant.
- Every decision below is a pre-specified count rule on point estimates; intervals are reported beside them.

## 13. Hypothesis decision rules (primary target α = 1%; new families unless stated)

A *cell* is one subset × detector run. There are 70 new cells (7 subsets × 10 runs): 49 residual and 21 CVAE.

**Counting convention**, used wherever a rule does not state its own count:
- A **subset** holds a statement if it is true in a strict majority of the relevant runs: ≥ 4 of 7 residual runs, ≥ 6 of 10 runs, or ≥ 2 of 3 CVAE runs.
- A **family** holds it if a strict majority of its subsets do (F3 needs 2 of 3; every other family has one subset).
- Cell shares (for example, U_S) are always also broken down by family.

### 13.1 H1

A subset **shows material conditional miscalibration** if pooled A2(P) ≥ 0.5α for PCA and for the seed means of IF and LSTM. The CVAE is reported separately under H5.

| Verdict | Rule |
| --- | --- |
| SUPPORTED | ≥ 3 of 5 families |
| WEAK | 1–2 families |
| NOT SUPPORTED | 0 families |

The phase with the highest pooled FPR under P is reported per cell (brief §11A/B).

### 13.2 H2

Part 1 counts cells (all 10 runs) with ΔA1 = A1(C) − A1(P) < 0, pooled.

| Verdict | Rule |
| --- | --- |
| SUPPORTED | ≥ 80% of the 70 cells **and** ≥ 4 of 5 families, where a family holds if ≥ 7 of 10 runs hold in the majority of its subsets |
| PARTIAL | 50–80% of cells |
| NOT SUPPORTED | < 50% of cells |

Part 2 reports the share of cells with n_worse(C) ≥ 1. It is descriptive.

### 13.3 H3

For each S ∈ {C, Q}, a cell shows **uniform improvement** if every audit engine has A2_e(S) < A2_e(P). U_S is the share of the 70 cells with uniform improvement.

| Verdict per S | Rule |
| --- | --- |
| SURVIVES | U_S < 0.5 |
| MIXED | 0.5 ≤ U_S < 0.8 |
| REFUTED | U_S ≥ 0.8 |

H3 survives overall only if it survives for both C and Q. U_S is also reported separately for residual and CVAE runs.

### 13.4 H4

- **Run level.** A run *supports coverage* if the median of Δ_cov(e) over eligible audit engines is > 0.
- **Subset level.** A subset supports coverage if ≥ 7 of 10 runs support under **both** P and C.
- **Balance check.** It holds if ME-A2(E) < mean_g ME-A2({g}) in ≥ 7 of 10 runs under both P and C.
- **Families.** The four composition-eligible new families are F1, F2, F3 and F4.

| Verdict | Rule |
| --- | --- |
| SUPPORTED | ≥ 3 of 4 families support coverage **and** ≥ 3 of 4 families pass the balance check |
| NOT SUPPORTED | ≤ 1 family supports coverage |
| PARTIAL | Otherwise |

**Qualifiers** (descriptive; brief: do not force):
- *Weak* if the median over families of the family-median Δ_cov is < 0.25 pp.
- *Beyond volume* if the family-median Δ_cov exceeds the family-median CE5 Δ_vol for uncovered engines in ≥ 3 of 4 families.
- *Dataset-specific* if support is confined to ≤ 2 families.

### 13.5 H5 (CVAE)

The residual reference is the best of PCA, the IF seed mean and the LSTM seed mean on ME-A2(P) in the same subset.

| Quantity | Definition |
| --- | --- |
| (a) Reduces phase dependence | CVAE seed-mean pooled A1(P) < the minimum over residual families of pooled A1(P) |
| (b) Substantially improves | All 3 CVAE seeds have ME-A2(P) ≤ 0.5 × best residual ME-A2(P) |
| (c) Solves transport | All 3 CVAE seeds have WE-A2(P) < 0.5α |

| Verdict | Rule |
| --- | --- |
| H5 SURVIVES (conditioning does not guarantee transport) | CVAE WE-A2(P) ≥ 0.5α in the majority of CVAE runs in ≥ 3 of 5 families |
| H5 REFUTED | (c) holds in ≥ 4 of 5 families |
| MIXED | Otherwise |

(a) and (b) are reported per family. The C and Q arms under the CVAE are reported as secondary.

### 13.6 H6

The primary quantity is WE-FFR at locked κ under arm P. A cell has a **flight-level transport problem** if WE-FFR ≥ 0.10, i.e. twice the nominal 5%.

| Verdict | Rule |
| --- | --- |
| H6 SURVIVES (failures remain) | Under **both** R1 and R2, the flight-level transport problem occurs in the majority of residual cells in ≥ 3 of 5 families |
| PERSISTENCE ABSORBS | Under R1 **or** R2, WE-FFR < 0.10 in ≥ 80% of residual cells in ≥ 4 of 5 families, while under R0 the problem occurs in the majority of residual cells in ≥ 3 families |
| MIXED | Otherwise |

The secondary quantity is WE-PA2 ≥ 0.5 (material relative row-level error) under R1 and R2. It is reported beside the primary result, with n_worse on PA2 for C and Q versus P.

### 13.7 H7

Matched delays follow §9. The rule "C improves detection delay" (frozen) requires "earlier at matched burden" in ≥ 5 of 7 residual runs, with a lower curve-level mean than P, per subset and rule. For the CVAE, the same rule needs all 3 runs. Otherwise the text states that there was no general delay advantage at matched burden.

## 14. Interpretation matrix (brief §15; triggers fixed now)

The matrix stories are named **M-A to M-E**, so that they are not confused with the pre-extension MSSP "Story B: calibration transport".

| Story | Trigger (new families, α = 1%) |
| --- | --- |
| **M-E** Original effect is dataset-specific | H1 holds in ≤ 2 of 5 families |
| **M-A** Representation solves transport | H5(b) holds in ≥ 4 of 5 families **and** H5(c) holds in ≥ 3 of 5 families |
| **M-B** Calibration-fleet coverage dominates | H4 SUPPORTED with the *beyond volume* qualifier |
| **M-C** Transport failure is broad | For every detector family (PCA, IF, LSTM, CVAE) and every arm (P, C, Q), WE-A2 ≥ 0.5α in the majority of runs in ≥ 3 of 5 families |
| **M-D** Alarm policy absorbs the problem | H6 = PERSISTENCE ABSORBS |

**Selection:**
- Every triggered story is reported.
- **Headline precedence:**
  1. M-E;
  2. M-A;
  3. M-C together with M-B if both are triggered ("context-aware calibration does not itself guarantee transport; calibration-fleet coverage is a primary determinant"), otherwise whichever of M-C or M-B is triggered;
  4. M-D.
- If none triggers, the story is **MIXED**: the manuscript reports the conditions under which each method fails, and nothing is forced.

## 15. Classification of the original (pre-extension) story (brief §11)

The components, evaluated per new family (a family holds a component if the majority of its subsets hold it), are:

| ID | Component | Subset-level rule |
| --- | --- | --- |
| S1 | Pooled calibration leaves material conditional miscalibration | H1 rule |
| S2 | C reduces pooled disparity | ΔA1 < 0 in ≥ 7 of 10 runs |
| S3 | The pooled correction fails to transport uniformly | n_worse(C) ≥ 1 in ≥ 6 of 10 runs |
| S4 | No general matched-delay advantage for C (R0) | Fewer than 5 of 7 residual runs are "earlier at matched burden" with a lower curve mean |
| S5 | The continuous context Q fails on some engine | WE-A2(Q) ≥ 0.5α in ≥ 6 of 10 runs |

| Class | Rule |
| --- | --- |
| **GENERALIZED** | S1, S2, S3 and S4 each in ≥ 4 of 5 families, S5 in ≥ 3, and H4 at least PARTIAL |
| **PARTIALLY GENERALIZED** | S1 and S3 each in ≥ 3 of 5 families, but not GENERALIZED |
| **CONFIGURATION-SPECIFIC** | S1 or S3 in only 1–2 families, and not REFUTED |
| **REFUTED** | S1 in 0 families, **or** C increases pooled disparity (ΔA1 > 0 in ≥ 6 of 10 runs) in ≥ 3 of 5 families |

**Descriptive answers to brief §11A–G**, reported beside the class:
- (A) descent-highest counts;
- (B) phase dependence versus ordering;
- (C) = S2;
- (D) = S3;
- (E) = H4;
- (F) = H5;
- (G) = H6.

## 16. Automatic rescope flags (brief §24)

Any flag raised is written to the final report for author review.

| Flag | Condition |
| --- | --- |
| A | H1 holds in ≤ 2 of 5 families (most new subsets show negligible conditional miscalibration) |
| B | H5 REFUTED (the CVAE almost completely eliminates the transport problem) |
| C | H6 = PERSISTENCE ABSORBS |
| D | H4 NOT SUPPORTED (no reproducible relation between class coverage and transport) |
| E | ΔA1(C − P) > 0 in ≥ 6 of 10 runs in ≥ 3 families, **or** descent is the *lowest* pooled phase under P for PCA and both seed means in ≥ 3 families (opposite effects to DS02/DS03) |
| F | For C versus P, pooled ΔA2 < 0 but ΔME-A2 > 0 or ΔEW-A2 > 0 in ≥ 6 of 10 runs in ≥ 3 families (equal-engine weighting repeatedly reverses pooled conclusions) |

## 17. After the results: coherence gate and title

Brief §25–§26 are applied **after** the results. The procedure is fixed now:
1. Determine the M-story (§14) and the original-story class (§15).
2. Choose among ONE PAPER, ONE PAPER + LARGE SUPPLEMENT and SPLIT by whether the primary transport result and at most one design-level result carry the paper. SPLIT is recommended only if the composition result (H4 SUPPORTED) or the CVAE result (M-A) is a separate methodological contribution that the calibration-transport question cannot hold within MSSP's 25 pages.
3. Choose the title from the brief's families to match the selected story. There are no sensational negative titles and no forbidden words.

## 18. Stop rules (brief §29; operational)

Execution stops immediately and reports if any of the following occurs:
- `docs/mssp/frozen_baseline.sha256` fails before or after any stage;
- an input HDF5 SHA-256 differs from the extraction record;
- non-finite values appear in a loaded array;
- an official-test array is requested without a committed, hash-verified lock (the code refuses);
- an audit engine appears in fit or calibration rows;
- a calibration or audit engine enters epoch selection;
- a lock or model fingerprint fails to reproduce;
- the one-shot marker already exists (the code refuses);
- a CVAE or LSTM loss is non-finite;
- CVAE or LSTM tuning would need official-test outcomes (none is permitted, so any such need stops the work);
- a subset cannot support the phase rule (already excluded by C8);
- fair row-count matching is impossible for a composition-eligible subset (N < 6,000);
- a comparison would need extrapolation outside matched support. That comparison is reported as not evaluable and is never extrapolated;
- any step would redefine or re-run the original DS03 confirmation.

## 19. Leakage and information-exposure audit

| # | Channel | Control |
| --- | --- | --- |
| X1 | Audit engines in fitting, epoch selection or calibration | R-ALLOC roles are asserted at every load; tests |
| X2 | Official-test data before the lock | Phase A gating on the committed lock; exclusive-create marker; tests |
| X3 | `hs = 0` rows in fitting or calibration | Only `hs = 1` rows of fit and calibration engines are loaded |
| X4 | Labels as detector inputs | Phase, `hs`, Fc and unit are never inputs (static and invariance tests) |
| X5 | Retrospective phases use within-flight future altitude | Arm C is labelled an oracle diagnostic. The CVAE and other detectors do not use phases |
| X6 | Composition chosen from outcomes | Designs, N and draws are fixed here from metadata and calibration data only |
| X7 | Prior knowledge of DS02/DS03 outcomes | The new cohort decides every hypothesis. DS02 and DS03 are reference only |
| X8 | Flight-profile reuse across subsets and engines | Disclosed. Families are the top level. Some audit-engine routes also occur in fit data (for example, the class-1 library), which is part of the realistic setting and is reported |
| X9 | Healthy altitude of test engines read at the metadata stage | Disclosed. It is an exogenous flight-profile input and carries no sensor, score or outcome information |
| X10 | Tuning after outcomes | Nothing is tunable after the locks. Amendments follow §22 |

## 20. Compute budget (estimates; recorded actuals in the final report)

- **Disk.** New HDF5 files of ≈ 22 GB (already extracted). Models, checkpoints and outputs are expected at ≈ 2–5 GB.
- **RAM.** Peak ≈ 8–12 GB per subset (DS08a audit: ≈ 3.7 M rows).
- **GPU.** Under 2 GB of VRAM.
- **Phase L, per new subset:**
  - load ≈ 1 min;
  - PCA and IF ≈ 3 min;
  - LSTM selection and refit ≈ 10–25 min (3 seeds);
  - CVAE ≈ 5–20 min (3 seeds);
  - calibration scoring ≈ 2 min;
  - 30 Q linear programs ≈ 10–15 min on 16 parallel processes;
  - composition thresholds ≈ 2 min.
  - The total is ≈ 35–70 min per subset, or ≈ 4–8 h for seven.
- **Reference work (DS02, DS03).** CVAE training, rescoring and Q refits take ≈ 1–1.5 h.
- **Phase A, per subset.** Audit scoring ≈ 5–15 min; endpoints and the U-EXT1 bootstrap ≈ 15–30 min; matched delay per rule ≈ 5–10 min. The total is ≈ 3–6 h for seven.
- **Overall.** ≈ 9–16 h, with no redundant experiment.

## 21. Tests required before any scientific stage (`tests/test_extension_*.py`)

The tests cover:
- subset schema compatibility;
- engine-disjoint partitions and R-ALLOC determinism;
- no audit-engine fitting;
- no calibration-engine epoch selection;
- no official-test or abnormal read before the lock, and marker ordering;
- class-balanced row-count matching and fixed calibration volume;
- no audit-outcome use in composition selection (designs built from metadata only);
- CVAE condition inputs, only from legitimate descriptors;
- no phase labels and no health labels as inputs, via invariance tests;
- persistence-rule definitions (R1, R2, flight resets, events);
- the matched-false-flag no-extrapolation rule;
- nominal calibration error and equal-engine weighting (ME, EW, WE);
- the family → subset → engine → flight bootstrap hierarchy;
- one-shot marker behaviour;
- immutability of the historical frozen baseline;
- equality of the reimplemented LSTM selection with the frozen loop, on synthetic data;
- CVAE determinism and row independence.

## 22. Amendments

- Any change after this freeze is logged in `docs/extension/AMENDMENTS.md` with its date, the exact change, the reason, whether it preceded any new outcome, and the outputs affected.
- An amendment after an outcome is reported as post hoc.
- Affected stages rerun into new directories; nothing is overwritten.
- No amendment may change a lock after the first audit, the cohort, R-ALLOC, the targets or the decision rules.
