# Abstract claim check

The Abstract contains no citations by design. Each numerical display below is copied from `paper/manuscript_core_results.csv`; its evidence ID resolves to `paper/evidence_ledger.csv`. Percentages are the core CSV's display-rounded row-FPR values, in climb/cruise/descent order.

| Abstract statement | Core manuscript keys | Evidence IDs | Required interpretation |
| --- | --- | --- | --- |
| Primary nominal 1% pooled calibration target | Primary pooled endpoint rows below | M0018 | Calibration target, not a guarantee of 1% FPR in each audit phase. |
| DS02 PCA: 0.125% / 0.428% / 3.459% | D02-PCA-SINGLE-climb_fpr; D02-PCA-SINGLE-cruise_fpr; D02-PCA-SINGLE-descent_fpr | E000107, E000108, E000109 | Exploratory, healthy row-level FPR under pooled threshold. |
| DS02 Isolation Forest seed mean: 0.268% / 0.558% / 2.487% | D02-IF-MEAN-climb_fpr; D02-IF-MEAN-cruise_fpr; D02-IF-MEAN-descent_fpr | E002627, E002628, E002629 | Arithmetic mean across tested seeds; no seed-mean bootstrap interval. |
| DS02 LSTM seed mean: 0.488% / 0.729% / 2.080% | D02-LSTM-MEAN-climb_fpr; D02-LSTM-MEAN-cruise_fpr; D02-LSTM-MEAN-descent_fpr | E002987, E002988, E002989 | Arithmetic mean across tested seeds; DS02 seed 0 reached the epoch ceiling. |
| Tested corrections did not eliminate DS02 phase dependence | D02-CORR-STATIC-descent_minus_climb; D02-CORR-STATIC-descent_minus_cruise; D02-CORR-DERIV-descent_minus_climb; D02-CORR-DERIV-descent_minus_cruise; D02-CORR-HISTORY-descent_minus_climb; D02-CORR-HISTORY-descent_minus_cruise | E021498, E021499, E021511, E021512, E021524, E021525 | Exploratory PCA comparison; not a DS03 correction comparison or causal explanation. |
| DS03 PCA: 0.877% / 0.912% / 1.977% | D03-PCA-SINGLE-climb_fpr; D03-PCA-SINGLE-cruise_fpr; D03-PCA-SINGLE-descent_fpr | E010947, E010948, E010949 | Frozen confirmation, healthy row-level FPR under pooled threshold. |
| DS03 Isolation Forest seed mean: 0.409% / 1.104% / 2.142% | D03-IF-MEAN-climb_fpr; D03-IF-MEAN-cruise_fpr; D03-IF-MEAN-descent_fpr | E012858, E012859, E012860 | Arithmetic seed mean; no seed-mean bootstrap interval. |
| DS03 LSTM seed mean: 0.751% / 1.889% / 2.215% | D03-LSTM-MEAN-climb_fpr; D03-LSTM-MEAN-cruise_fpr; D03-LSTM-MEAN-descent_fpr | E013131, E013132, E013133 | Arithmetic seed mean; no seed-mean bootstrap interval. |
| Frozen DS03 pooled directional pattern reproduced | D03-PCA-SINGLE-descent_minus_climb; D03-PCA-SINGLE-descent_minus_cruise; D03-IF-MEAN-descent_minus_climb; D03-IF-MEAN-descent_minus_cruise; D03-LSTM-MEAN-descent_minus_climb; D03-LSTM-MEAN-descent_minus_cruise | E010950, E010951, E012861, E012862, E013134, E013135 | Pre-specified pooled point-estimate rule only; not uniform engine-level replication. |
| Engine/seed heterogeneity and some LSTM descent-minus-cruise intervals including zero | Individual LSTM seed bootstrap rows in ledger; per-engine exception rows in ledger | E012043, E012316, E012589, E012536, E012550, E012576 | Individual-seed intervals, not an interval for the arithmetic seed mean. |

Nonquantitative Abstract wording remains bounded by `paper/introduction.md`, `paper/related_work.md`, and `paper/claim_audit.md`: no mechanism, deployment, detector-independence, or novelty claim is made.
