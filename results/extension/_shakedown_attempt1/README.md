# First shakedown attempt (superseded; kept for transparency)

DS02 and DS03 reference work, first attempt (2026-09-28, 12:58–14:20Z, code at `b9786ce`):
- **DS02** completed, and all of its gates and all eight cell-by-cell shakedown checks passed.
- **DS03** stopped at the healthy-audit fingerprint gate: the LSTM seed 0 scores differed from the frozen Stage C fingerprint.

**Cause.** Healthy and abnormal audit rows were scored in one call. LSTM scores depend at float32 rounding level on GPU batch composition, whereas the frozen stages scored healthy rows and abnormal rows in separate calls.

**Fix.** Amendment 3 (`docs/extension/AMENDMENTS.md`) scores healthy and post-onset rows separately in every audit.

**Status.** These outputs are superseded by the rerun under Amendment 3. They are kept unchanged. The fitted model binaries were removed; CVAE training is deterministic and was redone in the rerun.
