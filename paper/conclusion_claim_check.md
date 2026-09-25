# Conclusion claim check

| Conclusion claim | Evidence IDs | Boundary that must remain attached |
| --- | --- | --- |
| DS02 showed phase-dependent healthy FPR across three tested implementations. | E000107, E000108, E000109, E002627, E002628, E002629, E002987, E002988, E002989 | DS02 is exploratory; Isolation Forest and LSTM values are arithmetic seed means, not evidence of uniform engine or seed effects. |
| Tested static, derivative-based, and finite-history corrections did not eliminate DS02 dependence. | E021498, E021499, E021511, E021512, E021524, E021525 | PCA correction-specification comparison only; exploratory and not repeated as a DS03 comparison. No mechanism is identified. |
| The frozen DS03 pooled directional pattern reproduced. | E010950, E010951, E012861, E012862, E013134, E013135 | The pre-specified point-estimate rule was met once; per-engine exceptions and LSTM intervals including zero remain. |
| Aggregate healthy FPR can hide phase-conditional behaviour. | E000106, E000107, E000108, E000109, E010946, E010947, E010948, E010949 | The 1% target is a calibration quantile, not a guarantee of phase-wise audit FPR. |
| Scope is simulated data, retrospective phase labels, oracle healthy evaluation, and limited engines. | M0001, M0002, M0019, M0031, E010946, E010949; N-CMAPSS descriptor cited as [1] in `paper/introduction.md` | No real-aircraft validity, prospective phase inference, or precise population estimate. Fault recall and detection delay were not evaluated. |
| Agreement among implementations does not establish independence or causation. | E000109, E002629, E002989, E010949, E012860, E013133 | Shared preprocessing, correction, and calibration constrain generalization. |
