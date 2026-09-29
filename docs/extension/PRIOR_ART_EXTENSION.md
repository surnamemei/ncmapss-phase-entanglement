# Prior art for the extension: Chen 2026 and Asaadi 2025 read in full

**Date.** 2026-09-28.

**Sources.** The author supplied the publisher PDFs of both papers; their SHA-256 hashes are in the evidence file. Every quote below was machine-checked against the extracted text:
- `paper/mssp/literature_evidence/extension_fulltext_quotes.json`;
- `extension_fulltext_quote_check.txt` (16/16 verified, with page numbers).

The PDFs are not redistributed.

**Status change.** Earlier (`paper/mssp/NOVELTY_POSITIONING.md`, "Verification limits") these two papers were checked only at abstract or preprint-abstract level. They have now been read in full. Diallo 2025 is still unread in full.

## Chen, Li, Xu and Wang (2026), RESS 267:111894: SA-CVAE for gas turbines

| Brief's proposed distinction | Verified? | Evidence (quote ID, page) |
| --- | --- | --- |
| Variable operating conditions induce multiple-pattern normality | **Yes** | CH1, p. 3: "The variation of OCs in normal operating states (OSs) can cause the multiple pattern normality to emerge in the monitoring data." |
| A universal HI threshold may not apply across operating conditions | **Yes** | CH2, p. 3: "Training AD models using data samples from different OCs cannot provide a universal HI threshold applicable to all conditions, and the missed alarm or false alarm rate rises." (The earlier withdrawal of this point, made because the abstract did not support it, is reversed: the full text supports it.) |
| Condition-aware representations can explicitly incorporate OC variables | **Yes** | CH3, p. 1: "…by incorporating OC variables as conditional inputs in the variational autoencoder (VAE) model, and decoupled modeling of equipment states and external OCs is achieved." |
| Its main contribution is an SA-CVAE detector/representation | **Yes** | CH4, p. 1 (abstract: the framework "was proposed based on conditional variational autoencoder (CVAE) optimized with self-attention (SA)") |
| On N-CMAPSS it evaluates DS02 with its own train/test setup | **Yes, and narrower than stated** | It uses only the six DS02 development units: CH5, p. 8: "six long-range flight engine units (U2, U5, U10, U16, U18, U20)". These are all flight class 3, as the project's metadata audit confirms. CH6, p. 8: "the first 10 flight cycles of each engine are considered healthy samples and used for training, while subsequent flight cycles of U5 and U16 are reserved for testing". **The test engines therefore also contribute training cycles.** CH7, p. 8: dataset B is "mainly used to evaluate the correlation between the constructed HI and the engine's actual health status". The inputs are CH9, p. 8: "4 scenario descriptors and 14 sensor measurements", the same channels as this project |
| It does not perform the same engine-disjoint healthy-FPR calibration-transport audit | **Yes** | See the absences listed below |

**What Chen et al. do not do** (from the full text):
- no per-operating-condition or per-phase healthy FPR;
- no nominal-calibration-error endpoint;
- no engine-disjoint calibration and audit;
- no cross-engine transport;
- no held-out confirmation.

**Their threshold is a single KDE threshold** on the conditioned health indicator. CH8, p. 6: "When confidence level is set at 95 %, the corresponding lower bound is utilized as the LRP threshold for AD."

This is exactly the design question our H5 tests: **does representation-level conditioning make one pooled threshold on the conditioned score valid within operating contexts and across engines?**

**How the extension uses Chen et al.** The CVAE baseline is inspired by their conditioning idea and is explicitly not a reproduction:
- it has no self-attention;
- its score is the NLL at the posterior mean;
- it conditions on the project's 32 past-only descriptors;
- it is calibrated with the same P, C and Q arms as the other detectors.

## Asaadi, Yang and Wu (2025), J. Process Control 155:103536: operational zone-specific alarm design

| Brief's proposed distinction | Verified? | Evidence (quote ID, page) |
| --- | --- | --- |
| Nonstationary alarm behaviour should not be collapsed into stationary average FAR/MAR | **Yes** | AS1, p. 1: "Traditional alarm design methods often assume stationary, which limits their ability to reflect the evolving nature of incipient faults." AS2, p. 2: "a non-stationary model should provide time-variant FAR and MAR, and the alarm system should be designed based on these time-variant indices, rather than relying on constant mean values." |
| Time-varying FAR/MAR/AAD matter | **Yes** | AS2; AS3, p. 1: "the AAD metric reflects realistic delay patterns and avoids the misleading interpretations often associated with stationary models." |
| Persistence, filter and deadband policies change alarm trade-offs | **Yes** | AS4, p. 4: "when techniques such as Deadband, Filtering, and Delay Timers are introduced, we must recalculate the FAR, MAR, and AAD accordingly." AS7, p. 15 lists the design levers: "adjustments in trip points, implementation of deadband mechanisms, utilization of delay timers, and application of signal filtering." The introduction reviews n-out-of-m on-delay and off-delay timers |
| Its operational zones describe fault progression and recovery, not external flight operating context | **Yes** | AS5, p. 2: the zones "capture the progression of the fault and the system's response" (normal operating, rising, fault, return to normal) |
| It does not study cross-engine calibration transport | **Yes** | It is univariate process-variable alarm design, validated by Monte Carlo simulation and the Tennessee Eastman process (AS6, p. 1). There are no multiple units, and no calibration-to-audit transport |

**How the extension uses Asaadi et al.** The persistence rules R1 (3 consecutive exceedances) and R2 (3 of 5) are standard on-delay timers of the kind this literature analyses. Following it, the extension recomputes false-alarm and delay quantities under each policy instead of assuming that a row-level calibration carries over.

## Novelty statement after the extension (narrower, unchanged in spirit)

- It is **not** new that pooled or universal thresholds can fail across operating conditions. Chen et al. state it, and mode-specific limits (Zhao et al.), per-mode false-positive analysis (Michau and Fink) and regime-wise thresholds (Toshkova et al.) predate this work.
- It is **not** new that alarm policies change FAR/MAR/delay trade-offs (Asaadi et al. and the delay-timer literature).
- What remains specific to this work is the **engine-disjoint, pre-specified audit of nominal healthy-FPR calibration transport** under full-flight operation, now across nine N-CMAPSS subsets in seven fleet families. It covers:
  - pooled, phase-conditioned and continuous-context calibration arms;
  - a condition-aware representation baseline;
  - fixed-volume calibration-composition interventions;
  - standard persistence rules;
  - matched false-flag delay comparisons.

  Its conclusions are stated only as the pre-specified rules classify the results.
- **"First" is not claimed.**
