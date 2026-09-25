# Skeptical manuscript audit

Scope: assembled Markdown and frozen evidence only; no new experiments or protocol changes. I read the manuscript as a reviewer looking for reasons to reject an overstrong calibration claim. The central pooled directional statement survives the ledger check, but the manuscript is not yet a finished submission artifact.

## Five strongest aspects

1. A sharply specified endpoint: healthy row-level FPR at a nominal pooled threshold, with phase-conditional and cross-phase-transfer checks kept distinct.
2. DS02 discovery and DS03 one-shot frozen confirmation are separated in design and wording [M0034; E010950, E010951, E012861, E012862, E013134, E013135].
3. PCA, Isolation Forest, and the causal LSTM network are compared under shared correction/calibration rules without claiming detector independence [E000109, E002629, E002989].
4. Engine-then-flight bootstrap intervals, per-engine exceptions, and the absence of seed-mean confidence intervals are disclosed rather than suppressed [E010950, E010951, E012043, E012316, E012589, E012536, E012550, E012576].
5. The DS02 exploratory correction comparison and seed-0 epoch-ceiling limitation remain visible [E021498, E021511, E021524, E010738, E010744–E010746].

## Issues that could trigger major revision or rejection

1. **“Unsupervised” may be read too broadly.** Oracle health labels select healthy rows for fitting and threshold calibration, even though labels are never numerical detector features. Methods now says this explicitly; the title and any future cover letter must not imply label-free data selection. This is a terminology and design-scope risk, not a newly discovered leakage event [M0001; Methods III.C].
2. **Confirmation is directional, not uniformly interval-positive.** The DS03 pooled seed-mean rule is met, but all individual LSTM descent-minus-cruise intervals include zero and 3/42 per-engine detector/seed rows are exceptions. A reviewer could reject a broad “confirmed across engines” reading [E013135, E012043, E012316, E012589, E021559–E021560].
3. **Limited engine-level replication.** The engine-then-flight intervals are useful for the observed sets, but the number of top-level engines is small. The study cannot claim precise fleet-population effects; the present text correctly confines scope [M0019, M0031].
4. **The correction challenge is narrow.** The static/derivative/history comparison is DS02 exploratory PCA evidence, not a confirmatory three-detector or DS03 correction factorial. It supports “the tested schemes did not eliminate the observed DS02 dependence,” not a general claim that correction is futile [E021498, E021511, E021524].
5. **The assembled paper has no embedded final figures or tables.** Numbers are traceable in prose and a figure/table plan exists, but visual presentation and caption-level provenance still require completion before submission. This is a manuscript-package gap; no new scientific run is needed.

## Terminology, reproducibility, presentation, and citation checks

- **Terminology:** Use healthy false-positive rate (FPR) for `P(alarm | healthy)` at row level; the Introduction defines the false-alarm-rate synonym once. Keep cross-phase transfer FPR, overall pooled FPR, and exposure-dependent healthy-flight alarm burden separate. “Causal” in the LSTM name means forward-time recurrence, not a causal explanation of phase effects. Avoid calling the model a sequence-level latent autoencoder.
- **Reproducibility:** The manuscript names engine splits, training/validation/calibration separation, primary phase rule, correction, thresholds, and hierarchical bootstrap. The full manuscript is mechanically assembled by `scripts/build_full_manuscript.ps1`; the evidence comments are preserved in the internal copy. The source section files still retain some older wording, so future editing should regenerate and inspect both assembled versions rather than publish a source fragment unchanged. The 600-epoch seed-0 limitation must remain next to LSTM interpretation.
- **Presentation:** Figure/Table plan below is not yet executed. A table should explicitly label seed means versus individual-seed intervals. Heatmap colorbars must identify off-diagonal transfer FPR and avoid an apparent contradiction with the pooled phase-FPR plot. Flight-level alarm burden belongs in supplement or clearly secondary display.
- **Citations:** The 12 references resolve to original publisher or author sources. [4] concerns rotorcraft HUMS, [10] is a preprint, [11] uses a different conditional definition of false-alert probability, and [12] is conceptual warning-system literature. None should be cited as direct evidence of N-CMAPSS phase-FPR results. A duplicate [7] citation was removed, and the [9] sentence was narrowed to verifiable ROC-AUC/F1-style detection metrics; see `reference_audit.md`.

## Ten likely reviewer questions

1. What precise role did oracle health labels play in fitting, calibration, and evaluation if the title says “unsupervised”?
2. Which engines and flights form the independent units, and how many top-level engines actually contribute to each audit?
3. Why is the pooled 1% threshold not expected to yield 1% within each phase or even exactly 1% on the held-out subset?
4. Are the reported stochastic-detector intervals attached to individual seeds or to the arithmetic seed mean?
5. What rule was frozen before DS03 official-test access, and which DS03 development data were still legitimately used for fitting/calibration?
6. Why do all DS03 LSTM descent-minus-cruise intervals cross zero if the pooled directional rule is said to reproduce?
7. How are the three DS03 directional exceptions distributed across engines and seeds?
8. Could differing phase duration, transition samples, or engine composition explain part of the row-FPR contrast without implying a physical mechanism?
9. What is the distinction between the 27.281% DS02 Isolation Forest transfer maximum and its 2.487% pooled-threshold descent FPR?
10. Does the DS02 seed-0 LSTM run reaching 600 epochs while validation loss declined affect how broadly the LSTM evidence can be interpreted?

## High-risk claim table

| Manuscript wording or risk | Evidence | Reviewer judgment / weakening |
| --- | --- | --- |
| “The pre-specified pooled directional pattern was reproduced.” | E010950, E010951, E012861, E012862, E013134, E013135 | Keep exactly this point-estimate wording; attach exceptions and zero-crossing LSTM intervals. Never say all engines confirmed. |
| “Observed across three tested detector implementations.” | E000109, E002629, E002989; DS03 E010949, E012860, E013133 | Keep “tested” and acknowledge shared preprocessing/calibration. No detector-independence inference. |
| “The tested correction schemes did not eliminate the observed dependence.” | E021498, E021499, E021511, E021512, E021524, E021525 | Keep DS02 exploratory PCA qualifier. No mechanism, hysteresis, or exhaustive-correction inference. |
| “Healthy row-level FPR is phase dependent.” | DS02 E000107–E000111, E002627–E002631, E002987–E002991; DS03 E010947–E010951, E012858–E012862, E013131–E013135 | Keep conditional descriptive interpretation. Do not treat timestamps as independent inferential units. |
| “Thresholds did not transfer uniformly.” | E000113, E002633, E002993, E010952, E012863, E013136 | Keep maximum off-diagonal qualification. Do not recast maxima as pooled or projected operational FPR. |
| “Unsupervised anomaly detection.” | Methods III.C; M0001 and fitting/calibration protocol | Needs explicit disclosure that oracle labels select healthy rows. The assembled Introduction, Methods, and Discussion now state this. The title remains a reviewer-sensitive shorthand. |
| “DS03 independent confirmatory subset.” | M0025–M0027, M0033–M0034 | Keep “subset of N-CMAPSS” clear. Do not imply external real-aircraft validation or unused DS03 development data. |

## Prose tightening audit

The assembled manuscript removes one repeated [7] citation and an over-detailed [9] comparator sentence. Results states the phase-FPR and transfer numbers; Discussion interprets the conditional-versus-aggregate relationship without reprinting those numbers. The pooled-versus-conditional explanation necessarily occurs in Introduction, Results, and Discussion but serves different functions (motivation, observation, interpretation); it can be shortened further at copy-editing. The retrospective-label/simulation/small-engine limitations recur in Methods, Discussion, and Conclusion, appropriately in progressively briefer form. Longest remaining sentences are the Methods split and correction definitions; a final typesetting pass can split them without touching scientific content. Avoid repetitive lead-ins such as “These results show” when adding captions or tables.

## Readiness

**NOT READY** — the evidence audit found no numeric contradiction in the assembled text, but the missing integrated main figures/tables and the reviewer-sensitive “unsupervised” label-selection distinction require a final manuscript-package revision before submission. This rating concerns manuscript integrity and presentation only; it does not call for a new scientific experiment.
