# Focused validation report (final; post hoc)

**Plan.** `FOCUSED_VALIDATION_PLAN.md` (FROZEN v1.0), commit `d85aa10`, SHA-256 `f734cdf6…`.

**Code.** `src/ext_focused_validation.py` and `scripts/run_focused_validation.py`, commit `6f15aef`.

**Run.** 2026-09-29, 01:53Z–02:01Z; each subset took 48–100 s.

**Outputs.** `results/extension/focused_validation/`.

**Terminology.** The frozen plan calls component 1 the "engine-specific sampling-noise floor". The manuscript calls the same quantity the *cross-fitted self-calibration reference*, because it describes what calibrating on the engine's own flights achieves (Section 2). The approximate reference of the earlier post hoc checks is called the *approximate sampling reference*. The final uncertainty wording is "engine-specific sampling and self-calibration references".

**Scope.**
- It changes no pre-specified H1–H7 decision.
- Scientific analysis stops after this report.

## 1. Execution and gates

**Data read.**
- Healthy (`hs = 1`) official-test rows only, for the seven new subsets: 5,771,668 rows in total.
- The saved, locked models were used; nothing was fitted.
- Each re-read is logged in `OUTCOME_ACCESS_LOG.md` with the plan hash.

**Gates (all passed in every subset).**

| Gate | Check | Result |
| --- | --- | --- |
| G1 | Frozen baseline | Verified before and after |
| G2 | Plan hash; code committed and clean | Verified |
| G3 | Calibration fingerprints | Reproduced for all 10 runs |
| G4 | Committed per-engine, per-phase healthy row and alarm counts, and per-flight healthy R0 alarm counts | Reproduced exactly: 90 run × target × arm checks per subset |
| G5 | Original U-EXT1 α = 1% replicates and intervals | Reproduced exactly, all 10 runs |
| G6 | Committed U-EXT2 table | Reproduced |

**Class omission in the original bootstrap.** The original design omitted a calibration class in:
- 1,601 of 2,000 replicates in DS01;
- 700 in DS04;
- 1,566, 1,550 and 1,548 in DS05, DS06 and DS07;
- 828 in DS08a;
- 0 in DS08c.

## 2. Component 1: engine-specific noise floor (cross-fit)

**Pre-specified result** (α = 1%, residual runs; an engine "clearly exceeds" if its observed fleet-calibrated A2 is above its own cross-fit NF95 in ≥ 4 of 7 runs):

| Arm | Engines clearly exceeding | Families showing excess (≥ half of engines) | CVAE: engines clearly exceeding |
| --- | --- | --- | --- |
| P (pooled) | 29/30 | 5/5 | 27/30 |
| C (phase-conditioned) | 27/30 | 5/5 (F1 3/4, F2 4/4, F3 11/12, F4 5/6, F5 4/4) | 29/30 |
| Q (continuous context) | 28/30 | 5/5 | 28/30 |

**Engines that do not clearly exceed.**
- Under C: DS01 engine 8 (3/7 runs), DS07 engine 9 (3/7) and DS08a engine 12 (2/7).
- Under P: DS08a engine 12 (3/7).
- Under Q: DS08a engines 11 (0/7) and 12 (1/7).

**Magnitudes** (medians over residual runs):
- **Cross-fit floor NF50:** 0.13 pp across engines (range 0.02–0.41 pp, and 3.35 pp for DS08a engine 14).
- **NF95:** 0.04–1.33 pp (4.13 pp for engine 14).
- **Observed error under C:** median 0.63 pp (range 0.23–5.39 pp).
- **Ratio of observed error to NF50:** median 6.2.

Per-engine values are in `summary/engine_summary.csv`.

**Pre-declared interpretation (plan §6): STRENGTHENED.** Under C, the excess holds in 5 of 5 families.

**Caveat found at interpretation: the cross-fit floor is a self-calibration floor, not a measurement-noise floor.**

- **What the plan claimed.** It described the cross-fit reference as conservative, meaning larger than the sampling noise of the observed error. That was incorrect.
- **Why it fails.** Out-of-fold thresholds are estimated from the other folds of the same engine. A fold of higher-scoring flights raises every other fold's thresholds while lowering its own, so the fold-level deviations cancel to first order in the pooled out-of-fold rate. With equal folds, the first-order deviation is exactly zero.
- **What the reference therefore measures.**
  - It does measure the error left by calibrating an engine on its own flights.
  - It understates the flight-to-flight sampling noise of a single engine's measured error at a fixed threshold.
- **Consequence.** Measured against sampling noise, "clearly exceeds" overstates the evidence.
- **Size of the understatement.**
  - At the engine median, the cross-fit NF50 is 0.84 times the flight-clustered standard error of the same engine's overall FPR estimated earlier. It is also about one third of the earlier approximate A2 reference.
  - In DS04 the ratio is about one tenth: NF50 of 0.02–0.03 pp against an earlier reference median of 0.26 pp.

**Sensitivity reading** (existing outputs only; the same counting rule; no new data or model). Applying the rule to the earlier, committed approximate measurement-noise reference (`paper/mssp_extended/evidence/post_hoc_engine_noise.csv`), which is conservative in the other direction:

| Arm | Engines clearly exceeding | Families showing excess |
| --- | --- | --- |
| C | 13/30 | 3/5 (F1, F2, F5) |
| P | 17/30 | 3/5 |
| Q | 18/30 | 5/5 |

The pre-declared category (≥ 3 of 5 families) is reached under both references. How many individual engines exceed depends on the reference: between 13 and 27 of 30 under C.

## 3. Component 2: calibration-class-preserving bootstrap

**Per subset** (identical audit plans; residual runs; α = 1%). The share of the original C − P interval width attributable to class omission, taken as the median over runs, was:

| Subset | Share of width |
| --- | --- |
| DS01 | 33–43% |
| DS05 | 9–10% |
| DS06 | 14–16% |
| DS07 | 14–21% |
| DS08a | 11–15% |
| DS04 | 0–4% |
| DS08c | about 0% (no class can be omitted) |

Across subsets, the median shares are:
- ΔME-A2: 13%;
- ΔA1: 12%;
- ΔA2: 11%;
- ΔWE-A2: 15%.

**Intervals that include zero.**
- ΔME-A2 intervals changed in no subset.
- In DS01, ΔA1 intervals including zero fell from 7/7 to 4/7 runs, and ΔA2 intervals from 7/7 to 6/7.

**Cross-dataset (U-EXT2).**
- Widths changed by factors of 0.81–1.04.
- Every C − P interval still includes zero.
- The CVAE-minus-best-residual interval moved from 0.05–1.31 pp to 0.06–1.18 pp and still excludes zero.

**Conclusion.** Class omission inflated the per-subset intervals modestly, most in DS01. It does not explain the unresolved cross-dataset C − P effects.

## 4. Component 3: per-engine local recalibration (K = 5)

Thresholds were set from each audit engine's first 5 healthy flights and evaluated on its remaining 9–31 healthy flights.

| Arm | Median change (fleet − local; positive = local better) | Engines improved in ≥ 4/7 runs | Local within K-matched NF95^K | Fleet already within NF95^K | Local within the cross-fit NF95 |
| --- | --- | --- | --- | --- | --- |
| C-local | −0.16 pp | 12/30 | 29/30 | 30/30 | 1/30 |
| P-local | −0.04 pp | 10/30 | 30/30 | 30/30 | 2/30 |

**By family** (median change under C): F1 −0.26, F2 +0.12, F3 −0.19, F4 −0.40, F5 +0.01 pp. The K-matched reference NF95^K (medians) spans 0.72–9.30 pp.

**Pre-declared interpretation: "local correction possible"** (29/30 engines within NF95^K). Read with the other columns:
- the fleet thresholds were already within the same range for all 30 engines;
- local recalibration increased the median error;
- it brought only 1 engine (C) and 2 engines (P) to the self-calibration floor.

With five healthy flights, local recalibration is therefore not a remedy: its own estimation noise exceeds the fleet-to-engine error it would correct.

DS08a engine 14's out-of-envelope flight (flight 3) lies inside the recalibration window. On its evaluation flights the fleet error is 0.82 pp (C), not 5.39 pp.

## 5. Consequence for the cross-engine transport claim

**Verdict.** Under the pre-declared rule the claim is **STRENGTHENED**: C shows engine-level excess in 5/5 families, and in 3/5 against the more conservative earlier reference. It must, however, be **stated more narrowly** than "broad transport failure".

**What stands.**
- Fleet-calibrated per-engine errors are systematic: they exceed each engine's self-calibration floor in 27 of 30 engines under C.
- They are mostly modest, with a median of 0.63 pp at a 1% target.
- Whether an individual engine's error exceeds sampling noise depends on the reference used (13 to 27 of 30 engines).
- A five-flight local recalibration does not reduce these errors.
- The large failures remain concentrated:
  - classes absent from calibration (DS08c; DS02 engine 14 and DS03 engine 12);
  - one out-of-envelope flight (DS08a engine 14);
  - conditioning that backfired (PCA on DS05/DS06 under C and Q; Q in general).
- Class-preserving resampling narrowed per-subset intervals modestly, and did not change any cross-dataset conclusion.

Nothing else is run. The next stage is manuscript finalization.
