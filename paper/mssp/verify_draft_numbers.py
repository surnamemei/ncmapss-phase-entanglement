"""Re-derive every number cited in the MSSP manuscript and enforce its wording rules.

Sources:
- Frozen DS02/DS03 numbers: paper/manuscript_core_results.csv (unchanged evidence IDs). Every number in
  the frozen Sections 4.1-4.7 must also appear verbatim in the audited RESS text
  (paper/manuscript_submission.md).
- Post-confirmation numbers: results/mssp_mitigation/ (frozen protocol v1.0).
- Adversarial-validation numbers: results/mssp_adversarial/ (frozen plan).

Checks, in order:
1. Every re-derived value appears verbatim in paper/mssp/manuscript_mssp_draft.md. Structural claims
   (counts such as "14 of 14") are asserted against the outputs.
2. Reverse check: every decimal or percentage in the abstract, highlights and the post-confirmation
   Results, Discussion and Conclusion is either a re-derived value, a frozen value, or a design
   constant. No number can enter those sections without a source.
3. Frozen Sections 4.1-4.7 contain only numbers present in the audited RESS text.
4. Wording: forbidden terms (docs/mssp/FINAL_STORY_LOCK.md), placeholders, abstract length,
   highlight number and length, keyword count, and required locked sentences.
5. Citations: every cited key has a verified reference spec, and every spec key is cited.

No N-CMAPSS data are read. `--print` lists the values only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MIT = ROOT / "results/mssp_mitigation"
ADV = ROOT / "results/mssp_adversarial"
DRAFT = ROOT / "paper/mssp/manuscript_mssp_draft.md"
RESS_TEXT = ROOT / "paper/manuscript_submission.md"
CORE = ROOT / "paper/manuscript_core_results.csv"
SPEC = ROOT / "paper/mssp/references_spec.json"
ABSTRACT_WORDS = (200, 245)
HIGHLIGHTS = (3, 5)
HIGHLIGHT_CHARS = 85
KEYWORDS = (1, 7)
FORBIDDEN = ("pre-registered", "preregistered", "preregistration", "[ref:", "to verify]", "online", "causal regime",
             "causal-regime", "causal lstm", "causal arm", "causal conditioning", "non-inferior", "eliminates",
             "eliminate ", "deployment-ready", "fault sensitivity", "fault recall", "fault-state", "fault state",
             "independent confirmatory", "independent confirmation", "stabiliz", "robust ", "mitigation",
             "limiting factor", "transportable calibration fix", "significant", "significance", "universal",
             "fault-tolerant", "for the first time", "first to", "novel framework", "proves ", "proven",
             "{{", "}}", "[author to", "todo", "tbd", "xx ")
REQUIRED = ("the strongest observed transport failures coincided with flight classes absent from calibration",
            "abnormal-state ($hs = 0$)", "past-only LSTM", "retrospective phase-conditioned",
            "past-only regime-conditioned", "healthy flights with any alarm", "between-phase disparity",
            "nominal calibration error")
CONSTANTS = {"0.5%", "1%", "2%", "2.5%", "2.5", "5%", "10%", "15%", "20%", "0.95", "1.0", "0.001", "2.0", "90%", "85%"}
MINUS = "−"
DATASETS = ("ds02", "ds03")
ARMS = ("phase_conditioned", "causal_regime")


def signed(value, digits=2):
    return f"{value:+.{digits}f}".replace("-", MINUS)


def span(values, scale=100.0, digits=2, suffix=""):
    values = np.asarray(values, dtype=float) * scale
    return f"{values.min():.{digits}f}–{values.max():.{digits}f}{suffix}"


def mit(dataset, stage, table):
    return pd.read_csv(MIT / dataset / f"stage_{stage}" / f"{table}.csv", float_precision="round_trip")


def adv(dataset, folder, table):
    return pd.read_csv(ADV / dataset / folder / f"{table}.csv", float_precision="round_trip")


def require(condition, message):
    if not condition:
        raise SystemExit(f"Structural claim failed: {message}")


def frozen_values(items):
    core = pd.read_csv(CORE, dtype=str).set_index("manuscript_key")
    for key in ("D03-PCA-SINGLE-climb_fpr", "D03-PCA-SINGLE-cruise_fpr", "D03-PCA-SINGLE-descent_fpr",
                "D02-PCA-SINGLE-climb_fpr", "D02-PCA-SINGLE-cruise_fpr", "D02-PCA-SINGLE-descent_fpr"):
        row = core.loc[key]
        items.append((key, row.display_rounded_value, f"{row.evidence_id} (manuscript_core_results.csv)"))


def post_confirmation_values(items):
    reduced, intervals, with_zero, changes = 0, 0, 0, []
    for dataset in DATASETS:
        stab = mit(dataset, "d", "healthy_stability_by_scheme")
        pooled = stab[(stab.nominal_fpr == 0.01) & (stab.unit.astype(str) == "all")]
        by_run = pooled.pivot_table(index=["detector", "seed"], columns="scheme", values=["spread", "overall_fpr"])
        reduced += int((by_run["spread"]["phase_conditioned"] < by_run["spread"]["pooled"]).sum())
        require(int((by_run["spread"]["causal_regime"] < by_run["spread"]["pooled"]).sum()) == 7,
                f"{dataset}: C' reduces disparity in every run")
        changes += list(100 * (by_run["overall_fpr"]["phase_conditioned"] - by_run["overall_fpr"]["pooled"]))
        for scheme in ("pooled", "phase_conditioned", "causal_regime"):
            items.append((f"{dataset} {scheme} phase spread range (pp)", span(pooled[pooled.scheme == scheme].spread),
                          f"{dataset}/stage_d/healthy_stability_by_scheme.csv"))
        u1 = mit(dataset, "d", "u1_bootstrap_ci")
        ci = u1[u1.metric.isin([f"delta_spread.{s}" for s in ARMS])]
        intervals += len(ci)
        with_zero += int(((ci.ci_lower_95 <= 0) & (ci.ci_upper_95 >= 0)).sum())
    require(reduced == 14 and intervals == 28 and with_zero == 28, "spread reductions / intervals")
    items.append(("runs with lower phase-conditioned spread", "all 14 detector runs", "14 of 14"))
    items.append(("highlight count", "14/14 runs", "14 of 14"))
    items.append(("overall healthy FPR change C - P (pp)", f"{signed(min(changes))} to {signed(max(changes))}",
                  "healthy_stability_by_scheme.csv"))
    guard = pd.concat([mit(d, "e", "guardrails") for d in DATASETS], ignore_index=True)
    require(guard.guardrails_met.astype(bool).all(), "guardrails")
    ratio = guard.alarm_rate_ratio_all_post_onset
    items.append(("family abnormal-state alarm-rate ratio range", f"{ratio.min():.2f}–{ratio.max():.2f}", "guardrails.csv"))
    flags = pd.concat([mit(d, "e", "healthy_flight_false_flags_with_delay") for d in DATASETS], ignore_index=True)
    flags = flags[flags.nominal_fpr == 0.01]
    pooled_flags = flags[flags.unit.astype(str) == "all"].false_flag_rate
    items.append(("pooled healthy-flight false-flag range", span(pooled_flags, 100, 1, "%"), "false flags with delay"))
    engine = flags[flags.unit.astype(str) != "all"]
    worst = engine.loc[engine.false_flag_rate.idxmax()]
    require(str(worst.unit) == "14" and worst.dataset == "ds02", "57% engine is DS02 engine 14 (flight class 1)")
    items.append(("largest single-engine healthy-flight false-flag rate", f"{100 * worst.false_flag_rate:.0f}%",
                  f"{worst.dataset} engine {worst.unit}"))
    for dataset, n in (("ds02", "820,630"), ("ds03", "2,956,881")):
        record = json.loads((MIT / dataset / "stage_e/stage_e_record.json").read_text())
        require(f"{record['abnormal_rows_read']:,}" == n, f"{dataset} abnormal rows")
        items.append((f"{dataset} abnormal rows read once", n, "stage_e_record.json"))
    flights = [json.loads((MIT / d / "stage_l/mitigation_lock.json").read_text())["calibration_flights"] for d in DATASETS]
    items.append(("calibration flights behind kappa", f"{flights[0]} (DS02) or {flights[1]} (DS03)", "mitigation_lock.json"))
    audit = [int(mit(d, "b", "label_structure").query("role == 'audit'").healthy_flights.sum()) for d in DATASETS]
    items.append(("healthy audit flights N_h", f"$N_h$ = {audit[0]} in DS02 and {audit[1]} in DS03", "label_structure.csv"))


def label_structure_checks(items):
    """Flight-class composition statements (story lock, Amendment 1)."""
    absent = []
    for dataset in DATASETS:
        labels = mit(dataset, "b", "label_structure")
        present = set(labels[labels.role == "calibration"].flight_class)
        absent += [(dataset, int(u), int(c)) for u, c in labels[(labels.role == "audit")
                                                               & ~labels.flight_class.isin(present)][["unit", "flight_class"]].values]
        if dataset == "ds02":
            require(set(labels[labels.role != "audit"].flight_class) == {3}, "DS02 development engines are all class 3")
    require(absent == [("ds02", 14, 1), ("ds02", 15, 2), ("ds03", 12, 1), ("ds03", 14, 1)], f"absent-class engines {absent}")
    class_one = [a for a in absent if a[2] == 1]
    require(len(class_one) == 3, "three class-1 audit engines")
    items.append(("class-1 engines", "two of the three class-1 audit engines", "label_structure.csv + paired"))
    items.append(("abstract class-1 wording", "two of the three short-flight audit engines", "label_structure.csv"))


def adversarial_values(items):
    q = pd.concat([adv(d, "calibration_quality", "calibration_quality_metrics") for d in DATASETS], ignore_index=True)
    p = pd.concat([adv(d, "calibration_quality", "calibration_quality_paired") for d in DATASETS], ignore_index=True)
    q1 = q[(q.nominal_fpr == 0.01) & (q.unit == "all")]
    for dataset in DATASETS:
        for scheme in ("pooled", "phase_conditioned"):
            items.append((f"{dataset} {scheme} A2 range (pp)",
                          span(q1[(q1.dataset == dataset) & (q1.scheme == scheme)].max_abs_error), "A metrics"))
    pr = p[(p.weighting == "row_pooled") & (p.nominal_fpr == 0.01) & (p.arm == "phase_conditioned")]
    require(int((pr.diff_max_abs_error < 0).sum()) == 14, "A2 reduced in 14 runs")
    require(int((pr.diff_rms_error < 0).sum()) == 13, "A3 reduced in 13 runs")
    items.append(("A3 reduced by C, row-pooled, 1%", "13 of 14 runs", "calibration_quality_paired.csv"))
    ci = pd.concat([adv(d, "calibration_quality", "calibration_quality_u1_ci").assign(dataset=d) for d in DATASETS])
    ci = ci[ci.metric.str.startswith("diff_")]
    excl = (ci.ci_lower_95 > 0) | (ci.ci_upper_95 < 0)
    require(int(excl[ci.nominal_fpr == 0.01].sum()) == 0, "no paired interval excludes zero at 1%")
    other = ci.nominal_fpr != 0.01
    items.append(("paired intervals including zero at 0.5% and 2%",
                  f"{int((~excl[other]).sum())} of {int(other.sum())} paired U1 intervals", "calibration_quality_u1_ci.csv"))
    require(int((pr.diff_overall_abs_error < 0).sum()) == 4, "overall error improved in 4 runs")
    items.append(("overall-FPR error improved by C", "in only 4 of 14 runs", "calibration_quality_paired.csv"))
    cat = p[(p.weighting == "row_pooled") & (p.arm == "phase_conditioned")]
    ds02 = [int((cat[(cat.dataset == "ds02") & (cat.nominal_fpr == a)].category == 1).sum()) for a in (0.005, 0.01, 0.02)]
    ds03 = [int((cat[(cat.dataset == "ds03") & (cat.nominal_fpr == a)].category == 1).sum()) for a in (0.005, 0.01, 0.02)]
    require(ds02 == [7, 7, 7], f"DS02 category-1 counts {ds02}")
    items.append(("DS03 category-1 counts by target", f"{ds03[0]}, {ds03[1]}, and {ds03[2]} of 7 runs", "paired table"))
    ew = p[(p.weighting == "equal_engine") & (p.nominal_fpr == 0.01) & (p.arm == "phase_conditioned")]
    require(int((ew[ew.dataset == "ds02"].category == 4).sum()) == 5, "DS02 equal-engine category 4 in 5 runs")
    items.append(("DS02 equal-engine category 4 at 1%", "in 5 of 7 runs at 1%", "paired table (equal_engine)"))
    worse = int((ew[ew.dataset == "ds02"].diff_max_abs_error > 0).sum())
    items.append(("DS02 equal-engine A2 higher under C", f"higher than under P in {worse} of 7 runs", "paired (equal_engine)"))
    ds03_cat1 = int((ew[ew.dataset == "ds03"].category == 1).sum())
    require(int((ew[ew.dataset == "ds03"].diff_max_abs_error > 0).sum()) == 0, "DS03 equal-engine A2 never higher")
    items.append(("DS03 equal-engine category 1", f"category 1 in {ds03_cat1} of 7 runs and no run with a higher equal-engine A2",
                  "paired (equal_engine)"))
    engines = q[(q.nominal_fpr == 0.01) & (q.weighting == "per_engine")]
    paired_engine = p[(p.nominal_fpr == 0.01) & (p.weighting == "per_engine")]
    for dataset, unit in (("ds02", "14"), ("ds03", "12")):
        part = engines[(engines.dataset == dataset) & (engines.unit.astype(str) == unit)]
        for scheme in ("pooled", "phase_conditioned"):
            items.append((f"{dataset} engine {unit} A2 {scheme}", span(part[part.scheme == scheme].max_abs_error),
                          "per-engine metrics"))
        w = paired_engine[(paired_engine.dataset == dataset) & (paired_engine.unit.astype(str) == unit)
                          & (paired_engine.arm == "phase_conditioned")]
        require(int((w.diff_max_abs_error > 0).sum()) == 7 and int((w.diff_rms_error > 0).sum()) == 7,
                f"{dataset} engine {unit} worse in every run")
    e15 = engines[(engines.dataset == "ds02") & (engines.unit.astype(str) == "15")]
    w15 = paired_engine[(paired_engine.dataset == "ds02") & (paired_engine.unit.astype(str) == "15")
                        & (paired_engine.arm == "phase_conditioned")]
    require(int((w15.category == 1).sum()) == 7, "DS02 engine 15 improved (category 1) in every run")
    items.append(("DS02 engine 15 A2", f"from {span(e15[e15.scheme == 'pooled'].max_abs_error)} to "
                  f"{span(e15[e15.scheme == 'phase_conditioned'].max_abs_error)} pp", "per-engine metrics"))

    def worse_runs(dataset, unit, arm):
        w = paired_engine[(paired_engine.dataset == dataset) & (paired_engine.unit.astype(str) == unit)
                          & (paired_engine.arm == arm)]
        return int((w.diff_max_abs_error > 0).sum())
    require(worse_runs("ds03", "14", "phase_conditioned") == 3, "DS03 engine 14 worse in 3 runs")
    items.append(("DS03 engine 14 worse", "worsened in 3 of 7 runs", "paired per_engine"))
    items.append(("C' class-1 engines", f"for DS02 engine 14 in {worse_runs('ds02', '14', 'causal_regime')} of 7 runs and "
                  f"for DS03 engine 12 in {worse_runs('ds03', '12', 'causal_regime')} of 7", "paired per_engine"))
    items.append(("in-class engines worse", f"DS03 engine 10 (class 3) in {worse_runs('ds03', '10', 'phase_conditioned')} of 7 "
                  f"runs and DS03 engine 15 (class 2) in {worse_runs('ds03', '15', 'phase_conditioned')} of 7",
                  "paired per_engine"))
    worst_c = engines[(engines.scheme == "phase_conditioned")].max_abs_error.max()
    require(abs(100 * worst_c - 6.59) < 0.005, "largest per-engine A2 under C is 6.59 pp")
    den = pd.read_csv(ADV / "summary/denominator_audit.csv")
    agree = {d: den[(den.dataset == d) & den.check.str.contains("diff_max_abs_error|diff_rms_error")].agreeing.tolist()
             for d in DATASETS}
    items.append(("DS02 sign agreement A2/A3", f"{min(agree['ds02'])}–{max(agree['ds02'])} of 42", "denominator_audit.csv"))
    items.append(("DS03 sign agreement A2/A3", f"{min(agree['ds03'])}–{max(agree['ds03'])} of 42", "denominator_audit.csv"))
    burden = den[den.check.str.contains("healthy flights with any alarm") & den.check.str.contains("phase_conditioned")]
    require(int((burden.compared - burden.agreeing).sum()) > int(burden.compared.sum()) / 2,
            "'healthy flights with any alarm' and kappa FFR change in opposite directions in most runs")
    decomposition = pd.read_csv(ADV / "summary/post_plan_error_decomposition.csv")
    med = decomposition[decomposition.nominal_fpr == 0.01].groupby(["dataset", "scheme"])[["mse", "share_phase"]].median()
    for dataset in DATASETS:
        for scheme in ("pooled", "phase_conditioned"):
            items.append((f"{dataset} {scheme} phase share", f"{100 * med.loc[(dataset, scheme), 'share_phase']:.0f}%",
                          "post_plan_error_decomposition.csv"))
            items.append((f"{dataset} {scheme} equal-cell RMS", f"{100 * np.sqrt(med.loc[(dataset, scheme), 'mse']):.2f}",
                          "post_plan_error_decomposition.csv"))
    for dataset in DATASETS:
        effect = adv(dataset, "support_transport", "calibration_phase_effect")
        ins = effect[(effect.nominal_fpr == 0.01) & (effect.evaluation == "in_sample_pooled_tau")]
        require((ins.highest_phase == "descent").sum() == 7, f"{dataset} in-sample descent highest in 7 runs")
        items.append((f"{dataset} in-sample descent FPR", span(ins.descent_fpr, suffix="%"), "calibration_phase_effect.csv"))
        items.append((f"{dataset} in-sample climb FPR", span(ins.climb_fpr, suffix="%"), "calibration_phase_effect.csv"))
    both = pd.concat([adv(d, "support_transport", "calibration_phase_effect") for d in DATASETS])
    other = both[(both.evaluation == "in_sample_pooled_tau") & both.nominal_fpr.isin([0.005, 0.02])]
    cross = both[both.evaluation.str.startswith("cross") & (both.nominal_fpr == 0.01)]
    require(int((other.highest_phase == "descent").sum()) == 27 and len(other) == 28, "27 of 28 other targets")
    require(int((cross.highest_phase == "descent").sum()) == 27 and len(cross) == 28, "27 of 28 cross-engine")
    items.append(("descent highest at other targets and cross-engine", "27 of 28", "calibration_phase_effect.csv"))
    cells = pd.concat([adv(d, "support_transport", "support_cells") for d in DATASETS])
    class1 = cells[(cells.flight_class == 1) & (cells.phase == "cruise")]
    others = cells[~((cells.flight_class == 1) & (cells.phase == "cruise"))]
    items.append(("class-1 cruise support distance", span(class1.d_phase_median, 1), "support_cells.csv"))
    require(others.d_phase_median.max() < 0.07, "all other cells below 0.07")
    items.append(("other cells", "at most 0.07", "support_cells.csv"))
    items.append(("class-1 cruise outside range", span(class1.fraction_outside_phase_range, 100, 0, "%"), "support_cells.csv"))
    for dataset in DATASETS:
        assoc = adv(dataset, "support_transport", "support_associations")
        rho = assoc[assoc.nominal_fpr == 0.01].rho_dphase_vs_abs_error_C.median()
        items.append((f"{dataset} median rho", f"{rho:.2f} ({dataset.upper()})", "support_associations.csv"))
    summary = json.loads((ADV / "summary/summary_record.json").read_text())
    require(summary["support_verdict"] == "INDETERMINATE DUE TO SMALL ENGINE COUNT", "support verdict")
    matched_values(items)
    baseline_values(items)


def baseline_values(items):
    q = pd.concat([adv(d, "contextual_baseline", "baseline_calibration_quality") for d in DATASETS], ignore_index=True)
    a = pd.concat([adv(d, "calibration_quality", "calibration_quality_metrics") for d in DATASETS], ignore_index=True)
    fits = pd.concat([adv(d, "contextual_baseline", "baseline_fits") for d in DATASETS], ignore_index=True)
    require(set(fits.stride) == {5}, "baseline fitted on every fifth calibration row")
    require(all(len(c.split(";")) == 15 for c in fits.coefficients), "baseline has 14 terms plus an intercept")
    f1 = fits[fits.nominal_fpr == 0.01].calibration_row_alarm_rate
    items.append(("Q in-sample calibration alarm rate at 1%", span(f1, suffix="%"), "baseline_fits.csv"))
    both = pd.concat([a, q], ignore_index=True)
    pooled = both[(both.nominal_fpr == 0.01) & (both.unit == "all")].pivot_table(
        index=["dataset", "detector", "seed"], columns="scheme", values=["spread", "max_abs_error"])
    q_lt_p = int((pooled["spread"]["quantile_regression_W"] < pooled["spread"]["pooled"]).sum())
    q_lt_c = pooled["max_abs_error"]["quantile_regression_W"] < pooled["max_abs_error"]["phase_conditioned"]
    require(q_lt_p == 12, f"Q spread < P in {q_lt_p} runs")
    items.append(("Q reduces disparity vs P", "relative to P in 12 of 14 runs", "baseline + A metrics"))
    ds02 = int(q_lt_c.xs("ds02", level="dataset").sum())
    items.append(("Q A2 < C", f"in only {int(q_lt_c.sum())} of 14 runs ({ds02} of 7 on DS02)", "baseline + A metrics"))
    eng = both[(both.nominal_fpr == 0.01) & (both.weighting == "per_engine")]
    for dataset, unit in (("ds02", "14"), ("ds03", "12"), ("ds03", "10")):
        part = eng[(eng.dataset == dataset) & (eng.unit.astype(str) == unit) & (eng.scheme == "quantile_regression_W")]
        items.append((f"Q {dataset} engine {unit} A2", span(part.max_abs_error), "baseline per-engine metrics"))
    piv = eng[(eng.dataset == "ds03") & (eng.unit.astype(str) == "10")].pivot_table(
        index=["detector", "seed"], columns="scheme", values="max_abs_error")
    require(bool((piv["quantile_regression_W"] > piv["pooled"]).all()), "Q worse than P on DS03 engine 10 in every run")
    part = eng[(eng.dataset == "ds02") & eng.unit.astype(str).isin(["11", "15"]) & (eng.scheme == "quantile_regression_W")]
    items.append(("Q DS02 in-class maximum", f"up to {100 * part.max_abs_error.max():.2f} pp on engines 11 and 15",
                  "baseline per-engine metrics"))
    for dataset in DATASETS:
        ff = adv(dataset, "contextual_baseline", "baseline_flight_false_flags")
        ff = ff[(ff.nominal_fpr == 0.01) & (ff.unit.astype(str) == "all")]
        items.append((f"Q {dataset} FFR at calibration kappa", span(ff.false_flag_rate, 100, 1, "%"), "baseline flags"))


def matched_values(items):
    labels = pd.concat([adv(d, "matched_delay", "matched_labels") for d in DATASETS])
    labels = labels[labels.nominal_fpr == 0.01]
    earlier = {(d, a): int(((labels.dataset == d) & (labels.arm == a) & (labels.matched_label == "earlier at matched burden")).sum())
               for d in DATASETS for a in ARMS}
    items.append(("matched label C", f"{earlier[('ds02', 'phase_conditioned')]} of 7 DS02 runs and "
                                     f"{earlier[('ds03', 'phase_conditioned')]} of 7 DS03 runs", "matched_labels.csv"))
    items.append(("matched label C'", f"in {earlier[('ds02', 'causal_regime')]} and {earlier[('ds03', 'causal_regime')]} of 7 for C′",
                  "matched_labels.csv"))
    require(max(earlier.values()) < 5, "pre-specified delay criterion (>= 5 of 7) not met")
    c = labels[labels.arm == "phase_conditioned"]
    lower = {d: int((c[c.dataset == d].curve_mean_difference < 0).sum()) for d in DATASETS}
    require(lower["ds02"] == lower["ds03"], "curve-mean counts equal across datasets")
    items.append(("curve-level mean", f"lower for C than for P in {lower['ds02']} of 7 runs on each dataset", "matched_labels.csv"))
    locked = labels.locked_pareto.value_counts()
    require(int(locked.get("trade-off", 0)) > len(labels) / 2, "most locked comparisons are trade-offs")
    m = pd.concat([adv(d, "matched_delay", "matched_false_flag_comparisons") for d in DATASETS])
    m = m[(m.rule == "nearest") & (m.nominal_fpr == 0.01) & (m.arm == "phase_conditioned") & m.supported]

    def anchor(dataset, a):
        part = m[(m.dataset == dataset) & (m.anchor_ffr == a)]
        d = part.paired_lower_median_difference
        return int((d < 0).sum()), int((d > 0).sum()), len(part), float(np.median(d))
    e, l, n, med = anchor("ds02", 0.05)
    require((e, l, n) == (7, 0, 7), f"DS02 5% anchor {e, l, n}")
    items.append(("DS02 5% anchor", f"7 of 7 runs at 5% (median paired difference {MINUS}{abs(med):.0f} flights)",
                  "matched comparisons"))
    high = pd.concat([adv(d, "matched_delay", "matched_false_flag_comparisons") for d in DATASETS])
    high = high[(high.rule == "nearest") & (high.nominal_fpr == 0.01) & high.supported & (high.anchor_ffr >= 0.10)]
    top = int(max(high.pooled_median_delay.max(), high.arm_median_delay.max()))
    items.append(("max median delay at anchors >= 10%", f"median delays were at most {top} flights in every arm",
                  "matched comparisons"))
    e, l, n, _ = anchor("ds02", 0.025)
    items.append(("DS02 2.5% anchor", f"{e} of {n} supported runs at 2.5%", "matched comparisons"))
    require(l == 0 and e == n, "DS02 2.5% anchor all earlier")
    e, l, n, _ = anchor("ds03", 0.025)
    items.append(("DS03 2.5% anchor", f"Earlier in {e} of {n} runs at 2.5% (one later)", "matched comparisons"))
    require(l == 1, "DS03 2.5% one later")
    e, l, n, _ = anchor("ds03", 0.05)
    items.append(("DS03 5% anchor", f"{e} of {n} supported runs at 5% (one later)", "matched comparisons"))
    require(l == 1, "DS03 5% one later")
    grid = np.round(np.arange(0.025, 0.20 + 1e-9, 0.0025), 6)
    items.append(("curve grid size", f"({len(grid)} points)", "plan: 2.5-20% in 0.25-pp steps"))


def section(text, start, end=None):
    body = text.split(start, 1)[1]
    return body.split(end, 1)[0] if end else body


def derived_items():
    items = []
    frozen_values(items)
    post_confirmation_values(items)
    label_structure_checks(items)
    adversarial_values(items)
    return items


def numbers(text):
    return set(re.findall(r"[+−-]?\d+(?:\.\d+)?%?", text))


def reverse_check(draft, items):
    """Every decimal or percentage in the post-confirmation parts must have a source."""
    known = set()
    for _, value, _ in items:
        known |= {n.lstrip("+−-") for n in numbers(value)}
    core = pd.read_csv(CORE, dtype=str)
    for value in core.display_rounded_value.dropna():
        known |= {n.lstrip("+−-") for n in numbers(value)}
    known |= {c.lstrip("+−-") for c in CONSTANTS}
    parts = [section(draft, "## Abstract", "**Keywords:**"), section(draft, "**Highlights", "## 1."),
             section(draft, "### 4.8 ", "## Data availability")]
    missing = set()
    for part in parts:
        part = "\n".join(line for line in part.splitlines() if not line.startswith("#"))
        part = re.sub(r"(Supplementary )?(Tables?|Figs?\.?|Figures?|Sections?) S?\d+(\.\d+)*([–,-]S?\d+(\.\d+)*)?", "", part)
        part = re.sub(r"\[N?\d+\]", "", part)
        for token in numbers(part):
            bare = token.lstrip("+−-")
            if ("." in bare or "%" in bare) and bare not in known:
                missing.add(token)
    return sorted(missing)


def text_checks(draft):
    problems = []
    lowered = draft.lower()
    body = re.sub(r"<!--.*?-->", "", draft, flags=re.S).lower()
    for term in FORBIDDEN:
        pattern = re.escape(term.strip())
        if term[0].isalnum():
            pattern = r"\b" + pattern
        if term[-1].isalnum() or term.endswith(" "):
            pattern += r"\b"
        if re.search(pattern, body):
            problems.append(f"forbidden or placeholder text present: {term!r}")
    problems += [f"required locked wording missing: {t!r}" for t in REQUIRED if t.lower() not in lowered]
    abstract = section(draft, "## Abstract", "**Keywords:**")
    words = len(abstract.split())
    print(f"abstract: {words} words (limit {ABSTRACT_WORDS[1]})")
    if not ABSTRACT_WORDS[0] <= words <= ABSTRACT_WORDS[1]:
        problems.append(f"abstract has {words} words")
    if "calibration-set composition across flight classes is the limiting factor" in abstract:
        problems.append("superseded abstract sentence present")
    highlights = [l[2:] for l in section(draft, "**Highlights", "## 1.").splitlines() if l.startswith("- ")]
    if not HIGHLIGHTS[0] <= len(highlights) <= HIGHLIGHTS[1]:
        problems.append(f"{len(highlights)} highlights")
    problems += [f"highlight longer than {HIGHLIGHT_CHARS} characters: {h}" for h in highlights if len(h) > HIGHLIGHT_CHARS]
    keywords = [k for k in section(draft, "**Keywords:**").splitlines()[0].split(";") if k.strip()]
    if not KEYWORDS[0] <= len(keywords) <= KEYWORDS[1]:
        problems.append(f"{len(keywords)} keywords")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    cited = set()
    for a, b, c, d in re.findall(r"\[(N?)(\d+)\]–\[(N?)(\d+)\]", draft):
        cited.update(f"{a}{k}" for k in range(int(b), int(d) + 1))
    cited.update(re.findall(r"\[(N?\d+)\]", re.sub(r"<!--.*?-->", "", draft, flags=re.S)))
    cited = {k if k.startswith("N") else f"ref{k}" for k in cited}
    print(f"references: {len(spec)} in the verified spec; {len(cited)} cited")
    if cited - set(spec):
        problems.append(f"cited but not in the verified reference spec: {sorted(cited - set(spec))}")
    if set(spec) - cited:
        problems.append(f"verified but never cited: {sorted(set(spec) - cited)}")
    frozen = section(draft, "### 4.1 ", "### 4.8 ")
    frozen = "\n".join(line for line in frozen.splitlines() if not line.startswith("#"))
    frozen = re.sub(r"(Supplementary )?(Tables?|Sections?|Figs?\.) S?\d+(\.\d+)*([–-]S?\d+(\.\d+)*)?", "", frozen)
    ress = RESS_TEXT.read_text(encoding="utf-8")
    values = set(re.findall(r"[+−]?\d+\.\d+%?", frozen))
    missing = sorted(n for n in values if n not in ress)
    print(f"frozen sections: {len(values)} numbers checked against the RESS text")
    if missing:
        problems.append(f"frozen-section numbers not found in the RESS text: {missing}")
    for n in range(1, 7):
        if not re.search(rf"Figs?\. (\d+[a-z,–]* ?)*{n}(?![0-9])", section(draft, "## 1.", "## Figures (captions)")):
            problems.append(f"Fig. {n} never referenced in the text")
        if len(re.findall(rf"^\*\*Fig\. {n}\.\*\*", draft, flags=re.M)) != 1:
            problems.append(f"Fig. {n} caption missing or duplicated")
    for n in range(1, 6):
        if not re.search(rf"Tables? (\d+[,–] ?)*{n}(?![0-9])", section(draft, "## 1.", "## Figures (captions)")):
            problems.append(f"Table {n} never referenced in the text")
        if len(re.findall(rf"\*\*Table {n}\.\*\*", draft)) != 1:
            problems.append(f"Table {n} caption missing or duplicated")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", action="store_true", dest="print_only")
    args = parser.parse_args()
    items = derived_items()
    draft = DRAFT.read_text(encoding="utf-8")
    missing = []
    for label, value, source in items:
        present = value in draft
        if not present:
            missing.append(value)
        print(f"{'ok ' if present else '-- '} {value!r:<62} {label} <- {source}")
    if args.print_only:
        return
    problems = text_checks(draft)
    unsourced = reverse_check(draft, items)
    print(f"reverse check: {'all numbers sourced' if not unsourced else unsourced}")
    if unsourced:
        problems.append(f"numbers without a derived or frozen source: {unsourced}")
    if missing:
        problems.append(f"{len(missing)} value(s) not found verbatim in the draft: {missing}")
    if problems:
        sys.exit("\n".join(problems))
    print(f"All {len(items)} cited values re-derived and found verbatim; text checks passed.")


if __name__ == "__main__":
    main()
