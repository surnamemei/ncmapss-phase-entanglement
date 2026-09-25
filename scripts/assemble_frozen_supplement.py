"""Package frozen supplementary displays without fitting or new endpoints.

CSV files are copied byte-for-byte. Markdown tables select existing rows and
columns, preserving the executed decimal strings. Loss figures only plot the
recorded epoch histories; no smoothing or statistical analysis is performed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper/submission/supplementary"
SOURCE = {
    "S1": "results/phase3_dynamic_correction/correction_comparison.csv",
    "S2": "results/final_validation/canonical_results.csv",
    "S3": "results/final_validation/per_engine_phase_fpr.csv",
    "S4": "results/confirmation_ds03/canonical_results.csv",
    "S5": "results/final_validation/canonical_results.csv",
    "S5ci": "results/final_validation/hierarchical_bootstrap_ci.csv",
    "S6": "results/confirmation_ds03/canonical_results.csv",
    "S6ci": "results/confirmation_ds03/hierarchical_bootstrap_ci.csv",
    "S7a": "results/final_validation/canonical_results.csv",
    "S7b": "results/confirmation_ds03/canonical_results.csv",
    "S8a": "results/final_validation/lstm_training_history.csv",
    "S8b": "results/confirmation_ds03/lstm_training_history.csv",
    "S9": "results/final_validation/lstm_boundary_audit.csv",
}


def read(rel: str) -> list[dict[str, str]]:
    with (ROOT / rel).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def md_table(rows: list[dict[str, str]], cols: list[str]) -> str:
    if not rows:
        raise ValueError(f"Empty frozen supplementary selection: {cols}")
    def safe(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    lines += ["| " + " | ".join(safe(row[col]) for col in cols) + " |" for row in rows]
    return "\n".join(lines)


def primary(row: dict[str, str]) -> bool:
    return row["phase_rule"] == "primary" and row["nominal_fpr_target"] == "0.01"


def history_plot(dataset: str, rel: str, stem: str) -> None:
    rows = [r for r in read(rel) if r["stage"] == "engine_disjoint_epoch_selection"]
    seeds = sorted({r["seed"] for r in rows}, key=int)
    fig, axes = plt.subplots(1, len(seeds), figsize=(11, 3.2), sharey=False)
    for ax, seed in zip(axes, seeds):
        subset = sorted((r for r in rows if r["seed"] == seed), key=lambda r: int(r["epoch"]))
        x = [int(r["epoch"]) for r in subset]
        ax.plot(x, [float(r["train_loss"]) for r in subset], label="Training", lw=1.2)
        ax.plot(x, [float(r["validation_loss"]) for r in subset], label="Validation", lw=1.2)
        ax.set_title(f"Seed {seed}")
        ax.set_xlabel("Epoch")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Recorded loss")
    axes[-1].legend(frameon=False, fontsize=8)
    fig.suptitle(f"{dataset}: frozen LSTM epoch-selection histories", fontsize=11)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{stem}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for item, rel in SOURCE.items():
        source = ROOT / rel
        dest = OUT / f"table_{item.lower()}_{source.parent.name}_{source.name}"
        shutil.copyfile(source, dest)
        manifest[item] = {
            "source": rel,
            "packaged_file": dest.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "byte_identical_copy": True,
        }
    note_source = ROOT / "results/final_validation/seed0_last100_loss.md"
    note_dest = OUT / "ds02_seed0_last100_loss_executed.md"
    shutil.copyfile(note_source, note_dest)
    manifest["S8note"] = {
        "source": note_source.relative_to(ROOT).as_posix(),
        "packaged_file": note_dest.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(note_source.read_bytes()).hexdigest(),
        "byte_identical_copy": True,
    }

    ds02 = read(SOURCE["S2"])
    ds03 = read(SOURCE["S4"])
    sections = [
        "# Frozen supplementary material",
        "",
        "All tables reproduce executed CSV fields verbatim; filtering to the frozen nominal 1% target does not constitute a new analysis. The copied CSV files are byte-identical to their named sources. DS02 correction and alternative-rule checks are exploratory only. DS03 uses the frozen primary phase rule. Fractions are not percentages unless a heading explicitly says so. No supplementary display is a new inferential endpoint.",
        "",
        "## Table S1. DS02 correction sensitivity (exploratory)",
        "",
        "Source: `results/phase3_dynamic_correction/correction_comparison.csv`, primary phase-rule rows. Nominal 1% calibration. Static, static-plus-derivative, and finite-history values are executed exploratory comparisons; no DS03 correction-variant confirmation is implied.",
        "",
        md_table([r for r in read(SOURCE["S1"]) if r["phase_definition"] == "primary"], ["correction", "overall_fpr", "climb_fpr", "cruise_fpr", "descent_fpr", "worst_offdiagonal_transfer_fpr"]),
        "",
        "## Table S2. DS02 alternative phase-rule sensitivity (exploratory)",
        "",
        "Source: `results/final_validation/canonical_results.csv`; pooled rows, alternative-rate rule, nominal 1% target. The DS03 confirmation did not use the alternative rule.",
        "",
        md_table([r for r in ds02 if r["phase_rule"] == "alt_rate" and r["nominal_fpr_target"] == "0.01" and r["evaluation_unit"] == "pooled"], ["detector", "seed", "climb_fpr", "cruise_fpr", "descent_fpr", "descent_minus_climb", "descent_minus_cruise"]),
        "",
        "## Table S3. DS02 per-engine primary results (exploratory)",
        "",
        "Source: `results/final_validation/per_engine_phase_fpr.csv`; primary rule, nominal 1% target. Engine rows must not be read as independent timestamps.",
        "",
        md_table([r for r in read(SOURCE["S3"]) if primary(r)], ["detector", "seed", "evaluation_unit", "climb_fpr", "cruise_fpr", "descent_fpr", "descent_minus_climb", "descent_minus_cruise"]),
        "",
        "## Table S4. DS03 per-engine primary results (confirmatory)",
        "",
        "Source: `results/confirmation_ds03/canonical_results.csv`; engine rows, primary rule, nominal 1% target. Directional exceptions remain visible rather than being removed.",
        "",
        md_table([r for r in ds03 if primary(r) and r["evaluation_unit"].startswith("engine_")], ["detector", "seed", "evaluation_unit", "climb_fpr", "cruise_fpr", "descent_fpr", "descent_minus_climb", "descent_minus_cruise"]),
        "",
        "## Table S5. DS02 individual-seed pooled results (exploratory)",
        "",
        "Source: `results/final_validation/canonical_results.csv`; primary rule, nominal 1% target. No seed-mean interval is assigned to an individual seed.",
        "",
        md_table([r for r in ds02 if primary(r) and r["evaluation_unit"] == "pooled" and r["detector"] != "pca"], ["detector", "seed", "climb_fpr", "cruise_fpr", "descent_fpr", "descent_minus_climb", "descent_minus_cruise"]),
        "",
        "## Table S6. DS03 individual-seed pooled results (confirmatory)",
        "",
        "Source: `results/confirmation_ds03/canonical_results.csv`; primary rule, nominal 1% target. Byte-identical individual-run intervals are in `table_s6ci_confirmation_ds03_hierarchical_bootstrap_ci.csv`; these are not seed-mean intervals. The corresponding DS02 intervals are in `table_s5ci_final_validation_hierarchical_bootstrap_ci.csv`.",
        "",
        md_table([r for r in ds03 if primary(r) and r["evaluation_unit"] == "pooled" and r["detector"] != "pca"], ["detector", "seed", "climb_fpr", "cruise_fpr", "descent_fpr", "descent_minus_climb", "descent_minus_cruise"]),
        "",
        "## Table S7. Flight-level alarm burden (secondary descriptive)",
        "",
        "Sources: DS02 and DS03 canonical CSVs; pooled primary-rule rows at nominal 1%. Fractions and events per healthy flight depend on phase duration and exposure. They are not the primary row-level FPR endpoint.",
        "",
        md_table([dict(dataset="DS02", **r) for r in ds02 if primary(r) and r["evaluation_unit"] == "pooled"] + [dict(dataset="DS03", **r) for r in ds03 if primary(r) and r["evaluation_unit"] == "pooled"], ["dataset", "detector", "seed", "healthy_flights_with_alarm_climb", "healthy_flights_with_alarm_cruise", "healthy_flights_with_alarm_descent", "false_alarm_events_per_healthy_flight_climb", "false_alarm_events_per_healthy_flight_cruise", "false_alarm_events_per_healthy_flight_descent"]),
        "",
        "## Table S8 and Figures S1–S2. LSTM convergence histories (descriptive)",
        "",
        "The byte-identical executed histories are packaged as `table_s8a_final_validation_lstm_training_history.csv` and `table_s8b_confirmation_ds03_lstm_training_history.csv`. Figures S1–S2 plot the recorded training and epoch-selection validation losses without smoothing. DS02 seed 0 reached the pre-specified 600-epoch ceiling while validation loss was still improving; it is not described as converged. The copied `ds02_seed0_last100_loss_executed.md` provides the prior slope audit. These training diagnostics do not inspect downstream test results.",
        "",
        "![Figure S1. DS02 recorded LSTM training and validation losses](figure_s1_ds02_lstm_history.png)",
        "",
        "![Figure S2. DS03 recorded LSTM training and validation losses](figure_s2_ds03_lstm_history.png)",
        "",
        "## Table S9. Chunk, tail, and sequence-boundary audit (diagnostic)",
        "",
        "The byte-identical `table_s9_final_validation_lstm_boundary_audit.csv` contains the executed DS02 boundary categories and false-alarm diagnostics. It is not a frozen DS03 primary endpoint. Source: `results/final_validation/lstm_boundary_audit.csv`.",
        "",
        "## Provenance",
        "",
        "The companion `source_manifest.json` records SHA-256 digests of each copied executed CSV. Core claim interpretation remains governed by `paper/evidence_ledger.csv`, `paper/claim_audit.md`, and `docs/AUTHORITATIVE_RESULTS.md`; obsolete Phase 3 narratives are excluded.",
    ]
    history_plot("DS02 exploratory", SOURCE["S8a"], "figure_s1_ds02_lstm_history")
    history_plot("DS03 confirmatory", SOURCE["S8b"], "figure_s2_ds03_lstm_history")
    (OUT / "supplementary_material.md").write_text("\n".join(sections) + "\n", encoding="utf-8")
    (OUT / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Packaged {len(SOURCE)} byte-identical frozen CSV copies, one executed loss note, Tables S1-S9, and Figures S1-S2")


if __name__ == "__main__":
    main()
