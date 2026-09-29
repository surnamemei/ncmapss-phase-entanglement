# Extended MSSP manuscript package

This package is the manuscript rescoped after the frozen multi-subset extension (`docs/extension/`). The
pre-extension package `paper/mssp/` is left unchanged; its supplement is included unchanged as Part B of this
package's supplement.

## Sources of truth

- Text: `manuscript_mssp_draft.md`, including the captions and declarations.
- Numbers: `results/extension/` (protocol `docs/extension/GENERALIZATION_PROTOCOL.md` v1.0 with Amendments 1–3),
  certified by `docs/extension/EXTENSION_EVIDENCE_LEDGER.csv`. The frozen DS02/DS03 values come from
  `paper/manuscript_core_results.csv`.
- References: `references_spec.json`, with verification records in `reference_audit.csv` and `literature_evidence/`.

## Build order

No step reads N-CMAPSS data.

```
python paper/mssp_extended/build_figures_tables.py --rebuild   # figures/, tables/, evidence/ (with provenance)
python paper/mssp_extended/build_bibliography.py --offline     # latex/references_mssp.bib from cached Crossref records
python paper/mssp_extended/build_latex.py                      # latex/main.tex, main.pdf, highlights (and git-ignored exports)
python paper/mssp_extended/verify_numbers.py                   # re-derives every cited number; wording and citation checks
python paper/mssp_extended/build_supplement.py                 # supplement/supplement.pdf (Part A extension, Part B frozen)
python scripts/run_public_tests.py                             # data-free test suite of the public release
```

## Status

The manuscript provided in this repository is an author preprint and has not undergone peer review for the current
journal submission. If a version of record is later published, this repository will link to the publisher DOI.

This public release (v1.1.0) does not include the submission administration of this package: the cover letter, the
Editorial Manager declarations, the upload bundle and its checklists, or their builders.
