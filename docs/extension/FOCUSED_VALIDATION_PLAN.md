# Focused validation plan (final; post hoc) — FROZEN v1.0

**Authorization.** On 2026-09-29, the author approved one final focused validation, after the hostile review (`EXTENSION_HOSTILE_REVIEW.md`), with three components:
1. an engine-specific sampling-noise floor;
2. a calibration-class-preserving bootstrap;
3. a per-engine local recalibration diagnostic.

**What is not authorized.** No additional models, datasets, alarm policies, metrics or literature-driven experiments. The alarm-persistence analysis is not expanded; the existing two-flight confirmation result stays as labelled post hoc robustness only.

**Status of this analysis.**
- It is post hoc: every extension outcome already exists.
- It changes no pre-specified H1–H7 decision, lock, output or table; all frozen and extension outputs are preserved.
- After it completes, scientific analysis stops permanently, whatever the outcome. The next stage is manuscript finalization.

**Freeze rule.** This plan is committed before any official-test sensor value is re-read. The run refuses to start unless this file is tracked, clean and hash-verified.

## 1. Data, models and access

- **Subsets.** The seven new subsets (DS01, DS04, DS05, DS06, DS07, DS08a, DS08c), processed in the frozen order. DS02 and DS03 are not used.
- **Official-test rows.** Only healthy (`hs = 1`) rows of the audit engines are read (`ext_models.load_audit_rows(..., healthy_only=True)`). No abnormal (`hs = 0`) row is read, and no abnormal row enters any threshold.
- **Models.** The saved, locked models of each subset (hashes verified against the lock). Nothing is fitted or retrained. Calibration rows are rescored only for the gates and the bootstrap.
- **Runs.** All 10 runs per subset: PCA; Isolation Forest, LSTM and CVAE with seeds 0–2.
  - The seven residual runs are primary.
  - The CVAE runs are reported separately.
- **Target.** α = 1% only.
- **Mode.** Reproduction-only. Outputs are written by exclusive create into `results/extension/focused_validation/`. Nothing under `results/extension/<subset>/{lock,audit}/` is modified.
- **Access log.** Each re-read is appended to `OUTCOME_ACCESS_LOG.md` with this plan's SHA-256.

## 2. Gates (any failure stops the run and is reported)

- **G1.** The 186-file frozen baseline manifest verifies before and after the run.
- **G2.** This plan and the validation code are git-tracked and clean. The plan's SHA-256 is recorded.
- **G3.** The lock hash equals its record, and the model files equal the lock hashes. Rescored calibration scores reproduce the lock's calibration fingerprints for all 10 runs.
- **G4.** From the rescored healthy audit scores, the locked P, C and Q thresholds must reproduce exactly, for every run, arm and target:
  - the committed per-engine, per-phase healthy row and alarm counts (`audit/phase_fpr.csv`);
  - the committed per-flight healthy R0 alarm counts (`audit/flight_trajectories.csv`).
- **G5.** The original U-EXT1 design, rerun with its seed (20260929), reproduces the committed replicate table `audit/bootstrap_uext1_replicates_alpha_0.01.csv` exactly.
- **G6.** The U-EXT2 routine, applied to the committed replicates with its seed (20261002), reproduces the committed `summary/uext2_cross_dataset.csv`.

## 3. Component 1: engine-specific sampling-noise floor

**Observed fleet-calibrated error.** For each audit engine e, run r and arm a ∈ {P, C, Q}, the observed error is A2_e = max over phases of |FPR_{e,φ} − α|. It is computed over all of the engine's healthy flights with the locked fleet thresholds, and equals the committed per-engine values (G4).

**Noise reference: repeated 5-fold cross-fit over the engine's own healthy flights.** For engine e and run r, with R = 200 repetitions:
- **Seeding.** `numpy.random.default_rng([20261004, s, r, e])`, where s is the subset's index in the frozen order (DS01 = 0, …, DS08c = 6), r is the run index in protocol order (0–9) and e is the engine number.
- **Folds.** Randomly permute the engine's healthy flights and split them into 5 folds of near-equal size (`numpy.array_split`).
- **Out-of-fold thresholds.** For each fold, compute per-phase thresholds from the engine's rows in the other four folds: the upper 1 − α quantile with `method="higher"`, per phase. Apply them to the rows of the held-out fold.
- **Cross-fit error.** The out-of-fold alarms cover all of the engine's healthy rows. The cross-fit error is A2^cf = max over phases of |FPR^cf_φ − α|.

The thresholds come from the engine's own flights in each phase, so A2^cf contains no transport and no phase-mixing error, only error from the engine's finite number of healthy flights. Its distribution over the 200 repetitions is the engine-specific noise reference, with median NF50 and 95th percentile NF95.

The reference is conservative. Its thresholds are estimated from about 80% of one engine's flights, whereas the fleet thresholds come from a larger calibration pool. It therefore overstates noise, and exceedances are counted conservatively.

**Criterion** (no universal 0.5-pp line):
- For each run, record whether A2_e > NF95_e.
- An engine **clearly exceeds its own noise reference** under arm a if this holds in ≥ 4 of its 7 residual runs; the CVAE is reported separately, requiring ≥ 2 of 3 runs.
- Also reported: A2_e / NF50_e and A2_e − NF95_e (medians over residual runs).
- A fleet family **shows transport excess** under arm a if at least half of its audit engines clearly exceed.

## 4. Component 2: calibration-class-preserving bootstrap

**Original design (reproduced by G5).** The per-subset engine → flight bootstrap U-EXT1:
- 2,000 replicates, `default_rng(20260929)`;
- calibration plans drawn first, then audit plans;
- P and C thresholds re-estimated in every replicate.

**Class-preserving design.** The calibration plans are replaced; everything else is unchanged.
- **Calibration plans.** In each replicate, for every flight class in the original calibration pool, draw as many engines as the class has, with replacement, from that class's engines only. Then resample each drawn engine's flights with replacement.
  - Every calibration class is therefore present in every replicate.
  - Classes with one engine always keep it.
  - Seed: `default_rng([20261003, s])`.
- **Audit plans.** The identical audit plans of the original design. Calibration and audit resampling stay separate, and any change in an interval is due only to class preservation.

**Quantities.** At α = 1%, for every subset and run, the percentile 95% intervals of:
- the C − P differences in pooled A1, pooled A2, ME-A2 and WE-A2;
- ME-A2 and WE-A2 under P and under C.

**Width comparison.** For each interval, width_cp / width_orig. The **share of the original width due to class omission** is 1 − width_cp / width_orig, summarized by median per subset and quantity. Also reported: whether each interval includes zero under each design.

**Cross-dataset intervals.** The U-EXT2 quantities are recomputed from the class-preserving replicates with the same routine and seed (20261002), and compared with the committed U-EXT2 table.

## 5. Component 3: per-engine local recalibration diagnostic

**K is frozen now: K = 5 initial healthy flights per audit engine** (chronological by cycle). It was chosen from design constants only (metadata, not outcomes):
- audit engines have 14–36 healthy flights;
- the first 5 healthy flights of every audit engine contain ≥ 3,634 healthy rows per phase (≥ 36 expected exceedances per phase at α = 1%);
- at least 9 flights (≥ 20,621 rows per phase) remain for evaluation;
- K = 3 would leave as few as 2,164 rows per phase, and K = 8 or 10 would leave only 6 or 4 evaluation flights for the smallest engine.

K is not tuned, and no other K is evaluated.

**Local thresholds** (healthy rows only; no abnormal row is used):
- **P-local:** the upper 1 − α quantile (`higher`) of all of the engine's rows in its first K healthy flights.
- **C-local:** per-phase upper 1 − α quantiles of those rows.

Q is not recalibrated locally, because that would require fitting new quantile-regression models.

**Evaluation.** On the same engine's remaining healthy flights (K + 1 … n):
- A2^local under P-local and C-local;
- the fleet-calibrated A2^fleet (locked P and C thresholds) on the same evaluation flights;
- the improvement A2^fleet − A2^local.

**Noise reference for a K-flight local threshold** (same scheme, matched design):
- R = 200 random draws of K flights without replacement from the engine's healthy flights, seeded with `default_rng([20261005, s, r, e])`;
- per-phase thresholds from the drawn flights;
- A2 on the engine's other flights.

The 95th percentile is NF95^K. Local recalibration **brings an engine into the sampling-noise range** under arm a if A2^local ≤ NF95^K in ≥ 4 of 7 residual runs. The component-1 reference (NF95) is also reported.

**Summaries.** Per engine (median over residual runs) and per fleet family (median over the family's engines):
- improvement;
- A2^local relative to NF95^K and NF95;
- the share of engines brought into the noise range.

## 6. Pre-declared interpretation (fixed now)

**Cross-engine transport claim** (component 1; arm C primary, P and Q reported):
- **STRENGTHENED:** C shows transport excess in ≥ 3 of 5 families. The claim of engine-level non-transport stands, with an engine-specific noise reference.
- **NARROWED:** C shows transport excess in 1–2 families. The headline becomes "failures concentrated in uncovered or atypical engines and flights", naming the engines that clearly exceed.
- **WEAKENED:** C shows transport excess in no family. Fleet-to-engine errors are then within the engines' own sampling noise, and the transport claim is withdrawn as unresolvable at this sample size.

**Local recalibration** (component 3; C-local primary): "local correction possible" if the majority of engines are brought into the noise range; otherwise "not correctable with K = 5 healthy flights".

**Bootstrap** (component 2): descriptive; no decision rule.

## 7. Outputs and reporting

**Outputs** under `results/extension/focused_validation/`:
- **Per subset:**
  - `engine_noise_floor.csv` (per engine × run × arm: observed A2, NF50, NF95, exceeds);
  - `noise_floor_draws.csv` (per engine × run: the 200 cross-fit A2 values);
  - `local_recalibration.csv`;
  - `bootstrap_class_preserving_ci.csv`;
  - `bootstrap_class_preserving_replicates_alpha_0.01.csv`;
  - `validation_record.json` (gates, hashes, timings).
- **Summary:** engine and family summaries, bootstrap width comparison, class-preserving U-EXT2, and `focused_validation_summary.json`.

**Reported to the author:**
- per-engine observed error against the engine-specific noise floor;
- the share of engines clearly exceeding their own reference;
- original against class-preserving bootstrap intervals;
- local-recalibration improvement per engine and family;
- whether local recalibration reaches the noise range;
- whether the transport claim is strengthened, narrowed or weakened under §6;
- the exact final manuscript wording changes.

No further experiment is proposed or run.
