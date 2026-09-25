# Numerical and evidential-status consistency audit

Checked 2026-09-25 against `paper/manuscript_core_results.csv`, then its evidence IDs and original-source rows in `paper/evidence_ledger.csv`. The assembled manuscript copies the source sections; no scientific computation or new experiment was performed. All percentages below are **healthy row-level FPR under the nominal 1% pooled-calibration threshold**, except the explicitly labelled transfer and flight-level rows. An arithmetic seed mean has no bootstrap interval for the mean.

## Primary pooled phase-FPR values

| Dataset/status | Detector | Climb | Cruise | Descent | Ledger evidence IDs |
| --- | --- | ---: | ---: | ---: | --- |
| DS02 exploratory | PCA | 0.125% | 0.428% | 3.459% | E000107–E000109 |
| DS02 exploratory | Isolation Forest, three-seed arithmetic mean | 0.268% | 0.558% | 2.487% | E002627–E002629 |
| DS02 exploratory | LSTM, three-seed arithmetic mean | 0.488% | 0.729% | 2.080% | E002987–E002989 |
| DS03 frozen confirmation | PCA | 0.877% | 0.912% | 1.977% | E010947–E010949 |
| DS03 frozen confirmation | Isolation Forest, three-seed arithmetic mean | 0.409% | 1.104% | 2.142% | E012858–E012860 |
| DS03 frozen confirmation | LSTM, three-seed arithmetic mean | 0.751% | 1.889% | 2.215% | E013131–E013133 |

All 18 displayed values agree between Abstract, Results, core-results CSV, and ledger. They are not cross-phase transfer FPRs. The nominal 1% is a calibration target, not an audit-phase guarantee [M0018].

## Other Results numbers

| Claim group in Results | Verified displayed values | Evidence IDs and qualification |
| --- | --- | --- |
| DS02 descent minus climb / cruise (pp) | PCA +3.335 / +3.031; Isolation Forest mean +2.219 / +1.928; LSTM mean +1.592 / +1.351 | E000110–E000111; E002630–E002631; E002990–E002991. Seed means are point estimates. |
| DS03 descent minus climb / cruise (pp) | PCA +1.100 / +1.066; Isolation Forest mean +1.733 / +1.038; LSTM mean +1.464 / +0.325 | E010950–E010951; E012861–E012862; E013134–E013135. This is the frozen pooled directional rule, not a uniform-engine claim. |
| DS02 PCA static correction: climb/cruise/descent FPR and contrasts | 0.146% / 0.583% / 3.001%; +2.854 / +2.418 pp | E021489–E021491, E021498–E021499. Exploratory only. |
| DS02 PCA static-plus-derivative correction | 0.061% / 0.457% / 3.106%; +3.045 / +2.648 pp | E021502–E021504, E021511–E021512. Exploratory only. |
| DS02 PCA finite-history correction | 0.125% / 0.428% / 3.459%; +3.335 / +3.031 pp | E021515–E021517, E021524–E021525. Exploratory only; agrees with final-validation PCA primary history result. |
| Overall pooled audit FPR, DS02 | PCA 1.363%; Isolation Forest mean 1.127%; LSTM mean 1.118% | E000106, E002626, E002986. Distinct from the 1% calibration target. |
| DS02 seed ranges for descent-minus-climb | Isolation Forest +2.050 to +2.416 pp; LSTM +1.521 to +1.628 pp | E000470, E000830, E001190; E001550, E001910, E002270. Ranges over tested seeds, not confidence intervals. |
| Worst off-diagonal **cross-phase transfer** FPR, DS02 | PCA 15.555%; Isolation Forest mean of seed maxima 27.281%; LSTM mean of seed maxima 5.954% | E000113, E002633, E002993. Climb-calibrated threshold applied to descent is the maximizing cell for each run [E004822, E005686, E006550, E007414, E008278, E009142, E010006]. |
| Worst off-diagonal **cross-phase transfer** FPR, DS03 | PCA 6.716%; Isolation Forest mean of seed maxima 9.386%; LSTM mean of seed maxima 5.308% | E010952, E012863, E013136. Climb-to-descent maximum cells [E014791, E015547, E016303, E017059, E017815, E018571, E019327]. These are **not** the pooled-threshold descent FPRs above. |
| Secondary fraction of healthy flights with ≥1 descent alarm, DS02 / DS03 | DS02 PCA/IF/LSTM 98.684% / 86.404% / 100.000%; DS03 99.324% / 99.324% / 99.775% | E000119, E002639, E002999; E010957, E012868, E013141. Exposure-dependent descriptive endpoints. |
| Secondary mean contiguous descent-alarm events per healthy flight, DS02 / DS03 | DS02 PCA/IF/LSTM 16.026 / 9.013 / 9.053; DS03 30.662 / 21.775 / 24.626 events/flight | E000120, E002640, E003000; E010958, E012869, E013142. Not row FPRs or operator outcomes. |
| DS02 PCA 95% intervals, descent-minus-climb / cruise | [+2.070, +5.629] / [+1.808, +5.261] pp | E000110–E000111, hierarchical engine-then-flight bootstrap. |
| DS02 LSTM seeds 1 and 2, descent-minus-climb 95% intervals | [−0.022, +2.817] / [−0.347, +2.802] pp | E001910, E002270. Both include zero. All DS02 IF seed intervals for both contrasts have positive lower limits [E000470–E000471, E000830–E000831, E001190–E001191]. |
| DS02 LSTM engine 14 seed exceptions | Seed 1 −0.158 pp; seed 2 −0.521 pp, descent-minus-climb | E001880, E002240. Per-engine values; not pooled seed means. |
| DS03 PCA 95% intervals, descent-minus-climb / cruise | [+0.434, +1.785] / [+0.560, +1.573] pp | E010950–E010951. All DS03 IF individual-seed contrast intervals have positive lower limits [E011223–E011224, E011496–E011497, E011769–E011770]. |
| DS03 LSTM descent-minus-cruise 95% intervals by seed | Seed 0 [−0.222, +1.201]; seed 1 [−0.270, +1.158]; seed 2 [−0.582, +1.025] pp | E012043, E012316, E012589. All include zero; there is no interval for the arithmetic seed mean. |
| DS03 directional exceptions | 3 of 42 per-engine detector/seed rows; seed-2 LSTM engine 12 descent-minus-climb −0.086 pp, engines 13/15 descent-minus-cruise −0.105/−0.034 pp | E021559–E021560, E012536, E012550, E012576. Does not negate the pre-specified pooled point-estimate rule. |
| DS02 LSTM seed-0 epoch ceiling | Selected epoch 600 of maximum 600; validation-loss slopes over final 20/50/100 epochs remain negative | E010738, E010740, E010744–E010746. Not described as converged or as evidence about test-performance trend. |

The Abstract contains the primary 1% target and the 18 phase-FPR figures above; its other statements are qualitative and retain the LSTM interval caveat. The Discussion repeats only 3/42 and 600 as quantitative counts, with the same evidence IDs. The Conclusion contains no numerical effect estimate. There are no timestamp-level p-values or unsupported statistical-significance claims in the assembled text.

## Status and scope checks

- DS02 correction comparison, detector development, and phase-stratified discovery remain explicitly **exploratory**. The ledger's executed Phase 3A correction rows are used only through the ledger; obsolete Phase 3 narratives are absent.
- DS03 is described as a **frozen one-shot independent confirmatory subset of N-CMAPSS**, not external real-world validation. Its development partition supplied fitting/calibration under frozen rules; official-test arrays were accessed after those choices were locked [M0025, M0026, M0034].
- Healthy row FPR is descriptive at row resolution. Engines are the top-level inferential units; the bootstrap resamples engines and then flights, with thresholds recalibrated within replicates. Intervals summarize uncertainty for the observed engine sets, not precise population effects [M0019, M0031].
- The manuscript retains all three DS03 LSTM descent-minus-cruise intervals that include zero, the 3/42 exceptions, and the DS02 seed-0 600-epoch limitation. It does not claim fault recall, causal mechanism, real-aircraft validity, or independence among detectors.
- Search of both assembled versions found no old “25–35% pooled descent FPR” value and no instance in which a 15.555%/27.281%/5.954% or 6.716%/9.386%/5.308% transfer value was called a pooled phase FPR.

## Mechanical validation

`scripts/build_full_manuscript.ps1` completed and rebuilt idempotently. The internal manuscript contains evidence comments; the clean version contains neither those comments nor inline ledger IDs. Every evidence ID in the internal manuscript resolves in the ledger, all 12 numbered literature references are cited, and the Abstract is 216 words. The three read-only `test_paper_pipeline.py` checks passed, including core-to-ledger exact-value resolution and obsolete-source exclusion. Table and figure generators passed dry runs on 188 ledger-derived table rows and 18 plotted primary FPR values; no figure or table was written in this audit. The configured WSL Python could not be invoked in this Windows session (`Wsl/Service/CreateInstance/E_ACCESSDENIED`), so these standard-library checks used the available Windows Python; no GPU or scientific computation was attempted.
