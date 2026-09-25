# N-CMAPSS healthy false alarms across flight phases

This repository studies whether healthy false-alarm rates under pooled calibration differ among retrospectively defined climb, cruise, and descent in N-CMAPSS. DS02 is exploratory discovery data. DS03 is an independent, held-out confirmatory subset evaluated once under a protocol frozen before official-test access. Results were observed across three tested implementations—residual PCA, Isolation Forest, and a causal LSTM sequence-reconstruction network—under a common correction and calibration framework. The study does not establish a causal mechanism or deployment performance.

## Data and repository layout

Raw N-CMAPSS data are **not redistributed**. Obtain DS02 and DS03 through the NASA N-CMAPSS distribution and supply local HDF5 paths via `--data` or `NCMAPSS_DS02_H5` / `NCMAPSS_DS03_H5`. The default relative location is `N-CMAPSS/`, which is Git-ignored. Provenance records for the executed DS03 file are in `results/confirmation_ds03/source_provenance.json`.

- `src/`: validated scientific analysis and one-shot confirmation code.
- `configs/`: frozen-value snapshots of experimental constants; scientific scripts retain their original values.
- `results/final_validation/`: DS02 canonical and hierarchical-bootstrap outputs; frozen protocol.
- `results/confirmation_ds03/`: DS03 canonical and bootstrap outputs, calibration lock, and one-shot marker.
- `paper/`: evidence ledger, core result selection, manuscript work, and builders.
- `scripts/`: guarded reproduction and manuscript-generation entry points.
- `tests/`: synthetic and static leakage/provenance checks.
- `archive/obsolete_reports/`: superseded narrative reports, retained only for provenance.
- `archive/historical_reports/`: early screening reports, not manuscript numeric sources.

See `docs/AUTHORITATIVE_RESULTS.md` before citing numbers. Obsolete Phase 3 reports and superseded cross-detector outputs must not be used for manuscript claims.

## Code availability

Code and analysis materials are available at https://github.com/surnamemei/ncmapss-phase-entanglement. Raw NASA N-CMAPSS data are not included.

## Reproduction commands

Use the configured CUDA-enabled research Python (see `docs/ENVIRONMENT.md`). All reproduction wrappers default to a read-only dry run. An authorized full run requires `--execute` and a **new**, nonexisting output path; it can be computationally expensive. These commands document reproduction and were not run during the repository-cleanup freeze:

```text
python scripts/reproduce_ds02.py --data PATH_TO_DS02_H5 --output-root NEW_DS02_RUN
python scripts/reproduce_ds02.py --data PATH_TO_DS02_H5 --output-root NEW_DS02_RUN --include-correction-comparison --execute
python scripts/reproduce_ds03.py --data PATH_TO_DS03_H5 --output-dir NEW_DS03_RUN
python scripts/reproduce_ds03.py --data PATH_TO_DS03_H5 --output-dir NEW_DS03_RUN --execute
python scripts/build_paper_tables.py --dry-run
python scripts/build_paper_figures.py --dry-run
python scripts/build_paper_tables.py
python scripts/build_paper_figures.py
python -m unittest discover -s tests -v
```

The DS03 code creates its official-test-opened marker only after model fitting and threshold calibration. An existing output directory, including the archived canonical confirmation directory, is not overwritten by the wrapper. Manuscript builders consume the frozen core-results CSV, not HDF5 data. Do not treat the historical pre-confirmation status text in the frozen protocol as a later result update.
