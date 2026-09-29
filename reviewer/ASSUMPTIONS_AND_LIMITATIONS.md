# Assumptions and limitations — ncmapss-phase-entanglement (MSSP extended manuscript)

Every item is anchored to a manuscript location or a repository file. Items in C–H are this audit's reading of the code and
outputs; they are not claims made by the manuscript.

## A. Explicitly acknowledged assumptions

| # | Assumption | Where stated |
|---|---|---|
| A1 | N-CMAPSS simulated trajectories are an adequate test bed for calibration transport; "no deployment claim" | §1 "Scope" p. 3; §5.5 |
| A2 | The engine is the inferential unit; flights are nested; rows are never treated as independent; families are the top level | §3.9 p. 7 |
| A3 | Flight class is an observable, coarse descriptor of latent operating regimes and is "never called causal" | Protocol §1 (organizing hypothesis); implicit in §3.8 |
| A4 | The health label hs marks a simulated degradation onset, not a discrete fault event; abnormal endpoints are relative to that label | §3.3 p. 5 |
| A5 | Retrospective phases (90% within-flight altitude rule) are a meaningful context variable, even though C cannot be implemented online | §3.5 p. 6 ("C is a retrospective diagnostic") |
| A6 | Q is an adversarial control, not a proposed method | §3.5 |
| A7 | Detectors are compared only through calibrated quantities at the same α, never through raw scores | §3.4 p. 5 |
| A8 | The freeze is internal (committed and hashed), not externally registered | §3.2, §5.5 |

## B. Explicitly acknowledged limitations (§5.5 p. 16 unless noted)

1. One simulator, reusing a finite flight library; no real-aircraft or independently sourced validation.
2. Small units: five new families, one to three calibration engines per class, 14–36 healthy flights per audit engine.
   Whether an individual engine's error exceeds noise depends on the reference.
3. The pre-specified per-subset bootstrap did not stratify calibration engines by class (quantified in §4.8).
4. Coverage design: class coverage is confounded with engine identity and shared missions. The volume contrast cannot show
   substitution.
5. One condition-aware model: fleet-trained, with the score omitting the latent-prior term. Per-engine or early-cycle training
   (as in [N38]) was not tested.
6. Retrospective phases, simulated labels, low early sensitivity.
7. Fixed lines: the material and false-flag lines are pre-specified but arbitrary; A2 does not distinguish over- from
   under-alarming; H1 and H4 sat exactly on their thresholds.
8. Fit pools of three engines (DS03 had seven). In six of seven subsets the validation engine's class was absent from the
   selection-fit engines.
9. Internal freeze only.
10. §3.11: "the pipeline has not been independently reimplemented".
11. §4.6: delay comparisons have little power; burden was matched on the pooled rate.

## C. Implicit assumptions visible in the implementation

| # | Assumption | Evidence |
|---|---|---|
| C1 | The `method="higher"` empirical quantile gives a conservative finite-sample threshold. The small-sample bias of the per-phase quantiles (fewer rows per phase) is not modelled | `src/mssp_mitigation.py:q_higher`; `src/ext_calibration.py:quantile_taus` |
| C2 | κ as a 0.95 quantile over **calibration-flight** fractions assumes calibration flights are exchangeable with audit flights at the flight level | `src/ext_calibration.py:kappa` |
| C3 | GPU float32 scoring is treated as exact for reproduction purposes after Amendment 3. Scores depend on batch composition at rounding level | Amend. 3; `src/ext_pipeline.py:score_audit` |
| C4 | Hash-locked binaries define the models. Retraining is not expected to reproduce them bitwise (GPU nondeterminism) | Locks `models.files`; `docs/ENVIRONMENT.md` |
| C5 | The composition subsamples thin rows uniformly across an engine's flights, so "volume" means rows, not flights, engines or missions | §3.8; `src/ext_calibration.py:design_rows` |
| C6 | A subset or family "holds" by strict-majority vote over runs, treating seeds as votes although they are near-replicates | Protocol §13 counting convention; `src/ext_summary.py:family_holds` |
| C7 | The 1 Hz rows are the natural time unit. Within-flight persistence windows (3–5 rows) are seconds long | §3.7 |
| C8 | Q's quadratic surface in 4 standardized descriptors is adequate within the calibration envelope; extrapolation outside it is not guarded | Protocol §5; `src/ext_calibration.py:q_features` |
| C9 | Phase labels need complete flights (min/max altitude per flight), so C uses future information within a flight | `src/confirm_frozen_ds03.py:primary_phase` |
| C10 | The metadata audit's reading of healthy-row altitude for test engines (for phase feasibility) is not an outcome access | `docs/extension/SUBSET_SELECTION_LOCK.md`; `src/ext_subset_metadata.py:phase_feasibility` |

## D. Limitations visible in the code or results but not emphasized

| # | Observation | Evidence | Manuscript treatment |
|---|---|---|---|
| D1 | LSTM validation loss was 138–234 (standardized MSE) in DS01 and DS08c, against 0.07–0.19 elsewhere. Epoch selection there tracked an out-of-class engine | `docs/extension/EXTENSION_HOSTILE_REVIEW.md` §3 (last row); `*/lock/training_history.csv` | §5.5 mentions class absence, not the loss magnitude |
| D2 | CVAE decoder log-variance at its lower bound for many channels (variance-floor share up to 74% per the hostile review), and seeds differ up to tenfold | Locks `cvae_variance_bound_share`; Table S3; review §2.1 | §5.2 notes the variance floor; seed spread not highlighted |
| D3 | The abstract says "27 of 30" without naming the arm (C). P gives 29 and Q 28, and the sampling reference gives 13/17/18 | `focused_validation/summary/engine_summary.csv` | §4.8 gives all the numbers; the abstract does not |
| D4 | The per-subset U-EXT1 intervals are partly driven by replicates that drop a whole class (78% of replicates in DS01/DS05–07) | `post_hoc_checks.json["bootstrap_class_omission_probability"]` | §4.7, §4.9 and §4.8 quantify it (11–15% of width) |
| D5 | Families F3 (DS05–07) share identical healthy flight sequences. Five "families" is the effective N for every cross-dataset statement, so all interval statements rest on 5 units | §3.1; `profile_sharing_by_dataset.csv` | Stated ("crude") |
| D6 | The CI fix `3a4de78` relaxed the κ-grid comparison to `atol=1e-15`, because bitwise κ equality is platform-dependent | `tests/test_mssp_adversarial.py` diff | Not in the manuscript (test only) |
| D7 | A single out-of-envelope flight produces the largest covered-class failure. The "envelope" mechanism rests on one flight of one engine | `post_hoc_checks.json["ds08a_engine14"]` | Stated as observed, post hoc |
| D8 | The focused-validation reference and local recalibration were run only at α = 1% and k = 5 | `src/ext_focused_validation.py` (`ALPHA=0.01`, `K_LOCAL=5`) | Stated in §3.10 |

## E. Likely reviewer attack points

These are the concerns the repository's own four-reviewer hostile panel found (`docs/extension/EXTENSION_HOSTILE_REVIEW.md`), plus
new ones from this audit. Each is expanded in `LIKELY_REVIEWER_QUESTIONS.md` and `ISSUE_BANK.md`.

1. The negative headline could be "guaranteed by construction": strict every-engine and worst-engine rules with few flights.
   Mitigated post hoc (§4.8–4.9), but the pre-specified H3/H6 rules remain weak discriminators.
2. A2 lumps together in-sample pooling error, transport error and direction (C010, C034).
3. Knife-edge decisions (H1 3/5, H4 exactly 7/10 in F1/F2).
4. Coverage confounded with engine identity and shared missions; only 4 composition-eligible families.
5. Weak or unusual comparators: the C oracle, unregularized Q, one CVAE. There is no class-conditional or causal per-unit baseline.
6. Persistence tested at the wrong time scale (within-flight seconds), and matched delay on pooled burden with low power.
7. Novelty and venue fit: "a case study of existing detectors on one simulated benchmark" (editor persona: "roughly even
   odds of desk rejection").
8. Internal freeze; amendments added after the freeze (though before outcomes).
9. Extensive use of AI coding agents to write and run the analyses (§3.11 and the AI declaration).

## F. Claims that must not be strengthened without new evidence

- Anything about real engines or fleets, other simulators or deployment.
- "Class coverage is necessary", or "is the cause of transport", or "more data cannot substitute": the manuscript explicitly
  withdrew the last one.
- "Condition-aware representations do not solve transport" (general). Only one fleet-trained CVAE was tested.
- "Persistence or alarm policies cannot fix transport". Only within-flight on-delays were pre-specified; the two-flight rule is post hoc.
- "No delay advantage". Say only "no advantage meeting the pre-specified criterion".
- "Local recalibration does not help". Only k = 5, first-five-flights, per-phase quantiles were tested.
- Any per-engine transport failure for an individual engine near the 0.5 pp line.
- Any statement that the freeze constitutes preregistration.

## G. Generalization limits

- **Data:** one simulator (C-MAPSS dynamics), one flight library, 7 new + 2 reference subsets, 5 new families, 30 audit engines.
- **Detectors:** residual PCA, IF, a past-only LSTM, and one CVAE, all on the same 32-descriptor correction.
- **Targets:** 0.5, 1 and 2% row-level; flight rule at a nominal 5%.
- **Phases:** retrospective, altitude-based. Other context variables (e.g. regime clustering) were not tested in the extension.
- **Sampling:** 1 Hz rows. Real monitoring often uses snapshot or flight-summary data.

## H. Potential confounding factors

| Factor | Why it confounds | Where visible |
|---|---|---|
| Engine identity vs class | Most pools have one engine per class | §5.5; composition design |
| Shared recorded missions | Same-class pairs share 35–56% (class 1) / 5–20% (classes 2–3) of flight profiles | §4.9; `profile_sharing_engine_pairs.csv` |
| Cross-subset engine identities | DS01 test 7 ≡ DS03 dev 9; DS08a test 15 ≡ DS03 dev 5; DS01 dev 2 ≡ DS08a test 14. DS08a test 14, the largest covered-class failure, is the same engine as DS01 development engine 2 | Protocol §2 names the pairs; the manuscript (§3.1, line 89 of the Markdown) says only "several engines recur across other subsets" and does not list them |
| Flight envelope | Out-of-envelope flights drive errors regardless of class | §4.9 (DS08a e14) |
| Initial-health variation between engines | N-CMAPSS engine heterogeneity is initial health plus mission; it is not separated from class | Review §2.2 item 4 |
| Validation-engine class mismatch | May bias LSTM/CVAE epoch selection per subset | §5.5; D1 |
