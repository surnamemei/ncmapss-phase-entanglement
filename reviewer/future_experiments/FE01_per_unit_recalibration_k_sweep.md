# FE01: per-unit recalibration with k ∈ {3, 10} and causal re-baselining (prepared, not run)

**Scientific question.** The focused validation showed that recalibrating on each engine's first five healthy flights (k = 5)
did not reduce per-engine A2 (§4.8; C032). Does the conclusion change for fewer (k = 3) or more (k = 10) flights? Does a causal,
rolling re-baseline (thresholds updated from the most recent healthy flights) behave differently?

**Trigger.** Run only if a reviewer asks for a per-unit or practitioner recalibration baseline, or disputes the k = 5 choice
(Q24, I-09).

**Required inputs.**
- The locked models `results/extension/<DS>/models/*` (git-ignored; 84/84 hash-verified on 2026-09-29).
- Raw `N-CMAPSS/*.h5` for audit healthy rows.
- The lock files `results/extension/<DS>/lock/calibration_lock.json`.

**Reusable existing data.**
- `results/extension/focused_validation/*/local_recalibration.csv` and `noise_floor_draws.csv` (the k = 5 reference).
- The code path `src/ext_focused_validation.py:local_recalibration`, `k_matched_draws`, which is to be reused by import, not edited.

**New computation.**
- Re-score healthy audit rows with the locked models; the LSTM and CVAE need CUDA.
- Per engine and run: fit P and C thresholds on the first k healthy flights, evaluate on the remaining flights, and build a
  matched reference of 200 random k-flight subsets.
- Engines with fewer than k + 5 healthy flights are excluded, and the exclusion rule is fixed in advance.

**Proposed script.** `scripts/run_reviewer_fe01.py`, a new file. It must:
- use a new output root, e.g. `results/reviewer_fe01/`;
- refuse to write inside `results/extension/`;
- append an access-log entry.

**Expected outputs.**
- A per-engine table of fleet A2, local A2 and NFK95 for k = 3, 5 and 10.
- Summary counts: engines improved in a majority of runs, and the median change.

**Compute estimate.** GPU re-scoring of 7 subsets × 10 runs for healthy audit rows only. The hostile review estimated this at
"under one hour of GPU time" (`docs/extension/EXTENSION_HOSTILE_REVIEW.md` §6), plus minutes of CPU analysis. It is GPU
because of the LSTM and CVAE. PCA and IF can be scored on CPU, but the 7 residual runs include 3 LSTM seeds.

**What it could support.** Whether the k = 5 conclusion depends on k. It would also show whether per-unit re-baselining is a
practical remedy at this data size.

**What it could not support.**
- Any deployment claim.
- Real-fleet generalization.
- A change to the pre-specified decisions in Table 4, which would stay unchanged.
