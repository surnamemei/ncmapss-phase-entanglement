# Extension charter: final scientific extension of the calibration-transport study

**Date.** 2026-09-28.
**Branch.** `mssp-extended`, created from `mssp-revision` at `d5699a10ac816b73a18d2bd22de0afdcdb217653`.
**Pre-extension snapshot.** Annotated local tag `mssp-pre-extension-2026-09-28` → `d5699a1`. It is not pushed, and no release is created.

## 1. What existed before this extension

The submission-ready MSSP manuscript on `mssp-revision` tells **Story B: calibration transport**. It is locked in `docs/mssp/FINAL_STORY_LOCK.md` (commits `ce2e25a` and `cf64361`). In summary:
- pooled calibration loses conditional (phase-wise) validity;
- the effect was discovered on DS02 and reproduced once, under a frozen protocol, on held-out DS03 engines;
- retrospective phase-conditioned thresholds reduced pooled between-phase disparity, but the pooled correction did not transport reliably to individual engines;
- the strongest observed failures coincided with flight classes absent from calibration;
- equal-engine weighting reversed the DS02 pooled improvement;
- there was no general detection-delay advantage at matched false-flag burden;
- a continuous context threshold (Q) failed on different engines;
- nearest-neighbour operating-support distance did not explain the failures.

**State verified at the tag (2026-09-28):**
- 86/86 tests pass (`python -m unittest discover -s tests`).
- The 186-file frozen baseline (`docs/mssp/frozen_baseline.sha256`) verifies.
- `paper/mssp/verify_draft_numbers.py` re-derives all 81 cited values.
- The MSSP evidence `SHA256SUMS` (48 files) verifies.
- The Stage L lock hashes and 120 recorded output hashes of the post-confirmation and adversarial runs verify.
- The working tree is clean apart from the untracked `paper/ress/cover_letter_final.txt`, which is not touched.

**Story B and every number behind it predate this extension.** They were fixed from DS02 and DS03 alone.

## 2. Why the extension can falsify Story B

The extension asks four questions that the pre-extension evidence could not answer:

| Question | What would weaken or falsify Story B |
| --- | --- |
| **Q1.** Does the transport problem persist for a detector that conditions its representation on operating conditions (one pre-specified conditional variational autoencoder, CVAE)? | The CVAE largely removes phase-conditional miscalibration and cross-engine transport failures. The story would then shift towards representation-level conditioning (interpretation-matrix Story A). |
| **Q2.** At a fixed calibration volume, does calibration-fleet composition (flight-class coverage) control transport beyond raw calibration row count? | Class coverage has no reproducible relation to transport. The flight-class reading of Story B would then be weakened or removed. |
| **Q3.** Does the transport problem survive realistic alarm-persistence rules (3 consecutive; 3 of 5)? | Persistence absorbs the practical false-flag and delay problem at matched burden. The problem would then be one of raw row-level thresholding only (Story D). |
| **Q4.** Does the story generalize to previously unopened N-CMAPSS subsets and engines? | New subsets mostly show negligible phase-conditional miscalibration, or effects opposite to DS02/DS03. The original evidence would then be configuration-specific (Story E). |

**Rules:**
- The interpretation matrix (Stories A–E) and the endpoint hierarchy are frozen in `docs/extension/GENERALIZATION_PROTOCOL.md` before any new outcome is computed.
- The final story is chosen by those pre-specified rules, not by preference. If the rules select a story other than B, the manuscript is rewritten.
- A negative, dataset-specific or split outcome is an acceptable result.

## 3. Boundaries

**Immutable.** The following are never modified:
- `main`, `v1.0.0` and `ress-submission-2026-09-25`;
- the original RESS package (`paper/ress/`, `paper/submission/`);
- the frozen DS02 discovery and the frozen DS03 confirmation (the 186-file manifest, `results/final_validation/`, `results/confirmation_ds03/` and the one-shot marker);
- the post-confirmation and adversarial history (`results/mssp_mitigation/`, `results/mssp_adversarial/`, `docs/mssp/`);
- the `mssp-revision` branch and its manuscript history.

All new work is written to new paths on `mssp-extended`:
- `docs/extension/`;
- `results/extension/`;
- new `src/` and `scripts/` modules;
- new tests;
- later, a separate manuscript directory.

**Outcome discipline:**
- No new N-CMAPSS sensor value is read before the metadata-only subset selection (`docs/extension/SUBSET_SELECTION_LOCK.md`) and the protocol are committed.
- No official-test (audit) array of a new subset is read before that subset's calibration lock exists, is hashed, and is recorded in `docs/extension/OUTCOME_ACCESS_LOG.md`.
- Every official audit runs once, guarded by a one-shot marker.
- Nothing is tuned after an outcome is seen.
- An excluded subset is never opened because another subset gave an inconvenient result.

**Statistical units.**
- Engines are the inferential unit, with flights nested in engines. Datasets are a visible top level.
- Rows are never treated as independent replicates.
- An interval that includes zero is never called significant.

**Scope limits:**
- No push, release, journal submission or Elsevier transfer is part of this work.
- Frozen DS03 confirmation results are never re-labelled, and post-confirmation or extension results are never presented as part of that confirmation.
- Internally frozen protocols are never called externally preregistered.

## 4. Stop rules (from the author's brief, §29)

Execution stops and is reported if any of the following occurs:
- historical frozen hashes change;
- official-test data are opened before a calibration lock;
- an audit engine enters training;
- a calibration engine influences hyperparameter or epoch selection;
- CVAE tuning would need official-test outcomes;
- subset eligibility cannot be established without reading outcomes;
- HDF5 corruption or inconsistency is detected;
- row-count matching cannot be done fairly;
- a comparison would need extrapolation outside matched operating support;
- a new dataset cannot support the phase definition;
- the work would require redefining the original DS03 confirmation.

## 5. Planned sequence

1. Metadata-only audit of unopened subsets and a committed selection lock (no sensor values).
2. A frozen generalization protocol: hypotheses H1–H7, endpoints, splits, weighting, targets, composition designs, persistence rules, bootstrap, interpretation matrix and stop rules.
3. The CVAE specification and data-free tests (synthetic, leakage, determinism, memory and runtime), committed before any real training.
4. Per subset, in frozen numeric order: model fits on fit engines only; epoch selection on fit-pool validation only; calibration scores; thresholds and composition designs locked, hashed and time-stamped.
5. Official audits of all eligible subsets, once each, in frozen numeric order, after every lock exists.
6. Cross-dataset summaries, the extension evidence ledger (`EX…` IDs), the prior-art update, the hostile review and the final report.
7. Only then, a manuscript rescoped by the pre-specified rules.

## 6. Use of AI tools

This extension is planned, coded, executed and documented by Claude (Anthropic; Claude Opus 5.5 through Claude Code) working under the author's written brief. The author reviews and approves all conclusions. This will be disclosed in the manuscript's AI declaration together with the earlier ChatGPT/Codex and Claude assistance.
