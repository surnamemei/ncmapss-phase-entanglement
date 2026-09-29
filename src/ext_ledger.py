"""Extension evidence ledger (brief section 23): EX-numbered values with full provenance.

Every value is recomputed from committed audit and summary tables. Historical RESS (E/M) and
post-confirmation (PC) ledger IDs are never touched. Each row states:
- the source file and its SHA-256;
- the subset, engine, detector, seed, target, calibration arm, alarm policy and aggregation rule;
- the commit;
- whether the value is pre-specified or descriptive;
- its tier (primary, secondary, design, robustness, baseline);
- the exact generated claim.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import ext_common as ec

ALPHA = ec.PRIMARY_TARGET
FAMILY_NAME = {"pca": "residual PCA", "isolation_forest": "Isolation Forest (seed mean)",
               "lstm_autoencoder": "past-only LSTM (seed mean)", "cvae": "CVAE (seed mean)"}
ARM_NAME = {"pooled": "P", "phase_conditioned": "C", "quantile_regression_W": "Q"}


class Ledger:
    def __init__(self, commit):
        self.rows, self.commit, self.hashes = [], commit, {}

    def source(self, path):
        path = Path(path)
        if path not in self.hashes:
            self.hashes[path] = ec.file_digest(path)
        return str(path.resolve().relative_to(ec.ROOT)) if str(path.resolve()).startswith(str(ec.ROOT)) else str(path), \
            self.hashes[path]

    def add(self, *, statistic, value, source, claim, tier, status="pre-specified", subset="", engine="", detector="",
            seed="", target=ALPHA, arm="", rule="", aggregation=""):
        rel, digest = self.source(source)
        self.rows.append({"ex_id": f"EX{len(self.rows) + 1:06d}", "statistic": statistic,
                          "value": value if isinstance(value, str) else float(value), "subset": subset,
                          "family": ec.FAMILIES.get(subset, "") if subset else "", "engine": engine,
                          "detector": detector, "seed": seed, "target": target, "arm": arm, "rule": rule,
                          "aggregation": aggregation, "source_file": rel, "source_sha256": digest,
                          "commit": self.commit, "status": status, "tier": tier, "claim": claim})


def audit_path(key, table):
    return ec.RESULTS / key / "audit" / f"{table}.csv"


def summary_path(table):
    return ec.RESULTS / "summary" / table


def build(keys=None, out=None):
    keys = list(keys or (list(ec.REFERENCE_ORDER) + list(ec.NEW_ORDER)))
    ledger = Ledger(ec.git_sha())
    decisions_path = summary_path("decisions.json")
    decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
    for h in ("H1", "H2", "H3", "H4", "H5", "H6"):
        ledger.add(statistic=f"{h} verdict", value=decisions[h]["verdict"], source=decisions_path,
                   claim=f"{h} decision under the frozen count rule: {decisions[h]['verdict']}.",
                   tier={"H1": "primary", "H2": "secondary", "H3": "primary", "H4": "design", "H5": "baseline",
                         "H6": "robustness"}[h], aggregation="family-level count rule (protocol section 13)")
    ledger.add(statistic="original-story class", value=decisions["original_story"]["class"], source=decisions_path,
               claim=f"The pre-extension story is classified {decisions['original_story']['class']}.", tier="primary",
               aggregation="protocol section 15 with Amendment 1")
    ledger.add(statistic="matrix story headline", value=decisions["matrix_stories"]["headline"], source=decisions_path,
               claim=f"Interpretation-matrix headline: {decisions['matrix_stories']['headline']} (triggered "
                     f"{', '.join(decisions['matrix_stories']['triggered']) or 'none'}).", tier="primary",
               aggregation="protocol section 14")
    for flag, raised in decisions["rescope_flags"].items():
        ledger.add(statistic=f"rescope flag {flag}", value="raised" if raised else "not raised", source=decisions_path,
                   claim=f"Rescope flag {flag} was {'raised' if raised else 'not raised'}.", tier="primary",
                   aggregation="protocol section 16")
    for key in keys:
        ts_path = audit_path(key, "transport_summary")
        ts = pd.read_csv(ts_path)
        ts = ts[ts.nominal_fpr == ALPHA]
        for detector in FAMILY_NAME:
            for arm in ARM_NAME:
                part = ts[(ts.detector == detector) & (ts.arm == arm)]
                for metric, label, tier in (("pooled_A1", "pooled between-phase disparity A1", "secondary"),
                                            ("pooled_A2", "pooled maximum nominal calibration error A2", "primary"),
                                            ("ME_A2", "equal-engine mean per-engine A2 (ME-A2)", "primary"),
                                            ("WE_A2", "worst-engine A2 (WE-A2)", "primary"),
                                            ("EW_A2", "A2 of equal-engine-averaged phase FPRs (EW-A2)", "secondary")):
                    value = float(part[metric].mean())
                    ledger.add(statistic=f"{metric} ({ARM_NAME[arm]})", value=value, source=ts_path, subset=key,
                               detector=detector, seed="0,1,2" if detector != "pca" else "-1", arm=arm, rule="R0",
                               aggregation="row-pooled over audit engines" if metric.startswith("pooled") else
                               ("mean over audit engines" if metric.startswith("ME") else
                                ("max over audit engines" if metric.startswith("WE") else "equal-engine FPR average"))
                               + ("; seed mean" if detector != "pca" else ""),
                               tier="baseline" if detector == "cvae" and tier == "primary" else tier,
                               claim=f"{key}, {FAMILY_NAME[detector]}, arm {ARM_NAME[arm]}, α = 1%: {label} = "
                                     f"{100 * value:.2f} pp.")
                for phase in ("climb", "cruise", "descent"):
                    value = float(part[f"pooled_{phase}_fpr"].mean())
                    ledger.add(statistic=f"pooled {phase} FPR ({ARM_NAME[arm]})", value=value, source=ts_path,
                               subset=key, detector=detector, seed="0,1,2" if detector != "pca" else "-1", arm=arm,
                               rule="R0", aggregation="row-pooled over audit engines" + ("; seed mean" if detector != "pca" else ""),
                               tier="primary" if arm == "pooled" else "secondary",
                               claim=f"{key}, {FAMILY_NAME[detector]}, arm {ARM_NAME[arm]}, α = 1%: pooled healthy "
                                     f"{phase} FPR = {100 * value:.3f}%.")
        paired_path = audit_path(key, "paired_transport")
        paired = pd.read_csv(paired_path)
        paired = paired[paired.nominal_fpr == ALPHA]
        for arm in ("phase_conditioned", "quantile_regression_W"):
            part = paired[paired.arm == arm]
            for label, count in (("runs with uniform per-engine improvement", int(part.uniform_improvement.sum())),
                                 ("runs with at least one engine worse", int((part.n_worse >= 1).sum())),
                                 ("runs with reduced pooled disparity", int((part.diff_pooled_A1 < 0).sum()))):
                ledger.add(statistic=f"{label} ({ARM_NAME[arm]} vs P)", value=count, source=paired_path, subset=key,
                           arm=arm, rule="R0", aggregation=f"count over {len(part)} runs",
                           tier="primary" if "engine" in label else "secondary",
                           claim=f"{key}, {ARM_NAME[arm]} versus P at α = 1%: {label}: {count} of {len(part)}.")
    for name, tier in (("uext2_cross_dataset.csv", "primary"), ("composition_bootstrap.csv", "design")):
        path = summary_path(name)
        frame = pd.read_csv(path)
        for row in frame.to_dict("records"):
            label = row.get("quantity", row.get("statistic"))
            owner = row.get("detector_family", row.get("arm"))
            point = row.get("point_median_over_families", row.get("point"))
            ledger.add(statistic=f"{label} [{owner}]", value=point, source=path, aggregation=row.get("hierarchy",
                       "family -> subset -> engine"), tier=tier,
                       claim=f"Cross-dataset {label} [{owner}]: {100 * point:.3f} pp (95% interval "
                             f"{100 * row['ci_lower_95']:.3f} to {100 * row['ci_upper_95']:.3f} pp; "
                             f"{row.get('top_level_units', row.get('families'))} top-level units).")
    we_path = summary_path("we_ffr.csv")
    we = pd.read_csv(we_path)
    for key in keys:
        if key not in set(we.subset):
            continue
        for rule in ec.RULES:
            part = we[(we.subset == key) & (we.rule == rule) & (we.arm == "pooled") & (we.detector != "cvae")]
            value = float(part.WE_FFR.median())
            ledger.add(statistic="median worst-engine healthy-flight false-flag rate (P)", value=value, source=we_path,
                       subset=key, arm="pooled", rule=rule, aggregation="median over 7 residual runs",
                       tier="robustness", claim=f"{key}, rule {rule}, arm P, α = 1%: median worst-engine healthy-flight "
                                                f"false-flag rate {100 * value:.1f}% (locked κ).")
    descriptive(ledger, keys)
    frame = pd.DataFrame(ledger.rows)
    ec.write_csv(out or (ec.DOCS / "EXTENSION_EVIDENCE_LEDGER.csv"), frame)
    return frame


def descriptive(ledger, keys):
    """Descriptive statistics cited in the report and manuscript (status 'descriptive' unless a rule applies)."""
    order_path = summary_path("phase_ordering_pooled.csv")
    order = pd.read_csv(order_path)
    for key in keys:
        part = order[order.subset == key]
        if not len(part):
            continue
        for phase in ("climb", "cruise", "descent"):
            count = int((part.highest_phase == phase).sum())
            ledger.add(statistic=f"runs with {phase} the highest pooled phase FPR under P", value=count,
                       source=order_path, subset=key, arm="pooled", rule="R0", status="descriptive",
                       tier="primary", aggregation=f"count over {len(part)} runs (all detectors)",
                       claim=f"{key}: {phase} was the highest pooled healthy phase FPR under P in {count} of "
                             f"{len(part)} detector runs (α = 1%).")
    runs_path = summary_path("composition_run_summary.csv")
    runs = pd.read_csv(runs_path)
    for (key, arm), part in runs.groupby(["subset", "arm"]):
        ledger.add(statistic="runs supporting coverage (median within-engine coverage effect > 0)",
                   value=int(part.supports_coverage.sum()), source=runs_path, subset=key, arm=arm,
                   aggregation=f"count over {len(part)} runs", tier="design",
                   claim=f"{key}, arm {ARM_NAME[arm]}: the median within-engine coverage effect was positive in "
                         f"{int(part.supports_coverage.sum())} of {len(part)} runs (fixed volume, α = 1%).")
        ledger.add(statistic="median over runs of the median within-engine coverage effect",
                   value=float(part.median_delta_cov.median()), source=runs_path, subset=key, arm=arm,
                   aggregation="median over runs of the median over eligible audit engines", tier="design",
                   claim=f"{key}, arm {ARM_NAME[arm]}: median coverage effect {100 * part.median_delta_cov.median():.2f} pp.")
        ledger.add(statistic="runs where class-balanced calibration beats the mean single-engine design",
                   value=int(part.balance_check.sum()), source=runs_path, subset=key, arm=arm,
                   aggregation=f"count over {len(part)} runs", tier="design",
                   claim=f"{key}, arm {ARM_NAME[arm]}: class-balanced ME-A2 was below the mean single-engine ME-A2 in "
                         f"{int(part.balance_check.sum())} of {len(part)} runs.")
    we_path = summary_path("we_ffr.csv")
    we = pd.read_csv(we_path)
    new = we[we.subset.isin(ec.NEW_ORDER) & (we.detector != "cvae")]
    for (arm, rule), part in new.groupby(["arm", "rule"]):
        ledger.add(statistic="median worst-engine healthy-flight false-flag rate, new cohort", value=float(part.WE_FFR.median()),
                   source=we_path, arm=arm, rule=rule, aggregation=f"median over {len(part)} residual cells",
                   tier="robustness", claim=f"New cohort, arm {ARM_NAME[arm]}, rule {rule}: median worst-engine healthy-flight "
                                            f"false-flag rate {100 * part.WE_FFR.median():.1f}% at locked κ (α = 1%).")
        ledger.add(statistic="share of residual cells with worst-engine false-flag rate >= 10%",
                   value=float((part.WE_FFR >= 0.10).mean()), source=we_path, arm=arm, rule=rule,
                   aggregation=f"share of {len(part)} residual cells", tier="robustness",
                   claim=f"New cohort, arm {ARM_NAME[arm]}, rule {rule}: worst-engine false-flag rate at least 10% in "
                         f"{100 * (part.WE_FFR >= 0.10).mean():.0f}% of residual cells.")
    labels_path = summary_path("matched_labels_alpha_0.01.csv")
    labels = pd.read_csv(labels_path)
    for (arm, rule, group), part in labels.assign(group=np.where(labels.detector == "cvae", "cvae", "residual")).groupby(
            ["arm", "rule", "group"]):
        for label in ("earlier at matched burden", "later at matched burden", "equal", "mixed"):
            count = int((part.matched_label == label).sum())
            ledger.add(statistic=f"runs labelled '{label}'", value=count, source=labels_path, arm=arm, rule=rule,
                       aggregation=f"count over {len(part)} {group} runs (7 subsets)", tier="secondary",
                       claim=f"{ARM_NAME[arm]} versus P, rule {rule}, {group} runs: '{label}' in {count} of {len(part)}.")
    paired_path = summary_path("paired_transport_alpha_0.01.csv")
    paired = pd.read_csv(paired_path)
    new = paired[paired.subset.isin(ec.NEW_ORDER)]
    for arm in ("phase_conditioned", "quantile_regression_W"):
        part = new[new.arm == arm]
        for label, value in (("share of cells with uniform per-engine improvement", part.uniform_improvement.mean()),
                             ("share of cells with at least one engine worse", (part.n_worse >= 1).mean()),
                             ("share of cells with reduced pooled disparity", (part.diff_pooled_A1 < 0).mean())):
            ledger.add(statistic=label, value=float(value), source=paired_path, arm=arm,
                       aggregation=f"share of {len(part)} new-cohort cells", tier="primary",
                       claim=f"New cohort, {ARM_NAME[arm]} versus P (α = 1%): {label} = {100 * value:.0f}%.")
    for key in keys:
        engines_path = audit_path(key, "paired_transport_engines")
        pe = pd.read_csv(engines_path)
        pe = pe[(pe.nominal_fpr == ALPHA) & (pe.detector != "cvae")]
        for (arm, unit), part in pe.groupby(["arm", "unit"]):
            if arm == "phase_conditioned":
                ledger.add(statistic="per-engine A2 under P (median over 7 residual runs)", value=float(part.pooled_arm_A2.median()),
                           source=engines_path, subset=key, engine=int(unit), arm="pooled", aggregation="median over 7 residual runs",
                           tier="primary", claim=f"{key} engine {unit}: median per-engine A2 under P = {100 * part.pooled_arm_A2.median():.2f} pp.")
            ledger.add(statistic=f"per-engine A2 under {ARM_NAME[arm]} (median over 7 residual runs)", value=float(part.arm_A2.median()),
                       source=engines_path, subset=key, engine=int(unit), arm=arm, aggregation="median over 7 residual runs",
                       tier="primary", claim=f"{key} engine {unit}: median per-engine A2 under {ARM_NAME[arm]} = {100 * part.arm_A2.median():.2f} pp.")
            ledger.add(statistic=f"residual runs in which {ARM_NAME[arm]} worsened the engine's A2", value=int((part.diff_A2 > 0).sum()),
                       source=engines_path, subset=key, engine=int(unit), arm=arm, aggregation="count over 7 residual runs",
                       tier="primary", claim=f"{key} engine {unit}: {ARM_NAME[arm]} worsened A2 relative to P in {int((part.diff_A2 > 0).sum())} of 7 residual runs.")
        insample_path = ec.RESULTS / key / "lock" / "calibration_in_sample_phase_fpr.csv"
        ins = pd.read_csv(insample_path)
        ins = ins[(ins.nominal_fpr == ALPHA) & (ins.arm == "pooled")]
        table = ins.pivot_table(index=["detector", "seed"], columns="phase", values="in_sample_fpr")
        count = int((table.idxmax(axis=1) == "descent").sum())
        ledger.add(statistic="calibration-engine (in-sample) runs with descent highest under P", value=count, source=insample_path,
                   subset=key, arm="pooled", rule="R0", aggregation=f"count over {len(table)} runs", tier="secondary",
                   status="descriptive", claim=f"{key}: within the calibration engines, the pooled threshold left descent highest in "
                                               f"{count} of {len(table)} runs (α = 1%).")
    for key in ec.NEW_ORDER:
        record_path = ec.RESULTS / key / "audit" / "audit_record.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        ledger.add(statistic="official-test rows audited (healthy / post-onset)", value=f"{record['healthy_rows']} / "
                   f"{record['post_onset_rows']}", source=record_path, subset=key, aggregation="count",
                   tier="primary", status="descriptive",
                   claim=f"{key}: {record['healthy_rows']:,} healthy and {record['post_onset_rows']:,} post-onset audit rows.")


POST_HOC_STATUS = "post hoc (internal review; not pre-specified)"


def append_post_hoc(path=None):
    """Append the post hoc checks of the extended manuscript (Section 4.8) as new EX rows, append-only.

    Existing rows are left byte-for-byte unchanged; the rows are refused if post hoc rows already exist.
    Source: paper/mssp_extended/evidence/post_hoc_checks.json (paper/mssp_extended/post_hoc_checks.py).
    """
    import csv
    path = Path(path or (ec.DOCS / "EXTENSION_EVIDENCE_LEDGER.csv"))
    existing = pd.read_csv(path)
    if existing.status.astype(str).str.startswith("post hoc").any():
        raise ec.ExtensionError("post hoc rows already present in the ledger")
    source = ec.ROOT / "paper/mssp_extended/evidence/post_hoc_checks.json"
    ph = json.loads(source.read_text(encoding="utf-8"))
    ledger = Ledger(ec.git_sha())
    arms = ph["a2_noise_by_arm"]
    add = lambda statistic, value, claim, arm="", subset="", aggregation="", engine="", rule="": ledger.add(  # noqa: E731
        statistic=statistic, value=value, source=source, claim=claim, tier="robustness", status=POST_HOC_STATUS,
        subset=subset, arm=arm, engine=engine, rule=rule, detector="residual runs", aggregation=aggregation)
    add("median flight-clustered SE of an engine's overall healthy FPR", arms["pooled"]["se_overall_fpr_median"],
        f"Median flight-clustered SE of one engine's healthy FPR {100 * arms['pooled']['se_overall_fpr_median']:.2f} pp (P).",
        arm="pooled", aggregation="median over engine-run pairs")
    for arm, v in arms.items():
        a = ARM_NAME[arm]
        add("null probability that a perfectly calibrated engine reaches A2 >= 0.5 alpha", v["null_p_material_mean"],
            f"Arm {a}: a perfectly calibrated engine reaches the material line in {100 * v['null_p_material_mean']:.0f}% of pairs.",
            arm=arm, aggregation="mean over engine-run pairs (approximate clustered null)")
        add("observed share of engine-run pairs with A2 >= 0.5 alpha", v["observed_share_material"],
            f"Arm {a}: observed share at or above the material line {100 * v['observed_share_material']:.0f}%.",
            arm=arm, aggregation="share of engine-run pairs")
        add("observed share of engine-run pairs above the null 95th percentile", v["observed_share_above_null_q95"],
            f"Arm {a}: observed A2 above the null 95th percentile in {100 * v['observed_share_above_null_q95']:.0f}% of pairs.",
            arm=arm, aggregation="share of engine-run pairs")
        add("share of material per-engine errors that are under-alarming", v["material_share_under_alarming"],
            f"Arm {a}: {100 * v['material_share_under_alarming']:.0f}% of material per-engine errors are under-alarming.",
            arm=arm, aggregation="share of material engine-run pairs")
    for r in ph["we_ffr_null"]:
        add("perfect-calibration worst-engine FFR: median and P(>= 10%)",
            f"{r['null_median']:.4f} / {r['null_p_ge_10pct']:.4f}",
            f"{r['subset']}: null worst-engine FFR median {100 * r['null_median']:.1f}%, P(>= 10%) {r['null_p_ge_10pct']:.2f}; "
            f"observed runs above the null 95th percentile R0/R1/R2 "
            f"{'/'.join(str(round(7 * r[f'observed_share_above_null_q95_{x}'])) for x in ('R0', 'R1', 'R2'))} of 7.",
            arm="pooled", subset=r["subset"], aggregation="binomial null with kappa sampling; 200,000 draws")
    for arm, v in ph["engine_improvement"].items():
        add("mean share of audit engines improved per cell", v["mean_share_engines_improved"],
            f"Arm {ARM_NAME[arm]}: on average {100 * v['mean_share_engines_improved']:.0f}% of audit engines improved per cell "
            f"(every engine: {100 * v['share_cells_every_engine_improved']:.0f}% observed, "
            f"{100 * v['coin_flip_expectation']:.1f}% under a coin flip).", arm=arm, aggregation="mean over 70 cells")
    w = ph["ds04_runs_every_engine_within_material_line"]
    add("DS04 runs with every audit engine within the material line", f"Q {w['quantile_regression_W']}; P {w['pooled']}; "
        f"C {w['phase_conditioned']}", f"DS04: every engine within 0.5 pp in {w['quantile_regression_W']}/7 runs (Q), "
        f"{w['pooled']}/7 (P), {w['phase_conditioned']}/7 (C).", subset="DS04", aggregation="count over 7 residual runs")
    e = ph["ds08a_engine14"]
    add("DS08a engine 14: share of healthy alarms on one flight", e["share_of_healthy_alarms"],
        f"DS08a engine 14 flight {e['flight']} carries {100 * e['share_of_healthy_alarms']:.0f}% of healthy alarms under P; "
        f"FPR {100 * e['fpr_all_flights']:.2f}% -> {100 * e['fpr_without_flight']:.2f}% without it; altitude span "
        f"{e['flight_altitude_span_ft']:,.0f} ft vs fit <= {e['fit_max_altitude_span_ft']:,.0f} ft and calibration <= "
        f"{e['calibration_max_altitude_span_ft']:,.0f} ft.", subset="DS08a", engine=14, arm="pooled",
        aggregation="median over 7 residual runs of per-flight alarms")
    ms = ph["mission_sharing"]
    add("same-class recorded-mission sharing (audit vs calibration engine)",
        "; ".join(f"class {c}: {v['min']:.3f}-{v['max']:.3f}" for c, v in ms["same_class_by_audit_class"].items()),
        f"Same-class audit-calibration pairs share healthy flight profiles; other-class maximum {ms['other_class_max']:.0f}.",
        aggregation="shared signatures / audit healthy flights")
    for arm, v in ph["coverage_by_audit_class"].items():
        add("coverage effect by audit-engine class", "; ".join(f"class {c}: {x:+.5f}" for c, x in v.items()),
            f"Arm {ARM_NAME[arm]}: median per-engine coverage effect by audit class.", arm=arm,
            aggregation="median over engines of per-engine run medians")
    for arm, v in ph["balanced_design"].items():
        add("class-balanced design better than best / mean single-engine design",
            f"{v['better_than_best_single']} / {v['better_than_mean_single']} of {v['residual_runs']}",
            f"Arm {ARM_NAME[arm]}: balanced design beats the best single engine in {v['better_than_best_single']} of "
            f"{v['residual_runs']} runs.", arm=arm, aggregation="count over residual runs")
    cv = ph["cvae_vs_residual"]
    add("CVAE minus median residual detector ME-A2 (P)", cv["median_over_families_vs_median"],
        f"The CVAE's ME-A2 under P exceeds the median residual detector's by {100 * cv['median_over_families_vs_median']:.2f} pp.",
        arm="pooled", aggregation="median over families of family means")
    for key, v in ph["bootstrap_class_omission_probability"].items():
        add("probability that a U-EXT1 replicate omits a calibration class", v,
            f"{key}: {100 * v:.0f}% of calibration-engine bootstrap replicates omit a class.", subset=key,
            aggregation="design-based (resampling with replacement)")
    for arm, v in ph["two_flight_confirmation"].items():
        add("two-flight confirmation: worst-engine confirmed-alert rate zero / >= 10%; median delay",
            f"{v['we_two_zero']} / {v['we_two_ge_10pct']} of {v['residual_runs']}; delay {v['median_delay_single']:g} -> "
            f"{v['median_delay_two']:g}", f"Arm {ARM_NAME[arm]}: two-flight confirmation at locked kappa.", arm=arm, rule="R0",
            aggregation="residual runs")
    es = ph["early_sensitivity_pooled"]
    add("first-10-flight abnormal-state row alarm rate (P): min / median / max",
        f"{es['min']:.5f} / {es['median']:.5f} / {es['max']:.5f}",
        f"Early abnormal-state alarm rate under P {100 * es['min']:.2f}-{100 * es['max']:.2f}% (median {100 * es['median']:.2f}%).",
        arm="pooled", aggregation="over residual runs")
    start = len(existing)
    columns = list(existing.columns)
    with path.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        for i, row in enumerate(ledger.rows, start=1):
            row["ex_id"] = f"EX{start + i:06d}"
            writer.writerow({c: row.get(c, "") for c in columns})
    return len(ledger.rows)


VALIDATION_STATUS = "focused validation (post hoc; author-approved plan d85aa10)"


def append_focused_validation(path=None):
    """Append the final focused validation results as new EX rows (append-only; refused if already present)."""
    import csv
    path = Path(path or (ec.DOCS / "EXTENSION_EVIDENCE_LEDGER.csv"))
    existing = pd.read_csv(path)
    if existing.status.astype(str).str.startswith("focused validation").any():
        raise ec.ExtensionError("focused validation rows already present in the ledger")
    root = ec.RESULTS / "focused_validation" / "summary"
    ledger = Ledger(ec.git_sha())

    def add(statistic, value, claim, source, tier, **kw):
        ledger.add(statistic=statistic, value=value, source=root / source, claim=claim, tier=tier,
                   status=VALIDATION_STATUS, **kw)

    summary = json.loads((root / "focused_validation_summary.json").read_text(encoding="utf-8"))
    add("transport claim (pre-declared interpretation, plan section 6)", summary["transport_claim"],
        f"Pre-declared reading: {summary['transport_claim']} (families showing excess under C: "
        f"{summary['families_showing_excess_under_C']}/5; cross-fit self-calibration floor).",
        "focused_validation_summary.json", "primary")
    add("local recalibration verdict (pre-declared)", summary["local_recalibration_verdict"],
        f"Pre-declared reading of K = 5 local recalibration: {summary['local_recalibration_verdict']}.",
        "focused_validation_summary.json", "robustness")
    engines = pd.read_csv(root / "engine_summary.csv")
    for r in engines.itertuples():
        add("per-engine observed A2 vs cross-fit NF95 (median over residual runs)",
            f"{r.observed_A2_median:.6f} / {r.NF95_median:.6f}",
            f"{r.subset} engine {r.unit}, arm {ARM_NAME[r.arm]}: observed A2 {100 * r.observed_A2_median:.2f} pp, "
            f"NF95 {100 * r.NF95_median:.2f} pp, above in {r.residual_runs_exceeding}/7 runs "
            f"({'clearly exceeds' if r.clearly_exceeds else 'does not clearly exceed'}).",
            "engine_summary.csv", "primary", subset=r.subset, engine=int(r.unit), arm=r.arm, detector="residual runs",
            aggregation="median over 7 residual runs; exceedance count")
    families = pd.read_csv(root / "family_summary.csv")
    for r in families.itertuples():
        add("engines clearly exceeding their own noise reference, per family", f"{r.clearly_exceeding}/{r.engines}",
            f"{r.family}, arm {ARM_NAME[r.arm]}: {r.clearly_exceeding} of {r.engines} engines clearly exceed "
            f"({'shows' if r.shows_excess else 'does not show'} excess).", "family_summary.csv", "primary", arm=r.arm,
            aggregation="count of engines (>= 4/7 residual runs above NF95)")
    local = pd.read_csv(root / "local_engine_summary.csv")
    for r in local.itertuples():
        add("K = 5 local recalibration: fleet minus local A2 (median over residual runs)", r.improvement_median,
            f"{r.subset} engine {r.unit}, arm {ARM_NAME[r.arm]}: fleet {100 * r.fleet_eval_A2_median:.2f} pp, local "
            f"{100 * r.local_A2_median:.2f} pp on {r.eval_flights} evaluation flights; local within NF95K in "
            f"{r.runs_local_within_NFK95}/7 runs.", "local_engine_summary.csv", "robustness", subset=r.subset,
            engine=int(r.unit), arm=r.arm, detector="residual runs", aggregation="median over 7 residual runs")
    width = pd.read_csv(root / "bootstrap_width_comparison.csv")
    for r in width.itertuples():
        add("class-preserving / original bootstrap interval width (median over residual runs)", r.median_width_ratio,
            f"{r.subset} {r.metric}: width ratio {r.median_width_ratio:.3f}; share from class omission "
            f"{100 * r.share_of_width_from_class_omission:.0f}%.", "bootstrap_width_comparison.csv", "secondary",
            subset=r.subset, detector="residual runs", aggregation="median over 7 residual runs")
    u2 = pd.read_csv(root / "uext2_original_vs_class_preserving.csv")
    for r in u2.itertuples():
        add("U-EXT2 interval, original vs class-preserving",
            f"[{r.ci_lower_95_original:.6f}, {r.ci_upper_95_original:.6f}] / [{r.ci_lower_95_class_preserving:.6f}, "
            f"{r.ci_upper_95_class_preserving:.6f}]",
            f"{r.detector_family} {r.quantity}: width ratio {r.width_ratio:.2f}.", "uext2_original_vs_class_preserving.csv",
            "secondary", aggregation="family -> subset -> replicate bootstrap")
    start = len(existing)
    columns = list(existing.columns)
    with path.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        for i, row in enumerate(ledger.rows, start=1):
            row["ex_id"] = f"EX{start + i:06d}"
            writer.writerow({c: row.get(c, "") for c in columns})
    return len(ledger.rows)


if __name__ == "__main__":
    import sys
    if "--append-post-hoc" in sys.argv:
        print(append_post_hoc())
    elif "--append-focused-validation" in sys.argv:
        print(append_focused_validation())
    else:
        print(len(build()))
