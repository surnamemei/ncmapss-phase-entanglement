# MSSP manuscript package (final draft, calibration transport)

This package holds the *Mechanical Systems and Signal Processing* manuscript "Phase-Dependent False-Alarm Calibration and Its Transport Across Engines in Full-Flight Aero-Engine Anomaly Detection". It is separate from the RESS submission.

**Status:** complete, QA-checked final draft awaiting the author's approval. It has not been submitted.
- The interpretation is fixed in `docs/mssp/FINAL_STORY_LOCK.md`.
- The readiness decision is in `docs/mssp/FINAL_SUBMISSION_READINESS.md`.
- The upload set is listed in `SUBMISSION_FILES.md`.

## Contents

| Path | Purpose |
| --- | --- |
| `manuscript_mssp_draft.md` | Single source of the manuscript text, including the title, the 244-word abstract, highlights, keywords, Sections 1–6, declarations and captions |
| `verify_draft_numbers.py` | Re-derives every cited number from committed outputs and checks it verbatim. It also checks that every decimal or percentage in the post-confirmation text has a source, that the frozen sections match the audited RESS text, the terminology lock, the limits, and citation integrity |
| `references_spec.json`, `build_bibliography.py`, `latex/references_mssp.bib` | Cited references with DOI or manual metadata. The bibliography is built from cached Crossref records (`literature_evidence/crossref/`), and `literature_evidence/bibliography_check.csv` records the check of each DOI |
| `reference_audit.csv`, `NOVELTY_POSITIONING.md`, `literature_evidence/` | Final prior-art audit: feature flags, overlap and difference per reference, ESSENTIAL/USEFUL/DROP classification, novelty answers and verbatim-quote checks |
| `build_mssp_figures_tables.py`, `figures/`, `tables/`, `evidence/` | Figures 1–6, Tables 1–5 and supplementary CSVs built from committed outputs, each with a provenance sidecar |
| `build_latex.py`, `latex/` | Markdown to elsarticle LaTeX (A4, 11 pt, single spacing, line numbers), the compiled `main.pdf`, highlights (`.txt` and `.docx`) and exported declarations (`declarations/`) |
| `build_supplement.py`, `supplement/` | Supplementary material PDF: 23 tables and 4 figures, with provenance |
| `build_cover_letter.py`, `cover_letter/` | One-page MSSP cover letter (text source and PDF) |
| `package_submission.py`, `submission_bundle/` | Flat upload set, compile-tested, with a SHA-256 manifest |
| `SUBMISSION_REQUIREMENTS.md`, `requirements_evidence/` | MSSP and Elsevier requirements with verbatim quotes, mapped to the package |
| `adversarial_claim_audit.md`, `reference_audit_mssp.md`, `outline/` | Earlier audit and outline documents, kept for history (superseded where stated) |

## Evidence rules

- **Frozen DS02/DS03 numbers** are cited through unchanged evidence IDs (`paper/manuscript_core_results.csv`), and Sections 4.1–4.7 match the audited RESS text.
- **Post-confirmation numbers** come from `results/mssp_mitigation/` (frozen protocol v1.0) and `results/mssp_adversarial/` (the frozen adversarial-validation plan).
- **No new analysis** was run for the final manuscript. Figures, tables and the supplement are formatted views of committed outputs.

## Boundaries

- **Not modified:** `paper/ress/`, `paper/submission/`, the 186 frozen files, the Stage B–F and adversarial outputs, and the RESS tags. Tests enforce this.
- **Terminology** follows the lock in `docs/mssp/FINAL_STORY_LOCK.md`:
  - abnormal-state ($hs = 0$);
  - past-only LSTM;
  - retrospective phase-conditioned (C) and past-only regime-conditioned (C′) calibration;
  - between-phase disparity versus nominal calibration error;
  - "healthy flights with any alarm" kept separate from the κ-based false-flag rate.
