# Authoritative quantitative sources

Only these sources are approved for manuscript numbers:

1. `paper/manuscript_core_results.csv` — preselected main-manuscript endpoints, each with an evidence ID and original source row.
2. `paper/evidence_ledger.csv` — executed-result evidence and provenance. Its DS02 correction-comparison entries are exploratory only.
3. DS02 final-validation canonical outputs: `results/final_validation/canonical_results.csv`, `executed_row_false_alarm_rates.csv`, `executed_threshold_transfer_matrix.csv`, `executed_flight_alarm_detail.csv`, `per_engine_phase_fpr.csv`, and `lstm_training_history.csv`.
4. DS02 hierarchical-bootstrap output: `results/final_validation/hierarchical_bootstrap_ci.csv`.
5. DS03 confirmation canonical outputs: `results/confirmation_ds03/canonical_results.csv`, `row_false_alarm_rates.csv`, `threshold_transfer_matrix.csv`, `flight_alarm_detail.csv`, `flight_alarm_summary.csv`, and `lstm_training_history.csv`.
6. DS03 confirmation bootstrap output: `results/confirmation_ds03/hierarchical_bootstrap_ci.csv`.
7. The immutable decision specification: `results/final_validation/frozen_protocol.md`. This is a protocol source, not a result table. Its pre-confirmation status paragraph is historical; the executed DS03 marker and canonical outputs document the later one-shot run.

`results/phase3_dynamic_correction/correction_comparison.csv` and its component executed CSVs are preserved as **DS02 exploratory provenance only**; manuscript claims must pass through `paper/evidence_ledger.csv`. Legacy `results/phase3_cross_detector/` CSVs are superseded by final validation and must not be used for manuscript numbers. The three narrative reports in `archive/obsolete_reports/` contain expected or superseded Phase 3 values and **must never be used for numeric claims**. Pilot and second-stage narrative reports are historical screening material, not main-manuscript quantitative sources.

Paper-generation scripts may read only the ledger and core-results CSV, except the existing evidence-ledger builder, which reconciles executed source CSVs. Generated tables and figures carry source CSV, evidence IDs, and generator provenance. No raw N-CMAPSS data are required for manuscript generation.
