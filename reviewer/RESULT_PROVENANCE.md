# Result provenance — ncmapss-phase-entanglement (MSSP extended manuscript)

**Generic chain for extension numbers.**

```
manuscript_mssp_draft.md (§, page in latex/main.pdf)
 → Table/Figure (paper/mssp_extended/{tables,figures}/…, provenance sidecar)
 → summary artifact (results/extension/summary/*.csv|json, or evidence/post_hoc_checks.json, or focused_validation/summary/*)
 → per-subset audit artifact (results/extension/<DS>/audit/*.csv)
 → analysis code (src/ext_endpoints.py, src/ext_summary.py, paper/mssp_extended/post_hoc_checks.py, src/ext_focused_validation.py)
 → locked thresholds and models (results/extension/<DS>/lock/calibration_lock.json; models/*, git-ignored, hash-locked)
 → protocol (docs/extension/GENERALIZATION_PROTOCOL.md v1.0 + Amendments 1–3; FOCUSED_VALIDATION_PLAN.md)
 → raw data (N-CMAPSS/N-CMAPSS_<DS>.h5, not redistributed; hash recorded as input_sha256 in each lock)
```

**Verification legend.**
- **V** = `paper/mssp_extended/verify_numbers.py` re-derives the value from the source and finds it verbatim (all 78 claims pass, 2026-09-29).
- **R** = this audit independently re-read or re-aggregated the value from the committed CSV/JSON with its own code.
- **L** = the ledger row exists, with a source hash that still matches.
- "Rounding" compares the manuscript value with the stored full-precision value.
- "Reproducible without rerun?" means from committed artifacts only, with no raw data and no GPU.

## Headline numbers

| # | Manuscript value (location) | Source artifact → stored value | Rounding OK? | Checks | Reproducible without rerun? | Provenance complete? |
|---|---|---|---|---|---|---|
| 1 | H1 SUPPORTED, "three of five families" (§4.2, Abstract, Table 4) | `summary/decisions.json["H1"]` → SUPPORTED | n/a | V, R, L (EX000001) | Yes | Yes |
| 2 | DS01 LSTM 0.49, DS04 PCA 0.40, DS07 LSTM 0.35 pp (§4.2) | `summary/transport_summary_alpha_0.01.csv` pooled A2 (seed means) | Yes (2 dp) | V, L (EX001587–9) | Yes | Yes |
| 3 | 66% of 70 cells; H2 PARTIAL (§4.3) | `*/audit/paired_transport.csv` `diff_pooled_A1 < 0` → 46/70 = 65.71% | Yes | V, R, L | Yes | Yes |
| 4 | PCA DS05/DS06: P 2.64/2.62, C 4.72/5.67, Q 16.41/17.46 pp (§4.3) | `transport_summary_alpha_0.01.csv` → 0.026387/0.026196, 0.047188/0.056736, 0.164060/0.174577 | Yes | V, R, L | Yes | Yes |
| 5 | 14% every-engine improved; 86% ≥ 1 worse, for both C and Q (§4.3) | `paired_transport.csv` `uniform_improvement`, `n_worse` → 10/70, 60/70 | Yes (14.3, 85.7) | V, R, L | Yes | Yes |
| 6 | 28, 28, 26 of 30 engines at the material line (§4.3) | `*/audit/paired_transport_engines.csv` (median over 7 residual runs) | n/a (counts) | V, L (EX001599) | Yes | Yes |
| 7 | DS08a e14: 5.00 / 5.39 / 11.40 pp (§4.3) | `DS08a/audit/paired_transport_engines.csv` unit 14, α = 0.01, residual runs | Yes | V, R, L | Yes | Yes |
| 8 | e14 flight 3: 65% of healthy alarms; FPR 2.70% → 1.00%; span 32,029 ft vs ≤ 28,051 / ≤ 30,033 (§4.9) | `evidence/post_hoc_checks.json["ds08a_engine14"]` → 0.6535, 0.027029, 0.009969, 32029, 28051, 30033 | Yes | V, L (EX001640–1) | Yes | Yes. The per-flight alarm counts are derived by `post_hoc_checks.py` from `flight_trajectories.csv`; the altitude spans come from `results/extension/metadata/` |
| 9 | CVAE − best residual ME-A2(P): 0.52 pp [0.05, 1.31] (§4.4) | `summary/uext2_cross_dataset.csv` row `cvae_minus_best_residual_ME_A2_P` → 0.005228 [0.000543, 0.013056] | Yes | V, R, L | Yes | Yes |
| 10 | CVAE − median residual: 0.24 pp (§4.4, §4.9) | `post_hoc_checks.json["cvae_vs_residual"]` | Yes | V, L (EX001645–6) | Yes | Yes (post hoc) |
| 11 | CVAE uniform improvement 1/21 (C), 3/21 (Q) (§4.4) | `paired_transport.csv` (detector `cvae`) | n/a | V, R, L | Yes | Yes |
| 12 | H4 SUPPORTED: ≥ 7/10 runs in 5/6 subsets, 3/4 families (§4.5) | `decisions.json["H4"]`; `summary/composition_run_summary.csv` | n/a | V, L | Yes | Yes |
| 13 | Coverage effect 0.11 [−0.04, 0.18] (P); 0.55 [0.18, 1.11] (C) (§4.5) | `summary/composition_bootstrap.csv` → 0.001106 [−0.000381, 0.001763]; 0.005458 [0.001849, 0.011140] | Yes | V, R, L | Yes | Yes |
| 14 | Balanced vs best single: 7/42 (P), 11/42 (C) (§4.5, §4.9) | `post_hoc_checks.json["balanced_design"]` | n/a | V, L (EX001644) | Yes | Yes |
| 15 | WE-FFR under P: 13.0 / 13.0 / 14.3%; ≥ 10% in 63 / 69 / 69% of cells; Q 20.0–21.7% (§4.6) | `summary/we_ffr.csv` (`arm=pooled`, residual runs) | Yes | V, R, L | Yes | Yes |
| 16 | Null WE median 8.6–11.8%; P(≥ 10%) 41–69% (§4.9) | `post_hoc_checks.json["we_ffr_null_range"]` | Yes | V, L (EX001633) | Yes; Monte Carlo with fixed `SEED=20260930`, cheap CPU | Yes |
| 17 | Matched delay (R0): 7 earlier, 18 equal, 0 later, 24 mixed of 49; Q 23 / 32 / 28 earlier (§4.6) | `summary/matched_labels_alpha_0.01.csv` | n/a | V, L | Yes | Yes |
| 18 | U-EXT2: LSTM ΔA1 −0.31 [−0.52, 0.53]; IF ΔME-A2 −0.20 [−0.53, 0.22] (§4.7) | `summary/uext2_cross_dataset.csv` → −0.003082 [−0.005208, 0.005345]; −0.002010 [−0.005277, 0.002158] | Yes | V, R, L | Yes | Yes |
| 19 | Original story PARTIALLY GENERALIZED; S3 4/5; S4, S5 5/5; S1, S2 3/5; M-C + M-B; no rescope flag (§4.7) | `decisions.json` (`original_story`, `matrix_stories`, `rescope_flags`) | n/a | V, R (class, flags), L | Yes | Yes |
| 20 | Focused validation: 27 (C) / 29 (P) / 28 (Q) of 30; median 0.63 vs NF50 0.13 pp; exceptions DS01 e8, DS07 e9, DS08a e12 (§4.8, Abstract, Highlight 5) | `focused_validation/summary/engine_summary.csv` (`clearly_exceeds`) | Yes (0.63, 0.13) | V, R, L (EX001650–3) | Yes | Yes |
| 21 | Against the approximate sampling reference: 13 / 17 / 18 of 30 (§4.8) | `evidence/post_hoc_engine_noise.csv` | n/a | V, L (EX001654) | Yes | Yes |
| 22 | Class-preserving bootstrap: 11–15% of width (33–43% DS01; "about none" DS04, DS08c) (§4.8) | `focused_validation/summary/bootstrap_width_comparison.csv` | Yes. "About none" is operationalised as < 5% in `verify_numbers.py:499` | V, L (EX001655–7) | Yes | Yes |
| 23 | Local recalibration: −0.16 (C), −0.04 (P) pp; 12 and 10 of 30 engines (§4.8) | `focused_validation/summary/local_engine_summary.csv` | Yes | V, L (EX001658–60) | Yes | Yes |
| 24 | Sampling reference: SE median 0.15 pp; null 31 / 30 / 49% vs observed 87 / 80 / 82%; > 95th pct in 60 / 49 / 58% (§4.9) | `post_hoc_checks.json["a2_noise_by_arm"]`, `["se_overall_fpr_range"]` | Yes | V, L (EX001630–2) | Yes | Yes |
| 25 | 53% of material P errors under-alarming (§4.9) | `post_hoc_checks.json` (direction of errors) | Yes | V, L (EX001636) | Yes | Yes |
| 26 | Two-flight confirmation: 36/49 zero; 2/49 ≥ 10%; delay 9.5 → 17; Q 20/49 (§4.9) | `post_hoc_checks.json["two_flight_confirmation"]` → `we_two_zero` 36, `we_two_ge_10pct` 2, `median_delay_single` 9.5, `median_delay_two` 17.0 | Yes | V, R (P arm), L | Yes | Yes |
| 27 | Early sensitivity 0.52–4.67% (median 1.21%) (§4.9) | `post_hoc_checks.json["early_sensitivity_pooled"]` → 0.005176 / 0.012066 / 0.046669 | Yes | V, R, L | Yes | Yes |
| 28 | Frozen DS02: 0.125 / 0.428 / 3.459%; DS03: 0.877 / 0.912 / 1.977% (§4.1) | `paper/manuscript_core_results.csv` → 0.0012466 / 0.0042797 / 0.0345936; 0.0087718 / 0.0091177 / 0.0197738. Upstream: `results/final_validation/canonical_results.csv` row 9; `results/confirmation_ds03/canonical_results.csv` row 15 | Yes | V (frozen), R (CSV lookup), L (EX001661–2) | Yes (from frozen CSVs) | Complete to the frozen canonical CSVs. Upstream generation not re-audited here (see PROJECT_STATE "What I could not trace") |
| 29 | "14 detector runs" (post-confirmation, §4.1) | Frozen pre-extension text `paper/mssp/manuscript_mssp_draft.md` | n/a | Verbatim-text check only (EX001663) | Yes, via `paper/mssp/verify_draft_numbers.py` (passes) | Indirect in this manuscript |
| 30 | 30 audit engines; 14–36 healthy flights per engine; N per subset (§3.1, §4.9, Table 1) | Locks (`roles`); `post_hoc_checks.json`; Table 1 CSV | n/a | V, L (EX001626, EX001634) | Yes | Yes |

## Integrity checks performed in this audit (2026-09-29, read-only)

| Check | Result |
|---|---|
| `verify_numbers.py` (extended) | 78 claims, 5 tables, 6 figures, 47 citation keys; all checks passed |
| `paper/mssp/verify_draft_numbers.py` (pre-extension) | 81 values re-derived verbatim; references 47/47 |
| Provenance sidecars (figures, tables, supplement) | 242 hashes, 0 mismatches |
| `docs/release/v1.1.0/PUBLIC_RELEASE_MANIFEST.sha256` | 1,008 / 1,008 OK |
| `paper/mssp_extended/evidence/SHA256SUMS` | 22 / 22 OK |
| `docs/mssp/frozen_baseline.sha256` | 167 / 186 OK; the 19 absent files are RESS administration (documented) |
| Local model binaries vs lock hashes (`results/extension/*/models/`) | 84 / 84 match (git-ignored; local only) |
| Independent re-read or re-aggregation (items marked R; 14 items) | All matched to the displayed precision |

## Where regeneration would require expensive compute

- **Any per-row score:** re-scoring the audit rows needs the raw HDF5 plus the locked models; the LSTM and CVAE need a GPU.
  Needed for new calibration arms, per-engine thresholds with different k, or class-conditional thresholds.
- **Any retraining** (new detector, second CVAE): GPU training; the protocol estimates are in §20 of the protocol.
- **Q-arm refits:** CPU, about 1 h per subset with 10 workers (`docs/extension/FREEZE_RECORD.md`).
- **Everything in the table above:** regenerable from committed CSV/JSON only, via `verify_numbers.py` or the builders, in seconds.

## Discrepancies found

None in the numbers. The wording and metadata observations are:
1. The abstract and highlight 5 give "27 of 30" without naming the arm; it is the C-arm count.
2. The Markdown header says "not submitted", while the README refers to "the current journal submission".
3. The Code availability statement promises a Zenodo DOI that is not yet minted.

See `PROJECT_STATE.md` → "Known unresolved traceability issues" and "WHAT I COULD NOT TRACE".

## The two numbers without "independent support" (identified 2026-09-29)

`verify_numbers.py` reports independent support for 76 of 78 displayed numbers. A read-only wrapper, which replicates its
`independent_support` function and lists the misses, gives the following. Both numbers are forward-verified by the script,
were re-read here, and have pre-existing ledger rows that the heuristic misses for formatting reasons.

| Displayed | Claim (category) | Source value | Pre-existing ledger row | Why the heuristic misses it |
|---|---|---|---|---|
| −0.53 | "Isolation Forest −0.20 pp, −0.53 to 0.22 pp" (pre-specified) | `results/extension/summary/uext2_cross_dataset.csv`, `isolation_forest`/`diff_ME_A2`, `ci_lower_95` = −0.005277 | EX000938: "95% interval −0.528 to 0.216 pp" | The bound is only in the claim text, at three decimals; the `value` column holds the point estimate |
| −0.09 | "Under P … (+0.11 pp, against −0.09 and −0.08 pp for classes 2 and 3)" (post hoc) | `paper/mssp_extended/evidence/post_hoc_checks.json`, `coverage_by_audit_class/pooled/2` = −0.000925 | EX001335: "class 1: +0.00110; class 2: -0.00093; class 3: -0.00083" | The value is a composite string, so `pd.to_numeric` gives NaN |
