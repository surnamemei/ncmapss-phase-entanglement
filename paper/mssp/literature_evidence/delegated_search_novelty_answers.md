# Prior-art novelty answers (MSSP phase-dependent false-alarm calibration paper)

## How to read this file

- **Evidence keys** in `code` refer to `lit/agent_candidates.json`. Every content claim attributed to them comes from a
  quote in that file.
- **Quote checks:** each quote was machine-checked against the saved source text in `lit/raw2/quote_check.txt`
  (97/97 fragments matched).
- **[PV] = parent-verified.** These references were already on the caller's verified list. For them I only restate the
  claim text in the caller's own `lit/base_rows.py`; I did not re-verify them.

**Search coverage:**
- Crossref (all venues, plus an MSSP-filtered search), OpenAlex and Semantic Scholar
- arXiv abstract pages, HAL, RePEc/IDEAS and NASA NTRS
- DCASE proceedings, and PHM Society venues (the conference and IJPHM)
- Google Patents, the FAA document library, and general web search

**Blind spots:**
- ScienceDirect, MDPI HTML/PDF, IEEE Xplore full texts and SSRN blocked automated access.
- Five items were checked for metadata only (verified=false): `adnan2011_jpc`, `adnan2013_generalized`,
  `shimodaira2000_covshift`, `chen2026_universalthreshold` and `asaadi2022_mixture`.
- Two of these, `chen2026_universalthreshold` and `asaadi2022_mixture`, could bear directly on Q1 and Q2. The author
  should read them before submission, together with Diallo 2025 J. Process Control (your X5).

---

## Q1. Has phase/regime-dependent false-alarm calibration already been directly studied?

**Partly. Mode- or condition-specific thresholds and condition-dependent false alarms are well established. A per-flight-phase audit of a nominal pooled threshold was not found.**

**Mode- and condition-specific thresholds already exist, including in MSSP and for aero-engines:**
- Mode-specific control limits:
  - [PV] Zhao 2004: "single-mode monitoring triggers continuous warnings in other normal modes; mode-specific PCA models with own control limits reduce false alarms".
  - [PV] Quiñones-Grueiro 2019 reviews multimode monitoring.
  - `lu2004_subpca` uses phase- (stage-) specific models for batch processes.
- Aero-engine and aviation thresholds:
  - [PV] Zhao/Guo/Sun 2022: "adaptive aero-engine fault-detection thresholds over flight-envelope subareas".
  - `clifton2007_speedbins`: jet-engine vibration thresholds are set per shaft-speed bin.
  - `wang2025_maneuver` (RESS): aero-engine monitoring per flight-condition scene, with lower FAR.
  - `ge2020_patent_phasethresholds`: phase-specific severity thresholds for takeoff, climb, cruise and descent (a patent).
- Condition-wise thresholds in MSSP and rotorcraft practice:
  - `toshkova2020_evt` (MSSP): GEV thresholds per operating condition beat "uniform threshold levels".
  - `lee2025_hums`: flight-condition-agnostic HUMS thresholds cause "frequent false alarms".
  - [PV] Noura & Wiig: flight-stage normalisation of HUMS indicators.
- Radar: [PV] Rohling 1983 and Gandhi & Kassam 1988 on CFAR under non-homogeneous backgrounds.

**Condition-dependent score distributions are documented:**
- `wilkinghoff2025_dcase` and `dohi2022_dcase`: in acoustic machine monitoring, optimal thresholds "differ substantially" across operating domains.
- `miao2024_gasturbine`: gas-turbine reconstruction errors differ across operating conditions.
- `michau2021_utl`: FPR reported per flight operating mode on simulated AGTF30 turbofan data.

**The theory is established:**
- [PV] Vovk 2013: a 5% overall error rate "may be 10%/0% by group".
- [PV] Foygel Barber 2021, plus `gibbs2025_conditional` and `romano2020_equalized`.

**Not found in this search:** a study that did all of the following, on full-flight engine residuals:
- calibrated a single pooled threshold to a nominal false-alarm probability;
- showed that this controls only the exposure-weighted healthy FPR;
- reported the per-phase (climb/cruise/descent) healthy-FPR disparity as a primary result.

## Q2. Has cross-regime threshold transfer already been a primary endpoint?

**Partly. Failure of single-mode or single-regime calibration in other modes has been reported, including on simulated turbofan flight modes. A per-phase threshold transfer matrix with all phases present in calibration was not found.**

- **`michau2021_utl`** is the closest aero-engine precedent.
  - Its HELM detector has threshold = 1.2 × the 99.5th percentile of healthy high-altitude-cruise scores.
  - Trained on cruise only, it "detects all other operating modes as anomalous, which leads to 100% FPR".
  - Per-mode FPR is tabulated for take-off, both cruise levels, descent and landing.
  - Limitation: the source threshold never saw the other modes, and the paper's endpoint is the benefit of cross-unit alignment.
- **[PV] Zhao 2004** is the same phenomenon for process modes: single-mode models give continuous warnings in other normal modes.
- **DCASE work** makes the point in acoustic monitoring:
  - `dohi2022_dcase`: a source-domain model "performs poorly for a target domain", and the benchmark allows "only one threshold ... for all domains".
  - `wilkinghoff2025_dcase`: optimal thresholds differ across domains.
  - Both mostly use AUC/pAUC, not healthy FPR at a fixed threshold.
- **Transfer across units and conditions** is framed in [PV] Gardner 2020 (inferences may not transfer beyond the same system and operating conditions).
- **On N-CMAPSS**, transfer across flight classes has been an endpoint for RUL (`nejjar2024_opprofile`), not for alarm thresholds.
- **Not found in this search:** calibrating phase-specific thresholds with every phase present in calibration, then evaluating each threshold's healthy FPR on the other phases (uneven transfer) as a pre-specified primary endpoint for aero-engine residual detectors.

## Q3. Has a discovery -> frozen-confirmation audit been used for this question?

**Not for this question in aero-engine PHM. Related designs exist.**

- **`simon2014_prodimes`** (aero-engine gas-path benchmark):
  - Uses a blind test set whose ground truth is "retained by NASA".
  - Fixes a common false-alarm budget of at most one per 1000 flights before comparing methods.
  - This is a benchmark-owner hold-out, not discovery -> freeze -> one-shot confirmation by the same analyst, and it does not address phase-conditional calibration.
- **`mkrtchian2026_preprint`** (arXiv, not peer reviewed) is the closest design analogue found.
  - It pre-registers and freezes a per-domain, FPR-anchored calibration configuration before ground truth is released.
  - It is acoustic, a preprint, and has no delay or false-flag analysis.
- **General methodology:**
  - `wagenmakers2012_confirmatory`: "Only these analyses deserve the label 'confirmatory'".
  - `nosek2018_prereg`: preregistration, including for pre-existing data.
- **Not found in this search:** a DS02-discovery -> frozen-protocol -> one-shot DS03-confirmation audit of phase-dependent false-alarm calibration on N-CMAPSS or any aero-engine dataset.
- Following `wagenmakers2012_confirmatory`, the post-confirmation P/C/C' comparison should be labelled exploratory.

## Q4. Has stabilization been evaluated jointly with detection delay and false-flag burden?

**Joint reporting of delay and false alarms exists. Joint evaluation that also includes phase-disparity reduction was not found.**

Joint reporting of false alarms, missed alarms and delay is established:
- **Sequential detection theory:** [PV] Basseville & Nikiforov 1993 (delay minimised at a fixed mean time between false alarms), [PV] Fawcett & Provost 1999 (AMOC) and [PV] Miller 2021 MSSP (FPR vs delay tolerance).
- **Alarm systems:** `xu2012_farmaraad` (FAR, MAR and AAD) and `adnan2011_acc` (delay, FAR and MAR).
- **Engines:**
  - [PV] Borguet 2011: false-alarm-probability thresholds, with detection delay assessed.
  - [PV] Massé 2014: alert thresholds and repeated threshold crossings.
  - `simon2014_prodimes`: FPR, TPR and detection latency at a matched flight-level FPR.
- **Persistence rules:** `nogueira2026_persistence` shows persistence trades false positives against latency for IF, OCSVM, PCA and autoencoder detectors.
- **Aviation false-alarm burden:**
  - `lee2025_hums`: Background Alarm Rate reported with In-window Alarm Concentration.
  - `basora2021_fleet`: 1% FPR gives 110 alerts per 10 000 flights.
- **Other:**
  - `lavin2015_nab`: a streaming benchmark that scores earliness and false alarms jointly.
  - `michau2021_utl`: FPR and TPR must be jointly evaluated.
  - `miao2024_gasturbine`: raising the threshold cut false alarms but delayed detection.

**Not found in this search:** a study that evaluates the reduction of per-phase healthy-FPR disparity jointly with all of the following:
- overall healthy FPR;
- abnormal-state alarm rates;
- detection delay paired with the realized healthy-flight false-flag rate of a flight-level alarm rule.

No study was found that does this for aero-engines, nor that compares pooled, phase-conditioned and causal-regime threshold arms.

## Q5. What is actually novel after removing prior-art overlap?

The contribution is a specific audit and combination; no individual ingredient is new (see Q1–Q4). What was not found in this search:

1. **An empirical decomposition on full-flight simulated turbofan residuals.**
   - A nominal pooled threshold delivers its target FPR only as an exposure-weighted average, while healthy FPR differs across climb, cruise and descent.
   - This holds for three detector families.
   - The underlying theory is known ([PV] Vovk 2013, `gibbs2025_conditional`, `tibshirani2019_covshift`). The aero-engine full-flight quantification is what is new.
2. **Cross-phase transfer of phase-specific thresholds as a pre-specified endpoint, with all phases present in calibration.**
   - Closest precedents: `michau2021_utl` (cruise-only calibration) and [PV] Zhao 2004 (process modes).
3. **A protocol-frozen, one-shot confirmation on a second N-CMAPSS subset** for this calibration question.
   - Precedents: a benchmark blind test (`simon2014_prodimes`) and an acoustic preprint (`mkrtchian2026_preprint`).
4. **A joint mitigation assessment of the P, C and C' arms** across phase disparity, overall FPR, abnormal-state alarm rates, and delay paired with the realized healthy-flight false-flag rate.
   - Causal regime identification is not new (`simon2011_ssfilter`, `wang2025_maneuver`, `lee2025_hums`).
   - Condition-specific thresholds are not new ([PV] Zhao 2004, [PV] Zhao/Guo/Sun 2022, `toshkova2020_evt`).
   - The new element is their evaluation as calibration arms under this joint endpoint set, with delay never reported without the false-flag rate.

**Limitations to present as known concerns, not contributions:**
- Calibration-set composition: `marhadi2015_threshold`, `tibshirani2019_covshift`, [PV] Bates 2023 ("unlucky" calibration sets).
- Flight-class mix on N-CMAPSS: `nejjar2024_opprofile`.
- Engine heterogeneity and transportability: `king2009_assetspecific`, `fentaye2019_review`, `basora2021_fleet`, `dempsey2008_roc`, [PV] Gardner 2020.

**Wording advice (conservative):**
- Avoid "first".
- Use "we did not find a prior study that ...", or "to our knowledge ... has not been reported for full-flight aero-engine residual detectors".
- Name the closest precedents alongside the claim: `michau2021_utl`, `toshkova2020_evt`, `lee2025_hums`, `simon2014_prodimes`, [PV] Zhao 2004 and [PV] Zhao/Guo/Sun 2022.
- Do not present per-phase thresholds as a proposed method.
