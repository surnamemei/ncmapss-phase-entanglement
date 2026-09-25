"""Select prespecified main-manuscript endpoints from the evidence ledger."""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "paper/evidence_ledger.csv"
OUTPUT = ROOT / "paper/manuscript_core_results.csv"
with LEDGER.open(newline="", encoding="utf-8") as handle:
    evidence = list(csv.DictReader(handle))

index = {}
for row in evidence:
    if row["claim_id"].startswith("M"):
        continue
    key = (row["dataset"], row["detector"], row["seed_or_seed_aggregation"],
           row["phase_rule"], row["nominal_fpr_target"], row["evaluation_unit"],
           row["analysis_detail"], row["metric"])
    if key in index:
        raise ValueError(f"Duplicate ledger key: {key}")
    index[key] = row

FIELDS = [
    "manuscript_key", "selection_group", "dataset", "detector", "correction",
    "seed_or_aggregation", "phase_rule", "nominal_fpr_target", "evaluation_unit",
    "metric", "metric_definition", "exact_value", "display_rounded_value", "units",
    "ci_lower_95_exact", "ci_upper_95_exact", "ci_display_rounded",
    "ci_method", "evidence_id", "original_source_csv", "original_source_rows",
    "exploratory_or_confirmatory",
]
rows = []


def display(value, unit):
    number = float(value)
    if unit == "fraction":
        return f"{number * 100:.3f}%"
    if unit == "fraction difference":
        return f"{number * 100:+.3f} pp"
    if unit == "events per healthy flight":
        return f"{number:.3f} events/flight"
    if unit == "epochs":
        return f"{number:.0f} epochs"
    raise ValueError(unit)


def include(group, key, item, correction="history"):
    if any(row["manuscript_key"] == key for row in rows):
        raise ValueError(f"Duplicate manuscript key: {key}")
    unit = item["value_unit"]
    if unit not in ("fraction", "fraction difference", "events per healthy flight", "epochs"):
        raise ValueError(f"Unexpected main-result unit: {unit}")
    ci_lower, ci_upper = item["ci_lower_95"], item["ci_upper_95"]
    if bool(ci_lower) != bool(ci_upper):
        raise ValueError(f"Incomplete interval: {item['claim_id']}")
    rows.append({
        "manuscript_key": key,
        "selection_group": group,
        "dataset": item["dataset"],
        "detector": item["detector"],
        "correction": correction,
        "seed_or_aggregation": item["seed_or_seed_aggregation"],
        "phase_rule": item["phase_rule"],
        "nominal_fpr_target": item["nominal_fpr_target"],
        "evaluation_unit": item["evaluation_unit"],
        "metric": item["metric"],
        "metric_definition": item["metric_definition"],
        "exact_value": item["exact_numeric_value"],
        "display_rounded_value": display(item["exact_numeric_value"], unit),
        "units": unit,
        "ci_lower_95_exact": ci_lower,
        "ci_upper_95_exact": ci_upper,
        "ci_display_rounded": (f"[{display(ci_lower, unit)}, {display(ci_upper, unit)}]"
                               if ci_lower else ""),
        "ci_method": item["ci_method"],
        "evidence_id": item["claim_id"],
        "original_source_csv": item["source_csv"],
        "original_source_rows": item["source_rows"],
        "exploratory_or_confirmatory": item["evidence_status"],
    })


def get(dataset, detector, seed, metric, *, unit="pooled", detail="canonical", phase="primary"):
    if seed.startswith("mean(") and detail == "canonical":
        detail = "arithmetic seed mean"
    return index[(dataset, detector, seed, phase, "0.01", unit, detail, metric)]


PRIMARY_METRICS = (
    "overall_fpr", "climb_fpr", "cruise_fpr", "descent_fpr",
    "descent_minus_climb", "descent_minus_cruise",
    "worst_cross_phase_transfer_fpr",
    "healthy_flights_with_alarm_climb",
    "false_alarm_events_per_healthy_flight_climb",
    "healthy_flights_with_alarm_cruise",
    "false_alarm_events_per_healthy_flight_cruise",
    "healthy_flights_with_alarm_descent",
    "false_alarm_events_per_healthy_flight_descent",
)
BOOTSTRAP_METRICS = PRIMARY_METRICS[:7]
DET_SET = (
    ("pca", "-1", "PCA"),
    ("isolation_forest", "mean(seeds 0,1,2)", "IF"),
    ("lstm_autoencoder", "mean(seeds 0,1,2)", "LSTM"),
)
for dataset, short in (("DS02 discovery", "D02"), ("DS03 confirmation", "D03")):
    for detector, seed, label in DET_SET:
        for metric in PRIMARY_METRICS:
            summary_tag = "SINGLE" if detector == "pca" else "MEAN"
            include("frozen primary pooled endpoint", f"{short}-{label}-{summary_tag}-{metric}",
                    get(dataset, detector, seed, metric))
    # The executed intervals are per model seed. No CI for a three-seed mean was run.
    for detector, label in (("isolation_forest", "IF"),
                            ("lstm_autoencoder", "LSTM")):
        for seed in ("0", "1", "2"):
            for metric in BOOTSTRAP_METRICS:
                item = get(dataset, detector, seed, metric)
                assert item["ci_lower_95"] and item["ci_upper_95"]
                include("individual-seed bootstrap support",
                        f"{short}-{label}-S{seed}-{metric}", item)
    # PCA's empirical primary rows already carry their own bootstrap intervals.
    for metric in BOOTSTRAP_METRICS:
        assert get(dataset, "pca", "-1", metric)["ci_lower_95"]

# Complete, prespecified three-specification PCA comparison, not the
# subsequently frozen history-only detector-family validation.
for correction, label in (("static", "STATIC"),
                          ("static_derivative", "DERIV"),
                          ("history", "HISTORY")):
    detail = f"executed Phase 3A PCA correction comparison; correction={correction}"
    for metric in BOOTSTRAP_METRICS:
        item = get("DS02 discovery", "pca", "-1", metric, detail=detail)
        include("DS02 correction specification comparison",
                f"D02-CORR-{label}-{metric}", item, correction=correction)

# Existing executed DS02 phase-rule sensitivity: directional contrasts and
# transfer endpoint only. This is exploratory and not a DS03 confirmation row.
for detector, seed, label in DET_SET:
    for metric in ("descent_minus_climb", "descent_minus_cruise",
                   "worst_cross_phase_transfer_fpr"):
        include("DS02 exploratory alternative phase rule",
                f"D02-ALT-{label}-{metric}",
                get("DS02 discovery", detector, seed, metric, phase="alt_rate"))

# The frozen interpretation rule requires reporting every per-engine exception
# to both directional contrasts. Scan the complete prespecified DS03 engine set.
exception_ids = []
for detector, seed, label in (("pca", "-1", "PCA"),
                              *((det, str(seed), lab) for det, lab in
                                (("isolation_forest", "IF"),
                                 ("lstm_autoencoder", "LSTM"))
                                for seed in (0, 1, 2))):
    for engine in (10, 11, 12, 13, 14, 15):
        for metric in ("descent_minus_climb", "descent_minus_cruise"):
            item = get("DS03 confirmation", detector, seed, metric,
                       unit=f"engine_{engine}")
            if float(item["exact_numeric_value"]) <= 0:
                include("frozen per-engine directional exception",
                        f"D03-{label}-S{seed}-E{engine}-{metric}", item)
                exception_ids.append(item["claim_id"])
assert len(exception_ids) == 3, exception_ids

for metric in ("selected_epoch", "max_epochs"):
    item = index[("DS02 discovery", "lstm_autoencoder", "0", "not applicable", "",
                  "training engines", "training-only; stage=engine_disjoint_epoch_selection",
                  metric)]
    include("DS02 seed-0 training limitation", f"D02-LSTM-S0-{metric}", item)

assert all(row["original_source_csv"] and row["original_source_rows"]
           and row["evidence_id"].startswith("E") for row in rows)
assert all(row["exploratory_or_confirmatory"] == ("exploratory" if row["dataset"] == "DS02 discovery"
                                                       else "confirmatory") for row in rows)
with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
print(f"Wrote {len(rows)} prespecified main-manuscript evidence rows")
