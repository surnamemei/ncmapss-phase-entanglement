# Extension freeze record

This file records what was frozen before any new outcome existed. The hashes come from the DS01 calibration lock, whose `code` block is computed at lock time, and from the committed files.

| Item | Value |
| --- | --- |
| Protocol `docs/extension/GENERALIZATION_PROTOCOL.md` | frozen at `d298623`; SHA-256 at lock time `72ff84e198fcc4c466f898159c7bc04b879f55036c5d425a2a7285cffc3d3bce` |
| CVAE specification `docs/extension/CVAE_SPECIFICATION.md` | frozen at `1b3ca60`, with Amendment 2 at `27a6346`; SHA-256 at lock time `8fe45498a9f194d42a5e67fe3b871694e814bb3dfab69ecadbf2bee5b914bba7` |
| Amendments | 1: classification gaps, before any outcome (`e3cd95a`). 2: CVAE numerical safeguards after a stop-rule halt, before any outcome (`27a6346`) |
| Git HEAD recorded in the DS01 lock | `e6b6a857580d9ceb9f06aaa6acdb302c9f43119f` |
| `src/ext_calibration.py` at lock time | `4f3009102b038cf2b192edf0c36008fe43da72280d8a2e60cc1cea7f05c02918` |
| `src/ext_common.py` at lock time | `8b33f760c113f661fb4ce338656eac36b0197e8bfea2858e470d33e181e57f4c` |
| `src/ext_cvae.py` at lock time | `7db4ca5c099d5db1b8ecc78276478e65872ea2206e4c9b94d589f474f90725fe` |
| `src/ext_endpoints.py` at lock time | `3599f31faab73f6b8685b6746a93e10a890f87c70dfb7c7c7fced7f8edcf928f` |
| `src/ext_models.py` at lock time | `e0cd2e307d480af6532fc468db2e53dc71ee6afc7469453ad1878781c30e292b` |
| `src/ext_pipeline.py` at lock time | `a38cc1e994d528086996f7b13d91d67e3523c6c4a88865e73d6404d878f3c0f8` |
| `src/ext_qfit.py` at lock time | `465b352952b9e6e55090cc29a25bd453b841519b0023e6237c3d3ed98dd9d922` |
| `src/ext_summary.py` at lock time | `1219cc017d9afc2e58d9ec6318914bfd06b53896f2c9b491c01203f89546753d` |

**Tests at freeze.** 116/116 passed at `e3cd95a` (86 pre-existing and 30 new). Adding the Amendment 2 test made 31/31 extension tests pass.

**Lock order and runtime.** Phase L runs in frozen order (DS01, DS04, DS05, DS06, DS07, DS08a, DS08c). The Q-fit worker count (10 or 15 processes) is an execution parameter only: every linear program is independent and deterministic.

**Compute note.** The protocol estimated 10–15 minutes for the 30 Q-arm linear programs per subset. The actual time was about 1 hour: 3,549 s for DS01 with 10 workers. The frozen solver specification (`QuantileRegressor(alpha=0, solver='highs')`, every 5th row) was kept unchanged.
