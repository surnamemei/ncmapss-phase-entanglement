# Final RESS submission-package audit

## Package state

- Final manuscript: `paper/output/NCMAPSS_Flight_Phase_RESS_Final.pdf` — **20 pages**. Final compilation output was reviewed during the PDF audit; transient build files are not included in the submission package.
- Editable source: `paper/ress/main.tex`, `paper/ress/references.bib`, four frozen main figures in `paper/ress/figures/`, and three source tables in `paper/ress/tables/`.
- Submission text files: `highlights.txt`, `cover_letter_final.md`, `data_availability_final.md`, `code_availability_final.md`, `credit_author_statement.md`, `generative_ai_declaration.md`, `competing_interest_final.txt`, and `funding_statement_final.txt`.
- The AI-use statement, funding statement, competing-interest statement, all listed CRediT roles, corresponding-author email, and originality/exclusive-consideration declarations are author-confirmed. The AI declaration is included immediately before References. The repository URL is confirmed public. A standard MIT `LICENSE` is present for project-authored repository materials, not the unredistributed NASA data.
- Supplement: `paper/submission/supplementary/supplementary_material.md`, Tables S1–S9, Figures S1–S2 (PDF and PNG), 13 byte-identical executed CSV copies, one copied executed seed-0 loss note, and `source_manifest.json` with SHA-256 provenance. The supplementary displays select existing records and plot recorded loss histories without smoothing or new endpoints.

## Presentation and integrity checks

- Tables I, II, and III remain beside Methodology, DS02 Results, and DS03 Confirmation, respectively. No figure content was regenerated for the main manuscript.
- All 20 PDF pages were rendered and visually inspected. No clipped table, figure, citation, or blank page was observed. Final compilation output had no overfull-box or unresolved-reference warning; minor underfull-line and small-font substitution warnings had no visible defects.
- The final PDF text scan found no `[6]AS.1943-5525.0001483)` or `[12]00060-7)` artifact. The source builder verifies all 12 references are cited and checks exhibit counts and citation tails.
- Five highlights were automatically counted at **71, 68, 73, 84, and 67 characters** including their bullet prefixes; each is at most 85 characters. The cover letter now includes the confirmed corresponding-author email and author assertions.
- The selected package directories contain no HDF5/ZIP raw NASA data, model checkpoints, or detected API/private-key patterns.
- Automated checks: **14 data-free static/synthetic unittests passed** in the validated research environment. No scientific experiment, fitting run, calibration, or test-data access was performed for this cleanup pass.

## Remaining live-portal action

Check the live RESS author instructions and submission portal for current file categories and administrative requirements during upload. These live portal settings cannot be verified from the local package.

**Scientific freeze confirmation:** No detector definition, phase rule, correction method, split, threshold, statistical endpoint, citation, or numerical result was changed. The reviewer-response pass strengthened the wording on engine heterogeneity, descriptive seed means, PCA-only correction sensitivity, and exploratory DS02 phase-rule sensitivity without changing the frozen DS03 confirmation verdict or running a new experiment.

**Verdict: SUBMISSION READY**

The local manuscript/package is complete. The live submission portal must still be followed during upload; the manuscript has not been submitted.
