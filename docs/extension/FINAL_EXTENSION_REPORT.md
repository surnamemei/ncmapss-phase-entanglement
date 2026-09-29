**Final extension report: multi-subset calibration transport** (updated after the hostile review, `EXTENSION_HOSTILE_REVIEW.md`, and the final focused validation, `FOCUSED_VALIDATION_REPORT.md`).

**Branch and snapshot.** Branch `mssp-extended`; the pre-extension snapshot is the local tag `mssp-pre-extension-2026-09-28` (→ `d5699a1`).

**Governing documents** (all in `docs/extension/`):
- `EXTENSION_CHARTER.md`;
- `SUBSET_SELECTION_LOCK.md`;
- `GENERALIZATION_PROTOCOL.md` (FROZEN v1.0) with Amendments 1–3 in `AMENDMENTS.md`;
- `CVAE_SPECIFICATION.md`;
- `EXTENSION_HOSTILE_REVIEW.md` (four-reviewer panel, data check and post hoc re-checks);
- `FOCUSED_VALIDATION_PLAN.md` (FROZEN v1.0, `d85aa10`) and `FOCUSED_VALIDATION_REPORT.md` (final, author-approved post hoc validation).

**Evidence.**
- Per-subset outputs: `results/extension/<subset>/{lock,audit}/`.
- Cross-dataset outputs and decisions: `results/extension/summary/` (decisions in `decisions.json`).
- Post hoc checks: `paper/mssp_extended/post_hoc_checks.py` → `paper/mssp_extended/evidence/post_hoc_checks.json`.
- Focused validation: `results/extension/focused_validation/`.
- `EX` identifiers refer to `docs/extension/EXTENSION_EVIDENCE_LEDGER.csv`: 1,674 rows:
  - EX000001–EX001308 are pre-specified or descriptive;
  - EX001309–EX001349 are post hoc;
  - EX001350–EX001585 are the final focused validation;
  - EX001586–EX001674 register every value, table and figure cited in the manuscript (checked by `paper/mssp_extended/verify_numbers.py`).

**Manuscript.** `paper/mssp_extended/`: a 21-page PDF, a 43-page supplement, a one-page cover letter and a flat upload bundle. `verify_numbers.py` checks 78 claims against the evidence ledger. The final checklist is `paper/mssp_extended/FINAL_SUBMISSION_CHECKLIST.md`.

**Conventions.**
- α = 1% unless stated.
- pp means percentage points.
- "Family" means a fleet family, the top-level cross-dataset unit (F1 = DS01, F2 = DS04, F3 = DS05/06/07, F4 = DS08a, F5 = DS08c).
- "Post hoc" marks analyses added after all outcomes; they change no pre-specified decision.

# Original Pre-Extension Story

The pre-extension story was Story B, "calibration transport" (`docs/mssp/FINAL_STORY_LOCK.md`). It rested on DS02 and DS03 only:
- 2 calibration engines per subset;
- 3 and 6 audit engines;
- three residual detectors sharing one pipeline.

Its claims:
- A pooled nominal healthy-FPR threshold left phase-conditional FPRs unequal, with descent highest. This was discovered on DS02 and reproduced once on held-out DS03 engines under a frozen protocol.
- Retrospective phase-conditioned thresholds (C) reduced pooled between-phase disparity and pooled maximum nominal error in 14/14 detector runs. Every paired interval included zero.
- The pooled correction did not transport reliably to individual engines:
  - two of three class-1 audit engines worsened in every run;
  - equal-engine weighting reversed the DS02 improvement;
  - a continuous context threshold (Q) failed on other engines;
  - support distance did not explain the failures.
- There was no general delay advantage at matched false-flag burden.
- The strongest failures coincided with flight classes absent from calibration.

# New Datasets Opened

**Selection.** Nine objective criteria were committed before any metadata were read (`0fd3f67`). A metadata-only audit then selected the primary cohort (`7152b92`): DS01, DS04, DS05, DS06, DS07, DS08a and DS08c, with 30 official-test engines. The metadata audit read only labels, variable names and healthy-row altitude.

**Exclusion.** DS08d was excluded before any value was read. The official file is byte-identical to its archive entry but 32 bytes shorter than its own HDF5 superblock declares, so it cannot be opened.
- This is the HDF5-inconsistency case of stop rule §29. It was handled by the pre-specified exclusion criterion C1 at the subset level.
- The extension continued with the eligible subsets. The file was not repaired, and no other subset was substituted.

**Families.** Metadata showed that the subsets reuse recorded flights:
- DS05, DS06 and DS07 are one ten-unit fleet flying identical healthy flight sequences;
- some engines recur across subsets;
- 84–100% of each new subset's healthy flight signatures occur in another subset.

Families therefore replace subsets as the top-level unit. At data opening, the healthy sensor digests of DS05, DS06 and DS07 differed for every unit, so these are distinct data flying the same missions, not duplicates.

**Engine roles** (fixed from metadata by R-ALLOC):
- fit pools of 3 engines covering every class present;
- calibration pools of 3 engines (DS08a: 6);
- DS08c's calibration pool is class 3 only, while all four of its audit engines are class 2.

In six of seven subsets the validation engine's class was absent from the selection-fit engines (a disclosed limitation).

**Execution.**
- **Locks.** Seven calibration-only locks, committed before any official-test read (`b9786ce`).
- **Shakedown.** The DS02/DS03 reference shakedown reproduced every frozen table cell by cell, after Amendment 3 (`73e4555`).
- **Audits.** Seven one-shot audits ran in frozen order, each writing its marker before its first read (`4e7a45f`, the only commit that touches these audit outputs).
- **Access log.** Every opening is recorded in `OUTCOME_ACCESS_LOG.md`.
- **Post-review check.** The review's data check confirmed disjoint roles, lock-before-open, exact in-sample calibration, and identical recomputation of H1–H6 and CE1 from raw per-subset outputs.

# Condition-Aware Baseline

**Design.** One fleet-trained CVAE was frozen before training (`CVAE_SPECIFICATION.md`):
- input: standardized sensors;
- conditioning: the 32 past-only operating descriptors;
- a heteroscedastic Gaussian decoder;
- score: NLL at the posterior mean, with no latent-prior term;
- the same P, C and Q thresholds as the other detectors.

Amendment 2 bounded the encoder log-variance and clipped gradients after a non-finite loss on DS01. Nothing else changed, and it was made before any outcome.

**Result: H5 SURVIVES (EX000005).** Representation-level conditioning of a fleet-trained model did not remove the transport problem:
- **Worst engine.** The CVAE's worst-engine error under P stayed ≥ 0.5 pp in the majority of CVAE runs in 5/5 families.
- **No substantial improvement.** It never met the "substantially improves" criterion (ME-A2 ≤ half the best residual detector) in any family, and never "solved" transport.
- **Phase dependence.** It reduced pooled phase dependence relative to all residual detectors in only 2/5 families.
- **Comparison with residual detectors.** Its mean per-engine error under P exceeded:
  - the best residual detector's by a median of 0.52 pp (family bootstrap 0.05 to 1.31 pp; 5 top-level units; EX000945);
  - the median residual detector's by 0.24 pp. It was lower than the median residual detector in F1 (post hoc, EX001338).

  The CVAE therefore sits within the residual pack; it is not a clear loser.
- **References.** On DS02 and DS03, the CVAE showed the same descent elevation under P and the same class-1 failures under C: DS02 engine 14 in 3/3 seeds, DS03 engine 12 in 3/3 seeds.

**Diagnostics.**
- The decoder log-variance was within 1% of a bound (almost always the floor) for 0–73% of outputs, depending on seed and subset, because some channels are nearly deterministic given the descriptors.
- float32 and float64 scoring agreed (Spearman 1.0).
- Per-engine or early-cycle training, as in Chen et al., was not tested.

# Calibration-Composition Intervention

**Design.** Six subsets were eligible (DS01, DS04, DS05, DS06, DS07, DS08a), forming four families. With the detectors fixed, P and C thresholds were re-estimated from calibration designs of exactly equal volume N (60,000–96,000 rows; 5 nested draws). The primary endpoint (CE1) is the within-engine coverage effect:
- the error under single-engine calibrations from other classes minus the error under same-class calibrations;
- positive means coverage helps.

**Result: H4 SUPPORTED (EX000004)**, with the *beyond-volume* qualifier and a *weak* qualifier for pooled thresholds.
- **Coverage.** The coverage effect was positive in ≥ 7/10 runs under both P and C in 5/6 subsets and 3/4 families. F1 and F2 met the rule with exactly 7/10 runs under P; DS08a under P was 5/10.
- **Size.** The effect is **modest for pooled thresholds**: median 0.11 pp, bootstrap −0.04 to 0.18 pp (EX000946). Post hoc, it is confined to class-1 audit engines (+0.11 pp against −0.09 and −0.08 pp; EX001335).

  It is **clear for phase-conditioned thresholds**: 0.55 pp, bootstrap 0.18 to 1.11 pp (EX000947), positive for every audit class (EX001334).
- **Balance.** Class-balanced calibration beat the mean single-engine design in ≥ 9/10 runs under both arms in 5/6 subsets; DS04 under C was 0/10. Post hoc, it beat the *best* single engine in only 7/42 (P) and 11/42 (C) residual runs (EX001336–EX001337), so this largely reflects averaging.
- **Volume.** The volume contrast was about zero in every subset. By design this is automatic: protocol §7 thins rows across the same engine's flights. It therefore **cannot** show that more data from other classes fails to substitute for coverage, and that claim was withdrawn from the manuscript.
- **Mechanism caveat.** In N-CMAPSS, class coverage also means shared recorded missions:
  - same-class audit and calibration pairs share 35–56% (class 1) and 5–20% (classes 2–3) of healthy flight profiles;
  - different-class pairs share none (EX001333).

  Class coverage is also confounded with engine identity, because most pools have one engine per class.

# Alarm-Persistence Robustness

**Rules.** R1 (3 consecutive exceedances) and R2 (3 of 5) were applied within flights (a few seconds at 1 Hz), with κ recalibrated per rule on calibration flights.

**Result: H6 SURVIVES (EX000006)** under its pre-specified rule. The worst-engine healthy-flight false-flag rate was ≥ 10% at locked κ in the majority of residual cells:
- in 3/5 families under R0;
- in 4/5 under R1 and 4/5 under R2.

**Under P** (new cohort, residual runs):

| Rule | Median worst-engine false-flag rate | Share of cells ≥ 10% |
| --- | --- | --- |
| R0 | 13.0% | 63% |
| R1 | 13.0% | 69% |
| R2 | 14.3% | 69% |

(EX001032–EX001037.)

**Under Q**, the median worst-engine false-flag rate was 20.0–21.7%, and 86% of cells were ≥ 10% (EX001038–EX001043).

**Post hoc reading (EX001322–EX001328).** The pre-specified 10% line sits close to what a perfectly calibrated fleet shows with 14–36 healthy flights per engine. Under perfect calibration:
- the null median worst engine is 8.6–11.8%;
- P(≥ 10%) is 0.41–0.69 per cell.

The observed worst engine under P exceeded the null's 95th percentile in 0/7 runs in DS01, DS04, DS07 and DS08c, and in only 1–3/7 in DS05, DS06 and DS08a. **The flight-level H6 excess is mostly within sampling noise.**

**Row level.** Relative persistence calibration error was material on at least one engine in 98–100% of residual cells.

**Flight-to-flight confirmation** (post hoc, not pre-specified; EX001346–EX001348). Two consecutive flagged flights at locked κ:
- reduced P's worst-engine confirmed-alert rate to zero in 36/49 residual runs, with ≥ 10% in 2/49;
- raised the median delay from 9.5 to 17 flights;
- left Q at ≥ 10% in 20/49 runs.

**Conclusion.** Within-flight persistence does not repair calibration transport. Flight-level confirmation largely removes the healthy flight-level burden for P and C at a delay cost, but this is a post hoc observation.

# Multi-Subset Generalization

**H1 SUPPORTED (EX000001)**, at exactly the pre-specified threshold of 3/5 families: F3, F4 and F5.
- DS01 missed the rule because the LSTM's pooled error was 0.49 pp, just under the 0.5-pp line.
- DS04 missed it because PCA's pooled error was 0.40 pp.
- DS07 missed it because PCA (0.59 pp) and IF (0.56 pp) were above the line but the LSTM (0.35 pp) was below it.
- F5 (DS08c) counts through under-alarming.
- Post hoc, 53% of material per-engine errors under P are under-alarming (EX001317).

**Descent was the highest phase under P** in:
- 10/10 runs in DS01 and DS07;
- 9/10 in DS04, DS05 and DS06;
- 4/10 in DS08a (where cruise was highest in 5/10);
- 5/10 in DS08c (where climb was highest in 5/10).

(EX000971–EX000989.)

**DS08c differs.** All of its audit engines belong to a class absent from calibration, and they **under**-alarmed in every phase (0.2–0.8% at a 1% target). Its "material miscalibration" is a transport-level shift, not phase disparity.

**H2 PARTIAL (EX000002).** C reduced pooled disparity in 66% of the 70 new cells and in 3/5 families (F1, F2, F3), not in DS08a or DS08c. This is less consistent than the 14/14 on DS02/DS03. For PCA on DS05 and DS06, C (and Q) made calibration markedly worse.

**H3 SURVIVES (EX000003).**
- **C.** Uniform per-engine improvement over P occurred in 14% of cells, and at least one engine was worse in 86% (EX001092–EX001093).
- **Q.** The shares were identical: 14% and 86% (EX001095–EX001096).
- **Engine-level reading (post hoc; EX001329–EX001331).**
  - On average, C improved 50% and Q 49% of the engines in a cell: a coin flip.
  - The 14% every-engine share is above the 5.6% expected by chance, so it is not itself evidence of harm.
  - In DS04, every engine stayed within the material line in 4/7 residual runs under Q.

**Classification of the original story: PARTIALLY GENERALIZED (EX000007).** The components held in the following numbers of new families:

| Component | Families |
| --- | --- |
| S1, conditional miscalibration | 3/5 |
| S2, C reduces disparity | 3/5 |
| S3, the correction fails to transport uniformly | 4/5 |
| S4, no general matched-delay advantage for C | 5/5 |
| S5, Q fails on some engine | 5/5 |

**Rescope flags.** No rescope flag (A–F) was raised (EX000009–EX000014).

# Cross-Dataset Statistical Evidence

**Method.** A two-stage family → subset → (engine → flight) bootstrap with 2,000 replicates and 5 top-level families (U-EXT2). The medians over families of the C − P effects all have intervals that include zero:
- **Disparity (ΔA1):**
  - PCA −0.03 pp (−0.55 to 1.32);
  - IF −0.11 (−1.15 to 0.48);
  - LSTM −0.31 (−0.52 to 0.53);
  - CVAE +0.01 (−0.56 to 0.99).
- **Mean per-engine nominal error (ΔME-A2):**
  - PCA −0.02 (−0.20 to 1.41);
  - IF −0.20 (−0.53 to 0.22);
  - LSTM −0.03 (−0.21 to 0.34);
  - CVAE −0.03 (−0.22 to 0.46).

(EX000933–EX000944.)

**Caveat (post hoc; EX001339–EX001345).** The pre-specified per-subset bootstrap resamples calibration engines without stratifying by class. A replicate omits a calibration class with probability 78% in DS01 and DS05–07, 33% in DS04 and 42% in DS08a. That imposes the harmful intervention in most replicates and widens and skews the C − P intervals. With one calibration engine per class, variability between same-class calibration engines cannot be estimated.

**Direction counts.** C lowered pooled disparity in 5/7 subsets for each residual detector family and in 3/7 for the CVAE. It lowered ME-A2 in only 3/7 for every family.

**Heterogeneity against noise (post hoc; EX001309–EX001321).**
- A perfectly calibrated engine would reach the 0.5-pp material line in about 31% (P), 30% (C) and 49% (Q) of engine–run pairs.
- Observed shares were 87%, 80% and 82%, with 60%, 49% and 58% above the null 95th percentile.
- Per-engine row-level excess is therefore real in aggregate, but a single engine near the line is not evidence of transport failure.

**Final focused validation, class-preserving bootstrap** (EX001350–EX001585; `FOCUSED_VALIDATION_REPORT.md` §3). Resampling calibration engines within flight class, with identical audit plans, shows:
- class omission accounted for a median of 11–15% of the per-subset C − P interval widths;
- the share was largest in DS01 (33–43%) and about zero in DS04 and DS08c;
- no ΔME-A2 interval changed from including to excluding zero;
- every cross-dataset C − P interval still includes zero;
- the CVAE gap remains, at 0.06–1.18 pp.

**Status of the numbers.** No timestamp-level inference was made. No interval is called significant, and every count rule is pre-specified; the post hoc references are descriptive.

# What Generalized

- **Pooled calibration does not guarantee phase-conditional validity** (H1, 3/5 families, at the threshold). Descent-high FPR under P recurred in five of seven subsets, which is three of five families (F1–F3).
- **Context conditioning does not systematically help individual held-out engines.**
  - Phase-conditioned and continuous-context thresholds improved on average half of the engines in a cell, and a fleet-trained CVAE did not improve transport (H3 and H5).
  - They failed badly where calibration lacked the engine's class (DS08c under C; DS02 engine 14 and DS03 engine 12 in the references), and for PCA on DS05 and DS06.
- **Fleet-calibrated per-engine errors are systematic but modest** (final focused validation).
  - They exceeded each engine's own cross-fitted self-calibration reference in 27/30 engines under C (29/30 P, 28/30 Q), in all five families.
  - They were mostly below 1 pp (median 0.63 pp under C).
  - They survived within-flight persistence rules.
  - Recalibration on five healthy flights did not reduce them.
- **There is no matched-burden delay advantage for phase conditioning meeting the pre-specified criterion** (S4: 5/5 families; the H7 rule was never met for C). Early sensitivity was near the false-alarm floor, so these comparisons have little power.
- **Class coverage matters for phase-conditioned thresholds** at fixed volume (H4; 0.55 pp).

# What Failed to Generalize

- **"C reduces pooled disparity"** was universal on DS02/DS03 (14/14) but held in only 66% of new cells and 3/5 families. For PCA on DS05 and DS06, C and Q greatly worsened calibration.
- **"Descent is highest"** is not universal. DS08a is cruise- or descent-dominated, and DS08c splits between climb and descent.
- **Material phase-conditional miscalibration under P** was below the 0.5-pp line for at least one detector in DS01, DS04 and DS07. In DS08c it is uniform under-alarming.
- **The worst-engine flight-level false-flag burden** (H6's pre-specified quantity) is mostly within sampling noise.
- **Coverage for pooled thresholds** is weak (0.11 pp; interval includes zero) and confined to class-1 engines, which share many recorded missions with their same-class calibration engine.

# Organizing Variable

**Coverage of the audit engine's operating conditions by the calibration fleet**, at two levels.

1. **Flight class** (H4 SUPPORTED).
   - At fixed volume, same-class calibration transported better, clearly for phase-conditioned thresholds (0.55 pp) and weakly for pooled ones (0.11 pp).
   - In N-CMAPSS, class coverage also means shared recorded missions, and it is confounded with engine identity.
   - The "beyond volume" qualifier is automatic under the row-thinning design and carries no weight.
2. **Flight envelope** (post hoc; EX001332). The largest failure in a covered class, DS08a engine 14, came from one flight:
   - it carried 65% of the engine's healthy alarms;
   - without it, FPR falls from 2.70% to 1.00%;
   - its altitude span (32,029 ft) exceeded every fit (≤ 28,051 ft) and calibration (≤ 30,033 ft) flight in DS08a;
   - it was the only DS08a audit flight outside the calibration altitude envelope.

   The earlier reading ("engine-specific variation within a covered class") was wrong and has been corrected.

**Limits.** Neither class nor envelope is shown to be causal. Both are coarse, observable descriptors of which recorded missions and operating conditions the calibration data contain. The positive organizing hypothesis (brief §12) is **partly supported**.

# Fair-Matching Result

**Method.** All delay comparisons were made at matched realized healthy-flight false-flag burden (nearest supported anchor within one flight step; no interpolation). Only 5 of 420 run × rule × arm comparisons lacked three supported anchors.

**C versus P** (residual runs, R0): 7/49 runs "earlier", 18 "equal", 0 "later", 24 "mixed". The pre-specified "improves detection delay" rule (≥ 5/7 earlier with a lower curve mean) was met in **no** subset under any rule. C was never later than P.

**Q versus P.** Q was "earlier at matched burden" more often (23/49 at R0; 32/49 at R1; 28/49 at R2). It met the rule only on DS04, under R1 and R2. Q's calibration transport is the worst of the three arms, so any detection gain comes with the least reliable false-alarm meaning.

**CVAE.** For the CVAE, C was earlier in 4/21 runs and Q in 4–7/21, and neither met the rule in any subset.

**Limits (review).**
- Burden was matched on the pooled rate, not per engine.
- Early post-onset sensitivity under P was 0.52–4.67% (median 1.21%; EX001349), close to the healthy target.

The delay null is therefore low-powered: "no advantage meeting the criterion", not "no advantage".

# Strongest New Engineering Insight

**Context-conditioned false-alarm thresholds are not a safe default for individual units.**
- Calibrated on some engines, they improved about half of the held-out engines and worsened the rest.
- They failed badly when calibration lacked the unit's flight class.
- They could degrade a detector's calibration severalfold (PCA on DS05/DS06).

**Fleet-to-engine errors are systematic but modest.** They were mostly below 1 pp at a 1% target, yet above what each engine's own flights achieve by self-calibration in 27 of 30 engines. They cannot be removed by a short local recalibration: five-flight local thresholds were noisier than the fleet thresholds they replaced (median change −0.16 pp under C).

**What helped.**
- **Flight-class coverage in the calibration fleet**, at fixed calibration volume. This matters most for phase-conditioned thresholds.
- **Flight-envelope coverage.** One flight above every calibration altitude range produced the cohort's largest failure.

**Practical rule.**
1. Validate thresholds per held-out unit against engine-specific noise references.
2. Before trusting context-conditioned thresholds on a unit, ensure the calibration fleet covers its class, and treat out-of-envelope flights as outside the threshold's validity.
3. Do not expect a few local healthy flights to repair a fleet threshold.

# Closest Prior Art After Extension

Chen et al. (2026) and Asaadi et al. (2025) were read in full (`PRIOR_ART_EXTENSION.md`; 16/16 quotes verified).

**Chen et al.**
- They state that no single HI threshold fits across operating conditions (paraphrased).
- They condition a CVAE on operating variables with a single KDE threshold.
- They evaluate N-CMAPSS DS02 only on class-3 development units, training on early cycles of the engines they test.
- **This work's fleet-trained CVAE result tests their implicit assumption** that a pooled threshold on a conditioned score keeps its nominal meaning within contexts and across engines. For a fleet-trained model it did not, in 5/5 families. Their per-engine early-cycle training was not tested.

**Asaadi et al.** They show that alarm policies (deadbands, filtering, delay timers) change time-variant FAR/MAR/AAD. Their zones are fault stages in one variable, and there is no cross-unit transport.

**Other close precedents (unchanged):**
- Zhao et al. (mode-specific PCA limits);
- Michau and Fink (per-mode FPR);
- Toshkova et al. (per-condition thresholds);
- ProDiMES (fixed false-alarm budget);
- Lee et al. (flight-state thresholds);
- Hsu et al. (N-CMAPSS residual detectors, cruise only);
- Farouq et al. (fleet heterogeneity, sub-fleet calibration).

**Novelty.** It remains narrow: an engine-disjoint, pre-specified audit of nominal false-alarm calibration transport, across seven held-out N-CMAPSS subsets and five fleet families, with composition interventions. "First" is not claimed.

# Claims Strengthened

- **Non-transport of context-conditioned calibration** is now shown across five families, 30 new audit engines and four detector families, including a fleet-trained CVAE, and read at the engine level: about half of engines improved.
- **The flight-class association** is upgraded from descriptive (three class-1 engines) to a controlled, fixed-volume intervention in four families, clearly for phase-conditioned thresholds.
- **No matched-burden delay advantage for C meeting the pre-specified criterion** now holds in 5/5 families and under persistence rules. C was never later.
- **The pooled-calibration phase effect exists without any transport.** Within the calibration engines themselves, the pooled threshold left descent highest in 50 of 70 subset × run cells: 6 of 7 subsets, with DS08c the exception, where cruise is highest.

- **Engine-level miscalibration beyond self-calibration** (final focused validation). Fleet-calibrated errors exceeded each engine's own cross-fitted self-calibration reference in 27/30 engines under C, in 5/5 families. The pre-declared reading is STRENGTHENED.

# Claims Weakened

- **"C reduces pooled disparity"**: from 14/14 to 66% of new cells (H2 PARTIAL). It can badly worsen calibration for some detectors (PCA on DS05 and DS06).
- **"Descent is highest"**: not universal (DS08a, DS08c).
- **Material phase-conditional miscalibration under P**: holds in 3/5 families, exactly at the pre-specified threshold, one of them through under-alarming.
- **"Transport failure is broad"** (M-C, pre-specified headline): the per-engine rules are partly met by sampling noise. The excess is real in aggregate, but the flight-level worst-engine burden is mostly within noise.
- **Coverage for pooled thresholds**: weak, confined to class-1 engines, and confounded with shared missions and engine identity.

- **Magnitude and remediability of the per-engine errors.** They are mostly below 1 pp at a 1% target. Against the conservative approximate measurement-noise reference, only 13/30 engines clearly exceed it (C). A five-flight local recalibration did not reduce them.

# Claims Removed

- Any implication that phase conditioning is a generally beneficial correction, even for pooled disparity.
- Any implication that the transport problem is specific to DS02/DS03, or to residual detectors.
- Any implication that representation-level conditioning (a fleet-trained CVAE) resolves it.
- Any implication that within-flight alarm persistence absorbs it.
- "More calibration data from other classes did not substitute for coverage", and "coverage is necessary". The volume contrast cannot test this.
- "No calibration tested kept its nominal false-alarm rate on every held-out engine". This is false for DS04 runs.
- "Engine-specific variation within a covered class" as the explanation of DS08a engine 14, which is an out-of-envelope flight.
- "No delay advantage" stated as a positive null.

# Remaining Reviewer Attacks

1. **Sampling and self-calibration references bracket, rather than measure, sampling noise.** The final validation's cross-fitted self-calibration reference: out-of-fold errors cancel to first order, so it understates flight-to-flight sampling noise, and the plan wrongly called it conservative. The earlier clustered reference overstates that noise. How many engines exceed sampling noise therefore depends on the reference: 27/30 against the cross-fitted self-calibration reference and 13/30 against the approximate reference, under C. The families showing excess are 5/5 and 3/5 respectively.
2. **Per-unit remedy.** A per-engine recalibration with K = 5 healthy flights was tested and did not help (median −0.16 pp under C). Longer local baselines, per-engine models and flight-level k-of-n confirmation at matched per-engine burden are not tested.
3. **One simulator.** Flight-library reuse; there is no real-aircraft data.
4. **Small units.** 5 new families; 1–3 calibration engines per class; 14–36 healthy flights per audit engine; knife-edge H1 and H4.
5. **Coverage confounds.** Class coverage is confounded with engine identity and shared missions.
6. **One fleet-trained CVAE.** A single specification, whose variance floor binds.
7. **Operating points and policy realism.** The alarm operating points are far from engine health monitoring practice, and persistence is within-flight only; the two-flight confirmation is post hoc.
8. **Retrospective phases and simulated labels.**
9. **Venue risk.** An audit paper with no new method, on simulated data only.

# One-Paper vs Split Decision

**ONE PAPER + LARGE SUPPLEMENT.**
- **The paper.** The primary result — context-conditioned calibration does not reliably transport to individual engines, and failures concentrate where calibration lacks class or envelope coverage — carries the paper.
- **Supporting analyses.** The composition intervention answers the same question at the design level; the CVAE and persistence analyses are baselines and robustness.
- **No split.** None is a separate methodological contribution large enough to justify a split.
- **Supplement.** Per-subset detail, persistence tables, matched-delay labels, abnormal-state rates, the DS02/DS03 reference results, the post hoc checks and the complete pre-extension supplement.

# Final Recommended Story

**Pre-specified headline.** The interpretation-matrix headline is **M-C + M-B**: context-aware calibration does not itself guarantee calibration transport, and calibration-fleet coverage is a determinant of it.

**Faithfully qualified after the hostile review and the final focused validation.** Across seven held-out N-CMAPSS subsets (five fleet families):
- Retrospective phase-conditioned and continuous-context thresholds, and a fleet-trained condition-aware representation, did not systematically improve individual held-out engines: about half improved.
- Fleet-calibrated per-engine errors were systematic but mostly below 1 pp.
  - They exceeded each engine's cross-fitted self-calibration reference in 27 of 30 engines. Against a conservative measurement-noise reference, 13 of 30 engines exceed it.
  - Recalibration on five healthy flights did not reduce them.
- The largest failures arose where the calibration fleet lacked the audit engine's flight class or flight envelope, or where conditioning backfired.
- At fixed volume, covering the engine's class improved phase-conditioned calibration.

**The original Story B is PARTIALLY GENERALIZED.** Its central non-transport claim generalized, stated at the engine level and narrowed in magnitude.

# Final Recommended Title

*False-Alarm Calibration Transport Across Engines in Full-Flight Aero-Engine Anomaly Detection: A Multi-Subset Audit of Context Conditioning and Calibration-Fleet Coverage*

# Overall Status

**SUBMITTABLE WITH DISCLOSED LIMITATIONS.**

**How the focused gap was closed.** The one focused gap from the hostile review (the missing noise reference) was closed by the author-approved final validation:
- The validation followed a frozen plan (`d85aa10`) and read only healthy test rows.
- Every reproduction gate passed.
- The pre-declared reading is STRENGTHENED, with the self-calibration caveat and the narrowed wording above.

**Status of the evidence.**
- The pre-specified decisions (H1–H7) are unchanged.
- The manuscript (`paper/mssp_extended/`) reports the validation in Sections 3.10 and 4.8, with every number verified.

**Limitations to keep disclosed.**
- one simulator;
- small units;
- the bracketed engine-specific sampling and self-calibration references;
- coverage confounds;
- a single CVAE;
- retrospective phases.

No further experiment is proposed. The next stage is manuscript finalization and submission by the author.

