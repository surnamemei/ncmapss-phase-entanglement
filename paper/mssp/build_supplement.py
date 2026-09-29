"""Build the MSSP supplementary material (PDF) from frozen and committed outputs.

Every table is a formatted view of committed CSV values (fractions shown as percentages or
percentage points); nothing is recomputed from scores and no N-CMAPSS file is read. Sources:
- frozen DS02/DS03 outputs (results/phase3_dynamic_correction, results/final_validation,
  results/confirmation_ds03) and the frozen LSTM history figures in paper/submission/supplementary
  (included unchanged);
- post-confirmation outputs (results/mssp_mitigation, protocol v1.0);
- adversarial-validation outputs (results/mssp_adversarial, frozen plan).

Output: paper/mssp/supplement/{supplement.tex, supplement.pdf, tables/*.tex, figures/*}, plus
supplement.provenance.json listing the SHA-256 of every input and output. Machine-readable CSVs
remain in results/ and paper/mssp/evidence/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/mssp/supplement"
TAB, FIG = OUT / "tables", OUT / "figures"
MIT, ADV = ROOT / "results/mssp_mitigation", ROOT / "results/mssp_adversarial"
FV, CF = ROOT / "results/final_validation", ROOT / "results/confirmation_ds03"
FROZEN_SUPP = ROOT / "paper/submission/supplementary"
DATASETS = ("ds02", "ds03")
FAMILY = {"pca": "PCA", "isolation_forest": "IF", "lstm_autoencoder": "LSTM"}
ARM = {"pooled": "P", "phase_conditioned": "C", "causal_regime": "C$'$", "quantile_regression_W": "Q"}
PHASES = ("climb", "cruise", "descent")
SHORT = {"earlier at matched burden": "E", "later at matched burden": "L", "mixed": "M", "equal": "=",
         "not evaluable": "n/e"}
ANCHORS = (0.025, 0.05, 0.10, 0.15, 0.20)
TITLE = ("Phase-Dependent False-Alarm Calibration and Its Transport Across Engines in Full-Flight "
         "Aero-Engine Anomaly Detection")
INPUTS = set()

plt.rcParams.update({"font.size": 8.5, "axes.titlesize": 8.5, "axes.labelsize": 8.5, "legend.fontsize": 7.5,
                     "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42, "font.family": "DejaVu Sans"})


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def read(path):
    INPUTS.add(Path(path))
    return pd.read_csv(path, float_precision="round_trip")


def mit(dataset, stage, table):
    frame = read(MIT / dataset / f"stage_{stage}" / f"{table}.csv")
    return frame if "dataset" in frame.columns else frame.assign(dataset=dataset)


def adv(dataset, folder, table):
    frame = read(ADV / dataset / folder / f"{table}.csv")
    return frame if "dataset" in frame.columns else frame.assign(dataset=dataset)


def both(loader, *args):
    return pd.concat([loader(d, *args) for d in DATASETS], ignore_index=True)


def pct(x, digits=3):
    return "--" if pd.isna(x) else f"{100 * float(x):.{digits}f}"


def pp(x, digits=2):
    if pd.isna(x):
        return "--"
    value = 100 * float(x)
    return f"{value:+.{digits}f}".replace("-", "$-$")


def num(x, digits=2):
    if pd.isna(x):
        return "--"
    if np.isinf(x):
        return "cens."
    return f"{float(x):.{digits}f}".replace("-", "$-$")


def esc(text):
    """Escape free text from CSV cells for LaTeX."""
    text = str(text)
    for a, b in (("\\", r"\textbackslash{}"), ("%", r"\%"), ("&", r"\&"), ("_", r"\_"), ("#", r"\#")):
        text = text.replace(a, b)
    text = text.replace(">=", r"$\geq$").replace("<", "$<$").replace(">", "$>$").replace(" x ", r" $\times$ ")
    return text.replace("C'", "C\x00").replace("'", "`").replace("C\x00", "C$'$")


def run_label(detector, seed):
    return FAMILY[detector] if int(seed) < 0 else f"{FAMILY[detector]} s{int(seed)}"


def ci(lo, hi, digits=2):
    return f"[{pp(lo, digits)}, {pp(hi, digits)}]"


def run_order(frame):
    order = {"pca": 0, "isolation_forest": 1, "lstm_autoencoder": 2}
    return frame.assign(_o=frame.detector.map(order)).sort_values(["_o", "seed"]).drop(columns="_o")


def longtable(name, frame, caption, colspec, note="", size="footnotesize", group=2):
    header = " & ".join(frame.columns) + r" \\"
    lines = [rf"\begin{{{size}}}", rf"\begin{{longtable}}{{{colspec}}}",
             rf"\caption{{{caption}}}\label{{tab:{name}}}\\", r"\toprule", header, r"\midrule", r"\endfirsthead",
             rf"\multicolumn{{{len(frame.columns)}}}{{l}}{{\emph{{(continued)}}}}\\", r"\toprule", header, r"\midrule",
             r"\endhead", r"\bottomrule", r"\endfoot"]
    previous, last = None, [None] * group
    for row in frame.itertuples(index=False):
        values = [str(v) for v in row]
        if previous is not None and values[0] != previous and values[0] != "":
            lines.append(r"\midrule")
        previous = values[0] if values[0] != "" else previous
        for k in range(group):
            if values[k] == "":
                continue
            if values[k] == last[k] and all(values[j] in ("", last[j]) for j in range(k)):
                values[k] = ""
            else:
                last[k] = values[k]
                last[k + 1:] = [None] * (group - k - 1)
        lines.append(" & ".join(values) + r" \\")
    lines += [r"\end{longtable}", rf"\end{{{size}}}"]
    if note:
        lines += [r"\vspace{-0.5\baselineskip}", r"{\footnotesize " + note + r"\par}", r"\medskip"]
    path = TAB / f"{name}.tex"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Section S1: provenance
# ---------------------------------------------------------------------------

def s1_provenance():
    rows = []
    items = [
        ("Frozen baseline manifest (186 files)", "docs/mssp/frozen_baseline.sha256"),
        ("Post-confirmation protocol v1.0", "docs/mssp/post_confirmation_mitigation_protocol.md"),
        ("Protocol amendments", "docs/mssp/AMENDMENTS.md"),
        ("Adversarial validation plan", "docs/mssp/adversarial_validation_plan.md"),
        ("Final story lock", "docs/mssp/FINAL_STORY_LOCK.md"),
        ("Post-confirmation module", "src/mssp_mitigation.py"),
        ("Adversarial-validation module", "src/mssp_adversarial.py"),
        ("DS02 endpoint record (abnormal rows read once)", "results/mssp_mitigation/ds02/stage_e/stage_e_record.json"),
        ("DS03 endpoint record (abnormal rows read once)", "results/mssp_mitigation/ds03/stage_e/stage_e_record.json"),
        ("DS02 adversarial run record (A--C)", "results/mssp_adversarial/ds02/run_record_ABC.json"),
        ("DS03 adversarial run record (A--C)", "results/mssp_adversarial/ds03/run_record_ABC.json"),
        ("DS02 baseline run record (D)", "results/mssp_adversarial/ds02/run_record_D.json"),
        ("DS03 baseline run record (D)", "results/mssp_adversarial/ds03/run_record_D.json"),
        ("Adversarial summary record", "results/mssp_adversarial/summary/summary_record.json"),
    ]
    for label, path in items:
        INPUTS.add(ROOT / path)
        rows.append({"Artefact": label, "Path": r"\path{" + path + "}",
                     "SHA-256 (first 16 hex)": r"\texttt{" + sha256(ROOT / path)[:16] + "}"})
    longtable("s1_provenance", pd.DataFrame(rows),
              "Provenance of the analyses reported in the article. Each run record also names the analysis-module "
              "version that produced its outputs.", "p{0.27\\textwidth}p{0.44\\textwidth}l")


# ---------------------------------------------------------------------------
# Section S2: frozen discovery and confirmation (values unchanged)
# ---------------------------------------------------------------------------

def s2_correction():
    c = read(ROOT / "results/phase3_dynamic_correction/correction_comparison.csv")
    c = c[c.phase_definition == "primary"]
    rows = [{"Correction": r.correction.replace("_", "-"), "Overall": pct(r.overall_fpr), "Climb": pct(r.climb_fpr),
             "Cruise": pct(r.cruise_fpr), "Descent": pct(r.descent_fpr),
             "Worst transfer": pct(r.worst_offdiagonal_transfer_fpr)} for r in c.itertuples()]
    longtable("s2_correction", pd.DataFrame(rows),
              "Frozen DS02 PCA correction sensitivity (exploratory): pooled healthy FPR (\\%) by phase at the 1\\% "
              "target, primary phase rule, and worst off-diagonal cross-phase transfer FPR (\\%).", "lrrrrr")


def s3_alternative_rule():
    c = read(FV / "canonical_results.csv")
    c = run_order(c[(c.phase_rule == "alt_rate") & (c.nominal_fpr_target == 0.01) & (c.evaluation_unit == "pooled")])
    rows = [{"Run": run_label(r.detector, r.seed), "Climb": pct(r.climb_fpr), "Cruise": pct(r.cruise_fpr),
             "Descent": pct(r.descent_fpr), "Descent $-$ climb (pp)": pp(r.descent_minus_climb, 3),
             "Descent $-$ cruise (pp)": pp(r.descent_minus_cruise, 3)} for r in c.itertuples()]
    longtable("s3_alternative_rule", pd.DataFrame(rows),
              "Frozen DS02 alternative retrospective phase rule (exploratory; 85\\% altitude range and centred "
              "60-s altitude rate at most 2 ft/s): pooled healthy FPR (\\%) at the 1\\% target.", "lrrrrr")


def s4_runs_and_intervals():
    rows = []
    for label, canon, boot in (("DS02", FV / "canonical_results.csv", FV / "hierarchical_bootstrap_ci.csv"),
                               ("DS03", CF / "canonical_results.csv", CF / "hierarchical_bootstrap_ci.csv")):
        c = read(canon)
        b = read(boot)
        c = c[(c.phase_rule == "primary") & (c.nominal_fpr_target == 0.01) & (c.evaluation_unit == "pooled")]
        if "correction_variant" in c.columns:
            c = c[c.correction_variant == "history"]
        b = b[(b.phase_rule == "primary") & (b.nominal_fpr_target == 0.01)]
        for r in run_order(c).itertuples():
            iv = b[(b.detector == r.detector) & (b.seed == r.seed)].set_index("metric")
            rows.append({"Dataset": label, "Run": run_label(r.detector, r.seed), "Climb": pct(r.climb_fpr),
                         "Cruise": pct(r.cruise_fpr), "Descent": pct(r.descent_fpr),
                         "Descent $-$ climb, 95\\% CI (pp)": f"{pp(r.descent_minus_climb, 3)} " + ci(
                             iv.loc["descent_minus_climb", "ci_lower_95"], iv.loc["descent_minus_climb", "ci_upper_95"], 3),
                         "Descent $-$ cruise, 95\\% CI (pp)": f"{pp(r.descent_minus_cruise, 3)} " + ci(
                             iv.loc["descent_minus_cruise", "ci_lower_95"], iv.loc["descent_minus_cruise", "ci_upper_95"], 3)})
            label = ""
    longtable("s4_runs_intervals", pd.DataFrame(rows),
              "Frozen individual-run pooled healthy FPR (\\%) at the 1\\% target with hierarchical (engine, then flight) "
              "bootstrap 95\\% intervals for the contrasts (2000 replicates, thresholds re-estimated). Intervals "
              "belong to individual runs; no seed-mean interval exists.", "llrrrll")


def s5_per_engine():
    rows = []
    for label, path, unit_col in (("DS02", FV / "per_engine_phase_fpr.csv", "evaluation_unit"),
                                  ("DS03", CF / "canonical_results.csv", "evaluation_unit")):
        c = read(path)
        c = c[(c.phase_rule == "primary") & (c.nominal_fpr_target == 0.01) & c[unit_col].str.startswith("engine")]
        for r in run_order(c).itertuples():
            rows.append({"Dataset": label, "Run": run_label(r.detector, r.seed),
                         "Engine": getattr(r, unit_col).replace("engine_", ""), "Climb": pct(r.climb_fpr),
                         "Cruise": pct(r.cruise_fpr), "Descent": pct(r.descent_fpr),
                         "Descent $-$ climb (pp)": pp(r.descent_minus_climb, 3),
                         "Descent $-$ cruise (pp)": pp(r.descent_minus_cruise, 3)})
            label = ""
    longtable("s5_per_engine", pd.DataFrame(rows),
              "Frozen per-engine pooled-threshold healthy FPR (\\%) at the 1\\% target (DS02 exploratory; DS03 frozen "
              "confirmation). Directional exceptions remain visible.", "lllrrrrr")


def s6_transfer():
    rows = []
    for label, path in (("DS02", FV / "executed_threshold_transfer_matrix.csv"), ("DS03", CF / "threshold_transfer_matrix.csv")):
        t = read(path)
        t = t[(t.phase_definition == "primary") & (t.nominal_fpr == 0.01) & (t.unit.astype(str) == "all")]
        for (detector, seed), part in run_order(t).groupby(["detector", "seed"], sort=False):
            m = part.pivot_table(index="calibration_phase", columns="test_phase", values="false_alarm_rate")
            for cal in PHASES:
                rows.append({"Dataset": label, "Run": run_label(detector, seed) if cal == "climb" else "",
                             "Calibrated in": cal, **{f"Applied to {p}": pct(m.loc[cal, p]) for p in PHASES}})
            label = ""
    longtable("s6_transfer", pd.DataFrame(rows),
              "Frozen pooled cross-phase threshold-transfer matrices at the 1\\% target: healthy FPR (\\%) when the "
              "threshold calibrated within one phase is applied to each phase. Diagonal cells are the within-phase "
              "(phase-conditioned) FPRs.", "lllrrr")


def s7_burden():
    rows = []
    for label, path in (("DS02", FV / "canonical_results.csv"), ("DS03", CF / "canonical_results.csv")):
        c = read(path)
        c = c[(c.phase_rule == "primary") & (c.nominal_fpr_target == 0.01) & (c.evaluation_unit == "pooled")]
        if "correction_variant" in c.columns:
            c = c[c.correction_variant == "history"]
        for r in run_order(c).itertuples():
            rows.append({"Dataset": label, "Run": run_label(r.detector, r.seed),
                         **{f"\\makecell{{Any alarm,\\\\{p} (\\%)}}": pct(getattr(r, f"healthy_flights_with_alarm_{p}"), 1) for p in PHASES},
                         **{f"\\makecell{{Events per\\\\flight, {p}}}": num(getattr(r, f"false_alarm_events_per_healthy_flight_{p}"), 2) for p in PHASES}})
            label = ""
    longtable("s7_burden", pd.DataFrame(rows),
              "Frozen flight-level burden under pooled calibration at the 1\\% target: percentage of healthy audit "
              "flights with any alarm in each phase, and alarm events per healthy flight. This endpoint is distinct "
              "from the $\\kappa$-based healthy-flight false-flag rate of the post-confirmation analyses.",
              "llrrrrrr", size="scriptsize")


# ---------------------------------------------------------------------------
# Section S3: post-confirmation protocol v1.0
# ---------------------------------------------------------------------------

def s8_phase_fpr():
    rates = both(mit, "d", "healthy_phase_fpr_by_scheme")
    rates = rates[(rates.nominal_fpr == 0.01) & (rates.unit.astype(str) == "all")]
    rows = []
    for dataset in DATASETS:
        label = dataset.upper()
        part = run_order(rates[rates.dataset == dataset])
        for (detector, seed), run in part.groupby(["detector", "seed"], sort=False):
            for scheme in ("pooled", "phase_conditioned", "causal_regime"):
                r = run[run.scheme == scheme].set_index("phase").rate
                rows.append({"Dataset": label, "Run": run_label(detector, seed) if scheme == "pooled" else "",
                             "Arm": ARM[scheme], **{p.capitalize(): pct(r[p]) for p in (*PHASES, "overall")}})
                label = ""
    longtable("s8_phase_fpr", pd.DataFrame(rows),
              "Post-confirmation pooled audit healthy FPR (\\%) by phase at the 1\\% target under P, C and C$'$ "
              "(protocol v1.0).", "lllrrrr")


def s9_intervals():
    rows = []
    metrics = (("diff_spread", "A1"), ("diff_max_abs_error", "A2"), ("diff_rms_error", "A3"), ("diff_overall_abs_error", "A5"),
               ("diff_ew_max_abs_error", "\\makecell{A2, equal-\\\\engine"))
    for dataset in DATASETS:
        u = adv(dataset, "calibration_quality", "calibration_quality_u1_ci")
        u = u[u.nominal_fpr == 0.01]
        label = dataset.upper()
        for (detector, seed), part in run_order(u).groupby(["detector", "seed"], sort=False):
            for arm in ("phase_conditioned", "causal_regime"):
                row = {"Dataset": label, "Run": run_label(detector, seed) if arm == "phase_conditioned" else "",
                       "Arm $-$ P": ARM[arm]}
                for metric, head in metrics:
                    iv = part[part.metric == f"{metric}.{arm}"]
                    if len(iv) != 1:
                        raise ValueError(f"missing interval {metric}.{arm} for {detector} {seed}")
                    row[f"{head} (pp)" + ("}" if head.startswith("\\makecell") else "")] = ci(
                        iv.ci_lower_95.iloc[0], iv.ci_upper_95.iloc[0])
                rows.append(row)
                label = ""
    longtable("s9_intervals", pd.DataFrame(rows),
              "Paired arm-minus-P bootstrap 95\\% intervals (percentage points) at the 1\\% target for the row-pooled "
              "calibration metrics (frozen U1 resampling plans; engines then flights; thresholds re-estimated; 2000 "
              "replicates). A1, A2, A3 and A5 are row-pooled; the last column weights audit engines equally. Every "
              "interval includes zero.", "llllllll", size="scriptsize")


def s10_robustness():
    r = read(ADV / "summary/robustness_classification.csv")
    rows = [{"Dataset": d.upper() if i == 0 else "", "Claim": esc(c),
             "0.5\\%": a, "1\\%": b, "2\\%": e, "Class": esc(k)}
            for d in DATASETS
            for i, (c, a, b, e, k) in enumerate(r[r.dataset == d][["claim", "runs_holding_alpha_0.005",
                                                                  "runs_holding_alpha_0.01", "runs_holding_alpha_0.02",
                                                                  "classification"]].itertuples(index=False))]
    longtable("s10_robustness", pd.DataFrame(rows),
              "Target robustness of the post-confirmation claims: number of runs (of 7) in which each claim holds at "
              "the nominal targets 0.5\\%, 1\\% and 2\\%, with the pre-specified classification.",
              "lp{0.5\\textwidth}rrrl", size="scriptsize")


def s11_per_engine():
    q = pd.concat([both(adv, "calibration_quality", "calibration_quality_metrics"),
                   both(adv, "contextual_baseline", "baseline_calibration_quality")], ignore_index=True)
    q = q[(q.nominal_fpr == 0.01) & (q.weighting == "per_engine")]
    classes = {d: adv(d, "support_transport", "support_engines").set_index("unit").flight_class for d in DATASETS}
    rows = []
    for dataset in DATASETS:
        part = q[q.dataset == dataset]
        label = dataset.upper()
        for unit in sorted(part.unit.astype(int).unique()):
            cell = run_order(part[part.unit.astype(int) == unit])
            first = True
            for (detector, seed), run in cell.groupby(["detector", "seed"], sort=False):
                values = run.set_index("scheme").max_abs_error
                rows.append({"Dataset": label, "Engine (class)": f"{unit} ({classes[dataset].loc[unit]})" if first else "",
                             "Run": run_label(detector, seed),
                             **{ARM[s]: pct(values[s], 2) for s in ("pooled", "phase_conditioned", "causal_regime",
                                                                     "quantile_regression_W")}})
                first, label = False, ""
    longtable("s11_per_engine", pd.DataFrame(rows),
              "Per-engine maximum nominal calibration error A2 (percentage points) at the 1\\% target for every "
              "detector run under P, C, C$'$ and Q.", "lllrrrr", size="scriptsize")


def s12_weighting():
    den = read(ADV / "summary/denominator_audit.csv")
    rows = [{"Dataset": r.dataset.upper(), "Check": esc(r.check),
             "Agreeing": f"{r.agreeing} of {r.compared}"} for r in den.itertuples()]
    longtable("s12_weighting", pd.DataFrame(rows),
              "Denominator audit: sign agreement between row-pooled and alternative weightings or endpoints, over "
              "runs, targets and arms. The frozen burden endpoint (healthy flights with any alarm) and the "
              "$\\kappa$-based healthy-flight false-flag rate are distinct quantities.",
              "lp{0.62\\textwidth}r", size="scriptsize")


def s13_matched():
    m = both(adv, "matched_delay", "matched_false_flag_comparisons")
    m = m[(m.rule == "nearest") & (m.nominal_fpr == 0.01)]
    rows = []
    for dataset in DATASETS:
        label = dataset.upper()
        for (detector, seed), part in run_order(m[m.dataset == dataset]).groupby(["detector", "seed"], sort=False):
            first = True
            for r in part.sort_values(["arm", "anchor_ffr"], ascending=[False, True]).itertuples():
                rows.append({"Dataset": label, "Run": run_label(detector, seed) if first else "", "Arm": ARM[r.arm],
                             "\\makecell{Anchor\\\\(\\%)}": f"{100 * r.anchor_ffr:g}",
                             "\\makecell{Sup-\\\\ported}": "yes" if r.supported else "no",
                             "\\makecell{FFR (\\%)\\\\P / arm}": f"{pct(r.pooled_ffr, 1)} / {pct(r.arm_ffr, 1)}",
                             "\\makecell{Median delay\\\\P / arm}": f"{num(r.pooled_median_delay, 0)} / {num(r.arm_median_delay, 0)}",
                             "\\makecell{Engines earlier/\\\\same/later}": f"{r.earlier}/{r.same}/{r.later}",
                             "\\makecell{Paired\\\\median diff.}": num(r.paired_lower_median_difference, 0)})
                first, label = False, ""
    longtable("s13_matched", pd.DataFrame(rows),
              "Matched healthy-flight false-flag comparisons at the 1\\% row target (nearest-anchor rule): realized "
              "pooled false-flag rates, lower-median delays (flights from the labelled abnormal-state onset), per-engine "
              "earlier/same/later counts, and the paired lower-median difference (arm $-$ P). Unsupported anchors are "
              "shown but were not used.", "lllrlllll", size="scriptsize")


def s14_labels():
    lab = both(adv, "matched_delay", "matched_labels")
    lab = lab[lab.nominal_fpr == 0.01]
    rows = []
    for dataset in DATASETS:
        label = dataset.upper()
        for r in run_order(lab[lab.dataset == dataset]).sort_values(["arm"], ascending=False, kind="stable").itertuples():
            rows.append({"Dataset": label, "Run": run_label(r.detector, r.seed), "Arm": ARM[r.arm],
                         "\\makecell{Supported\\\\anchors}": r.supported_anchors,
                         "\\makecell{Label\\\\(nearest)}": SHORT[r.matched_label],
                         "\\makecell{Label\\\\(conservative)}": SHORT[r.matched_label_not_exceeding_rule],
                         "\\makecell{Curve mean\\\\P / arm}": f"{num(r.curve_mean_pooled)} / {num(r.curve_mean_arm)}",
                         "\\makecell{Locked\\\\point}": r.locked_pareto})
            label = ""
    longtable("s14_labels", pd.DataFrame(rows),
              "Pre-specified run labels at the 1\\% target under the nearest-anchor rule and the conservative "
              "(not-exceeding) sensitivity rule, curve-level mean delays over realized false-flag rates 2.5--20\\% "
              "(flights), and the Pareto class of the locked operating point against P. Labels: E, earlier at matched "
              "burden; L, later; M, mixed; =, equal; n/e, not evaluable.",
              "lllrllll", size="scriptsize")


def s15_delays():
    flags = both(mit, "e", "healthy_flight_false_flags_with_delay")
    delay = both(mit, "e", "detection_delay")
    flags = flags[(flags.nominal_fpr == 0.01) & (flags.unit.astype(str) != "all")].assign(
        unit=lambda f: f.unit.astype(str))
    delay = delay[(delay.nominal_fpr == 0.01)].assign(unit=lambda f: f.unit.astype(str))
    merged = flags.merge(delay[["dataset", "detector", "seed", "scheme", "unit", "delay_flights", "censored"]],
                         on=["dataset", "detector", "seed", "scheme", "unit"], how="left")
    rows = []
    for dataset in DATASETS:
        label = dataset.upper()
        for (detector, seed), part in run_order(merged[merged.dataset == dataset]).groupby(["detector", "seed"], sort=False):
            first = True
            for unit, cell in part.groupby(part.unit.astype(int)):
                values = cell.set_index("scheme")
                row = {"Dataset": label, "Run": run_label(detector, seed) if first else "", "Engine": unit}
                for scheme in ("pooled", "phase_conditioned", "causal_regime"):
                    v = values.loc[scheme]
                    d = "cens." if bool(v.censored) else num(v.delay_flights, 0)
                    row[f"{ARM[scheme]}: delay / FFR (\\%)"] = f"{d} / {pct(v.false_flag_rate, 1)}"
                rows.append(row)
                first, label = False, ""
    longtable("s15_delays", pd.DataFrame(rows),
              "Per-engine detection delay (flights from the labelled abnormal-state onset; cens. = no flagged "
              "post-onset flight) and healthy-flight false-flag rate at the locked $\\kappa$ (1\\% row target).",
              "lllrll", size="scriptsize")


def s16_abnormal():
    rates = both(mit, "e", "abnormal_alarm_rates")
    rates = rates[(rates.nominal_fpr == 0.01) & (rates.unit.astype(str) == "all") & (rates.phase == "overall")]
    pauc = both(mit, "e", "separability_pauc")
    rows = []
    for dataset in DATASETS:
        label = dataset.upper()
        for (detector, seed), part in run_order(rates[rates.dataset == dataset]).groupby(["detector", "seed"], sort=False):
            for scheme in ("pooled", "phase_conditioned", "causal_regime"):
                cell = part[part.scheme == scheme].set_index("window").rate
                pa = pauc[(pauc.dataset == dataset) & (pauc.detector == detector) & (pauc.seed == seed)
                          & (pauc.scheme == scheme)].set_index("window")["normalized_pauc_fpr_0_to_0.02"]
                rows.append({"Dataset": label, "Run": run_label(detector, seed) if scheme == "pooled" else "",
                             "Arm": ARM[scheme], "All post-onset (\\%)": pct(cell["all_post_onset"], 2),
                             "First 10 post-onset flights (\\%)": pct(cell["early_first_10"], 2),
                             "S4 pAUC, all": num(pa["all_post_onset"], 3), "S4 pAUC, first 10": num(pa["early_first_10"], 3)})
                label = ""
    guard = both(mit, "e", "guardrails")
    guard = guard[guard.nominal_fpr == 0.01]
    longtable("s16_abnormal", pd.DataFrame(rows),
              "Abnormal-state ($hs = 0$) row alarm rates (\\%) at the 1\\% target and the S4 separability of "
              "calibration p-values. S4 pAUC is the normalized partial area under the row-level ROC curve of abnormal "
              "versus healthy audit rows over row FPR in [0, 2\\%], computed on calibration p-values; it is "
              "threshold-free and is not a flight-level operating characteristic. Family guardrail ratios "
              f"(arm/P, all post-onset rows) ranged {guard.alarm_rate_ratio_all_post_onset.min():.2f}--"
              f"{guard.alarm_rate_ratio_all_post_onset.max():.2f}.", "lllrrrr", size="scriptsize")


def s17_any_alarm():
    b = both(mit, "d", "healthy_flight_burden_by_scheme")
    b = b[(b.nominal_fpr == 0.01) & (b.unit.astype(str) == "all")]
    flags = both(mit, "e", "healthy_flight_false_flags_with_delay")
    flags = flags[(flags.nominal_fpr == 0.01) & (flags.unit.astype(str) == "all")]
    rows = []
    for dataset in DATASETS:
        label = dataset.upper()
        for (detector, seed), part in run_order(b[b.dataset == dataset]).groupby(["detector", "seed"], sort=False):
            for scheme in ("pooled", "phase_conditioned", "causal_regime"):
                cell = part[part.scheme == scheme].set_index("phase").fraction_flights_with_alarm
                ffr = flags[(flags.dataset == dataset) & (flags.detector == detector) & (flags.seed == seed)
                            & (flags.scheme == scheme)].false_flag_rate
                rows.append({"Dataset": label, "Run": run_label(detector, seed) if scheme == "pooled" else "",
                             "Arm": ARM[scheme], "\\makecell{Any alarm,\\\\overall (\\%)}": pct(cell["overall"], 1),
                             **{f"\\makecell{{Any alarm,\\\\{p} (\\%)}}": pct(cell[p], 1) for p in PHASES},
                             "\\makecell{$\\kappa$-based\\\\FFR (\\%)}": pct(ffr.iloc[0], 1)})
                label = ""
    longtable("s17_any_alarm", pd.DataFrame(rows),
              "Healthy flights with any alarm (the frozen burden endpoint) under P, C and C$'$ at the 1\\% target, "
              "shown beside the $\\kappa$-based healthy-flight false-flag rate. The two quantities are distinct and "
              "are never merged.", "lllrrrrr", size="scriptsize")


def s18_baseline():
    fits = both(adv, "contextual_baseline", "baseline_fits")
    ff = both(adv, "contextual_baseline", "baseline_flight_false_flags")
    rows = []
    for dataset in DATASETS:
        label = dataset.upper()
        part = run_order(fits[fits.dataset == dataset])
        for r in part.sort_values(["nominal_fpr"], kind="stable").itertuples():
            f = ff[(ff.dataset == dataset) & (ff.detector == r.detector) & (ff.seed == r.seed)
                   & (ff.nominal_fpr == r.nominal_fpr) & (ff.unit.astype(str) == "all")].false_flag_rate
            rows.append({"Dataset": label, "Target": f"{100 * r.nominal_fpr:g}\\%", "Run": run_label(r.detector, r.seed),
                         "Fit rows": f"{r.fit_rows:,}", "In-sample alarm rate (\\%)": pct(r.calibration_row_alarm_rate, 2),
                         "$\\kappa$": num(r.kappa, 4), "Audit FFR at $\\kappa$ (\\%)": pct(f.iloc[0], 1)})
            label = ""
    longtable("s18_baseline", pd.DataFrame(rows),
              "Continuous contextual baseline Q: linear quantile regression of the detector score at level $1-\\alpha$ on "
              "a quadratic surface of the four standardized operating descriptors (4 linear, 4 squared and 6 pairwise "
              "terms plus an intercept), solved exactly by linear programming (HiGHS, no penalty) on every fifth healthy "
              "calibration row, per run and target, with no tuning and no phase input. Fitted coefficients are in the "
              "machine-readable evidence files.", "lllrrrr", size="scriptsize")


def s19_baseline_phase():
    q = both(adv, "contextual_baseline", "baseline_calibration_quality")
    q = q[(q.nominal_fpr == 0.01) & (q.unit == "all")]
    rows = []
    for dataset in DATASETS:
        label = dataset.upper()
        for r in run_order(q[q.dataset == dataset]).itertuples():
            rows.append({"Dataset": label, "Run": run_label(r.detector, r.seed), "Climb": pct(r.climb_fpr),
                         "Cruise": pct(r.cruise_fpr), "Descent": pct(r.descent_fpr), "Overall": pct(r.overall_fpr),
                         "A1 (pp)": pct(r.spread, 2), "A2 (pp)": pct(r.max_abs_error, 2), "A3 (pp)": pct(r.rms_error, 2)})
            label = ""
    longtable("s19_baseline_phase", pd.DataFrame(rows),
              "Continuous contextual baseline Q: pooled audit healthy FPR (\\%) by phase and calibration metrics at the "
              "1\\% target (healthy side only).", "llrrrrrrr")


def s20_support_cells():
    cells = both(adv, "support_transport", "support_cells")
    rows = [{"Dataset": r.dataset.upper(), "Engine (class)": f"{r.unit} ({r.flight_class})", "Phase": r.phase,
             "Rows": f"{r.rows:,}", "\\makecell{Median\\\\$d$}": num(r.d_phase_median, 3),
             "\\makecell{95th pct\\\\$d$}": num(r.d_phase_p95, 3),
             "\\makecell{Median $d$,\\\\any phase}": num(r.d_all_median, 3),
             "\\makecell{Median\\\\$d$, 8-D}": num(r.d8_phase_median, 3),
             "\\makecell{Beyond\\\\ref. (\\%)}": pct(r.fraction_beyond_support_d_phase, 1),
             "\\makecell{Outside\\\\range (\\%)}": pct(r.fraction_outside_phase_range, 1)} for r in cells.itertuples()]
    longtable("s20_support_cells", pd.DataFrame(rows),
              "Operating-support distances of healthy audit rows to the nearest healthy calibration row of the same "
              "retrospective phase (standardized altitude, Mach number, throttle-resolver angle and fan-inlet "
              "temperature), with the any-phase and 8-D (adding 120-s trailing slopes) variants, the fraction beyond "
              "the cross-calibration-engine 95th-percentile reference, and the fraction outside the calibration range.",
              "lllrrrrrrr", size="scriptsize")


def s21_associations():
    a = both(adv, "support_transport", "support_associations")
    a = a[a.nominal_fpr == 0.01]
    rows = [{"Dataset": r.dataset.upper(), "Run": run_label(r.detector, r.seed), "Cells": r.cells,
             "\\makecell{$\\rho$($d$,\\\\|err| C)}": num(r.rho_dphase_vs_abs_error_C),
             "\\makecell{$\\rho$($d$,\\\\|err| C$'$)}": num(r.rho_dphase_vs_abs_error_Cprime),
             "\\makecell{$\\rho$($d_{\\mathrm{all}}$,\\\\|err| P)}": num(r.rho_dall_vs_abs_error_P),
             "\\makecell{$\\rho$($d$, change\\\\P$\\to$C)}": num(r.rho_dphase_vs_change_abs_error_P_to_C),
             "\\makecell{Leave-one-engine-\\\\out range}": f"[{num(r.loeo_min)}, {num(r.loeo_max)}]"}
            for r in run_order(a).itertuples()]
    summary = json.loads((ADV / "summary/summary_record.json").read_text())
    INPUTS.add(ADV / "summary/summary_record.json")
    longtable("s21_associations", pd.DataFrame(rows),
              "Spearman correlations across engine $\\times$ phase cells between median same-phase support distance and "
              "calibration error, per run at the 1\\% target, with leave-one-engine-out ranges. Pre-specified verdict: "
              f"{summary['support_verdict'].lower()}.", "llrrrrrl", size="scriptsize")


def s22_c0():
    e = both(adv, "support_transport", "calibration_phase_effect")
    e = e[e.nominal_fpr == 0.01]
    rows = [{"Dataset": r.dataset.upper(), "Run": run_label(r.detector, r.seed),
             "Evaluation": r.evaluation.replace("_", " ").replace("in sample pooled tau", "in-sample").replace("cross engine ", "engine "),
             "Climb": pct(r.climb_fpr), "Cruise": pct(r.cruise_fpr), "Descent": pct(r.descent_fpr),
             "Overall": pct(r.overall_fpr), "Highest": r.highest_phase} for r in run_order(e).itertuples()]
    longtable("s22_c0", pd.DataFrame(rows),
              "C0: pooled-threshold healthy FPR (\\%) by phase within the calibration engines at the 1\\% target, "
              "in-sample and from one calibration engine to the other, where calibration-to-audit mismatch is absent "
              "by construction.", "lllrrrrl", size="scriptsize")


def s23_decomposition():
    d = read(ADV / "summary/post_plan_error_decomposition.csv")
    d = d[d.nominal_fpr == 0.01]
    rows = []
    for r in run_order(d).sort_values(["dataset"], kind="stable").itertuples():
        rows.append({"Dataset": r.dataset.upper(), "Run": run_label(r.detector, r.seed), "Arm": ARM[r.scheme],
                     "RMS (pp)": f"{100 * np.sqrt(r.mse):.2f}", "Bias$^2$ (\\%)": f"{100 * r.share_bias_sq:.0f}",
                     "Phase (\\%)": f"{100 * r.share_phase:.0f}", "Engine (\\%)": f"{100 * r.share_engine:.0f}",
                     "Engine$\\times$phase (\\%)": f"{100 * r.share_interaction:.0f}"})
    longtable("s23_decomposition", pd.DataFrame(rows),
              "Post-plan descriptive decomposition (deviation Dev-1) of the equal-cell mean squared nominal error over "
              "audit engine $\\times$ phase cells at the 1\\% target into overall bias, phase, engine and interaction "
              "shares.", "lllrrrrr", size="scriptsize")


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

COLORS = {"pooled": "#4d4d4d", "phase_conditioned": "#1f77b4", "causal_regime": "#ff7f0e"}


def fig_operating_curves():
    fig, axes = plt.subplots(2, 3, figsize=(6.3, 4.2), sharex=True)
    for r, dataset in enumerate(DATASETS):
        points = adv(dataset, "matched_delay", "operating_points")
        locked = adv(dataset, "matched_delay", "locked_operating_points")
        points, locked = points[points.nominal_fpr == 0.01], locked[locked.nominal_fpr == 0.01]
        for c, family in enumerate(FAMILY):
            ax = axes[r, c]
            for anchor in ANCHORS:
                ax.axvline(100 * anchor, color="#dddddd", linewidth=0.6, zorder=0)
            for (seed, scheme), part in points[points.detector == family].groupby(["seed", "scheme"]):
                part = part.sort_values("ffr")
                ax.step(100 * part.ffr, part.median_delay.replace(np.inf, np.nan), where="post",
                        color=COLORS[scheme], linewidth=0.8, alpha=0.8)
            for row in locked[locked.detector == family].itertuples():
                ax.scatter(100 * row.ffr, row.median_delay if np.isfinite(row.median_delay) else np.nan,
                           color=COLORS[row.scheme], edgecolor="black", linewidth=0.4, s=16, zorder=3)
            ax.set_xlim(0, 35)
            ax.set_ylim(bottom=0)
            if r == 0:
                ax.set_title({"pca": "Residual PCA", "isolation_forest": "Isolation Forest",
                              "lstm_autoencoder": "Past-only LSTM"}[family])
            if r == 1:
                ax.set_xlabel("Realized healthy-flight\nfalse-flag rate (%)")
            if c == 0:
                ax.set_ylabel(f"{dataset.upper()}\nmedian delay (flights)")
    handles = [plt.Line2D([], [], color=COLORS[a], label=l) for a, l in
               (("pooled", "P"), ("phase_conditioned", "C"), ("causal_regime", "C′"))]
    handles.append(plt.Line2D([], [], marker="o", linestyle="", color="white", markeredgecolor="black",
                              label="locked κ"))
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.03))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    path = FIG / "figS3_operating_characteristics.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_decomposition():
    table = read(ADV / "summary/post_plan_error_decomposition.csv")
    table = table[table.nominal_fpr == 0.01]
    fig, ax = plt.subplots(figsize=(4.2, 2.6))
    components = (("bias_sq", "overall bias²", "#bdbdbd"), ("phase", "phase", "#d62728"),
                  ("engine", "engine", "#6a51a3"), ("interaction", "engine × phase", "#9e9ac8"))
    for i, dataset in enumerate(DATASETS):
        for j, scheme in enumerate(("pooled", "phase_conditioned", "causal_regime")):
            part = table[(table.dataset == dataset) & (table.scheme == scheme)]
            bottom = 0.0
            for key, label, color in components:
                value = 1e4 * part[key].median()
                ax.bar(i * 3.6 + j, value, 0.8, bottom=bottom, color=color, edgecolor="black", linewidth=0.3,
                       label=label if (i, j) == (0, 0) else None)
                bottom += value
    ax.set_xticks([j + i * 3.6 for i in range(2) for j in range(3)], ["P", "C", "C′"] * 2)
    ax.text(1, -0.17, "DS02", ha="center", transform=ax.get_xaxis_transform())
    ax.text(4.6, -0.17, "DS03", ha="center", transform=ax.get_xaxis_transform())
    ax.set_ylabel("Mean squared nominal error\n(pp², median over runs)")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    path = FIG / "figS4_error_decomposition.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

DOCUMENT = r"""\documentclass[11pt]{article}
\usepackage[a4paper,margin=2cm]{geometry}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern,amsmath,amssymb,booktabs,longtable,graphicx,array,url,makecell}
\renewcommand{\cellalign}{bl}\renewcommand{\theadalign}{bl}
\usepackage[hidelinks]{hyperref}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\thefigure}{S\arabic{figure}}
\setlength{\LTcapwidth}{\textwidth}
\title{Supplementary material for\\``TITLE''}
\author{Jinghang Mei}
\date{}
\begin{document}
\maketitle

\noindent This supplement accompanies the article. Every table is a formatted view of committed outputs of the frozen
and post-confirmation analyses; values are rounded for display and nothing is recomputed. Healthy false-positive rates
(FPR) are percentages of healthy rows; differences are in percentage points (pp). Runs are one PCA run (PCA) and three
seeds each of Isolation Forest (IF s0--s2) and the past-only LSTM (LSTM s0--s2). Arms: P, pooled; C, retrospective
phase-conditioned; C$'$, past-only regime-conditioned; Q, continuous contextual baseline (healthy side only). The primary
nominal target is 1\%. Machine-readable versions of all tables are in the public repository
(\url{https://github.com/surnamemei/ncmapss-phase-entanglement}; \texttt{results/} and \texttt{paper/mssp/evidence/}).

\tableofcontents
\bigskip

\section{Provenance, reproduction and deviations}
The study was staged: DS02 exploratory discovery, a protocol freeze, a one-shot frozen DS03 confirmation, and two
post-confirmation stages (protocol v1.0 and the adversarial-validation plan), each committed before execution.
Before every post-confirmation run, reproduction gates required exact agreement with the frozen evidence:
rescored healthy score vectors equalled the frozen fingerprints bit for bit; recomputed healthy count tables,
calibration-only $\kappa$ locks and bootstrap summaries equalled the committed outputs; and the committed per-flight
alarm fractions reproduced every committed detection delay. A hash manifest of 186 frozen files was verified before
and after every run. Abnormal-state ($hs = 0$) rows were read once per dataset, after the calibration-only lock, and
never again. Table~\ref{tab:s1_provenance} lists the governing documents and records.

\paragraph{Deviations and amendments.}
(i) Amendment A-1 corrected a repository-metadata statement about the published v1.0.0 release tag; it was recorded
before any abnormal-state row was opened and changed no analysis. (ii) Dev-1: the error decomposition (Section~\ref{sec:adversarial}) was added after the plan and is
descriptive. (iii) Dev-2: operational definitions of the target-robustness claims were fixed in code before execution.
(iv) Dev-3: after all runs, an output guard and a robustness fix for phases without rows were added to the analysis
module; no output was regenerated, and every output names the module version that produced it. (v) Story-lock
Amendment 1 corrected the count of audit engines from flight classes absent from calibration (four, three of them
class 1) without changing any analysis.

\paragraph{Verification.} The repository's test suite re-derives the post-confirmation metrics and operating points
from committed inputs, and a checker re-derives every number cited in the article and verifies that it appears
verbatim.

\input{tables/s1_provenance.tex}

\section{Frozen discovery and confirmation}
The values in this section are the frozen DS02 (exploratory) and DS03 (frozen confirmation) results, shown unchanged.

\input{tables/s2_correction.tex}
\input{tables/s3_alternative_rule.tex}
\input{tables/s4_runs_intervals.tex}
\input{tables/s5_per_engine.tex}
\input{tables/s6_transfer.tex}
\input{tables/s7_burden.tex}

\subsection*{LSTM training and convergence}
Figures~\ref{fig:s1} and~\ref{fig:s2} reproduce the recorded training and epoch-selection validation losses without
smoothing. The DS02 seed-0 selection reached the pre-specified 600-epoch ceiling while validation loss was still
improving; it is reported as a convergence limitation and was not retuned. These diagnostics do not inspect test
outcomes.

\begin{figure}[htbp]\centering
\includegraphics[width=0.9\textwidth]{FROZEN/figure_s1_ds02_lstm_history.pdf}
\caption{Frozen DS02 LSTM training and epoch-selection validation losses (seeds 0--2).}\label{fig:s1}
\end{figure}
\begin{figure}[htbp]\centering
\includegraphics[width=0.9\textwidth]{FROZEN/figure_s2_ds03_lstm_history.pdf}
\caption{Frozen DS03 LSTM training and epoch-selection validation losses (seeds 0--2).}\label{fig:s2}
\end{figure}

\section{Post-confirmation protocol v1.0}
These analyses are exploratory. They reuse the frozen detectors and engine partitions and are not part of the
DS03 confirmation.

\input{tables/s8_phase_fpr.tex}
\input{tables/s9_intervals.tex}
\input{tables/s10_robustness.tex}

\section{Adversarial validation}\label{sec:adversarial}
\input{tables/s11_per_engine.tex}
\input{tables/s12_weighting.tex}

\subsection*{Matched false-flag delay}
Figure~\ref{fig:s3} shows the full operating characteristics: the lower-median detection delay against the realized
pooled healthy-flight false-flag rate as $\kappa$ is swept over the calibration-only grid. Tables~\ref{tab:s13_matched}
and~\ref{tab:s14_labels} give the matched comparisons at the pre-specified anchors, and Table~\ref{tab:s15_delays}
gives per-engine delays at the locked $\kappa$ together with their false-flag rates.

\begin{figure}[htbp]\centering
\includegraphics[width=\textwidth]{figures/figS3_operating_characteristics.pdf}
\caption{Median detection delay against realized pooled healthy-flight false-flag rate at the 1\% row target, one step
curve per seed and arm over the calibration-only $\kappa$ grid. Grey vertical lines mark the matching anchors; filled
markers are the locked-$\kappa$ operating points (nominal 5\%). Vertical segments mark $\kappa$ intervals that share a
realized rate.}\label{fig:s3}
\end{figure}

\input{tables/s13_matched.tex}
\input{tables/s14_labels.tex}
\input{tables/s15_delays.tex}
\input{tables/s16_abnormal.tex}
\input{tables/s17_any_alarm.tex}

\subsection*{Continuous contextual baseline}
\input{tables/s18_baseline.tex}
\input{tables/s19_baseline_phase.tex}

\subsection*{Operating support and the phase effect within calibration engines}
\input{tables/s20_support_cells.tex}
\input{tables/s21_associations.tex}
\input{tables/s22_c0.tex}

\subsection*{Post-plan error decomposition}
\input{tables/s23_decomposition.tex}
\begin{figure}[htbp]\centering
\includegraphics[width=0.65\textwidth]{figures/figS4_error_decomposition.pdf}
\caption{Post-plan descriptive decomposition (Dev-1) of the equal-cell mean squared nominal error at the 1\% target
(median over the seven detector runs).}\label{fig:s4}
\end{figure}

\end{document}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-compile", action="store_true")
    args = parser.parse_args()
    for folder in (TAB, FIG):
        folder.mkdir(parents=True, exist_ok=True)
    builders = (s1_provenance, s2_correction, s3_alternative_rule, s4_runs_and_intervals, s5_per_engine, s6_transfer,
                s7_burden, s8_phase_fpr, s9_intervals, s10_robustness, s11_per_engine, s12_weighting, s13_matched,
                s14_labels, s15_delays, s16_abnormal, s17_any_alarm, s18_baseline, s19_baseline_phase,
                s20_support_cells, s21_associations, s22_c0, s23_decomposition)
    for build in builders:
        build()
    figures = [fig_operating_curves(), fig_decomposition()]
    frozen = FROZEN_SUPP.relative_to(OUT, walk_up=True).as_posix()
    for name in ("figure_s1_ds02_lstm_history.pdf", "figure_s2_ds03_lstm_history.pdf"):
        INPUTS.add(FROZEN_SUPP / name)
    tex = DOCUMENT.replace("TITLE", TITLE).replace("FROZEN/", frozen + "/")
    (OUT / "supplement.tex").write_text(tex, encoding="utf-8")
    print(f"wrote {len(builders)} tables and {len(figures)} figures")
    if not args.no_compile:
        for _ in range(3):
            result = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "supplement.tex"],
                                    cwd=OUT, capture_output=True, text=True, errors="replace")
            if result.returncode != 0:
                print(result.stdout[-3000:])
                sys.exit(1)
        print("compiled supplement.pdf")
    outputs = sorted([*TAB.glob("*.tex"), *FIG.glob("*.pdf"), OUT / "supplement.tex"]
                     + ([OUT / "supplement.pdf"] if (OUT / "supplement.pdf").exists() else []))
    record = {"builder": rel(__file__), "builder_sha256": sha256(__file__),
              "inputs": {rel(p): sha256(p) for p in sorted(INPUTS)},
              "outputs": {rel(p): sha256(p) for p in outputs},
              "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "note": "Formatted views of committed outputs; no recomputation from scores; no N-CMAPSS data read."}
    (OUT / "supplement.provenance.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
