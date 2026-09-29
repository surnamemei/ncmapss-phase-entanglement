# v1.1.0 — Calibration Transport Manuscript and Reproducibility Release

> **Preprint notice.** The manuscript provided in this repository is an author preprint and has not undergone peer review for the current journal submission. If a version of record is later published, this repository will link to the publisher DOI.

This is a preprint and reproducibility release, not a peer-reviewed version of record.

## Summary

- **Scope.** This release is a multi-subset N-CMAPSS calibration-transport audit. It accompanies the author preprint "False-Alarm Calibration Transport Across Engines in Full-Flight Aero-Engine Anomaly Detection: A Multi-Subset Audit of Context Conditioning and Calibration-Fleet Coverage" by Jinghang Mei.
- **Earlier stages preserved.** The DS02 discovery and the frozen DS03 confirmation, a one-shot evaluation released in v1.0.0, are preserved unchanged.
- **New subsets.** Seven additional, previously unopened N-CMAPSS subsets were evaluated under a frozen extension protocol:
  - the subsets are DS01, DS04, DS05, DS06, DS07, DS08a and DS08c;
  - they form five fleet families with 30 held-out audit engines;
  - calibration-only locks were committed before any official-test read;
  - each audit was one-shot.
- **Detectors.** Residual PCA, Isolation Forest, a past-only LSTM and a condition-aware CVAE.
- **Analyses.** Calibration-fleet coverage, cross-engine transport, matched false-flag evaluation and a final engine-specific validation. The validation is post hoc: it was frozen as a separate plan before any re-read and used healthy official-test rows only.
- **Data.** Raw NASA data are not redistributed.

The results, the pre-specified decisions H1–H7 and their limitations are reported in the preprint and in `docs/extension/FINAL_EXTENSION_REPORT.md`. These notes add nothing to them.

## Preprint and supplement

| File | Pages | SHA-256 |
| --- | --- | --- |
| `paper/mssp_extended/latex/main.pdf` (preprint) | 21 | `d51ec1cef13b4a8e4515252013eafc00c4314c05716ead19d5842fc90db3b701` |
| `paper/mssp_extended/supplement/supplement.pdf` (supplementary material) | 43 | `7ff25b50fb92b1ba9b6660aa96a331633244988c6048e67df5ecbd01a84d5b13` |

**Part A** of the supplement (Tables S1–S24) covers:
- the extension;
- the post hoc checks;
- the final focused validation.

**Part B** reproduces, unchanged, the supplement of the pre-extension manuscript "Phase-Dependent False-Alarm Calibration and Its Transport Across Engines in Full-Flight Aero-Engine Anomaly Detection" (`paper/mssp/supplement/supplement.pdf`, SHA-256 `f1d38a515ca6e6ce22f686500aac462faa7a56bb6eb9e6775d6b459a04996b2a`). That pre-extension package is superseded. It is kept as the frozen record of the post-confirmation analyses, and as the source of the frozen DS02/DS03 values that the final package checks.

## Contents

**Code and tests.**
- Analysis code, guarded runners and reproduction wrappers: `src/`, `scripts/`, `configs/`.
- The data-free tests in `tests/`.

**Governance and provenance records.**
- Frozen protocols and plans, amendments, freeze records and locks.
- The outcome-access log.
- The internal review, and the plan and report of the focused validation.
- The final extension report: `docs/extension/`, `docs/mssp/`, and the locks in `results/`.

**Outputs and evidence.**
- Derived outputs and run records: `results/`.
- The evidence ledgers: `docs/extension/EXTENSION_EVIDENCE_LEDGER.csv` and `paper/evidence_ledger.csv`.
- Hash manifests: the frozen-baseline manifest `docs/mssp/frozen_baseline.sha256`, the evidence `SHA256SUMS`, and the figure, table and supplement provenance records.

**The preprint package.** `paper/mssp_extended/` holds:
- the Markdown and LaTeX source;
- the PDF;
- the figures, tables and supplement;
- machine-readable evidence;
- the reference verification records.

**Frozen manuscript records of the earlier stages.** These are `paper/mssp/` (pre-extension, superseded) and `paper/ress/`, `paper/output/`, `paper/manuscript_submission*.md`, `paper/figures/`, `paper/tables/` and `paper/submission/` (DS02/DS03 study, as in v1.0.0, without its submission administration).

**Release manifest.** `docs/release/v1.1.0/PUBLIC_RELEASE_MANIFEST.sha256` lists the SHA-256 of every distributed file.

## Not included

- **Raw data.** The NASA N-CMAPSS HDF5 and ZIP files are available from the NASA PCoE Data Set Repository.
- **Models.** Model binaries and checkpoints. The hashes of the fitted extension models are recorded in the locks.
- **Submission administration.** Cover letters, Editorial Manager declarations and upload bundles, submission checklists and requirement mappings.
- **Internal material.** Internal memos and notes.
- **Superseded drafts and exploratory reports.** The drafting intermediates and the historical exploratory reports and figures of the DS02 study are not here; they remain in v1.0.0.
- **Build products.** Build logs, caches and temporary files.

## Provenance history

The release is a single commit, published without the author's internal development history. It was cut from the author's private provenance branch at commit `54b25ee0934a2c0570428f1e84894603ea1a0f70`.

- **Changes from that commit.** Apart from the files left out, this snapshot changes six files:
  - `README.md`;
  - `.zenodo.json` (notes only);
  - `.gitignore`;
  - `.github/workflows/tests.yml`;
  - `paper/mssp_extended/README.md`;
  - these notes.

  It also adds three files: the release manifest, `scripts/run_public_tests.py` and `tests/test_public_release.py`.
- **Commit identifiers.** Those cited in the frozen records refer to the private history and cannot be resolved here.
- **Integrity.** Every distributed frozen file is byte-identical to its frozen record:
  - 155 of the 186 entries of the frozen-baseline manifest verify;
  - the 31 absent entries are exactly the 12 LSTM checkpoints and the 19 RESS submission-administration files;
  - the frozen plans, protocols and freeze-record hashes verify;
  - all nine extension locks record the distributed protocol and CVAE specification.

## How to verify without NASA data

Use Python 3.12 with `requirements-lock.txt`, `poppler-utils` and `git`.

1. Check every distributed file.

   ```bash
   sha256sum -c docs/release/v1.1.0/PUBLIC_RELEASE_MANIFEST.sha256
   ```

2. Run the data-free test suite. The synthetic GPU tests need CUDA and are skipped without it.

   ```bash
   python scripts/run_public_tests.py
   ```

3. Re-derive every number cited in the preprint, and check each against the evidence ledger.

   ```bash
   python paper/mssp_extended/verify_numbers.py
   ```

4. Re-derive the numbers of the pre-extension manuscript.

   ```bash
   python paper/mssp/verify_draft_numbers.py
   ```

**Inherited tests the runner handles differently.** `scripts/run_public_tests.py` does not run 26 inherited tests as they stand, and prints each one with its reason.
- **23 check material this snapshot leaves out:**
  - the cover letters, declarations, upload bundles and Highlights `.docx`;
  - LaTeX build logs;
  - the absent frozen-manifest entries;
  - the private tags.

  `tests/test_public_release.py` repeats their applicable checks.
- **3 are synthetic end-to-end tests of the one-shot runners.** The first gate of those runners checks the complete manifest. `tests/test_public_release.py` runs these three tests unchanged behind a public gate. That gate verifies every distributed entry and requires the absent entries to be exactly the documented ones.

**Re-running the analyses.** This needs the NASA data and a CUDA GPU; see `README.md`. The one-shot runners of the later stages fail closed: they verify the complete frozen-baseline manifest, which lists the non-distributed checkpoints and files.

## License scope

The MIT License applies to project-authored software and code. Manuscript text and figures are © 2026 Jinghang Mei and are not offered under the MIT License unless explicitly stated otherwise.

NASA N-CMAPSS data remain subject to their original terms and are not redistributed.

## Relationship to earlier releases

**v1.0.0** holds the DS02 discovery and the frozen one-shot DS03 confirmation, and is unchanged.
- The 155 frozen v1.0.0 files that this release distributes are byte-identical to v1.0.0.
- Its submission administration, drafting intermediates and historical exploratory reports are not repeated here.

## Citation

- Cite the repository through `CITATION.cff`.
- Cite the article if a version of record is published.
- The Zenodo DOI for this release will be added to `CITATION.cff` and `README.md` after the release is archived.
