"""Render the frozen main-paper figures, tables, and submission Markdown.

This script only presents existing evidence. It does not load raw N-CMAPSS arrays,
fit models, calibrate thresholds, or compute new scientific endpoints.
"""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
FIGURES = PAPER / "figures"
TABLES = PAPER / "tables"
CORE_PATH = PAPER / "manuscript_core_results.csv"
LEDGER_PATH = PAPER / "evidence_ledger.csv"
TRANSFER_PATH = ROOT / "results/final_validation/executed_threshold_transfer_matrix.csv"
SOURCE_NOTE = "scripts/build_submission_package.py"
PHASES = ("climb", "cruise", "descent")
DETECTORS = (
    ("pca", "-1", "PCA"),
    ("isolation_forest", "mean(seeds 0,1,2)", "Isolation Forest\n(seed mean)"),
    ("lstm_autoencoder", "mean(seeds 0,1,2)", "Causal LSTM reconstruction\n(seed mean)"),
)
COLORS = ("#0072B2", "#D55E00", "#009E73")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


CORE = read_csv(CORE_PATH)
LEDGER = {row["claim_id"]: row for row in read_csv(LEDGER_PATH)}


def evidence(claim_id: str) -> dict[str, str]:
    if claim_id not in LEDGER:
        raise ValueError(f"Missing ledger ID: {claim_id}")
    return LEDGER[claim_id]


def meta(claim_id: str) -> str:
    return evidence(claim_id)["exact_numeric_value"]


def core_row(dataset: str, detector: str, seed: str, metric: str) -> dict[str, str]:
    matches = [
        row for row in CORE
        if row["dataset"] == dataset
        and row["detector"] == detector
        and row["seed_or_aggregation"] == seed
        and row["metric"] == metric
        and row["selection_group"] == "frozen primary pooled endpoint"
        and row["phase_rule"] == "primary"
        and row["nominal_fpr_target"] == "0.01"
        and row["evaluation_unit"] == "pooled"
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one frozen primary row: {dataset}/{detector}/{seed}/{metric}")
    row = matches[0]
    source = evidence(row["evidence_id"])
    if row["exact_value"] != source["exact_numeric_value"]:
        raise ValueError(f"Core/ledger numeric mismatch: {row['evidence_id']}")
    if row["original_source_csv"] != source["source_csv"]:
        raise ValueError(f"Core/ledger provenance mismatch: {row['evidence_id']}")
    return row


def primary_target() -> float:
    targets = {float(row["nominal_fpr_target"]) for row in CORE if row["selection_group"] == "frozen primary pooled endpoint"}
    if targets != {0.01}:
        raise ValueError(f"Unexpected primary target set: {targets}")
    return targets.pop()


def percent_label(row: dict[str, str]) -> str:
    value = row["display_rounded_value"]
    if not value.endswith("%"):
        raise ValueError(f"Expected percent display: {row['evidence_id']}")
    return value


def percent_value(row: dict[str, str]) -> float:
    return float(row["exact_value"]) * 100.0


def evidence_comment(ids: list[str], sources: list[str] | None = None) -> str:
    for claim_id in ids:
        evidence(claim_id)
    source_part = ""
    if sources:
        source_part = "; sources: " + ", ".join(dict.fromkeys(sources))
    return f"<!-- evidence: {', '.join(dict.fromkeys(ids))}{source_part}; generation_script: {SOURCE_NOTE} -->"


def save_figure(fig, stem: str, ids: list[str], source_paths: list[str], status: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    fig.savefig(FIGURES / f"{stem}.png", dpi=400, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    sidecar = {
        "status": status,
        "source_paths": list(dict.fromkeys(source_paths)),
        "evidence_ids": list(dict.fromkeys(ids)),
        "generation_script": SOURCE_NOTE,
        "formats": [f"paper/figures/{stem}.svg", f"paper/figures/{stem}.png"],
    }
    (FIGURES / f"{stem}.provenance.json").write_text(
        json.dumps(sidecar, indent=2) + "\n", encoding="utf-8"
    )


def set_plot_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8.5,
        "svg.fonttype": "none",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.pad_inches": 0.15,
    })


def figure_1() -> tuple[str, list[str], list[str]]:
    stem = "figure_1_study_design"
    ids = ["M0020", "M0021", "M0022", "M0025", "M0026", "M0027", "M0034"]
    fig, ax = plt.subplots(figsize=(10.8, 3.35))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.4)
    ax.axis("off")
    stages = [
        (0.18, "DS02 discovery", "Exploratory fitting,\ncalibration, and audit", "#E8F2FA", "#0072B2"),
        (3.18, "Robustness analyses", "Correction, phase, and\ncross-detector checks", "#EAF5EF", "#009E73"),
        (6.18, "Protocol freeze", "Rules and endpoints\nlocked before test access", "#F5F1E7", "#6B5A2B"),
        (9.18, "DS03 confirmation", "Independent N-CMAPSS subset;\none-shot official-test audit", "#FBEDE7", "#D55E00"),
    ]
    width = 2.62
    for x, title, detail, fill, edge in stages:
        ax.add_patch(FancyBboxPatch(
            (x, 1.02), width, 1.55,
            boxstyle="round,pad=0.07,rounding_size=0.1",
            linewidth=1.5, edgecolor=edge, facecolor=fill,
        ))
        ax.text(x + width / 2, 2.13, title, ha="center", va="center", weight="bold", color="#17212B")
        ax.text(x + width / 2, 1.54, detail, ha="center", va="center", fontsize=8.6, color="#253443", linespacing=1.35)
    for x in (2.84, 5.84, 8.84):
        ax.add_patch(FancyArrowPatch((x, 1.80), (x + 0.27, 1.80), arrowstyle="-|>", mutation_scale=15, linewidth=1.5, color="#455565"))
    ax.text(7.55, 0.43, "No DS03 official-test access before protocol freeze", ha="center", va="center", fontsize=9, color="#4B5563")
    fig.tight_layout(pad=0.4)
    sources = ["results/final_validation/frozen_protocol.md", "paper/evidence_ledger.csv"]
    save_figure(fig, stem, ids, sources, "conceptual design; DS02 exploratory / DS03 confirmatory")
    return stem, ids, sources


def phase_figure(dataset: str, stem: str, title: str, status: str) -> tuple[str, list[str], list[str]]:
    data = {
        (detector, seed): [core_row(dataset, detector, seed, f"{phase}_fpr") for phase in PHASES]
        for detector, seed, _ in DETECTORS
    }
    all_phase_values = [
        percent_value(core_row(ds, detector, seed, f"{phase}_fpr"))
        for ds in ("DS02 discovery", "DS03 confirmation")
        for detector, seed, _ in DETECTORS
        for phase in PHASES
    ]
    y_max = math.ceil(max(all_phase_values) * 1.2 * 2) / 2
    fig, ax = plt.subplots(figsize=(8.6, 4.7))
    x_positions = range(len(PHASES))
    width = 0.23
    ids: list[str] = []
    sources: list[str] = []
    for j, (detector, seed, label) in enumerate(DETECTORS):
        rows = data[(detector, seed)]
        xs = [i + (j - 1) * width for i in x_positions]
        bars = ax.bar(xs, [percent_value(row) for row in rows], width=width, color=COLORS[j], label=label, zorder=3)
        for bar, row in zip(bars, rows):
            ax.annotate(
                percent_label(row), (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=8,
            )
            ids.append(row["evidence_id"])
            sources.append(row["original_source_csv"])
    ax.set_xticks(list(x_positions), [phase.capitalize() for phase in PHASES])
    ax.set_ylabel("Healthy row-level FPR (%)")
    ax.set_ylim(0, y_max)
    ax.set_xlim(-0.53, 2.53)
    ax.set_title(title, loc="left", pad=12, weight="bold")
    ax.grid(axis="y", color="#E4E8EC", linewidth=0.7, zorder=0)
    ax.legend(loc="upper left", ncol=3, frameon=False, bbox_to_anchor=(0, 1.0), columnspacing=1.2)
    fig.tight_layout(pad=1.15)
    save_figure(fig, stem, ids, sources, status)
    return stem, ids, sources


def transfer_matrix() -> tuple[list[list[float]], list[str], list[str]]:
    source_rel = "results/final_validation/executed_threshold_transfer_matrix.csv"
    rows = []
    with TRANSFER_PATH.open(newline="", encoding="utf-8") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            if (
                row["detector"] == "pca"
                and row["seed"] == "-1"
                and row["phase_definition"] == "primary"
                and row["nominal_fpr"] == "0.01"
                and row["unit"] == "all"
            ):
                rows.append((line_number, row))
    if len(rows) != 9:
        raise ValueError(f"Expected nine pooled DS02 PCA transfer cells, found {len(rows)}")
    matrix: dict[tuple[str, str], float] = {}
    ids = []
    for source_line, row in rows:
        key = (row["calibration_phase"], row["test_phase"])
        if key in matrix:
            raise ValueError(f"Duplicate transfer cell: {key}")
        matches = [
            item for item in LEDGER.values()
            if item["source_csv"] == source_rel
            and item["source_rows"] == str(source_line)
            and item["evaluation_unit"] == "pooled"
            and item["metric"] == "false_alarm_rate"
        ]
        if len(matches) != 1 or matches[0]["exact_numeric_value"] != row["false_alarm_rate"]:
            raise ValueError(f"Transfer cell does not reconcile to ledger: CSV line {source_line}")
        matrix[key] = float(row["false_alarm_rate"]) * 100
        ids.append(matches[0]["claim_id"])
    values = [[matrix[(cal, audit)] for audit in PHASES] for cal in PHASES]
    canonical_max = percent_value(core_row("DS02 discovery", "pca", "-1", "worst_cross_phase_transfer_fpr"))
    displayed_max = max(matrix[(cal, audit)] for cal in PHASES for audit in PHASES if cal != audit)
    if not math.isclose(displayed_max, canonical_max, rel_tol=0, abs_tol=1e-12):
        raise ValueError("Transfer-matrix maximum disagrees with canonical PCA endpoint")
    ids.append(core_row("DS02 discovery", "pca", "-1", "worst_cross_phase_transfer_fpr")["evidence_id"])
    return values, ids, [source_rel, "results/final_validation/canonical_results.csv"]


def figure_3() -> tuple[str, list[str], list[str]]:
    stem = "figure_3_cross_phase_transfer"
    matrix, ids, sources = transfer_matrix()
    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    boundaries = [-0.5, 0.5, 1.5, 2.5]
    im = ax.pcolormesh(boundaries, boundaries, matrix, cmap="Blues", vmin=0, vmax=max(map(max, matrix)), shading="flat")
    ax.set_xlim(-0.5, 2.5)
    ax.set_ylim(2.5, -0.5)
    ax.set_aspect("equal")
    ax.set_xticks(range(3), [p.capitalize() for p in PHASES])
    ax.set_yticks(range(3), [p.capitalize() for p in PHASES])
    ax.set_xlabel("Audit phase")
    ax.set_ylabel("Calibration phase")
    ax.set_title("DS02 exploratory PCA threshold transfer", loc="left", pad=12, weight="bold")
    midpoint = max(map(max, matrix)) * 0.55
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{matrix[i][j]:.3f}%", ha="center", va="center", weight="bold", color="white" if matrix[i][j] > midpoint else "#12212E")
    cbar = fig.colorbar(im, ax=ax, shrink=0.82, pad=0.04)
    cbar.set_label("Healthy row-level transfer FPR (%)")
    fig.tight_layout(pad=1.0)
    save_figure(fig, stem, ids, sources, "DS02 exploratory cross-phase transfer; not pooled phase FPR")
    return stem, ids, sources


def write_table(name: str, content: str) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    (TABLES / name).write_text(content.rstrip() + "\n", encoding="utf-8")


def fmt_engines(claim_id: str) -> str:
    value = meta(claim_id)
    if not re.fullmatch(r"\d+(?:,\d+)*", value):
        raise ValueError(f"Unexpected engine-list value: {claim_id}: {value}")
    return ", ".join(value.split(","))


def table_i() -> tuple[str, list[str], list[str]]:
    ids = [f"M{i:04d}" for i in range(20, 30)] + ["M0002", "M0018", "M0033", "M0034", "E021498", "E021511", "E021524"]
    target = primary_target()
    targets = [float(x) * 100 for x in meta("M0018").split(",")]
    if not any(math.isclose(x, target * 100) for x in targets):
        raise ValueError("Primary target missing from frozen target list")
    target_display = ", ".join(f"{x:g}%" for x in targets)
    phase_fraction = float(meta("M0002")) * 100
    ds02 = [fmt_engines(f"M{i:04d}") for i in (20, 23, 24, 21, 22)]
    ds03 = [fmt_engines(f"M{i:04d}") for i in (25, 28, 29, 26, 27)]
    caption = (
        "**Table I. Dataset and frozen protocol summary.** DS02 is exploratory discovery; "
        "DS03 is an independent confirmatory N-CMAPSS subset under the frozen one-shot protocol. "
        "This design table contains no pooled phase-FPR or cross-phase transfer-FPR outcomes; "
        "seed means are not applicable."
    )
    lines = [
        caption,
        "",
        "| Item | DS02 discovery (exploratory) | DS03 independent confirmatory subset |",
        "| --- | --- | --- |",
        "| Role | Discovery, correction sensitivity, detector development | Frozen one-shot confirmation |",
        f"| Model-fitting engines | {ds02[0]} | {ds03[0]} |",
        f"| LSTM epoch-selection fitting engines | {ds02[1]} | {ds03[1]} |",
        f"| LSTM epoch-selection validation engine | {ds02[2]} | {ds03[2]} |",
        f"| Threshold-calibration engines | {ds02[3]} | {ds03[3]} |",
        f"| Official audit/test engines | {ds02[4]} | {ds03[4]} |",
        f"| Phase-label role | Retrospective full-flight stratification; cruise spans the first through last sample at or above the minimum plus {phase_fraction:g}% of each flight's observed altitude range | Same frozen retrospective primary rule |",
        f"| Nominal pooled healthy row-FPR targets | {target_display}; {target * 100:g}% primary | Same frozen targets and primary target |",
        "| Detector implementations | PCA; Isolation Forest; causal LSTM sequence reconstruction | Same frozen implementations |",
        "| Operating-condition correction | Static, static + derivative, and finite-history compared for PCA exploratorily; finite-history used for canonical detector results | Finite-history only; no DS03 correction-variant selection |",
        "",
        "Health-state annotations select healthy rows for retrospective fitting, calibration, and FPR evaluation; they are not detector features. Phase labels are retrospective strata, not an online phase detector.",
        "",
        evidence_comment(ids, ["paper/evidence_ledger.csv", "results/final_validation/frozen_protocol.md"]),
    ]
    name = "table_i_dataset_protocol.md"
    write_table(name, "\n".join(lines))
    return name, ids, ["paper/evidence_ledger.csv", "results/final_validation/frozen_protocol.md"]


def table_ii() -> tuple[str, list[str], list[str]]:
    ids = []
    sources = []
    metrics = ("overall_fpr", "climb_fpr", "cruise_fpr", "descent_fpr", "descent_minus_climb", "descent_minus_cruise", "worst_cross_phase_transfer_fpr")
    target = primary_target() * 100
    lines = [
        f"**Table II. DS02 exploratory canonical results at the nominal {target:g}% pooled healthy calibration target.** Phase FPR columns use the pooled threshold; the final column is the worst off-diagonal cross-phase **transfer** FPR and is not a pooled phase FPR. Isolation Forest and LSTM rows are arithmetic means across the tested seeds, with no seed-mean confidence interval.",
        "",
        "| Detector | Overall FPR (%) | Climb FPR (%) | Cruise FPR (%) | Descent FPR (%) | Descent − climb (pp) | Descent − cruise (pp) | Worst cross-phase transfer FPR (%) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for detector, seed, label in DETECTORS:
        rows = [core_row("DS02 discovery", detector, seed, metric) for metric in metrics]
        ids.extend(row["evidence_id"] for row in rows)
        sources.extend(row["original_source_csv"] for row in rows)
        cells = [row["display_rounded_value"] for row in rows]
        lines.append(f"| {label.replace(chr(10), ' ')} | " + " | ".join(cells) + " |")
    lines += ["", evidence_comment(ids, sources)]
    name = "table_ii_ds02_canonical.md"
    write_table(name, "\n".join(lines))
    return name, ids, sources


def table_iii() -> tuple[str, list[str], list[str]]:
    ids = []
    sources = []
    metrics = ("climb_fpr", "cruise_fpr", "descent_fpr", "descent_minus_climb", "descent_minus_cruise")
    target = primary_target() * 100
    coverage = float(meta("M0031")) * 100
    ids.append("M0031")
    lines = [
        f"**Table III. Frozen DS03 confirmatory pooled results at the nominal {target:g}% pooled healthy calibration target.** Climb/cruise/descent columns are pooled-threshold phase FPRs, not cross-phase transfer FPRs. Isolation Forest and LSTM point estimates are arithmetic seed means; the {coverage:g}% hierarchical-bootstrap contrast intervals apply only to individual detector runs, so no interval is assigned to a seed mean.",
        "",
        "| Detector | Climb FPR (%) | Cruise FPR (%) | Descent FPR (%) | Descent − climb (pp) | Run-level 95% CI (pp) | Descent − cruise (pp) | Run-level 95% CI (pp) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for detector, seed, label in DETECTORS:
        rows = [core_row("DS03 confirmation", detector, seed, metric) for metric in metrics]
        ids.extend(row["evidence_id"] for row in rows)
        sources.extend(row["original_source_csv"] for row in rows)
        cells = [row["display_rounded_value"] for row in rows]
        ci_a = rows[3]["ci_display_rounded"] or "—"
        ci_b = rows[4]["ci_display_rounded"] or "—"
        if seed != "-1" and (ci_a != "—" or ci_b != "—"):
            raise ValueError("A seed-mean CI was unexpectedly supplied")
        lines.append(
            f"| {label.replace(chr(10), ' ')} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {ci_a} | {cells[4]} | {ci_b} |"
        )
    exception_count = int(meta("E021560"))
    tested_count = int(meta("E021559"))
    exception_ids = ["E012536", "E012550", "E012576"]
    if exception_count != len(exception_ids) or any(evidence(claim_id)["seed_or_seed_aggregation"] != "2" for claim_id in exception_ids):
        raise ValueError("DS03 directional-exception note does not reconcile")
    ids.extend(["E021559", "E021560", *exception_ids])
    zero_ci_ids = ["E012043", "E012316", "E012589"]
    for claim_id in zero_ci_ids:
        row = evidence(claim_id)
        if not (float(row["ci_lower_95"]) <= 0 <= float(row["ci_upper_95"])):
            raise ValueError(f"Expected zero-containing LSTM interval: {claim_id}")
    ids.extend(zero_ci_ids)
    lines += [
        "",
        f"*Note:* {exception_count}/{tested_count} per-engine detector/seed directional rows were exceptions, all from LSTM seed 2. All three individual LSTM descent-minus-cruise bootstrap intervals include zero. Individual-seed interval tables belong in the supplement; an arithmetic seed-mean interval was not executed. Cross-phase transfer FPR is not tabulated here.",
        "",
        evidence_comment(ids, [*sources, "results/confirmation_ds03/hierarchical_bootstrap_ci.csv", "paper/evidence_ledger.csv"]),
    ]
    name = "table_iii_ds03_confirmation.md"
    write_table(name, "\n".join(lines))
    return name, ids, sources


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"Expected exactly one occurrence ({count}): {old[:90]}")
    return text.replace(old, new)


def assemble_submission(figures: list[tuple[str, list[str], list[str]]], tables: list[tuple[str, list[str], list[str]]]) -> None:
    base = (PAPER / "manuscript_full_internal.md").read_text(encoding="utf-8")
    anchor = "The present study concerns the healthy-alarm side of that trade-off; it does not evaluate fault-detection sensitivity or operational response.\n\n"
    clarification = (
        "The detectors are unsupervised with respect to fault labels; supplied health-state annotations are used only to select healthy samples for retrospective fitting, calibration, and evaluation. "
        "<!-- evidence: M0001; source_csv: paper/evidence_ledger.csv; generation_script: scripts/build_submission_package.py -->\n\n"
    )
    base = replace_once(base, anchor, anchor + clarification)
    base = replace_once(
        base,
        "Oracle health-state labels select healthy rows for model fitting, threshold calibration, and retrospective FPR evaluation; they are never numerical detector inputs. The study consequently makes no claim about fault sensitivity or real-aircraft deployment.",
        "The study consequently makes no claim about fault sensitivity or real-aircraft deployment.",
    )
    base, n = re.subn(r"(?m)^As secondary descriptive endpoints,.*?\n\n", "", base, count=1)
    if n != 1:
        raise ValueError("Could not move flight-level Results paragraph to supplementary plan")
    base, n = re.subn(r"(?m)^Flight-level fractions with any alarm.*?\n\n", "", base, count=1)
    if n != 1:
        raise ValueError("Could not move flight-level Discussion paragraph to supplementary plan")

    target = primary_target() * 100
    figure_captions = [
        "**Fig. 1. Study design.** DS02 exploratory discovery and robustness analyses preceded protocol freeze; DS03 is an independent confirmatory N-CMAPSS subset assessed once after freeze. No DS03 official-test access preceded the freeze. Conceptual workflow; no pooled phase FPR or cross-phase transfer FPR is plotted, and seed aggregation is not applicable.",
        f"**Fig. 2. DS02 exploratory phase-wise healthy row-level FPR at the nominal {target:g}% pooled calibration target.** PCA is a single run; Isolation Forest and causal LSTM reconstruction are arithmetic three-seed means. Bars are phase FPRs under pooled thresholds, not cross-phase transfer FPRs. Figures 2 and 4 use the same vertical scale; the nominal target is not an expected value for every audit phase. Error bars are omitted because run-level and seed-mean uncertainty are not interchangeable.",
        f"**Fig. 3. DS02 exploratory PCA cross-phase threshold transfer at the nominal {target:g}% target.** Calibration phase is on the vertical axis and healthy audit phase on the horizontal axis. Each cell is transfer FPR after phase-specific calibration, **not** pooled-threshold phase FPR. PCA has no seed mean.",
        f"**Fig. 4. Frozen DS03 confirmatory phase-wise healthy row-level FPR at the nominal {target:g}% pooled calibration target.** PCA is a single run; Isolation Forest and causal LSTM reconstruction are arithmetic three-seed means. Bars are pooled-threshold phase FPRs, not cross-phase transfer FPRs. The vertical scale matches Fig. 2. Error bars are omitted because run-level and seed-mean uncertainty are not interchangeable; no hierarchical-bootstrap interval for either seed mean was executed.",
    ]
    figure_lines = ["## Main Figures", ""]
    alt_texts = (
        "DS02 discovery, protocol freeze, and DS03 confirmation study design",
        "DS02 pooled-threshold healthy phase FPR by detector",
        "DS02 PCA cross-phase threshold transfer heatmap",
        "DS03 confirmatory pooled-threshold healthy phase FPR by detector",
    )
    for index, ((stem, ids, sources), caption) in enumerate(zip(figures, figure_captions), start=1):
        figure_lines += [f"![Figure {index}: {alt_texts[index - 1]}](figures/{stem}.png)", "", caption, "", evidence_comment(ids, sources), ""]
    table_lines = ["## Main Tables", ""]
    for name, _, _ in tables:
        table_lines += [(TABLES / name).read_text(encoding="utf-8").rstrip(), ""]
    internal = base.rstrip() + "\n\n" + "\n".join(figure_lines + table_lines).rstrip() + "\n"
    clean = re.sub(r"[ \t]*<!-- evidence:[^\r\n]*?-->", "", internal)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    if "<!-- evidence:" in clean or re.search(r"\[[EM]\d{4,6}", clean):
        raise ValueError("Submission copy still contains temporary evidence markup")
    (PAPER / "manuscript_submission_internal.md").write_text(internal, encoding="utf-8")
    (PAPER / "manuscript_submission.md").write_text(clean, encoding="utf-8")


def main() -> None:
    for required in (PAPER / "claim_audit.md", ROOT / "docs/AUTHORITATIVE_RESULTS.md", ROOT / "results/final_validation/frozen_protocol.md"):
        if not required.is_file():
            raise FileNotFoundError(required)
    set_plot_style()
    figures = [
        figure_1(),
        phase_figure("DS02 discovery", "figure_2_ds02_phase_fpr", "DS02 discovery: pooled-threshold phase FPR", "DS02 exploratory"),
        figure_3(),
        phase_figure("DS03 confirmation", "figure_4_ds03_phase_fpr", "DS03 frozen confirmation: pooled-threshold phase FPR", "DS03 confirmatory"),
    ]
    tables = [table_i(), table_ii(), table_iii()]
    assemble_submission(figures, tables)
    print("Generated exactly four main figures (SVG + 400-dpi PNG), three Markdown tables, and two submission manuscripts.")


if __name__ == "__main__":
    main()
