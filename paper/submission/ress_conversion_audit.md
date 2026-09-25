# RESS-style conversion audit

## Scope and template basis

- Source: `paper/latex_clean/main.tex`, its verified `references.bib`, four existing figure files, and three existing tables. No HDF5, model, or results-generation script was run.
- Elsevier's [LaTeX author instructions](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions) identify `elsarticle` as its article class. No separate RESS-specific class was found locally, so `paper/ress/main.tex` uses standard `elsarticle` in single-column preprint mode. This does not assert an unverified journal-specific requirement.
- Local compilation used Tectonic 0.17.0 and its standard-bundle `elsarticle` 3.3. The build log is `paper/output/NCMAPSS_Flight_Phase_RESS_Draft.log`.

## Formatting changes

- Converted the title, sole author, Sydney affiliation, abstract, and keywords to `elsarticle` front matter; no email, ORCID, coauthor, or correspondence status was added.
- Used automatic sections 1–6 and retained the existing subsection structure. Removed the class's misleading “Preprint submitted to” footer from the unsubmitted draft.
- Converted the 12 verified in-text references to LaTeX citations while preserving their existing bibliography order and DOI/arXiv details. The compiled source uses the verified manual `\bibitem` entries; `paper/ress/references.bib` is provided as an editable Elsevier-compatible companion.
- Moved exhibits near their first relevant sections: Fig. 1 on p. 5; Table I on p. 7; Fig. 2 on p. 10; Table II on p. 11; Fig. 3 on p. 12; Fig. 4 and Table III on p. 14. Figures use the frozen image files and original captions. Tables were reflowed without altering data values to avoid tiny scaled type. Table III places each contrast next to its original run-level interval in one column.
- Final PDF: 19 letter-size pages. Every page was rendered for visual inspection. No blank page, clipped element, unresolved citation, draft label, or overfull box remains. The log contains only non-fatal underfull-line warnings.

## Editorial wording changes

1. Introduction: `unchanged. [2], [10].` became `unchanged [2], [10].` (citations are represented with `\cite` in LaTeX).
2. Discussion: `conditional calibration` became `phase-conditional false-alarm behaviour` in the passage describing observed phase-wise behaviour.

No other scientific claim or numerical result was rewritten. Automated comparison found identical numeric tokens in all six detector data rows across Tables II–III before and after conversion; the 11 verified DOI identifiers and one arXiv identifier remain present. The four figure and three table captions retain their original meaning and values.

## Submission documents

- `highlights.txt`: five factual highlights.
- `cover_letter.md`: restrained RESS-oriented draft.
- `declaration_of_interests.md`, `data_availability.md`, `code_availability.md`, `funding_statement.md`, and `author_contributions.md`: conservative drafts with author-verification markers where needed.
- `ai_assistance_note.md`: internal author-review note, not an asserted journal-required declaration.
- `graphical_abstract_plan.md`: optional concept only; no graphical abstract was created.

## Author confirmation still required

- Confirm originality and exclusive consideration before using the cover letter.
- Confirm competing-interest and funding statements, each CRediT role, and the AI-assistance description against actual circumstances and current journal policy.
- Confirm the final NASA data landing page, repository public visibility, and a citable code release or commit.
- Recheck current RESS submission instructions in Editorial Manager before upload. This package has **not** been submitted.

**Scientific freeze:** No experiment was run and no detector definition, phase rule, correction, threshold, split, statistical endpoint, scientific claim, or numerical result was changed.

## Citation-rendering correction

- The clean Markdown links were complete, and the BibTeX DOI fields and bibliography `\href` entries were not the cause. The earlier Markdown-to-LaTeX conversion had stopped at parentheses within the DOI URLs of references [6] and [12], leaving two `AS.1943-5525.0001483)` tails and one `00060-7)` tail after in-text citation tokens in `paper/latex_clean/main.tex`. The RESS builder had copied those tails.
- `scripts/build_ress_package.py` now removes exactly those three conversion artifacts, verifies their expected counts, and rejects an in-text `\cite{refN}` immediately followed by alphanumeric text. Full DOI strings remain in the bibliography and `references.bib` only.
- `paper/output/NCMAPSS_Flight_Phase_RESS_Clean.pdf` was compiled in an empty output directory. Its `.aux` and `.out` files were regenerated; `.bbl` and `.blg` are not applicable because the compiled manuscript uses the verified manual `\bibitem` list rather than a BibTeX run. The compilation log is `paper/output/NCMAPSS_Flight_Phase_RESS_Clean.log`.
- All 19 pages were rendered and visually inspected. All 12 distinct bibliography entries are cited, none is duplicated, no unresolved citation or stray DOI fragment remains in prose, and no text extends off-page. Minor underfull-line warnings remain; there are no overfull-box warnings. Tables II and III received a small layout-only font/row-spacing increase. Detector-table numeric tokens and frozen figure bytes remain unchanged.
