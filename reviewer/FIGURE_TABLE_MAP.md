# Figure and table map — ncmapss-phase-entanglement (MSSP extended manuscript)

**Builders.**
- Main figures and tables: `paper/mssp_extended/build_figures_tables.py` (functions named below). SHA-256 `be4c042e…` matches
  every provenance sidecar.
- Captions: taken from `manuscript_mssp_draft.md` ("## Figures (captions)", "## Tables") by `paper/mssp_extended/build_latex.py`.
- Supplement: `paper/mssp_extended/build_supplement.py`.

**Provenance check (2026-09-29).** Every `*.provenance.json` under `paper/mssp_extended/{figures,tables,supplement}` was
re-hashed: 242 hashes (outputs, inputs, builder), 0 mismatches. PNG content hashes are also in the ledger (EX001669–EX001674),
and table CSV hashes as well (EX001664–EX001668).

**Determinism.**
- The builder refuses to overwrite without `--rebuild`, and every sidecar records `built_utc`.
- The PDF outputs (figures and paper) embed build dates, so they are not byte-reproducible.
- The PNG and CSV outputs should be deterministic with the pinned matplotlib, pandas and NumPy (`requirements-lock.txt`). This
  was not re-run in this audit, because `--rebuild` rewrites tracked files.

**Manual editing.** None is apparent. Figures come straight from matplotlib calls and tables from code-generated `.csv` and
`.tex`, with no hand-edit markers. `main.tex` is generated and `\input`s the table `.tex` files.

## Main figures

| ID | Page | Purpose | Builder function | Inputs (all hash-verified) | Outputs | Caption vs implementation | Stale / duplicate versions |
|---|---|---|---|---|---|---|---|
| Fig. 1 | p. 5 (§3.1) | Staged design and fleet families (schematic) | `fig1_design` | None declared; the counts come "from `docs/extension/SUBSET_SELECTION_LOCK.md`" | `figures/fig1_study_design.{pdf,png}` | Matches (schematic) | `paper/figures/figure_1_study_design.*` (v1.0.0 DS02/DS03 paper) and `paper/mssp/figures/` (pre-extension). Neither is used by this manuscript |
| Fig. 2 | p. 10 (§4.2) | Pooled phase FPR by subset and detector family under P | `fig2_pooled_phase_fpr` | `results/extension/{DS01..DS08c,DS02,DS03}/audit/transport_summary.csv` | `figures/fig2_pooled_phase_fpr.*` | Matches: seed mean point, seed range bar, grey references (sidecar note) | Earlier phase-FPR figures in `paper/figures/figure_2_*`, `figure_4_*` are for the frozen DS02/DS03 study |
| Fig. 3 | p. 11 (§4.3) | Per-engine A2 under P/C/Q; post hoc sampling-reference ticks | `fig3_engine_transport` | `results/extension/*/audit/paired_transport_engines.csv`; `*/lock/calibration_lock.json` (for the "class absent" crosses); `paper/mssp_extended/evidence/post_hoc_engine_noise.csv` (grey ticks) | `figures/fig3_engine_transport.*` | Matches: median/range over 7 residual runs; grey ticks = post hoc 95th percentile (sidecar note) | None |
| Fig. 4 | p. 12 (§4.5) | Composition: (a) per-engine coverage effect; (b) balanced minus mean single engine | `fig4_composition` | `results/extension/summary/composition_engine_effects.csv`, `composition_run_summary.csv` | `figures/fig4_composition.*` | (a) is the median of `delta_cov` over runs per (subset, unit), matching "median over the ten runs"; (b) plots `CE2_balanced_minus_mean_single` per run. Matches | None |
| Fig. 5 | p. 12 (§4.4) | CVAE vs residual detectors: ME-A2 and WE-A2 under P | `fig5_cvae` | `results/extension/*/audit/transport_summary.csv` | `figures/fig5_cvae_vs_residual.*` | Matches. **Log y-axis**, not mentioned in the caption; a reviewer may ask | None |
| Fig. 6 | p. 13 (§4.6) | (a) WE-FFR under R0/R1/R2 with post hoc null bands; (b) matched-burden delay labels | `fig6_persistence_delay` | `results/extension/*/audit/flight_false_flags.csv`; `results/extension/summary/matched_labels_alpha_0.01.csv`; `paper/mssp_extended/evidence/post_hoc_checks.json` | `figures/fig6_persistence_and_delay.*` | Matches (sidecar note) | None |

## Main tables

| ID | Page | Purpose | Builder function | Inputs | Outputs (`paper/mssp_extended/tables/`) | Ledger | Notes |
|---|---|---|---|---|---|---|---|
| Table 1 | p. 6 (§3.3) | Subsets, families, engine roles, flight classes, audited rows, composition volume N | `table1_design` | `results/extension/*/lock/calibration_lock.json`, `*/audit/audit_record.json` | `table1_subsets_roles.{csv,tex}` | EX001664 | Roles are frozen by `src/ext_common.py:allocate` / `FROZEN_ROLES` |
| Table 2 | p. 8 (§3.9 float, cited §4.2) | Pooled calibration: highest-FPR-phase counts, pooled A2 per family, material rule | `table2_pooled` | `*/audit/transport_summary.csv`; `summary/phase_ordering_pooled.csv` | `table2_pooled_calibration.*` | EX001665 | IF, LSTM and CVAE values are seed means |
| Table 3 | p. 8 | C and Q transport: disparity-reduction counts, every-engine-improved, ≥ 1 worse; ME/WE-A2 medians | `table3_transport` | `*/audit/paired_transport.csv`, `*/audit/transport_summary.csv` | `table3_transport.*` | EX001666 | Counts over 10 runs (7 residual + 3 CVAE); ME/WE medians over 7 residual runs |
| Table 4 | p. 9 | Hypotheses H1–H7, decision rules, counts, decisions; S1–S5, M-B and M-C | `table4_decisions` | `summary/decisions.json`, `summary/composition_bootstrap.csv` | `table4_decisions.*` | EX001667 | H7 is a rule, not a test (no verdict in `decisions.json`) |
| Table 5 | p. 13 (§4.5) | Composition: runs with positive coverage effect, coverage and volume effects, balance check | `table5_composition` | `*/lock/calibration_lock.json`; `summary/composition_engine_effects.csv`, `composition_run_summary.csv` | `table5_composition.*` | EX001668 | The volume column is ~0 by construction (§3.8) |

## Supplementary tables (Part A; `paper/mssp_extended/supplement/supplement.pdf`)

All are built by `build_supplement.py` from committed outputs, and `supplement.provenance.json` lists 97 input hashes (all
verified). The numbering was confirmed from the PDF text.

| ID | Content | Primary source files |
|---|---|---|
| S1 | Candidate subsets, metadata-only eligibility C1–C9 | `docs/extension/subset_metadata_audit.csv` |
| S2 | Engine roles | `results/extension/*/lock/calibration_lock.json` (`roles`) |
| S3 | Locks, compute, CVAE float64 check, variance-bound share | `*/lock/calibration_lock.json`; `paper/mssp_extended/evidence/numerical_audit_locks.csv` |
| S4 | LSTM/CVAE epoch selection and refit | `paper/mssp_extended/evidence/numerical_audit_training.csv` (built by `src/ext_numerical_audit.py` from `*/lock/training_history.csv`) |
| S5 | Row-pooled phase FPRs and transport metrics (all subsets, runs, arms) | `*/audit/transport_summary.csv` |
| S6 | Paired C/Q vs P comparisons | `*/audit/paired_transport.csv` |
| S7 | Per-engine A2 (all audit engines) | `*/audit/paired_transport_engines.csv` |
| S8 | U-EXT1 per-subset bootstrap, C − P | `*/audit/bootstrap_uext1_ci.csv` |
| S9 | U-EXT2 cross-dataset bootstrap | `summary/uext2_cross_dataset.csv` |
| S10 | Target sensitivity (0.5/1/2%) | `*/audit/transport_summary.csv` |
| S11 | Composition per run and arm | `summary/composition_run_summary.csv` |
| S12 | Composition bootstrap | `summary/composition_bootstrap.csv` |
| S13 | CE4 engine count vs coverage | `summary/composition_ce4.csv` |
| S14 | Persistence at locked κ | `*/audit/persistence_calibration.csv`, `*/audit/flight_false_flags.csv` |
| S15 | Matched-burden delay labels | `*/audit/matched_labels.csv` |
| S16 | Abnormal-state row alarm rates | `*/audit/abnormal_alarm_rates.csv` |
| S17 | Reference reproduction gates (DS02, DS03) | `results/extension/{DS02,DS03}/audit/audit_record.json` |
| S18 | Post hoc WE-FFR null | `evidence/post_hoc_checks.json` |
| S19 | Post hoc A2 sampling reference | `evidence/post_hoc_checks.json`, `post_hoc_engine_noise.csv` |
| S20 | Post hoc two-flight confirmation | `evidence/post_hoc_checks.json` |
| S21 | Focused validation 1: cross-fitted self-calibration reference | `results/extension/focused_validation/summary/engine_summary.csv` |
| S22 | Focused validation 3: local recalibration (k = 5) | `focused_validation/summary/local_engine_summary.csv` |
| S23 | Focused validation 2: class-preserving bootstrap widths | `focused_validation/summary/bootstrap_width_comparison.csv` |
| S24 | Focused validation 2: U-EXT2 recomputed | `focused_validation/summary/uext2_original_vs_class_preserving.csv` |

- **Order.** S21 is component 1, S22 component 3 and S23–S24 component 2. The order is by table, not by component number, and
  a reviewer could find it confusing.
- **The exact source column for each supplement table** was not traced line by line. Each source file above is one of the 97
  inputs recorded in `supplement.provenance.json` and was matched to its table by caption.
- **Part B** is `paper/mssp/supplement/supplement.pdf`, unchanged (SHA-256 `f1d38a51…96b2a`, per `docs/release/v1.1.0/RELEASE_NOTES.md`).

## Stale, duplicate or superseded manuscript assets in the tree (do not cite)

| Path | What it is | Status |
|---|---|---|
| `paper/mssp/` | Pre-extension MSSP package: `manuscript_mssp_draft.md`, `latex/`, `figures/`, `tables/`, `supplement/` | Superseded. Kept as the source of the frozen DS02/DS03 values and as supplement Part B |
| `paper/ress/`, `paper/output/NCMAPSS_Flight_Phase_RESS_Final.pdf`, `paper/manuscript_submission*.md`, `paper/figures/`, `paper/tables/` | v1.0.0 DS02/DS03 manuscript (RESS; desk-declined) | Frozen record; not the current manuscript |
| `results/extension/figures/` | Extension-stage working figures (`src/ext_figures.py`) | Not used by the manuscript (the manuscript uses `paper/mssp_extended/figures/`) |
| `paper/mssp_extended/submission_bundle/latex_source.zip`, `cover_letter/cover_letter.log`, `latex/*.aux` | Git-ignored local build products on `main` | Present locally only. The tracked submission bundle is on branch `mssp-extended` |
| `results/extension/_shakedown_attempt1/` | First reference attempt, before Amendment 3 | Archived unchanged, not used |

## Provenance gaps

- Fig. 1 has no data inputs by design (schematic).
- The per-table column mapping of the supplement was not verified cell by cell in this audit. The supplement's input hashes
  are verified.
