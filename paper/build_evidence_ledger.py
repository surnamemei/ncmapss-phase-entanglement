"""Rebuild the manuscript evidence ledger from executed CSVs only."""

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper"
SOURCES = {
    "DS02 discovery": "results/final_validation",
    "DS03 confirmation": "results/confirmation_ds03",
}
FIELDS = [
    "claim_id", "dataset", "detector", "seed_or_seed_aggregation",
    "phase_rule", "nominal_fpr_target", "evaluation_unit", "analysis_detail",
    "metric", "metric_definition", "exact_numeric_value", "value_unit",
    "ci_lower_95", "ci_upper_95", "ci_method", "ci_source_csv",
    "ci_source_rows", "source_csv", "source_file", "source_rows", "corresponding_figure",
    "evidence_status",
]
DESCRIPTIONS = {
    "overall_fpr": ("Healthy audit rows alarmed / all healthy audit rows, pooled or within engine as indicated.", "fraction"),
    "climb_fpr": ("Healthy climb audit rows alarmed / healthy climb audit rows.", "fraction"),
    "cruise_fpr": ("Healthy cruise audit rows alarmed / healthy cruise audit rows.", "fraction"),
    "descent_fpr": ("Healthy descent audit rows alarmed / healthy descent audit rows.", "fraction"),
    "descent_minus_climb": ("Descent healthy row-FPR minus climb healthy row-FPR; percentage-point difference when multiplied by 100.", "fraction difference"),
    "descent_minus_cruise": ("Descent healthy row-FPR minus cruise healthy row-FPR; percentage-point difference when multiplied by 100.", "fraction difference"),
    "max_min_phase_ratio": ("Maximum divided by minimum of the three phase healthy row-FPRs.", "ratio"),
    "worst_cross_phase_transfer_fpr": ("Maximum audit healthy row-FPR among off-diagonal calibration-phase to audit-phase threshold transfers.", "fraction"),
    "score_only_phase_balanced_accuracy": ("Balanced accuracy of phase classification using detector score alone.", "fraction"),
}
for phase in ("climb", "cruise", "descent"):
    DESCRIPTIONS[f"healthy_flights_with_alarm_{phase}"] = (
        f"Fraction of healthy flights with at least one {phase}-phase false alarm.", "fraction"
    )
    DESCRIPTIONS[f"false_alarm_events_per_healthy_flight_{phase}"] = (
        f"Mean number of contiguous {phase}-phase false-alarm events per healthy flight.",
        "events per healthy flight",
    )


def read(relpath):
    with (ROOT / relpath).open(newline="", encoding="utf-8-sig") as handle:
        return [(line, row) for line, row in enumerate(csv.DictReader(handle), 2)]


ledger = []
index = {}


def add(dataset, detector, seed, phase_rule, target, unit, detail, metric,
        value, source, rows, description, value_unit, *, ci=None):
    evidence_id = f"E{len(ledger) + 1:06d}"
    ci = ci or {}
    item = dict.fromkeys(FIELDS, "")
    item.update(
        claim_id=evidence_id,
        dataset=dataset,
        detector=detector,
        seed_or_seed_aggregation=str(seed),
        phase_rule=phase_rule,
        nominal_fpr_target=str(target),
        evaluation_unit=unit,
        analysis_detail=detail,
        metric=metric,
        metric_definition=description,
        exact_numeric_value=str(value),
        value_unit=value_unit,
        ci_lower_95=ci.get("ci_lower_95", ""),
        ci_upper_95=ci.get("ci_upper_95", ""),
        ci_method=ci.get("method", ""),
        ci_source_csv=ci.get("source", ""),
        ci_source_rows=ci.get("rows", ""),
        source_csv=source,
        source_rows=";".join(map(str, rows)),
        evidence_status="exploratory" if dataset == "DS02 discovery" else "confirmatory",
    )
    ledger.append(item)
    index[(dataset, detector, str(seed), phase_rule, str(target), unit, detail, metric)] = evidence_id
    return evidence_id


for dataset, directory in SOURCES.items():
    canonical_path = f"{directory}/canonical_results.csv"
    bootstrap_path = f"{directory}/hierarchical_bootstrap_ci.csv"
    bootstrap = {}
    for line, row in read(bootstrap_path):
        key = (row["detector"], row["seed"], row["phase_rule"],
               row["nominal_fpr_target"], row["metric"])
        if key in bootstrap:
            raise ValueError(f"Duplicate bootstrap key: {key}")
        bootstrap[key] = (line, row)
    grouped = defaultdict(list)
    matched_ci = set()
    for line, row in read(canonical_path):
        detector, seed = row["detector"], row["seed"]
        phase_rule, target, unit = (row["phase_rule"], row["nominal_fpr_target"],
                                    row["evaluation_unit"])
        grouped[(detector, phase_rule, target, unit)].append((line, row))
        for metric, value in row.items():
            if metric not in DESCRIPTIONS:
                continue
            ci = None
            ci_key = (detector, seed, phase_rule, target, metric)
            if unit == "pooled" and ci_key in bootstrap:
                ci_line, ci_row = bootstrap[ci_key]
                ci = {
                    "ci_lower_95": ci_row["ci_lower_95"],
                    "ci_upper_95": ci_row["ci_upper_95"],
                    "method": "hierarchical engine-then-flight bootstrap; threshold re-estimated; 2000 replicates",
                    "source": bootstrap_path,
                    "rows": str(ci_line),
                }
                matched_ci.add(ci_key)
            desc, value_unit = DESCRIPTIONS[metric]
            add(dataset, detector, seed, phase_rule, target, unit, "canonical",
                metric, value, canonical_path, [line], desc, value_unit, ci=ci)
    if matched_ci != set(bootstrap):
        raise ValueError(f"Unmatched bootstrap rows: {set(bootstrap) - matched_ci}")

    # This is the arithmetic mean of three reported seed-level results, never a
    # pooled score or a bootstrap interval for the mean.
    for (detector, phase_rule, target, unit), members in grouped.items():
        if detector == "pca":
            continue
        if sorted(row["seed"] for _, row in members) != ["0", "1", "2"]:
            raise ValueError(f"Unexpected seed set: {(dataset, detector, phase_rule, target, unit)}")
        for metric, (desc, value_unit) in DESCRIPTIONS.items():
            if metric not in members[0][1]:
                continue
            value = mean(float(row[metric]) for _, row in members)
            add(dataset, detector, "mean(seeds 0,1,2)", phase_rule, target,
                unit, "arithmetic seed mean", metric, repr(value),
                canonical_path, [line for line, _ in members],
                f"Arithmetic mean over seeds 0, 1, 2 of: {desc} No CI for the seed mean was executed.",
                value_unit)

    # The executed bootstrap mean is a separate estimate; it is not substituted
    # for the empirical canonical point estimate.
    for (detector, seed, phase_rule, target, metric), (line, row) in bootstrap.items():
        desc, value_unit = DESCRIPTIONS[metric]
        add(dataset, detector, seed, phase_rule, target, "pooled",
            "bootstrap distribution", f"bootstrap_mean_{metric}",
            row["bootstrap_mean"], bootstrap_path, [line],
            f"Mean across 2000 hierarchical engine-then-flight bootstrap replicates, with calibration threshold re-estimated, of: {desc}",
            value_unit,
            ci={"ci_lower_95": row["ci_lower_95"],
                "ci_upper_95": row["ci_upper_95"],
                "method": "hierarchical engine-then-flight bootstrap; threshold re-estimated; 2000 replicates",
                "source": bootstrap_path, "rows": str(line)})

    # Denominators and counts permit auditing of the row-FPR numerator.
    rates_path = (f"{directory}/executed_row_false_alarm_rates.csv"
                  if dataset == "DS02 discovery" else f"{directory}/row_false_alarm_rates.csv")
    for line, row in read(rates_path):
        unit = "pooled" if row["unit"] == "all" else f"engine_{row['unit']}"
        detail = f"healthy row counts; phase={row['phase']}; flight_class={row['flight_class']}"
        for metric, desc in (
            ("n", "Number of healthy audit rows in the specified phase and evaluation unit."),
            ("false_alarms", "Number of healthy audit rows whose detector score exceeded the calibrated threshold."),
        ):
            add(dataset, row["detector"], row["seed"], row["phase_definition"],
                row["nominal_fpr"], unit, detail, metric, row[metric], rates_path,
                [line], desc, "rows")

    transfer_path = (f"{directory}/executed_threshold_transfer_matrix.csv"
                     if dataset == "DS02 discovery" else f"{directory}/threshold_transfer_matrix.csv")
    for line, row in read(transfer_path):
        unit = "pooled" if row["unit"] == "all" else f"engine_{row['unit']}"
        detail = (f"calibration_phase={row['calibration_phase']}; "
                  f"audit_phase={row['test_phase']}; flight_class={row['flight_class']}")
        for metric, desc, value_unit in (
            ("false_alarm_rate", "Healthy audit-phase rows exceeding the calibration-phase threshold / healthy audit-phase rows.", "fraction"),
            ("n", "Number of healthy audit-phase rows in this cross-phase transfer cell.", "rows"),
            ("false_alarms", "Number of healthy audit-phase rows exceeding the transferred threshold.", "rows"),
            ("threshold", "Score threshold estimated from the specified calibration phase at the nominal FPR target.", "score"),
        ):
            add(dataset, row["detector"], row["seed"], row["phase_definition"],
                row["nominal_fpr"], unit, detail, metric, row[metric],
                transfer_path, [line], desc, value_unit)

    if dataset == "DS03 confirmation":
        flights_path = f"{directory}/flight_alarm_summary.csv"
        for line, row in read(flights_path):
            unit = "pooled" if row["unit"] == "all" else f"engine_{row['unit']}"
            detail = f"phase={row['phase']}; flight_class={row['flight_class']}"
            add(dataset, row["detector"], row["seed"], row["phase_definition"],
                row["nominal_fpr"], unit, detail, "healthy_flights",
                row["healthy_flights"], flights_path, [line],
                "Number of healthy flights forming the denominator of the flight-alarm fraction.", "flights")
    else:
        probe_path = f"{directory}/executed_score_only_phase_prediction.csv"
        for line, row in read(probe_path):
            unit = "pooled" if row["unit"] == "all" else f"engine_{row['unit']}"
            detail = f"flight_class={row['flight_class']}"
            add(dataset, row["detector"], row["seed"], row["phase_definition"],
                "not applicable", unit, detail, "chance_balanced_accuracy",
                row["chance_balanced_accuracy"], probe_path, [line],
                "Chance-level balanced accuracy for the three-phase score-only classifier.", "fraction")

    history_path = f"{directory}/lstm_training_history.csv"
    history_groups = defaultdict(list)
    for line, row in read(history_path):
        history_groups[(row["seed"], row["stage"])].append((line, row))
    for (seed, stage), samples in history_groups.items():
        samples.sort(key=lambda pair: int(pair[1]["epoch"]))
        first_line, first = samples[0]
        last_line, last = samples[-1]
        detail = f"training-only; stage={stage}"
        for metric, value, source_line, desc, value_unit in (
            ("selected_epoch", first["best_epoch"], first_line,
             "Epoch selected by engine-disjoint validation with patience 6 and minimum improvement 0.0001; applied to full-training-engine refit.", "epochs"),
            ("epochs_run", first["epochs_run"], first_line,
             "Number of epochs executed in this training stage.", "epochs"),
            ("max_epochs", first["max_epochs"], first_line,
             "Prespecified maximum permitted training epochs.", "epochs"),
            ("final_train_loss", last["train_loss"], last_line,
             "Training reconstruction loss at final recorded epoch of this training stage.", "loss"),
        ):
            add(dataset, "lstm_autoencoder", seed, "not applicable", "", "training engines",
                detail, metric, value, history_path, [source_line], desc, value_unit)
        if stage == "engine_disjoint_epoch_selection":
            add(dataset, "lstm_autoencoder", seed, "not applicable", "", "held-out fit engine",
                detail, "final_validation_loss", last["validation_loss"], history_path,
                [last_line], "Validation reconstruction loss at the final epoch of engine-disjoint epoch selection.", "loss")
            selected = int(first["best_epoch"])
            selected_line, selected_row = next((line, row) for line, row in samples
                                               if int(row["epoch"]) == selected)
            add(dataset, "lstm_autoencoder", seed, "not applicable", "", "held-out fit engine",
                detail, "selected_epoch_validation_loss", selected_row["validation_loss"],
                history_path, [selected_line],
                "Validation reconstruction loss at the early-stopping selected epoch.", "loss")
            for window in (20, 50, 100):
                if len(samples) < window:
                    continue
                tail = samples[-window:]
                xs = [int(row["epoch"]) for _, row in tail]
                ys = [float(row["validation_loss"]) for _, row in tail]
                xbar, ybar = mean(xs), mean(ys)
                slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / sum(
                    (x - xbar) ** 2 for x in xs)
                add(dataset, "lstm_autoencoder", seed, "not applicable", "", "held-out fit engine",
                    detail, f"final_{window}_epoch_validation_loss_slope", repr(slope),
                    history_path, [line for line, _ in tail],
                    f"Ordinary least-squares slope of validation loss versus epoch across the final {window} executed selection epochs.",
                    "loss per epoch")

# The boundary table is an executed DS02 LSTM diagnostic, not a DS03 endpoint.
boundary_path = "results/final_validation/lstm_boundary_audit.csv"
for line, row in read(boundary_path):
    detail = f"subset={row['subset']}; category={row['category']}; phase={row['phase']}"
    for metric, desc, unit in (
        ("n", "Number of sequence-endpoint rows in this boundary category and phase.", "rows"),
        ("mean_reconstruction_error", "Mean LSTM reconstruction error in this boundary category and phase.", "score"),
        ("median_reconstruction_error", "Median LSTM reconstruction error in this boundary category and phase.", "score"),
        ("p95_reconstruction_error", "95th percentile LSTM reconstruction error in this boundary category and phase.", "score"),
        ("false_alarm_rate", "Fraction of healthy sequence-endpoint rows alarmed in this boundary category and phase.", "fraction"),
    ):
        add("DS02 discovery", "lstm_autoencoder", row["seed"], row["phase_rule"],
            row["nominal_fpr"], row["subset"], detail, metric, row[metric],
            boundary_path, [line], desc, unit)

# User-authorized executed Phase 3A correction comparison. Reconstruct each
# cell from its executed component CSVs before admitting it to the ledger.
comparison_path = "results/phase3_dynamic_correction/correction_comparison.csv"
comparison_dir = "results/phase3_dynamic_correction"
rate_rows = [row for _, row in read(f"{comparison_dir}/row_false_alarm_rates.csv")]
transfer_rows = [row for _, row in read(f"{comparison_dir}/threshold_transfer_matrix.csv")]
flight_rows = [row for _, row in read(f"{comparison_dir}/flight_alarm_summary.csv")]
probe_rows = [row for _, row in read(f"{comparison_dir}/score_only_phase_prediction.csv")]


def unique(rows, **where):
    found = [row for row in rows if all(row.get(key) == value for key, value in where.items())]
    if len(found) != 1:
        raise ValueError(f"Expected one executed component row, got {len(found)}: {where}")
    return found[0]


def same(actual, expected):
    if not math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError(f"Correction comparison mismatch: {actual} != {expected}")


comparison_count = 0
for line, row in read(comparison_path):
    correction, phase_rule = row["correction"], row["phase_definition"]
    rate = lambda phase: unique(rate_rows, detector=correction, phase_definition=phase_rule,
                                subset="official_test", unit="all", phase=phase)
    transfer = [item for item in transfer_rows
                if item["detector"] == correction and item["phase_definition"] == phase_rule
                and item["unit"] == "all" and item["calibration_phase"] != item["test_phase"]]
    if len(transfer) != 6:
        raise ValueError("Incomplete off-diagonal transfer matrix")
    flight = lambda phase: unique(flight_rows, detector=correction,
                                  phase_definition=phase_rule, subset="official_test",
                                  unit="all", phase=phase)
    probe = unique(probe_rows, detector=correction, phase_definition=phase_rule, unit="all")
    for phase in ("overall", "climb", "cruise", "descent"):
        same(row[f"{phase}_fpr"], rate(phase)["false_alarm_rate"])
        observed = rate(phase)
        same(observed["false_alarm_rate"], int(observed["false_alarms"]) / int(observed["n"]))
    phase_values = [float(rate(phase)["false_alarm_rate"])
                    for phase in ("climb", "cruise", "descent")]
    same(row["max_min_phase_fpr_ratio"], max(phase_values) / min(phase_values))
    same(row["worst_offdiagonal_transfer_fpr"],
         max(float(item["false_alarm_rate"]) for item in transfer))
    same(row["score_only_phase_balanced_accuracy"], probe["balanced_accuracy"])
    for phase in ("climb", "cruise", "descent"):
        same(row[f"{phase}_flights_with_alarm"],
             flight(phase)["fraction_flights_with_false_alarm"])
    same(row["events_per_flight"], flight("overall")["events_per_healthy_flight"])
    comparison_count += 1
    if phase_rule != "primary":
        continue
    detail = f"executed Phase 3A PCA correction comparison; correction={correction}"
    mapping = {
        "overall_fpr": "overall_fpr", "climb_fpr": "climb_fpr",
        "cruise_fpr": "cruise_fpr", "descent_fpr": "descent_fpr",
        "max_min_phase_fpr_ratio": "max_min_phase_ratio",
        "worst_offdiagonal_transfer_fpr": "worst_cross_phase_transfer_fpr",
        "score_only_phase_balanced_accuracy": "score_only_phase_balanced_accuracy",
        "climb_flights_with_alarm": "healthy_flights_with_alarm_climb",
        "cruise_flights_with_alarm": "healthy_flights_with_alarm_cruise",
        "descent_flights_with_alarm": "healthy_flights_with_alarm_descent",
    }
    for source_metric, ledger_metric in mapping.items():
        desc, value_unit = DESCRIPTIONS[ledger_metric]
        add("DS02 discovery", "pca", "-1", "primary", "0.01", "pooled",
            detail, ledger_metric, row[source_metric], comparison_path, [line],
            f"Executed correction comparison ({correction}); {desc}", value_unit)
    for metric, other in (("descent_minus_climb", "climb"),
                          ("descent_minus_cruise", "cruise")):
        desc, value_unit = DESCRIPTIONS[metric]
        value = float(row["descent_fpr"]) - float(row[f"{other}_fpr"])
        add("DS02 discovery", "pca", "-1", "primary", "0.01", "pooled",
            detail, metric, repr(value), comparison_path, [line],
            f"Derived from the executed correction comparison ({correction}); {desc}", value_unit)
    add("DS02 discovery", "pca", "-1", "primary", "0.01", "pooled",
        detail, "false_alarm_events_per_healthy_flight_overall",
        row["events_per_flight"], comparison_path, [line],
        "Mean contiguous false-alarm events per healthy flight across all phases in the executed correction comparison.",
        "events per healthy flight")
assert comparison_count == 6

# Configuration evidence is kept distinct from numerical outcome evidence.
# These are executed code/configuration references, not fabricated CSV results.
METHOD_SPECS = [
    ("M0001", "DS02 discovery", "sensor_channels", "14", "channels", "src/second_stage_audit.py", "30-31"),
    ("M0002", "DS03 confirmation", "primary_altitude_fraction", "0.90", "fraction", "src/confirm_frozen_ds03.py", "53"),
    ("M0003", "DS02 discovery", "history_windows", "30,120", "samples at 1 Hz", "src/phase3_dynamic.py", "30"),
    ("M0004", "DS03 confirmation", "ridge_alpha", "1.0", "ridge penalty", "src/confirm_frozen_ds03.py", "477"),
    ("M0005", "DS02 discovery", "pca_components", "5", "components", "src/second_stage_audit.py", "38"),
    ("M0006", "DS03 confirmation", "isolation_forest_trees", "200", "trees", "src/confirm_frozen_ds03.py", "493"),
    ("M0007", "DS03 confirmation", "isolation_forest_max_samples", "8192", "rows per tree", "src/confirm_frozen_ds03.py", "493"),
    ("M0008", "DS03 confirmation", "lstm_sequence_length", "256", "rows", "src/final_validation.py", "51"),
    ("M0009", "DS03 confirmation", "lstm_batch_size", "256", "sequences", "src/final_validation.py", "289"),
    ("M0010", "DS03 confirmation", "lstm_encoder_units", "16", "units", "src/final_validation.py", "233"),
    ("M0011", "DS03 confirmation", "lstm_dense_width", "8", "units", "src/final_validation.py", "234"),
    ("M0012", "DS03 confirmation", "lstm_decoder_units", "16", "units", "src/final_validation.py", "235"),
    ("M0013", "DS03 confirmation", "lstm_adam_learning_rate", "0.001", "learning rate", "src/confirm_frozen_ds03.py", "184"),
    ("M0014", "DS03 confirmation", "lstm_maximum_epochs", "600", "epochs", "src/final_validation.py", "46"),
    ("M0015", "DS03 confirmation", "lstm_patience", "6", "epochs", "src/final_validation.py", "47"),
    ("M0016", "DS03 confirmation", "lstm_minimum_improvement", "0.0001", "validation loss", "src/final_validation.py", "48"),
    ("M0017", "DS03 confirmation", "stochastic_seeds", "0,1,2", "seed identifiers", "src/final_validation.py", "56"),
    ("M0018", "DS03 confirmation", "nominal_fpr_targets", "0.005,0.01,0.02", "fractions", "src/final_validation.py", "57"),
    ("M0019", "DS03 confirmation", "bootstrap_replicates", "2000", "replicates", "src/final_validation.py", "53"),
    ("M0020", "DS02 discovery", "model_fit_engines", "2,5,10,16", "engine IDs", "results/final_validation/run_config.json", "3-8"),
    ("M0021", "DS02 discovery", "calibration_engines", "18,20", "engine IDs", "results/final_validation/run_config.json", "9-12"),
    ("M0022", "DS02 discovery", "official_audit_engines", "11,14,15", "engine IDs", "results/final_validation/run_config.json", "13-17"),
    ("M0023", "DS02 discovery", "epoch_selection_fit_engines", "2,5,10", "engine IDs", "results/final_validation/run_config.json", "54-58"),
    ("M0024", "DS02 discovery", "epoch_selection_validation_engine", "16", "engine ID", "results/final_validation/run_config.json", "59"),
    ("M0025", "DS03 confirmation", "model_fit_engines", "1,2,3,5,6,7,9", "engine IDs", "results/confirmation_ds03/pre_audit_plan.json", "15-23"),
    ("M0026", "DS03 confirmation", "calibration_engines", "4,8", "engine IDs", "results/confirmation_ds03/pre_audit_plan.json", "24-27"),
    ("M0027", "DS03 confirmation", "official_audit_engines", "10,11,12,13,14,15", "engine IDs", "results/confirmation_ds03/run_config.json", "95-102"),
    ("M0028", "DS03 confirmation", "epoch_selection_fit_engines", "1,2,3,5,6,7", "engine IDs", "results/confirmation_ds03/pre_audit_plan.json", "28-35"),
    ("M0029", "DS03 confirmation", "epoch_selection_validation_engine", "9", "engine ID", "results/confirmation_ds03/pre_audit_plan.json", "36"),
    ("M0030", "DS02 discovery", "sample_frequency", "1", "Hz", "src/second_stage_audit.py", "59"),
    ("M0031", "DS03 confirmation", "bootstrap_interval_coverage", "0.95", "coverage fraction", "src/final_validation.py", "736-737"),
    ("M0032", "DS03 confirmation", "static_basis_polynomial_degree", "3", "degree", "src/phase3_dynamic.py", "79"),
]
for method_id, dataset, metric, value, value_unit, source, lines in METHOD_SPECS:
    item = dict.fromkeys(FIELDS, "")
    item.update(claim_id=method_id, dataset=dataset, detector="protocol",
                seed_or_seed_aggregation="not applicable", phase_rule="not applicable",
                nominal_fpr_target="not applicable", evaluation_unit="not applicable",
                analysis_detail="executed method configuration, not an outcome",
                metric=metric, metric_definition=f"Executed protocol parameter: {metric.replace('_', ' ')}.",
                exact_numeric_value=value, value_unit=value_unit, source_file=source,
                source_rows=lines,
                evidence_status="exploratory" if dataset == "DS02 discovery" else "confirmatory")
    ledger.append(item)

# Frozen-rule denominator and exception count, evaluated over every DS03
# primary-target per-engine detector/seed row (not selected by effect size).
ds03_canonical_path = "results/confirmation_ds03/canonical_results.csv"
ds03_engine_rows = [(line, row) for line, row in read(ds03_canonical_path)
                    if row["phase_rule"] == "primary"
                    and row["nominal_fpr_target"] == "0.01"
                    and row["evaluation_unit"].startswith("engine_")]
assert len(ds03_engine_rows) == 42
ds03_exceptions = [(line, row) for line, row in ds03_engine_rows
                   if float(row["descent_minus_climb"]) <= 0
                   or float(row["descent_minus_cruise"]) <= 0]
assert len(ds03_exceptions) == 3
for metric, value, definition in (
    ("per_engine_detector_seed_rows_tested", len(ds03_engine_rows),
     "Count of all DS03 primary-target per-engine PCA, Isolation Forest seed, and LSTM seed rows tested under the frozen directional rule."),
    ("per_engine_directional_exception_rows", len(ds03_exceptions),
     "Count of DS03 primary-target per-engine detector/seed rows with nonpositive descent-minus-climb or descent-minus-cruise contrast."),
):
    add("DS03 confirmation", "PCA+IF+LSTM", "all frozen runs", "primary", "0.01",
        "per-engine", "frozen directional rule audit", metric, value,
        ds03_canonical_path, [line for line, _ in ds03_engine_rows],
        definition, "engine-detector-seed rows")

# Confirmation provenance is stated by the authoritative executed report.
for method_id, metric, value, lines, definition in (
    ("M0033", "official_nasa_distribution", "1", "3",
     "The executed confirmation report identifies the source as the official NASA N-CMAPSS DS03 distribution."),
    ("M0034", "official_test_array_open_count", "1", "5",
     "The executed confirmation report states that official-test arrays were opened once, after model fitting and calibration thresholds were locked."),
):
    item = dict.fromkeys(FIELDS, "")
    item.update(claim_id=method_id, dataset="DS03 confirmation", detector="protocol",
                seed_or_seed_aggregation="not applicable", phase_rule="primary",
                nominal_fpr_target="not applicable", evaluation_unit="not applicable",
                analysis_detail="executed confirmation provenance, not an outcome",
                metric=metric, metric_definition=definition,
                exact_numeric_value=value, value_unit="boolean/count",
                source_file="results/confirmation_ds03/CONFIRMATION_REPORT.md",
                source_rows=lines, evidence_status="confirmatory")
    ledger.append(item)

# Added after outcome IDs are fixed so existing evidence references remain stable.
for method_id, metric, value, unit, lines in (
    ("M0035", "alternative_altitude_fraction", "0.85", "fraction", "63-69"),
    ("M0036", "alternative_centered_rate_window", "60", "seconds", "58-66"),
    ("M0037", "alternative_absolute_altitude_rate_limit", "2.0", "altitude units per second", "66-69"),
):
    item = dict.fromkeys(FIELDS, "")
    item.update(claim_id=method_id, dataset="DS02 discovery", detector="protocol",
                seed_or_seed_aggregation="not applicable", phase_rule="alt_rate",
                nominal_fpr_target="not applicable", evaluation_unit="not applicable",
                analysis_detail="executed exploratory phase-rule configuration, not an outcome",
                metric=metric, metric_definition=f"Executed alternative phase-rule parameter: {metric.replace('_', ' ')}.",
                exact_numeric_value=value, value_unit=unit,
                source_file="src/second_stage_audit.py", source_rows=lines,
                evidence_status="exploratory")
    ledger.append(item)


def eid(dataset, detector, seed, phase, target, unit, metric, detail="canonical"):
    if str(seed).startswith("mean(") and detail == "canonical":
        detail = "arithmetic seed mean"
    return index[(dataset, detector, str(seed), phase, str(target), unit, detail, metric)]


claims = []


def claim(claim_id, manuscript_claim, supported, overclaim, evidence):
    claims.append((claim_id, manuscript_claim, supported, overclaim,
                   ", ".join(dict.fromkeys(evidence))))


for dataset, claim_id in (("DS02 discovery", "C01"), ("DS03 confirmation", "C02")):
    ids = [eid(dataset, detector, seed, "primary", "0.01", "pooled", metric)
           for detector, seed in (("pca", "-1"),
                                  ("isolation_forest", "mean(seeds 0,1,2)"),
                                  ("lstm_autoencoder", "mean(seeds 0,1,2)"))
           for metric in ("descent_minus_climb", "descent_minus_cruise")]
    claim(claim_id, f"{dataset}: pooled primary directional pattern",
          "At the 1% nominal target, pooled descent-minus-climb and descent-minus-cruise point estimates are positive for PCA and the three-seed means of Isolation Forest and LSTM.",
          "Every engine and every seed shows the same direction; all six effects have positive confidence intervals; the effect proves faults are detected.",
          ids)

claim("C03", "Confirmation status under the frozen rule",
      "The frozen DS03 directional point-estimate rule was met once, using the official healthy test split and prespecified detectors, seeds, and 1% target.",
      "The DS03 confirmation establishes universal statistical significance, causal phase effects, or performance on faulty/online operation.",
      [eid("DS03 confirmation", d, s, "primary", "0.01", "pooled", m)
       for d, s in (("pca", "-1"), ("isolation_forest", "mean(seeds 0,1,2)"),
                    ("lstm_autoencoder", "mean(seeds 0,1,2)"))
       for m in ("descent_minus_climb", "descent_minus_cruise")])

claim("C04", "Per-engine and seed heterogeneity in DS03",
      "The pooled directional pattern has per-engine/seed exceptions; the listed negative DS03 LSTM seed-2 contrasts must be reported.",
      "The directional pattern holds for every audit engine and all individual seeds.",
      [eid("DS03 confirmation", "lstm_autoencoder", "2", "primary", "0.01",
           unit, metric) for unit, metric in (
               ("engine_12", "descent_minus_climb"),
               ("engine_13", "descent_minus_cruise"),
               ("engine_15", "descent_minus_cruise"))])

claim("C05", "Uncertainty for DS03 LSTM descent-minus-cruise",
      "Each individual DS03 LSTM seed has a hierarchical-bootstrap 95% interval for the pooled descent-minus-cruise contrast that includes zero.",
      "The LSTM descent-minus-cruise contrast is statistically established as positive for every seed or for the seed mean.",
      [eid("DS03 confirmation", "lstm_autoencoder", str(seed), "primary", "0.01",
           "pooled", "descent_minus_cruise") for seed in (0, 1, 2)])

claim("C06", "Nominal calibration versus audit FPR",
      "The 1% target identifies calibration quantiles, not a guarantee of exactly 1% FPR on DS02 or DS03 healthy audit rows.",
      "All audited overall or phase-specific FPRs equal the nominal 1% target.",
      [eid(ds, d, s, "primary", "0.01", "pooled", "overall_fpr")
       for ds in SOURCES for d, s in (("pca", "-1"),
                                      ("isolation_forest", "mean(seeds 0,1,2)"),
                                      ("lstm_autoencoder", "mean(seeds 0,1,2)"))])

claim("C07", "Cross-phase threshold transfer",
      "At the 1% target, the executed worst off-diagonal cross-phase transfer FPR can be reported for each detector; this is a maximum over phase pairs, not the pooled operating FPR.",
      "The worst transfer FPR is the expected deployment FPR or is caused solely by phase.",
      [eid(ds, d, s, "primary", "0.01", "pooled", "worst_cross_phase_transfer_fpr")
       for ds in SOURCES for d, s in (("pca", "-1"),
                                      ("isolation_forest", "mean(seeds 0,1,2)"),
                                      ("lstm_autoencoder", "mean(seeds 0,1,2)"))])

claim("C08", "Descent-phase healthy-flight alarm burden",
      "For descent, the fraction of healthy flights with at least one alarm and contiguous false-alarm events per healthy flight are distinct from row-FPR.",
      "Row-FPR is the probability that a flight has any alarm, or each alarmed row is a separate event.",
      [eid(ds, d, s, "primary", "0.01", "pooled", m)
       for ds in SOURCES for d, s in (("pca", "-1"),
                                      ("isolation_forest", "mean(seeds 0,1,2)"),
                                      ("lstm_autoencoder", "mean(seeds 0,1,2)"))
       for m in ("healthy_flights_with_alarm_descent",
                 "false_alarm_events_per_healthy_flight_descent")])

claim("C09", "DS02 alternative phase-rule sensitivity",
      "Under the exploratory DS02 altitude-rate alternative, pooled directional contrasts remained positive for all three tested implementations; worst off-diagonal transfer FPRs are separately reported. DS03 confirmation evaluated the primary phase rule only.",
      "The alternative phase rule was independently confirmed on DS03.",
      [eid("DS02 discovery", d, s, rule, "0.01", "pooled", metric)
       for d, s in (("pca", "-1"), ("isolation_forest", "mean(seeds 0,1,2)"),
                    ("lstm_autoencoder", "mean(seeds 0,1,2)"))
       for rule in ("primary", "alt_rate")
       for metric in ("descent_minus_climb", "descent_minus_cruise",
                      "worst_cross_phase_transfer_fpr")])

claim("C10", "DS02 LSTM seed-0 convergence limit",
      "DS02 LSTM seed 0 selected the 600-epoch ceiling, with negative fitted validation-loss slopes in the final 20, 50, and 100 epochs; the fit had not demonstrably plateaued by this criterion.",
      "The seed-0 model is proven converged, or its ongoing loss decrease establishes a downstream test-performance trend.",
      [eid("DS02 discovery", "lstm_autoencoder", "0", "not applicable", "",
           "training engines", m, "training-only; stage=engine_disjoint_epoch_selection")
       for m in ("selected_epoch", "max_epochs")]
      + [eid("DS02 discovery", "lstm_autoencoder", "0", "not applicable", "",
             "held-out fit engine", f"final_{n}_epoch_validation_loss_slope",
             "training-only; stage=engine_disjoint_epoch_selection") for n in (20, 50, 100)])

claim("C11", "DS03 LSTM training selected before official-test audit",
      "The three DS03 LSTM epoch selections and validation losses are training-only quantities; they do not measure audit performance.",
      "The selected epochs were optimized using DS03 official-test outcomes.",
      [eid("DS03 confirmation", "lstm_autoencoder", str(seed), "not applicable", "",
           "training engines", "selected_epoch",
           "training-only; stage=engine_disjoint_epoch_selection") for seed in (0, 1, 2)])

claim("C12", "DS02 LSTM middle-only sensitivity diagnostic",
      "The DS02 executed boundary audit reports a middle-only official-test false-alarm rate for each LSTM seed.",
      "The boundary diagnostic was a frozen DS03 confirmation endpoint or proves boundary effects explain all phase differences.",
      [eid("DS02 discovery", "lstm_autoencoder", str(seed), "primary", "0.01",
           "official_test", "false_alarm_rate",
           "subset=official_test; category=middle_only_sensitivity; phase=overall")
       for seed in (0, 1, 2)])

claim("C13", "Scope of inference",
      "All FPR and flight-alarm endpoints describe oracle hs=1 healthy rows and retrospective complete-flight phase labels in the specified N-CMAPSS splits.",
      "The results quantify faulty-state detection, prospective online phase inference, or generalization beyond DS02/DS03.",
      [eid("DS03 confirmation", "pca", "-1", "primary", "0.01", "pooled", "overall_fpr"),
       eid("DS03 confirmation", "pca", "-1", "primary", "0.01", "pooled", "descent_fpr")])

claim("C14", "DS02 correction-specification comparison",
      "In exploratory DS02 PCA analysis only, static, derivative-based, and finite-history corrections did not eliminate the phase-dependent FPR pattern. Cross-detector consistency was evaluated under the selected finite-history correction.",
      "Correction-scheme robustness was established for Isolation Forest or LSTM, independently confirmed on DS03, or proves a causal mechanism.",
      [eid("DS02 discovery", "pca", "-1", "primary", "0.01", "pooled",
           "descent_minus_climb",
           f"executed Phase 3A PCA correction comparison; correction={correction}")
       for correction in ("static", "static_derivative", "history")])

claim("C15", "Limited audit-engine counts and heterogeneity",
      "The official audit sets contain three DS02 and six DS03 engines. Individual-engine directional reversals are material relative to those sets; bootstrap intervals summarize uncertainty for the observed engine sets.",
      "Engine-level reversals are negligible edge cases or bootstrap intervals provide precise population-level effects.",
      ["M0022", "M0027", *[eid("DS03 confirmation", "lstm_autoencoder", "2", "primary", "0.01", unit, metric)
                             for unit, metric in (("engine_12", "descent_minus_climb"),
                                                  ("engine_13", "descent_minus_cruise"),
                                                  ("engine_15", "descent_minus_cruise"))]])

claim("C16", "Fixed-three-seed mean uncertainty gap",
      "Stochastic-detector seed means are descriptive point summaries rather than inferential estimates. Executed hierarchical intervals exist for individual seeds, but no valid interval for the fixed three-seed arithmetic mean is available from the retained summary outputs.",
      "A mean of per-seed interval endpoints is a 95% interval for the seed mean, or the three seeds form an independent population bootstrap sample.",
      [eid("DS03 confirmation", "lstm_autoencoder", str(seed), "primary", "0.01", "pooled", "descent_minus_cruise")
       for seed in (0, 1, 2)])


OUT.mkdir(exist_ok=True)
with (OUT / "evidence_ledger.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(ledger)

with (OUT / "claim_audit.md").open("w", encoding="utf-8", newline="\n") as handle:
    handle.write("# Manuscript claim audit\n\n")
    handle.write("| Claim | Manuscript claim | Supported wording | Wording that would overclaim | Evidence IDs |\n")
    handle.write("| --- | --- | --- | --- | --- |\n")
    for item in claims:
        handle.write("| " + " | ".join(str(value).replace("|", "\\|") for value in item) + " |\n")
    handle.write("\nLedger convention: numerical values are unrounded source CSV strings, except explicitly labeled arithmetic seed means, fitted slopes, and derived correction contrasts. CSV row numbers count the header as row 1. Blank CI cells mean no interval was executed for that estimate. Existing figure files were not linked to these authoritative executed outputs, so the figure column is blank. DS02 is exploratory; DS03 is confirmatory under the frozen primary rule. The user-authorized executed Phase 3A correction comparison was reconciled against its component row-rate, transfer, phase-probe, and flight-alarm CSVs; obsolete Phase 3 narrative reports were not used.\n")

assert len({item["claim_id"] for item in ledger}) == len(ledger)
assert all("phase3" not in item["source_csv"].lower()
           or item["source_csv"] == comparison_path for item in ledger)
assert all(not item["corresponding_figure"] for item in ledger)
source_cache = {}
direct_checks = 0
for item in ledger:
    source = item["source_csv"]
    if not source:
        assert item["source_file"] and (ROOT / item["source_file"]).is_file()
        continue
    if source not in source_cache:
        source_cache[source] = read(source)
    source_lines = item["source_rows"].split(";")
    if len(source_lines) == 1:
        source_line, source_row = source_cache[source][int(source_lines[0]) - 2]
        assert source_line == int(source_lines[0])
        if item["metric"] in source_row:
            assert item["exact_numeric_value"] == source_row[item["metric"]], item["claim_id"]
            direct_checks += 1
all_ids = {item["claim_id"] for item in ledger}
audit_text = (OUT / "claim_audit.md").read_text(encoding="utf-8")
assert set(re.findall(r"[EM]\d{4,6}", audit_text)) <= all_ids
assert all(item["phase_rule"] == "primary" for item in ledger
           if item["dataset"] == "DS03 confirmation" and item["phase_rule"] not in ("not applicable", ""))

print(f"Wrote {len(ledger)} evidence rows and {len(claims)} claim-audit rows; verified {direct_checks} direct source values")
