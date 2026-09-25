# Experiment and evidence timeline

Dates below are as recorded in repository history or frozen artifacts; no more precise experiment timestamps are inferred.

| Stage | Record | Status |
| --- | --- | --- |
| DS02 exploratory discovery | `src/pca_pilot.py`, `archive/historical_reports/EXPERIMENT_REPORT.md` | Historical screening; not an approved manuscript numeric source. |
| Operating-condition correction robustness | `src/phase3_dynamic.py`, `results/phase3_dynamic_correction/` | Executed DS02 exploratory comparison; ledger-reconciled entries only. |
| Cross-detector validation | `src/phase3_cross_detector.py`, historical outputs | Superseded by final-validation detector runs. |
| Final-validation cleanup | `src/final_validation.py`, `results/final_validation/` | Canonical DS02 discovery outputs, converged/final LSTM, hierarchical uncertainty. Seed 0 reached the 600-epoch ceiling while validation loss was improving. |
| Protocol freeze | `results/final_validation/frozen_protocol.md`, dated 2026-09-25 | Frozen before non-DS02 outcome access; retain file unchanged. |
| One-shot DS03 confirmation | `results/confirmation_ds03/official_test_opened.json`, `calibration_lock.json`, canonical and bootstrap CSVs | Executed after protocol freeze; DS03 was a held-out confirmatory subset. |
| Manuscript evidence freeze | `paper/evidence_ledger.csv`, `paper/manuscript_core_results.csv`, `paper/claim_audit.md` | Main manuscript numbers are ledger-traceable. |

Available repository commits: `8c39713` (first recorded commit, 2026-09-25) and `2d3ec9f` (confirmation provenance and result-claim check, 2026-09-25). These hashes document repository state, not separate experiment completion timestamps. The present cleanup is uncommitted and no release tag has been created.
