# Reproduction gate: DS03

Overall status: **PASS**

Protocol docs/mssp/post_confirmation_mitigation_protocol.md (SHA-256 `b4a669cdd00d4075…`), git `c2c49f1410a3` on `mssp-revision`.
Started 2026-09-27T14:27:31+00:00; finished 2026-09-27T14:31:11+00:00 (219.2 s).

## Data read

- A arrays fully; W and X_s only as contiguous healthy (hs = 1) row blocks of the development and official-test splits
- Healthy rows scored: calibration 458,105; healthy audit 1,294,679.
- Abnormal (hs = 0) rows read: False.
- HDF5 MD5 `a301cd2cfa9b7da6e6ec12051ded9afe` matches provenance; baseline manifest 186 files verified before the run and verified after it.

## Frozen tables regenerated with the unchanged frozen assembly code

| Table | Frozen file | Rows | Status | Byte-identical |
|---|---|---:|---|---|
| rates | `results/confirmation_ds03/row_false_alarm_rates.csv` | 588 | exact | yes |
| transfer | `results/confirmation_ds03/threshold_transfer_matrix.csv` | 1323 | exact | yes |
| detail | `results/confirmation_ds03/flight_alarm_detail.csv` | 12432 | exact | yes |
| summary | `results/confirmation_ds03/flight_alarm_summary.csv` | 588 | exact | yes |
| canonical | `results/confirmation_ds03/canonical_results.csv` | 147 | exact | yes |
| bootstrap | `results/confirmation_ds03/hierarchical_bootstrap_ci.csv` | 49 | exact | no |

## Calibration thresholds against the frozen lock

`results/confirmation_ds03/calibration_lock.json`: 84 values, status **exact**, exact 84/84.

## Environment

- Python 3.12.3 (/home/mei/global-python/bin/python)
- GPU NVIDIA GeForce RTX 5090; CUDA 13.0; cuDNN 92400
- Package mismatches against requirements-lock.txt: none

No mitigation endpoint, flight threshold, or lock was computed in this stage.
