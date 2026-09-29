# Novelty positioning (final prior-art audit)

**Date.** 2026-09-28.

**Scope.** This file re-audits the closest literature, not the broad background. Every row, with its full citation, DOI, the claim it supports, feature flags, overlap, difference and a keep/drop decision, is in `reference_audit.csv`. Evidence for the newly examined works is in `literature_evidence/`.

**Rule.** Claims below are limited to what was read. Each entry states its access level, and an access level of "abstract only" means the full text could not be legally obtained.

## Closest prior work: what each study does, overlap, and non-overlap

| Work | Access | What it does | Overlap with this study | Not overlapping |
| --- | --- | --- | --- | --- |
| Zhao et al. 2004 [N8] (multimode PCA) | abstract | Multiple PCA models, each with its own control limit, reduce false alarms that a single-mode model raises in other normal modes | Mode-specific control limits for PCA residuals, motivated by false alarms | Steady-state chemical-process modes. No transport across units, no delay at matched false-alarm burden, no frozen confirmation |
| Toshkova et al. 2020 [N22] (MSSP) | abstract | Extreme-value alarm thresholds per identified operating condition give a more reliable health indication than uniform thresholds | Per-condition alarm thresholds in this journal | The abstract reports no per-condition healthy FPR, no cross-condition transfer, no delay and no cross-unit transport |
| Michau and Fink 2021 [N23] | journal abstract and full text of the arXiv version (2008.07815v2) | Report FPR for five operating modes of simulated turbofan data. A cruise-only calibration flags all data from the other modes (100% FPR). The remedy is cross-unit transfer learning | Per-mode FPR and failure of a single-context calibration in other contexts | The failure is trivial because the source never saw the other modes. There is no pooled-versus-per-phase calibration audit with every phase present, no engine-level calibration transport and no frozen confirmation |
| Simon et al. 2014, ProDiMES [N24] | journal abstract and full text of the NASA technical-memorandum version | Blind hold-out benchmark with a fixed flight-level false-alarm target (at most 1 in 1000 flights) and joint reporting of detection rate and latency | Fixing false-alarm burden before comparing latency; blind hold-out evaluation | Snapshot data, not full-flight time series. Detection-method benchmarking, with no calibration-transport question |
| Lee et al. 2025 [N26] | abstract | Flight-state-aware threshold re-estimation for rotorcraft HUMS lowers the background alarm rate (0.202 to about 0.030) while keeping the in-window alarm concentration | Flight-state-specific thresholds judged jointly by alarm burden and usefulness | In-service rotorcraft vibration indicators. No transport audit across aircraft and no frozen confirmation |
| Wang et al. 2025 [N25] | abstract | Segments aero-engine flights into flight-condition scenes, builds a monitor per condition set and reports a lower FAR | Flight-condition-specific aero-engine monitoring | No nominal-FPR calibration, per-condition healthy FPR, cross-condition transfer or confirmation |
| Clifton et al. 2007 [N27] | abstract | Shaft-speed-binned novelty thresholds for jet-engine vibration | Operating-bin thresholds for engines | No FPR-by-bin audit and no transfer analysis |
| Zhao et al. 2022 [6] | abstract | KDE-EWMA adaptive thresholds over flight-envelope subareas | Condition-dependent adaptive aero-engine thresholds | Threshold method; no calibration-transport audit |
| Nejjar et al. 2024 [N28] | abstract | On N-CMAPSS, flight phases differ between flight classes; phase-wise alignment matters for RUL transfer across flight-class sub-fleets | Same benchmark; flight class as a source of shift | RUL prediction, not false-alarm calibration |
| Chen et al. 2026 [N38] (RESS 267:111894) | **full text** (publisher PDF supplied by the author, 2026-09-28; 9 quotes machine-checked, `extension_fulltext_quotes.json`) | A conditional VAE with self-attention takes operating-condition variables as conditional inputs, modelling equipment state and operating conditions separately, and thresholds its log reconstruction probability once, at a 95% kernel-density bound. It states that variable operating conditions cause multiple-pattern normality and that models trained across them "cannot provide a universal HI threshold applicable to all conditions" | Operating-condition conditioning of the detector; the same 4 descriptors and 14 sensors on N-CMAPSS; explicit statement that a universal threshold across operating conditions fails | On N-CMAPSS only the six DS02 development units (all class 3) are used, with test engines U5 and U16 also contributing training cycles; the evaluation is HI–degradation correlation. There is no per-condition healthy FPR, no engine-disjoint calibration/audit, no cross-engine transport and no confirmation. **The earlier withdrawal of the "no universal threshold" note is reversed: the full text supports it (p. 3).** |
| Asaadi et al. 2022 [N39] (J. Process Control 114:120–130) | **abstract, highlights and section snippets** (Internet Archive copy of the publisher page) | Assesses univariate alarm systems over time for a process variable with an intermittent fault, modelled by time-variant finite mixtures, using FAR, MAR and averaged alarm delay for deadband and moving-average designs (Monte Carlo) | Joint false-alarm and delay indices; non-stationary, mixture-type behaviour of the monitored variable | The mixture describes a fault that alternates with normal behaviour, not normal operating contexts. Univariate alarms, with no calibration transport across units |
| Asaadi et al. 2025 [N40] (J. Process Control 155:103536) | **full text** (publisher PDF supplied by the author, 2026-09-28; 7 quotes machine-checked) | Operational zone-specific alarm design: change-point segmentation into normal, rising, fault and return-to-normal zones, with time-variant FAR, MAR and average alarm delay. Deadband, filtering and delay-timer policies change these indices, and stationary averaging is criticized as misleading (Monte Carlo; Tennessee Eastman) | Zone-specific alarm design with joint FAR, MAR and delay; explicit rejection of stationarity; persistence and delay-timer policies as design levers | The "zones" are stages of fault progression and recovery in one variable, not exogenous operating contexts. There are no multiple units and no cross-unit calibration transport |
| Diallo et al. 2025 [N41] (J. Process Control 152:103495) | **title and the first author's open thesis abstract** (HAL tel-05503471) | Compares conformal and classical threshold setting for PCA and autoencoder fault detectors to reduce false alarms | Calibrating reconstruction-detector thresholds for false-alarm control | A threshold-method comparison; no phase-conditional or transport audit |
| Hsu, Frusque and Fink 2023 [N42] (PHM Society) | full text | Residual-based detectors on N-CMAPSS (DS04/05/07) with a threshold from healthy data, compared by unit-level false positives and detection delay. **Cruise only**, "as it exhibits a more stable behavior in comparison to the take-off or landing phases" | Same benchmark and detector family; joint false-positive and delay reporting; restricting to cruise implicitly acknowledges phase-dependent healthy behaviour | No phase-wise FPR, no cross-phase transfer, unit-level (not nominal row-level) FPR, all units used in training, no held-out confirmation and no transport analysis. **Consequence:** no claim that false-positive and delay evaluation on N-CMAPSS is new |
| Zhong et al. 2026 [N43] (Scientific Reports, in press) | full text | For an aviation piston engine (ECU intake data), detection performance under one global threshold is reported per power-lever phase; climb is worst. Phase-adaptive thresholds and cross-engine transfer are named as future work | Phase-dependent detector behaviour under a single threshold on aero-engine flight data | F1 on mixed normal/fault windows, not healthy FPR against a nominal calibration target. No calibration audit, transfer matrix, held-out confirmation or transport evaluation. **Consequence:** phase dependence of detector behaviour is not claimed as a new observation; the calibration framing and the transport audit are |
| Farouq et al. 2021 [N44] (Neurocomputing) | thesis account of the article (full article not accessed) | In heterogeneous fleets, operational heterogeneity can make fleet-level models inefficient at individual units, so each unit is compared with a similar sub-fleet using Mondrian conformal detection with a bounded false-alarm probability | Conceptually the closest precedent for the transport finding | District-heating substations, heterogeneity between units rather than phases, and no nominal-FPR audit per operating phase. **Consequence:** the transport result is stated as specific to per-phase false-alarm calibration across engines, not as the general idea that fleet models may not transfer |
| Steland, Rafajłowicz and Rafajłowicz 2024 [N45] (Statistica Neerlandica 79(1):e12352, 2025) | abstract only | Thresholds that depend on discrete environments, with two-stage designs that distribute the false-alarm budget over an a priori partition | Statistical precedent for arm C (environment-specific thresholds under a false-alarm budget) | Statistical theory; no transport across units and no held-out confirmation |
| Steland 2026, arXiv:2609.26652 (**preprint, not cited**) | full text (preprint) | Adapts the threshold of any threshold-type monitoring rule to a context covariate, keeping the false-alarm rate fixed, with estimation theory; example on credit scoring | Context-adaptive thresholds with a false-alarm constraint: the statistical counterpart of arm C | Not peer reviewed (posted 22 September 2026). A method, with no engine data and no transport or confirmation audit. Recorded here so that it is not overlooked |

**Two broader bodies of prior art** also bound the claim:
- **Environmental and operational variability.** Sohn 2007 [N2], Deraemaeker et al. 2008 [N5], Avendaño-Valencia et al. 2020 [N4], Worden and Cross 2018 [N6] and Schmidt et al. 2018 [N3] establish that operating conditions must be normalized or modelled.
- **Calibration validity.** The conformal and exchangeability literature — Vovk 2013 [N7], Bates et al. 2023 [N16], Foygel Barber et al. 2023 [N20] and Tibshirani et al. 2019 [N30] — and adapted-threshold monitoring theory [N45] establish that marginal calibration does not imply conditional or transported validity, and that environment-specific thresholds can be calibrated under a false-alarm budget.

## 1. What is definitely prior art?

- **Condition- and context-specific thresholds.** Examples are mode-specific control limits [N8], per-condition alarm thresholds [N22], operating-bin, flight-condition and flight-state thresholds [N25]–[N27], adaptive thresholds over the flight envelope [6], zone-specific alarm design [N40], environment-specific thresholds under a false-alarm budget [N45], category-conditional conformal calibration [N7], and CFAR adaptation [N10].
- **Condition-aware detection models and operating-condition normalization.** See [N2]–[N6], [N13], [N38] and [3]–[5].
- **Phase- or mode-dependent detector behaviour.** Per-mode false-positive rates, including the failure of a single-context calibration in other contexts [N23]; per-phase detection metrics under one global threshold on aero-engine data [N43]; and restricting N-CMAPSS evaluation to cruise because other phases are less stable [N42].
- **Joint false-alarm and delay evaluation.** Fixed false-alarm budgets before latency comparisons [N17], [N24]; FAR/MAR/AAD alarm design, including for non-stationary process variables [N32], [N39], [N40]; and false-positive plus delay reporting for residual detectors on N-CMAPSS [N42].
- **Theory.** Marginal calibration does not guarantee conditional validity [N7], [N12], and calibration guarantees rest on exchangeability [N16], [N20], [N30].
- **Transfer across units and domains.** Cross-unit transfer and domain adaptation of monitoring models [N21], [N23], [N28], [N37], and the inefficiency of fleet-level normal models at heterogeneous individual units [N44].
- **Confirmatory methodology** [N33], and blind hold-out benchmarking [N24].

## 2. What is not our novelty?

- phase-aware or context-aware detection;
- regime-, zone- or condition-specific thresholds, and adaptive thresholds;
- the observation that operating variability affects monitoring statistics;
- the principle that delay must be compared at a fixed false-alarm burden;
- the theory that marginal calibration does not imply conditional or transported validity;
- the detectors (PCA, Isolation Forest, LSTM) and the residualization.

None of these is claimed.

## 3. What exact empirical and methodological contribution remains?

> The contribution is not phase-aware detection or regime-specific thresholding themselves. It is the controlled audit of nominal healthy-FPR calibration transport under full-flight operation, including cross-phase threshold transfer, a frozen discovery–confirmation separation, and a post-confirmation demonstration that apparent pooled phase-level correction need not transport across engines.

This audit comprises four parts:
1. **Pooled calibration and cross-phase transfer.** It quantifies, on full-flight engine residuals with three detector families, that a pooled nominal threshold controls only the exposure-weighted healthy FPR while climb, cruise and descent differ. Cross-phase threshold transfer is an endpoint, with every phase present in calibration.
2. **Frozen confirmation.** The pooled directional pattern discovered on one subset was reproduced by a frozen, one-shot evaluation on held-out engines of another.
3. **Post-confirmation transport audit.** Here we show, with every negative result retained, that per-phase thresholds which fix the pooled phase-composition error do not transport reliably to individual engines:
   - the strongest failures fall on engines of a flight class absent from calibration;
   - equal-engine weighting reverses the pooled improvement on one subset;
   - there is no general delay advantage at matched false-flag rates;
   - a continuous contextual baseline fails on other engines;
   - operating-support distance does not explain the failures.
4. **Evaluation protocol.** Nominal calibration error, between-context disparity, engine-weighted summaries and matched false-flag delay are reported together, under frozen plans with exact reproduction gates.

We did not find this combination in the documented search. That is a search result, not a systematic-review finding.

## 4. Is any "first" claim defensible?

**No.** Every ingredient has precedents (Section 1), and the search was documented but not systematic. "First" and its equivalents ("novel framework", "for the first time") are forbidden by the manuscript checker.

## 5. What wording is safest?

- **Safest.** "The contribution is not phase-aware detection or regime-specific thresholding. It is a controlled audit of nominal healthy-FPR calibration and its transport under full-flight operation."
- **For the gap.** "In a documented search we did not find a study that combines …", followed by the four elements.
- **Name the closest precedents in the text.** In the manuscript these are Zhao et al. [N8], Toshkova et al. [N22], Michau and Fink [N23], ProDiMES [N24], Lee et al. [N26], Hsu et al. [N42], Zhong et al. [N43], Farouq et al. [N44], Asaadi et al. [N39], [N40] and Chen et al. [N38]. Each is discussed substantively in Section 2.2 or 5.5, not only listed.
- **Avoid:**
  - "we propose phase-conditioned thresholds";
  - any claim that context-conditioned calibration is superior;
  - "novel", "first", "pioneering";
  - any priority claim for the transport concept itself, which follows from [N20], [N21], [N30].

## Verification limits

- **Update (extension, 2026-09-28): Chen 2026 [N38] and Asaadi 2025 [N40] have now been read in full** (`docs/extension/PRIOR_ART_EXTENSION.md`; 16/16 quotes verified). Neither contains a cross-unit calibration-transport evaluation, so the novelty wording stands. **Diallo 2025 [N41] is still not read in full.** It rests on the title and the thesis abstract, and reading it remains an author action before submission.
- **Asaadi 2022 [N39]** was checked from the publisher abstract, highlights and section snippets in an Internet Archive copy.

## Considered but not cited

The delegated search also identified related work that was verified but not cited. It was left out because the manuscript is at the 25-page limit and these works add no distinct point beyond the cited precedents:
- **Raymond et al. 2025** (Wind Energy 28(9):e70050). Wind-turbine normal-behaviour models carried to farms not used in training, with the threshold re-set per case to FPR = 5%, so the model transports but the calibrated threshold is not tested.
- **Laguna et al. 2026** (J. Phys. Conf. Ser. 3224:062054). Conformal calibration per wind-turbine cluster, with coverage below nominal, attributed partly to calibration-to-test shift.
- **Aslansefat et al. 2020** (ISA Transactions 97:282–295). Variable-threshold alarm systems assessed by FAR, MAR and average alarm delay.
- **Miao et al. 2024** (Sensors 24(3):941). Gas-turbine reconstruction errors adjusted per operating-condition category before one threshold.

Their records, quotes and screening reasons are in `literature_evidence/final_audit_records.json` and `literature_evidence/final_audit_screening_log.txt`. The author may add any of them if space allows.

