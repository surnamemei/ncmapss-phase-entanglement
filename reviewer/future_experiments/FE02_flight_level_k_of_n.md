# FE02: flight-level k-of-n confirmation at matched per-engine burden (prepared, not run)

**Scientific question.** The pre-specified persistence rules act within a flight (seconds). A post hoc two-consecutive-flight
rule removed most healthy flight-level burden under P at a delay cost (§4.9; C037). Two questions follow:
- Under k-of-n confirmation across flights (for example, 2-of-2 and 2-of-3), with burden matched **per engine** rather than pooled, does:
  - the transport conclusion (per-engine burden) change?
  - the delay comparison between C, Q and P change?

**Trigger.** Run only if a reviewer says persistence was tested at the wrong time scale, or that delay matching should be per
engine (Q33, Q34, I-10, I-11).

**Required inputs.** All are committed, so no raw data or GPU is needed:
- `results/extension/<DS>/audit/flight_trajectories.csv`. Columns: `subset, detector, seed, nominal_fpr, arm, rule, unit,
  cycle, state, k, rows, alarms, alarm_fraction, events, kappa, flagged`.
- `results/extension/<DS>/audit/detection_delay.csv` and `locked_operating_points.csv`.

**New computation.**
- For each run, arm and rule: apply a k-of-n rule to the flight flag sequence of each engine (the healthy flights in order,
  then post-onset).
- For per-engine matching: sweep κ over the observed `alarm_fraction` values so that each engine's healthy confirmed-alert
  rate hits a common anchor.
- Compare delays at matched per-engine burden.
- Note that κ is applied to the stored `alarm_fraction`, so the flight flags can be recomputed for any κ without re-scoring.

**Proposed script.** `reviewer/future_experiments/fe02_flight_k_of_n.py`, a new read-only file that writes only to
`results/reviewer_fe02/`. The anchors, the k-of-n set and the tie rules must be fixed in a dated plan before it runs.

**Expected outputs.** Per run, arm and rule:
- the worst-engine confirmed-alert rate at locked κ;
- per-engine matched-burden delay labels;
- a summary by family.

**Compute estimate.** CHEAP_CPU: pandas over roughly 10 MB per subset, seconds to minutes. No GPU.

**What it could support.** Whether flight-level confirmation, rather than within-flight persistence, absorbs the healthy burden
without losing transport information. It would also give a fairer delay comparison.

**What it could not support.**
- A change to H6 or H7, which stay pre-specified.
- Claims about operationally realistic false-alarm rates: there are only 14–36 healthy flights per engine.
