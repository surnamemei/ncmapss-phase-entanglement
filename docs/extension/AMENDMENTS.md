# Amendments to the generalization protocol

This log is kept under `GENERALIZATION_PROTOCOL.md` §22. Each entry records:
- the date;
- the exact change;
- the reason;
- whether it preceded any new outcome;
- the outputs affected.

## Amendment 1 (2026-09-28): closing two classification gaps

**Timing.** This amendment preceded every new outcome. It was made while encoding the frozen decision rules in `src/ext_summary.py`, before any new-subset sensor value was read and before any extension score existed.

**Change 1: original-story classification (§15).** Under the frozen text, the case "S3 holds in 0 families while S1 holds in ≥ 3 families" matched no class. S3 holding in no family means the pooled correction transported uniformly in every new family. The classes are now evaluated in this order:
1. **REFUTED:** S1 in 0 families, **or** S3 in 0 families, **or** C increases pooled disparity (ΔA1 > 0 in ≥ 6 of 10 runs) in ≥ 3 of 5 families.
2. **GENERALIZED:** unchanged.
3. **PARTIALLY GENERALIZED:** S1 and S3 each in ≥ 3 of 5 families, and not GENERALIZED (unchanged).
4. **CONFIGURATION-SPECIFIC:** every remaining case, which means S1 or S3 holds in only 1–2 families.

**Change 2: H2 verdict (§13.2).** Under the frozen text, the case "≥ 80% of cells hold but fewer than 4 families hold" had no verdict.
- **PARTIAL** now means every case with ≥ 50% of cells that is not SUPPORTED.
- SUPPORTED and NOT SUPPORTED are unchanged.

**Reason.** Both rules were incomplete partitions: some outcome configurations fell under no class. The amendment only assigns a class to those configurations. No threshold changes.

**Outputs affected.** None exist yet.

## Amendment 2 (2026-09-28): CVAE numerical safeguards after a stop-rule halt

**Timing.** This amendment preceded every new outcome. It was made after the first Phase L run for DS01 halted, and before any lock was written, any official-test array was read, or any CVAE score was used.

**Event.** Protocol §18 ("a CVAE or LSTM loss is non-finite") fired during `lock DS01` at 03:39:50Z. The CVAE refit for seed 1 on fit-pool healthy rows went NaN at epoch 101 of 126. It was not retried with other settings.

**Diagnosis.** The fit-pool healthy rows (`/scratchpad/diag_cvae.py`, not committed) showed three things:
- The decoder log-variance sat at its lower bound (log 10⁻⁴) throughout training: some channels are nearly deterministic given the operating descriptors.
- Gradient norms were routinely 10³–10⁴.
- At epoch 98 a gradient spike (≈ 7.8 × 10⁶) pushed the **unbounded** encoder log-variance from about 3 to 107, and `exp` overflowed.

**Change** (`src/ext_cvae.py`, uniform for every subset and seed, including DS02 and DS03):
1. The encoder log-variance is soft-bounded to [log 10⁻⁸, log 10²], with the same smooth bound already used for the decoder.
2. The global gradient norm is clipped at 1.0 before every Adam step, in both selection and refit.

**Unchanged:** the architecture, objective, score, data, epoch-selection rule, seeds and every other constant. Adam is approximately invariant to a common rescaling of gradients, so clipping bounds spikes without materially changing routine updates.

**Check.** On the DS01 fit pool, all three seeds now train to completion: 75, 52 and 36 epochs are selected, and nothing is non-finite. No other subset was pre-checked, and the stop rule remains in force.

**Outputs affected.** None exist. The halted run wrote only LSTM checkpoints to the git-ignored `results/extension/DS01/models/`. Those are deleted, and Phase L for DS01 reruns from scratch under this amendment.

## Amendment 3 (2026-09-28): score healthy and post-onset audit rows separately (shakedown finding)

**Timing.** This amendment was made during the DS02/DS03 reference shakedown (protocol §10), before any new-cohort official-test array was read.

**Finding.** The first reference attempt scored all audit rows (healthy and post-onset) of a subset in one call.
- DS02 passed every gate and all eight cell-by-cell shakedown checks.
- DS03 stopped at the reproduction gate: the LSTM seed 0 scores of healthy audit rows differed from the frozen Stage C fingerprint, while every calibration fingerprint matched.
- The frozen stages scored healthy rows (Stages C/D) and abnormal rows (Stage E) in separate calls. LSTM scores are chunked within flights, but GPU batches mix chunks, so their values depend at float32 rounding level on which other flights are scored in the same call.

**Change.** `src/ext_pipeline.py` gains `score_audit`, which scores healthy and post-onset rows in separate calls and restores file order. It is used by the reference work and by every new-cohort Phase A audit. Because `hs` is constant within flights, each call receives whole flights.

**Unchanged.** Models, thresholds, locks, endpoints and decision rules.

**Scope.** The change applies uniformly. New-cohort outcomes do not exist yet, and new-cohort locks are unaffected, since calibration scoring is unchanged.

**Consequence.** Per protocol §10, the reference work is rerun under this amendment before the first new-cohort audit. The first attempt's outputs are archived unchanged in `results/extension/_shakedown_attempt1/` (model binaries removed).
