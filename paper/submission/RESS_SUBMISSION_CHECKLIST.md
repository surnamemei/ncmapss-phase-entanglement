# RESS submission checklist

This is a pre-submission checklist, not evidence that any file has been uploaded. Scientific analysis and numerical results remain frozen.

## Files and author declarations

- [x] Final RESS-style manuscript PDF: `paper/output/NCMAPSS_Flight_Phase_RESS_Final.pdf` (18 pages).
- [x] Editable LaTeX source and verified bibliography: `paper/ress/main.tex`, `paper/ress/references.bib`.
- [x] Four main figure files: `paper/ress/figures/`.
- [x] Five highlights: `paper/submission/highlights.txt`; lengths including bullet prefix are 71, 68, 73, 84, and 67 characters, respectively.
- [x] Cover-letter draft: `paper/submission/cover_letter_final.md` (author assertions require confirmation).
- [x] Author-confirmed competing-interest declaration: `competing_interest_final.txt`.
- [x] Author-confirmed funding statement: `funding_statement_final.txt`.
- [x] Data-availability draft with the official NASA source: `data_availability_final.md`.
- [x] Code-availability statement with confirmed public repository URL: `code_availability_final.md`.
- [x] Author-confirmed CRediT roles: `credit_author_statement.md`.
- [x] Author-confirmed AI-use statement: `generative_ai_declaration.md`.
- [ ] Place the confirmed AI declaration immediately before references in the manuscript file used for submission, as required by the current Elsevier journal policy.
- [x] Frozen supplementary material: `paper/submission/supplementary/` (Tables S1–S9, Figures S1–S2, byte-identical source copies, provenance manifest).
- [ ] Corresponding-author email.
- [x] Repository URL and public access confirmed: https://github.com/surnamemei/ncmapss-phase-entanglement (HTTP 200 checked).
- [x] Standard MIT `LICENSE` is present; it does not license NASA N-CMAPSS data.
- [ ] All author metadata, correspondence designation, and affiliation details confirmed.
- [ ] Originality, prior-publication status, and exclusive consideration confirmed for the cover letter.

## Manuscript and package audit

- [x] Title in the PDF matches the frozen working title and cover letter.
- [x] Abstract and keywords were carried directly from the frozen clean manuscript source.
- [x] All 12 verified references resolve to numbered citations; no orphan or duplicate bibliography entries were found in the source audit.
- [x] No unresolved citation or stray DOI-citation artifact appears in the final PDF.
- [x] No unsupported claim was introduced by this packaging pass; presentation changes are limited to table/bibliography spacing.
- [x] Main figures and tables are beside their intended sections; all 18 pages rendered and visually reviewed.
- [x] No raw NASA HDF5/ZIP files or model checkpoints are included in `paper/submission/` or `paper/ress/`.
- [x] No API-key/private-key pattern was found in those package directories.
- [x] No raw NASA data or model checkpoints are staged in this cleanup.
- [x] Repository checks: 14 data-free static/synthetic unittests passed in the validated research environment.
- [ ] Author to recheck the live RESS submission portal's file categories and current journal instructions before upload.

NASA data source: [NASA Prognostics Center of Excellence Data Set Repository, entry 17](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/). Elsevier policy check: [Generative AI policies for journals](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals).
