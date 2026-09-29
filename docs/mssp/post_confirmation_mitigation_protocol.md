# MSSP revision: post-confirmation mitigation protocol (pooled vs phase-conditioned calibration)

> **Status: FROZEN v1.0.** Approved by the author on 2026-09-27; the decision record is in §12. The freeze commit and the SHA-256 of this file are recorded in `docs/mssp/FREEZE_RECORD.md`. Any change after the freeze follows §13 only.
>
> **Branches and tags.**
> - Branch `mssp-revision` was created from `main` at `1f59e9e`.
> - The RESS-submitted snapshot is preserved by the annotated tag `ress-submission-2026-09-25` → `1f59e9e`. No GitHub Release is created.
> - The earlier release tag `v1.0.0` (`24c2836`) is unchanged.
> - No file under `results/`, `src/`, `configs/`, `scripts/`, or `tests/` differs between `v1.0.0` and `1f59e9e`.
>
> **Drafting exposure.** While drafting v0.1, no N-CMAPSS HDF5 file was opened and no model was fitted, loaded, or scored. Quantities quoted below come from tracked, already-frozen CSV/JSON files or from recorded file sizes. The outer NASA archive ZIP's directory was listed (member names only); nothing was extracted.

**Reviewer quick path:** §12 decision record → §6 stages, stops, and gates → §7 leakage and information-exposure audit → §4 exact endpoints → §11 manuscript plan.

---

## 0. Constraints this protocol cannot override

| ID | Constraint | Enforcement |
| --- | --- | --- |
| C1 | The RESS submission and release are preserved. This covers: `main`; tags `v1.0.0` and `ress-submission-2026-09-25`; `paper/ress/`; `paper/submission/`; `paper/output/NCMAPSS_Flight_Phase_RESS_Final.pdf`; `paper/evidence_ledger.csv`; `paper/manuscript_core_results.csv`; RESS figures and tables; and the RESS manuscript sources. All remain byte-identical. | All MSSP work lives on `mssp-revision`, in new paths only (§10). `docs/mssp/frozen_baseline.sha256` lists 186 files: every tracked file under `results/`, `src/`, `configs/`, `scripts/`, and `tests/`; the RESS package and evidence files; and all 12 LSTM `.pt` checkpoints (final and selection, both datasets). It must pass `sha256sum -c` before and after every stage. |
| C2 | The frozen DS03 confirmation is not altered, rerun as a confirmation, or reinterpreted. | `results/confirmation_ds03/` and `results/final_validation/`, including checkpoints, are read-only inputs. The confirmation verdict, numbers, exceptions, and intervals are cited only through existing evidence IDs. Firewall rules F1–F6 apply (§5.4). |
| C3 | The mitigation analysis is post-confirmation and exploratory on both DS02 and DS03. | Outputs, the ledger, and the manuscript carry this label (§11). The interpretation rules yield descriptive statements only (§5.3). |
| C4 | Detectors, correction, hyperparameters, engine split, phase rule, and nominal targets do not change. There is no training and no tuning. | PCA and Isolation Forest are deterministic refits of the frozen specification. The LSTM runs are loaded from the frozen final checkpoints. Gate G4 must show identity with the frozen outputs before anything new is computed. |
| C5 | GPU work fails rather than falling back to CPU (`AGENTS.md`). | `final_validation.configure_cuda_runtime()` runs first in every model stage; if no CUDA device is present, the stage aborts. Only LSTM inference uses the GPU. |
| C6 | Nothing runs beyond what the author has approved. | The protocol, code, and data-free tests are committed before Stage B (§6, Stage A). Execution stops after the reproduction gate (Stages B–C) for the author's review. Abnormal-state rows (Stage E) need a separate, explicit author approval. |

## 1. Question and signal-processing framing

Residual-based health monitoring under nonstationary operation is a three-step chain:

1. **Operating-condition normalization.** The frozen finite-history ridge correction regresses the 14 `X_s` channels on causal `alt`/`Mach`/`TRA`/`T2` descriptors.
2. **A scalar detection statistic $s_t$.** This is the PCA squared prediction error, the Isolation Forest path score, or the causal LSTM reconstruction error.
3. **A threshold decision.** $a_t = \mathbb{1}[s_t > \tau]$, with $\tau$ set for a nominal false-alarm probability $\alpha$.

A pooled threshold controls only the exposure-weighted (marginal) false-alarm probability:

$$P(a=1\mid h) = \sum_{\phi} \pi_\phi \, P(a=1 \mid h,\phi).$$

The frozen study showed that $P(a=1\mid h,\phi)$ differs by phase under pooled calibration.

The standard remedy is **phase-conditioned calibration**: one threshold per operating regime. This is a regime-wise constant-false-alarm-rate (CFAR) threshold, equivalently group-conditional ("Mondrian") quantile calibration. On calibration data it sets $P(a=1\mid h,\phi)\approx\alpha$ in every phase by construction. It also moves alarms, and therefore detection power, between phases.

The evaluation is therefore a **trade-off, not a false-alarm reduction**. The overall healthy FPR need not fall, and fault sensitivity can move in either direction.

**RQ4 (post-confirmation, exploratory).** On the existing engine-disjoint calibration/audit structure:
- Does phase-conditioned calibration make healthy phase-wise FPR more stable across phases and engines than the existing pooled calibration?
- What does it cost or gain in abnormal-state sensitivity and detection delay, where the retained N-CMAPSS labels support those endpoints?

**Terminology.** In N-CMAPSS, `hs = 0` marks the simulated onset of *abnormal degradation*. It is not a discrete fault event, and `hs = 1` flights already include normal degradation. Endpoints are therefore named *abnormal-state sensitivity* and *delay relative to the labelled onset*, never fault-detection accuracy.

## 2. Data, engines, and labels

Engine roles are unchanged from the frozen configurations (`configs/ds02_discovery.yaml`, `configs/ds03_confirmation.yaml`).

| Dataset | Role in the MSSP paper | Model-fit engines | Calibration engines | Audit engines |
| --- | --- | --- | --- | --- |
| DS02 `N-CMAPSS_DS02-006.h5` (MD5 `61056251…`) | Discovery; post-hoc mitigation replicate | 2, 5, 10, 16 | 18, 20 | 11, 14, 15 |
| DS03 `N-CMAPSS_DS03-012.h5` (MD5 `a301cd2c…`) | Frozen confirmation subset, reused *after* confirmation as the primary dataset for the exploratory mitigation analysis | 1, 2, 3, 5, 6, 7, 9 | 4, 8 | 10, 11, 12, 13, 14, 15 |

**Labels used.** Only `A_*` columns: unit, cycle, Fc, hs.

- `hs = 1` selects rows for fitting, calibration, and healthy FPR. This is the unchanged, disclosed oracle restriction.
- `hs = 0` defines abnormal-state audit rows.
- $o_e$ is the first cycle with `hs = 0` in audit engine $e$.
- $\mathrm{EOL}_e$ is the last recorded cycle.

**Not used:** `Y` (RUL, which is redundant with cycle for run-to-failure records), `T` (health parameters), and `X_v` (virtual sensors). Labels, phases, and identifiers are never detector inputs.

**Label structure already known from tracked files.** No data access was needed for the following.

DS02 (`results/cycle_phase_audit.csv`, per-flight `healthy_rows`): every flight is entirely `hs = 1` or entirely `hs = 0`, and each engine switches exactly once.

| DS02 engine | Role | Fc | Flights | Healthy | Abnormal | Onset cycle $o_e$ | EOL | Abnormal rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 18 | calibration | 3 | 71 | 16 | 55 | 17 | 71 | not used |
| 20 | calibration | 3 | 66 | 16 | 50 | 17 | 66 | not used |
| 11 | audit | 3 | 59 | 18 | 41 | 19 | 59 | 450,189 |
| 14 | audit | 1 | 76 | 35 | 41 | 36 | 76 | 84,510 |
| 15 | audit | 2 | 67 | 23 | 44 | 24 | 67 | 285,931 |

DS02 audit totals: 433,113 healthy rows and 820,630 abnormal rows.

DS03 (frozen confirmation outputs):
- Healthy audit flights for engines 10–15: 17, 18, 36, 18, 35, 24.
- Healthy audit rows: 1,294,679 in total.
- Audit flight classes: 3, 3, 1, 3, 1, 2.
- Total file rows: 9,822,837. This is inferred exactly from the recorded byte size at 376 bytes/row, using the same 9,064-byte container overhead as DS02.
- DS03 onset/EOL cycles, abnormal-flight counts, and calibration-engine healthy-flight counts are established in Stage B.

**Label-support rules.** These are fixed now and applied in Stage B from the `A_*` arrays only.

| Rule | Content |
| --- | --- |
| LS-1 | `hs` ∈ {0, 1}, starts at 1, is monotone non-increasing per engine, and has at most one transition. Engines that violate this are excluded from S/D endpoints but kept in healthy endpoints. |
| LS-2 | `hs` is constant within every flight. If an engine violates this, $o_e$ is the first flight containing any `hs = 0` row, rows are still classed by their own `hs`, and the engine's delay is flagged. LS-2 is also a precondition of the healthy-only loaders (§6, Stage C), so a violation in any flight containing healthy rows halts Stage C. |
| LS-3 | Cycles within an engine are contiguous. If not, flight offsets $k$ count recorded flights. |
| LS-4 | S1, S3, and S4 need ≥ 1 post-onset flight. S2 needs ≥ 10 post-onset flights. D1–D3 need ≥ 1 healthy and ≥ 1 post-onset flight. Ineligible engines are listed and never imputed. |
| LS-5 | No engine is added to or removed from the frozen split. Abnormal rows of model-fit and calibration engines are never loaded. |

## 3. Calibration schemes (exact)

**Notation.**
- $m$ is a detector run: PCA; Isolation Forest seeds 0/1/2; LSTM seeds 0/1/2.
- $\alpha$ is the nominal target, one of {0.005, 0.01, 0.02}; 0.01 is primary.
- $\phi(i)$ is the frozen primary retrospective phase of row $i$ (90% within-flight altitude rule, `confirm_frozen_ds03.primary_phase`).
- $\mathcal{C}$ is the set of healthy rows of the calibration engines, and $\mathcal{C}_\phi$ its phase-$\phi$ subset.
- $Q^{\uparrow}_{q}$ is `np.quantile(·, q, method="higher")`.

**Scheme P (existing pooled).**
- Threshold: $\tau^{P}_{m,\alpha} = Q^{\uparrow}_{1-\alpha}\{s_m(i): i\in\mathcal{C}\}$.
- Alarm: $a^{P}(i)=\mathbb{1}[s_m(i) > \tau^{P}_{m,\alpha}]$.
- This is identical to the `"pooled"` values in `results/confirmation_ds03/calibration_lock.json` and to the pooled thresholds in the frozen DS02 outputs.

**Scheme C (phase-conditioned; primary comparator).**
- Threshold: $\tau^{C}_{m,\alpha,\phi} = Q^{\uparrow}_{1-\alpha}\{s_m(i): i\in\mathcal{C}_\phi\}$.
- Alarm: $a^{C}(i)=\mathbb{1}[s_m(i) > \tau^{C}_{m,\alpha,\phi(i)}]$.
- This is identical to the lock's `"climb"`/`"cruise"`/`"descent"` values for DS03 and to the calibration-phase thresholds in the frozen DS02 transfer matrix.
- Scheme C is the diagonal of the frozen cross-phase transfer design. Its DS03 thresholds were locked before official-test access, and no threshold is estimated from audit data.
- The primary phase rule uses each complete flight's altitude trace, including future samples. Scheme C is therefore *oracle-regime* conditioning: an upper bound on what phase conditioning can deliver with a perfect retrospective segmenter, not an online-implementable rule.

**Scheme C′ (causal regime; secondary post-confirmation sensitivity/feasibility arm, decision D-5).**

Within each flight, starting at its first sample $t_0$:

$$v_t = \frac{\mathrm{alt}_t - \mathrm{alt}_{t-w_t}}{w_t}, \qquad w_t=\min(60, t-t_0) \text{ samples}, \qquad v_{t_0}=0.$$

The regime is $\rho_t$ = ascending if $v_t>2.0$, descending if $v_t<-2.0$, and level otherwise.
- **Current and past information only.** The rule uses the current and past altitude of the same flight.
- **Constants not tuned.** The window (60 samples) and limit (2.0 altitude units s⁻¹) are inherited from the executed DS02 exploratory alternative phase rule (ledger M0036–M0037). They were fixed without any DS03 abnormal-state outcome, none of which has been computed.
- **Differences from the DS02 rule.** It is trailing rather than centred, and it has no altitude-fraction condition, because that condition needs the flight maximum.
- **Thresholds.** $\tau^{C'}_{m,\alpha,\rho}$ are the $Q^{\uparrow}_{1-\alpha}$ values of healthy calibration scores by regime, applied by regime.
- **Evaluation.** Endpoints are stratified by the primary retrospective phases for comparability, and additionally by regime.
- **Feasibility descriptor.** Row shares of $\rho$ against $\phi$ on healthy calibration and healthy audit rows.
- **Status.** C′ never replaces the retrospective primary analysis.

**Summaries.** PCA is a single run. Isolation Forest and LSTM family values are arithmetic seed means, which are descriptive. There are no seed-mean intervals (frozen convention).

## 4. Endpoints (exact)

Audit sets:
- $\mathcal{H}$ is the set of healthy rows of the audit engines.
- $\mathcal{A}$ is the set of abnormal rows of the audit engines.
- Subscripts restrict these to a phase or engine.

Rates are alarmed rows divided by eligible rows. $S$ ranges over {P, C, C′}. "pp" means percentage points.

### 4.1 Healthy phase-wise stability (H)

| ID | Definition |
| --- | --- |
| **H1 (primary)** | Phase-FPR spread $R^{S}=\max_\phi \mathrm{FPR}^{S}_\phi-\min_\phi \mathrm{FPR}^{S}_\phi$ over pooled audit engines, where $\mathrm{FPR}^{S}_\phi = \lvert\{i\in\mathcal{H}_\phi: a^{S}(i)=1\}\rvert/\lvert\mathcal{H}_\phi\rvert$. Paired reduction: $\Delta R = R^{P}-R^{S}$ (pp). A positive value means $S$ is more phase-stable than P. |
| H2 | Maximum phase calibration error $\mathrm{MPCE}^{S}=\max_\phi \lvert \mathrm{FPR}^{S}_\phi-\alpha\rvert$, with paired reduction $\Delta\mathrm{MPCE}=\mathrm{MPCE}^{P}-\mathrm{MPCE}^{S}$. |
| H3 | For C and C′: $\mathrm{FPR}^{S}_\phi$ for each of the three phases; overall $\mathrm{FPR}^{S}$; descent−climb and descent−cruise; and the share of healthy alarms falling in each phase, compared with that phase's share of healthy rows. The P values are the frozen values; they are reproduced in the gate and not re-reported as new. |
| H4 | Healthy flight burden, per phase and whole flight: the fraction of healthy audit flights with ≥ 1 alarm, and the mean number of contiguous alarm events per healthy flight. Definitions match `final_validation.flight_metrics` and `second_stage_audit.count_events`, applied to each scheme's alarm vector. Flight denominators include flights with no rows in a phase, as in the frozen code. Whole-flight events are counted on the concatenated vector. |

### 4.2 Engine-level heterogeneity (E)

| ID | Definition |
| --- | --- |
| E1 | Per audit engine $e$, for P, C, and C′: $\mathrm{FPR}^{S}_{e,\phi}$, $R^{S}_e$, and $\mathrm{MPCE}^{S}_e$. |
| E2 | Across-engine dispersion for each phase and scheme: range and sample standard deviation (ddof = 1) of $\mathrm{FPR}^{S}_{e,\phi}$ over audit engines; the worst cell $\max_{e,\phi}\mathrm{FPR}^{S}_{e,\phi}$; and the exceedance count $\#\{(e,\phi):\mathrm{FPR}^{S}_{e,\phi}>2\alpha\}$. |
| E3 | Sign counts $\#\{e: R^{S}_e<R^{P}_e\}$ and $\#\{e:\mathrm{MPCE}^{S}_e<\mathrm{MPCE}^{P}_e\}$ out of 6 (DS03) or 3 (DS02), per run, for S ∈ {C, C′}. |
| E4 (secondary) | Calibration-source sensitivity: H1–H3 and E2 recomputed with the thresholds of each scheme estimated from one calibration engine alone (DS03: {4} and {8}; DS02: {18} and {20}). |

### 4.3 Abnormal-state sensitivity (S), audit engines only

| ID | Definition |
| --- | --- |
| S1 | Row-level abnormal-state alarm rate $\mathrm{TPR}^{S}_\phi$ and overall $\mathrm{TPR}^{S}$, where TPR is alarmed abnormal audit rows divided by abnormal audit rows. Reported with $\Delta\mathrm{TPR}=\mathrm{TPR}^{S}-\mathrm{TPR}^{P}$ (pp) and the ratio $\mathrm{SR}=\mathrm{TPR}^{S}/\mathrm{TPR}^{P}$, both pooled and per engine. |
| S2 | Early-window rate: S1 restricted to post-onset flights with offset $k\in\{0,\dots,9\}$, i.e. the first 10 post-onset flights of each engine. Gives $\mathrm{SR}_{\mathrm{early}}$. |
| S3 | Rate by quartile of normalized abnormal life $u=k/(\mathrm{EOL}_e-o_e+1)$: [0, 0.25), [0.25, 0.5), [0.5, 0.75), [0.75, 1]. |
| S4 (secondary; point estimates only) | Threshold-free separability of abnormal versus healthy audit rows, using each arm's calibration p-value as the statistic (see below). |

S4 details:
- For each arm, $p^{S}(i)=\bigl(1+\#\{j\in\mathcal{R}^{S}(i): s(j)\ge s(i)\}\bigr)/\bigl(1+\lvert\mathcal{R}^{S}(i)\rvert\bigr)$.
- The reference set $\mathcal{R}^{S}(i)$ is $\mathcal{C}$ for P, $\mathcal{C}_{\phi(i)}$ for C, and $\mathcal{C}_{\rho(i)}$ for C′.
- The statistic is $-p^{S}$, so all arms share the same tie structure.
- Summary: normalized partial AUC over audit-row FPR ∈ [0, 0.02], i.e. the area divided by 0.02. Ties are handled by the trapezoidal ROC, which equals the expectation under random tie-breaking.
- It is computed for all abnormal rows and for the S2 window.

### 4.4 Flight-level decision rule and detection delay (D)

**Flight statistic.** $r^{S}(f)=\lvert f\rvert^{-1}\sum_{i\in f}a^{S}(i)$, the fraction of alarmed rows in flight $f$.

**Flight threshold (decision D-3).** $\kappa^{S}_{m,\alpha}=Q^{\uparrow}_{0.95}\{r^{S}(f): f \text{ a healthy flight of a calibration engine}\}$.
- It is a calibration-only empirical flight-alarm-fraction threshold, computed separately for each detector run $m$, arm $S$, and nominal target $\alpha$.
- It targets a nominal 5% healthy-flight false-flag rate.
- It uses the full-calibration $\tau^{S}$. The number of calibration flights and the order statistic used are recorded; with DS02's 32 calibration flights, this is the second largest value.

**Flagging.** A flight is flagged iff $r^{S}(f)>\kappa^{S}$. Every κ is written to `mitigation_lock.json` in Stage L, **before any abnormal sensor row is opened**.

**Reporting rule.** The realized healthy-flight false-flag rate (D2) is always reported alongside detection delay (D1).

| ID | Definition |
| --- | --- |
| D1 | Delay $D^{S}_e=\min\{k\ge 0:$ post-onset flight $o_e+k$ flagged$\}$, in flights. It is right-censored ("not detected by EOL") if no post-onset flight is flagged. Reported per engine; as the median over audit engines, with censored values ranking above all observed values; and as paired $\Delta D_e=D^{S}_e-D^{P}_e$ with counts of earlier, same, and later. Censoring conventions: both censored gives 0; only S censored gives +∞; only P censored gives −∞. Every median of delays or delay differences is the lower (inverted-CDF) median, so it is always an observed value and censored ±∞ values never average into an undefined value. |
| D2 | Healthy flight false-flag fraction $\mathrm{FFR}^{S}$: flagged healthy audit flights divided by healthy audit flights, pooled and per engine. |
| D3 (secondary) | Two-flight persistence: detection at the first $k\ge1$ where post-onset flights $k-1$ and $k$ are both flagged. The healthy counterpart is the number of consecutive flagged healthy-flight pairs per engine, and the fraction of audit engines with ≥ 1 such pair. |
| D4 | Number of engines censored under each scheme. |

### 4.5 Endpoint hierarchy

- **Primary:** H1 for C versus P on DS03 at α = 1%, over pooled audit engines, per run and with family summaries.
- **Key secondary (C versus P, DS03, α = 1%):** H2, E1–E3, S1, S2, D1, D2.
- **Secondary:**
  - every endpoint at α = 0.5% and 2%;
  - every endpoint on DS02;
  - H3, H4, E4, S3, S4, D3, D4;
  - all C′ results and the C′ feasibility descriptor.

No p-values are computed. There is no multiplicity adjustment; the hierarchy and the descriptive labelling take that role.

## 5. Uncertainty and interpretation

### 5.1 U1: healthy paired bootstrap (α = 1%, per run)

The plans reproduce the frozen procedure exactly: `rng = np.random.default_rng(20260925)`, then `final_validation.bootstrap_plans` on the healthy calibration metadata and then on the healthy audit metadata, in frozen row order, for 2,000 replicates.

In each replicate:
- $\tau^{P}_b$, $\tau^{C}_{\phi,b}$, and $\tau^{C'}_{\rho,b}$ are re-estimated with `weighted_higher_quantile(·, 0.99)` on the matching calibration view.
- Audit counts under all three arms are computed from the same plan, so the comparison is paired.

Recorded per replicate:
- For each arm: $\mathrm{FPR}_\phi$, overall FPR, the descent contrasts, $R$, and MPCE.
- $\Delta R$ and $\Delta\mathrm{MPCE}$ for C and C′.
- H4 any-alarm flight fractions per phase. Event counts are point estimates only.
- For the pooled arm, the frozen worst off-diagonal transfer FPR, used only for the self-check.

Intervals are percentile 95% intervals from `np.quantile` at its default method, as in the frozen code.

**Stage D self-check (halting).** The pooled-arm U1 summaries of the seven frozen metrics must equal `hierarchical_bootstrap_ci.csv` within 1e-12. The C-arm and C′-arm results are not written unless this passes.

### 5.2 U2: abnormal-state and delay bootstrap (α = 1%, per run)

A separate stream is used: `rng = np.random.default_rng(20260927)`.

**Plans.**
- Calibration: `bootstrap_plans` on healthy calibration flights.
- Audit: engines sampled with replacement; then, within each sampled engine, flights sampled with replacement separately within the healthy segment and within the post-onset segment.
- Only D-eligible engines are resampled. Flights of any other engine keep zero multiplicity.
- The S2 window counts only S2-eligible engines.

**In each replicate:**
- $\tau^{S}_b$ is re-estimated as in U1.
- $\kappa^{S}_b$ is the flight-multiplicity-weighted 0.95 "higher" quantile of calibration-flight $r^{S}$.
- $\mathrm{TPR}$ (S1, S2), $\mathrm{FFR}$ (D2), and the median delay (D1) are recomputed for every arm. For D1, each sampled engine keeps its original, time-ordered trajectory.
- Recorded quantities: $\Delta\mathrm{TPR}$, $\mathrm{SR}$, $\mathrm{SR}_{\mathrm{early}}$, $\Delta\mathrm{FFR}$, and the median $\Delta D$, for C and C′ against P.

S4 and D3 are point estimates only.

**Interval methods.** Intervals for delay quantities use `np.quantile(..., method="inverted_cdf")`, because delays are integer-valued and may be censored. All other U2 intervals use the default linear method.

With two calibration engines and three or six audit engines, all intervals are crude summaries for the observed engine sets, not population estimates. This is stated wherever they appear.

### 5.3 Interpretation rules (descriptive; fixed now)

**IR-H.** On a dataset at α = 1%, the text may say "phase-conditioned calibration reduced the healthy phase-FPR spread" only if ΔR > 0 for PCA *and* for both the Isolation Forest and LSTM seed means. Otherwise it says the spread was "not consistently reduced". Per-run intervals, E3 sign counts, and every run or engine with ΔR ≤ 0 are always shown.

**IR-S: interpretive guardrails (decision D-2).** These are pre-specified interpretive guardrails, *not* formal non-inferiority margins. The full continuous estimates and 95% intervals are reported whether or not the guardrails are met. For each detector family at α = 1% (PCA is a single run):

- **Family alarm-rate ratio.** The seed mean of $\mathrm{TPR}^{S}$ divided by the seed mean of $\mathrm{TPR}^{P}$, computed for all post-onset rows and for the S2 window.
- **Family delay change.** For each eligible audit engine, take the median of $\Delta D_{m,e}$ over the family's runs. The family value is the median of these over engines.
- **Guardrails met** iff both ratios are ≥ 0.90 **and** the family delay change is ≤ +1 flight.
- An engine censored under exactly one scheme is named explicitly.
- The words "non-inferior" and "no loss" are not used.

**IR-T.** The summary sentence for C against P is one of four pre-written templates. It is chosen by the IR-H outcome crossed with the combined IR-S outcome: "outside the guardrails" applies if any family fails, and those families are named. C′ uses the same templates, labelled as the causal-regime sensitivity/feasibility arm.

All templates begin: "In this post-confirmation, exploratory analysis of simulated N-CMAPSS [dataset] data with retrospective (oracle) phase labels, phase-conditioned calibration…"

| IR-H \ IR-S | Guardrails met | Outside guardrails |
| --- | --- | --- |
| Spread reduced | **T1:** "…reduced the healthy phase-FPR spread relative to pooled calibration at the 1% target, and abnormal-state alarm rate and detection delay stayed within the pre-specified interpretive guardrails; intervals were wide with [n] audit engines." | **T2:** "…reduced the healthy phase-FPR spread relative to pooled calibration at the 1% target, but abnormal-state alarm rate [and/or detection delay] fell outside the pre-specified interpretive guardrails for [families]." |
| Spread not consistently reduced | **T3:** "…did not consistently reduce the healthy phase-FPR spread at the 1% target; abnormal-state alarm rate and detection delay stayed within the pre-specified interpretive guardrails." | **T4:** "…did not consistently reduce the healthy phase-FPR spread at the 1% target, and abnormal-state alarm rate [and/or detection delay] fell outside the pre-specified interpretive guardrails for [families]." |

### 5.4 Frozen-confirmation firewall

| Rule | Content |
| --- | --- |
| F1 | No frozen file is modified. The baseline manifest verifies before and after each stage. |
| F2 | Frozen DS02 and DS03 numbers are cited only via their existing evidence IDs. Recomputed pooled-arm values appear only in the gate report and the paired comparisons, and never replace frozen values. |
| F3 | No new inferential summary is attached to the frozen pooled endpoints: no seed-mean intervals, no p-values, and no new contrasts for P alone. This matches the author's earlier decision not to reopen the frozen analysis for seed-mean intervals. Pooled-arm replicate values exist only as the paired comparator. |
| F4 | Mitigation results are never used to qualify the frozen verdict. Examples of forbidden readings: "artefact of pooled calibration", "phase dependence resolved", "confirmation moot". |
| F5 | DS03 is described as "the frozen confirmation subset, reused after confirmation for exploratory mitigation analysis". It is never described as held out for the mitigation. |
| F6 | IR-H mirrors the structure of the frozen directional rule but is descriptive. It is never called a confirmation or a reproduction. |

## 6. Execution stages, author stops, and integrity gates

**Order.**

1. Stage A.
2. Stage B for DS02 and DS03.
3. Stage C for DS02 and DS03.
4. **Stop: the author reviews the gate report.**
5. Stage L for both datasets.
6. Stage D for both datasets.
7. **Stop: explicit author approval for abnormal-state rows.**
8. Stage E for DS02, then Stage E for DS03.
9. Stage F.

**DS02 shakedown rule.** DS02 Stage E serves as the engineering shakedown for the abnormal-row code. Any code change after it that alters numbers requires an amendment (§13), and DS02 Stage E must be rerun under the amended code *before* DS03 Stage E.

| Stage | Data touched | Actions | Stop conditions |
| --- | --- | --- | --- |
| **A. Freeze** | None | Set this file to FROZEN v1.0. Write `configs/mssp_mitigation.yaml`, the frozen-value snapshot. Implement the code and data-free tests (§10) and a synthetic benchmark. Commit on `mssp-revision`, then record the commit hash and this file's SHA-256 in `docs/mssp/FREEZE_RECORD.md`. | Any test failure. |
| **B. Label structure** | `A_*` arrays (unit, cycle, Fc, hs) and variable-name vectors only. No `W`, no `X_s`, no scores. | Apply LS-1…LS-5. Write a per-engine table: flights, healthy and post-onset flights, $o_e$, EOL, Fc, rows by state, calibration healthy-flight counts, and eligibility. Cross-check DS02 against `results/cycle_phase_audit.csv`. Re-derive the DS03 split with the frozen ID-only rule `choose_units`. | G2 or G3 failure. |
| **C. Reproduction gate** | Healthy rows only. `W_*` and `X_s_*` are requested from HDF5 only as contiguous healthy row blocks, so no abnormal-row operating or sensor value is read. Phases and descriptors are computed per flight, which is equivalent to the frozen loaders under LS-2. | Run the CUDA check and verify input hashes. Refit the correction and Isolation Forest (frozen specification and seeds). Load the frozen LSTM final checkpoints. Re-run the frozen assembly code unchanged on the recomputed scores and compare it with the frozen files (G4). **DS02:** `audit_run`, `make_canonical`, `per_engine_table`, `boundary_audit`, `hierarchical_bootstrap`. **DS03:** `calibration_thresholds`, `row_metrics`, `transfer_with_locked_thresholds`, `flight_metrics`, `canonical_table`, `hierarchical_bootstrap`. Write the gate report and score fingerprints (SHA-256 of each run's calibration and healthy-audit score vectors). **No mitigation endpoint, κ, or lock is computed in this stage.** | G1, G2, G3, or G4 failure: halt and escalate. |
| **L. Calibration-only lock** (after author review of C) | Same as C | Compute every run × target's $\tau^{P}$, $\tau^{C}$, $\tau^{C'}$, $\kappa^{P}$, $\kappa^{C}$, and $\kappa^{C'}$ from healthy calibration rows and flights only. Verify that $\tau^{P}$ and $\tau^{C}$ equal the frozen thresholds. Write `mitigation_lock.json` with exclusive create and record its SHA-256. | G6 failure, or the thresholds differ from the frozen ones. |
| **D. Healthy endpoints** | Same as C | H1–H4, E1–E4, D2, the C′ feasibility descriptor, and U1 with the halting frozen self-check. | Self-check failure. |
| **E. Abnormal-state endpoints** (one-shot per dataset; explicit author approval) | Abnormal (`hs = 0`) rows of audit engines only | Requires `mitigation_lock.json`, hash-verified, and the flag `--authorize-abnormal-open`. Re-verify the score fingerprints and recompute the lock in-process; the recomputed lock must be identical. Create `abnormal_rows_opened.json` with exclusive create *before* reading those rows. Score them with the verified models and compute S1–S4, D1–D4, and U2. | The marker already exists (rerun only by amendment), or verification fails. |
| **F. Report** | None | Write `MITIGATION_REPORT.md` (IR-H, IR-S, IR-T) and `run_manifest.json`, and re-verify the baseline manifest (G5). | G5 failure invalidates the run. |

**Gates.**

| Gate | Check | Tolerance / action |
| --- | --- | --- |
| G1 | Environment | CUDA must be present; otherwise abort. Python and package versions are recorded against `requirements-lock.txt`; any mismatch is recorded and G4 decides. |
| G2 | Inputs | HDF5 MD5 over the raw file bytes must match the provenance records. Checkpoints and all frozen files must match `frozen_baseline.sha256`. |
| G3 | Label structure and loaders | LS-1…LS-5 hold. Engine sets equal the frozen configs. The healthy-block loader is equivalent to the frozen loaders: this is shown by a synthetic-HDF5 test and confirmed on real data by G4. |
| G4 | Reproduction | Every regenerated frozen table must match its frozen file cell by cell, with exact equality after round-trip parsing. The only exception is LSTM floating-point columns other than counts: a relative difference ≤ 1e-6 is accepted only if every count column (`n`, `false_alarms`, `any_false_alarm`, `false_alarm_events`, `rows`, `healthy_flights`) is exact. DS03 thresholds must equal `calibration_lock.json` under the same rule. The bootstrap tables must match within 1e-12 after sorting by detector, seed, and metric. Byte identity of the regenerated CSV text is also reported. |
| G5 | Post-run | The baseline manifest verifies. All writes are new files under the output root; no output file was overwritten. |
| G6 | Stage consistency | The score fingerprints recomputed in Stages L, D, and E equal the gate's fingerprints bit for bit. |

**If G4 fails**, execution halts and the gate report is sent to the author. The pre-agreed fallback needs explicit author approval: recomputed scores are used for **both** arms, so the comparison stays paired; the discrepancy is disclosed; and the frozen numbers remain canonical.

## 7. Leakage and information-exposure audit

| # | Channel | Status | Control / disclosure |
| --- | --- | --- | --- |
| L1 | Audit data in model fitting | None. The models are the frozen fits on model-fit engines' `hs = 1` rows. | G4 identity; static test; engine-set disjointness assertion. |
| L2 | Audit data in τ or κ | None. Both use calibration engines only. | Functions receive calibration arrays only; synthetic test. |
| L3 | `hs = 0` rows in fitting or calibration | None. `hs = 0` only defines evaluation rows and $o_e$. Stages B–D read no abnormal-row operating or sensor value at all. | Healthy-block reads; abnormal rows of non-audit engines are never loaded (LS-5). |
| L4 | Labels as detector inputs | None; the pipeline is unchanged. | The existing static guards plus a new guard for the new module. |
| L5 | Retrospective phases use future samples within a flight | Present and inherent to C. This is not health-label leakage but a deployability limit. | Reported as oracle-regime conditioning. C′ is the causal comparison. |
| L6 | Post-hoc choice of mitigation | Present. C was chosen after the DS02 and DS03 results were known, although its thresholds were pre-locked. | Labelled post-confirmation and exploratory; no confirmatory claim (C3, F6). |
| **L7** | **Healthy outcomes already observed** | **Present.** Every C-arm healthy row-level phase FPR (pooled and per engine; all runs, targets, and both datasets) is a diagonal cell (`calibration_phase == test_phase`) of the frozen transfer matrices and is in the RESS evidence ledger. The DS02 PCA 1% diagonal is displayed in RESS Fig. 3. H1–H3 and E1–E3 for C are therefore deterministic functions of outputs the authors can already see. | Declared unblinded and descriptive: a re-expression of frozen outputs, not a test. Stage C reproduces those cells exactly. **Drafting exposure:** reading the schemas displayed the first three data rows of each transfer CSV, which included two diagonal cells at the 0.5% target (DS03 PCA engine 10 climb→climb; DS02 PCA engine 11 climb→climb). No diagonal cells were aggregated or summarized. |
| L8 | Outcomes never observed | Not yet computed: every C′ result; H4 under C; all intervals and paired contrasts; κ; and all `hs = 0` endpoints (S, D). No `hs = 0` row has ever been scored in any analysis: the pilot, second-stage, Phase 3, final-validation, and confirmation code all filter to `hs = 1` before scoring. | Freeze-before-open sequencing; κ locked in Stage L; the one-shot `abnormal_rows_opened.json` marker; author stops. |
| L9 | Tuning after seeing results | Guarded. | All constants are fixed here: targets, the 5% flight false-flag target, the 10-flight early window, quartiles, persistence 2, the guardrails, the C′ constants, and the bootstrap seeds. DS02-first execution grants no latitude; changes follow §13 and apply to both datasets. |
| L10 | Reproduction drift | Possible (environment or GPU determinism). | G4 halts. Frozen values stay canonical (F2). |
| L11 | Reinterpretation of the frozen confirmation | Guarded. | F1–F6. |
| L12 | Label semantics | `hs = 1` includes normal degradation; the `hs = 0` onset is a simulator label. | Endpoint names (§1). Early-window results are read as sensitivity near a labelled transition, not as field fault detection. |
| L13 | In-sample κ | Mild optimism: τ and κ use the same calibration flights. This is symmetric across arms. | D2 measures actual false-flag behaviour on audit engines; stated as a limitation. |
| L14 | Same-engine evaluation | Avoided. | Abnormal rows of fit and calibration engines are unused. |
| L15 | File-system contamination | Guarded. | The runner refuses frozen or source paths and never overwrites. Before/after manifest check (G5). |
| L16 | Future confirmation capacity | Unaffected. The local official archive (`N-CMAPSS/nasa_dataset2_official.zip`) contains the nested `data_set.zip`. `src/fetch_confirmation_ds03.py` extracts only the DS03 member, and only DS02 and DS03 exist locally in extracted form. | Out of scope. A later, separately pre-registered test of healthy-FPR stabilization on an unopened subset remains possible. Fault modes differ across subsets, so the S and D endpoints would not transfer. |

## 8. Required existing files and environment

**Interpreter.** `/home/mei/global-python/bin/python`: Python 3.12.3, torch 2.14.0+cu130, CUDA 13.0 available. The torch, scikit-learn, NumPy, pandas, SciPy, h5py, and Matplotlib versions equal `requirements-lock.txt` (observed 2026-09-27).

**Local, git-ignored files.** These must exist and verify; none is modified.

| File | Use | Integrity |
| --- | --- | --- |
| `N-CMAPSS/N-CMAPSS_DS02-006.h5` | Stages B, C, L, D, E | MD5 `61056251b36290e11371e017eed70eac`, 2,450,472,504 B (`N-CMAPSS/official_verification.json`) |
| `N-CMAPSS/N-CMAPSS_DS03-012.h5` | Stages B, C, L, D, E | MD5 `a301cd2cfa9b7da6e6ec12051ded9afe`, 3,693,395,776 B (`results/confirmation_ds03/source_provenance.json`) |
| `results/confirmation_ds03/checkpoints/lstm_seed_{0,1,2}_final.pt` | DS03 LSTM inference (no training) | SHA-256 `c7c2e64c…`, `a604c7c2…`, `f5ea3178…` |
| `results/final_validation/checkpoints/lstm_seed_{0,1,2}_final.pt` | DS02 LSTM inference | SHA-256 `b8dbb11d…`, `978a7ce2…`, `2a366013…` |

The DS02 `.pt` checkpoints were written at 10:58–10:59 on 2026-09-25, just before the canonical CSVs (11:01). The neighbouring `.keras` files belong to an earlier run and are not used.

**Tracked, frozen, read-only files.** These are the gate references and cited sources.

| File(s) | Use |
| --- | --- |
| `results/confirmation_ds03/calibration_lock.json` (`ebdf2f50…`) | G4 reference for τ^P and τ^C (DS03) |
| `results/confirmation_ds03/{row_false_alarm_rates,threshold_transfer_matrix,flight_alarm_detail,flight_alarm_summary,canonical_results,hierarchical_bootstrap_ci}.csv` | G4 references and frozen P-arm values; diagonal source for L7 |
| `results/confirmation_ds03/{pre_audit_plan,run_config,official_test_opened,source_provenance}.json` | Engine sets and provenance. The one-shot marker is left untouched. |
| `results/final_validation/{executed_row_false_alarm_rates,executed_threshold_transfer_matrix,executed_score_only_phase_prediction,executed_flight_alarm_detail,canonical_results,per_engine_phase_fpr,lstm_boundary_audit,hierarchical_bootstrap_ci}.csv` | DS02 G4 references and frozen values |
| `results/final_validation/frozen_protocol.md` (`b472591d…`) | Frozen rules; quoted, never amended |
| `results/cycle_phase_audit.csv` | DS02 label-structure cross-check (Stage B) |
| `configs/ds02_discovery.yaml`, `configs/ds03_confirmation.yaml` | Engine sets |
| `paper/evidence_ledger.csv` (`b8f49c70…`), `paper/manuscript_core_results.csv` (`cfd2c5c4…`) | Frozen evidence IDs cited by the MSSP manuscript |
| `docs/ENVIRONMENT.md`, `requirements-lock.txt` | G1 |
| `docs/mssp/frozen_baseline.sha256` | Baseline manifest: 186 entries, verified |

**Frozen code imported unchanged.** Importing these modules has no side effects beyond path constants.

| Module (SHA-256 prefix) | Functions reused |
| --- | --- |
| `src/final_validation.py` (`e1f7525b…`) | `configure_cuda_runtime`, `build_torch_lstm`, `score_lstm_with_positions`, `audit_run`, `make_canonical`, `per_engine_table`, `boundary_audit`, `bootstrap_plans`, `weighted_higher_quantile`, `hierarchical_bootstrap`, `row_metrics`, `flight_metrics`, constants |
| `src/confirm_frozen_ds03.py` (`7be27a45…`) | `primary_phase`, `choose_units`, `calibration_thresholds`, `transfer_with_locked_thresholds`, `canonical_table`, `load_primary_split` (equivalence test only) |
| `src/phase3_dynamic.py` (`fa09c4c3…`) | `ResidualPCADetector`, `causal_descriptors` |
| `src/second_stage_audit.py` (`3e3aee33…`) | `phase_labels`, `load_split` (equivalence test only), `SENSORS`, `W_NAMES`, `PHASES`, `count_events` |

`causal_descriptors`, `primary_phase`, and `phase_labels` each reset at flight boundaries. Because `hs` is constant within flights (verified for DS02; checked for DS03 by LS-2), the phases, descriptors, and scores of healthy rows are identical whether or not abnormal flights are loaded. This is verified by the synthetic test and by G4.

## 9. Expected computational cost

**Basis.** File modification times:
- The frozen one-shot DS03 run took ≈ 10 min wall-clock (`pre_audit_plan.json` 11:40 → report 11:50 on 2026-09-25), including LSTM epoch selection and refits for three seeds, all scoring, and the 2,000-replicate bootstrap.
- The DS02 bootstrap took ≈ 1.5 min (11:01:34 → 11:03:07).

The mitigation run needs **no training**.

**Data volumes.**
- DS02: 6,517,190 rows in total, of which 820,630 are abnormal audit rows (exact).
- DS03: 9,822,837 rows in total. Abnormal audit rows are estimated at ≈ 2.2–2.7 M, scaling from DS02's abnormal-to-healthy audit ratio of 1.89; the exact count comes from Stage B.

| Stage | DS02 | DS03 | Resources |
| --- | --- | --- | --- |
| B label structure | < 1 min (~0.21 GB) | < 1 min (~0.31 GB) | CPU; < 2 GB RAM |
| C reproduction gate | ~8–15 min: correction refit, 3 Isolation Forest refits and scoring (DS02 also scores training rows, as the frozen `audit_run` requires), LSTM inference < 1 min, frozen bootstrap replay | ~10–20 min | Peak RAM ≈ 6–12 GB; GPU < 2 GB VRAM, busy < 2 min |
| L lock | ~5–10 min, mostly the rescoring precondition | ~8–15 min | as C |
| D healthy endpoints + U1 | ~8–15 min | ~10–20 min | CPU |
| E abnormal endpoints + U2 | ~10–20 min (820,630 rows × 7 runs; Isolation Forest scoring dominates) | ~15–35 min | CPU; GPU < 2 min |
| F report | < 5 min | < 5 min | — |
| **Total** | **≈ 40–70 min** | **≈ 50–110 min** | **≈ 1.5–3 h for both. No training or hyperparameter search.** |

U1 and U2 use vectorized counting: global score ranks plus a single `searchsorted` over per-(flight, phase, regime) cells per threshold.

**Stage A synthetic benchmark (no data).** The benchmark (`scripts/run_mssp_mitigation.py --benchmark`) used DS03-like shapes: 540,000 calibration rows, 3,780,000 audit rows, and 420 audit flights. Timing 20 replicates and extrapolating to 2,000 replicates × 7 runs gave U1 ≈ 3.4 min and U2 ≈ 7.7 min, well under the 30-minute limit.

**Disk.** Tracked CSV outputs are ≈ 20–100 MB per dataset. No row-level score cache is written; stages recompute scores and verify them against the gate fingerprints (G6).

## 10. Code and outputs

| New file | Purpose |
| --- | --- |
| `configs/mssp_mitigation.yaml` | Frozen-value snapshot of every constant above. A test compares it with the module constants. |
| `src/mssp_mitigation.py` | Contains the stage functions B, C, L, D, E, F. It includes the healthy- and abnormal-block loaders (reusing the frozen phase and descriptor code), the causal regime, scheme thresholds, endpoints, the U1 and U2 bootstraps, the gates, and the markers. It imports the frozen modules and never edits them. |
| `scripts/run_mssp_mitigation.py` | Guarded wrapper. It is a dry run by default. Options: `--dataset`, `--stage` (`gate` = B,C), `--execute`, `--authorize-abnormal-open` (Stage E), `--output-root`, `--benchmark` (synthetic only). It refuses frozen or source paths, overwrites, a failed manifest, or a missing lock. |
| `tests/test_mssp_mitigation.py` | Data-free tests: manifest; write guard; YAML/constant agreement; healthy-block loaders against the frozen loaders on synthetic HDF5; causal-regime causality; C thresholds and alarms against the frozen functions; the vectorized cell counter against brute force; the U1 pooled arm against the frozen `bootstrap_one_model`; delay, censoring, and persistence; partial AUC; lock construction; Stage E marker ordering (AST); labels not used as detector inputs. |
| `docs/mssp/FREEZE_RECORD.md` | Freeze commit hash, this file's SHA-256, and test/benchmark results. |

**Outputs.** Everything goes under `results/mssp_mitigation/<ds02|ds03>/stage_<b|c|l|d|e|f>/`. Every file is written by exclusive creation.

`docs/mssp/AUTHORITATIVE_RESULTS_MSSP.md` will later list these as the only approved mitigation sources. The RESS `docs/AUTHORITATIVE_RESULTS.md` is left unchanged.

## 11. Manuscript integration plan (MSSP)

### 11.1 Package separation and evidence

**New package directory `paper/mssp/`.** It holds the manuscript Markdown, `main.tex`, figures and tables with provenance sidecars, and the builders. `paper/ress/`, `paper/submission/`, and the RESS manuscript files are not edited, so the existing RESS tests keep passing unchanged.

**New ledger `paper/mssp/evidence_ledger_mssp.csv`.** It is built only from `results/mssp_mitigation/**`.
- IDs are `PC000001…`, so they cannot collide with the frozen `E…` or `M…` IDs.
- Statuses are `post-confirmation exploratory (DS03)` and `exploratory (DS02 discovery)`.
- Frozen numbers are referenced by their unchanged E-IDs; the frozen ledger is not rebuilt.

**`paper/mssp/manuscript_core_results_mssp.csv`.** It contains the frozen core rows copied by E-ID and verified equal, plus the new PC rows.

**`tests/test_mssp_package.py`** checks that:
- every frozen number in the MSSP text equals `paper/manuscript_core_results.csv`;
- every mitigation number resolves to a PC ID;
- every paragraph that reports mitigation results contains "post-confirmation";
- none of these phrases appears: "confirmed mitigation", "eliminates phase dependence", "deployment-ready", "non-inferior", "no loss of sensitivity";
- the RESS baseline manifest verifies.

### 11.2 Reframing: signal processing under nonstationary operating conditions

**Title candidates**, for the author to choose from:
1. *Regime-dependent false-alarm rates of residual-based health monitoring under nonstationary full-flight operation: discovery, frozen confirmation, and post-confirmation evaluation of phase-conditioned calibration.*
2. *Pooled versus regime-conditioned threshold calibration for turbofan health monitoring under nonstationary operating conditions.*
3. *Constant false-alarm rate under operating-regime switching? Auditing threshold calibration of residual-based engine monitoring on N-CMAPSS.*

**Keywords:** condition monitoring; nonstationary operating conditions; operating-condition normalization; false-alarm rate; threshold calibration; detection delay; turbofan engine; N-CMAPSS.

| Current section | MSSP version |
| --- | --- |
| I Introduction | Lead with the signal-processing problem: detection statistics under time-varying operating conditions; residual generation after compensating for operating and environmental variability; and marginal versus regime-conditional false-alarm control (the CFAR analogy). Keep RQ1–RQ3 verbatim as the frozen questions and add RQ4 as post-confirmation. Contributions add (i) the mixture decomposition as a signal-model statement and (ii) the pooled-versus-conditioned trade-off evaluation, including the causal-regime feasibility arm. |
| II Related work | Keep refs [1]–[12]. Add short subsections on operating/environmental variability compensation in condition monitoring and SHM; on threshold setting (CFAR, group-conditional calibration); and on the detection-delay versus false-alarm trade-off (sequential detection). |
| III Methods | Re-express the frozen chain with equations ($x_t$ → residual $r_t$ → statistic $s_t$ → decision $a_t$) without changing any content. Add §III.G "Post-confirmation mitigation analysis": §§3–6 of this protocol, condensed, including the oracle-regime caveat, the C′ definition, and the reproduction gate. |
| IV Results | Sections A–G keep their numbers unchanged and may be condensed. New section H: H.1 healthy stability; H.2 engine heterogeneity; H.3 abnormal-state sensitivity; H.4 delay with healthy-flight false flags; H.5 causal-regime arm; H.6 DS02 replicate. |
| V Discussion | V.A–B unchanged. New V.C: what conditional calibration buys and costs; the CFAR reading; stabilization is not reduction; online feasibility from C′. Revise V.D implications. Revise V.F limitations to add post-confirmation status, oracle phases, simulated onset labels, in-sample κ, normal degradation within `hs = 1`, and 2 calibration versus 3/6 audit engines. |
| VI Conclusion | Answer RQ1–RQ3 exactly as frozen, then RQ4 with the IR-T template. |

**Sentences that must change in the MSSP text; the RESS text is untouched.** Each is scoped to "the frozen discovery–confirmation analysis" and given its post-confirmation counterpart; the frozen-scope statement is never deleted.

| Location | Sentence | Change |
| --- | --- | --- |
| Intro ¶1 | "…it does not evaluate fault-detection sensitivity or operational response." | Scope and add counterpart. |
| Intro ¶2 | "…health-state annotations are used only to select healthy samples…" | Add that, in the post-confirmation analysis, they also define abnormal-state evaluation rows and onset times; they are never detector inputs. |
| Intro ¶6 | "The study consequently makes no claim about fault sensitivity…" | Scope and add counterpart. |
| Methods III.C | "…the reported false-alarm endpoints do not measure detection of faulty-state observations." | Scope and add counterpart. |
| Discussion V.C | "Consider context-specific calibration only after checking that it does not degrade fault sensitivity… not evidence that an alternative threshold policy is superior." | Keep the second clause. |
| Discussion V.E | "The analysis does not estimate fault recall, detection delay…" | Scope and add counterpart. |
| Conclusion | "It does not assess fault recall or detection delay…", and "Future work … without compromising fault sensitivity." | Scope and add counterpart. |

**Figures and tables.**
- Figs 2–4 and Tables II–III are reused with unchanged data.
- Fig. 1 is regenerated as a new file with a visually separated "post-confirmation" block.
- New Fig. 5: paired phase FPR under P, C, and C′ per detector family, with DS03 and DS02 panels.
- New Fig. 6: engine × phase FPR under each arm, with the α line.
- New Fig. 7: flight alarm fraction versus flights since onset for each audit engine (with κ), or delay versus healthy false-flag fraction.
- New Table IV: mitigation summary at α = 1% (DS03).
- The supplement keeps S1–S9 unchanged and adds S10 onward: all targets, per-engine results, intervals, the Stage B label table, and the reproduction-gate report.

**Literature candidates.** These are unverified and must pass the `paper/reference_audit.md` process before being cited:
- Sohn (2007), environmental/operational variability in SHM, *Phil. Trans. R. Soc. A*.
- Worden, Manson and Fieller (2000), outlier analysis, *J. Sound Vib.*
- Figueiredo et al. (2011), *Struct. Health Monit.*
- Cross, Worden and Chen (2011), cointegration, *Proc. R. Soc. A*.
- Rohling (1983), CFAR, *IEEE Trans. Aerosp. Electron. Syst.*
- Basseville and Nikiforov (1993), *Detection of Abrupt Changes*.
- Page (1954); Lorden (1971).
- Vovk, Gammerman and Shafer (2005), Mondrian calibration.
- Recent MSSP work on operating-condition normalization and threshold setting, to be found by a documented search.

### 11.3 Submission logistics

- **RESS status.** The author reported a scope-based RESS desk rejection on 2026-09-27, so the exclusive-consideration caution is resolved. The submitted RESS state stays preserved: tag `ress-submission-2026-09-25` → `1f59e9e`, plus the baseline manifest. The untracked `paper/ress/cover_letter_final.txt` is outside version control and is not part of the tag.
- Check the MSSP Guide for Authors (highlights, abstract, graphical abstract, data statement) when the package is built.
- Keep `v1.0.0` and `ress-submission-2026-09-25` as the RESS code references. Any later MSSP release is a separate, author-approved decision; no GitHub Release is created as part of this protocol.
- Reframing text (Introduction, Related Work, Methods formalization) does not depend on results and may proceed. Results text waits for Stage F.

## 12. Decision record (author approval, 2026-09-27)

| ID | Decision | Status |
| --- | --- | --- |
| D-1 | Primary healthy endpoint is H1 (spread). | Recommended default adopted with the approval of the protocol direction. |
| D-2 | Abnormal-state alarm-rate ratio ≥ 0.90 and median delay increase ≤ +1 flight serve as pre-specified interpretive guardrails only, not formal non-inferiority margins. The full continuous estimates and uncertainty are reported regardless. | **Author decision.** |
| D-3 | A calibration-only empirical flight-alarm-fraction threshold, separate for each detector and calibration arm (and target), targeting a nominal 5% healthy-flight false-flag rate. It is locked before any abnormal sensor rows are opened, and the realized healthy-flight false-flag rate is always reported alongside detection delay. | **Author decision.** |
| D-4 | The early window is the first 10 post-onset flights. | Default adopted. |
| D-5 | Include the causal online-implementable regime arm as a secondary post-confirmation sensitivity/feasibility analysis. It uses only current and past information, is specified without DS03 abnormal outcomes, and does not replace the retrospective primary analysis. | **Author decision.** |
| D-6 | Include S4 as point estimates only. The statistic was corrected before the freeze to calibration p-values for every arm (see "Changes from v0.1"). | Default adopted. |
| D-7 | No seed-mean intervals (frozen convention; F3). | Default adopted. |
| D-8 | Execute gate first (B, C) and stop for review. L and D follow after review. E follows only on explicit approval. DS02 E runs before DS03 E. | **Author decision.** |
| D-9 | Annotated tag `ress-submission-2026-09-25` at the RESS-submitted commit `1f59e9e`. No GitHub Release. | **Author decision.** `1f59e9e` was identified from the evidence below. |
| D-10 | RESS status. | Resolved: scope-based desk rejection, reported by the author. |

Evidence for D-9:
- All commits are dated 2026-09-25.
- The final RESS PDF and `paper/ress/main.tex` last changed in `faf8b42` (20:51 AEST) and are identical at `1f59e9e`.
- `1f59e9e` (21:11) added the author/ORCID submission metadata.
- The final cover letter was downloaded at 22:20, and nothing was committed afterwards.

## 13. Amendments and deviations

Every change after the freeze is logged in `docs/mssp/AMENDMENTS.md` with:
- its ID and date;
- the exact change;
- the reason;
- whether it was made before or after any `hs = 0` row was scored;
- the affected outputs.

Affected stages are rerun into a new output root; no file is ever overwritten. Amendments made after Stage E are reported in the manuscript as post hoc. An amendment can never modify frozen files, the engine split, detector specifications, or the nominal targets.

## Changes from v0.1 (made before freeze)

1. **Decisions.** D-2, D-3, D-5, D-8, D-9, and D-10 were recorded, and C′ was promoted to an included secondary arm.
2. **S4 statistic.** It was corrected to calibration p-values for every arm. The raw score is not tie-equivalent to the pooled p-value, so comparing raw P against the C p-value would have mixed tie structures.
3. **Stage B scope.** Stage B was restricted to the `A_*` arrays.
4. **Stage C scope.** Stage C was restricted to healthy row blocks and to reproduction only. The κ lock moved to the new Stage L, after author review of the gate.
5. **U1 simplification.** U1 records H4 intervals for the any-alarm fraction only.
6. **No score cache.** The row-level score cache was dropped in favour of bit-level score fingerprints (G6).
7. **Guardrail definitions.** Family-level guardrail quantities (seed-mean alarm-rate ratio; median-of-medians delay change) were defined exactly.
8. **Cost estimates.** Compute estimates were updated for the added Stage L and the rescoring preconditions.
9. **Delay conventions.** Lower (inverted-CDF) medians and inverted-CDF intervals are used for delay quantities.
10. **U2 eligibility.** U2 resamples D-eligible engines only.
11. **Benchmark.** The synthetic benchmark result was recorded.
