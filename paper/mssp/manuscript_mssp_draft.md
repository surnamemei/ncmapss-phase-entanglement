<!--
MSSP MANUSCRIPT, final draft (v3), written after the story lock (docs/mssp/FINAL_STORY_LOCK.md).
Status: complete draft for author approval; not submitted.

Evidence rules:
- Frozen DS02/DS03 numbers (Sections 4.1-4.7) are carried verbatim from the audited RESS text
  and are cited through unchanged evidence IDs (paper/manuscript_core_results.csv).
- Post-confirmation numbers come from results/mssp_mitigation/ (frozen protocol v1.0) and
  results/mssp_adversarial/ (frozen adversarial-validation plan, commit 39a5f81).
- paper/mssp/verify_draft_numbers.py re-derives every cited post-confirmation number and checks
  it verbatim; it also enforces the terminology lock, word limits and citation integrity.

Citation labels: "[n]" are references carried from the audited RESS list; "[N#]" are references
verified in paper/mssp/reference_audit.csv. Numbering follows first citation at typesetting.
The RESS package (paper/ress/, paper/submission/) is not modified.
-->

# Phase-Dependent False-Alarm Calibration and Its Transport Across Engines in Full-Flight Aero-Engine Anomaly Detection

## Abstract

Residual-based anomaly detectors are usually given one alarm threshold calibrated to a nominal healthy false-alarm probability. Under nonstationary operation, such a pooled threshold controls only the exposure-weighted false-alarm rate. We audited this in full-flight aero-engine monitoring on the N-CMAPSS benchmark with residual principal component analysis (PCA), Isolation Forest and a past-only long short-term memory (LSTM) reconstruction network. Phase-dependent healthy false-positive rates, highest in descent, were discovered on the DS02 subset. A frozen protocol, applied once to held-out engines of the DS03 subset, reproduced the pre-specified pooled directional pattern (PCA: climb 0.877%, cruise 0.912%, descent 1.977% at a 1% target). Separately frozen post-confirmation analyses then examined calibration transport from two calibration engines to held-out audit engines. Retrospective phase-conditioned thresholds reduced pooled between-phase disparity and pooled maximum nominal calibration error in all 14 detector runs, although every paired bootstrap interval included zero. At matched healthy-flight false-flag rates, conditioning gave no general detection-delay advantage; earlier detection was confined mainly to low false-flag burdens. The pooled correction did not transport reliably to individual engines: two of the three short-flight audit engines, a flight class absent from calibration, became worse calibrated in every run, and weighting audit engines equally reversed the pooled improvement on DS02. A continuous operating-context quantile-regression threshold failed on different engines, and distance to calibration operating states did not explain the failures. Pooled phase-level correction therefore did not guarantee calibration transport across engines, and the strongest observed transport failures coincided with flight classes absent from calibration.

**Keywords:** condition monitoring; false-alarm calibration; nonstationary operating conditions; calibration transport; anomaly detection; aero-engine

**Highlights (Elsevier limit 85 characters each):**
- A pooled alarm threshold left healthy false-alarm rates dependent on flight phase
- The phase pattern found on DS02 reproduced under a frozen one-shot DS03 protocol
- Per-phase thresholds cut pooled disparity in 14/14 runs; paired intervals span zero
- Pooled gains failed on 2 of 3 engines of a short-flight class absent from calibration
- At matched false-flag rates, conditioning gave no general detection-delay advantage

## 1. Introduction

**Detection as a calibrated threshold test.** Condition monitoring of machines and systems increasingly relies on data-driven detection statistics computed from residuals between measured signals and a model of nominal behaviour [N1]. Whatever the model (principal-component reconstruction, an isolation-based score or a sequence reconstruction network), the monitoring decision is ultimately a threshold test: an alarm is raised when the statistic exceeds a level chosen for a nominal false-alarm probability. In aero-engine monitoring, false-alarm probability has long been an explicit design parameter of anomaly detection and alert-threshold placement [2], [11]. Frequent healthy alarms add review workload and can weaken the usefulness of a warning stream [12].

**Pooled thresholds under nonstationary operation.** The healthy distribution of a detection statistic is rarely stationary. Operating point, manoeuvres and ambient conditions change measured signals even when health is unchanged [N2]–[N4]. Schematically, a measured vector can be written as $x_t = f(h_t, o_t, d_t, \epsilon_t)$, where $h_t$ is health, $o_t$ the operating point, $d_t$ normal operating dynamics and $\epsilon_t$ measurement and model error. Operating-condition normalization removes part of the dependence on $o_t$ and $d_t$ before a statistic $s_t$ is formed and a decision $a_t = \mathbb{1}[s_t > \tau]$ is taken [N2], [N4]–[N6]. When a single threshold $\tau$ is calibrated on pooled healthy data, it controls only the exposure-weighted false-alarm probability,

$$P(a=1\mid h) = \sum_{\phi} \pi_\phi \, P(a=1 \mid h,\phi),$$

where $\phi$ indexes operating contexts and $\pi_\phi$ is their share of healthy exposure. The pooled rate can meet its nominal target while individual contexts run well above or below it [N7]. The expression for $x_t$ is conceptual, not an identified model.

**Context-specific thresholds are established.** The standard response is to condition the threshold on the operating context. Established examples, reviewed in Section 2, are:
- mode-specific control limits in multimode process monitoring [N8];
- constant-false-alarm-rate (CFAR) radar detectors [N10];
- category-conditional conformal calibration [N7] and thresholds adapted to discrete environments under a false-alarm budget [N45];
- alarm thresholds set per operating condition, shaft-speed bin, flight condition or flight state in machinery, jet-engine and rotorcraft monitoring [N22], [N25]–[N27];
- time-variant and zone-specific alarm design for non-stationary process variables [N39], [N40].

Conditioning a threshold on an operating category is therefore not new, and it is not proposed here.

**The open question is transport.** A context-specific threshold is calibrated on some units and then applied to others. Its guarantees rest on exchangeability between calibration and deployment data [N20], a particular calibration set can be unrepresentative [N16], and monitoring models may fail to transfer beyond the systems and conditions they were built on [N21]. An improvement measured after pooling all audit data may therefore not hold for the individual engines on which alarms are raised. We call this property *calibration transport*: whether a nominal healthy false-alarm calibration obtained on calibration engines remains valid, context by context, on other engines.

**The full-flight setting.** The N-CMAPSS benchmark simulates complete flights (climb, cruise and descent) driven by recorded flight conditions [1]. Anomaly detection on N-CMAPSS has used increasingly sophisticated temporal and graph models, evaluated mainly through aggregate detection metrics [7]–[9]. On simulated turbofan data, false-positive rates have been reported per operating mode, and a detector whose threshold was set on healthy cruise data alone flagged all data from the other modes [N23]. Three questions are rarely made held-out endpoints:
- whether a pooled healthy calibration remains valid across normal flight phases;
- whether a conditioned calibration that improves the pooled audit population also transports to individual engines;
- what conditioning changes in abnormal-state detection when arms are compared at matched false-flag burden rather than at unequal operating points.

**Staged design.** The study proceeded in stages (Fig. 1):
1. **DS02 discovery.** Three residual-based detectors, a correction challenge and a cross-phase threshold-transfer audit.
2. **Frozen DS03 confirmation.** All detector, correction, phase, calibration, endpoint and interpretation rules were frozen before a single evaluation on held-out engines.
3. **Post-confirmation transport analyses.** These were two further plans, each frozen before execution. A protocol comparing pooled with context-conditioned calibration was followed by an adversarial validation of it (nominal calibration error, engine weighting, matched false-flag delay, operating-support distance and a continuous contextual baseline).

The frozen confirmation is reported unchanged; the post-confirmation analyses are exploratory and never qualify it.

**Research questions.**
- **RQ1 (frozen).** Under pooled calibration, do healthy row-level false-positive rates (FPRs) vary systematically across flight phases?
- **RQ2 (frozen).** Do the tested static, derivative-based and finite-history operating-condition corrections sufficiently attenuate that dependence?
- **RQ3 (frozen).** Does the pooled directional pattern reproduce across three detector implementations and on a frozen, held-out subset?
- **RQ4 (post-confirmation).** Does context-conditioned calibration reduce nominal calibration error, not only between-phase disparity, and does a pooled improvement transport to individual engines?
- **RQ5 (post-confirmation).** At matched healthy-flight false-flag rates, does conditioning change abnormal-state detection delay?
- **RQ6 (post-confirmation).** Is the residual transport failure explained by the operating-state distance between audit and calibration data?

**Contributions.** The contribution is not phase-aware detection or regime-specific thresholding. It is a controlled audit of nominal healthy-FPR calibration and its transport under full-flight operation:
1. **Pooled calibration and cross-phase transfer.** Under pooled calibration, healthy FPR depended on flight phase for three residual-based detectors, and phase-specific thresholds transferred unevenly between phases.
2. **Discovery separated from confirmation.** The DS02 pattern was reproduced by a frozen one-shot DS03 evaluation, with engine- and seed-level exceptions reported.
3. **A post-confirmation transport audit.** Retrospective phase-conditioned thresholds removed most of the pooled phase-composition error, but the correction did not transport reliably to engines. The negative results are retained: no general delay advantage at matched false-flag rates, a continuous contextual baseline that failed on other engines, and support distance that did not explain the failures.
4. **An evaluation protocol for monitoring studies.** Nominal calibration error, between-context disparity, engine-weighted summaries and matched false-flag delay are reported together, under frozen plans with exact reproduction gates and re-derivable numbers.

**Scope.** The work provides calibration evidence for simulated N-CMAPSS subsets. It does not propose a detector or a threshold policy, identify a mechanism, or validate deployment on aircraft. The calibration question is not specific to aero-engines. It arises wherever one detection threshold, or one set of context-specific thresholds, is calibrated on part of a fleet and applied to other units operating under changing conditions, for example wind turbines [N1], [N4], gearboxes [N3], gas turbines [N13] and civil structures subject to environmental and operational variability [N2], [N5], [N6].

## 2. Related work

### 2.1 Operating-condition variability in machinery health monitoring

Environmental and operational variability is a central problem in structural and machine monitoring, because changing conditions alter measured features and can mask or mimic damage [N2]. Established responses include:
- data normalization and factor analysis before control charting [N2], [N5];
- models of the healthy response driven by measured operating parameters [N4];
- regime-switching response surfaces for structures whose behaviour changes abruptly between regimes [N6];
- machine-condition methods that first infer the operating condition and then assess condition relative to it, for gearboxes under fluctuating operation [N3].

For gas-turbine engines, classical practice monitored a restricted set of operating points or corrected measurements to reference conditions [N35]. Flight-condition-aware monitoring predates full-flight benchmarks. It includes flight-stage normalization of health and usage indicators [4], models of flight-data interrelations within a specified flight regime [3], and fleet monitoring with adaptive performance models across variable conditions [5].

N-CMAPSS replaced the snapshot-oriented C-MAPSS benchmark with complete simulated flights and assigns each engine a flight class [1]; its flight phases differ between flight classes, which motivates phase-wise alignment when models are transferred between flight-class sub-fleets [N28]. Operating-condition normalization and regime-specific modelling are therefore not contributions of this paper.

### 2.2 Condition-aware anomaly detection and adaptive alarm thresholds

**Anomaly detection under changing conditions.** For gas turbines under frequently changing operating conditions, anomaly detectors have been trained on a single condition and evaluated by aggregate discrimination (AUROC), with conventional vibration limits described as hard limits that do not adjust to conditions [N13]. A variational autoencoder conditioned on operating-condition variables has been used to decouple equipment state from operating conditions in power-plant gas turbines, and it was evaluated against six detection methods [N38]. On N-CMAPSS, residual models have been used to study training-data contamination [7], information-based fault detection has been evaluated [8], and a physics-guided spatiotemporal graph model has been assessed through ROC-AUC and F1 [9]. Residual-based detectors with thresholds set on healthy data have been compared by unit-level false positives and detection delay using cruise data only, because cruise is more stable than take-off or landing [N42]. For an aviation piston engine, detection metrics reported per power-lever phase under one global threshold were worst in climb, with phase-adaptive thresholds and cross-engine transfer left for future work [N43]. These studies make detection performance, not the phase-conditional validity of a healthy calibration, the endpoint.

**Adaptive and automatic thresholds.** Adaptive thresholds for aero-engine fault detection have been set over flight-envelope subareas [6]. Automatic, data-driven threshold setting for vibration-based anomaly detection is an active topic in this journal [N14]. In machine-sound anomaly detection, optimal decision thresholds differ across operating domains, so a single threshold across domains degrades performance [N37].

**Condition-specific alarm thresholds.** The closest precedents are condition-specific thresholds motivated by false alarms:
- **Multimode process monitoring.** Zhao et al. noted that a single-region model "would always trigger continuous warnings" in other normal modes. Mode-specific principal-component control limits reduced such false alarms [N8]. Mode-specific control limits for PCA residuals therefore predate this work.
- **Machinery alarms.** Toshkova et al. set extreme-value alarm thresholds per identified operating condition and reported a more reliable health indication than with uniform thresholds [N22].
- **Aero-engines and rotorcraft.** Clifton et al. set novelty thresholds per shaft-speed bin for jet-engine vibration [N27]. Wang et al. segmented aero-engine monitoring by flight condition [N25]. Lee et al. optimized thresholds per flight state for rotorcraft health and usage monitoring, where condition-agnostic thresholds caused frequent false alarms [N26].
- **Alarm-system design.** Alarm design balances false-alarm rate, missed-alarm rate and alarm delay [N32]. Asaadi et al. assessed univariate alarm systems for a process variable affected by an intermittent fault, modelled as a time-variant finite mixture, through the false-alarm rate, missed-alarm rate and averaged alarm delay over time [N39]. Their operational zone-specific design segments a process variable by change-point detection into normal, rising, fault and return-to-normal zones and evaluates zone-wise indices [N40]. These zones are stages of fault evolution in one variable, not normal operating contexts, and neither study evaluates whether an alarm calibration transports across units.

**Per-mode false-positive rates.** Michau and Fink reported false-positive rates for five operating modes of simulated turbofan data (take-off, cruise at two altitudes, descent and landing). A detector whose threshold was set on healthy cruise data alone flagged all data from the other modes [N23]. This is the closest demonstration that a calibration obtained in one context does not carry to another. It concerns transfer between operating modes rather than the validity of a pooled or context-conditioned calibration across engines.

### 2.3 Calibration validity, threshold transfer and the remaining gap

**Calibration validity.** Distribution-free calibration clarifies what a pooled threshold guarantees:
- Conformal p-values computed against a held-out inlier calibration set control the false-positive rate on average over calibration sets. A particular calibration set can be "unlucky" [N16].
- Validity within categories requires category-conditional calibration [N7]; monitoring thresholds can likewise be adapted to discrete environments while a false-alarm budget is distributed over an a priori partition [N45].
- Conformal threshold setting has been compared with classical thresholds for PCA and autoencoder fault detectors as a way to control false alarms [N41].
- In heterogeneous fleets, fleet-level normal models can be inefficient at individual units, which has motivated calibrating each unit against a similar sub-fleet with a bounded false-alarm probability [N44].
- All of these guarantees rest on exchangeability between calibration and deployment data, which drift violates [N20]. Under covariate shift, validity requires likelihood-ratio weighting [N30].

**Changing nuisance statistics.** Signal-processing detection faces the same issue. Subspace damage-detection tests fail when the excitation statistics change between the reference and monitored states [N15]. CFAR processors keep a constant false-alarm rate only by adapting to local clutter, and their behaviour at clutter edges is a separate design concern [N10].

**Delay and false-alarm burden.** Detection delay must be tied to the false-alarm rate. Sequential change detection defines and optimizes delay for a fixed mean time between false alarms [N17], and the ProDiMES benchmark fixed a common flight-level false-alarm target before comparing aircraft-engine gas-path detection rates and latency [N24].

**The remaining gap.** In a documented search we did not find a study that combines:
- an audit showing that a pooled nominal threshold on full-flight engine residuals controls only the exposure-weighted healthy FPR while climb, cruise and descent FPRs differ;
- cross-phase threshold transfer as a pre-specified endpoint, with every phase present in calibration;
- a frozen discovery-to-confirmation separation for that question;
- a post-confirmation evaluation of whether an apparent pooled phase-level correction transports to individual engines, with nominal calibration error, engine weighting, matched false-flag delay, a continuous contextual baseline and operating-support distance.

No priority is claimed for context-aware monitoring, regime-specific thresholds or adaptive thresholding. The contribution is the controlled calibration-transport audit.

## 3. Methodology

The analysis chain is $x_t \rightarrow r_t \rightarrow s_t \rightarrow a_t$: a sensor vector $x_t$, an operating-condition residual $r_t$, a detector score $s_t$ and a row alarm $a_t = \mathbb{1}[s_t > \tau(\cdot)]$. A pooled threshold $\tau$ is a single calibration quantile. A conditioned threshold $\tau_c$ is computed within a context $c$ (a retrospective phase, a past-only regime, or a continuous operating state). A pooled quantile sets $\sum_\phi \pi_\phi P(a=1\mid h,\phi)$ to the nominal level, whereas a conditioned quantile targets each $P(a=1\mid h,\phi)$ on the calibration engines. Transport is the question of whether either target, set on calibration engines, holds on audit engines, both pooled over them and engine by engine.

### 3.1 Dataset and staged study design

N-CMAPSS provides simulated run-to-failure trajectories of turbofan engines flown along recorded flight profiles [1]. Each engine flies one flight class: class 1 comprises short flights (1–3 h) at low altitude and speed, class 2 flights of 3–5 h, and class 3 the longest and highest flights (5–7 h) [1]. The analysis used subset DS02 for exploratory discovery and subset DS03 for frozen confirmation (Table 1). The study was staged as follows (Fig. 1).

**Discovery and freeze.** Detector families, the correction specification, the calibration rule, the phase definition, the evaluation endpoints and the interpretation rule were fixed before the DS03 audit outcomes were examined. DS03 was evaluated once under the frozen primary protocol. DS02 estimates were not treated as confirmation.

**Post-confirmation analyses.** After the confirmation, DS02 and DS03 were reused for exploratory transport analyses under two further plans, each committed before execution:
- **Protocol v1.0.** This protocol compared calibration arms and locked all calibration-derived quantities before any abnormal-state row was read. Abnormal-state rows were then read once per dataset (820,630 DS02 and 2,956,881 DS03 rows).
- **Adversarial validation plan.** This plan added calibration-quality, engine-weighting, matched-delay, support and baseline analyses. It reread no abnormal-state row.

Every stage began with exact reproduction gates (rescored healthy vectors equal to the frozen fingerprints bit for bit; recomputed tables, locks and bootstrap summaries equal to the committed ones), and a 186-file hash manifest of the frozen evidence was verified before and after every run. DS03 is described as held out only for the frozen confirmation.

### 3.2 Engine-disjoint fitting, calibration and audit partitions

The engine was the partitioning and top-level inferential unit, and timestamped observations were nested within flights identified by engine and cycle. Model-fitting, calibration and audit engines were disjoint (Table 1). LSTM epoch selection, model fitting and calibration followed this frozen allocation, and no detector, correction or threshold setting was changed after audit outcomes were available.

Flight class is a descriptive engine attribute that was never used to change a rule. In DS02 every model-fitting and calibration engine is class 3, so audit engines 14 (class 1) and 15 (class 2) come from classes absent from calibration. In DS03, calibration covers classes 2 and 3 (engines 4 and 8), so class-1 audit engines 12 and 14 are the absent-class engines; class 1 does appear among the DS03 model-fitting engines.

### 3.3 Healthy and abnormal-state labels

The detectors used 14 measured sensor channels. Four operating descriptors (altitude, Mach number, throttle-resolver angle and fan-inlet temperature; together $W$) were used for residualization and for the contextual analyses. The N-CMAPSS health-state annotation was never a detector input. It has two roles:
- It selects healthy ($hs = 1$) rows for fitting, threshold calibration and healthy false-alarm evaluation.
- In the post-confirmation analyses, it defines abnormal-state ($hs = 0$) rows and the labelled onset, the first flight with $hs = 0$, from which detection delay is counted in flights.

Because $hs = 0$ marks the simulated onset of degraded operation rather than a discrete fault event, abnormal-state endpoints are reported as alarm rates and delays relative to that labelled onset.

### 3.4 Retrospective phase definition

**Primary rule.** For each complete flight, the cruise interval ran from the first through the last sample whose altitude reached at least 90% of the flight's observed altitude range above its minimum. Earlier samples were labelled climb and later samples descent. These labels require the complete flight; they serve retrospective stratification only and are not available during a flight.

**Alternative retrospective rule (DS02 sensitivity only).** Cruise was defined by 85% of the altitude range together with an absolute centred 60-s altitude rate of at most 2 ft/s (0.61 m/s).

**Past-only regimes.** For the past-only regime-conditioned arm, each row was labelled ascending, level or descending from its trailing 60-s altitude rate, with a dead-band of ±2.0 ft/s (0.61 m/s; altitude sampled at 1 Hz, with shorter trailing windows at the start of each flight). Only current and past samples of the same flight are used. This rule reuses the window and limit of the alternative rule, but it is trailing and has no altitude-fraction condition.

### 3.5 Operating-condition residualization

The exploratory DS02 correction comparison considered three bases: static operating state, static plus first differences, and finite history. All confirmation and post-confirmation detector analyses used the finite-history specification. For each flight, its descriptors were:
- the current operating state and its first differences;
- trailing means, standard deviations and endpoint slopes over 30- and 120-sample windows (30 and 120 s at 1 Hz).

Descriptor construction reset at flight boundaries and used no future samples. A ridge regression (penalty 1.0) predicted the measured sensors from these descriptors. Its basis had cubic terms of the instantaneous operating state, linear and squared dynamic terms, and interactions between the instantaneous state and its first differences. Regression fitting and residual standardization used model-fitting engines only.

### 3.6 PCA, Isolation Forest and past-only LSTM scores

**Residual PCA.** Five components were fitted to the standardized residuals. The row score was the mean squared reconstruction error.

**Isolation Forest.** The forest used 200 trees, a maximum sample size of 8192 and automatic contamination, with seeds 0, 1 and 2. The score was the negative of the library `score_samples` output.

**Past-only LSTM.** A sequence-reconstruction network whose forward recurrences use only the current and preceding samples within a window:
- **Architecture.** Two 16-unit forward LSTM layers around an eight-feature per-time-step bottleneck, applied to 256-row windows within each flight, with a per-row mean squared reconstruction error.
- **Fitting.** Adam with learning rate 0.001 and batch size 256, and engine-disjoint epoch selection with at most 600 epochs and patience 6, for seeds 0, 1 and 2.
- **Convergence.** The DS02 seed-0 selection reached the epoch ceiling while validation loss was still improving. It is retained as a convergence limitation without test-informed retuning (Supplementary Figs. S1–S2).

The seven detector runs per dataset (one PCA run and three seeds each for Isolation Forest and the LSTM) are the units over which post-confirmation results are counted.

### 3.7 Pooled calibration and cross-phase transfer

**Pooled calibration (P).** For each detector run, pooled healthy calibration scores set nominal row-level FPR targets α of 0.5%, 1% and 2% by the empirical upper quantile ("higher" order statistic); 1% was primary. Phase-specific healthy FPRs were computed as alarmed healthy rows over healthy rows, pooled over audit engines and per engine.

**Frozen endpoints.** The directional contrasts were descent minus climb and descent minus cruise. For cross-phase transfer, a threshold calibrated within one phase was applied to each of the other phases. The frozen flight-level burden endpoint was "healthy flights with any alarm". It is kept separate throughout from the κ-based false-flag rate of Section 3.9.4.

**Uncertainty.** Two thousand hierarchical bootstrap replicates resampled calibration and audit data separately (engines, then flights within engines) and re-estimated thresholds in every replicate. No timestamp-level test was used. Intervals pertain to individual detector runs; no interval for a seed mean was computed, and interval endpoints were never averaged.

### 3.8 Frozen DS03 confirmation

The frozen protocol specified the primary phase rule, the history correction, the three detector families, pooled calibration at the three targets, the directional contrasts and the verdict rule before the DS03 audit engines were scored. The confirmation asked whether the pooled directional pattern (descent above climb and cruise under pooled calibration) reproduced. Per-engine directional exceptions and individual-run intervals were reported alongside the verdict. The confirmation was run once and is not revised by any later analysis.

### 3.9 Post-confirmation calibration-transport analyses

All post-confirmation analyses reuse the frozen detectors, scores and engine partitions; calibration-derived quantities use healthy calibration engines only, and nothing was changed after outcomes were seen.

#### 3.9.1 Phase-conditioned thresholds

The arms share the same healthy calibration rows:
- **P:** the frozen pooled thresholds;
- **C, retrospective phase-conditioned calibration:** per-phase upper quantiles, which are the diagonal of the frozen transfer design and were therefore observed before these analyses;
- **C′, past-only regime-conditioned calibration:** per-regime upper quantiles, with regimes from the trailing altitude rate (Section 3.4).

C requires complete-flight labels and is a retrospective diagnostic. C′ uses current and past samples only and is examined as an implementable alternative, not as a deployed system.

#### 3.9.2 Continuous contextual calibration baseline

Coarse phase labels might cause any transport failure of C. To test that objection, a continuous contextual threshold (Q) was added as an adversarial control, not as a proposed method. Its specification was fixed before execution:
- **Model.** Linear quantile regression of the detector score at level $1-\alpha$ on a quadratic response surface of the four standardized operating descriptors $W$: four linear terms, four squares and six pairwise products (14 terms plus an intercept).
- **Fitting.** The model was solved exactly by linear programming (unpenalized, HiGHS solver) on every fifth healthy calibration row, per detector run and target, with no tuning and no phase input.
- **Alarm rule.** A row alarms when its score exceeds the predicted quantile. The flight-level κ is computed from healthy calibration flights, as for the other arms.

Q was pre-specified to run only if C reduced between-phase disparity in at least 5 of 7 runs per dataset, which held. Only its healthy-side endpoints were evaluated, because its abnormal-state endpoints would have required a new read of abnormal-state rows.

#### 3.9.3 Calibration-quality metrics

For each arm and target, with phase FPRs $\{\mathrm{FPR}_\phi\}$ over climb, cruise and descent:
- **A1, between-phase disparity:** $\max_\phi \mathrm{FPR}_\phi - \min_\phi \mathrm{FPR}_\phi$;
- **A2, maximum nominal calibration error:** $\max_\phi |\mathrm{FPR}_\phi - \alpha|$;
- **A3, root-mean-square nominal calibration error:** computed over the three phases;
- **A5, overall-FPR error:** $|\mathrm{FPR} - \alpha|$ over all healthy audit rows.

Disparity measures only equality between phases, whereas nominal calibration error measures distance from α. A disparity reduction is called a calibration improvement only when the nominal-error metrics also decrease.

**Weightings.** Every metric was computed row-pooled over audit engines (the frozen estimand), with audit engines weighted equally, and per engine.

**Categories.** Each comparison with P (dataset × run × target × arm) fell into one of four pre-specified categories:
1. disparity and nominal calibration both improve;
2. disparity improves but nominal calibration does not;
3. mixed;
4. conditioning worsens both.

**Wording rule.** The pre-specified rule allowed the wording "improved nominal phase-wise calibration" only for category 1 in at least 6 of 7 runs at 1%, at least 5 of 7 at the other targets, and no contradiction in a majority of engines.

**Uncertainty.** Paired arm-minus-P intervals extended the frozen bootstrap resampling plans (engines, then flights; thresholds re-estimated; 2000 replicates). Each claim was also classified across the three targets as invariant, mostly invariant, target-sensitive or reversed.

#### 3.9.4 Matched false-flag delay analysis

**Flight rule.** A flight's alarm fraction $r(f)$ is its share of alarmed rows, and the flight is flagged if $r(f) > \kappa$. For each run, arm and target, κ was locked in advance at the 0.95 "higher" quantile of healthy calibration-flight alarm fractions, a nominal 5% healthy-flight false-flag rate. It is the second-largest of 32 (DS02) or 40 (DS03) calibration flights.

**Delay and burden.** The realized healthy-flight false-flag rate (FFR) is the share of healthy audit flights that are flagged. An audit engine's detection delay is the number of flights from the labelled onset to its first flagged post-onset flight; it is censored if no post-onset flight is flagged. Delays are summarized by the lower median over audit engines, with censored engines ranked last.

**Matching.** Comparing arms at their own locked κ confounds delay with false-flag burden, because each locked κ yields a different realized FFR. Arms were therefore compared at matched realized FFR:
- **Operating characteristic.** κ was swept over a calibration-only grid: zero, the healthy calibration-flight alarm fractions, and 400 fixed log-spaced values in $[10^{-4}, 1]$. No audit or abnormal-state quantity entered the grid.
- **Anchors.** At each anchor FFR (2.5%, 5%, 10%, 15% and 20%), each arm used the grid point with the nearest realized FFR.
- **Support.** A match was supported only within one healthy-flight step of the anchor ($1/N_h$, with $N_h$ = 76 in DS02 and 148 in DS03). Delays were never interpolated or extrapolated.

**Labels.** At each supported anchor, the per-engine arm-minus-P delay differences were summarized by their lower median. A run was labelled:
- "earlier at matched burden" if the difference was negative at a majority of its supported anchors and positive at none;
- "later" in the mirror case;
- "equal" if it was zero at every supported anchor;
- "mixed" otherwise.

The statement "improves detection delay" required the earlier label in at least 5 of 7 runs, together with a lower curve-level mean than P.

**Curve-level mean.** It is the mean of the matched median delay over a grid of realized FFR from 2.5% to 20% in 0.25-point steps (71 points), using at each grid point the nearest operating point within one healthy-flight step and excluding grid points without one. It is therefore a normalized partial area under the median-delay operating characteristic over a range of false-flag rates that every arm covers, with no interpolation.

#### 3.9.5 Engine weighting and transport analysis

**Transport metrics.** Transport was assessed through:
- per-engine metrics;
- the equal-engine summaries;
- the sign agreement between row-pooled and equal-engine paired differences.

A post-plan descriptive decomposition (Supplement) splits the equal-cell mean squared nominal error over engine × phase cells into overall bias, phase, engine and interaction components.

**C0, phase effect without support mismatch.** Pooled thresholds were applied to the calibration engines themselves, both in-sample and from one calibration engine to the other. Calibration-to-audit mismatch is absent there by construction.

**Operating-support distance.** With operating descriptors standardized by calibration statistics, each healthy audit row's support distance was its Euclidean distance to the nearest healthy calibration row of the same retrospective phase. Secondary versions ignored phase or added the 120-s trailing slopes, and the distance between the two calibration engines served as the reference scale. Spearman correlations between median cell distance and $|\mathrm{FPR} - \alpha|$ under C were computed across engine × phase cells, per run, with leave-one-engine-out ranges; rows were never treated as independent units. A pre-specified rule classified the association as supported, not supported, or indeterminate because of the small engine count.

### 3.10 Implementation, reproducibility and use of AI tools

The pipeline was implemented in Python 3.12 (NumPy, pandas, scikit-learn and PyTorch; package versions are locked in the repository), and every stage writes run records with the hashes of its inputs and analysis module. Generative AI coding assistants were used in the research process under the author's direction:
- **OpenAI ChatGPT and Codex (OpenAI)** supported code development and debugging for the discovery and confirmation pipeline.
- **Claude (Anthropic; Claude Opus 5.5, used through the Claude Code tool)** wrote the post-confirmation and adversarial-validation code, ran those analyses in the author's environment under the frozen plans, and wrote the figure, table and verification scripts.

The author set the research questions, approved every protocol and plan before execution, and reviewed the code and outputs. Correctness rests on the exact reproduction gates (Section 3.1), automated tests, and scripts that re-derive every reported number; the pipeline has not been independently reimplemented. The figures are data plots and a schematic drawn by these scripts, and no generative image tool was used.

## 4. Results

Sections 4.1–4.7 report the frozen discovery and confirmation results unchanged. Section 4.8 is post-confirmation and exploratory.

### 4.1 DS02 discovery

At the primary nominal 1% pooled calibration target, PCA healthy row-level FPR was 0.125% in climb, 0.428% in cruise and 3.459% in descent (Fig. 2, Table 2). The descent-minus-climb and descent-minus-cruise contrasts were +3.335 and +3.031 percentage points (pp).

The corresponding Isolation Forest seed-mean FPRs were 0.268%, 0.558% and 2.487% (contrasts +2.219 and +1.928 pp). For the LSTM, the seed-mean FPRs were 0.488%, 0.729% and 2.080% (contrasts +1.592 and +1.351 pp). Under pooled calibration, descent therefore had the highest healthy FPR across the three tested implementations. The nominal 1% target applied to pooled healthy calibration scores; it did not constrain each audit phase to 1% FPR.

### 4.2 Correction sensitivity

For DS02 PCA, the descent-minus-climb contrasts were +2.854, +3.045 and +3.335 pp under static, static-plus-derivative and finite-history correction, respectively. The descent-minus-cruise contrasts were +2.418, +2.648 and +3.031 pp. The tested corrections therefore did not sufficiently attenuate the dependence: both contrasts remained positive under every tested correction and did not shrink. This exploratory comparison was not repeated on DS03 (Supplementary Table S2).

### 4.3 Cross-detector consistency

With the common history correction and pooled calibration, DS02 overall healthy row-level FPRs were 1.363% for PCA, 1.127% for the Isolation Forest seed mean and 1.118% for the LSTM seed mean. The descent elevation was observed across the three tested implementations. They share preprocessing and calibration, so this does not establish detector independence.

### 4.4 Cross-phase threshold transfer

On DS02, the worst off-diagonal healthy row-level FPR after phase-specific calibration was 15.555% for PCA. The arithmetic means of the per-seed maxima were 27.281% for Isolation Forest and 5.954% for the LSTM. The corresponding DS03 values were 6.716%, 9.386% and 5.308%. In every run on both subsets, the maximum cell applied a climb-calibrated threshold to healthy descent rows (Supplementary Table S6). Off-diagonal cells are cross-phase transfer FPRs, and diagonal cells are within-phase healthy FPRs. Neither is a pooled-threshold phase FPR. The diagonal is the phase-conditioned arm examined in Section 4.8.

### 4.5 Cluster-aware uncertainty and engine heterogeneity

The audit sets contain three DS02 and six DS03 engines, so reversals in individual engines matter.
- **DS02 PCA.** The hierarchical-bootstrap 95% intervals were [+2.070, +5.629] pp for descent minus climb and [+1.808, +5.261] pp for descent minus cruise.
- **DS02 LSTM.** The descent-minus-climb intervals for seeds 1 and 2 included zero: [−0.022, +2.817] and [−0.347, +2.802] pp.
- **DS03 PCA.** The intervals were [+0.434, +1.785] and [+0.560, +1.573] pp.
- **DS03 LSTM.** Every descent-minus-cruise interval included zero.

Per-engine values are given in Supplementary Tables S4–S5.

### 4.6 Frozen DS03 confirmation

At the pre-specified primary target, the pooled climb, cruise and descent FPRs were:
- PCA: 0.877%, 0.912% and 1.977%;
- Isolation Forest seed means: 0.409%, 1.104% and 2.142%;
- LSTM seed means: 0.751%, 1.889% and 2.215%.

The pooled descent-minus-climb and descent-minus-cruise contrasts were:
- PCA: +1.100 and +1.066 pp;
- Isolation Forest seed mean: +1.733 and +1.038 pp;
- LSTM seed mean: +1.464 and +0.325 pp.

The pre-specified pooled directional pattern was therefore reproduced (Fig. 2, Table 2). Three of 42 per-engine detector/seed rows were directional exceptions, all for LSTM seed 2. All three individual-seed LSTM descent-minus-cruise intervals included zero: [−0.222, +1.201], [−0.270, +1.158] and [−0.582, +1.025] pp. The pooled pattern therefore reproduced without uniform engine-level replication.

### 4.7 Phase-rule sensitivity

Under the alternative retrospective rule (85% of the altitude range and an absolute centred 60-s altitude rate of at most 2), the pooled descent-minus-climb and descent-minus-cruise contrasts remained positive on DS02:
- PCA: +3.432/+3.293 pp;
- Isolation Forest: +2.383/+2.256 pp;
- LSTM: +1.803/+1.756 pp.

The frozen DS03 confirmation used the primary rule only (Supplementary Table S3).

### 4.8 Post-confirmation calibration transport

All results in this section are exploratory point-estimate patterns over the seven detector runs per dataset, reported with paired bootstrap intervals and engine-level results (Tables 3–5; every run, engine, target and interval is in the Supplement).

#### 4.8.1 Between-phase disparity

**Point estimate.** Retrospective phase-conditioned calibration (C) reduced the pooled between-phase disparity A1 in all 14 detector runs (Fig. 3a, Table 3):
- DS02: from 1.52–3.33 to 0.31–0.92 pp;
- DS03: from 1.10–1.75 to 0.27–0.63 pp.

Past-only regime-conditioned calibration (C′) also reduced it in every run, to DS02 0.33–0.60 and DS03 0.12–0.88 pp. The continuous baseline Q reduced disparity relative to P in 12 of 14 runs.

**Uncertainty.** None of the paired arm-minus-P intervals for disparity excluded zero.

**Engine heterogeneity.** Disparity reduction did not hold in every engine (Section 4.8.5).

**Interpretation.** Because calibration and audit engines were disjoint, the pooled reduction is out of sample. Most of the pooled phase disparity therefore comes from calibrating one threshold over a mixture of phases.

#### 4.8.2 Nominal calibration error

**Point estimate.** The disparity reduction was not only an equalization of phases around a biased level. For the row-pooled audit population, C also reduced the maximum nominal calibration error A2 in all 14 runs and the RMS error A3 in 13 of 14 runs at 1% (Fig. 3b,c):
- DS02: A2 fell from 1.06–2.46 to 0.28–0.85 pp;
- DS03: A2 fell from 0.98–1.23 to 0.66–0.86 pp.

**Categories.** C fell in category 1 (disparity and nominal calibration both improve):
- DS02: 7 of 7 runs at every target;
- DS03: 7, 6, and 5 of 7 runs at 0.5%, 1% and 2%.

**Overall rate.** Overall healthy FPR moved by −0.10 to +0.40 pp, and its error A5 improved in only 4 of 14 runs. Conditioning therefore redistributed healthy alarms across phases rather than reducing them.

**Uncertainty.** No paired arm-minus-P interval excluded zero at 1%, for any metric, arm or dataset. At 0.5% and 2%, 558 of 560 paired U1 intervals included zero. The two exceptions were disparity reductions by C′ for DS02 Isolation Forest seeds 0 and 1 at 2%.

**Interpretation.** Under the pre-specified wording rule, only DS02 C qualifies for "improved nominal phase-wise calibration" on the row-pooled estimand. DS03 C and both C′ arms qualify only for "reduced between-phase disparity". The 14 of 14 count is a directional pattern, not an inferential result.

#### 4.8.3 Row-pooled versus equal-engine weighting

**Point estimate.** The row-pooled estimand gives most weight to the engines with the most healthy rows. With the audit engines weighted equally, the DS02 improvement reversed (Fig. 3d, Table 5). C fell in category 4, worsening both disparity and nominal calibration, in 5 of 7 runs at 1%, and its equal-engine A2 was higher than under P in 6 of 7 runs. On DS03, the equal-engine results agreed with the row-pooled ones: category 1 in 6 of 7 runs and no run with a higher equal-engine A2.

**Sign agreement.** The signs of the calibration-error changes (A2, A3) agreed between the two weightings in 15–16 of 42 DS02 comparisons and in 36–39 of 42 DS03 comparisons, counted over runs, targets and both conditioned arms.

**Decomposition.** A post-plan descriptive decomposition treats engine × phase cells equally (Supplementary Table S23 and Fig. S4). Under P, the phase component dominated the mean squared nominal error, with medians of 72% (DS02) and 57% (DS03). Under C it fell to 14% and 5%. The equal-cell RMS error, however, rose on DS02 (1.61 against 0.96 pp) and was essentially unchanged on DS03 (0.81 against 0.84 pp).

**Interpretation.** Conditioning converted most of a phase-composition error into engine and engine × phase error. Whether it helps depends on the weighting, and the operationally relevant weighting depends on the deployment.

#### 4.8.4 Matched false-flag detection delay

**Why matching is needed.** Comparisons at the locked κ were potentially confounded, because the locked κ did not transport. Realized pooled healthy-flight false-flag rates ranged from 2.7–31.6% against a nominal 5%, and one class-1 engine reached 57% (Fig. 4c). Delays were therefore compared at matched realized FFR, using supported operating points only.

**Matched comparisons, point estimates** (Fig. 4a,b; Table 4):
- **DS02, low burden.** C flagged abnormal-state onset earlier than P at the lowest anchors: 5 of 5 supported runs at 2.5%, and 7 of 7 runs at 5% (median paired difference −7 flights).
- **DS03, low burden.** Earlier in 4 of 7 runs at 2.5% (one later), and in 3 of 6 supported runs at 5% (one later).
- **Higher burdens.** At 10% or more, the differences largely vanished (mostly ties), and median delays were at most 7 flights in every arm.

**Pre-specified labels.** Because of these ties, "earlier at matched burden" held in only 3 of 7 DS02 runs and 0 of 7 DS03 runs for C, and in 4 and 2 of 7 for C′. The pre-specified criterion for "improves detection delay" was therefore not met. The curve-level mean delay over 2.5–20% FFR was lower for C than for P in 6 of 7 runs on each dataset, but that is only the second condition of the criterion.

**Uncertainty.** No interval was attached to the matched differences (three and six audit engines); per-engine values are in the Supplement.

**Locked points.** At the locked κ, most comparisons were trade-offs: one arm had the lower delay and the other the lower false-flag rate. The apparent locked-point delay advantages therefore mainly reflected more aggressive flight-level operating points, especially on DS03.

**Row-level rates.** Abnormal-state row alarm rates stayed within the interpretive guardrails (family ratios 0.98–1.16). Row-level alarm rates and flight-level delays often moved in different directions, so neither substitutes for the other. The frozen burden endpoint "healthy flights with any alarm" and the κ-based FFR also changed in opposite directions in most runs (Supplementary Tables S12 and S17).

**Interpretation.** Conditioning offered a trade-off concentrated at low false-flag burden: it did not dominate P, and it gave no general delay advantage.

#### 4.8.5 Cross-engine failures and flight-class composition

**Class-1 engines.** Calibration contained no class-1 engine in either subset. Conditioning worsened A2 and A3 in every detector run at 1% for two of the three class-1 audit engines (Fig. 5, Table 5):
- **DS02 engine 14.** A2 rose from 0.99–3.97 pp under P to 3.74–6.59 pp under C. Climb, which over-alarmed under C, carried the largest error.
- **DS03 engine 12.** A2 rose from 0.39–0.85 to 0.82–2.17 pp.
- **DS03 engine 14.** This third class-1 engine worsened in 3 of 7 runs.

The past-only regime arm showed the same engine-level pattern: its A2 exceeded that of P for DS02 engine 14 in 7 of 7 runs and for DS03 engine 12 in 6 of 7.

**Other absent-class and in-class engines.** Not every engine from a class absent from calibration failed. DS02 engine 15 (class 2, also absent from DS02 calibration) improved under C in every run, with A2 falling from 0.66–2.67 to 0.14–0.30 pp. Some in-class engines worsened in several runs: DS03 engine 10 (class 3) in 3 of 7 runs and DS03 engine 15 (class 2) in 4 of 7.

**Interpretation.** This is descriptive evidence from three class-1 engines and one class-2 engine, without per-engine intervals. The largest and most consistent failures coincided with the class that no calibration engine represented, which points to calibration composition and transport. It does not establish flight class as the causal variable, and flight class was never used to change a rule.

#### 4.8.6 Continuous contextual baseline

**Calibration.** The in-sample calibration alarm rate of Q (Section 3.9.2) was 0.97–1.03% at the 1% target.

**Pooled point estimates** (Fig. 3, Table 3). Q reduced disparity relative to P in 12 of 14 runs. However, its row-pooled maximum phase error was lower than that of C in only 3 of 14 runs (0 of 7 on DS02).

**Engine heterogeneity** (Fig. 5, Table 5):
- **Class-1 engines.** Q transported better than C to the two engines on which C failed. DS02 engine 14 had a maximum phase error of 0.54–2.20 pp under Q against 3.74–6.59 pp under C, and DS03 engine 12 had 0.40–0.74 against 0.82–2.17 pp.
- **In-class engines.** Q failed where C did not. DS03 engine 10 (class 3) reached 3.59–7.57 pp, worse than P in every run, and on DS02 single runs reached up to 4.25 pp on engines 11 and 15.
- **Flight level.** The realized healthy-flight false-flag rate at Q's calibration κ was 7.9–22.4% (DS02) and 4.1–10.8% (DS03).

**Interpretation.** Neither discrete phase conditioning nor the tested continuous contextual calibration produced uniformly transportable calibration across engines. Because the two failed on different engines, the transport failure is not solely an artefact of coarse phase discretization. Q is one transparent baseline, not an exhaustive search over contextual models, and its abnormal-state side was not evaluated.

#### 4.8.7 Operating-support-distance analysis

**The phase effect needs no support mismatch.** Applied to the calibration engines themselves, the pooled threshold reproduced the phase ordering (Fig. 6a). In-sample, descent was the highest-FPR phase in 7 of 7 runs on each dataset:
- DS02: descent 1.92–2.45% against climb 0.04–0.32%;
- DS03: descent 1.27–1.74% against climb 0.35–0.45%.

Descent was also highest in 27 of 28 run–target combinations at 0.5% and 2%, and in 27 of 28 evaluations from one calibration engine to the other at 1%. The pooled phase effect is therefore a property of the healthy score distribution that a pooled threshold averages over, not a product of calibration-to-audit mismatch.

**Where the class-1 engines leave support.** Their cruise rows lay far from calibration cruise states (Fig. 6b,c; Supplementary Table S20):
- a median same-phase distance of 0.74–1.13, against at most 0.07 for every other engine × phase cell;
- 82–95% of their cruise rows outside the calibration cruise range.

Their climb and descent rows lay within support.

**Distance did not explain the residual failures.** The largest residual errors under C occurred in cells that were within support: DS02 engine 14 climb and DS03 engine 10 climb (class 3). Across engine × phase cells, the Spearman correlation between support distance and |FPR − α| under C had a median of 0.03 (DS02) and 0.04 (DS03), and its sign flipped when single engines were left out. The pre-specified verdict was *indeterminate due to the small engine count*. Descriptively, nearest-neighbour operating-state distance did not explain the residual transport failures. The largest failures sat on class-1 engines, not on the cells farthest from calibration support.

## 5. Discussion

### 5.1 What pooled calibration misses

As the mixture decomposition implies, a pooled nominal target controls an exposure-weighted average and can conceal large differences in $P(\mathrm{alarm}\mid\mathrm{healthy},\mathrm{phase})$. The effect has four features:
- it appeared in discovery and reproduced under the frozen confirmation;
- it was present within the calibration engines themselves, at every target and for three detector implementations;
- it is therefore a property of the healthy score distribution under the tested corrections, not an artefact of moving thresholds between engines;
- the tested corrections did not sufficiently attenuate it.

That last point is a bounded statement about these fitted corrections. Finite sensor response, omitted operating variables, longer state history, path dependence and simulator structure remain hypotheses. Phase is a retrospective stratum here, not a physical cause.

### 5.2 Why lower phase disparity is not sufficient

A threshold rule can equalize phases around the wrong level, or equalize them for the pooled population while individual engines diverge. The post-confirmation results show the second failure:
- Pooled disparity and pooled nominal error fell.
- Overall healthy FPR was not reduced; alarms were redistributed across phases.
- With engines weighted equally, the DS02 improvement reversed, because most of the pooled phase-composition error became engine and engine × phase error.

A context-specific calibration rule can therefore look successful when evaluated after pooling across engines, yet fail on engines outside the calibration composition. Reporting disparity alone, or only the row-pooled estimand, would have hidden this.

### 5.3 Calibration transport across engines

Calibration guarantees are statements about exchangeable data [N20]. Marginal validity is an average over calibration sets, a particular calibration set can be unrepresentative [N16], and transfer under covariate shift requires reweighting [N30]. Monitoring models likewise transfer poorly beyond the systems and conditions they were built on [N21], and fleet-level normal models can be inefficient at heterogeneous individual units [N44]. On N-CMAPSS, flight phases differ between flight classes [N28], and the class-1 cruise rows lie outside the calibration cruise support.

Three observations nevertheless bound any composition explanation:
1. **Support distance.** Class-1 climb rows were within support yet over-alarmed under C.
2. **An absent-class engine that improved.** DS02 engine 15 came from a class absent from calibration, yet it improved in every run, so class absence was not sufficient for failure.
3. **The continuous baseline.** Q moved the failure to other engines.

Together they suggest an engine- or flight-profile-level shift in the healthy score distribution conditional on operating state, which neither phase labels nor the tested operating descriptors captured. That is a hypothesis for future work. The strongest observed transport failures coincided with the flight class absent from calibration, but three engines cannot establish flight class as the governing variable.

### 5.4 Implications for machine-health-monitoring evaluation

Context-specific false-alarm calibration should not be judged only by aggregate or phase-pooled improvements. Its transport should be audited across engines and operating classes, with nominal calibration error, between-context disparity and detection/false-flag trade-offs reported jointly. Concretely, a monitoring evaluation should report:
- phase- or context-conditional healthy FPR alongside the pooled FPR;
- nominal calibration error, not only between-context disparity;
- row-pooled and equal-engine summaries, with every engine exception;
- the composition of the calibration set (engines, flight classes and operating ranges) relative to the units on which thresholds are used;
- detection delay as an operating characteristic against realized false-flag burden, compared at matched burden and without interpolation.

These are evaluation requirements, not evidence that any threshold policy is superior. Phase-conditioned thresholds are not recommended here as a deployment solution.

The staged design mattered: freezing and a one-shot confirmation separated exploration from the confirmatory claim [N33], and the frozen post-confirmation plans exposed the weighting dependence, the transport failure and the matched-burden delay pattern, all of which would have been easy to explain away afterwards.

### 5.5 Relation to prior context-aware methods

This study does not compete with context-aware monitoring methods; it evaluates the calibration question that they raise:
- **Mode- and condition-specific thresholds.** Mode-specific control limits [N8], per-condition extreme-value alarms [N22], speed-binned engine thresholds [N27], flight-condition segmentation [N25] and flight-state thresholds [N26] all motivate context-specific thresholds by false alarms. Our results support that motivation for the pooled population: C removed most of the phase-composition error. They add that such an improvement need not transport to engines outside the calibration composition.
- **Per-mode false-positive rates.** Michau and Fink showed that a single-mode calibration fails in other modes [N23]. Here, even with every phase present in calibration, a per-phase calibration failed on two of the three engines of an unrepresented flight class.
- **Delay at a fixed false-alarm budget.** ProDiMES compared detection latency at a fixed flight-level false-alarm target [N24], and sequential detection defines delay at a fixed false-alarm rate [N17]. Our matched analysis applies the same principle to calibration arms and shows how locked-point comparisons can mislead when the flight-level threshold does not transport.
- **Alarm-system design.** Joint false-alarm, missed-alarm and delay design [N32], including time-variant and zone-specific designs for non-stationary process variables [N39], [N40], shares our insistence on evaluating false alarms and delay together. Here the contexts are normal flight phases rather than fault-evolution stages, and the question is whether a context-specific calibration transports across units. The same question applies to the thresholds of context-conditioned detectors [N38] and of conformally calibrated detectors [N41].

### 5.6 Limitations

- **Simulated data.** N-CMAPSS is a simulation driven by recorded flight conditions. The results do not establish validity on real aircraft, and there was no real-aircraft validation.
- **Few engines.** There are only two calibration engines per dataset and three (DS02) and six (DS03) audit engines. Class-1 transport evidence rests on three engines in total, and absent-class evidence on four.
- **Intervals.** All primary paired post-confirmation intervals include zero. Every post-confirmation statement is a point-estimate pattern, and the support association is indeterminate.
- **Post-confirmation status.** The post-confirmation analyses were frozen before execution but are exploratory. They reuse the confirmation engines and are not part of the DS03 confirmation.
- **Retrospective phases.** Phase labels require complete trajectories. The retrospective phase-conditioned arm is a diagnostic, not an implementable monitor.
- **Simulated labels.** The abnormal-state label ($hs = 0$) is a simulated degradation-state annotation, not a discrete real-aircraft fault event, and delays are measured from that labelled onset.
- **Baseline scope.** The continuous contextual baseline is one transparent specification, not an exhaustive search. Its abnormal-state side was not evaluated.
- **No mechanism.** The operating-support metrics tested do not identify a mechanism. The flight-class association is descriptive, not causal evidence.
- **Shared pipeline.** The detector families share preprocessing, residualization and calibration, so they are not independent replications. Seed means are descriptive.
- **Implementation.** No independent implementation or reimplementation of the pipeline exists. The analysis code was developed with AI assistance and verified by the author (see the declaration below).

## 6. Conclusion

**What was discovered and confirmed.** Pooled healthy calibration of full-flight aero-engine anomaly detectors left false-alarm rates dependent on flight phase. The dependence was discovered on DS02, the pre-specified pooled directional pattern reproduced under a frozen one-shot DS03 protocol, and the same ordering was present within the calibration engines.

**What the transport audit changed.** Post-confirmation, retrospective phase-conditioned thresholds reduced pooled between-phase disparity and pooled nominal calibration error in every detector run, although all paired intervals included zero. The correction did not transport reliably to individual engines. The strongest failures coincided with the flight class absent from calibration, equal-engine weighting reversed the DS02 improvement, a continuous contextual threshold failed on other engines, and operating-support distance did not explain the failures. At matched false-flag rates, conditioning gave no general detection-delay advantage.

**Why pooled correction is insufficient.** A context-specific calibration rule can look successful when evaluated after pooling across engines yet fail on engines outside the calibration composition. Full-flight anomaly-detection studies should therefore evaluate not only conditional false-alarm disparity but also calibration transport across engines and operating classes.

**What remains to be validated.** The evidence is limited to simulated N-CMAPSS subsets and small engine sets, and it identifies no mechanism. Future validation should use real or independently sourced full-flight data, calibration sets that deliberately span the flight classes and operating ranges to which thresholds will be applied, and frozen transport tests on units held out from calibration.

## Data availability

N-CMAPSS is publicly available from the NASA Prognostics Center of Excellence Data Set Repository ("Turbofan Engine Degradation Simulation-2"). This study used subsets DS02 and DS03. The raw NASA files are not redistributed.

## Code availability

Code, frozen protocols and plans, run records, derived outputs and the scripts that re-derive every reported number are available at https://github.com/surnamemei/ncmapss-phase-entanglement. The MSSP version corresponds to release v1.1.0, which is to be archived with a persistent identifier before publication.

## Declaration of competing interest

The author declares no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

## Funding

This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors.

## CRediT authorship contribution statement

**Jinghang Mei:** Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Data curation, Visualization, Writing – original draft, Writing – review & editing.

## Appendix A. Supplementary data

The supplementary material (Tables S1–S23 and Figures S1–S4) and machine-readable evidence files accompany this article.

## Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

During the preparation of this work, the author used OpenAI ChatGPT and Codex (OpenAI) and Claude (Anthropic; Claude Opus 5.5, through the Claude Code tool) in order to assist with code development and debugging (described in Section 3.10), literature searching, organization of the literature and verification of references, and drafting and editing of substantial parts of the manuscript text, figure captions, tables and supplementary material. After using these tools, the author reviewed and edited the content as needed and takes full responsibility for the content of the published article.

## Figures (captions)

**Fig. 1.** Staged study design. DS02 discovery, the protocol freeze and the one-shot DS03 confirmation form the frozen evidence, which is cited unchanged. The post-confirmation protocol v1.0 (arms P, C and C′, with κ locked before abnormal-state rows were read once) and the adversarial validation (nominal error, engine weighting, matched false flags, operating support and the continuous baseline Q) were each frozen before execution. They are exploratory and do not revise the DS03 verdict.

**Fig. 2.** Frozen pooled-threshold healthy row-level FPR by flight phase at the 1% target: (a) DS02 exploratory discovery; (b) DS03 frozen one-shot confirmation on held-out engines. Isolation Forest and LSTM bars are frozen seed means. The dashed line marks the nominal 1% pooled target, which constrains the pooled rate, not each phase. Evidence IDs are listed in Table 2.

**Fig. 3.** Between-phase disparity and nominal calibration error at the 1% target under pooled (P), retrospective phase-conditioned (C), past-only regime-conditioned (C′) and continuous contextual (Q) calibration; one grey line per detector run. Panels (a–c) are row-pooled over audit engines, and panel (d) weights audit engines equally. All paired arm-minus-P bootstrap intervals include zero.

**Fig. 4.** Detection delay at matched healthy-flight false-flag burden (1% row target). (a, b) Paired lower-median per-engine delay difference (arm minus P, flights) at each matched realized false-flag rate, for supported anchors only (within one healthy-flight step), without interpolation; negative values mean earlier detection. Counts are in Table 4. (c) Realized pooled healthy-flight false-flag rate at the calibration-locked κ (P, C, C′) and at Q's calibration κ; the dashed line is the nominal 5% design rate.

**Fig. 5.** Per-engine transport at the 1% target: maximum nominal calibration error A2 of each audit engine for every detector run under P, C and Q. Shading and asterisks mark engines whose flight class is absent from that dataset's calibration set: class 1 in both subsets, and class 2 in DS02. DS02 calibration engines are class 3; DS03 calibration engines are classes 2 and 3.

**Fig. 6.** Operating context and support. (a) Pooled-threshold phase FPR within the calibration engines (in-sample; open markers) and in the audit engines (filled), one marker per detector run. (b, c) Median same-phase support distance against |FPR − α| under C for each audit engine × phase cell (mean over the seven runs), with the median per-run Spearman correlation. Descriptive; no p-values are computed.

## Tables

- **Table 1.** Datasets, engine partitions with flight classes, phase roles and calibration arms.
- **Table 2.** Frozen pooled-calibration audit at the 1% target: phase FPRs, contrasts and worst cross-phase transfer FPR, with evidence IDs. Isolation Forest and LSTM rows are frozen seed means.
- **Table 3.** Post-confirmation calibration quality at the 1% target (percentage points; range over the seven detector runs): between-phase disparity A1, maximum and RMS nominal error A2 and A3, overall-FPR error A5, the number of runs in which each arm is below P, and the equal-engine A2. All paired intervals include zero.
- **Table 4.** Detection delay at matched healthy-flight false-flag burden (1% row target). Anchor columns give earlier/tie/later run counts of the paired lower-median delay difference against P at supported anchors. The table also gives the pre-specified run labels (earlier/mixed/equal/later), the realized pooled false-flag rates at the locked κ, and the curve-level mean delay difference (flights).
- **Table 5.** Cross-engine transport at the 1% target: per-engine and equal-engine A2 ranges under P, C and Q, the number of runs in which C or Q is worse than P, and the C-against-P category counts. "Absent" marks a flight class not represented among that dataset's calibration engines.
