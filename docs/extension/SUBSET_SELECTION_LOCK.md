# Subset selection lock (extension stage 1)

**Status.** Part 1 (the criteria) was committed **before** the metadata audit ran. Part 2 (results and cohorts) is added by the metadata-audit commit. Both parts precede any read of new sensor values.

## Part 1. Objective eligibility criteria (fixed before the metadata audit)

**Candidates.** Every HDF5 member of the local official NASA archive other than DS02 and DS03. Extraction on 2026-09-28 found:
- DS01;
- DS04, DS05, DS06 and DS07;
- DS08a, DS08c and DS08d.

Extraction copied bytes only (`docs/extension/archive_extraction_record.json`). DS02 and DS03 were already opened by the frozen study. They are audited with the same code as references, but they are not candidates.

**What the metadata audit may read:**
- file bytes (hashes);
- the HDF5 object tree, shapes, dtypes and chunk layout;
- the `*_var` name arrays;
- the complete `A_dev` and `A_test` arrays (unit, cycle, Fc, hs);
- the altitude column `W[:, 0]`, only for `hs = 1` rows. The altitude is an exogenous flight-profile input, and the frozen primary phase rule needs only it.

**What it must not read:**
- `X_s`, `X_v`, `T` or `Y` values;
- the other `W` columns;
- any `hs = 0` altitude;
- scores, residuals or phase FPRs.

| ID | Criterion (primary generalization cohort) | Operational test |
| --- | --- | --- |
| **C1** | Valid HDF5 integrity | The size and CRC-32 equal the official ZIP directory (checked at extraction). The file opens in h5py. `A`, `W` and `X_s` exist for both `dev` and `test`, and so do `A_var`, `W_var` and `X_s_var`. Within each split, every row-indexed array present (`A`, `W`, `X_s`, `X_v`, `T`, `Y`) has the same row count. Each `*_var` length equals its array width. `A` values are finite integers with unit ≥ 1, cycle ≥ 1, Fc ∈ {1, 2, 3} and hs ∈ {0, 1} |
| **C2** | Same 14 measured sensor channels | `X_s_var` equals the frozen `SENSORS` list, in order |
| **C3** | Operating descriptors required by the residualization and context models | `W_var` equals `["alt", "Mach", "TRA", "T2"]` |
| **C4** | Health-state labels identify healthy calibration data and abnormal-state onset | `A_var` equals `["unit", "cycle", "Fc", "hs"]`. Every engine satisfies LS-1: `hs` starts at 1, is monotone non-increasing and has at most one transition. Every engine also satisfies LS-2: `hs` is constant within every flight. Every development engine has ≥ 1 healthy flight. At least 3 official test engines have ≥ 1 healthy **and** ≥ 1 post-onset flight |
| **C5** | Complete flight/cycle identifiers | Every engine's rows are contiguous within its split. The rows of every flight (unit, cycle) are contiguous. Cycles are strictly increasing, contiguous integers per engine. No unit appears in both splits. Fc is constant per engine |
| **C6** | ≥ 3 official development engines | Distinct units in `A_dev` |
| **C7** | ≥ 3 official test (audit) engines | Distinct units in `A_test`, each with ≥ 1 healthy flight |
| **C8** | Healthy complete flights support every primary retrospective phase | A healthy flight is *phase-complete* if its altitude range is positive and the frozen 90% rule (`confirm_frozen_ds03.primary_phase`) gives non-empty climb, cruise and descent segments. Required: ≥ 99% of the dataset's healthy flights are phase-complete; every engine has ≥ 1 phase-complete healthy flight; and every official test engine has ≥ 1,000 healthy rows in each of climb, cruise and descent (≥ 5 expected alarms per engine and phase at α = 0.5%) |
| **C9** | No prior outcome inspection by this project | The file was never extracted or opened before 2026-09-28: only DS02 and DS03 existed in extracted form (protocol L16; extraction record). No commit reachable from `mssp-pre-extension-2026-09-28` references the subset in `src/`, `scripts/`, `configs/`, `results/` or `tests/`. Literature results by other authors (for example, Hsu et al. 2023 on DS04, DS05 and DS07, cruise only) are external, and they are disclosed rather than treated as project outcomes |

**Cohort rules** (applied mechanically to the audit results):
- **PRIMARY GENERALIZATION COHORT.** Every candidate that passes C1–C9.
- **STRESS-TEST COHORT.** Only a candidate that passes C1–C3, C5, C6, C8 and C9 but fails an engine-count or label-support part of C4 or C7, while still having ≥ 2 official test engines with healthy flights. Such a subset may contribute healthy-side endpoints only. It is reported separately and never pooled with the primary cohort. A candidate failing C1, C2, C3, C5, C8 or C9 is **excluded**, and the reason is recorded before any sensor value is read.
- **No moves.** No subset moves between cohorts after any outcome is seen. The whole cohort runs through one frozen pipeline in numeric-then-letter order (DS01, DS04, DS05, DS06, DS07, DS08a, DS08c, DS08d).
- **No reputation-based choices.** No candidate is included or excluded because an external repository called it easy, difficult, corrupted or unusual.

**Composition-intervention eligibility** is decided separately in the generalization protocol. It depends on whether the development engines can be split, by metadata alone, into a fit pool and a calibration-composition pool that covers ≥ 2 flight classes (brief §6). A subset that cannot support that split still contributes to the generalization audit.

## Part 2. Metadata audit results and cohort assignment

**Run.**
- `src/ext_subset_metadata.py` ran on 2026-09-28 (02:52:10Z–02:52:17Z) at the criteria commit `0fd3f67`.
- **Evidence:**
  - `docs/extension/subset_metadata_audit.csv`;
  - `docs/extension/subset_engine_metadata.csv`;
  - `docs/extension/subset_metadata_audit.json`, which holds the HDF5 trees, variable names, a read log per file and the criterion evaluation;
  - `results/extension/metadata/healthy_flight_phase_segments.csv`, one row per healthy flight.

**What was read, per file:**
- the `*_var` name arrays;
- the complete `A_dev` and `A_test` arrays;
- `W_dev[:, 0]` and `W_test[:, 0]` (altitude), for `hs = 1` rows only.

**What was not read:** `X_s`, `X_v`, `T` or `Y`, the other `W` columns, or any `hs = 0` altitude. No model was fitted or scored, and no rate was computed.

| Subset | Result | Dev engines (unit:class) | Test engines (unit:class) | Healthy flights dev / test | Post-onset flights test | Healthy rows dev / test | C1–C9 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DS01 | PRIMARY | 1:1 2:3 3:2 4:1 5:3 6:2 | 7:1 8:2 9:1 10:3 | 158 / 111 | 230 | 1,276,402 / 778,379 | ✓✓✓✓✓✓✓✓✓ |
| DS02 | reference (frozen study) | 2:3 5:3 10:3 16:3 18:3 20:3 | 11:3 14:1 15:2 | 95 / 76 | 126 | 1,146,725 / 433,113 | ✓✓✓✓✓✓✓✓✗ |
| DS03 | reference (frozen study) | 1:1 2:2 3:2 4:2 5:1 6:3 7:2 8:3 9:1 | 10:3 11:3 12:1 13:3 14:1 15:2 | 237 / 148 | 290 | 1,849,271 / 1,294,679 | ✓✓✓✓✓✓✓✓✗ |
| DS04 | PRIMARY | 1:2 2:3 3:2 4:3 5:3 6:3 | 7:2 8:2 9:2 10:3 | 105 / 79 | 265 | 1,288,708 / 779,384 | ✓✓✓✓✓✓✓✓✓ |
| DS05 | PRIMARY | 1:2 2:3 3:2 4:1 5:1 6:3 | 7:2 8:1 9:3 10:1 | 153 / 112 | 215 | 1,240,824 / 803,959 | ✓✓✓✓✓✓✓✓✓ |
| DS06 | PRIMARY | 1:2 2:3 3:2 4:1 5:1 6:3 | 7:2 8:1 9:3 10:1 | 141 / 100 | 222 | 1,150,965 / 721,888 | ✓✓✓✓✓✓✓✓✓ |
| DS07 | PRIMARY | 1:2 2:3 3:2 4:1 5:1 6:3 | 7:2 8:1 9:3 10:1 | 154 / 113 | 231 | 1,252,737 / 808,457 | ✓✓✓✓✓✓✓✓✓ |
| DS08a | PRIMARY | 1:1 2:3 3:1 4:2 5:2 6:3 7:2 8:2 9:1 | 10:1 11:2 12:3 13:3 14:3 15:1 | 197 / 122 | 261 | 1,527,036 / 1,121,583 | ✓✓✓✓✓✓✓✓✓ |
| DS08c | PRIMARY | 1:3 2:3 3:3 4:3 5:3 6:2 | 7:2 8:2 9:2 10:2 | 100 / 86 | 151 | 1,349,802 / 758,018 | ✓✓✓✓✓✓✓✓✓ |
| DS08d | EXCLUDED | — | — | — | — | — | ✗ (C1) |

Additional checks:
- Every engine in every file satisfies LS-1 and LS-2.
- Cycles are contiguous and Fc is constant per engine.
- Every healthy flight is phase-complete (share 1.000 in every subset).
- The smallest per-engine, per-phase healthy row count among test engines is 24,255 (DS08a), far above the 1,000-row minimum.

### Cohorts (applied mechanically; final)

- **PRIMARY GENERALIZATION COHORT:** DS01, DS04, DS05, DS06, DS07, DS08a and DS08c. These are 7 subsets with 30 official test (audit) engines in total.
- **STRESS-TEST COHORT:** none. No candidate met the stress-test rule, so none is created.
- **EXCLUDED:** DS08d. Its failure was **C1 (HDF5 integrity)**. The member `data_set/N-CMAPSS_DS08d-010.h5` is byte-identical to the official ZIP directory entry (2,885,034,848 bytes, CRC-32 `c3acd78a`, SHA-256 `693b035b…`). HDF5 nevertheless refuses to open it: "truncated file: eof = 2885034848, stored_eof = 2885034880". The official file is therefore 32 bytes shorter than its own superblock declares.
  - Nothing was read from it.
  - It is not repaired, padded or opened by any other means.
  - It stays excluded whatever the other subsets show.
- **References:** DS02 and DS03 are re-used as the frozen study's reference subsets, not as new evidence.
- **Audit order (frozen):** DS01, DS04, DS05, DS06, DS07, DS08a, DS08c.

### Structural finding from metadata: the subsets share flight profiles

Healthy flights were compared by an altitude-derived signature: row count, climb, cruise and descent segment sizes, and altitude span (`src/ext_profile_sharing.py`; `docs/extension/profile_sharing_engine_pairs.csv`; `docs/extension/profile_sharing_by_dataset.csv`). The comparison shows that the subsets reuse a common library of recorded flights.

- **DS05, DS06 and DS07 are one fleet flying the same missions.** Each of units 1–10 has an identical healthy flight sequence in all three subsets, flight by flight. The subsets differ in failure mode and onset time; DS06's healthy periods are 1–4 flights shorter. Whether their healthy *sensor* values also coincide cannot be known from metadata. It is checked at data opening by hash comparison only (protocol §2).
- **Whole engines recur across subsets:**
  - DS01 test unit 7 ≡ DS03 development unit 9 (35/35 flights);
  - DS08a test unit 15 ≡ DS03 development unit 5 (27/27);
  - DS01 development unit 2 ≡ DS08a test unit 14 (15/15).
- **Flight reuse is pervasive.** 84–100% of each new subset's healthy flights have a signature that also occurs in another subset. For 45–77%, that other subset is DS02 or DS03.
- **Class-1 (short) flights come from a small route library.** Class-1 engines of the same subset share 11–16 of their 13–18 distinct healthy flight profiles, and in DS03 this includes fit engines {1, 5, 9} and audit engines {12, 14}. The DS03 class-1 audit engines' routes were therefore present in the *fit* data but absent from the *calibration* data.

**Consequence.** The seven new subsets are **not seven independent replications**. The generalization protocol therefore:
- groups subsets into **fleet families**, with {DS05, DS06, DS07} as one family;
- uses families as the top level of cross-dataset inference;
- reports every directional count at both the family and the subset level.

This is decided now, from metadata only, before any outcome exists.

**External knowledge disclosed.** Hsu, Frusque and Fink (2023) reported cruise-only, unit-level results on DS04, DS05 and DS07 with other detectors and splits. No project outcome on any new subset exists, and no subset was chosen or excluded because of that work.
