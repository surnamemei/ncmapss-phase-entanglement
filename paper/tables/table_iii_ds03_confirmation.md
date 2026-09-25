**Table III. Frozen DS03 confirmatory pooled results at the nominal 1% pooled healthy calibration target.** Climb/cruise/descent columns are pooled-threshold phase FPRs, not cross-phase transfer FPRs. Isolation Forest and LSTM point estimates are arithmetic seed means; the 95% hierarchical-bootstrap contrast intervals apply only to individual detector runs, so no interval is assigned to a seed mean.

| Detector | Climb FPR (%) | Cruise FPR (%) | Descent FPR (%) | Descent − climb (pp) | Run-level 95% CI (pp) | Descent − cruise (pp) | Run-level 95% CI (pp) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PCA | 0.877% | 0.912% | 1.977% | +1.100 pp | [+0.434 pp, +1.785 pp] | +1.066 pp | [+0.560 pp, +1.573 pp] |
| Isolation Forest (seed mean) | 0.409% | 1.104% | 2.142% | +1.733 pp | — | +1.038 pp | — |
| Causal LSTM reconstruction (seed mean) | 0.751% | 1.889% | 2.215% | +1.464 pp | — | +0.325 pp | — |

*Note:* 3/42 per-engine detector/seed directional rows were exceptions, all from LSTM seed 2. All three individual LSTM descent-minus-cruise bootstrap intervals include zero. Individual-seed interval tables belong in the supplement; an arithmetic seed-mean interval was not executed. Cross-phase transfer FPR is not tabulated here.

<!-- evidence: M0031, E010947, E010948, E010949, E010950, E010951, E012858, E012859, E012860, E012861, E012862, E013131, E013132, E013133, E013134, E013135, E021559, E021560, E012536, E012550, E012576, E012043, E012316, E012589; sources: results/confirmation_ds03/canonical_results.csv, results/confirmation_ds03/hierarchical_bootstrap_ci.csv, paper/evidence_ledger.csv; generation_script: scripts/build_submission_package.py -->
