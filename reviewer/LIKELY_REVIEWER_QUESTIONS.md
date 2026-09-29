# Likely reviewer questions — ncmapss-phase-entanglement (MSSP extended manuscript)

**Severity.** FATAL means it could sink the paper if unanswered; MAJOR means a revision is likely; MODERATE means it needs a
clear answer; MINOR means a text fix.

**Compute.** NONE, CHEAP_CPU (minutes, committed CSVs), MODERATE_CPU (hours, CPU), GPU (needs the locked models plus raw data
on a CUDA GPU) or EXPENSIVE (retraining or new data).

**"Now?"** says whether to act before any review ("now") or only if a reviewer asks ("if asked"). The default for this project
is "if asked": the manuscript is frozen and every change must pass `verify_numbers.py`.

Claim IDs (C…) refer to `CLAIMS_INDEX.md` and issue IDs (I-…) to `ISSUE_BANK.md`.

## Novelty and positioning

| ID | Sev. | Question | Why a reviewer asks | Existing evidence | Files to inspect | Sufficient? | New experiment? | Compute | Now? |
|---|---|---|---|---|---|---|---|---|---|
| Q01 | MAJOR | What is new beyond applying known detectors and known conditional thresholds to one benchmark? | Editor persona: "case study"; desk-rejection risk | §1 contributions 1–4; §2.3 last paragraph (no priority claim); `paper/mssp_extended/NOVELTY_POSITIONING.md`; `docs/extension/PRIOR_ART_EXTENSION.md` | `NOVELTY_POSITIONING.md`, `manuscript_mssp_draft.md` §1–2 | Partly. The novelty is the audit design (engine-disjoint, frozen, per-unit endpoint), not a method | No | NONE | If asked |
| Q02 | MAJOR | How does this differ from Chen et al. [N38], who condition a CVAE on operating conditions? | Closest prior art; the CVAE baseline is "inspired by" it | §2.2, §5.4; `NOVELTY_POSITIONING.md` row N38 (full text checked, 9 quotes) | `paper/mssp_extended/NOVELTY_POSITIONING.md`, `literature_evidence/` | Yes for positioning. No per-engine or early-cycle training was tested | Only if asked to replicate [N38] training (I-08) | GPU | If asked |
| Q03 | MODERATE | Isn't "a threshold controls only the exposure-weighted rate" textbook (mixture identity)? | Eq. in §1 is elementary | §1 cites [N7]; the contribution is empirical magnitude, not the identity | §1 | Yes | No | NONE | If asked |
| Q04 | MINOR | Why MSSP rather than a PHM or reliability venue, given the earlier RESS desk-rejection on scope? | Venue fit | Cover letter on branch `mssp-extended` (line 26) | `git show mssp-extended:paper/mssp_extended/cover_letter/cover_letter.txt` | Yes | No | NONE | If asked |

## Research question, design, protocol

| ID | Sev. | Question | Why | Existing evidence | Files | Sufficient? | New exp.? | Compute | Now? |
|---|---|---|---|---|---|---|---|---|---|
| Q05 | MAJOR | Is the negative headline guaranteed by construction (strict every-engine or worst-engine rules, few flights)? | All four internal reviewers raised it | Post hoc references §4.9 (C033, C026); focused validation §4.8 (C030) | `evidence/post_hoc_checks.json`, `results/extension/focused_validation/summary/engine_summary.csv`, `docs/extension/EXTENSION_HOSTILE_REVIEW.md` §2–4 | Mostly. The row-level excess is real in aggregate; the flight-level worst-engine excess is mostly within noise, and the manuscript says so | No | NONE | If asked |
| Q06 | MODERATE | Was the protocol really frozen before outcomes? How can a reader verify it without your private history? | Internal freeze only; public snapshot commit IDs are unresolvable | `docs/extension/FREEZE_RECORD.md`; `OUTCOME_ACCESS_LOG.md`; lock hashes; local branch `mssp-extended` resolves every cited commit | `docs/extension/FREEZE_RECORD.md`, `docs/extension/OUTCOME_ACCESS_LOG.md`, `git log mssp-extended` | Partly. Timestamps are self-attested. An external archive of the private history (Zenodo) would help | No | NONE | Now: consider depositing the private history or a signed bundle (I-19) |
| Q07 | MODERATE | Amendments 1–3 were made after the freeze. Did any change a decision? | Standard preregistration scrutiny | `AMENDMENTS.md`: each amendment preceded every new outcome; Amendment 1 only closes classification gaps | `docs/extension/AMENDMENTS.md` | Yes | No | NONE | If asked |
| Q08 | MAJOR | Five RQs, seven hypotheses, five stories and S1–S5: isn't the paper overloaded? | Editor and PHM personas | Table 4 caption defines the codes | `manuscript_mssp_draft.md` §3.9, Table 4 | Partly; a restructuring question | No | NONE | If asked (text) |
| Q09 | MODERATE | Why are DS02/DS03 excluded from decisions if the CVAE was run on them? | Mixed roles | Protocol §2 "Historical reference subsets"; §3.1 | `GENERALIZATION_PROTOCOL.md` §2 | Yes | No | NONE | If asked |
| Q10 | MODERATE | The post hoc focused validation re-read test data after all outcomes. Doesn't that undermine the one-shot design? | Garden of forking paths | §3.10: separate frozen plan (`d85aa10`), healthy rows only, changes no decision; access log | `docs/extension/FOCUSED_VALIDATION_PLAN.md`, `FOCUSED_VALIDATION_REPORT.md`, `OUTCOME_ACCESS_LOG.md` | Yes, if presented as post hoc (it is) | No | NONE | If asked |

## Dataset and sample size

| ID | Sev. | Question | Why | Existing evidence | Files | Sufficient? | New exp.? | Compute | Now? |
|---|---|---|---|---|---|---|---|---|---|
| Q11 | FATAL→MAJOR | The evidence is simulated N-CMAPSS only. Why should MSSP readers believe it transfers to real fleets? | External validity | §1 Scope, §5.5; no real data in the repository | `manuscript_mssp_draft.md` §1, §5.5 | No new evidence possible within the repository. The defence is scope limitation | Real fleet data (not available) | EXPENSIVE / not feasible | If asked: rebut by scope (I-06) |
| Q12 | MAJOR | Five families (effectively five units) and 30 engines: how can cross-dataset intervals mean anything? | Small N | §3.9 "crude … descriptive"; no p-values | `summary/uext2_cross_dataset.csv` | Yes as stated (descriptive only) | No | NONE | If asked |
| Q13 | MODERATE | Why is DS08d excluded? Could a truncated file be repaired or re-downloaded? | Selection bias | §3.1; selection lock C1 (32 bytes short) | `docs/extension/subset_metadata_audit.json`, `archive_extraction_record.json` | Partly. It is not documented whether a re-download was attempted | Possibly re-download plus a protocol amendment (not planned) | MODERATE_CPU + GPU | If asked |
| Q14 | MODERATE | Families F3 share identical flights, and some engines recur across subsets (e.g. DS08a test 14 ≡ DS01 dev 2). Is anything double-counted? | Dependence | Protocol §2 lists the identities; families are the top unit | `GENERALIZATION_PROTOCOL.md` §2; `docs/extension/profile_sharing_*.csv` | Partly. The manuscript says "several engines recur" but does not list them | No | NONE | If asked: add the list to the supplement |
| Q15 | MODERATE | Only 14–36 healthy flights per engine. What is the power to detect a per-engine calibration error of 0.5 pp? | Power | C033 (SE median 0.15 pp); null shares 31/30/49% | `evidence/post_hoc_checks.json` | Partly; a formal power curve is absent | A cheap binomial or cluster simulation | CHEAP_CPU | If asked |

## Statistics and uncertainty

| ID | Sev. | Question | Why | Existing evidence | Files | Sufficient? | New exp.? | Compute | Now? |
|---|---|---|---|---|---|---|---|---|---|
| Q16 | MAJOR | Why no hypothesis tests? Count rules on point estimates ignore uncertainty | Statistical reviewer | §3.9 design choice; U-EXT1/U-EXT2 intervals reported | `GENERALIZATION_PROTOCOL.md` §11–13 | Defensible as designed; will need a clear rationale | No | NONE | If asked |
| Q17 | MAJOR | The per-subset bootstrap drops whole calibration classes in 78% of replicates. Aren't the intervals invalid? | Design mismatch | §4.8 class-preserving rerun: 11–15% of width, no inference change (C031) | `focused_validation/summary/bootstrap_width_comparison.csv`, `uext2_original_vs_class_preserving.csv` | Yes | No | NONE | If asked |
| Q18 | MAJOR | H1 is exactly 3/5 and H4 has F1/F2 at exactly 7/10. Would the verdicts flip at 0.5% or 2%, or with a different material line? | Knife-edge | Table S10 (targets); §5.5 | Supplement Table S10; `*/audit/transport_summary.csv` | Partly: a target sensitivity exists, but the verdict at other targets is not stated | Re-evaluate the rules at 0.5/2% from committed CSVs (post hoc) | CHEAP_CPU | If asked (I-03) |
| Q19 | MODERATE | Seeds are near-replicates; why count them as votes? | Counting convention | Protocol §13; seed means used for H1 | `src/ext_summary.py` | Partly | Sensitivity with seed means only | CHEAP_CPU | If asked |
| Q20 | MODERATE | How is the cross-fitted self-calibration reference defined, and why does it understate noise? | Novel reference | §3.10 explains fold cancellation | `src/ext_focused_validation.py:crossfit_draws`; plan | Yes | No | NONE | If asked |
| Q21 | MINOR | "27 of 30": for which arm? | Abstract ambiguity | §4.8: C = 27, P = 29, Q = 28 | `focused_validation/summary/engine_summary.csv` | Yes | No | NONE | At proof stage (I-20) |

## Baselines, detectors, calibration arms

| ID | Sev. | Question | Why | Existing evidence | Files | Sufficient? | New exp.? | Compute | Now? |
|---|---|---|---|---|---|---|---|---|---|
| Q22 | MAJOR | C uses complete-flight phases (non-causal). Why not a causal, past-only regime? | Oracle arm | §3.5; the earlier C′ (past-only) arm was reported in the pre-extension study (protocol §5) | `docs/mssp/post_confirmation_mitigation_protocol.md`; `paper/mssp/` | Partly. The extension deliberately dropped C′ | Re-score with C′ on the new cohort | GPU (re-scoring) | If asked (I-07) |
| Q23 | MAJOR | Q is an unregularized quadratic quantile regression; isn't its failure trivially extrapolation? | Strawman concern | §3.5 "adversarial control, not a proposed method" | Protocol §5 | Partly | A regularized or bounded Q variant | GPU re-scoring + CPU fits (~1 h per subset) | If asked (I-07) |
| Q24 | MAJOR | The obvious practitioner baseline, per-unit recalibration, is missing; k = 5 only | Alarm-system persona | §4.8 local recalibration k = 5 (C032) | `focused_validation/summary/local_engine_summary.csv` | Partly | k = 3, 10, and causal per-unit re-baselining | GPU (row scores needed) | If asked (I-09; `future_experiments/FE01_per_unit_recalibration_k_sweep.md`) |
| Q25 | MAJOR | Is one CVAE (no KL in the score, variance floor, fleet-trained) a fair representative of condition-aware models? | Weak comparator | §3.4, §5.5; Table S3 | `docs/extension/CVAE_SPECIFICATION.md`; locks `cvae_variance_bound_share` | No for a general claim; yes for the scoped claim | A second model (e.g. per-engine-trained or KL-scored CVAE) | EXPENSIVE (GPU training) | If asked (I-08; `future_experiments/FE03_second_condition_aware_model.md`) |
| Q26 | MODERATE | Why compare the CVAE with the *best* residual detector rather than each detector? | Fairness | §4.4 also gives the median residual gap (0.24 pp) | `post_hoc_checks.json["cvae_vs_residual"]` | Yes | No | NONE | If asked |
| Q27 | MODERATE | LSTM epoch selection used out-of-class validation engines (loss 138–234 in DS01/DS08c). Are those detectors degenerate? | Model quality | §5.5; hostile review §3 | `*/lock/training_history.csv`; Table S4 | Partly: the magnitude is not in the paper | No (a sensitivity would need retraining) | EXPENSIVE | If asked (I-15) |
| Q28 | MINOR | Why a 90% altitude rule for phases? Sensitivity to the phase definition? | Arbitrary constant | The frozen DS02/DS03 stages also ran `alt_rate` (`src/final_validation.py:PHASE_DEFINITIONS`) | `paper/mssp/` supplement (Part B) | Partly: not repeated in the extension | Re-score with the alternative phases | GPU | If asked (I-21) |

## Metrics and endpoints

| ID | Sev. | Question | Why | Existing evidence | Files | Sufficient? | New exp.? | Compute | Now? |
|---|---|---|---|---|---|---|---|---|---|
| Q29 | MAJOR | A2 conflates in-sample pooling error, transport error and direction. How much of A2 is transport? | Statistical and PHM personas | C010 (in-sample descent-highest counts); C034 (53% under-alarming) | `*/lock/calibration_in_sample_phase_fpr.csv`; `post_hoc_checks.json` | Partly: no decomposition "audit A2 − in-sample A2" is reported | Compute the transport gap from committed in-sample and audit phase FPRs | CHEAP_CPU | If asked (I-02; `future_experiments/FE04_a2_decomposition.md`) |
| Q30 | MAJOR | Is under-alarming (DS08c) really a *false-alarm* calibration failure? | Definition | §4.2 says F5 counts via under-alarming; §4.9 | `transport_summary_alpha_0.01.csv` | Yes (disclosed) | An over-alarming-only H1 variant (post hoc; reviewers say only F4 holds) | CHEAP_CPU | If asked (I-03) |
| Q31 | MODERATE | Why is 0.5α "material"? | Arbitrary line | §3.6; §5.5 | Protocol §13.1 | Partly | Sensitivity curve over lines (post hoc) | CHEAP_CPU | If asked |
| Q32 | MINOR | Row-level FPR at 1 Hz vs flight-level decisions: which matters operationally? | Practice | §3.6 separates FFR; §4.6 | Protocol §6 | Yes | No | NONE | If asked |

## Robustness, persistence, delay

| ID | Sev. | Question | Why | Existing evidence | Files | Sufficient? | New exp.? | Compute | Now? |
|---|---|---|---|---|---|---|---|---|---|
| Q33 | MAJOR | Within-flight on-delays act over seconds; real systems confirm across flights. Why test the wrong time scale? | Alarm-system persona | Post hoc two-flight rule (C037) | `post_hoc_checks.json["two_flight_confirmation"]` | Partly: post hoc, not matched per engine | k-of-n flight confirmation at matched per-engine burden | CHEAP_CPU (committed `flight_trajectories.csv`) | If asked (I-10; `future_experiments/FE02_flight_level_k_of_n.md`) |
| Q34 | MAJOR | Delay is matched on pooled burden, not per engine, and early sensitivity is near the floor. Is "no delay advantage" meaningful? | Low power | §4.6 "little power"; C038 | `summary/matched_labels_alpha_0.01.csv`; `*/audit/matched_operating_points.csv` | Yes as worded ("no advantage meeting the criterion") | Per-engine matched burden (post hoc) | CHEAP_CPU | If asked (I-11) |
| Q35 | MODERATE | Why the 2.5–20% FFR anchors, far above practical flight false-alarm rates? | Realism | Protocol §9 (frozen adversarial Part B) | `docs/mssp/adversarial_validation_plan.md` | Partly | Lower anchors are infeasible with 14–36 flights per engine | NONE | If asked |

## Interpretation and composition

| ID | Sev. | Question | Why | Existing evidence | Files | Sufficient? | New exp.? | Compute | Now? |
|---|---|---|---|---|---|---|---|---|---|
| Q36 | MAJOR | Coverage is confounded with engine identity and shared missions. What is actually shown? | Statistical reviewer M3 | §4.9 mission sharing (C035); §5.5 | `docs/extension/profile_sharing_engine_pairs.csv`; `post_hoc_checks.json` | Partly; the confound is acknowledged, not resolved | Coverage effect stratified by shared-signature share | CHEAP_CPU | If asked (I-04) |
| Q37 | MAJOR | The volume contrast is ~0 by construction. Why report it, and what substitutes for coverage? | Design flaw | §3.8 states it; the claim was withdrawn | Protocol §7 | Yes (withdrawn claim) | Engine-adding volume contrast (needs new calibration designs) | GPU: calibration-row scores are not stored (locks hold only fingerprints); LSTM/CVAE re-scoring needs CUDA, PCA/IF can run on CPU | If asked |
| Q38 | MODERATE | The DS08a e14 "envelope" mechanism rests on one flight. Is it an anecdote? | n = 1 | §4.9 (C017) | `post_hoc_checks.json["ds08a_engine14"]` | Yes as an observation; not as a mechanism | Envelope check for all audit flights (cheap, metadata) | CHEAP_CPU | If asked |
| Q39 | MODERATE | Why does conditioning worsen PCA so badly on DS05/DS06 (F3)? | Mechanism | §4.3 (C012); no mechanism given | `DS05/audit/phase_fpr.csv`, `transport_summary.csv` | No mechanism | Per-phase calibration-row counts vs audit (cheap) | CHEAP_CPU | If asked |

## Reproducibility and implementation

| ID | Sev. | Question | Why | Existing evidence | Files | Sufficient? | New exp.? | Compute | Now? |
|---|---|---|---|---|---|---|---|---|---|
| Q40 | MAJOR | Can I reproduce the numbers without NASA data and a GPU? | Reproducibility | `verify_numbers.py`, manifests, `scripts/run_public_tests.py` | README "Verifying the release" | Yes for numbers from outputs; no for re-running models (binaries not distributed) | No | CHEAP_CPU | If asked |
| Q41 | MODERATE | Model binaries are not distributed. How can outputs be checked against the models? | Verification gap | Lock hashes; local binaries 84/84 match | `results/extension/*/lock/calibration_lock.json` | Partly | Deposit binaries (Zenodo) | NONE | Now: consider archiving `results/extension/*/models/` privately (I-19) |
| Q42 | MODERATE | AI agents wrote and ran the analysis code. How was correctness assured? | Editorial policy | §3.11; AI declaration; reproduction gates; tests | `tests/`, `docs/extension/EXTENSION_HOSTILE_REVIEW.md` | Partly: "not independently reimplemented" | Independent reimplementation of the endpoint layer (CPU, from committed per-flight outputs) | MODERATE_CPU | If asked (I-18) |
| Q43 | MINOR | The Zenodo DOI is promised but missing | Code availability | README; `.zenodo.json` | `.zenodo.json` | No | No | NONE | Now/at acceptance (I-19) |

## Figure- and table-specific

| ID | Sev. | Question | Why | Existing evidence | Files | Sufficient? | New exp.? | Compute | Now? |
|---|---|---|---|---|---|---|---|---|---|
| Q44 | MINOR | Fig. 5 uses a log y-axis; the caption does not say so | Readability | `build_figures_tables.py:fig5_cvae` (`set_yscale("log")`) | Fig. 5 | Text fix | No | NONE | At revision |
| Q45 | MINOR | Fig. 3: what exactly are the grey ticks, and why only for P? | Post hoc overlay | Caption; `post_hoc_engine_noise.csv` (arm P) | Fig. 3 sidecar | Yes | No | NONE | If asked |
| Q46 | MINOR | Table 4: S1–S5, M-B, M-C are opaque | Readability | The caption defines them | Table 4 | Yes | No | NONE | If asked |
| Q47 | MINOR | Supplement order: S21 = component 1, S22 = component 3, S23–24 = component 2 | Confusing | `supplement.tex` order | Supplement | Text fix | No | NONE | At revision |
