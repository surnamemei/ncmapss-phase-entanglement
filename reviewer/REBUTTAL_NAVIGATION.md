# Rebuttal navigation — ncmapss-phase-entanglement (MSSP extended manuscript)

Use this sheet first when reviewer comments arrive. Claim IDs (C…) are in `CLAIMS_INDEX.md`; question IDs (Q…) are in
`LIKELY_REVIEWER_QUESTIONS.md`; issue IDs (I-…) are in `ISSUE_BANK.md`. Paths are relative to the repository root.

**Before answering anything, run these read-only checks, which take seconds:**

```bash
.venv/bin/python -B paper/mssp_extended/verify_numbers.py
```
```bash
sha256sum -c docs/release/v1.1.0/PUBLIC_RELEASE_MANIFEST.sha256 | grep -v ': OK$'
```

The canonical text is `paper/mssp_extended/manuscript_mssp_draft.md`. Edit only that file, then regenerate the LaTeX with
`build_latex.py`. The verifier enforces a forbidden-word list, including "robust", "significant", "novel framework" and
"preregistered".

| Topic | First file | Second file | Claim IDs | Fig./Table IDs | Result artifacts | New compute likely? |
|---|---|---|---|---|---|---|
| Novelty / prior art | `paper/mssp_extended/NOVELTY_POSITIONING.md` | `docs/extension/PRIOR_ART_EXTENSION.md`; `paper/mssp_extended/literature_evidence/` | C040 | — | `reference_audit.csv` | No |
| Research question / RQ1–RQ5 | `manuscript_mssp_draft.md` §1 (p. 2) | `docs/extension/EXTENSION_CHARTER.md` | C007–C027 | Table 4 | `summary/decisions.json` | No |
| Dataset / cohort / DS08d | `docs/extension/SUBSET_SELECTION_LOCK.md` | `docs/extension/subset_metadata_audit.json` | C005, C006 | Table 1, S1 | `docs/extension/subset_engine_metadata.csv` | No |
| Engine roles / splits / leakage | `src/ext_common.py:allocate` | `docs/extension/OUTCOME_ACCESS_LOG.md`; `tests/test_leakage_guards.py` | C005 | Table 1, S2 | `*/lock/calibration_lock.json` (`roles`) | No |
| Protocol, freeze, amendments | `docs/extension/GENERALIZATION_PROTOCOL.md` | `docs/extension/AMENDMENTS.md`, `FREEZE_RECORD.md` | C029, C039 | Table 4 | `decisions.json` | No |
| Preprocessing / history correction / phases | `src/phase3_dynamic.py` | `src/confirm_frozen_ds03.py:primary_phase` | C001, C002 | — | `*/models/correction.pkl` (local) | No |
| Detectors (PCA, IF, LSTM) | `src/ext_models.py` | `src/final_validation.py:LSTMAutoencoder`; `configs/ds03_confirmation.yaml` | C018 | S3, S4 | `*/lock/training_history.csv` | No (retraining = EXPENSIVE) |
| CVAE | `docs/extension/CVAE_SPECIFICATION.md` | `src/ext_cvae.py`; Amendment 2 | C018–C020 | Fig. 5; S3 | locks `cvae_variance_bound_share` | Only if a second model is demanded (I-08) |
| Calibration arms P/C/Q | `src/ext_calibration.py` | Protocol §5; `src/ext_qfit.py` | C011–C017 | Table 3; Fig. 3 | `*/audit/paired_transport*.csv` | Only for new arms (I-07) |
| Statistics / decision rules | Protocol §11–13 | `src/ext_summary.py` | C007, C011, C013, C018, C021, C025 | Table 4 | `decisions.json` | No |
| Confidence intervals / bootstrap | `src/ext_endpoints.py:bootstrap_uext1` | `src/ext_summary.py:uext2`, `composition_bootstrap` | C019, C022, C028, C031 | S8, S9, S12, S23, S24 | `summary/uext2_cross_dataset.csv`, `composition_bootstrap.csv` | No |
| Sampling noise / null references | `paper/mssp_extended/post_hoc_checks.py` | `docs/extension/EXTENSION_HOSTILE_REVIEW.md` §3 | C026, C033 | Figs. 3, 6a; S18, S19 | `evidence/post_hoc_checks.json`, `post_hoc_engine_noise.csv` | No |
| Self-calibration reference / local recalibration | `docs/extension/FOCUSED_VALIDATION_PLAN.md` | `src/ext_focused_validation.py`; `FOCUSED_VALIDATION_REPORT.md` | C030–C032 | S21–S24 | `results/extension/focused_validation/summary/*` | Only for k ≠ 5 (I-09) |
| Baselines | Protocol §4–5 | `manuscript_mssp_draft.md` §3.4–3.5 | C012, C018, C032 | Table 3; Fig. 5 | — | Possibly (I-07, I-08, I-09) |
| Composition / coverage | Protocol §7 | `src/ext_calibration.py:build_designs`; `src/ext_summary.py:composition_analysis` | C021–C024, C035 | Fig. 4; Table 5; S11–S13 | `summary/composition_*.csv` | Cheap stratification only (I-04) |
| Persistence / flight rule | Protocol §5, §8 | `src/ext_calibration.py:apply_rule`, `kappa` | C025, C026, C037 | Fig. 6a; S14, S20 | `summary/we_ffr.csv`, `*/audit/flight_false_flags.csv` | Cheap k-of-n (I-10) |
| Matched-burden delay | Protocol §9 | `src/ext_endpoints.py:matched_tables`; `docs/mssp/adversarial_validation_plan.md` | C027, C038 | Fig. 6b; S15, S16 | `summary/matched_labels_alpha_0.01.csv` | Cheap per-engine matching (I-11) |
| Robustness (targets, rules) | Supplement Table S10 | `*/audit/transport_summary.csv` | C007 | S10 | — | No |
| Ablations | (none in the ML sense) Composition = design ablation | Protocol §7 | C021 | Fig. 4 | — | — |
| Largest failures / mechanisms | `evidence/post_hoc_checks.json["ds08a_engine14"]` | `results/extension/metadata/healthy_flight_phase_segments.csv` | C017 | Fig. 3 | `DS08a/audit/paired_transport_engines.csv` | No |
| Limitations | `manuscript_mssp_draft.md` §5.5 (p. 16) | `reviewer/ASSUMPTIONS_AND_LIMITATIONS.md` | — | — | — | No |
| Reproducibility | `README.md` "Verifying the release" | `PROJECT_STATE.md` | C039 | — | `docs/release/v1.1.0/*`, `docs/mssp/frozen_baseline.sha256` | No |
| Frozen DS02/DS03 values | `paper/manuscript_core_results.csv` | `paper/mssp/verify_draft_numbers.py`; `results/{final_validation,confirmation_ds03}/` | C001–C003 | Part B | `canonical_results.csv` | No |
| AI-tool use | `manuscript_mssp_draft.md` §3.11 and AI declaration | `docs/extension/EXTENSION_HOSTILE_REVIEW.md` | — | — | — | Independent reimplementation only if demanded (I-18) |
| Fig. 1 | `build_figures_tables.py:fig1_design` | `SUBSET_SELECTION_LOCK.md` | C005, C006 | Fig. 1 | — | No |
| Fig. 2 | `build_figures_tables.py:fig2_pooled_phase_fpr` | `*/audit/transport_summary.csv` | C007–C010 | Fig. 2 | — | No |
| Fig. 3 | `build_figures_tables.py:fig3_engine_transport` | `evidence/post_hoc_engine_noise.csv` | C013–C017, C033 | Fig. 3 | `*/audit/paired_transport_engines.csv` | No |
| Fig. 4 | `build_figures_tables.py:fig4_composition` | `summary/composition_engine_effects.csv` | C021–C023 | Fig. 4 | — | No |
| Fig. 5 | `build_figures_tables.py:fig5_cvae` (log y-axis) | `*/audit/transport_summary.csv` | C018–C019 | Fig. 5 | — | No |
| Fig. 6 | `build_figures_tables.py:fig6_persistence_delay` | `summary/matched_labels_alpha_0.01.csv` | C025–C027 | Fig. 6 | — | No |
| Tables 1–5 | `build_figures_tables.py:table{1..5}_*` | `paper/mssp_extended/tables/*.provenance.json` | see FIGURE_TABLE_MAP | Tables 1–5 | — | No |
| Supplement S1–S24 | `paper/mssp_extended/build_supplement.py` | `supplement.provenance.json` (97 inputs) | — | S1–S24 | — | No |
| Implementation details / environment | `docs/ENVIRONMENT.md` | `requirements-lock.txt`; `AGENTS.md` (GPU must fail, not fall back) | — | — | — | — |

## Quick answers that are safe to give

- **"Are the numbers right?"** Yes. `verify_numbers.py` re-derives all 78 displayed claims from committed outputs. This audit
  independently re-read or re-aggregated 14 headline items from the committed CSV/JSON (items marked R in
  `RESULT_PROVENANCE.md`).
- **"Was the test set touched more than once?"** Each extension audit ran once (one-shot markers, access log). The focused
  validation re-read healthy test rows once, under a separately frozen plan, after all outcomes. It is labelled post hoc and
  changed no decision.
- **"Are thresholds tuned on test data?"** No. Locks were committed before any official-test read (`*/lock/`,
  `FREEZE_RECORD.md`).

## Answers that need care

- Anything implying significance: there are no p-values by design.
- Anything about real fleets: out of scope.
- Anything claiming coverage "causes" transport, or that the CVAE result generalizes: this is overclaiming (see
  `ASSUMPTIONS_AND_LIMITATIONS.md` F).
