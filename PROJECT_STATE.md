# Project State

Recovery sheet for `ncmapss-phase-entanglement`, written 2026-09-29 by a documentation-only audit. The audit
changed no code, manuscript, result, figure, config, frozen artifact, tag or branch. The reviewer package is in
`reviewer/`; start with `reviewer/REBUTTAL_NAVIGATION.md`.

> **Git status of these notes.** `PROJECT_STATE.md` and `reviewer/` were left **untracked** on purpose.
> `tests/test_public_release.py` (lines 156–158) asserts that the set of git-tracked files equals the v1.1.0
> release manifest `docs/release/v1.1.0/PUBLIC_RELEASE_MANIFEST.sha256`. Committing these notes to `main` would break
> that test, `scripts/run_public_tests.py` and the GitHub Actions job on the next push. They also contain reviewer
> strategy that should not go to the public remote. To keep them under version control, commit them on a private
> local branch, e.g. `git switch -c reviewer-notes && git add PROJECT_STATE.md reviewer && git commit`, and
> never push that branch.

## Scientific status

**Preprint and journal manuscript, public release v1.1.0; journal submission status not recorded in the repository.**

- `main` = tag `v1.1.0` = commit `3a4de78` (2026-09-29), tracking public `origin/main`. It is a sanitized single-snapshot
  public release plus two CI-test commits (`e2f9f37`, `3a4de78`, tests and manifest only).
- **Update, archival cleanup (2026-09-29, about 17:50).** This file was written against `3a4de78`, but `main` has since moved.
  - **New commit.** The user committed `1519ed7` at 17:31, after this audit: "Final pre-submission wording and
    code-availability update" (unpushed; `main` is ahead of `origin/main` by 1).
  - **What it changed.** Wording of the Abstract, Highlights, Discussion, Conclusion and Code availability; the Table 4
    verdict label; `verify_numbers.py`; two ledger rows; and figure provenance records. It also added
    `docs/release/v1.1.0/POST_RELEASE_CHANGES.sha256`.
  - **Verification.** `verify_numbers.py` passes on `1519ed7` (78 claims).
  - **Upload staged.** A non-Git bundle `../ncmapss-phase-entanglement-mssp-upload/` (17:40) holds `manuscript.pdf`
    `a62289df…`, which is `latex/main.pdf` at `1519ed7`.
  - **Not re-audited.** Quotations in `reviewer/` that come from the Abstract or Highlights may predate this wording.
  - **See also** `../SUBMISSION_LEDGER.md`.
- The README calls the manuscript "an author preprint and has not undergone peer review for the current journal
  submission". The manuscript source header (`paper/mssp_extended/manuscript_mssp_draft.md`, line 3) still says
  "complete draft for author approval; not submitted". The private branch `mssp-extended` (`54b25ee`) says "not submitted".
  **UNKNOWN** whether the MSSP upload happened: there is no manuscript ID, portal record or submission date.
- Earlier, narrower DS02/DS03 version: tag `ress-submission-2026-09-25` (= `v1.0.0`, `1f59e9e`). According to the MSSP cover letter
  (branch `mssp-extended`, `paper/mssp_extended/cover_letter/cover_letter.txt`, line 26), RESS "declined [it] on scope grounds without
  review in September 2026".

## Canonical manuscript

- Text source of truth: `paper/mssp_extended/manuscript_mssp_draft.md` (Markdown; captions and declarations included).
- LaTeX (generated): `paper/mssp_extended/latex/main.tex` (elsarticle preprint; 386 lines). It is identical on `main` and `mssp-extended`.
- PDF: `paper/mssp_extended/latex/main.pdf`, 21 pages, SHA-256 `d51ec1ce…3b701` (matches README and release notes).
- Title: "False-Alarm Calibration Transport Across Engines in Full-Flight Aero-Engine Anomaly Detection: A Multi-Subset
  Audit of Context Conditioning and Calibration-Fleet Coverage".

## Canonical supplement

`paper/mssp_extended/supplement/supplement.pdf` (43 pages, SHA-256 `7ff25b50…4b5d13`). Source is `supplement.tex`, built by
`paper/mssp_extended/build_supplement.py`.
- Part A: Tables S1–S24, formatted from committed extension outputs.
- Part B: the unchanged pre-extension supplement `paper/mssp/supplement/supplement.pdf`.

## Canonical result directory

- `results/extension/` for the multi-subset extension (DS01, DS04–DS07, DS08a, DS08c; references DS02, DS03).
  - Per-subset `lock/` and `audit/`, plus `summary/`, `focused_validation/`, `metadata/` and `benchmark/`.
- Frozen earlier stages, carried verbatim:
  - `results/final_validation/`: DS02 discovery;
  - `results/confirmation_ds03/`: DS03 one-shot confirmation;
  - `results/mssp_mitigation/` and `results/mssp_adversarial/`: post-confirmation analyses.
- Manuscript evidence: `paper/mssp_extended/evidence/` (22 files + `SHA256SUMS`).
- Ledger: `docs/extension/EXTENSION_EVIDENCE_LEDGER.csv` (1,674 rows; byte-identical copy in `evidence/`).
- `results/phase3_*`, `results/second_stage/` and root `results/*.csv` are DS02 exploratory provenance only
  (`docs/AUTHORITATIVE_RESULTS.md`). They are **not** the source of any extension-manuscript number.

## Frozen protocol/config

- Extension: `docs/extension/GENERALIZATION_PROTOCOL.md` v1.0, frozen at `d298623`, with `AMENDMENTS.md` 1–3.
  - Also `SUBSET_SELECTION_LOCK.md` (cohort locked at `7152b92`), `CVAE_SPECIFICATION.md` and `FREEZE_RECORD.md`.
  - Code constants are in `src/ext_common.py` (targets, seeds, bootstrap replicates, composition seeds).
- Focused validation (post hoc): `docs/extension/FOCUSED_VALIDATION_PLAN.md`, frozen at `d85aa10` before any re-read.
- Earlier stages:
  - `results/final_validation/frozen_protocol.md`;
  - `configs/ds02_discovery.yaml` and `configs/ds03_confirmation.yaml` (audited snapshots, not parsed by the code);
  - `docs/mssp/post_confirmation_mitigation_protocol.md`, `docs/mssp/adversarial_validation_plan.md` and
    `configs/mssp_mitigation.yaml`.
- Integrity manifest: `docs/mssp/frozen_baseline.sha256` (186 files).

## Important Git commit

- `3a4de78` (`main`, `v1.1.0`): the public snapshot as tagged.
- `d1d3e58`: the sanitized v1.1.0 snapshot before two CI-only test fixes.
- `54b25ee` (branch `mssp-extended`, local only): the full internal history, with submission administration. Protocol,
  ledger and lock commit IDs such as `131a884`, `95a1379`, `d298623`, `d85aa10` and `e6b6a85` resolve **locally**, on this branch.
- `d5699a1` (branch `mssp-revision`; tag `mssp-pre-extension-2026-09-28`): the pre-extension MSSP package.

## Important Git tag

- `v1.1.0` → `3a4de78`: this release.
- `v1.0.0` = `ress-submission-2026-09-25` → `1f59e9e`: DS02/DS03 study.
- `mssp-pre-extension-2026-09-28` → `d5699a1`.

## Release

v1.1.0, "Calibration Transport Manuscript and Reproducibility Release" (`docs/release/v1.1.0/RELEASE_NOTES.md`).

## DOI

None yet. `.zenodo.json` is prepared; the README says the DOI "will be added after the release is archived".

## Journal/venue

Mechanical Systems and Signal Processing (MSSP, Elsevier): the elsarticle class, "Elsevier limit 85 characters" highlights, and the cover letter on `mssp-extended`.

## Submission date

UNKNOWN. The submission bundle `paper/mssp_extended/submission_bundle/latex_source.zip` (git-ignored on `main`) and
`cover_letter/cover_letter.log` are dated 2026-09-29 12:48–12:49; no upload record exists.

## Primary scientific claims

Details are in `reviewer/CLAIMS_INDEX.md`; all apply to simulated N-CMAPSS data only.
1. Pooled calibration left material phase-conditional miscalibration in 3 of 5 new fleet families (H1 SUPPORTED, exactly at
   threshold; one family is uniform under-alarming).
2. Retrospective phase-conditioned (C) and continuous-context (Q) thresholds improved on average ~half of held-out engines
   per cell and sometimes made calibration much worse (H2 PARTIAL, H3 SURVIVES).
3. A fleet-trained condition-aware CVAE did not improve transport (H5 SURVIVES).
4. At fixed calibration volume, class coverage improved phase-conditioned calibration, but pooled only weakly (H4 SUPPORTED).
5. Post hoc focused validation: fleet-calibrated per-engine errors, mostly < 1 pp, exceeded the engine's cross-fitted
   self-calibration reference in 27/30 engines under C, and 5-flight local recalibration did not reduce them.

## Known limitations

The full list is in `reviewer/ASSUMPTIONS_AND_LIMITATIONS.md`.
- There is one simulator with a shared flight library, and five top-level families.
- Each audit engine has 14–36 healthy flights.
- Class coverage is confounded with engine identity and shared missions.
- There is one CVAE specification, phases are retrospective, and the freeze is internal rather than external.
- H1 and H4 sit exactly on their thresholds.

## Things that MAY be changed safely

- Everything in `reviewer/` and this file.
- New dated notes under `docs/`, in new files only.
- Local build products that are git-ignored (LaTeX aux files).
- Response-to-reviewer drafts in new files outside `paper/mssp_extended/` and `results/`.

## Things that MUST NOT be changed silently

- Anything listed in `docs/mssp/frozen_baseline.sha256` or `docs/release/v1.1.0/PUBLIC_RELEASE_MANIFEST.sha256`.
- `results/**`, `paper/mssp_extended/{figures,tables,evidence}/**` and `docs/extension/EXTENSION_EVIDENCE_LEDGER.csv`.
  - The ledger is append-only, via `verify_numbers.py --register`.
- The protocol, amendments, plan and lock files.
- `manuscript_mssp_draft.md` numbers: every number is checked by `paper/mssp_extended/verify_numbers.py`.
  - If text changes, rerun it; never edit a number without re-deriving it.
- The engine-role allocation (`src/ext_common.py:allocate`), targets, seeds, bootstrap seeds and decision rules
  (`src/ext_summary.py`).
- Tags `v1.0.0`, `v1.1.0`, `ress-submission-2026-09-25` and `mssp-pre-extension-2026-09-28`.
- The git-ignored but essential local files (not in git; losing them makes re-scoring impossible without retraining):
  - `results/extension/*/models/` (84 binaries; all match lock hashes, checked 2026-09-29);
  - `results/final_validation/checkpoints/` and `results/confirmation_ds03/checkpoints/`;
  - `N-CMAPSS/*.h5`.

## Cheap verification commands

These use no N-CMAPSS data and no GPU. They were run on 2026-09-29 with `.venv/bin/python -B`; all passed.

```bash
python -B paper/mssp_extended/verify_numbers.py
```
Result: 78 claims, 5 tables, 6 figures, 47 cited keys; "all checks passed". Read-only unless `--register` is given.

```bash
python -B paper/mssp/verify_draft_numbers.py
```
Result: "All 81 cited values re-derived and found verbatim".

```bash
sha256sum -c docs/release/v1.1.0/PUBLIC_RELEASE_MANIFEST.sha256
```
Result: 1,008 of 1,008 OK.

```bash
cd paper/mssp_extended/evidence && sha256sum -c SHA256SUMS
```
Result: 22 of 22 OK.

`sha256sum -c docs/mssp/frozen_baseline.sha256` gives 167/186 OK. The 19 absent files are the RESS
submission-administration files under `paper/submission/`, which are not distributed (documented). The 12 LSTM checkpoints
are present locally.

Not run in this audit, to avoid GPU use and an unknown runtime:
```bash
CUDA_VISIBLE_DEVICES= python scripts/run_public_tests.py -v
```
The empty `CUDA_VISIBLE_DEVICES` forces a CPU-only run so that the CUDA tests skip, as in CI.

## Expensive reproduction commands

These need the NASA HDF5 files and a CUDA GPU; CPU fallback is not validated (`docs/ENVIRONMENT.md`). Do not run them
without a frozen plan.
- `scripts/reproduce_ds02.py` and `scripts/reproduce_ds03.py` (dry-run by default; `--execute` writes to a new path).
- The one-shot, fail-closed runners `scripts/run_mssp_mitigation.py`, `run_mssp_adversarial.py`, `run_extension.py` and `run_focused_validation.py`.
  - They refuse to overwrite outputs or reopen test data without their locks and plans.
  - They verify the 186-file manifest first.
- Rebuild of figures, tables and PDF, which needs TeX and rewrites tracked files: `paper/mssp_extended/build_figures_tables.py --rebuild`,
  then `build_bibliography.py --offline`, `build_latex.py` and `build_supplement.py`.

## Reviewer-response starting point

`reviewer/REBUTTAL_NAVIGATION.md`

## Known unresolved traceability issues

1. The journal submission status and date are not recorded (see above).
2. The Zenodo DOI for v1.1.0 is not yet minted. The manuscript's Code availability says "will be released as v1.1.0 and archived
   on Zenodo … before publication". The tag exists; the archive does not.
3. On a fresh public clone, protocol, lock and ledger commit IDs are unresolvable. They resolve only in this local repository
   (branches `mssp-extended` and `mssp-revision`). Losing this local repository loses that audit trail.
4. The abstract and highlight 5 say "exceeded … self-calibration in 27 of 30 engines" without naming the arm. 27 is the C-arm
   count; P gives 29 and Q gives 28 (§4.8). This is correct but could be queried.
5. `verify_numbers.py` reports "independent support: 76 of 78 displayed numbers also occur in pre-existing ledger rows". Two
   displayed numbers are supported only by forward re-derivation, not by an earlier ledger row. The script does not print which
   two, and this audit did not identify them.
   - **Identified 2026-09-29** with a read-only wrapper around `verify_numbers.py` (no `--register`, no bytecode). Both do
     have pre-existing ledger rows; the heuristic misses them only because of formatting.
     - **"−0.53"** is the lower 95% bound of the Isolation Forest ME-A2 difference ("−0.20 pp, −0.53 to 0.22 pp").
       - Source: `results/extension/summary/uext2_cross_dataset.csv`, `isolation_forest`/`diff_ME_A2`, `ci_lower_95` =
         −0.005277.
       - Ledger: **EX000938** records it as "95% interval −0.528 to 0.216 pp", with three decimals in the claim text.
     - **"−0.09"** is the class-2 coverage effect under arm P.
       - Source: `paper/mssp_extended/evidence/post_hoc_checks.json`, `coverage_by_audit_class/pooled/2` = −0.000925.
       - Ledger: **EX001335**'s composite value string "class 2: -0.00093", which `pd.to_numeric` cannot parse.
6. CI fix `3a4de78` relaxed the `kappa_low`/`kappa_high` comparison in `tests/test_mssp_adversarial.py` from exact equality to
   `atol=1e-15`, after a float mismatch between platforms. No reported number depends on this, but it shows that bitwise
   reproducibility of κ grids is platform-dependent.
7. A stale worktree registration, `/home/mei/Research/ncmapss-phase-entanglement-public-v1.1.0` (branch `public-v1.1.0`), is
   marked "prunable": its directory no longer exists. It was left untouched.

# WHAT I COULD NOT TRACE

- **Submission:** the MSSP submission status, date and manuscript ID.
- **Two displayed numbers: RESOLVED 2026-09-29.** They are "−0.53" (EX000938) and "−0.09" (EX001335); see item 5 above.
  Both were re-read from their source files and match.
- **Raw-data integrity:** the NASA HDF5 files were not re-hashed against `N-CMAPSS/official_verification.json` in this audit
  (59 GB). Integrity rests on the recorded `input_sha256` in each lock and on the frozen-stage source records.
- **LSTM/CVAE training determinism:** GPU training is not claimed bitwise reproducible. Reproducibility rests on saved
  binaries (hash-verified locally), not on retraining. Retraining was not attempted.
- **Frozen DS02/DS03 numbers:** these (C001–C003) were traced only to `paper/manuscript_core_results.csv`, the frozen
  `canonical_results.csv` files and the frozen pre-extension text. Their upstream generation (v1.0.0 pipeline,
  `src/final_validation.py` and `src/confirm_frozen_ds03.py`) was not re-audited here; it was checked at v1.0.0 by
  `paper/mssp/verify_draft_numbers.py`.
- **Figure 1:** a schematic whose provenance names no data inputs (counts "from `docs/extension/SUBSET_SELECTION_LOCK.md`").
  It has no numerical source beyond that file.
- **The "about none" phrase:** "about none in DS04 and DS08c" (§4.8, class-preserving bootstrap) is traced. Its operational
  meaning, a share < 5%, is set only in `paper/mssp_extended/verify_numbers.py` (the assertion `none < 0.05`, line 499); the
  manuscript does not state the cut-off.
