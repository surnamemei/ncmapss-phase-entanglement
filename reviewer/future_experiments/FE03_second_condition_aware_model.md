# FE03: a second condition-aware representation (prepared, not run)

**Scientific question.** H5 rests on one fleet-trained CVAE. That model has a heteroscedastic decoder at its variance floor for
many channels, and its score omits the latent-prior (KL) term (§3.4, §5.5; C018). Would a different condition-aware
representation reduce per-engine transport error? Candidates are:
- (a) a KL-inclusive ELBO score;
- (b) training on the early cycles of the audited engines themselves, as in Chen et al. [N38] (a different, per-engine regime);
- (c) a fixed-variance decoder.

**Trigger.** Run only if a reviewer rejects the scoped CVAE claim, or insists on a replication of [N38]-style training (Q25, I-08).

**Required inputs.**
- The raw `N-CMAPSS/*.h5` files.
- The locked roles and correction models (`results/extension/<DS>/models/correction.pkl`).
- `docs/extension/CVAE_SPECIFICATION.md`, as the template for a new, separately frozen specification.

**Reusable existing data.**
- The locks: calibration rows and roles.
- The residual-detector outputs, for comparison: `*/audit/transport_summary.csv`.
- The CVAE training code `src/ext_cvae.py`. It is to be reused by import or copied into a new module; it must not be edited.

**New computation.** Training 7 subsets × 3 seeds per variant on GPU, then calibration, audit scoring and the endpoint tables.

**Important.** Variant (b) trains on audit engines' early cycles. That breaks engine-disjointness, so it must be reported as a
different estimand (per-engine monitoring), never mixed into H5.

**Proposed script.** `scripts/run_reviewer_fe03.py` plus a new frozen specification `docs/extension/CVAE2_SPECIFICATION.md`.
Outputs go to `results/reviewer_fe03/`.

**Expected outputs.** For each variant: ME-A2, WE-A2 and n_worse under P/C/Q, in the same table format as Table 3 and Fig. 5.

**Compute estimate.** EXPENSIVE: hours of GPU. The CVAE lock timings range from 57 s to 633 s per subset for three seeds, plus
epoch selection. The number of variants multiplies the cost.

**What it could support.** Whether the "no transport improvement" result is specific to the tested CVAE.

**What it could not support.** A general statement about all condition-aware models; and, for variant (b), any claim about
cross-engine transport.
