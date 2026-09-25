# Elsevier-style manuscript source

`main.tex` uses the standard Elsevier `elsarticle` class in its single-column preprint layout. The four figures, three tables, manual verified bibliography entries, and structured `references.bib` are included in this directory. The manual `\bibitem` list is intentionally used in the compiled manuscript to preserve the already-audited reference text and numbering; `references.bib` is a companion source for later editorial conversion.

From the repository root, with Tectonic and its standard bundle installed:

```text
tectonic --keep-logs --keep-intermediates -o paper/output paper/ress/main.tex
```

This produces transient `paper/output/main.pdf` and `paper/output/main.log`, which are Git-ignored. For a clean rebuild, direct output to a new empty directory so `.aux` and `.out` files are regenerated. The retained, audited artifact is `paper/output/NCMAPSS_Flight_Phase_RESS_Final.pdf`; earlier draft/intermediate builds are not retained. A standard TeX distribution with `elsarticle` can also compile `main.tex` with two LaTeX passes. No RESS-specific class or unpublished requirement is assumed.

The source is generated without changing experimental outputs by `python scripts/build_ress_package.py` from the frozen clean LaTeX package. The script applies only the two requested wording edits and layout conversions.
