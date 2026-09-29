# Future reviewer experiments (prepared, NOT run)

None of these has been executed. Each is triggered only by a specific reviewer request. Each must first be frozen as a
dated plan under `docs/extension/` (following `FOCUSED_VALIDATION_PLAN.md`), must write to a **new** output directory, and must
never modify `results/extension/**`, `paper/mssp_extended/**` or the ledger.

| ID | Question | Trigger | Compute | GPU? | Needs raw data? |
|---|---|---|---|---|---|
| FE01 | Does per-unit recalibration with k = 3 or 10 flights, or causal re-baselining, fix per-engine error? | Reviewer asks for a per-unit or practitioner baseline (Q24, I-09) | GPU (re-scoring audit rows with locked models) | Yes, for LSTM/CVAE | Yes |
| FE02 | Does flight-level k-of-n confirmation at matched **per-engine** burden change transport or delay conclusions? | Reviewer says persistence was tested at the wrong time scale (Q33, Q34, I-10, I-11) | CHEAP_CPU | No | No (committed `flight_trajectories.csv`) |
| FE03 | Does a second condition-aware model (per-engine or early-cycle training, or a KL-inclusive score) change H5? | Reviewer says one CVAE is unrepresentative (Q25, I-08) | EXPENSIVE (training) | Yes | Yes |
| FE04 | How much of per-engine A2 is transport rather than in-sample pooling error, and how much is under-alarming? | Reviewer says A2 conflates error sources (Q29, Q30, I-02, I-03) | CHEAP_CPU | No | No |

For the cheapest items (FE02, FE04), a read-only skeleton script may be written in a new file under this folder. Nothing
here imports or modifies the scientific pipeline.
