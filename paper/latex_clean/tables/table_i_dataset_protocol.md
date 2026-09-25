**Table I. Dataset and frozen protocol summary.** DS02 is exploratory discovery; DS03 is an independent confirmatory N-CMAPSS subset under the frozen one-shot protocol. This design table contains no pooled phase-FPR or cross-phase transfer-FPR outcomes; seed means are not applicable.

| Item | DS02 discovery (exploratory) | DS03 independent confirmatory subset |
| --- | --- | --- |
| Role | Discovery, correction sensitivity, detector development | Frozen one-shot confirmation |
| Model-fitting engines | 2, 5, 10, 16 | 1, 2, 3, 5, 6, 7, 9 |
| LSTM epoch-selection fitting engines | 2, 5, 10 | 1, 2, 3, 5, 6, 7 |
| LSTM epoch-selection validation engine | 16 | 9 |
| Threshold-calibration engines | 18, 20 | 4, 8 |
| Official audit/test engines | 11, 14, 15 | 10, 11, 12, 13, 14, 15 |
| Phase-label role | Retrospective full-flight stratification; cruise spans the first through last sample at or above the minimum plus 90% of each flight's observed altitude range | Same frozen retrospective primary rule |
| Nominal pooled healthy row-FPR targets | 0.5%, 1%, 2%; 1% primary | Same frozen targets and primary target |
| Detector implementations | PCA; Isolation Forest; causal LSTM sequence reconstruction | Same frozen implementations |
| Operating-condition correction | Static, static + derivative, and finite-history compared for PCA exploratorily; finite-history used for canonical detector results | Finite-history only; no DS03 correction-variant selection |

Health-state annotations select healthy rows for retrospective fitting, calibration, and FPR evaluation; they are not detector features. Phase labels are retrospective strata, not an online phase detector.

<!-- evidence: M0020, M0021, M0022, M0023, M0024, M0025, M0026, M0027, M0028, M0029, M0002, M0018, M0033, M0034, E021498, E021511, E021524; sources: paper/evidence_ledger.csv, results/final_validation/frozen_protocol.md; generation_script: scripts/build_submission_package.py -->
