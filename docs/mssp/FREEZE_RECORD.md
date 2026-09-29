# Freeze record: MSSP post-confirmation mitigation protocol v1.0

## Freeze commit

- **Commit:** `546e5d8a14e6077629d384ca4b0ef05438a6b377` on branch `mssp-revision`.
- **Committed:** 2026-09-28T00:23:21+10:00.
- **Parent:** `1f59e9e`, the RESS-submitted state.
- **Approval:** the author approved the protocol direction and decisions D-2, D-3, D-5, D-8, and D-9 on 2026-09-27. The remaining decisions took the recommended defaults (protocol §12).
- **Data access:** none. No N-CMAPSS HDF5 content was read and no model was fitted, loaded, or scored before or at this commit.

## Frozen artifacts (SHA-256 at the freeze commit)

| File | SHA-256 |
| --- | --- |
| `docs/mssp/post_confirmation_mitigation_protocol.md` | `b4a669cdd00d40753b4b7cca3576ab701f69a19b333a5ff216e21be86a33cacb` |
| `docs/mssp/frozen_baseline.sha256` | `37c0cef26826bef2b3ee503d89823530a639581133fbea029d775821f2545a60` |
| `configs/mssp_mitigation.yaml` | `23bb3b04559162f3538f6eaa3bdd14d5324df316b97f0d49be3ac11361cee144` |
| `src/mssp_mitigation.py` | `2764f27113a0c7af84772817c48cafe3a67efc24e807ad0efb9b25ed56fc113b` |
| `scripts/run_mssp_mitigation.py` | `8f69dc7561ee69c6fb61547881c8d4d7d5e2cce99c05d0ea2faf51b28880f75a` |
| `tests/test_mssp_mitigation.py` | `4586811e06ca6511819393983707cad7f1aad1a809d7d95dceedb75a08160144` |

## Checks at freeze

- **Baseline manifest:** 186 of 186 frozen files verified with `sha256sum -c`. They cover the tracked results, the frozen code, configs, scripts, and tests, the RESS package, and 12 LSTM checkpoints.
- **Data-free tests:** 39 passed: the 14 existing tests unchanged, plus 25 new ones.
  - Interpreter: `/home/mei/global-python/bin/python` (Python 3.12.3, torch 2.14.0+cu130). Package versions equal `requirements-lock.txt`.
  - On synthetic data, the new pooled-arm bootstrap reproduces the frozen `bootstrap_one_model` exactly.
  - On a synthetic HDF5 file, the healthy-block loaders equal the frozen DS02 and DS03 loaders.
- **Synthetic benchmark (DS03-like shapes, no data):** U1 ≈ 3.4 min and U2 ≈ 7.7 min for 2,000 replicates × 7 runs.

## RESS snapshot

- The annotated tag `ress-submission-2026-09-25` points to `1f59e9e`. It was created locally and has not been pushed; no GitHub Release was created.
- The release tag `v1.0.0` (`24c2836`) is unchanged.

## Authorized next step

The author authorized Stages B and C only: the label structure and the integrity/reproduction gate on healthy rows. Execution stops for author review after the gate.

Stages L and D follow only after that review. Stage E, which opens abnormal-state rows, requires separate explicit approval.
