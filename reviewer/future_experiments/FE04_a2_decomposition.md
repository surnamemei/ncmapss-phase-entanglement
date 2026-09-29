# FE04: decomposing per-engine A2 into in-sample pooling error, transport error and sign (prepared, not run)

**Scientific question.** A2 = max_φ |FPR_φ − α| mixes three things:
- (i) the error the pooled threshold already has on the calibration engines themselves (in-sample phase error; C010);
- (ii) the additional error on held-out engines (transport);
- (iii) the direction, over- or under-alarming (53% of material P errors are under-alarming; C034).

How much of each engine's A2 is transport?

**Trigger.** Run only if a reviewer says A2 conflates error sources, or disputes counting under-alarming as a false-alarm
failure (Q29, Q30, I-02, I-03).

**Required inputs.** All are committed, so no raw data or GPU is needed:
- `results/extension/<DS>/lock/calibration_in_sample_phase_fpr.csv`: calibration-pool in-sample FPR per phase, run and arm.
- `results/extension/<DS>/audit/phase_fpr.csv`: per-engine, per-phase audit FPR, with counts `n` and `alarms`.
- `results/extension/<DS>/audit/paired_transport_engines.csv`: for cross-checking A2.

**New computation.** For each engine, run and arm at α = 1%:
- the transport gap per phase = audit FPR_φ − in-sample FPR_φ;
- the signed A2 (the argmax phase error with its sign);
- the share of A2 explained by the in-sample error.

Summarize by family. A variant of H1 that counts only over-alarming (FPR_φ − α ≥ 0.5α) is a one-line change, and must be
labelled post hoc.

**Proposed script.** `reviewer/future_experiments/fe04_a2_decomposition.py`, a new read-only file that writes only to
`results/reviewer_fe04/`.

**Expected outputs.** A per-engine decomposition table, family summaries and the post hoc over-alarming-only H1 count. The
internal review predicted that only F4 holds under that criterion (`docs/extension/EXTENSION_HOSTILE_REVIEW.md` §2.2). That is
unverified, and it would weaken H1 if confirmed.

**Compute estimate.** CHEAP_CPU, in seconds.

**What it could support.** A clearer statement of how much per-engine error is attributable to transport, and an honest
answer to the direction question.

**What it could not support.** Any change to the pre-specified H1 verdict.

**Risk.** The over-alarming-only count may be unfavourable: F4 only, if the hostile review is right. Weigh that before offering
this analysis unprompted.
