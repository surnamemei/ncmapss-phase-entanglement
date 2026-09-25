"""Draw the primary pooled phase-FPR figure from core CSV values only."""

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper/manuscript_core_results.csv"
DEST = ROOT / "paper/generated/primary_phase_fpr.png"


def figure_data():
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    selected = [row for row in rows if row["selection_group"] == "frozen primary pooled endpoint"
                and row["evaluation_unit"] == "pooled"
                and row["nominal_fpr_target"] == "0.01"
                and row["metric"] in ("climb_fpr", "cruise_fpr", "descent_fpr")]
    if not selected or any(not row["evidence_id"] for row in selected):
        raise ValueError("Missing pooled primary endpoints or evidence IDs")
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rows = figure_data()
    if args.dry_run:
        print(f"DRY RUN: validated {len(rows)} plotted values; no output written")
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    datasets = list(dict.fromkeys(row["dataset"] for row in rows))
    detectors = list(dict.fromkeys(row["detector"] for row in rows))
    phases = ("climb_fpr", "cruise_fpr", "descent_fpr")
    fig, axes = plt.subplots(1, len(datasets), figsize=(6 * len(datasets), 4), squeeze=False)
    for ax, dataset in zip(axes[0], datasets):
        subset = [row for row in rows if row["dataset"] == dataset]
        for index, detector in enumerate(detectors):
            vals = {row["metric"]: float(row["exact_value"]) * 100 for row in subset
                    if row["detector"] == detector}
            if len(vals) != len(phases):
                continue
            ax.plot(range(len(phases)), [vals[phase] for phase in phases], marker="o",
                    label=detector)
        ax.set_xticks(range(len(phases)), [phase.removesuffix("_fpr") for phase in phases])
        ax.set_title(dataset)
        ax.set_ylabel("Healthy row false-positive rate (%)")
        ax.legend()
    fig.tight_layout()
    DEST.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(DEST, dpi=200)
    plt.close(fig)
    (DEST.with_suffix(".provenance.json")).write_text(json.dumps({
        "source_csv": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "evidence_ids": [row["evidence_id"] for row in rows],
        "generation_script": "scripts/build_paper_figures.py",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {DEST}")


if __name__ == "__main__":
    main()
