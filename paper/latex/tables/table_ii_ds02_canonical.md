**Table II. DS02 exploratory canonical results at the nominal 1% pooled healthy calibration target.** Phase FPR columns use the pooled threshold; the final column is the worst off-diagonal cross-phase **transfer** FPR and is not a pooled phase FPR. Isolation Forest and LSTM rows are arithmetic means across the tested seeds, with no seed-mean confidence interval.

| Detector | Overall FPR (%) | Climb FPR (%) | Cruise FPR (%) | Descent FPR (%) | Descent − climb (pp) | Descent − cruise (pp) | Worst cross-phase transfer FPR (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PCA | 1.363% | 0.125% | 0.428% | 3.459% | +3.335 pp | +3.031 pp | 15.555% |
| Isolation Forest (seed mean) | 1.127% | 0.268% | 0.558% | 2.487% | +2.219 pp | +1.928 pp | 27.281% |
| Causal LSTM reconstruction (seed mean) | 1.118% | 0.488% | 0.729% | 2.080% | +1.592 pp | +1.351 pp | 5.954% |

<!-- evidence: E000106, E000107, E000108, E000109, E000110, E000111, E000113, E002626, E002627, E002628, E002629, E002630, E002631, E002633, E002986, E002987, E002988, E002989, E002990, E002991, E002993; sources: results/final_validation/canonical_results.csv; generation_script: scripts/build_submission_package.py -->
