# Reproduction gate: DS02

Overall status: **PASS**

Protocol docs/mssp/post_confirmation_mitigation_protocol.md (SHA-256 `b4a669cdd00d4075…`), git `c2c49f1410a3` on `mssp-revision`.
Started 2026-09-27T14:24:38+00:00; finished 2026-09-27T14:27:31+00:00 (173.3 s).

## Data read

- A arrays fully; W and X_s only as contiguous healthy (hs = 1) row blocks of the development and official-test splits
- Healthy rows scored: calibration 386,643; healthy audit 433,113; model-fit 760,082.
- Abnormal (hs = 0) rows read: False.
- HDF5 MD5 `61056251b36290e11371e017eed70eac` matches provenance; baseline manifest 186 files verified before the run and verified after it.

## Frozen tables regenerated with the unchanged frozen assembly code

| Table | Frozen file | Rows | Status | Byte-identical |
|---|---|---:|---|---|
| rates | `results/final_validation/executed_row_false_alarm_rates.csv` | 672 | exact | yes |
| transfer | `results/final_validation/executed_threshold_transfer_matrix.csv` | 1512 | exact | yes |
| probe | `results/final_validation/executed_score_only_phase_prediction.csv` | 56 | exact | yes |
| detail | `results/final_validation/executed_flight_alarm_detail.csv` | 12768 | exact | yes |
| canonical | `results/final_validation/canonical_results.csv` | 168 | exact | yes |
| per_engine | `results/final_validation/per_engine_phase_fpr.csv` | 21 | exact | yes |
| boundary | `results/final_validation/lstm_boundary_audit.csv` | 222 | exact | yes |
| bootstrap | `results/final_validation/hierarchical_bootstrap_ci.csv` | 49 | exact | no |

## Environment

- Python 3.12.3 (/home/mei/global-python/bin/python)
- GPU NVIDIA GeForce RTX 5090; CUDA 13.0; cuDNN 92400
- Package mismatches against requirements-lock.txt: none

No mitigation endpoint, flight threshold, or lock was computed in this stage.
