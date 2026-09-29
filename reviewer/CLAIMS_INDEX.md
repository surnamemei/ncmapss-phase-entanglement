# Claims index — ncmapss-phase-entanglement (MSSP extended manuscript)

- **Canonical text:** `paper/mssp_extended/manuscript_mssp_draft.md`, rendered as `paper/mssp_extended/latex/main.pdf` (21 pp.).
- **Page numbers** refer to that PDF (build 2026-09-29 12:48, SHA-256 `d51ec1ce…`).
- **Claim IDs** (C001…) are stable identifiers for this reviewer package. They are not used anywhere else in the repository.

**How the evidence was checked (2026-09-29).**
- `paper/mssp_extended/verify_numbers.py` passes. It re-derives every number in the abstract, the highlights and §§4–6 from
  committed outputs, and checks each against its row in the evidence ledger.
- The ledger is `docs/extension/EXTENSION_EVIDENCE_LEDGER.csv`. "EX…" below are its row IDs; the manuscript-claim rows are EX001586–EX001663.
- **"Recomputed"** means this audit independently re-read or re-aggregated the value from the committed CSV/JSON with its
  own code (pandas; no repository code).
  - Re-aggregated from lower-level CSVs: C011, C013, C017, C020, C025 and C030.
  - Re-read from the stored summary value: C001, C002, C012, C019, C022 and C028.

## Shared defaults

These apply to every claim unless the claim says otherwise.

| Field | Default |
|---|---|
| Dataset / split | 7 new subsets DS01, DS04, DS05, DS06, DS07, DS08a, DS08c (families F1=DS01, F2=DS04, F3=DS05–07, F4=DS08a, F5=DS08c); references DS02, DS03 (no hypothesis decisions). Engine roles by `src/ext_common.py:allocate` (R-ALLOC; protocol §3), from engine identity and flight class only; audit engines = official test engines (30 in the new cohort). Table 1 / Table S2 |
| Runs | 10 per subset (`src/ext_common.py:RUNS`): PCA ×1, Isolation Forest seeds 0–2, LSTM seeds 0–2, CVAE seeds 0–2; "residual runs" = first 7 |
| Target | α = 1% primary; 0.5% and 2% secondary (`ext_common.TARGETS`) |
| Arms | P pooled, C retrospective phase-conditioned, Q continuous-context quantile regression (`src/ext_calibration.py:quantile_taus`, `fit_q_thresholds`, `row_thresholds`; quantile = `np.quantile(..., method="higher")` in `src/mssp_mitigation.py:q_higher`) |
| Statistical procedure | Count rules on point estimates (protocol §13); **no p-values**. Subset holds if strict majority of runs; family holds if strict majority of subsets |
| CI procedure | U-EXT1: per-subset engine→flight bootstrap, 2,000 replicates, thresholds re-estimated (`src/ext_endpoints.py:bootstrap_uext1`, seed `UEXT1_SEED=20260929`). U-EXT2: family→subset→U-EXT1 replicate, 2,000 (`src/ext_summary.py:uext2`, `UEXT2_SEED=20261002`). Composition bootstrap (`ext_summary.composition_bootstrap`, `COMPOSITION_BOOT_SEED=20261001`). Five top-level units → crude |
| Seeds | Model seeds 0,1,2; composition subsamples `COMPOSITION_BASE_SEED=20260930`, draws 0–4; post hoc checks `SEED=20260930` (`paper/mssp_extended/post_hoc_checks.py`); focused validation 20261003/4/5 (`src/ext_focused_validation.py`) |
| Pipeline | `scripts/run_extension.py` → `src/ext_pipeline.py` (`phase_lock`, `phase_audit`, `reference_work`, `evaluate`, `score_audit`) → `src/ext_endpoints.py` tables → `src/ext_summary.py:main` → `results/extension/summary/*` |
| Protocol | `docs/extension/GENERALIZATION_PROTOCOL.md` v1.0 (+ Amendments 1–3, `docs/extension/AMENDMENTS.md`) |
| Compute | Every claim is reproducible from committed outputs **without** data or GPU (verify script). Regenerating the outputs requires the NASA HDF5 files and a CUDA GPU |

---

## Frozen earlier stages (cited, not re-tested)

### C001 — DS02 discovery: pooled calibration left healthy FPR phase-dependent
| Field | Value |
|---|---|
| Claim | PCA at 1%: climb 0.125%, cruise 0.428%, descent 3.459% |
| Location | §4.1 p. 9; §1 "Earlier stages" p. 2 |
| Table/Figure | Fig. 2 (grey DS02 panel shows the extension rerun, not these frozen values); Supplement Part B |
| Code | `src/final_validation.py` (v1.0.0 pipeline) |
| Config | `configs/ds02_discovery.yaml`; `results/final_validation/frozen_protocol.md`; `results/final_validation/run_config.json` |
| Input → processed | `N-CMAPSS/N-CMAPSS_DS02-006.h5` → `results/final_validation/canonical_results.csv` row 9 → `paper/manuscript_core_results.csv` keys `D02-PCA-SINGLE-{climb,cruise,descent}_fpr` (E000107–E000109) |
| Ledger | EX001661 |
| Statistic / CI | Point estimates; frozen CIs exist in `manuscript_core_results.csv` (hierarchical engine→flight bootstrap, 2,000, `BOOTSTRAP_SEED=20260925`) but are **not** quoted in the extension manuscript |
| Split | DS02 frozen roles (`src/ext_common.py:FROZEN_ROLES`) |
| Evidence | Direct but **exploratory** (the `exploratory_or_confirmatory` column says `exploratory`) |
| Overclaiming | Presenting DS02 as confirmatory; generalizing "descent highest" (not universal in the extension, C008) |
| New compute to strengthen | None possible without re-opening frozen data; not needed |

### C002 — DS03 one-shot confirmation reproduced the pre-specified pooled directional pattern
| Field | Value |
|---|---|
| Claim | PCA: climb 0.877%, cruise 0.912%, descent 1.977% |
| Location | §4.1 p. 9; §1 p. 2 |
| Code | `src/confirm_frozen_ds03.py` (phase rule `primary_phase`, 90% altitude) |
| Config / locks | `configs/ds03_confirmation.yaml`; `results/confirmation_ds03/{pre_audit_plan.json,calibration_lock.json,official_test_opened.json,run_config.json}` |
| Processed | `results/confirmation_ds03/canonical_results.csv` row 15 → `paper/manuscript_core_results.csv` `D03-PCA-SINGLE-*` (E010947–E010949) |
| Ledger | EX001662 |
| Evidence | Direct, confirmatory (6 official test engines) |
| Limitations | Climb (0.877%) and cruise (0.912%) are nearly equal; the confirmed statement is the **directional** pattern only. Six audit engines |
| Overclaiming | "Confirmed a phase effect in general" or "descent always highest" |
| New compute | None (the one-shot confirmation cannot be repeated) |

### C003 — Post-confirmation: C reduced pooled disparity in all 14 runs but did not transport to individual engines
| Field | Value |
|---|---|
| Location | §4.1 p. 9; §1 p. 2 |
| Source | Frozen pre-extension text `paper/mssp/manuscript_mssp_draft.md`; outputs `results/mssp_mitigation/{ds02,ds03,stage_f}/`; protocol `docs/mssp/post_confirmation_mitigation_protocol.md` |
| Code | `src/mssp_mitigation.py`, `scripts/run_mssp_mitigation.py` |
| Ledger | EX001663 (verbatim-text check against the frozen text only) |
| Evidence | Indirect in this manuscript. It cites a frozen earlier result; the number itself is not re-derived by `verify_numbers.py`. It was verified at pre-extension time by `paper/mssp/verify_draft_numbers.py` (passes, 81 values) |
| Overclaiming | Treating "14/14 runs" as independent replications (seeds are near-replicates) |

### C004 — Extension reference runs: uncovered-class engines worsened under C in every run
| Field | Value |
|---|---|
| Claim | DS02 class-1 engine 14 and DS03 class-1 engine 12 (classes absent from calibration) were worse under C in every residual run and every CVAE seed |
| Location | §4.1 p. 9 |
| Artifacts | `results/extension/{DS02,DS03}/audit/paired_transport_engines.csv` |
| Code | `src/ext_endpoints.py:healthy_tables` (per-engine A2), paired differences written by `src/ext_pipeline.py:evaluate` |
| Ledger | EX001602 |
| Evidence | Direct, descriptive; reference subsets decide no hypothesis |
| Overclaiming | Using reference-subset results as evidence for H3 |

## Cohort and design facts

### C005 — Cohort: seven unopened subsets, five families, 30 audit engines; DS08d excluded before reading
| Field | Value |
|---|---|
| Location | §3.1 p. 4; Abstract; Table 1 p. 6; Table S1 |
| Artifacts | `docs/extension/SUBSET_SELECTION_LOCK.md` (locked at `7152b92`); `docs/extension/subset_metadata_audit.{json,csv}`; `docs/extension/archive_extraction_record.json` |
| Code | `src/ext_subset_metadata.py` (criteria C1–C9; `MIN_TEST_PHASE_ROWS=1000`, `MIN_ENGINES=3`) |
| Ledger | EX001626 (30 engines), EX001627 (DS08c class-3-only calibration), EX001628 (32-byte truncation) |
| Evidence | Direct |
| Assumption | The metadata audit read only engine, cycle, flight class, health label, variable names and healthy altitude. This is asserted in the lock and the access log (`docs/extension/OUTCOME_ACCESS_LOG.md`); it is not independently verifiable after the fact |

### C006 — Subsets reuse a library of recorded flights; fleet families defined accordingly
| Field | Value |
|---|---|
| Location | §3.1 p. 4; §4.9 p. 14–15; §5.5 |
| Artifacts | `docs/extension/profile_sharing_engine_pairs.csv`, `profile_sharing_by_dataset.csv`; `results/extension/metadata/healthy_flight_phase_segments.csv` |
| Code | `src/ext_profile_sharing.py` (flight "signatures"); the F3 duplicate digests are in each lock (`duplicate_digests_development`) |
| Evidence | Direct (data-structure fact) |
| Limitation | Families reduce but do not remove dependence; the statistical reviewer noted 45–77% of new flight signatures also occur in DS02/DS03 (`docs/extension/EXTENSION_HOSTILE_REVIEW.md` §2.3; not re-checked there, and not in the manuscript) |

## H1 — pooled calibration

### C007 — Pooled calibration left material phase-conditional miscalibration in 3 of 5 families (H1 SUPPORTED)
| Field | Value |
|---|---|
| Claim | Pooled A2 ≥ 0.5 pp for PCA and the IF and LSTM seed means in DS05, DS06, DS08a, DS08c. Near misses: DS01 LSTM 0.49, DS04 PCA 0.40, DS07 LSTM 0.35 pp |
| Location | §4.2 p. 10; Abstract; Highlight 1; §6 |
| Equation | A2 = max over phases of \|FPR_φ − α\| (§3.6 p. 6, inline) |
| Table/Figure | Table 2 (p. 8); Table 4 row H1 (p. 9); Fig. 2 (p. 10); Table S5 |
| Code | `src/ext_summary.py:h1`; A2 in `src/ext_endpoints.py:errors` / `quality_from_counts` |
| Protocol | §13.1 (≥ 3 of 5 families) |
| Input → processed | `results/extension/*/audit/transport_summary.csv` → `results/extension/summary/decisions.json["H1"]`, `transport_summary_alpha_0.01.csv` |
| Ledger | EX000001, EX001586–EX001589 |
| Statistic / CI | Count rule on point estimates; no interval |
| Evidence | Direct |
| Limitations | Sits **exactly** at threshold (3/5). F5 (DS08c) counts only because A2 counts under-alarming (C009). Near misses of 0.01 pp (DS01) |
| Overclaiming | "Pooled calibration fails on N-CMAPSS"; "phase disparity in most fleets" (DS08c is a level shift, not a disparity) |
| New compute | None; a target sensitivity already exists (Table S10). An over-alarming-only criterion is cheap from existing CSVs but post hoc (see ISSUE_BANK I-03) |

### C008 — Descent was usually, not always, the highest phase under P
| Field | Value |
|---|---|
| Claim | Descent was highest in 10/10 runs in DS01 and DS07, and in 9/10 in DS04–DS06. In DS08a, cruise led in 5/10; in DS08c, climb and descent split 5/5 |
| Location | §4.2 p. 10; §5.1 |
| Figure | Fig. 2; Table 2 column "highest-FPR phase" |
| Artifact | `results/extension/summary/phase_ordering_pooled.csv` (from `ext_summary.h1`) |
| Ledger | EX001590, EX001591 |
| Evidence | Direct, descriptive |
| Overclaiming | "Descent is the problem phase" as a general law |

### C009 — DS08c: FPR below target in every phase (uniform under-alarming)
| Field | Value |
|---|---|
| Location | §4.2 p. 10; §4.9 "Direction of errors" |
| Artifact | `results/extension/summary/transport_summary_alpha_0.01.csv` |
| Ledger | EX001592 |
| Evidence | Direct |
| Note | This is the reason F5 counts toward H1; the text states it (hostile-review correction) |

### C010 — The phase effect does not require transport (in-sample calibration engines)
| Field | Value |
|---|---|
| Claim | In the calibration engines themselves, descent was highest in 10/10 runs (DS01), 7–9/10 (DS04–DS08a) and 2/10 (DS08c) |
| Location | §4.2 p. 10 |
| Artifact | `results/extension/*/lock/calibration_in_sample_phase_fpr.csv` (written at lock time, before any test read) |
| Ledger | EX001593 |
| Evidence | Direct |
| Implication | Part of every "transport" error under P is in-sample pooling error. A2 does not separate the two (reviewer attack, ISSUE_BANK I-02) |

## H2/H3 — conditioned calibration

### C011 — C reduced pooled disparity in 66% of 70 cells and 3 of 5 families (H2 PARTIAL)
| Field | Value |
|---|---|
| Location | §4.3 p. 10; §5.1 |
| Table | Table 3 (p. 8), Table 4 row H2; Table S6 |
| Code | `src/ext_summary.py:h2` |
| Protocol | §13.2 (+ Amendment 1, change 2, which closed a classification gap) |
| Artifact | `results/extension/*/audit/paired_transport.csv` (`diff_pooled_A1`) → `decisions.json["H2"]` |
| Ledger | EX000002, EX001594 |
| Recomputed | 46/70 = 65.7% |
| Evidence | Direct |

### C012 — For PCA on DS05/DS06, C and especially Q made pooled calibration much worse
| Field | Value |
|---|---|
| Claim | Pooled A2 4.72 and 5.67 pp under C against 2.64 and 2.62 under P; Q 16.41 and 17.46 pp |
| Location | §4.3 p. 10; §5.1, §5.2 |
| Artifact | `results/extension/summary/transport_summary_alpha_0.01.csv` (rows `pca`, DS05/DS06) |
| Ledger | EX001595, EX001596 |
| Recomputed | Re-read: yes (exact to 2 dp) |
| Evidence | Direct, descriptive |
| Overclaiming | "Phase conditioning is harmful" in general; this is two PCA cells from one family (F3) |

### C013 — C (and Q) improved every audit engine in only 14% of cells; ≥ 1 engine worse in 86% (H3 SURVIVES)
| Field | Value |
|---|---|
| Location | §4.3 p. 10; Table 3; Table 4 row H3 |
| Code | `src/ext_summary.py:h3` (uniform improvement = every engine A2_e(S) < A2_e(P)) |
| Protocol | §13.3 (U_S < 0.5 → SURVIVES) |
| Artifact | `paired_transport.csv` (`uniform_improvement`, `n_worse`) → `decisions.json["H3"]` |
| Ledger | EX000003, EX001597 |
| Recomputed | 14.3% and 85.7% for both C and Q |
| Limitation | A strict-dominance rule with 4–6 audit engines is nearly guaranteed to "survive" under noise. The manuscript says so and reports the engine-level share (C014) |
| Overclaiming | Using 14% alone as evidence of non-transport |

### C014 — On average, conditioning improved about half of the engines per cell (post hoc)
| Field | Value |
|---|---|
| Claim | C improved 50% and Q 49% of the engines in a cell; under coin flips, every engine would improve in about 5.6% of cells, against 14% observed |
| Location | §4.3 p. 10 (pointer), §4.9 p. 15 |
| Code | `paper/mssp_extended/post_hoc_checks.py:main` |
| Artifact | `paper/mssp_extended/evidence/post_hoc_checks.json` |
| Ledger | EX001637, EX001638 |
| Evidence | Direct but **post hoc** (not pre-specified) |
| Overclaiming | "Conditioning does not help": it helps about as often as it hurts |

### C015 — DS04 exception: C and Q each improved every engine in 6/10 runs
| Field | Value |
|---|---|
| Location | §4.3 p. 10; §4.9 (DS04 within material line: 4/7 runs under Q, 1/7 under P and C) |
| Artifacts | `decisions.json`; `post_hoc_checks.json` |
| Ledger | EX001598, EX001639 |
| Evidence | Direct |

### C016 — Median per-engine error reached the material line for 28/28/26 of 30 engines under P/C/Q
| Field | Value |
|---|---|
| Location | §4.3 p. 10; Fig. 3 p. 11; Table S7 |
| Artifact | `results/extension/*/audit/paired_transport_engines.csv` |
| Ledger | EX001599 |
| Limitation | A perfectly calibrated engine would reach the line in ~31/30/49% of engine–run pairs (C033). The count therefore mixes transport and sampling noise |
| Overclaiming | "28 of 30 engines are miscalibrated" without the noise reference |

### C017 — Largest failures: missing class (DS08c) or missing flight envelope (DS08a engine 14)
| Field | Value |
|---|---|
| Claim | C worsened DS08c engines 7, 8, 9 in 7/7 residual runs. DS08a engine 14 had median A2 5.00 (P), 5.39 (C) and 11.40 (Q) pp. One of its 15 healthy flights carried 65% of its healthy alarms under P (FPR 2.70% → 1.00% without it); that flight's altitude span of 32,029 ft exceeded every fit flight (≤ 28,051 ft) and calibration flight (≤ 30,033 ft) |
| Location | §4.3 p. 10–11; §4.9 p. 15; §5.2; Abstract ("largest failures arose where…") |
| Artifacts | `results/extension/DS08c/audit/paired_transport_engines.csv`; `results/extension/DS08a/audit/paired_transport_engines.csv`; `post_hoc_checks.json` (flight decomposition) |
| Ledger | EX001600, EX001601, EX001640, EX001641 |
| Recomputed | 5.00 / 5.39 / 11.40 pp (7 residual runs) |
| Evidence | Direct for the numbers; the **mechanism** (envelope) is a post hoc attribution from one flight |
| Overclaiming | "Envelope coverage causes failures" (n = 1 flight, one engine); "class coverage is necessary" |
| New compute | None needed; a flight-exclusion sensitivity is already in `post_hoc_checks.json` |

## H5 — condition-aware representation

### C018 — The fleet-trained CVAE did not remove the transport problem (H5 SURVIVES)
| Field | Value |
|---|---|
| Claim | CVAE WE-A2(P) reached the material line in a majority of runs in all 5 families. It never met the halving criterion, and it reduced pooled phase dependence relative to every residual detector in only 2 families |
| Location | §4.4 p. 11; Abstract; Highlight 3; Fig. 5 p. 12; Table 4 row H5 |
| Code | `src/ext_summary.py:h5`; model `src/ext_cvae.py` (`ConditionalVAE`, `score`); spec `docs/extension/CVAE_SPECIFICATION.md` (+ Amendment 2) |
| Artifact | `transport_summary.csv` (per subset) → `decisions.json["H5"]` |
| Ledger | EX000005, EX001603, EX001604 |
| Seeds | CVAE seeds 0–2; epoch selection on the validation engine (≤ 600 epochs, patience 6), then refit |
| Limitations | One specification. The score omits the latent-prior (KL) term. The decoder variance sits at its floor for many channels (lock field `cvae_variance_bound_share`; Table S3). Fleet-trained, not per-engine, unlike [N38] |
| Overclaiming | "Condition-aware representations do not help transport" (general); "CVAE-based monitoring fails" |
| New compute | A second condition-aware model or per-engine training (GPU) — ISSUE_BANK I-08 |

### C019 — CVAE per-engine error exceeded the best residual detector by 0.52 pp [0.05, 1.31] and the median one by 0.24 pp
| Field | Value |
|---|---|
| Location | §4.4 p. 11; §4.9 p. 15; §4.8 (class-preserving: 0.06–1.18) |
| Code | `src/ext_summary.py:uext2` (row `cvae_minus_best_residual_ME_A2_P`); median-residual gap in `post_hoc_checks.py` |
| Artifacts | `results/extension/summary/uext2_cross_dataset.csv`; `post_hoc_checks.json`; `results/extension/focused_validation/summary/uext2_original_vs_class_preserving.csv` |
| Ledger | EX001605, EX001645, EX001646, EX001657 |
| CI | U-EXT2 family bootstrap, 2,000 replicates, five top-level units ("crude"; the manuscript says so) |
| Recomputed | 0.5228 pp [0.0543, 1.3056] from `uext2_cross_dataset.csv` |
| Overclaiming | Stating the interval as a significance test; ignoring that the CVAE was lower than the median residual detector in F1 |

### C020 — Conditioned thresholds did not rescue the CVAE (every engine improved in 1/21 cells under C, 3/21 under Q)
| Field | Value |
|---|---|
| Location | §4.4 p. 11; Table 3 |
| Artifact | `paired_transport.csv` (CVAE rows) |
| Ledger | EX001606 |
| Recomputed | 1/21 and 3/21 |

## H4 — composition

### C021 — Coverage mattered for phase-conditioned thresholds at fixed volume (H4 SUPPORTED)
| Field | Value |
|---|---|
| Claim | The within-engine coverage effect was positive in ≥ 7/10 runs under both P and C in 5 of 6 eligible subsets and 3 of 4 eligible families. F1 and F2 reached the rule with exactly 7/10 runs under P |
| Location | §4.5 p. 11; Abstract; Highlight 4 (indirect); Table 5 p. 13; Fig. 4 p. 12; Table S11 |
| Code | `src/ext_calibration.py:build_designs`, `design_thresholds`; `src/ext_endpoints.py:composition_tables`; `src/ext_summary.py:composition_analysis`, `h4` |
| Protocol | §7, §13.4 |
| Artifacts | `results/extension/*/audit/composition_metrics.csv` → `summary/composition_engine_effects.csv`, `composition_run_summary.csv`, `decisions.json["H4"]` |
| Ledger | EX000004, EX001607, EX001611 |
| Seeds | Nested subsamples: `COMPOSITION_BASE_SEED=20260930`, draws 0–4 |
| Limitations | Knife-edge (F1/F2 exactly 7/10 under P). In most pools each class is one engine, so coverage is confounded with engine identity and shared missions (C035). Only 4 eligible families |
| Overclaiming | "Coverage is necessary", "coverage causes better transport", or "more data from other classes does not substitute" (explicitly withdrawn after internal review) |

### C022 — Coverage effect: 0.11 pp [−0.04, 0.18] under P; 0.55 pp [0.18, 1.11] under C
| Field | Value |
|---|---|
| Location | §4.5 p. 11; Fig. 4a |
| Code | `src/ext_summary.py:composition_bootstrap` (family → subset → audit engine, 2,000) |
| Artifact | `results/extension/summary/composition_bootstrap.csv` |
| Ledger | EX001612, EX001613 |
| Recomputed | P 0.1106 [−0.0381, 0.1763]; C 0.5458 [0.1849, 1.1140] |
| Overclaiming | Claiming coverage helps pooled thresholds (the interval includes zero) |

### C023 — Class-balanced designs beat the mean single engine but rarely the best single engine
| Field | Value |
|---|---|
| Claim | The balanced design beat the mean single-engine design in ≥ 9/10 runs under both arms in 5/6 subsets (DS04 under C: 0/10), but beat the best single engine in only 7/42 (P) and 11/42 (C) residual runs |
| Location | §4.5 p. 11; §4.9 p. 15; Fig. 4b |
| Artifacts | `composition_run_summary.csv`; `post_hoc_checks.json` |
| Ledger | EX001608, EX001609, EX001644 |
| Note | Beating the mean is largely averaging (convexity), and the manuscript says so |

### C024 — Volume contrast within 0.05 pp of zero in every subset (by construction)
| Field | Value |
|---|---|
| Location | §4.5 p. 11; §3.8 p. 7 |
| Ledger | EX001610 |
| Evidence | Direct, but **uninformative by design**: rows are thinned within the same engine's flights. The manuscript states this |

## H6/H7 — persistence and delay

### C025 — Within-flight persistence did not remove flight-level burden (H6 SURVIVES)
| Field | Value |
|---|---|
| Claim | Median worst-engine FFR under P at locked κ was 13.0% (R0), 13.0% (R1) and 14.3% (R2). A worst engine ≥ 10% occurred in 63/69/69% of residual cells, and in the majority of cells in 3/4/4 of 5 families. Under Q the median worst engine was 20.0–21.7% |
| Location | §4.6 p. 12; Fig. 6a p. 13; Table S14 |
| Code | `src/ext_calibration.py:apply_rule`, `kappa` (0.95 quantile of healthy calibration-flight fractions); `src/ext_endpoints.py:persistence_and_flight_tables`; `src/ext_summary.py:h6`, `we_ffr_table` |
| Artifacts | `results/extension/*/audit/flight_false_flags.csv` → `summary/we_ffr.csv` |
| Ledger | EX000006, EX001614–EX001616 |
| Limitations | Persistence rules act within a flight (seconds at 1 Hz), not across flights. Most worst-engine rates are within the null (C026) |
| Overclaiming | "Persistence rules cannot fix transport": only within-flight on-delays were tested |

### C026 — Most worst-engine flight-level rates are within sampling noise (post hoc)
| Field | Value |
|---|---|
| Claim | Under an exchangeable-calibration null, the median worst engine is 8.6–11.8% and reaches 10% in 41–69% of cells. The observed worst engine under P exceeded the null 95th percentile in 0 runs (DS01, DS04, DS07, DS08c) and in 1–3 of 7 (DS05, DS06, DS08a) |
| Location | §4.6 p. 12 (pointer); §4.9 p. 14; Fig. 6a grey bands; Table S18 |
| Code | `paper/mssp_extended/post_hoc_checks.py:we_ffr_null` (seed 20260930) |
| Artifact | `post_hoc_checks.json` |
| Ledger | EX001633–EX001635 |
| Evidence | Direct, post hoc |
| Consequence | H6's pre-specified 10% line has little discriminating power. The manuscript acknowledges this |

### C027 — No matched-burden delay advantage meeting the pre-specified criterion
| Field | Value |
|---|---|
| Claim | Under R0, 7 of 49 residual runs were earlier than P, 18 equal, none later and 24 mixed; the criterion was met in no subset under any rule. Q was earlier in 23/32/28 of 49 runs (R0/R1/R2) but met the criterion only on DS04 under R1/R2 |
| Location | §4.6 p. 12; Fig. 6b; Table S15 |
| Code | `src/ext_endpoints.py:matched_tables` (frozen adversarial Part B); `src/ext_summary.py:h7` |
| Protocol | §9 (H7 is a rule, not a test; `decisions.json["H7"]` has no verdict) |
| Artifacts | `results/extension/*/audit/matched_labels.csv` → `summary/matched_labels_alpha_0.01.csv` |
| Ledger | EX001617–EX001620 |
| Limitations | Burden is matched on the pooled rate, not per engine. Early post-onset sensitivity is near the false-alarm floor (C038), so power is low |
| Overclaiming | "No delay advantage" without "meeting the pre-specified criterion"; any delay claim for Q |

## Cross-dataset and story

### C028 — Cross-dataset C − P intervals include zero for every detector family
| Field | Value |
|---|---|
| Claim | For example, LSTM disparity −0.31 pp [−0.52, 0.53]; Isolation Forest ME-A2 −0.20 pp [−0.53, 0.22] |
| Location | §4.7 p. 13; Table S9 |
| Code | `src/ext_summary.py:uext2` |
| Artifact | `results/extension/summary/uext2_cross_dataset.csv` |
| Ledger | EX001621, EX001622 |
| Recomputed | LSTM −0.3082 [−0.5208, 0.5345]; IF −0.2010 [−0.5277, 0.2158] |
| Limitations | The per-subset bootstrap resamples calibration engines **without** class stratification and omits a class in 78% of replicates in DS01/DS05–07 (C036, C031) |

### C029 — The earlier story is PARTIALLY GENERALIZED; interpretation matrix selects M-C + M-B; no rescope flag
| Field | Value |
|---|---|
| Location | §4.7 p. 13; Table 4 |
| Code | `src/ext_summary.py:original_story`, `stories`, `rescope_flags` |
| Protocol | §14, §15 (+ Amendment 1, change 1), §16 |
| Artifact | `decisions.json` (`original_story.class = PARTIALLY GENERALIZED`; `rescope_flags` A–F all false) |
| Ledger | EX000007, EX000008, EX001623–EX001625 |
| Note | Amendment 1 changed the class ordering (REFUTED first) before any outcome existed. A reviewer may still ask why the rule was completed after the freeze |

## Focused validation (post hoc, frozen plan)

### C030 — Fleet-calibrated per-engine errors exceeded the engine's cross-fitted self-calibration reference in 27/30 engines (C)
| Field | Value |
|---|---|
| Claim | Median fleet error 0.63 pp under C against median NF50 0.13 pp. Exceeded in 27 of 30 engines (C), 29 (P) and 28 (Q), in all five families; exceptions under C were DS01 e8, DS07 e9 and DS08a e12. Against the approximate sampling reference, 13/17/18 of 30 |
| Location | §4.8 p. 14; Abstract; Highlight 5; §5.1; §6; Table S21 |
| Code | `src/ext_focused_validation.py:crossfit_draws` (5-fold, 200 repetitions, `SEED_CROSSFIT=20261004`), `run_subset`, `summarize`; `scripts/run_focused_validation.py` |
| Plan | `docs/extension/FOCUSED_VALIDATION_PLAN.md` (frozen `d85aa10` before re-read); report `docs/extension/FOCUSED_VALIDATION_REPORT.md` |
| Artifacts | `results/extension/focused_validation/{DS*}/engine_noise_floor.csv`, `noise_floor_draws.csv` → `summary/engine_summary.csv`; `paper/mssp_extended/evidence/post_hoc_engine_noise.csv` |
| Ledger | EX001650–EX001654 |
| Recomputed | 29/30 (P), 27/30 (C), 28/30 (Q); medians 0.74 / 0.63 / 0.76 pp; NF50 0.13 pp |
| Rule | "Clearly exceeds" = fleet A2 > NF95 in ≥ 4 of 7 residual runs |
| Limitations | Post hoc: it re-read healthy official-test rows after all outcomes, under a separately frozen plan. The cross-fitted reference **understates** flight-to-flight noise (manuscript §3.10). The count depends on the reference (27 vs 13) |
| Overclaiming | Quoting "27 of 30" without the arm or without the 13/17/18 alternative; calling the result confirmatory |

### C031 — Class-preserving bootstrap: omitting classes explained 11–15% of C − P interval width; no inference changed
| Field | Value |
|---|---|
| Location | §4.8 p. 14; Tables S23–S24 |
| Code | `src/ext_focused_validation.py:class_preserving_plans` (`SEED_CLASS_BOOT=20261003`), `uext2_with` |
| Artifacts | `focused_validation/*/bootstrap_class_preserving_{ci,replicates_alpha_0.01}.csv` → `summary/bootstrap_width_comparison.csv`, `uext2_original_vs_class_preserving.csv` |
| Ledger | EX001655–EX001657 |

### C032 — Five-flight local recalibration did not reduce per-engine error
| Field | Value |
|---|---|
| Claim | Median change −0.16 pp (C) and −0.04 pp (P); a majority of runs improved for only 12 (C) and 10 (P) of 30 engines. Fleet errors were already within the range of random five-flight local thresholds for every engine |
| Location | §4.8 p. 14; §5.3; Table S22 |
| Code | `src/ext_focused_validation.py:local_recalibration`, `k_matched_draws` (`K_LOCAL=5`, `R_LOCAL=200`, `SEED_LOCAL=20261005`) |
| Artifacts | `focused_validation/*/local_recalibration.csv` → `summary/local_engine_summary.csv` |
| Ledger | EX001658–EX001660 |
| Limitation | k = 5 only (fixed before the run); the k = 3 and k = 10 arms proposed by the internal review were not run |
| Overclaiming | "Local recalibration does not work": only a first-five-flights, per-phase quantile version was tested |

## Other post hoc checks (§4.9)

### C033 — Approximate sampling reference for per-engine A2
| Field | Value |
|---|---|
| Claim | Median flight-clustered SE of an engine's healthy FPR is 0.15 pp. A perfectly calibrated engine would reach the material line in ~31/30/49% of engine–run pairs (P/C/Q), against 87/80/82% observed; 60/49/58% exceeded the reference's 95th percentile |
| Code | `post_hoc_checks.py:a2_noise` |
| Ledger | EX001630–EX001632; Table S19 |
| Note | This reference **overstates** pure sampling noise because it includes between-flight variation (manuscript says so) |

### C034 — 53% of material per-engine errors under P were under-alarming
| Ledger | EX001636 (`post_hoc_checks.json`); §4.9 p. 15 |
|---|---|
| Consequence | A2 counts under-alarming as miscalibration; a reviewer may dispute calling that a "false-alarm" problem |

### C035 — Class coverage coincides with shared recorded missions
| Field | Value |
|---|---|
| Claim | Class-1 audit engines shared 35–56% of healthy flight profiles with their same-class calibration engine, class 2–3 engines 5–20%, and none across classes. Under P, the coverage effect was confined to class 1 (+0.11 against −0.09 and −0.08 pp) |
| Ledger | EX001642, EX001643; §4.9 p. 15; §5.2; §5.5 |
| Artifacts | `post_hoc_checks.json`; `docs/extension/profile_sharing_engine_pairs.csv` |
| Consequence | The coverage effect (C021) may partly be mission reuse. This is a stated limitation |

### C036 — The pre-specified bootstrap omits ≥ 1 calibration class in 78% of replicates (DS01, DS05–07)
| Ledger | EX001647; §4.9 p. 15 |
|---|---|
| Code | `post_hoc_checks.py` (exact design-based enumeration, line ~256) |

### C037 — A two-consecutive-flight confirmation removes most healthy flight-level burden at a delay cost
| Field | Value |
|---|---|
| Claim | Under P, the worst-engine confirmed-alert rate was zero in 36/49 runs and ≥ 10% in 2/49; median delay rose from 9.5 to 17 flights. Under Q, 20/49 runs still reached 10% |
| Ledger | EX001648; §4.9 p. 15; §5.3; Table S20 |
| Artifacts | `post_hoc_checks.json`, computed from `results/extension/*/audit/flight_trajectories.csv` |
| Note | Post hoc; not matched per engine |

### C038 — Early post-onset sensitivity near the healthy target
| Ledger | EX001649: abnormal-state row alarm rate over the first 10 post-onset flights under P, 0.52–4.67% (median 1.21%); §4.9 p. 15; Table S16 |
|---|---|
| Consequence | Delay comparisons (C027) have little power |

## Reproducibility and interpretation claims

### C039 — Reproducibility controls: 186-file frozen manifest verified around every run; every number re-derivable
| Field | Value |
|---|---|
| Location | §3.11 p. 8; Code availability p. 17 |
| Artifacts | `docs/mssp/frozen_baseline.sha256`; per-stage `*_record.json`; `verify_numbers.py` |
| Ledger | EX001629 |
| Status (2026-09-29) | 167/186 verify locally; the 19 absent files are RESS administration files, documented as not distributed |
| Caveat | "The pipeline has not been independently reimplemented" (§3.11); the manuscript states this |

### C040 — Engineering recommendation: judge per-unit calibration against engine-specific references; cover classes and envelopes
| Field | Value |
|---|---|
| Location | Abstract (last sentence); §5.3 p. 16; §6 p. 17; Contribution 4 |
| Evidence | **Indirect**: a recommendation inferred from C016, C017, C021, C030 and C033. It is not itself tested |
| Overclaiming | Presenting it as validated guidance for real fleets or as a deployment claim. §1 "Scope" says no deployment claim is made |
