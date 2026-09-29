# Amendments and errata: MSSP mitigation protocol v1.0

Changes after the freeze are governed by protocol §13. The frozen protocol and `docs/mssp/FREEZE_RECORD.md` stay byte-identical; their SHA-256 values are in the freeze record. Each entry below supersedes the statements it corrects.

## A-1 (2026-09-28): erratum, repository metadata only

| Field | Content |
| --- | --- |
| Type | Factual correction about a release tag. No analysis change. |
| Timing | Before any abnormal (`hs = 0`) row was opened or scored. Stages B–D were complete and Stage E had not started. |
| Authorized by | The author, 2026-09-28: treat the published remote `v1.0.0` as authoritative, record the correction here, and change no analysis history or frozen baseline file. |

**Statements corrected.**
- Protocol v1.0 header: "The earlier release tag `v1.0.0` (`24c2836`) is unchanged."
- `FREEZE_RECORD.md`: "The release tag `v1.0.0` (`24c2836`) is unchanged."

**Correct facts.**
- The published tag `v1.0.0` on `origin` (https://github.com/surnamemei/ncmapss-phase-entanglement) is a lightweight tag at `1f59e9e`. That is the RESS-submitted commit, and this published tag is authoritative.
- The corrected statements described a stale local lightweight tag at `24c2836` (2026-09-25 17:35 AEST).
- On 2026-09-28 the local tag was synced to the published one with `git fetch origin +refs/tags/v1.0.0:refs/tags/v1.0.0`. The previous local value was `24c2836c202572675dc9f5c90d6364b3077f2c68`.

**Unaffected.**
- `ress-submission-2026-09-25` → `1f59e9e`. It is the same commit as the published `v1.0.0`, and its annotation already says so.
- The identification of `1f59e9e` as the submitted state.
- Constraint C1 and §11.3, which name `v1.0.0` as a RESS reference. They now refer to the published tag at `1f59e9e`.
- The header statement that no file under `results/`, `src/`, `configs/`, `scripts/`, or `tests/` differs between `v1.0.0` and `1f59e9e`. It was true for `24c2836` and is trivially true for the published tag.

**Analysis impact.** None. No threshold, κ, causal-regime rule, guardrail, endpoint definition, split, code, or output changed. The baseline manifest (186 files) still verifies.
