## IV. Results

### A. Discovery of Phase-Dependent Healthy False Alarms on DS02

At the primary 1% pooled-calibration target, PCA healthy row-level FPR was 0.125% in climb, 0.428% in cruise, and 3.459% in descent. The descent-minus-climb and descent-minus-cruise contrasts were +3.335 and +3.031 percentage points (pp), respectively. <!-- evidence: E000107, E000108, E000109, E000110, E000111 -->

The corresponding Isolation Forest seed-mean FPRs were 0.268%, 0.558%, and 2.487%, with contrasts of +2.219 and +1.928 pp. For the causal LSTM sequence-reconstruction network, the seed-mean FPRs were 0.488%, 0.729%, and 2.080%, with contrasts of +1.592 and +1.351 pp. Descent therefore had the highest pooled healthy FPR across the three tested implementations. These pooled results do not imply uniform direction in every engine. <!-- evidence: E002627, E002628, E002629, E002630, E002631, E002987, E002988, E002989, E002990, E002991 -->

### B. Sensitivity to Operating-Condition Correction

In the executed DS02 exploratory PCA comparison, the static correction yielded climb, cruise, and descent FPRs of 0.146%, 0.583%, and 3.001%. The static-plus-derivative correction yielded 0.061%, 0.457%, and 3.106%, whereas finite-history correction yielded 0.125%, 0.428%, and 3.459%. All values used the primary phase rule and nominal 1% calibration target. <!-- evidence: E021489, E021490, E021491, E021502, E021503, E021504, E021515, E021516, E021517 -->

Descent-minus-climb contrasts were +2.854, +3.045, and +3.335 pp for static, static-plus-derivative, and finite-history correction, respectively; descent-minus-cruise contrasts were +2.418, +2.648, and +3.031 pp in the same order. None of these corrections eliminated the observed DS02 phase dependence. This correction comparison was exploratory and was not independently repeated on DS03. <!-- evidence: E021498, E021499, E021511, E021512, E021524, E021525 -->

### C. Cross-Detector Replication

With the common history correction and pooled calibration, DS02 overall healthy row-FPRs were 1.363% for PCA, 1.127% for the Isolation Forest seed mean, and 1.118% for the LSTM seed mean. The descent elevation was observed across three tested detector implementations under this shared preprocessing and calibration protocol. The comparison is limited to those implementations. <!-- evidence: E000106, E002626, E002986, E000109, E002629, E002989 -->

The Isolation Forest descent-minus-climb contrast spanned +2.050 to +2.416 pp across the tested seeds; the LSTM contrast spanned +1.521 to +1.628 pp. These ranges describe all tested seeds, not uncertainty intervals for their means. The DS02 LSTM seed-0 run reached the pre-specified 600-epoch ceiling while its validation loss was still improving over the final monitored windows; it was not classified as converged. <!-- evidence: E000470, E000830, E001190, E001550, E001910, E002270, E010738, E010740, E010744, E010745, E010746 -->

### D. Cross-Phase Threshold Transfer

On DS02, the worst off-diagonal healthy row-FPR after phase-specific calibration was 15.555% for PCA; the arithmetic means of the per-seed maxima were 27.281% for Isolation Forest and 5.954% for LSTM. The corresponding DS03 values were 6.716%, 9.386%, and 5.308%. Each per-run maximum is over cross-phase transfer cells, not a phase FPR obtained with the pooled calibration threshold. The transfer values show that phase-calibrated thresholds did not perform uniformly across healthy phases. <!-- evidence: E000113, E002633, E002993, E010952, E012863, E013136 -->

As secondary descriptive endpoints, the fraction of healthy flights with at least one descent alarm was 98.684%, 86.404%, and 100.000% for PCA, Isolation Forest, and LSTM on DS02, compared with 99.324%, 99.324%, and 99.775% on DS03. Mean contiguous descent alarm events per healthy flight were 16.026, 9.013, and 9.053 on DS02 and 30.662, 21.775, and 24.626 on DS03, in the same detector order. These flight-level summaries depend on phase duration and exposure and are not substitutes for row-level FPR or directional contrasts. <!-- evidence: E000119, E002639, E002999, E010957, E012868, E013141, E000120, E002640, E003000, E010958, E012869, E013142 -->

### E. Cluster-Aware Uncertainty and Heterogeneity

For DS02 PCA, hierarchical-bootstrap 95% intervals were [+2.070, +5.629] pp for descent-minus-climb and [+1.808, +5.261] pp for descent-minus-cruise. All tested Isolation Forest seeds had positive intervals for both contrasts. By contrast, the DS02 LSTM descent-minus-climb intervals for seeds 1 and 2 included zero: [−0.022, +2.817] and [−0.347, +2.802] pp. At the engine level, DS02 engine 14 had negative LSTM descent-minus-climb contrasts for seeds 1 and 2 (−0.158 and −0.521 pp), despite the positive pooled seed-mean contrast. <!-- evidence: E000110, E000111, E000470, E000471, E000830, E000831, E001190, E001191, E001910, E002270, E001880, E002240, E002990 -->

On DS03, the PCA intervals were [+0.434, +1.785] pp for descent-minus-climb and [+0.560, +1.573] pp for descent-minus-cruise. Each Isolation Forest seed had a positive interval for both contrasts. The LSTM descent-minus-climb intervals were positive for all seeds, but every LSTM descent-minus-cruise interval included zero. The engine-then-flight bootstrap accounts for clustering and recalibrates thresholds within replicates; with limited engines, these intervals summarize uncertainty for the observed N-CMAPSS engine sets rather than precise population-level effects. No timestamp-level p-values were used. <!-- evidence: E010950, E010951, E011223, E011224, E011496, E011497, E011769, E011770, E012042, E012043, E012315, E012316, E012588, E012589 -->

### F. Frozen DS03 Confirmation

DS03 was evaluated as an independent confirmatory subset after the analysis protocol was frozen and was not used for method development. At the pre-specified primary target, pooled PCA climb, cruise, and descent FPRs were 0.877%, 0.912%, and 1.977%; the corresponding Isolation Forest seed means were 0.409%, 1.104%, and 2.142%; and LSTM seed means were 0.751%, 1.889%, and 2.215%. <!-- evidence: E010947, E010948, E010949, E012858, E012859, E012860, E013131, E013132, E013133 -->

The pooled descent-minus-climb and descent-minus-cruise contrasts were +1.100 and +1.066 pp for PCA, +1.733 and +1.038 pp for the Isolation Forest seed mean, and +1.464 and +0.325 pp for the LSTM seed mean. Thus, the pre-specified pooled directional pattern was reproduced. These are point-estimate seed means for the stochastic detectors, not estimates with bootstrap intervals for the means. <!-- evidence: E010950, E010951, E012861, E012862, E013134, E013135 -->

Three of 42 per-engine detector/seed rows were directional exceptions, all for LSTM seed 2: engine 12 had a descent-minus-climb contrast of −0.086 pp, and engines 13 and 15 had descent-minus-cruise contrasts of −0.105 and −0.034 pp. In addition, the LSTM descent-minus-cruise 95% intervals included zero for seeds 0, 1, and 2: [−0.222, +1.201], [−0.270, +1.158], and [−0.582, +1.025] pp. The pooled pattern therefore reproduced without uniform engine-level replication or a positive interval for every individual LSTM contrast. <!-- evidence: E021559, E021560, E012536, E012550, E012576, E012043, E012316, E012589 -->
