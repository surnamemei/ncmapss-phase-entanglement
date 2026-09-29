# Outcome access log (extension)

This log is kept under `GENERALIZATION_PROTOCOL.md` §10.
- **Entries are append-only.** Automated entries are appended by `src/ext_pipeline.py` with UTC timestamps, lock hashes, commit SHAs, run commands and output hashes.
- **Manual entries** are marked as such.

| UTC time | Subset | Event | Detail | Commit | Lock SHA-256 | Command |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-09-28T02:4xZ | DS01, DS04, DS05, DS06, DS07, DS08a, DS08c, DS08d | Byte-only extraction from the official archive (manual entry) | CRC-32 and sizes match the ZIP directory; no HDF5 opened (`archive_extraction_record.json`) | `0fd3f67` (script) | — | `python src/ext_extract_subsets.py` |
| 2026-09-28T02:52:10Z | all candidates, DS02, DS03 | **Metadata opened** (manual entry) | `A_*` complete; `*_var`; `W[:, 0]` for `hs = 1` rows only. DS08d failed to open (C1). No `X_s`, `X_v`, `T`, `Y` or other `W` column was read | `0fd3f67` | — | `python src/ext_subset_metadata.py` |
| 2026-09-28T03:37:13Z | DS01 | Healthy fit and calibration data first opened | hs = 1 rows of fit [1, 2, 3] and calibration [4, 5, 6]; no official-test array | `e3cd95a` | — | `python scripts/run_extension.py lock DS01` |
| 2026-09-28T03:39:50Z | DS01 | **Phase L halted by stop rule** (manual entry) | Non-finite CVAE refit loss (seed 1, epoch 101) on fit-pool healthy rows; no lock written; no official-test array read; partial git-ignored LSTM checkpoints deleted; Amendment 2 | `e3cd95a` | — | `python scripts/run_extension.py lock DS01` |
| 2026-09-28T03:47:41Z | DS01 | Healthy fit and calibration data first opened | hs = 1 rows of fit [1, 2, 3] and calibration [4, 5, 6]; no official-test array | `27a6346` | — | `python scripts/run_extension.py lock DS01` |
| 2026-09-28T04:49:51Z | DS01 | Calibration lock written | thresholds, kappa and composition locked; 3732 s | `e6b6a85` | ec0d79cb0f51 | `python scripts/run_extension.py lock DS01` |
| 2026-09-28T04:50:15Z | DS04 | Healthy fit and calibration data first opened | hs = 1 rows of fit [1, 2, 4] and calibration [3, 5, 6]; no official-test array | `e6b6a85` | — | `python scripts/run_extension.py lock DS04` |
| 2026-09-28T06:07:13Z | DS04 | Calibration lock written | thresholds, kappa and composition locked; 4627 s | `03b1b18` | 575629ef0845 | `python scripts/run_extension.py lock DS04` |
| 2026-09-28T06:07:44Z | DS05 | Healthy fit and calibration data first opened | hs = 1 rows of fit [1, 2, 4] and calibration [3, 5, 6]; no official-test array | `03b1b18` | — | `python scripts/run_extension.py lock DS05` |
| 2026-09-28T07:03:16Z | DS05 | Calibration lock written | thresholds, kappa and composition locked; 3336 s | `03b1b18` | 4fabae04df14 | `python scripts/run_extension.py lock DS05` |
| 2026-09-28T07:03:28Z | DS06 | Healthy fit and calibration data first opened | hs = 1 rows of fit [1, 2, 4] and calibration [3, 5, 6]; no official-test array | `03b1b18` | — | `python scripts/run_extension.py lock DS06` |
| 2026-09-28T07:53:53Z | DS06 | Calibration lock written | thresholds, kappa and composition locked; 3029 s | `03b1b18` | b6b4d6780ac0 | `python scripts/run_extension.py lock DS06` |
| 2026-09-28T07:54:06Z | DS07 | Healthy fit and calibration data first opened | hs = 1 rows of fit [1, 2, 4] and calibration [3, 5, 6]; no official-test array | `03b1b18` | — | `python scripts/run_extension.py lock DS07` |
| 2026-09-28T08:55:22Z | DS07 | Calibration lock written | thresholds, kappa and composition locked; 3681 s | `03b1b18` | 29c0897515a3 | `python scripts/run_extension.py lock DS07` |
| 2026-09-28T08:55:36Z | DS08a | Healthy fit and calibration data first opened | hs = 1 rows of fit [1, 2, 4] and calibration [3, 5, 6, 7, 8, 9]; no official-test array | `03b1b18` | — | `python scripts/run_extension.py lock DS08a` |
| 2026-09-28T11:50:26Z | DS08a | Calibration lock written | thresholds, kappa and composition locked; 10496 s | `03b1b18` | d874adf74a2c | `python scripts/run_extension.py lock DS08a` |
| 2026-09-28T11:50:42Z | DS08c | Healthy fit and calibration data first opened | hs = 1 rows of fit [1, 2, 6] and calibration [3, 4, 5]; no official-test array | `03b1b18` | — | `python scripts/run_extension.py lock DS08c` |
| 2026-09-28T13:10:04Z | DS08c | Calibration lock written | thresholds, kappa and composition locked; 4767 s | `03b1b18` | 50ce8d467484 | `python scripts/run_extension.py lock DS08c` |
| 2026-09-28T13:10:45Z | DS02 | Reference subset re-read (post-confirmation; data opened by the frozen study) | healthy development rows for CVAE training and rescoring | `b9786ce` | — | `python scripts/run_extension.py reference DS02` |
| 2026-09-28T13:35:45Z | DS02 | Reference outputs written | 20 tables; gates passed | `b9786ce` | 686950cc3e7a | `python scripts/run_extension.py reference DS02` |
| 2026-09-28T13:36:17Z | DS03 | Reference subset re-read (post-confirmation; data opened by the frozen study) | healthy development rows for CVAE training and rescoring | `b9786ce` | — | `python scripts/run_extension.py reference DS03` |
| 2026-09-28T14:22:03Z | DS02, DS03 | Reference shakedown attempt 1 superseded (manual entry) | DS03 LSTM healthy-audit fingerprint gate failed (joint healthy+abnormal scoring); outputs archived in `results/extension/_shakedown_attempt1/`; Amendment 3; reference rerun follows | `b9786ce` | — | `python scripts/run_extension.py reference DS02/DS03` |
| 2026-09-28T14:24:54Z | DS02 | Reference subset re-read (post-confirmation; data opened by the frozen study) | healthy development rows for CVAE training and rescoring | `b0ee43c` | — | `python scripts/run_extension.py reference DS02` |
| 2026-09-28T14:26:21Z | DS03 | Reference subset re-read (post-confirmation; data opened by the frozen study) | healthy development rows for CVAE training and rescoring | `b0ee43c` | — | `python scripts/run_extension.py reference DS03` |
| 2026-09-28T15:01:45Z | DS02 | Reference outputs written | 20 tables; gates passed | `b0ee43c` | 5729c40ebb7c | `python scripts/run_extension.py reference DS02` |
| 2026-09-28T15:20:41Z | DS03 | Reference outputs written | 20 tables; gates passed | `b0ee43c` | 8f97e4f2ed63 | `python scripts/run_extension.py reference DS03` |
| 2026-09-28T15:21:20Z | DS01 | Official test sensor data first opened; abnormal rows first opened | all rows of audit engines [7, 8, 9, 10] | `73e4555` | ec0d79cb0f51 | `python scripts/run_extension.py audit DS01` |
| 2026-09-28T15:23:15Z | DS01 | Official audit outputs written | 20 tables; 126 s | `73e4555` | ec0d79cb0f51 | `python scripts/run_extension.py audit DS01` |
| 2026-09-28T15:23:36Z | DS04 | Official test sensor data first opened; abnormal rows first opened | all rows of audit engines [7, 8, 9, 10] | `73e4555` | 575629ef0845 | `python scripts/run_extension.py audit DS04` |
| 2026-09-28T15:26:07Z | DS04 | Official audit outputs written | 20 tables; 169 s | `73e4555` | 575629ef0845 | `python scripts/run_extension.py audit DS04` |
| 2026-09-28T15:26:19Z | DS05 | Official test sensor data first opened; abnormal rows first opened | all rows of audit engines [7, 8, 9, 10] | `73e4555` | 4fabae04df14 | `python scripts/run_extension.py audit DS05` |
| 2026-09-28T15:28:03Z | DS05 | Official audit outputs written | 20 tables; 113 s | `73e4555` | 4fabae04df14 | `python scripts/run_extension.py audit DS05` |
| 2026-09-28T15:28:15Z | DS06 | Official test sensor data first opened; abnormal rows first opened | all rows of audit engines [7, 8, 9, 10] | `73e4555` | b6b4d6780ac0 | `python scripts/run_extension.py audit DS06` |
| 2026-09-28T15:30:02Z | DS06 | Official audit outputs written | 20 tables; 116 s | `73e4555` | b6b4d6780ac0 | `python scripts/run_extension.py audit DS06` |
| 2026-09-28T15:30:15Z | DS07 | Official test sensor data first opened; abnormal rows first opened | all rows of audit engines [7, 8, 9, 10] | `73e4555` | 29c0897515a3 | `python scripts/run_extension.py audit DS07` |
| 2026-09-28T15:32:11Z | DS07 | Official audit outputs written | 20 tables; 126 s | `73e4555` | 29c0897515a3 | `python scripts/run_extension.py audit DS07` |
| 2026-09-28T15:32:34Z | DS08a | Official test sensor data first opened; abnormal rows first opened | all rows of audit engines [10, 11, 12, 13, 14, 15] | `73e4555` | d874adf74a2c | `python scripts/run_extension.py audit DS08a` |
| 2026-09-28T15:35:30Z | DS08a | Official audit outputs written | 20 tables; 196 s | `73e4555` | d874adf74a2c | `python scripts/run_extension.py audit DS08a` |
| 2026-09-28T15:35:47Z | DS08c | Official test sensor data first opened; abnormal rows first opened | all rows of audit engines [7, 8, 9, 10] | `73e4555` | 50ce8d467484 | `python scripts/run_extension.py audit DS08c` |
| 2026-09-28T15:37:32Z | DS08c | Official audit outputs written | 19 tables; 119 s | `73e4555` | 50ce8d467484 | `python scripts/run_extension.py audit DS08c` |
| 2026-09-29T01:53:31Z | DS01 | Focused validation: official-test healthy rows re-read (reproduction only) | hs = 1 rows of audit engines [7, 8, 9, 10]; no abnormal row; plan f734cdf6b5b0 | `6f15aef` | ec0d79cb0f51 | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:54:17Z | DS01 | Focused validation outputs written | 5 tables; gates G1-G5 passed; 59 s | `6f15aef` | ec0d79cb0f51 | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:54:34Z | DS04 | Focused validation: official-test healthy rows re-read (reproduction only) | hs = 1 rows of audit engines [7, 8, 9, 10]; no abnormal row; plan f734cdf6b5b0 | `6f15aef` | 575629ef0845 | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:55:21Z | DS04 | Focused validation outputs written | 5 tables; gates G1-G5 passed; 64 s | `6f15aef` | 575629ef0845 | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:55:32Z | DS05 | Focused validation: official-test healthy rows re-read (reproduction only) | hs = 1 rows of audit engines [7, 8, 9, 10]; no abnormal row; plan f734cdf6b5b0 | `6f15aef` | 4fabae04df14 | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:56:13Z | DS05 | Focused validation outputs written | 5 tables; gates G1-G5 passed; 51 s | `6f15aef` | 4fabae04df14 | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:56:22Z | DS06 | Focused validation: official-test healthy rows re-read (reproduction only) | hs = 1 rows of audit engines [7, 8, 9, 10]; no abnormal row; plan f734cdf6b5b0 | `6f15aef` | b6b4d6780ac0 | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:57:00Z | DS06 | Focused validation outputs written | 5 tables; gates G1-G5 passed; 48 s | `6f15aef` | b6b4d6780ac0 | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:57:10Z | DS07 | Focused validation: official-test healthy rows re-read (reproduction only) | hs = 1 rows of audit engines [7, 8, 9, 10]; no abnormal row; plan f734cdf6b5b0 | `6f15aef` | 29c0897515a3 | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:57:54Z | DS07 | Focused validation outputs written | 5 tables; gates G1-G5 passed; 54 s | `6f15aef` | 29c0897515a3 | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:58:10Z | DS08a | Focused validation: official-test healthy rows re-read (reproduction only) | hs = 1 rows of audit engines [10, 11, 12, 13, 14, 15]; no abnormal row; plan f734cdf6b5b0 | `6f15aef` | d874adf74a2c | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:59:34Z | DS08a | Focused validation outputs written | 5 tables; gates G1-G5 passed; 100 s | `6f15aef` | d874adf74a2c | `python scripts/run_focused_validation.py all` |
| 2026-09-29T01:59:45Z | DS08c | Focused validation: official-test healthy rows re-read (reproduction only) | hs = 1 rows of audit engines [7, 8, 9, 10]; no abnormal row; plan f734cdf6b5b0 | `6f15aef` | 50ce8d467484 | `python scripts/run_focused_validation.py all` |
| 2026-09-29T02:00:43Z | DS08c | Focused validation outputs written | 5 tables; gates G1-G5 passed; 69 s | `6f15aef` | 50ce8d467484 | `python scripts/run_focused_validation.py all` |
