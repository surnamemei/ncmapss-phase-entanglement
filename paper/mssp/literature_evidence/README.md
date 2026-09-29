# Literature evidence (2026-09-28)

These files record how the references in `../reference_audit.csv` and `../reference_audit_mssp.md` were verified.

- **`delegated_search_candidates.json`.** One record per candidate from the second, delegated search. Each record gives the metadata source and the verbatim supporting quotation, an explicit `verified` flag, and the reasoning behind the keep/optional/drop decision.
- **`delegated_search_quote_check.txt`.** A machine check that every quoted fragment (97/97) appears in the saved source text.
- **`delegated_search_novelty_answers.md`.** Answers to the five prior-art questions, with evidence keys.

N22, N23 and N24 (the closest precedents) were independently re-checked against their saved source texts. The downloaded PDFs and pages are not committed, because they are third-party copyrighted material; the DOIs and URLs in the audit identify them.

No personal data was sent to any service; requests used a generic User-Agent.

## Final prior-art audit (2026-09-28)

- **`closest_prior_art_quotes.json`.** Verbatim quotations, with source URLs, for the newly examined closest works:
  - Chen et al. 2026 [N38];
  - Asaadi et al. 2022 [N39];
  - Asaadi et al. 2025 [N40];
  - Diallo et al. 2025 [N41];
  - the uncited Steland 2026 preprint.
- **`closest_prior_art_quote_check.txt`.** A machine check that every quotation occurs in the saved source text (9 of 9).
- **`crossref/`.** Cached Crossref records (CC0 metadata) for every DOI in the manuscript bibliography.
- **`bibliography_check.csv`.** The result of checking each DOI's title, year and first author against the reference spec (`../build_bibliography.py`).

Access levels and their limits are stated in `../NOVELTY_POSITIONING.md` and in the `access_level` column of `../reference_audit.csv`.
- **`final_audit_records.json`, `final_audit_quote_check.txt`, `final_audit_screening_log.txt`.** Output of the delegated final closest-prior-art check: 14 records with feature flags and verbatim quotes, a 121/121 machine quote check, and the task-6 screening log. The quotes point to source texts saved outside the repository, because they are copyrighted.
