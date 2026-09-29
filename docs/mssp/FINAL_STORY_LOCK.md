# Final story lock: MSSP calibration-transport manuscript

**Date.** 2026-09-28.
**Branch.** `mssp-revision`. This lock was committed before the final manuscript rewrite (parent commit `fad352a`).
**Status.** LOCKED. The scientific analysis is closed. The manuscript, abstract, highlights, captions, cover letter, supplement and release notes must conform to this file. The story can change only if a genuine reproducibility or factual contradiction is found. Such a change must be recorded here as a dated amendment, and it must never alter a frozen artefact.

**Evidence base.** Nothing in this lock is new analysis. It restates results that are already committed:
- **Frozen.** DS02 discovery and the DS03 one-shot confirmation: `paper/manuscript_core_results.csv` (unchanged evidence IDs), `docs/AUTHORITATIVE_RESULTS.md`, and the 186-file manifest `docs/mssp/frozen_baseline.sha256`.
- **Post-confirmation (frozen protocol v1.0).** `results/mssp_mitigation/`.
- **Adversarial validation (frozen plan, commit `39a5f81`).** `results/mssp_adversarial/`. The claim-by-claim evidence is in `paper/mssp/adversarial_claim_audit.md`.

## Final interpretation in plain language

A single pooled threshold calibrated to a nominal healthy false-alarm rate controls only the exposure-weighted rate over everything it was calibrated on. It does not control the rate inside each operating context.

**Frozen discovery and confirmation.** In simulated full-flight aero-engine data (N-CMAPSS), a pooled threshold on residual-based anomaly scores left healthy false-alarm rates dependent on flight phase, with descent highest. This was discovered on DS02. The pre-specified pooled directional pattern then reproduced on held-out DS03 engines under a frozen, one-shot protocol.

**Post-confirmation analyses.** After that confirmation, separately frozen analyses calibrated per-phase thresholds on the same two calibration engines. For the pooled audit population, these thresholds reduced between-phase disparity and maximum nominal calibration error in every one of the 14 detector runs. These are point estimates; every paired bootstrap interval included zero.

**The pooled correction did not transport reliably to individual engines:**
- the strongest observed failures were on engines from a flight class that no calibration engine represented;
- weighting audit engines equally reversed the DS02 pooled improvement;
- at matched healthy-flight false-flag rates there was no general detection-delay advantage;
- a continuous operating-context quantile-regression threshold did not solve the transport problem, because it failed on different engines;
- the distance from audit operating states to the nearest calibration operating state did not explain the residual failures.

**What this means.** The practical message is an evaluation requirement, not a threshold recipe. Context-specific false-alarm calibration should be judged by its transport across engines and operating classes. Nominal calibration error, between-context disparity, and detection-versus-false-flag trade-offs should be reported together.

## A. Frozen claims that survived unchanged

| # | Claim | Class | Evidence | Manuscript constraint |
| --- | --- | --- | --- | --- |
| A1 | Pooled calibration does not guarantee phase-conditional healthy FPR stability. At the 1% pooled target, DS02 healthy row-level FPR differed across climb, cruise and descent (PCA 0.125%/0.428%/3.459%), with descent highest for all three detector implementations | SUPPORTED (frozen; DS02 exploratory discovery) | `manuscript_core_results.csv` (D02 keys) | Numbers verbatim from the RESS text |
| A2 | Cross-phase threshold transfer is nonuniform in the evaluated subsets. The worst off-diagonal cell applied a climb-calibrated threshold to healthy descent rows in every run on both subsets | SUPPORTED (frozen) | Frozen transfer matrices (E-IDs in `manuscript_core_results.csv`) | Off-diagonal cells are transfer FPRs, not pooled-threshold FPRs |
| A3 | The DS02 discovery and the frozen DS03 pooled directional confirmation remain intact. Engine- and seed-level exceptions stay reported: 3/42 per-engine detector/seed rows (all LSTM seed 2), and every individual-seed DS03 LSTM descent-minus-cruise interval includes zero | SUPPORTED (frozen verdict) | `results/confirmation_ds03/`, `docs/AUTHORITATIVE_RESULTS.md` | Verdict quoted verbatim. Never qualified, reinterpreted or strengthened by post-confirmation results |
| A4 | The tested static, derivative-based and finite-history corrections did not sufficiently attenuate the dependence. The descent contrasts remained positive and did not shrink | SUPPORTED (frozen; DS02 PCA, exploratory) | Contrasts +2.854/+3.045/+3.335 pp | "did not sufficiently attenuate", never "eliminate" or "remove" |
| A5 | The descent elevation appeared across three tested detector implementations | SUPPORTED (frozen) | Frozen DS02/DS03 tables | The implementations share preprocessing and calibration, so they are not independent replications |
| A6 | Under an alternative retrospective phase rule, the DS02 contrasts remained positive | SUPPORTED (frozen; DS02 exploratory) | Frozen sensitivity outputs | The DS03 confirmation used the primary rule only |

## B. Post-confirmation claims that survived only with qualification

**Qualifications common to every B-claim:**
- Each is post-confirmation and exploratory: frozen before execution, but after the DS03 confirmation, and on the same engines.
- None is part of the DS03 confirmation.
- Every paired bootstrap interval at the primary 1% target includes zero, so no B-claim is a significance claim.
- At 0.5% and 2%, 558 of 560 paired intervals include zero.

| # | Claim | Class | Evidence | Required qualification in text |
| --- | --- | --- | --- | --- |
| B1 | Retrospective phase-conditioned thresholds (C) reduced pooled between-phase disparity in all 14 detector runs. The reduction is invariant across 0.5/1/2% | SUPPORTED WITH QUALIFICATION | `mssp_mitigation/*/stage_d/healthy_stability_by_scheme.csv`; `summary/robustness_classification.csv` (R2) | "point estimates; all paired bootstrap intervals included zero" |
| B2 | Pooled (row-pooled) maximum nominal calibration error (A2) improved in all 14 runs, and RMS error (A3) in 13 of 14 | SUPPORTED WITH QUALIFICATION | `calibration_quality_paired.csv` (row_pooled); R3/R4 | Row-pooled estimand only. "Improved nominal phase-wise calibration" is allowed only for DS02 C (pre-specified wording rule); otherwise write "reduced between-phase disparity". Intervals include zero |
| B3 | These pooled improvements did not transport uniformly to engines. Under equal-engine weighting, DS02 was category 4 (both worse) in 5 of 7 runs at 1% | SUPPORTED WITH QUALIFICATION | `calibration_quality_paired.csv` (equal_engine, per_engine); `summary/denominator_audit.csv` | Three and six audit engines. Stated as observed engine heterogeneity, not a population estimate |
| B4 | Continuous contextual calibration (Q) did not systematically solve the problem. It reduced disparity relative to P in 12/14 runs and beat C on row-pooled A2 in only 3/14. It transported better to the class-1 engines but failed on DS03 engine 10 and reached up to 4.25 pp on DS02 engines 11 and 15 | SUPPORTED WITH QUALIFICATION | `contextual_baseline/*`; `summary/claim_truth_values.csv` | Q is one transparent adversarial control, not a proposed method and not exhaustive. Its abnormal-state side was not evaluated |
| B5 | Past-only regime-conditioned calibration (C′) reduced pooled disparity in 14/14 runs. Its nominal-error results are target-sensitive (DS03 RMS), and its redistribution statement reversed at 0.5% on DS02 | SUPPORTED WITH QUALIFICATION | R2–R5 for C′ | "implementable with current and past samples; not uniformly preferable". Never "online", "causal" or "deployable" |
| B6 | The pooled phase ordering is already present inside the calibration engines (C0). Descent was the highest phase in-sample in 7/7 runs per dataset at 1%, in 27/28 at the other targets, and in 27/28 cross-calibration-engine evaluations | SUPPORTED WITH QUALIFICATION | `support_transport/calibration_phase_effect.csv` | Shows that the pooled effect does not require calibration-to-audit mismatch. Identifies no mechanism |
| B7 | The locked flight-level κ did not transport: the realized pooled healthy-flight false-flag rate was 2.7–31.6% against a nominal 5%, and 57% on one class-1 engine. Locked-point delays therefore compare unequal operating points | SUPPORTED WITH QUALIFICATION | `mssp_mitigation/*/stage_e/healthy_flight_false_flags_with_delay.csv` | Always report the false-flag burden with any delay |
| B8 | Abnormal-state (hs = 0) row alarm rates stayed within the interpretive guardrails (family ratios 0.98–1.16) | SUPPORTED WITH QUALIFICATION | `stage_e/guardrails.csv` | The guardrails are interpretive, not hypothesis-test margins |
| B9 | Flight-class-1 association: calibration contained no class-1 engine. Two of the three class-1 audit engines (DS02 engine 14, DS03 engine 12) became worse calibrated under C in every detector run at 1%; DS03 engine 14 did in 3/7 | DESCRIPTIVE ONLY | `calibration_quality_paired.csv` (per_engine) | "descriptive evidence from three engines". It suggests a calibration-composition/transport problem but does not establish flight class as the causal variable. Flight class was never used to change a rule |
| B10 | Operating-support distance did not explain the residual failures. The median Spearman ρ between same-phase support distance and \|FPR − α\| under C was 0.03 (DS02) and 0.04 (DS03), with leave-one-engine-out sign flips. The largest errors under C lie in in-support climb cells. The pre-specified verdict was INDETERMINATE DUE TO SMALL ENGINE COUNT | DESCRIPTIVE ONLY (a negative result) | `support_transport/support_associations.csv`, `support_cells.csv`; `summary/summary_record.json` | State plainly that nearest-neighbour operating-state distance did NOT explain the failures. Do not upgrade it to proof that support is irrelevant |
| B11 | Per-engine transport failures and exceptions: DS02 engine 14 A2 0.99–3.97 → 3.74–6.59 pp; DS03 engine 12 0.39–0.85 → 0.82–2.17 pp; DS03 engines 10 and 15 worsened in several runs | DESCRIPTIVE ONLY | per-engine metrics | Report every exception, and remove none |
| B12 | Class-specific patterns: class-1 cruise rows lie outside the calibration cruise support (median distance 0.74–1.13; 82–95% of rows outside the range), while class-1 climb rows are in support yet over-alarm under C | DESCRIPTIVE ONLY | `support_cells.csv` | A hypothesis about engine- or flight-profile-level shift only |
| B13 | Low-burden matched-delay pattern: C flagged onset earlier at 2.5–5% realized false-flag burden in most DS02 runs and about half of the DS03 runs, with mostly ties at 10% or more | DESCRIPTIVE ONLY | `matched_delay/matched_false_flag_comparisons.csv` | Three and six engines and no interval. The pre-specified criterion was not met (see C2) |
| B14 | Error decomposition (post-plan, Dev-1): under C, the phase share of equal-cell squared error fell (72% → 14% on DS02; 57% → 5% on DS03), but the equal-cell RMS error did not fall (DS02 0.96 → 1.61 pp; DS03 0.84 → 0.81 pp) | DESCRIPTIVE ONLY | `summary/post_plan_error_decomposition.csv` | Label it post-plan and descriptive. Supplement only, with a one-sentence mention in the main text |

## C. Claims that failed and must not appear

Each of these is **NOT SUPPORTED**. None may appear as a claim in the manuscript, highlights, abstract, captions, cover letter or release notes. It may appear only as an explicitly negated or rejected statement.

| # | Claim that must not appear | Why |
| --- | --- | --- |
| C1 | Phase-conditioned calibration is generally superior (to pooled calibration or to continuous context) | It fails per engine and under equal-engine weighting, and Q is better on some engines |
| C2 | Phase conditioning provides a general detection-delay improvement | "Earlier at matched burden" held in 3/7 (DS02) and 0/7 (DS03) runs for C, and in 4/7 and 2/7 for C′; the pre-specified ≥ 5/7 criterion was not met |
| C3 | Conditioning reduces overall healthy FPR | The overall change was −0.10 to +0.40 pp, and the overall-FPR error improved in only 4/14 runs. Conditioning redistributes healthy alarms |
| C4 | Phase is the physical cause of the calibration instability | No mechanism was identified. Phase is a retrospective stratum |
| C5 | Continuous context conditioning solves the issue | Q failed on DS03 engine 10 and reached up to 4.25 pp on DS02 engines 11 and 15 |
| C6 | Calibration-set composition is proven to be the sole cause, or "the limiting factor" | It is descriptive evidence from three class-1 engines. Required wording: "the strongest observed transport failures coincided with flight classes absent from calibration" |
| C7 | Causal or online superiority, or "causal regime"/"causal LSTM" wording | C′ uses current and past samples only; it is not a causal-inference claim. Retrospective phases are not available in flight |
| C8 | Phase-conditioned thresholds are a transportable calibration fix or a deployment solution | See B3, B9 and B11 |
| C9 | Operating-support mismatch explains the failures | See B10 |
| C10 | Any statistical-significance claim for a post-confirmation paired difference | Every paired interval at 1% includes zero |
| C11 | "Stabilization", "stable calibration", "robust" or "eliminates" wording for the conditioned arms | Disparity reduction is not calibration stability |
| C12 | "Pre-registered", "preregistered", or externally registered analyses | Freezing was internal and recorded in the repository |
| C13 | "Independent confirmation", "independent detectors", or independent reimplementation | DS03 is held out, not independent. The detectors share preprocessing, and no independent reimplementation exists |
| C14 | Any "first" claim | The prior-art audit supports none |

## D. Claims that remain unknown

| # | Question | Class |
| --- | --- | --- |
| D1 | Behaviour on real aircraft (real sensors, real flight profiles, real fault events) | UNKNOWN |
| D2 | Population-level effect magnitude beyond the observed engines | UNKNOWN |
| D3 | Transport with broader calibration fleets (more engines, every flight class represented) | UNKNOWN |
| D4 | The mechanism: why descent is elevated under pooled calibration, and why class-1 climb over-alarms under C | UNKNOWN |
| D5 | Behaviour on unopened N-CMAPSS subsets | UNKNOWN (not opened; protocol L16) |
| D6 | The abnormal-state (detection) side of the continuous baseline Q | UNKNOWN (not evaluated; it would require a new abnormal-row read) |
| D7 | Post-confirmation behaviour of other detectors, corrections or phase definitions | UNKNOWN |
| D8 | Which weighting (row-pooled, equal-engine, per-engine) is operationally relevant | UNKNOWN; it depends on the deployment. All are reported |

## E. Exact novelty claim

> The contribution is not phase-aware detection or regime-specific thresholding themselves. It is the controlled audit of nominal healthy-FPR calibration transport under full-flight operation, including cross-phase threshold transfer, a frozen discovery–confirmation separation, and a post-confirmation demonstration that apparent pooled phase-level correction need not transport across engines.

**Constraints on using it:**
1. **No priority claims.** No "first", "novel framework" or "new method" wording is used for phase-conditioned or regime-specific thresholds.
2. **Name the closest precedents in the text.** The minimum set is Michau and Fink (per-mode FPR under a single-mode calibration), Toshkova *et al.* (MSSP; per-condition alarm thresholds), ProDiMES (fixed false-alarm budget with latency), Lee *et al.* (flight-state thresholds) and Zhao *et al.* 2004 (multimode PCA control limits). Add any paper that the final prior-art audit (`paper/mssp/NOVELTY_POSITIONING.md`) identifies as closer.
3. **The audit can only narrow this claim.** The final prior-art audit may narrow the novelty claim but never broaden it.

## F. Exact scope limitation

> The evidence is limited to two simulated N-CMAPSS subsets (DS02, DS03) from one simulator; two calibration engines per subset; three (DS02) and six (DS03) audit engines, of which four in total belong to a flight class absent from their calibration set (three of them class 1); three residual-based detector families that share one residualization and calibration pipeline; retrospective phase labels that require complete flights; a simulated abnormal-state annotation (hs = 0) rather than discrete real-aircraft fault events; and post-confirmation analyses that were frozen before execution but are exploratory and not part of the DS03 confirmation. There is no real-aircraft validation and no independent implementation.

## Locked terminology

| Use | Instead of / never |
| --- | --- |
| abnormal-state (hs = 0) | fault-state, fault (except in cited titles) |
| past-only LSTM | causal LSTM |
| retrospective phase-conditioned calibration (C) | phase conditioning as a method or mitigation |
| past-only regime-conditioned calibration (C′) | causal regime, online conditioning |
| between-phase disparity (A1, max − min) | calibration improvement, stabilization |
| nominal calibration error (A2 max, A3 RMS, A5 overall) | "better calibrated", unless A2 or A3 supports it |
| healthy flights with any alarm | never merged with the κ-based rate |
| κ-based healthy-flight false-flag rate (FFR) | never merged with "flights with any alarm" |
| held-out DS03, frozen one-shot confirmation | independent confirmatory subset |
| pre-specified; frozen before execution | pre-registered |
| continuous contextual calibration baseline (Q), an adversarial control | proposed method |

**Final abstract sentence (locked).** It is "… the strongest observed transport failures coincided with flight classes absent from calibration." The superseded sentence ("calibration-set composition across flight classes is the limiting factor") must not reappear.

## Amendments

### Amendment 1 (2026-09-28): absent-class engine count

This is a factual correction of wording found while the figures were being rebuilt. No analysis or output changed.

**What was found.** The committed label structure (`results/mssp_mitigation/{ds02,ds03}/stage_b/label_structure.csv`) shows:
- In DS02, every development engine is flight class 3. That covers the model-fitting engines 2, 5, 10 and 16 and the calibration engines 18 and 20. Consequently, DS02 audit engine 14 (class 1) **and audit engine 15 (class 2)** both come from classes absent from calibration.
- In DS03, calibration covers classes 2 and 3 (engines 4 and 8). Class 1 is absent from calibration but present among the model-fitting engines (1, 5, 9). Only class-1 audit engines 12 and 14 are absent-class engines.

**What changed.** Earlier documents wrote "two of three engines from a flight class absent from calibration". That wording is correct only for class 1. Across all absent-class engines, four in total, the outcomes under C were:

| Engine | Outcome under C |
| --- | --- |
| DS02 engine 14 | Worse in 7/7 runs |
| DS03 engine 12 | Worse in 7/7 runs |
| DS03 engine 14 | Worse in 3/7 runs |
| DS02 engine 15 | **Improved** in 7/7 runs (A2 0.66–2.67 → 0.14–0.30 pp; category 1 in 7/7) |

These counts come from `calibration_quality_paired.csv` (per_engine, 1%).

**Rules from now on:**
- Class-1 statements keep the form "two of the three class-1 audit engines".
- Any statement about absent classes must say that four engines came from classes absent from their calibration set, and that not every absent-class engine failed.
- The locked abstract sentence remains accurate: the strongest failures occurred on class-1 engines. No text may imply that every absent-class engine failed.
- Where it is relevant, the text notes that DS02 fitting also lacked classes 1 and 2, whereas DS03 fitting included class 1.
- The scope statement in section F was corrected from "three in total" to "four in total (three of them class 1)".
