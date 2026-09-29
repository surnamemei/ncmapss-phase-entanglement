# Hostile extension review (brief §27)

**Date.** 2026-09-28.

**Reviewed version.** Commit `80d2d5d`: the extended manuscript `paper/mssp_extended/`, with its figures, tables, supplement and cover letter, together with the frozen protocol and all committed outputs.

**Panel.** Four reviewers worked independently and in parallel. Each was a separate agent with read-only access to the repository:
- the MSSP handling editor;
- a PHM (aero-engine health monitoring) specialist;
- a statistical reviewer;
- an industrial alarm-system reviewer.

**Instructions.** Each reviewer:
- answered the eight questions of brief §27;
- listed at most five substantive concerns (no nitpicks, as the author asked);
- gave a recommendation and a verdict.

The reviewers could read every committed text, CSV and JSON file. The statistical reviewer could also run read-only Python on the outputs. No reviewer opened N-CMAPSS data.

**Record of the reviews.** The reviews are reproduced below, lightly condensed; every number they cite is theirs. Section 3 lists the reviewer claims that were independently re-checked against committed outputs before being acted on.

**Result.**
- **Unanimous verdict: ONE FINAL FOCUSED GAP.**
- **Recommendation:** major revision as the paper stood (the statistical reviewer: minor revision once the gap is closed).
- **Text corrections:** these, and post hoc checks computed only from committed outputs, were applied in the revision that follows this review (Section 5).
- **Not run:** the focused validation that needs the saved models to rescore the audit engines. It awaits the author's decision (Section 6).

## 1. Data and paper check (before the reviews)

The check was run against commit `80d2d5d`. No N-CMAPSS file was read; every check uses committed outputs.

| Check | Method | Result |
| --- | --- | --- |
| Engine roles | Fit, calibration and audit pools pairwise disjoint; fit and calibration pools drawn from development engines; audit pool = official test engines; validation engine inside the fit pool (all 9 subsets) | Pass (9/9) |
| Lock before opening | Every new-subset lock committed (`b9786ce`, 13:10Z) before its one-shot marker (15:21Z–15:35Z); the lock SHA-256 in the audit record equals the committed lock file | Pass (7/7). The DS02/DS03 reference locks were written in the reference run after all new locks and before any new audit, as protocol §10 specifies (no one-shot gating for data the frozen study had already opened) |
| Outputs written once | Commits touching `results/extension/<subset>/audit/` | Exactly one (`4e7a45f`) for every new subset |
| Calibration sanity | In-sample FPR on calibration rows at 1% | P: 1.000% overall in every run. C: 1.000% in every phase and run. Q: 0.97–1.05% overall. The large out-of-sample errors (e.g. PCA on DS05/DS06 under C and Q) are transport failures, not threshold errors |
| Independent recomputation | H1, H2, H3 (C and Q), H5 and H6 recomputed from the raw per-subset CSVs, bypassing the summary tables | Identical to `decisions.json`: H1 3/5 families; H2 65.7% of cells; H3 U = 14.3% and any-worse 85.7% for both C and Q; H5 5/5; H6 medians 13.0/13.0/14.3% and 63/69/69% of cells, 3/4/4 families |
| Composition endpoint | CE1 (Δcov) for DS01 recomputed from the raw per-design metrics (draw means, single-engine designs) | Largest absolute difference from the committed values: 1.0e-16 |
| Frozen evidence | 186-file frozen baseline manifest; tags `v1.0.0`, `ress-submission-2026-09-25`, `mssp-pre-extension-2026-09-28`; pre-extension manuscript sources and built outputs | Unchanged. Pass |
| Manuscript numbers | `paper/mssp_extended/verify_numbers.py` | Pass. 47 claims rebuilt and found verbatim; every decimal and percentage in the abstract, highlights and Sections 4–6 sourced; wording lock; citations; source files still carry the SHA-256 recorded in the evidence ledger |
| Build | PDF, flat upload source, supplement, cover letter | Pass. PDF 18 pages (limit 25); the flat source compiles on its own to the same page count; supplement 38 pages; cover letter 1 page |
| Tests | Full suite | 130/130 in 165 s |

**Disclosure.** One extension commit (`e6b6a85`) made additive updates to the literature records in `paper/mssp/`:
- the reference-audit rows for Chen 2026 and Asaadi 2025 were upgraded to full text;
- the novelty positioning was updated;
- full-text quote files were added.

The pre-extension manuscript text and all of its built outputs are unchanged.

**Conclusion of the check.** The data handling, the one-shot discipline and the numbers are sound. The reviewers' concerns (below) are about what the numbers mean, not whether they are right. Every reviewer who spot-checked numbers found that they matched.

## 2. The four reviews

### 2.1 MSSP handling editor. Verdict: ONE FINAL FOCUSED GAP

1. **Strongest contribution.**
   - The per-engine audit is engine-disjoint, locked before outcomes and one-shot, with reproduction gates and a public evidence ledger; this rigour is rare in MSSP/PHM work.
   - Three findings are credible and useful:
     - context conditioning can badly degrade calibration (PCA on DS05/DS06);
     - large failures occur even for covered classes (DS08a engine 14);
     - class coverage matters for phase-conditioned thresholds at fixed volume.
   - An undersold benchmark fact: the N-CMAPSS subsets reuse one flight library.
2. **Strongest rejection reason.**
   - *At the desk:* existing detectors and thresholds applied to one simulated benchmark, with a mostly negative result — a "case study".
   - *At review:* the headline is never compared with what finite samples would produce under perfect transport, so it may be largely guaranteed by construction.
3. **Baselines.**
   - The detectors are adequate. The calibration baselines are not:
     - C is a non-causal oracle;
     - Q extrapolates badly;
     - the CVAE is fragile (variance floor up to 74%; seeds differ tenfold).
   - The CVAE is compared with the best residual detector, not the median one.
   - The obvious practitioner baseline, per-unit recalibration, is absent.
4. **Generalization.** As good as N-CMAPSS allows. The effective sample is small, and claims outside N-CMAPSS have no evidence behind them.
5. **Fair matching.**
   - Delay is matched on pooled burden, which sits oddly with a paper about per-engine burden.
   - Early sensitivity is at the false-alarm floor, so "no delay advantage" means inconclusive.
   - The composition volume contrast is trivial, and coverage is confounded with engine identity and shared missions.
6. **Positive message.** Thin. The most actionable finding — conditioning can make per-unit calibration much worse, so it needs held-out per-unit checks — is buried.
7. **Scope.** Coherent in theme but overloaded (five RQs, seven hypotheses, five stories, S1–S5). Table 4's codes are undefined in the text.
8. **More experiments.**
   - *Necessary before submission:* a post hoc reference distribution for the per-engine endpoints (within-engine split calibration; a binomial null for worst-engine FFR).
   - *Likely in revision:* a causal per-unit recalibration arm.
   - *Nice to have:* real fleet data; a second condition-aware model.
   - *Worthless:* more subsets, seeds or targets.

**Major concerns.**
- **M1. No null reference.** Per-engine sampling noise, strict "every engine"/"worst engine" rules, and in-sample phase error under P counted as transport.
- **M2. A2 conflates shift, disparity and direction.** DS08c is a uniform shift; about half the material errors are under-alarming; H1 is knife-edge.
- **M3. The volume arm cannot support "more data did not substitute for coverage".** Same-class engines share recorded missions.
- **M4. Weak comparators and no remedy tested.**
- **M5. Venue fit and external validity.** Scope all claims to N-CMAPSS. State that the freeze is internal, not external preregistration.

**Likely decision as submitted.** Roughly even odds of desk rejection; otherwise major revision.

### 2.2 PHM specialist. Verdict: ONE FINAL FOCUSED GAP

1. **Strongest contribution.**
   - Engine-disjoint locks from metadata alone, across every readable subset.
   - Pooled summaries mislead: C cut pooled disparity in 66% of cells but was a coin flip at the engine level (about half of engines improved).
   - C worsened every uncovered class-2 engine in DS08c.
   - The coverage effect under C (0.55 pp) is mechanistically sensible.
2. **Strongest rejection reason.** No sampling-noise reference for per-engine and worst-engine endpoints with 14–36 healthy flights per engine. A perfect-calibration null reaches WE-FFR ≥ 10% with probability 0.4–0.7 per cell.
3. **Baselines.**
   - The residual detectors are credible.
   - LSTM epoch selection in DS01 and DS08c monitored a validation engine with standardized MSE of 138–234, against 0.07–0.19 elsewhere.
   - The CVAE is not a fair stand-in for condition-aware models: a single untuned variant, no KL term in the score, a variance floor, lower detection, and compared with the best of three residual detectors.
   - There is no per-engine baseline.
4. **Generalization.**
   - As broad as N-CMAPSS allows.
   - H1 depends on counting under-alarming; with an over-alarming criterion only F4 holds.
   - "Engine" heterogeneity in N-CMAPSS is only initial health plus recorded missions.
5. **Fair matching.**
   - The delay matching is carefully built but uninformative: first-10-flight abnormal-state alarm rates of 0.6–2.1%.
   - "Fixed volume" is random row thinning, so the volume effect is about zero by construction.
   - The balanced design beats the *mean* single engine by convexity, but the *best* single engine in only 7/42 (P) and 11/42 (C) runs.
6. **Positive message.** Weak. The lever the data do support: never apply per-context thresholds to classes or missions absent from calibration.
7. **Scope.** Overloaded; lead with engine transport and coverage.
8. **More experiments.**
   - *Necessary:* a noise floor (binomial FFR plus split-half self-calibration); a flight-level decomposition of covered-class failures.
   - *Text:* the volume claim, H1/DS08c, the DS08a mechanism, the CVAE highlight.

**Major concerns.**
1. **No noise floor, and error sources conflated.** In-sample error, transport, flight noise and sign.
2. **Mechanism misattributed.** DS08a engine 14's covered-class failure comes from one flight whose altitude span exceeds every fit and calibration flight. It is mission or envelope coverage, not engine-specific drift.
3. **The composition design cannot test "more data" or isolate coverage.**
4. **Detection capability and realism.** Delay largely measures false-flag timing; the operating points are far from practice.
5. **The CVAE result is over-generalized, and there is no per-engine baseline.**

**Spot checks.** Every number checked matched the committed outputs.

**Recommendation.** Major revision.

### 2.3 Statistical reviewer. Verdict: ONE FINAL FOCUSED GAP

1. **Strongest contribution.**
   - Exemplary confirmatory discipline; the verifier passes; no misapplied rule was found.
   - Most robust result: class coverage for C. Same-class calibration won in 10/10 runs in all six eligible subsets and in 67/80 pairwise engine comparisons.
2. **Strongest rejection reason.** No comparison with perfect transport. With 4–6 audit engines × 14–36 flights, "every engine improved", "worst-engine A2 ≥ 0.5α" and "WE-FFR ≥ 10%" fire often from noise alone, so H3/H5/H6 and M-C were close to foregone.
3. **Baselines.**
   - Adequate for auditing common practice, not for general claims.
   - The CVAE degenerated in places; Q extrapolates.
   - Class-conditional and per-unit recalibration baselines are absent.
4. **Generalization.** F3 is near-duplicate, and 45–77% of new flight signatures also occur in DS02/DS03. "Reproduced across N-CMAPSS families" is defensible; "generalizes" is not.
5. **Fair matching.**
   - The delay matching is sound at pooled level, but burden is matched pooled, not per engine.
   - Labels are coarse, and the direction is lopsided (C never later; Q earlier 83 times against 6 later).
   - "Volume" is varied only by thinning one engine's rows.
6. **Positive message.** Modest. Coverage halves C's error but leaves 17/26 engines at or above 0.5 pp. Q wins delay by concentrating false flags.
7. **Scope.** The core is coherent, but the story machinery buries the strong results. H1's estimand is loose.
8. **More experiments.**
   - *Necessary:* a noise reference for A2, WE-A2 and WE-FFR; a rerun of the bootstraps that respects the class-covering design.
   - *Nice to have:* class-conditional and per-unit baselines, coverage split by shared signatures, an engine-adding volume contrast, a second CVAE.

**Major concerns.**
- **M1. No noise floor; the failure rules are nearly unfalsifiable.**
  - H3: 14% every-engine-improved against 5.6% under no effect.
  - H6: null P(WE-FFR ≥ 10%) 0.41–0.69 per cell.
  - A2: about 9–22 of 30 engines would cross 0.5 pp under perfect transport.
- **M2. Knife-edge verdicts.**
  - H1 is exactly 3/5 and changes with the target.
  - H4 needs F1 and F2 at exactly 7/10 runs under P.
  - Seeds are near-replicates, not independent votes.
- **M3. The composition does not isolate class coverage.**
  - Engine identity matters where it can be separated (DS04, DS08a).
  - Under P, same-class engines win only 41/80 pairs, and the effect is confined to class-1 audit engines, which share many recorded missions with their same-class calibration engine.
  - The volume effect, and hence "beyond volume", is automatic.
  - The balanced design rarely beats the best single engine.
- **M4. The uncertainty machinery does not match the design.**
  - The per-subset bootstrap resamples calibration engines without class stratification, so most replicates in DS01/DS05–07 omit a class and impose the harmful intervention.
  - With one calibration engine per class, between-engine variability is not estimable.
  - The CVAE should be compared with each residual detector (0.24 pp above the median one).
- **M5. A2 lumps together different failures.** It includes in-sample pooling error and is blind to sign (53% (P) and 48% (C) of material errors are under-alarming).

**Claims not supported as written.**
- "No calibration tested kept its nominal false-alarm rate on every held-out engine" (highlight) and "in any family" (§5.1). DS04 kept every engine within tolerance in several runs.
- The 14% every-engine share offered as evidence of non-transport.
- "Material phase-conditional miscalibration in three of five families". F5 is a level shift.
- Coverage claimed for P.
- "More calibration data from other classes did not substitute for coverage", and "coverage is necessary".
- "No delay advantage" instead of "no advantage meeting the pre-specified criterion".
- "Not an artefact of unequal operating points" (§5.1).

**Recommendation.** Major revision; minor once M1 is done and the text is corrected.

### 2.4 Industrial alarm-system reviewer. Verdict: ONE FINAL FOCUSED GAP

1. **Strongest contribution.**
   - A protocol-frozen, engine-disjoint audit with per-unit error as the endpoint.
   - A "do-no-harm" warning for mode-specific thresholds: conditioning helped every engine in only 14% of cells and badly worsened PCA on DS05/DS06.
   - The fixed-volume coverage design is credible for C.
2. **Strongest rejection reason.** The operational layer is neither representative of practice nor compared with a null. With 14–36 healthy flights per engine, a perfectly calibrated fleet shows a median worst engine of about 9.5% (observed 13.0%).
3. **Baselines.**
   - The detectors are adequate for an audit.
   - The threshold and alarm policies are not:
     - Q is an unregularized 99th-percentile polynomial quantile regression;
     - per-unit baseline recalibration is absent;
     - flight-to-flight confirmation (k-of-n, EWMA/CUSUM on flight statistics) is absent.
4. **Generalization.**
   - The calibration claim is adequate within N-CMAPSS.
   - The alarm-policy claim is not: anchors of 2.5–20% of flights flagged are far above practice, and per-engine tests on about 25 flights have low power.
5. **Fair matching.** The principle is sound, but burden is matched pooled rather than per engine, and delay is measured where there is little signal, so "no delay advantage" is a low-power null.
6. **Positive message.** Present but thin. The paper's own outputs point to a stronger, untested message: flight-level confirmation and per-unit re-baselining.
7. **Scope.** Coherent as an audit, but the decision is post-flight while persistence is modelled as 3-s on-delays inside flights.
8. **More experiments.**
   - *Necessary:* null or noise references; rescoping or adding flight-level k-of-n confirmation at matched burden; a per-unit recalibration positive control. All can run on existing flight-level outputs or calibration-only data.

**Major concerns.**
- **M1. No null reference for burden metrics.** The H6 rule barely discriminates, and most of P's excess is a pooled κ shift.
- **M2. The persistence rules act at the wrong time scale.** A two-consecutive-flight rule at locked κ removes most healthy flight-level burden under P (worst engine zero in 36/49 cells), at a median delay of 17 instead of 10 flights; Q still fails.
- **M3. Matched-delay burden is pooled and power is low.**
- **M4. No positive control or practitioner remedy.**
- **M5. Burden is not scoped to practice.** State it in fleet units; restrict the coverage recommendation to regime-specific thresholds.

**Recommendation.** Major revision.

## 3. Reviewer claims re-checked before acting on them

Every claim below was recomputed from committed outputs only. The computations are in `paper/mssp_extended/post_hoc_checks.py`, with outputs in `paper/mssp_extended/evidence/post_hoc_checks.json`. They are post hoc and change no pre-specified decision.

| Reviewer claim | Re-check (new cohort, residual runs, α = 1%) | Status |
| --- | --- | --- |
| A perfectly calibrated fleet already shows high worst-engine FFR | Independent binomial flagging with κ-sampling: median worst engine 8.6–11.8%; P(≥ 10%) 0.41–0.69 per cell. The observed worst engine under P exceeds the null's 95th percentile in 0/7 runs in DS01, DS04, DS07 and DS08c, and in 1–3/7 in DS05, DS06 and DS08a | Confirmed. The flight-level H6 excess is mostly within noise |
| Per-engine A2 has a noise floor near the 0.5 pp line | Clustered design effect scaled to phases. Null P(A2 ≥ 0.5 pp): 31% (P), 30% (C), 49% (Q). Observed: 87%, 80%, 82%. Above the null 95th percentile: 60%, 49%, 58%. Median SE of an engine's overall FPR: 0.15 pp | Confirmed. The aggregate excess is real; individual engines near the line are not |
| About half of material errors are under-alarming | P 53%, C 48%, Q 38%. All of DS08c, most of DS04 and DS07, none in DS01 | Confirmed |
| "Every engine improved" is a strict-dominance rule | Mean share of engines improved per cell: 50% (C), 49% (Q). Coin-flip expectation of every engine improving: 5.6%, against 14% observed | Confirmed |
| DS08a engine 14 is one out-of-envelope flight | Flight 3 carries 65% of healthy alarms under P. Without it, FPR falls from 2.70% to 1.00%. Its altitude span of 32,029 ft exceeds every fit (≤ 28,051 ft) and calibration (≤ 30,033 ft) flight; it is the only DS08a audit flight above the calibration envelope | Confirmed. The manuscript's mechanism was corrected |
| Coverage partly means shared missions | Same-class audit–calibration pairs share 35–56% (class 1) and 5–20% (classes 2–3) of healthy flight profiles; different-class pairs share none | Confirmed |
| Under P, the coverage effect is confined to class 1 | Median per-engine Δcov under P: +0.11 pp (class 1), −0.09 (class 2), −0.08 (class 3). Under C: +0.64, +0.08, +0.70 pp | Confirmed |
| The balanced design mostly measures averaging | Beats the best single engine in 7/42 (P) and 11/42 (C) residual runs; beats the mean single engine in 42/42 (P) and 35/42 (C) | Confirmed |
| The volume contrast is automatic | Protocol §7: the N-row designs thin rows across the same engine's flights | Confirmed (by design) |
| The bootstrap omits calibration classes | Design-based probability that a replicate omits a class: 78% (DS01, DS05–07), 33% (DS04), 42% (DS08a), 0 (DS08c) | Confirmed |
| The CVAE is near the median residual detector | CVAE minus median residual ME-A2(P): 0.24 pp (median over families). Lower in F1 | Confirmed |
| DS04 kept every engine within tolerance in some runs | Every audit engine < 0.5 pp in 4/7 residual runs under Q, and in 1/7 under P and under C | Confirmed; the highlight was false as written |
| Two-flight confirmation absorbs most flight-level burden | Worst-engine confirmed-alert rate under P: zero in 36/49 runs, ≥ 10% in 2/49; median delay 9.5 → 17 flights. Q: ≥ 10% in 20/49 | Confirmed |
| Early sensitivity is near the false-alarm floor | First-10-post-onset abnormal-state row alarm rate under P: 0.52–4.67% (median 1.21%) | Confirmed |
| Validation engines lie outside the selection-fit classes | In 6 of 7 subsets (all but DS04), the validation engine's class is absent from the selection-fit engines. LSTM validation loss 138–234 in DS01/DS08c, 0.07–0.19 elsewhere | Confirmed; disclosed as a limitation |

**Not re-checked, and not used in the manuscript:**
- the permutation homogeneity counts (7/49, 2/49, 22/49);
- per-engine matched-burden figures (e.g. Q's worst engine 13.0% against P's 9.7% at matched pooled 5%);
- the 67/80 and 41/80 pairwise counts;
- the seed-agreement rates;
- CVAE detection rates relative to the residual median.

## 4. Synthesis

**Consensus strengths.**
- The design, transparency and reproducibility are strong and need no rebuilding.
- The robust scientific findings are:
  1. context conditioning does not systematically help individual held-out engines, and can badly hurt specific cases;
  2. class coverage matters for phase-conditioned thresholds at fixed volume;
  3. the largest failures sit where calibration lacks the audit engine's class or flight envelope.

**Consensus gap.** The per-engine and worst-engine endpoints had no sampling-noise reference. As written, the negative headline was partly guaranteed by three things:
- 14–36 flights per engine;
- strict "every engine" and "worst engine" criteria;
- counting in-sample phase error under P as transport.

**Consensus text defects.**
- The volume claim is not supported.
- DS08c's under-alarming shift was counted as "phase-conditional miscalibration" without saying so.
- The DS08a engine 14 mechanism was misattributed.
- The CVAE was over-generalized.
- The persistence claims were stated at the wrong time scale.
- The delay null was overstated.
- The freeze was described without saying it was internal.
- One highlight was literally false.

**Disagreement.** Only on how much new analysis is *necessary*:
- editor and PHM reviewer: a noise floor plus self-calibration;
- statistical reviewer: a noise floor plus a class-stratified bootstrap rerun;
- alarm reviewer: null bands, flight-level confirmation and a per-unit recalibration control.

**Verdict of the panel: ONE FINAL FOCUSED GAP.**

## 5. Response applied in the revision (no new data access)

All of the following use committed outputs only and change no pre-specified decision.

**Post hoc checks.**
- A new Section 4.8 reports every item in Section 3 that was confirmed.
- Grey reference markers were added to Figs. 3 and 6a.
- Tables S18–S20 were added to the supplement.
- The verifier checks every post hoc number against `post_hoc_checks.json`.

**Abstract and highlights.** Rewritten:
- DS08c is identified as under-alarming;
- the non-transport claim is stated as an engine-level result (about half of engines improved);
- the noise references are reported;
- the failures are located (class or envelope);
- the coverage claim is limited to phase-conditioned thresholds;
- the unsupported volume claim is removed.

**Methods.**
- §3.2 says the freeze is internal, not externally registered.
- §3.7 places the persistence rules within flights (seconds at 1 Hz) and points to the post hoc two-flight rule.
- §3.8 explains that the volume contrast measures only row-subsampling noise.
- §3.9 marks the post hoc checks.

**Results.**
- §4.2 states that H1 sat on its threshold and that DS08c counts through under-alarming.
- §4.3 adds the coin-flip reading and corrects the DS08a engine 14 mechanism.
- §4.4 describes the CVAE as fleet-trained and gives the median-residual gap.
- §4.5 limits coverage to C, reports the best-single comparison and mission sharing, and says F1/F2 met the rule exactly.
- §4.6 reads H6 against the null and adds "no advantage meeting the pre-specified criterion" and "little power".
- §4.7 notes the bootstrap's class-dropping.

**Discussion and conclusion.**
- §5.1–5.3 and §6 were rewritten to match.
- §5.5 adds limitations: sampling noise; the non-stratified bootstrap; the missions/engine confound; the CVAE score without the latent-prior term; epoch selection on unseen classes; the internal freeze.
- Table 4's caption defines S1–S5, M-B and M-C.

**Status after the revision.**
- The pre-specified decisions (Table 4) are unchanged.
- The headline is re-worded from "broad failure" to "conditioning did not systematically help individual engines; failures concentrate where calibration lacks class or envelope coverage; per-engine errors need a noise reference".

## 6. Remaining focused validation (not run; requires the author's decision)

**Why not run now.** The reviewers' preferred references need the saved models to rescore the audit rows. That is a new, post-outcome access to official-test data under a new analysis. The brief reserves such a step, and the author asked only for a check and an evaluation. If authorized, it should be frozen as a short plan before it runs.

**Plan (to be frozen before running).** Use the saved models in `--reproduction-only` mode, write outputs to a new directory, and add access-log entries.

1. **Within-engine split-flight self-calibration floor.** For each audit engine, calibrate P and C on half of its healthy flights (odd or even) and evaluate A2 on the other half. This gives, per engine, the A2 that perfect transport would give.
   - Report each transport endpoint (ME-A2, WE-A2, n_worse) as its excess over this floor.
   - Report the transport gap: audit phase FPR minus the calibration pool's in-sample phase FPR.
2. **Class-stratified per-subset bootstrap.** Rerun U-EXT1 with calibration engines fixed, or resampled within class, so that no replicate omits a covered class.
3. **Per-unit recalibration positive control.** Set P and C thresholds from each audit engine's first k = 3, 5 and 10 healthy flights; evaluate on its remaining healthy flights and on post-onset delay.
4. **Flight-level k-of-n confirmation at matched per-engine burden.** This one needs no rescoring and can use committed per-flight outputs.
5. **Pre-declared consequence.** If the per-engine excess over the self-calibration floor holds in fewer than 3 of 5 families, the headline moves to "failures concentrated in uncovered or atypical engines and flights". That would be a rescope of the claims, not of the design.

**Estimated cost.** Rescoring of 7 new subsets × 10 runs for audit rows only, with no training: under one hour of GPU time, plus analysis.

## 7. Final verdict

**ONE FINAL FOCUSED GAP.** The extension is sound and fully documented. After this review's text corrections and post hoc checks, the manuscript is accurate. But its central per-engine claims should be tested against a proper self-calibration noise floor before submission (Section 6). The post hoc references already in the paper show that:
- per-engine row-level excess is real in aggregate;
- the flight-level worst-engine excess is mostly within noise.

## 8. Addendum (2026-09-29): the focused validation was run

**Authorization and scope.** The author approved one final focused validation, limited to three components:
- an engine-specific noise reference (the manuscript's cross-fitted self-calibration reference);
- a class-preserving bootstrap;
- local recalibration with K = 5.

**Execution.** The plan was frozen and committed before any re-read (`FOCUSED_VALIDATION_PLAN.md`, `d85aa10`). The code was committed and tested next (`6f15aef`). The run then used healthy official-test rows only, and every reproduction gate passed (`76220c0`).

**Results** (`FOCUSED_VALIDATION_REPORT.md`):
- **Engine-specific noise floor.** Fleet-calibrated errors exceeded each engine's cross-fitted self-calibration floor in 27/30 engines under C, in 5/5 families. The pre-declared reading is STRENGTHENED.
  - The floor proved to be a self-calibration floor, because out-of-fold errors cancel to first order. It therefore understates flight-to-flight sampling noise, contrary to the plan's "conservative" description.
  - Against the earlier, conservative approximate reference, 13/30 engines exceed it, in 3/5 families.
- **Class-preserving bootstrap.** Class omission explained a median of 11–15% of the per-subset C − P interval widths. No conclusion changed.
- **Local recalibration (K = 5).** It did not reduce errors (median −0.16 pp under C).

**Effect on this review.** The focused gap of Section 6 is thereby addressed, with the claim narrowed in magnitude. Scientific analysis has stopped.
