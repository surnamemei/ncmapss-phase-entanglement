# False-alarm calibration transport in full-flight aero-engine anomaly detection (N-CMAPSS)

This repository holds the code, frozen protocols, locks, run records, derived outputs and evidence ledgers for an audit of nominal healthy false-alarm calibration on the NASA N-CMAPSS benchmark. It also holds the author preprint of the accompanying manuscript.

**Release.** v1.1.0, "Calibration Transport Manuscript and Reproducibility Release" (public snapshot). The release notes are in [`docs/release/v1.1.0/RELEASE_NOTES.md`](docs/release/v1.1.0/RELEASE_NOTES.md).

> **Preprint notice.** The manuscript provided in this repository is an author preprint and has not undergone peer review for the current journal submission. If a version of record is later published, this repository will link to the publisher DOI.

## Manuscript

**Title.** "False-Alarm Calibration Transport Across Engines in Full-Flight Aero-Engine Anomaly Detection: A Multi-Subset Audit of Context Conditioning and Calibration-Fleet Coverage".

**Author.** Jinghang Mei, School of Electrical and Computer Engineering, The University of Sydney. ORCID: https://orcid.org/0009-0007-2901-3285.

| Item | Path |
| --- | --- |
| Preprint (PDF, 21 pages) | [`paper/mssp_extended/latex/main.pdf`](paper/mssp_extended/latex/main.pdf) |
| Supplementary material (PDF, 43 pages) | [`paper/mssp_extended/supplement/supplement.pdf`](paper/mssp_extended/supplement/supplement.pdf) |
| Manuscript source | `paper/mssp_extended/manuscript_mssp_draft.md` (the single source of the text), `latex/main.tex`, `latex/references_mssp.bib`, `latex/highlights.txt` |
| Figures and tables | `paper/mssp_extended/figures/` (Figs. 1–6, PDF and PNG) and `paper/mssp_extended/tables/` (Tables 1–5, CSV and LaTeX), each with a provenance record |
| Machine-readable evidence | `paper/mssp_extended/evidence/`, with `SHA256SUMS` |
| Supplement source | `paper/mssp_extended/supplement/supplement.tex`. Part A (Tables S1–S24) is built from the committed outputs. Part B is the unchanged pre-extension supplement (`paper/mssp/supplement/supplement.pdf`) |

SHA-256 of the released PDFs:

```text
d51ec1cef13b4a8e4515252013eafc00c4314c05716ead19d5842fc90db3b701  paper/mssp_extended/latex/main.pdf
7ff25b50fb92b1ba9b6660aa96a331633244988c6048e67df5ecbd01a84d5b13  paper/mssp_extended/supplement/supplement.pdf
```

Every distributed file is listed with its SHA-256 in [`docs/release/v1.1.0/PUBLIC_RELEASE_MANIFEST.sha256`](docs/release/v1.1.0/PUBLIC_RELEASE_MANIFEST.sha256).

## Study design

The results, the pre-specified decisions H1–H7 and their limitations are reported in the preprint and in `docs/extension/FINAL_EXTENSION_REPORT.md`. This README describes only the design and where each record is.

1. **DS02 discovery and the frozen one-shot DS03 confirmation.** These were released in v1.0.0 and are preserved unchanged. The detectors were residual PCA, Isolation Forest and a past-only LSTM.
2. **Post-confirmation analyses** of DS02 and DS03. They ran under a separately frozen protocol and a frozen adversarial-validation plan.
3. **Frozen multi-subset extension.**
   - **Subsets.** Seven previously unopened subsets: DS01, DS04, DS05, DS06, DS07, DS08a and DS08c. They form five fleet families with 30 held-out audit engines. DS08d could not be opened and was excluded.
   - **Locks.** Calibration-only locks were committed before any official-test read, and each audit was one-shot.
   - **Detectors.** A condition-aware CVAE was added to the three detectors above.
   - **Calibration.** Pooled, retrospective phase-conditioned and continuous-context thresholds.
   - **Analyses.** Calibration-fleet coverage (a fixed-volume composition intervention), cross-engine transport, matched false-flag evaluation and alarm persistence.
4. **Internal review, then a final engine-specific validation.** The validation is post hoc. It was frozen as a separate plan before any re-read and used healthy official-test rows only. It has three components:
   - cross-fitted self-calibration references;
   - a calibration-class-preserving bootstrap;
   - five-flight local recalibration.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/`, `scripts/`, `configs/` | Analysis code, guarded runners, reproduction wrappers and frozen experimental constants |
| `tests/` | Data-free tests: static, provenance, manuscript QA and synthetic |
| `docs/extension/` | Governance and protocol documents: the extension charter, subset-selection lock, generalization protocol and amendments, CVAE specification and freeze record |
| `docs/extension/` (continued) | Records and reports: the outcome-access log, internal review, focused-validation plan and report, final extension report, subset metadata audits, and the extension evidence ledger (`EXTENSION_EVIDENCE_LEDGER.csv`) |
| `docs/mssp/` | The post-confirmation protocol, adversarial-validation plan, amendments, freeze record, interpretation lock, the adversarial-review record (with its recorded deviation) and the frozen-baseline manifest (`frozen_baseline.sha256`) |
| `docs/AUTHORITATIVE_RESULTS.md`, `docs/experiment_timeline.md`, `docs/ENVIRONMENT.md` | The numeric-source allowlist and timeline of the DS02/DS03 study, and the validated environment |
| `results/final_validation/`, `results/confirmation_ds03/` | The frozen DS02 discovery and one-shot DS03 confirmation: outputs, protocol, locks and markers |
| `results/phase3_*`, `results/second_stage/`, `results/*.csv`, `results/*.json` | DS02 exploratory outputs, kept as provenance only (see `docs/AUTHORITATIVE_RESULTS.md`) |
| `results/mssp_mitigation/`, `results/mssp_adversarial/` | Post-confirmation and adversarial-validation outputs and run records |
| `results/extension/` | Extension locks, one-shot audit outputs, summaries and decisions, and the focused validation |
| `paper/mssp_extended/` | The preprint package (see above) |
| `paper/mssp/` | The frozen pre-extension manuscript package, "Phase-Dependent False-Alarm Calibration and Its Transport Across Engines in Full-Flight Aero-Engine Anomaly Detection". It is superseded and is not the preprint. It is kept for two reasons: its supplement is Part B of the final supplement, and its text supplies the frozen DS02/DS03 values that the final package checks |
| `paper/evidence_ledger.csv`, `paper/manuscript_core_results.csv` | The evidence ledger and the core-results selection of the DS02/DS03 study |
| `paper/ress/`, `paper/output/`, `paper/manuscript_submission*.md`, `paper/figures/`, `paper/tables/`, `paper/submission/` | The frozen manuscript record of the DS02/DS03 study, as in v1.0.0, including its supplementary material but not its submission administration |

## Verifying the release without NASA data

**Requirements.**
- Python 3.12 with the packages pinned in `requirements-lock.txt`. The synthetic GPU tests need a CUDA build of PyTorch; without CUDA they are skipped.
- `poppler-utils` (`pdftotext`, `pdfinfo`, `pdffonts`), `sha256sum` and `git`. Run the test runner from a git checkout, because some tests read the committed tree.

No step below reads N-CMAPSS data.

1. Check every distributed file against the release manifest.

   ```bash
   sha256sum -c docs/release/v1.1.0/PUBLIC_RELEASE_MANIFEST.sha256
   ```

2. Run the data-free test suite.
   - The runner lists the inherited tests that check material this snapshot leaves out, with the reason for each.
   - `tests/test_public_release.py` re-checks the parts of those tests that still apply.
   - It also runs the synthetic end-to-end tests of the one-shot runners unchanged, behind a public frozen-baseline gate.

   ```bash
   python scripts/run_public_tests.py
   ```

3. Re-derive every number cited in the preprint. Each is checked against the evidence ledger and its source hash.

   ```bash
   python paper/mssp_extended/verify_numbers.py
   ```

4. Re-derive the numbers of the pre-extension manuscript, which is the source of the frozen values.

   ```bash
   python paper/mssp/verify_draft_numbers.py
   ```

**Optional rebuild.** This needs a TeX distribution with `latexmk`, `pdflatex` and `bibtex`. It rewrites the tracked figures, tables, bibliography, LaTeX and PDFs and their provenance records. PDFs embed their build date.

```bash
python paper/mssp_extended/build_figures_tables.py --rebuild
```
```bash
python paper/mssp_extended/build_bibliography.py --offline
```
```bash
python paper/mssp_extended/build_latex.py
```
```bash
python paper/mssp_extended/build_supplement.py
```

## Re-running the analyses

Re-running needs the raw NASA N-CMAPSS HDF5 files, which are not redistributed here, and a CUDA GPU. CPU fallback is not part of the validated protocol; see `docs/ENVIRONMENT.md`.

- **DS02 and DS03.** `scripts/reproduce_ds02.py` and `scripts/reproduce_ds03.py` default to a dry run. With `--execute` they write only to a new output path.
- **Later stages.** `scripts/run_mssp_mitigation.py`, `run_mssp_adversarial.py`, `run_extension.py` and `run_focused_validation.py` are one-shot runners that fail closed. They refuse to overwrite outputs and refuse to reopen official-test data without their committed locks and plans. Before writing, they verify the complete 186-file frozen-baseline manifest.
- **Why those runners stop here.** The manifest lists 12 LSTM checkpoints, which the post-confirmation stages load as inputs, and 19 submission-administration files of the earlier RESS submission. This snapshot distributes neither, so as distributed the runners stop at that check. Their committed outputs are included, and steps 1–4 above verify every reported number against those outputs.
- **Model binaries.** The fitted extension models are not distributed. Their SHA-256 hashes are recorded in the locks.

## Provenance history

This snapshot is published as a single commit, without the author's internal development history. The frozen protocols, locks and ledgers cite commit identifiers from that history, and those identifiers cannot be resolved here.

Every distributed frozen file is byte-identical to its frozen record. The tests check them against the SHA-256 values recorded in:
- the frozen-baseline manifest;
- the evidence checksums;
- the provenance records;
- the evidence ledgers.

## Not included

- **Raw data.** The NASA N-CMAPSS HDF5 and ZIP files are available from the [NASA PCoE Data Set Repository](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/) ("Turbofan Engine Degradation Simulation-2").
- **Models.** Model binaries and checkpoints.
- **Submission administration.** Cover letters, Editorial Manager declarations and upload bundles, submission checklists and requirement mappings.
- **Internal material.** Internal memos and notes.
- **Superseded drafts and exploratory reports.** The drafting intermediates and the historical exploratory reports and figures of the DS02 study are not here; they remain in the published v1.0.0 release. Some provenance documents here refer to them by path.
- **Build products.** Build logs, caches and temporary files.

## License

The MIT License applies to project-authored software and code. Manuscript text and figures are © 2026 Jinghang Mei and are not offered under the MIT License unless explicitly stated otherwise.

- The MIT License text is in [`LICENSE`](LICENSE).
- NASA N-CMAPSS data remain subject to their original terms and are not redistributed here.
- The cached Crossref records and the short quotations of cited works in `literature_evidence/` are third-party material. They are included only to verify the references.

## Citation

- Use the metadata in [`CITATION.cff`](CITATION.cff) for this repository.
- Cite the article if a version of record is published.
- A Zenodo DOI for this release will be added after the release is archived.

## Earlier releases

**v1.0.0** is the DS02 discovery and the frozen one-shot DS03 confirmation.
- Every frozen v1.0.0 file that this snapshot distributes is byte-identical to v1.0.0; there are 155 such files.
- The v1.0.0 submission administration, drafting intermediates and historical exploratory reports are not repeated here.
