> **Status (2026-09-28).** This audit precedes the final story lock. The binding interpretation is `docs/mssp/FINAL_STORY_LOCK.md`, including Amendment 1: four audit engines came from flight classes absent from calibration, and the DS02 class-2 engine improved. The final manuscript is `manuscript_mssp_draft.md`.

# Adversarial claim audit (MSSP draft v2)

**Date.** 2026-09-28.

**Evidence base:**
- frozen DS02/DS03 results (evidence IDs);
- the post-confirmation analysis (frozen protocol v1.0);
- the adversarial validation (frozen plan, commit `39a5f81`).

`paper/mssp/verify_draft_numbers.py` re-derives every number and checks it verbatim in `manuscript_mssp_draft.md`.

**Status legend:**
- **SUPPORTED:** holds under the pre-specified rule, at every target and denominator checked;
- **SUPPORTED WITH QUALIFICATION:** holds for the stated estimand, with a stated qualification;
- **DESCRIPTIVE ONLY:** a pattern with no inferential support, or post-plan;
- **NOT SUPPORTED:** fails its pre-specified rule;
- **REMOVE:** wording withdrawn from the manuscript.

## 1. Headline claims

| # | Claim | Status | Evidence (source) | Manuscript wording |
| --- | --- | --- | --- | --- |
| 1 | Under pooled calibration, healthy FPR depended on flight phase; descent was highest (DS02 discovery) | SUPPORTED (frozen, exploratory) | E000107–E000109 and the family means; invariant across the 0.5/1/2% targets (`summary/robustness_classification.csv`, R1) | Unchanged frozen text |
| 2 | The pre-specified pooled directional pattern was reproduced on DS03 | SUPPORTED (frozen verdict) | Frozen confirmation. The 3/42 per-engine exceptions and the LSTM descent-minus-cruise intervals are reported | Verbatim frozen verdict. Never qualified by later results (F4) |
| 3 | The tested corrections did not sufficiently attenuate the dependence | SUPPORTED (DS02 PCA, exploratory) | Contrasts +2.854/+3.045/+3.335 pp; they did not shrink | "did not sufficiently attenuate"; the clause "remained positive … did not shrink" is kept |
| 4 | The pooled phase effect is not produced by calibration-to-audit support mismatch | SUPPORTED WITH QUALIFICATION | C0: descent was the highest phase in-sample in 7/7 runs per dataset, in 27/28 other-target combinations, and in 27/28 cross-calibration-engine evaluations (`calibration_phase_effect.csv`) | "The same ordering appeared within calibration engines". The qualification: this concerns the tested corrections and detectors; no mechanism is identified |
| 5 | Phase-conditioned calibration (C) reduced between-phase disparity | SUPPORTED (point estimates) | 14/14 runs at 1%; invariant across targets. All 28 paired U1 intervals include zero | "reduced between-phase disparity in all 14 detector runs … all paired bootstrap intervals included zero" |
| 6 | C improved nominal calibration (not only equalization) | SUPPORTED WITH QUALIFICATION (row-pooled estimand) | Row-pooled A2 improved in 14/14 runs and A3 in 13/14. Category 1: DS02 7/7 at every target; DS03 7/6/5 of 7. The pre-specified wording rule allows "improved nominal phase-wise calibration" for DS02 C only. Every paired U1 interval includes zero | "For the pooled audit population …". DS03 and C′ are worded "reduced between-phase disparity" |
| 7 | C improves calibration for individual engines | NOT SUPPORTED | Class-1 engines: DS02 engine 14 and DS03 engine 12 were worse in 7/7 runs at 1%. Equal-engine weighting in DS02 gave category 4 in 5/7 runs at 1%. The decomposition (post-plan) shows the phase error converted into engine and interaction error | "The gains did not transport across engines" |
| 8 | Conditioning reduced overall healthy FPR | NOT SUPPORTED → REMOVE | Change −0.10 to +0.40 pp; the overall error improved in only 4/14 runs | "mainly redistributed healthy alarms across phases" |
| 9 | Conditioning improves detection delay | NOT SUPPORTED (pre-specified rule) | "Earlier at matched burden" in 3/7 (DS02) and 0/7 (DS03) runs for C, and 4/7 and 2/7 for C′; the rule required at least 5/7 | "the pre-specified criterion for a delay improvement was not met" |
| 10 | At low matched false-flag burden, conditioning detected earlier | DESCRIPTIVE ONLY | Per-anchor outputs: DS02 7/7 runs earlier at 5% (median −7 flights) and 5/5 at 2.5%; DS03 4/7 at 2.5% (one later) and 3/6 at 5% (one later); differences vanish at 10% or more. There are 3/6 audit engines and no interval | "earlier mainly at low burdens (2.5–5%; …)" |
| 11 | Locked-κ delay differences reflect operating points | SUPPORTED WITH QUALIFICATION | The locked κ did not transport: realized FFR 2.7–31.6% against 5% nominal, and 57% on one class-1 engine. DS03 locked comparisons were mostly Pareto trade-offs | "Delays at the locked points therefore compared arms at unequal operating points" |
| 12 | Abnormal-state alarm rates were not reduced by conditioning | SUPPORTED WITH QUALIFICATION | Guardrail ratios 0.98–1.16; the ≥ 0.9 ratio per run is invariant across targets. The guardrails are interpretive, not test margins | "stayed within the interpretive guardrails" |
| 13 | Operating-support mismatch organizes the failures | NOT SUPPORTED | Median ρ 0.03 (DS02) and 0.04 (DS03); leave-one-engine-out sign flips; class-1 cruise cells are the most distant, but the largest errors are in in-support climb cells. The verdict was INDETERMINATE DUE TO SMALL ENGINE COUNT | "Operating-point distance to calibration data did not explain residual errors" |
| 14 | Flight class organizes the failures | DESCRIPTIVE ONLY | 2/3 class-1 engines were worse in every run at 1%; DS03 class-3 engine 10 also worsened in 3/7 runs | Flight class is described as a descriptive attribute and never used to change a rule |
| 15 | Past-only regime conditioning (C′) is implementable and comparable to C | SUPPORTED WITH QUALIFICATION | C′ reduced disparity in 14/14 runs; its nominal-calibration results are target-sensitive (DS03 RMS) and its redistribution statement reversed at 0.5% on DS02 | "implementable alternative"; never "online", "deployable" or "causal" |
| 16 | A continuous operating-context threshold outperforms phase conditioning | NOT SUPPORTED (healthy side); DESCRIPTIVE for transport | Q reduced disparity relative to P in 12/14 runs, but beat C on row-pooled A2 in only 3/14 (0/7 DS02). It transported better to class-1 engines (DS02 engine 14: 0.54–2.20 against C 3.74–6.59 pp; DS03 engine 12: 0.40–0.74 against 0.82–2.17 pp) but failed on class-3 DS03 engine 10 (3.59–7.57 pp). Abnormal-state side not evaluated (plan rule R2) | "Conditioning on continuous operating state therefore did not solve transport either; the two approaches failed on different engines" |
| 17 | Phase-conditioned thresholds are a transportable fix | NOT SUPPORTED → REMOVE | Claims 7 and 13 | "a diagnostic of phase-composition error rather than a transportable calibration fix" |

## 2. Word audit

| Word | Decision | Current use in the draft |
| --- | --- | --- |
| stable, stabilization | **Weakened.** A spread reduction alone is never called "stabilization". Row-pooled nominal calibration improved only for DS02 C (claim 6) | "stable" appears only in a research question; "stabilization" is absent |
| robust | **Removed as a claim.** Used only to name the robustness checks ("robustness to the nominal target and the denominator") | No robustness claim is made |
| general | Not used | — |
| independent | **Restricted.** DS03 is "held-out", not "independent", and the detectors are "non-independent" | Used in negations only |
| causal | **Restricted.** C′ is the "past-only regime arm"; the LSTM is "past-only"; "causal" appears only in "no causal mechanism" and "not an identified causal model" | The data identifier `causal_regime` is kept in tables only |
| mechanism | Negated only | "identifies no causal mechanism" |
| mitigation | **Removed** from the manuscript text; conditioning is described, not called a mitigation | Only in the output path name `results/mssp_mitigation/` |
| improvement, improve | **Restricted** to claims 6 and 10 with their qualifications; claims 7, 8 and 9 are stated as not supported | See claims 6–10 |
| superior | Negated only | "not evidence that an alternative threshold policy is superior" |
| transportable | **Used negatively:** the thresholds did not transport | Claims 7, 13 and 17 |
| deployable, deployment | Negated only | "does not validate deployment on aircraft" |
| online | Not used; C′ is "implementable with current and past data" | — |
| fault | "Abnormal-state ($hs = 0$)" throughout; "fault" is kept only for a prior-literature title | — |
| sensitivity | Used only in "phase-rule sensitivity" (the frozen section name) and "target-sensitive" | "fault sensitivity" is removed |
| confirmation | Used only for the frozen DS03 confirmation and in "post-confirmation" | Never used for the mitigation or the adversarial results |

## 3. Claims removed or weakened relative to the outline (commit `6b85148`)

1. **Disparity versus stability.** "Phase-conditioned calibration reduced the point-estimate phase spread …" is kept. Any reading of it as stabilization or improved calibration stability is removed, except for the qualified row-pooled DS02 statement.
2. **Delay.** "Detection delays, however, were obtained at realized healthy-flight false-flag rates of 2.7–31.6%" is kept. The matched-burden comparison (claims 9 and 10) is added, and no delay advantage is claimed.
3. **C′ wording.** "Causal conditioning was implementable in the benchmark but not uniformly preferable" becomes "past-only regime conditioning is an implementable alternative". "Causal" is removed.
4. **Title.** "Phase-Dependent False-Alarm Calibration in Full-Flight Aero-Engine Anomaly Detection under Nonstationary Operating Conditions" gets a recommended alternative that names engine-level transport (the author decides).
5. **Novelty.** Novelty statements are narrowed: mode-specific control limits predate this work [N8]. The contribution is the frozen evaluation of phase conditioning's population-versus-engine calibration and its matched-burden detection trade-off, not the conditioning idea.
