"""Generate a provenance-preserving main table from the frozen core CSV only."""

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper/manuscript_core_results.csv"
DEST = ROOT / "paper/generated/main_results_table.csv"
FIELDS = ("manuscript_key", "dataset", "detector", "phase_rule", "nominal_fpr_target",
          "evaluation_unit", "metric", "exact_value", "display_rounded_value", "units",
          "ci_lower_95_exact", "ci_upper_95_exact", "evidence_id", "source_csv",
          "original_source_rows", "generation_script")


def build_rows():
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        source = list(csv.DictReader(handle))
    if not source or any(not row["evidence_id"] or not row["original_source_csv"]
                         for row in source):
        raise ValueError("Core results missing rows or provenance")
    rows = []
    for item in source:
        row = {key: item[key] for key in FIELDS if key in item}
        row["source_csv"] = item["original_source_csv"]
        row["generation_script"] = "scripts/build_paper_tables.py"
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rows = build_rows()
    if args.dry_run:
        print(f"DRY RUN: validated {len(rows)} ledger-derived rows; no output written")
        return
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with DEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {DEST}")


if __name__ == "__main__":
    main()
