# Proposed release: v0.2-manuscript-analysis-freeze

DS02 discovery analysis, DS03 frozen confirmation, authoritative evidence ledger, and manuscript-generation pipeline frozen.

The repository preserves the executed canonical/bootstrapped outputs and the unchanged one-shot protocol. Superseded Phase 3 narrative reports are archived, not deleted. Guarded reproduction wrappers refuse to overwrite existing runs, and manuscript-generation scripts read the ledger-derived core-results CSV. This cleanup changed path configuration and repository documentation/tests only; it did not change detector definitions, phase rules, correction methods, splits, thresholds, or the frozen confirmation protocol.

No tag was created. Before tagging, review the uncommitted cleanup, the remaining limits in `docs/ENVIRONMENT.md` and `docs/AUTHORITATIVE_RESULTS.md`, and rerun the lightweight tests. Do not rerun scientific experiments merely to create the tag.
