# Post-confirmation mitigation report

Post-confirmation, exploratory analysis. The frozen DS03 confirmation verdict and numbers are unchanged and are cited only through the frozen evidence ledger.

## DS02

**Phase-conditioned calibration.** In this post-confirmation, exploratory analysis of simulated N-CMAPSS DS02 data with retrospective (oracle) phase labels, phase-conditioned calibration reduced the healthy phase-FPR spread relative to pooled calibration at the 1% target, and abnormal-state alarm rate and detection delay stayed within the pre-specified interpretive guardrails; intervals were wide with 3 audit engines.

| Family | Mean ΔR (pp) | Alarm-rate ratio (all) | Alarm-rate ratio (early) | Median delay change (flights) | Guardrails met |
|---|---:|---:|---:|---:|---|
| pca | +3.013 | 1.162 | 2.111 | +0 | True |
| isolation_forest | +1.460 | 1.104 | 7.180 | -2 | True |
| lstm_autoencoder | +1.232 | 1.013 | 2.314 | +0 | True |

**Causal-regime calibration (sensitivity/feasibility arm).** In this post-confirmation, exploratory analysis of simulated N-CMAPSS DS02 data with retrospective (oracle) phase labels, causal-regime calibration (sensitivity/feasibility arm) reduced the healthy phase-FPR spread relative to pooled calibration at the 1% target, and abnormal-state alarm rate and detection delay stayed within the pre-specified interpretive guardrails; intervals were wide with 3 audit engines.

| Family | Mean ΔR (pp) | Alarm-rate ratio (all) | Alarm-rate ratio (early) | Median delay change (flights) | Guardrails met |
|---|---:|---:|---:|---:|---|
| pca | +2.947 | 1.162 | 2.633 | +0 | True |
| isolation_forest | +1.651 | 1.114 | 7.570 | -2 | True |
| lstm_autoencoder | +1.173 | 1.044 | 2.833 | +0 | True |

## DS03

**Phase-conditioned calibration.** In this post-confirmation, exploratory analysis of simulated N-CMAPSS DS03 data with retrospective (oracle) phase labels, phase-conditioned calibration reduced the healthy phase-FPR spread relative to pooled calibration at the 1% target, and abnormal-state alarm rate and detection delay stayed within the pre-specified interpretive guardrails; intervals were wide with 6 audit engines.

| Family | Mean ΔR (pp) | Alarm-rate ratio (all) | Alarm-rate ratio (early) | Median delay change (flights) | Guardrails met |
|---|---:|---:|---:|---:|---|
| pca | +0.475 | 1.062 | 1.123 | -6 | True |
| isolation_forest | +1.314 | 1.010 | 1.050 | +0 | True |
| lstm_autoencoder | +1.144 | 0.996 | 1.188 | +0 | True |

**Causal-regime calibration (sensitivity/feasibility arm).** In this post-confirmation, exploratory analysis of simulated N-CMAPSS DS03 data with retrospective (oracle) phase labels, causal-regime calibration (sensitivity/feasibility arm) reduced the healthy phase-FPR spread relative to pooled calibration at the 1% target, and abnormal-state alarm rate and detection delay stayed within the pre-specified interpretive guardrails; intervals were wide with 6 audit engines.

| Family | Mean ΔR (pp) | Alarm-rate ratio (all) | Alarm-rate ratio (early) | Median delay change (flights) | Guardrails met |
|---|---:|---:|---:|---:|---|
| pca | +0.231 | 1.076 | 1.157 | -4 | True |
| isolation_forest | +0.871 | 0.983 | 1.092 | +0 | True |
| lstm_autoencoder | +1.236 | 0.989 | 1.847 | +0 | True |

Guardrails are interpretive, not non-inferiority margins; full estimates and intervals are in the stage D and E tables.
