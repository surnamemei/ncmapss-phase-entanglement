> **Status (2026-09-28).** Superseded for submission decisions by `docs/mssp/FINAL_SUBMISSION_READINESS.md` and `docs/mssp/FINAL_STORY_LOCK.md`.
>
> **Erratum.** Statements here about engines "from a flight class absent from calibration" should be read as class-1 statements. Amendment 1 of the story lock records that DS02 audit engine 15 (class 2) is also absent from DS02 calibration and improved under C.
>
> **Resolved items.**
> - The two papers previously flagged as unread (Chen 2026, Asaadi 2022) were re-audited at the access level obtainable; see `paper/mssp/NOVELTY_POSITIONING.md`.
> - The earlier note that Chen 2026 "states that no universal threshold fits" is withdrawn.

# Central Claim

**Frozen evidence (unchanged).** Under pooled healthy calibration, full-flight aero-engine anomaly detectors on N-CMAPSS showed phase-dependent healthy false-alarm rates: descent was highest. This was discovered on DS02 and reproduced on the frozen one-shot DS03 confirmation.

**Surviving post-confirmation claim.** Conditioning thresholds on flight phase:
- corrects the population-level phase-composition error;
- reduces between-phase disparity in all 14 runs;
- for the row-pooled audit population, reduces nominal calibration error (A2 in 14/14 runs, A3 in 13/14).

Three limits bound this claim:
- It does not transport across engines: two of three engines from a flight class absent from calibration became worse calibrated in every run at 1%.
- It offers no pre-specified detection-delay improvement at matched false-flag burden. An earlier-detection pattern appears only at low burdens and is descriptive.
- Its failures are not organized by operating-point distance to the calibration data.

**Story selected: B (calibration transport).** The failure axis is engine and flight-class composition of the calibration set, not operating-point support. All paired bootstrap intervals include zero, so every post-confirmation statement is a point-estimate pattern.

# What Changed After Adversarial Validation

| issue | old interpretation | new evidence | final interpretation | manuscript action |
| --- | --- | --- | --- | --- |
| A. Spread metric | "C consistently reduced the phase spread" (outline) | Row-pooled A2 improved in 14/14 runs and A3 in 13/14 (category 1: DS02 7/7 at every target; DS03 7/6/5 of 7). Per engine, class-1 engines worsen. Equal-engine weighting reverses DS02 (category 4 in 5/7) | Disparity reduction is real (point estimates) and, row-pooled, is not only equalization. It is not an engine-level property | The abstract reports disparity and A2 row-pooled; a transport paragraph is added; "stabilization" is never used |
| B. Unequal operating points | Delays reported with the realized FFR of the locked κ | The locked κ did not transport (FFR 2.7–31.6%). At matched burden: DS02 C earlier at 5% in 7/7 runs (median paired difference −7 flights); DS03 earlier in about half the runs at 2.5–5%; mostly ties at 10% or more. Run-level labels: 3/7 and 0/7 "earlier" | No pre-specified delay improvement. There is a descriptive low-burden advantage, and the locked-κ differences mostly reflect operating points | Matched operating characteristic (Fig. 4, Table 4); delay improvement explicitly not claimed |
| C. Support mismatch | "calibration-set composition … central limitations" (untested) | C0: the phase ordering is present inside the calibration engines. Distance ρ has a median of 0.03/0.04, with leave-one-engine-out sign flips (INDETERMINATE). Class-1 cruise is the most distant, but the largest errors are in in-support class-1 climb | The pooled phase effect is not a mismatch artefact. The residual failures are organized by flight class and engine (descriptively), not by operating-point distance | Section 4.8 (C0), Section 4.11 (support), Fig. 5 |
| D. Weak baseline | Phase thresholds only | A continuous quantile-regression threshold on operating descriptors (Q) cut disparity relative to P in 12/14 runs but beat C on row-pooled A2 in only 3/14. It transported better to class-1 engines but failed on class-3 DS03 engine 10 (3.59–7.57 pp) | C remains the better population calibrator. Neither discrete nor continuous conditioning transports across all engines | Section 4.13; Q column in Fig. 3 and Table 3; healthy side only |
| Denominator | Row-pooled only | DS02 A2/A3 sign agreement between row-pooled and equal-engine weighting: 15–16/42 (DS03 36–39/42). Decomposition: the phase share falls from 72% to 14% (DS02) and from 57% to 5% (DS03), but the equal-cell RMS error does not fall | The row-pooled estimand is stated as the target, and the engine-level result is reported beside it | Section 4.10, Fig. 6 |
| Target | 1% only emphasized | Disparity reduction invariant across 0.5/1/2%. C′ RMS error target-sensitive (DS03); C′ redistribution reversed at 0.5% (DS02); matched delay labels reversed or target-sensitive | Target sensitivity is shown | Section 4.14 |

# Hidden Assumptions

1. **Exchangeability within phase.** Per-phase quantiles assume that audit rows of a phase are exchangeable with calibration rows of that phase. This fails for flight classes absent from calibration. Retrospective "cruise" of short flights is a different operating region: 82–95% of class-1 cruise rows lie outside the calibration cruise range.
2. **Retrospective phases.** C uses complete-flight phase labels, which are not available during a flight. Only C′ (past-only regime) is implementable with current and past data.
3. **Oracle healthy labels.** The healthy-state annotation selects the fitting, calibration and healthy-evaluation rows; the onset label is simulated.
4. **Flight-level rule.** κ is estimated from 32 or 40 calibration flights (the second-largest order statistic), so its transport is itself uncertain; the realized audit FFR was 2.7–31.6%.
5. **Engine as the unit.** There are three and six audit engines and two calibration engines, so no interval excludes zero and associations are indeterminate.
6. **Shared preprocessing.** The three detectors share the correction and calibration, so they are not independent replications.
7. **Fixed configuration.** The frozen correction (history basis, ridge 1.0), detector hyperparameters and phase rule are taken as given. Their effect on the conclusions is untested beyond the frozen DS02 sensitivity analyses.

# Fair-Matching Results

- **Candidate grid.** κ candidates came from healthy calibration flights (plus a data-free fixed grid), never from audit or abnormal data. Matching used the nearest realized FFR within one healthy-flight step, with no interpolation or extrapolation. The minimum number of supported anchors at 1% was 3 of 5 (the stop threshold), so no extrapolation was needed.
- **DS02 (C against P).** Earlier at the 2.5% anchor in 5/5 supported runs and at 5% in 7/7 (median paired difference −7 flights). At 10% and above, the results were mostly ties.
- **DS03 (C against P).** At 2.5%: 4 earlier and 1 later of 7. At 5%: 3 earlier and 1 later of 6 supported. At 10% and above: no earlier runs.
- **Pre-specified run labels at 1%.**
  - "Earlier at matched burden": C 3/7 (DS02) and 0/7 (DS03); C′ 4/7 and 2/7. The rest are mixed or equal.
  - Criterion for "improves detection delay" (at least 5/7): **not met**.
- **Curve-level mean delay (2.5–20% FFR), C against P.**
  - DS02: lower in 6/7 runs, by 1.83–4.93 flights; the seventh run (LSTM seed 1) was +0.04.
  - DS03: lower in 6/7 runs, by 0.13–2.56 flights; PCA was 3.09 flights later.
  - C′: lower in 5/7 runs per dataset.
  - This summary averages over the low-burden region where P is slow, so it is consistent with the anchor-level pattern. It is not a pre-specified decision criterion.
- **Locked operating points.** They differed in realized FFR, mostly Pareto trade-offs on DS03. The locked-κ delay differences therefore largely reflected different operating points.

# Metric Robustness

- **Equality versus accuracy.** Validation A shows that the spread reduction coincided with lower max-absolute and RMS nominal error for the row-pooled population (Section 4.9). The spread therefore did not manufacture the result at that level.
- **Engine level.** The same metrics expose the transport failure. DS02 engine 14: A2 went from 0.99–3.97 pp under P to 3.74–6.59 pp under C. DS03 engine 12: 0.39–0.85 to 0.82–2.17 pp.
- **Overall FPR error.** It improved in only 4/14 runs, so conditioning redistributes rather than removes healthy alarms.
- **Paired intervals.** Every paired U1 interval, for A1–A5 and for the equal-engine variants, includes zero at 1% (7 runs × 20 metrics × 2 datasets). At 0.5% and 2%, 558 of 560 do. The exceptions are C′ disparity reductions for DS02 Isolation Forest seeds 0 and 1 at 2%.
- **Endpoint agreement.** "Healthy flights with any alarm" and the κ-based FFR moved in opposite directions in most runs, and row-level abnormal-state alarm rates and flight-level delay often disagree in direction. None of these endpoints substitutes for another.

# Calibration Accuracy vs Phase Equality

**Categories (row-pooled, C against P):**
- DS02: category 1 (equality and accuracy improve) in 7/7 runs at 0.5%, 1% and 2%;
- DS03: 7/7, 6/7 and 5/7.

**C′:**
- DS02: category 1 in 4/7 runs at 0.5%, with 3 runs in category 2;
- DS03: 4, 6 and 5 of 7.

**Wording verdicts under the pre-specified rule:**
- DS02 C: "improved nominal phase-wise calibration" (row-pooled estimand).
- DS03 C, DS02 C′ and DS03 C′: "reduced between-phase disparity" only.

**Engine level and equal-engine weighting:**
- Class-1 engines are in category 4 (conditioning worsens both) in 6/7 runs (DS02 engine 14) and 7/7 runs (DS03 engine 12).
- Under equal-engine weighting, DS02 is in category 4 in 5/7 runs at 1%.

**Decomposition (post-plan Dev-1, equal cell weight):**
- Under P, most error is a phase component (72% and 57%).
- Under C, most error is engine and engine × phase (phase share 14% and 5%), and the total RMS error does not fall (DS02 1.61 against 0.96 pp; DS03 0.81 against 0.84 pp).

# Matched False-Flag Detection Trade-off

- **Summary.** At comparable realized healthy-flight false-flag burden there is no pre-specified detection-delay improvement. The apparent locked-κ advantages primarily reflected more aggressive flight-level operating points, especially on DS03.
- **Low burden (descriptive).** At the lowest burdens (2.5–5%), conditioning tended to flag onset earlier (DS02 consistently; DS03 in about half the runs). This is where a monitoring system targeting rare false flags would operate, but with three or six audit engines it remains descriptive.
- **Row-level rates.** Abnormal-state row alarm-rate ratios stayed at or above 0.9 in every run at every target.

# Operating-Support / Transportability Findings

- **C0.** Descent was the highest pooled-FPR phase in-sample in the calibration engines in 7/7 runs per dataset:
  - DS02: descent 1.92–2.45% against climb 0.04–0.32%;
  - DS03: descent 1.27–1.74% against climb 0.35–0.45%.

  It was also highest in 27/28 other-target combinations and in 27/28 cross-calibration-engine evaluations. The pooled phase effect therefore does not require calibration-to-audit mismatch.
- **Support distance.** Median same-phase distance was 0.74–1.13 for class-1 cruise cells and at most 0.07 for every other cell. For class-1 engines only cruise leaves support, with 82–95% of rows outside the calibration cruise range.
- **Association.** Spearman ρ(support distance, |FPR_C − α|) had a median of 0.03 (DS02) and 0.04 (DS03), and leaving out engine 14 (DS02) or engines 10 or 15 (DS03) flipped the sign.
- **Verdict: INDETERMINATE DUE TO SMALL ENGINE COUNT.** Operating-point distance does not organize the residual failures. The largest errors under C are in in-support cells (DS02 engine 14 climb; DS03 engine 10 climb). The organizing variable is, descriptively, flight class and engine.
- **Transport.** Two of three class-1 audit engines were worse under C in every run at 1%, and the κ lock did not transport either: FFR 2.7–31.6%, and 57% on DS02 engine 14. The story is therefore calibration transport across engines and flight classes, not across operating-point support.

# Stronger Baseline Result

**Run rule.** D ran under the pre-specified rule, because C still reduced disparity in 7/7 runs per dataset.

**Specification** (fixed before execution, no tuning, no phase input):
- Linear quantile regression at level 1 − α on a quadratic response surface of the four calibration-standardized operating descriptors.
- Solved exactly with HiGHS on every fifth healthy calibration row, per run and target.
- The in-sample calibration alarm rate at the 1% target was 0.97–1.03%.

**Results at 1% (healthy side):**
- **Disparity.** Q reduced between-phase disparity relative to P in 12/14 runs.
- **Row-pooled calibration.** Q's maximum phase error beat C's in only 3/14 runs (0/7 DS02, 3/7 DS03).
- **Other targets.** At 0.5% on DS02, Q was worse than P on row-pooled A2 (0.52–2.59 against 0.51–0.76 pp). At 2%, Q had the lowest equal-engine error ranges on both datasets; run-by-run comparisons were not made.
- **Transport.** Q transported better than C to class-1 engines:
  - DS02 engine 14: 0.54–2.20 against 3.74–6.59 pp;
  - DS03 engine 12: 0.40–0.74 against 0.82–2.17 pp.
- **In-class failures.** Q failed where C did not:
  - DS03 class-3 engine 10: 3.59–7.57 pp;
  - DS02 engines 11 and 15: up to 4.25 pp in single runs.
- **Flight-level false flags.** The realized FFR at the calibration κ was 7.9–22.4% (DS02) and 4.1–10.8% (DS03). The DS03 range is closer to the nominal 5% than P's (2.7–16.2%) or C's (2.7–19.6%).

**Verdict.** The continuous baseline does **not** dominate phase conditioning. C remains the better population-level calibrator. Q moves the transport failure to different engines instead of removing it. The phase-conditioned arm is therefore reported as an interpretable diagnostic of phase-composition error, alongside a continuous baseline that fails differently.

**Not evaluated.** Q's abnormal-state endpoints (alarm rates and matched-burden delay) need a new abnormal-row read (plan rule R2). That requires author approval and a separately frozen amendment.

# Configuration Dependence

- **Nominal targets (0.5/1/2%).** Disparity reduction is invariant. Nominal-error reduction is invariant (DS02) or mostly invariant (DS03). C′ nominal-error results are target-sensitive, and the matched delay labels are target-sensitive or reversed.
- **Weighting.** The conclusions depend on the denominator for DS02 but not for DS03.
- **Seeds.** Directions are reported per seed in `summary/seed_consistency.csv`, and family means are descriptive only.
- **Phase definition.**
  - The post-confirmation analyses used the frozen primary phase rule. C′ (a trailing altitude rate) gives similar disparity reduction but weaker and target-sensitive calibration results.
  - The RESS alternative phase rule was examined only in DS02 discovery.
- **Correction.** Only the frozen history correction was evaluated after confirmation.
- **Flight rule.** κ at a nominal 5% was locked. The matched operating characteristic removes the dependence on that choice.

# Generalization

- **Simulated data.** Two simulated N-CMAPSS subsets (DS02, DS03) with the same simulator.
- **Engine coverage.** Three and six audit engines, with two calibration engines each. Flight class 1 is absent from calibration in both.
- **Detectors.** Three detector families that share preprocessing.
- **Not established.** Nothing here establishes real-aircraft validity, other flight-class compositions, or other detectors and corrections.
- **Possible follow-up.** The official archive contains further N-CMAPSS subsets that have not been opened (protocol L16). A separately frozen transport test on one of them is possible but was not done.

# Numerical / Computational Invariance

**Exact reproduction:**
- Rescored healthy score vectors equalled the reproduction-gate fingerprints bit for bit (DS02 and DS03).
- Recomputed Stage D count tables were exact: 1,008 and 1,764 rows, maximum rate difference 0.0.
- Recomputed κ locks were identical.
- Extended U1 frozen-metric summaries reproduced the committed U1 with a maximum absolute difference of 0.0.
- The Stage E trajectory table reproduced every committed per-engine delay: 189 and 378 rows.

**Deterministic re-derivations.** `tests/test_mssp_adversarial.py` (25 tests; 64 in the whole suite, all passing) recomputes Part A metrics and Part B operating points from committed inputs and checks them for exact equality. The number checker re-derives all 70 cited values and is itself run as a test.

**Environment.** Python 3.12.3, torch 2.14.0+cu130 (CUDA required, no CPU fallback), and deterministic cuDNN settings for LSTM scoring. PCA and Isolation Forest are refitted with frozen seeds and verified by fingerprint.

**Integrity.**
- The 186-file frozen baseline manifest verified before and after every run.
- No `hs = 0` row was read after Stage E.
- The plan hash was checked in every run: `d993dd3f…`.

**Deviations from the frozen plan:**
- **Dev-1.** A post-plan descriptive error decomposition, computed from committed Stage D tables only.
- **Dev-2.** Operational definitions of the target-robustness claims (for example, redistribution as |ΔFPR_overall| < 0.5·|ΔA1|). These were fixed in code before execution: module `9c9484dc…` was committed with the outputs.
- **Dev-3.** After all runs, the module gained an output guard confining writes to `results/mssp_adversarial/` and a robustness fix to `outside_range` for phases without query rows (module `0b2db2b4…`). No output was regenerated: every phase had rows, so the committed outputs are unaffected. Each output's run record names the module version that produced it (`9c9484dc…` for A–C and the summary; `086b2ece…` for D and Dev-1), and those versions are committed with their outputs.
- **Plan stop threshold.** The minimum supported-anchor count equalled the plan's stop threshold (3) but did not fall below it.

# Causal-Claim Audit

- **"Causal".** No causal mechanism is claimed. "Causal" appears only in "no causal mechanism" and "not an identified causal model". The past-only regime arm (C′) and the past-only LSTM are never called causal in the causal-inference sense.
- **Phase is not claimed as the physical cause.** C0 shows that the phase ordering exists in-sample, and the support analysis shows that operating-point distance does not explain the residual errors. Mechanisms such as finite sensor response, path dependence, flight-profile shape or simulator structure remain hypotheses.
- **Flight class is descriptive.** It was never used to change a rule.

# Prior-Art Positioning

`paper/mssp/reference_audit.csv` has 96 rows: 48 kept, 35 optional (verified but not cited), and 13 dropped.
- **Verification.** Every kept reference was verified against an abstract or full text that was read. Quotes from the delegated search were machine-checked (97/97 fragments). The three closest precedents were re-checked independently against the saved source text.
- **Unreadable.** Five candidates had readable metadata only. Two could bear directly on Q1–Q2 and **must be read by the author before submission**: Chen *et al.* 2026 (RESS 267:111894; reportedly states that no universal threshold fits multi-condition gas-turbine data) and Asaadi *et al.* 2022 (J. Process Control 114:120–130; alarm assessment for mixture processes).

1. **Has phase or regime-dependent false-alarm calibration been directly studied? Partly.** Condition-specific thresholds, often motivated by false alarms, are established:
   - Toshkova *et al.* 2020, MSSP (per-condition extreme-value thresholds against uniform ones);
   - Clifton *et al.* 2007 (jet-engine speed bins);
   - Wang *et al.* 2025 (aero-engine condition segmentation);
   - Lee *et al.* 2025 (HUMS flight-state thresholds);
   - Zhao *et al.* 2004 (multimode PCA limits);
   - a GE patent with phase-specific severity thresholds (industrial practice; not cited).

   Michau and Fink 2021 report per-mode FPR on simulated turbofan data. **Not found:** an audit showing that a pooled nominal threshold on full-flight engine residuals controls only the exposure-weighted healthy FPR while the climb, cruise, and descent FPRs differ.
2. **Has cross-regime threshold transfer been a primary endpoint? Partly.** Michau and Fink report near-100% FPR when a cruise-only calibration meets other modes, and DCASE work documents domain-dependent thresholds. **Not found:** a per-phase transfer matrix with every phase present in calibration, as a pre-specified endpoint.
3. **Has a discovery → frozen-confirmation audit been used for this question? Not found for aero-engine calibration.**
   - The ProDiMES blind test (Simon *et al.* 2014) is a benchmark-owner hold-out.
   - An acoustic-domain preprint (Mkrtchian 2026) froze a calibration before a forward test.
   - General confirmatory methodology: Wagenmakers *et al.* 2012.
4. **Has stabilization been evaluated jointly with delay and false-flag burden? The joint delay/false-alarm evaluation is established.**
   - ProDiMES: a fixed ≤ 1/1000-flight false-alarm target with detection latency.
   - Alarm-systems FAR/MAR/AAD (Xu *et al.* 2012; Adnan *et al.* 2011).
   - Persistence rules (Nogueira *et al.* 2026).
   - Fleet alert burden (Basora *et al.* 2021).
   - Sequential detection (Basseville and Nikiforov 1993).

   **Not found:** that evaluation combined with the reduction of per-phase healthy-FPR disparity, nominal calibration error, and engine transport across pooled, phase-conditioned, and past-only regime arms.
5. **What is novel after removing prior-art overlap?** No individual ingredient. The novel element is the combination under frozen plans:
   - the quantified exposure-weighting failure of a pooled nominal threshold on full-flight engine residuals, present even within the calibration engines;
   - pre-specified cross-phase transfer;
   - the DS02 → DS03 frozen confirmation;
   - an adversarially validated evaluation of phase conditioning, which shows a population-level calibration gain, an engine-level transport failure for an unrepresented flight class, and no pre-specified delay advantage at matched false-flag burden.

   **Wording:**
   - Never use "first".
   - Use "we did not find in a documented search …".
   - Always name the closest precedents (Michau and Fink; Toshkova *et al.*; Lee *et al.*; ProDiMES).
   - Per-phase thresholds are never presented as a proposed method.

# Top 3 Remaining Reviewer Attacks

1. **"Three and six audit engines and two calibration engines cannot support a transport claim."**
   - Every paired interval includes zero at 1%, and the support association is indeterminate.
   - The class-1 result rests on three engines: two worsened in every run and one in 3/7.
   - *Response:* this is stated as the central limitation, and the result is framed as an evaluation requirement ("calibration sets must represent the flight classes to which thresholds transfer"), not a population estimate.
   - *Would be answered by:* a separately frozen transport test on an unopened N-CMAPSS subset with more engines and flight classes.
2. **"Phase conditioning uses retrospective labels; the implementable arm is weaker, and the continuous alternative's detection cost is unknown."**
   - C′ results are target-sensitive.
   - Q's abnormal-state side needs a new abnormal-row read, which requires author approval.
   - *Response:* C is presented as a diagnostic, not a deployable method. Q is healthy-side only, with that stated.
3. **"The novelty is thin: condition-specific thresholds, per-mode FPR, fixed-budget latency and blind testing all exist."**
   - Precedents: Toshkova *et al.* (MSSP), Michau and Fink, ProDiMES, Lee *et al.*
   - *Response:* the contribution is stated as the combination under frozen plans, the closest precedents are named, and "first" is never used.
   - *Open:* two metadata-only papers (Chen 2026, Asaadi 2022) must be read before submission.

# Claims Removed or Weakened

See `paper/mssp/adversarial_claim_audit.md` §1 and §3. In summary:
- **Stabilization.** Phase-spread reduction is no longer read as stabilization.
- **Delay.** No delay improvement is claimed.
- **Overall FPR.** No reduction in overall FPR is claimed.
- **Transport.** No transportable fix is claimed.
- **C′.** C′ is no longer "causal" or "online".
- **Novelty.** The novelty statement is narrowed because mode-specific control limits predate this work.

# Strongest Surviving Contribution

**A frozen, adversarially validated demonstration.** Pooled healthy calibration of full-flight aero-engine anomaly detectors hides a phase-composition error that is present even within the calibration engines. Phase conditioning removes that error for the audit population but converts it into an engine-level transport error for flight classes absent from calibration.

**An evaluation design that exposes this** (reusable for other monitoring studies):
- frozen stages and exact reproduction gates;
- calibration-accuracy metrics alongside disparity;
- engine-weighted reporting;
- detection delay compared at matched false-flag burden.

# Minimum Remaining Work Before MSSP Submission

1. **Author decisions on the rescope.**
   - Story B (calibration transport) and the title. Candidates:
     1. **(recommended)** *Phase-Dependent False-Alarm Calibration and Its Transport Across Engines in Full-Flight Aero-Engine Anomaly Detection.*
     2. *Phase-Dependent False-Alarm Calibration in Full-Flight Aero-Engine Anomaly Detection under Nonstationary Operating Conditions* (the author's earlier choice; still accurate but silent on transport).
     3. *Why Phase-Conditioned Thresholds Do Not Transport: False-Alarm Calibration in Full-Flight Aero-Engine Anomaly Detection* (cautionary; slightly overstates, since the population-level gain is real).
     4. *Population Gains and Engine-Level Transport Failures of Phase-Conditioned Alarm Thresholds in Aero-Engine Anomaly Detection.*
   - None of the candidates uses "robust", "mitigation", "causal", "fault detection", or "general".
   - Approval of the 37 new references, and the post-plan decomposition (Dev-1).
2. **Two unread papers.** Read Chen *et al.* 2026 (RESS 267:111894) and Asaadi *et al.* 2022 (J. Process Control 114:120–130) and adjust the positioning if either studies a pooled threshold over operating modes directly.
3. **Submission items.**
   - An MSSP cover letter.
   - Declarations: competing interests, CRediT, generative-AI use, funding.
   - A data and code availability statement with an archived release. It is the author's decision whether to create a new MSSP release; the RESS tags are not to be reused.
   - A supplementary-material PDF describing S1–S9, S10–S16, and the adversarial evidence tables.
4. **Rebuild.** Regenerate `paper/mssp/latex/main.pdf` with `build_latex.py` after the author's text edits. `verify_draft_numbers.py` must pass before upload.
5. **Pushing.** Push `mssp-revision` and the annotated tag `ress-submission-2026-09-25`. This session has no credentials.
6. **Optional (strengthening, not required).**
   - An author-approved, separately frozen abnormal-row read to evaluate Q's abnormal-state endpoints.
   - A frozen transport test on an unopened N-CMAPSS subset.

# Overall Status

**NEEDS MINOR MANUSCRIPT WORK**

**Science.** The adversarial validation is complete, and its results are committed with exact reproduction checks. The story has already been rescoped from a mitigation claim to a calibration-transport claim (Story B), and every number and citation is machine-checked.

**Remaining work.** It is author review and submission paperwork: the rescope and title approval, two papers to read, a cover letter, declarations, and an archived release. The main scientific weakness, the small number of engines, is disclosed, and it cannot be fixed without new data. The optional focused validations would strengthen the paper, but the current claims do not depend on them.

| issue | old interpretation | new evidence | final interpretation | manuscript action |
| --- | --- | --- | --- | --- |
| Spread metric (A) | C "consistently reduced spread" | Row-pooled A2 improved in 14/14 runs and A3 in 13/14; engine level fails; equal-engine weighting reverses DS02 | Real population-level calibration gain; not an engine-level property | Disparity and A2 reported; the "stabilization" wording removed |
| Unequal operating points (B) | Delays paired with realized FFR | Matched: no pre-specified improvement; earlier only at 2.5–5% (descriptive); the locked κ did not transport (FFR 2.7–31.6%) | No delay-improvement claim | Matched operating characteristic (Fig. 4, Table 4) |
| Support mismatch (C) | Untested "calibration-set composition" | C0: the phase effect is present in-sample; distance ρ ≈ 0.03–0.04 (INDETERMINATE); errors sit in in-support class-1 climb cells | The phase effect is not a mismatch artefact; transport fails by flight class and engine, not by operating-point distance | Sections 4.8 and 4.11; Fig. 5 |
| Stronger baseline (D) | None | Q beats C in 3/14 runs; better on class 1, fails on DS03 engine 10 | Neither discrete nor continuous conditioning transports | Section 4.13; Q in Fig. 3 and Table 3 |
| Target and denominator | 1%, row-pooled | Disparity reduction invariant; C′ and the delay labels target-sensitive; DS02 weighting-dependent | Estimands and sensitivities stated | Section 4.14 |
| Prior art | "The gap" framed broadly | Michau & Fink, Toshkova (MSSP), ProDiMES, Lee, GE patent | Novelty only as the frozen, adversarially checked combination | Positioning paragraph rewritten; 16 new references |
