# Final RESS submission-package audit

## Package state

- Final manuscript: `paper/output/NCMAPSS_Flight_Phase_RESS_Final.pdf` — **18 pages**; compilation log: `paper/output/NCMAPSS_Flight_Phase_RESS_Final.log`.
- Editable source: `paper/ress/main.tex`, `paper/ress/references.bib`, four frozen main figures in `paper/ress/figures/`, and three source tables in `paper/ress/tables/`.
- Submission text files: `highlights.txt`, `cover_letter_final.md`, `data_availability_final.md`, `code_availability_final.md`, `credit_author_statement.md`, and `generative_ai_declaration.md`.
- Internal-only declarations: `competing_interest_draft.txt` and `funding_draft.txt`; neither is an author-confirmed official declaration.
- Supplement: `paper/submission/supplementary/supplementary_material.md`, Tables S1–S9, Figures S1–S2 (PDF and PNG), 13 byte-identical executed CSV copies, one copied executed seed-0 loss note, and `source_manifest.json` with SHA-256 provenance. The supplementary displays select existing records and plot recorded loss histories without smoothing or new endpoints.

## Presentation and integrity checks

- Tables I, II, and III remain beside Methodology, DS02 Results, and DS03 Confirmation, respectively. Table rows received modest additional spacing; bibliography type/spacing was tightened to remove the mostly empty nineteenth page. No figure content was regenerated for the main manuscript.
- All 18 PDF pages were rendered and visually inspected. No clipped table, figure, citation, or blank page was observed. The final log has no overfull-box or unresolved-reference warning; minor underfull-line and small-font substitution warnings remain without visible defects.
- The final PDF text scan found no `[6]AS.1943-5525.0001483)` or `[12]00060-7)` artifact. The source builder verifies all 12 references are cited and checks exhibit counts and citation tails.
- Five highlights were automatically counted at **71, 68, 73, 84, and 67 characters** including their bullet prefixes; each is at most 85 characters. The cover letter is approximately **369 words** including its author-confirmation note.
- The selected package directories contain no HDF5/ZIP raw NASA data, model checkpoints, or detected API/private-key patterns. Git has no staged files.
- Automated checks: **13 passed**, zero failed. No scientific experiment, fitting run, calibration, or test-data access was performed for this packaging pass.

## Unresolved placeholders and author actions

1. Replace `[REPOSITORY URL]` only after confirming the final public or reviewer-accessible code location.
2. Add and verify the corresponding-author email and complete author metadata.
3. Confirm the cover letter's originality, prior-publication, and exclusive-consideration statements.
4. Confirm competing interests, funding, and each proposed CRediT role. The current files are drafts, not submitted declarations.
5. Review the full substantive-AI-use statement against [Elsevier's current journal policy](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals); incorporate the approved separate declaration immediately before the references in the actual submission manuscript. Check whether Methods or figure-specific disclosure is additionally warranted.
6. Check the live RESS author instructions and submission portal for final file-category and administrative requirements.

**Scientific freeze confirmation:** No detector definition, phase rule, correction method, split, threshold, statistical endpoint, scientific claim, citation, or numerical result was changed. This pass made layout-only manuscript changes and assembled administrative/supplementary materials from frozen sources.

**Verdict: READY AFTER AUTHOR CONFIRMATIONS**

The manuscript has not been submitted.
