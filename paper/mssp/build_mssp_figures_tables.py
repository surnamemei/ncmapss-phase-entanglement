"""Build MSSP main-text figures, tables, and evidence files from committed outputs.

Inputs (read-only): frozen core results (paper/manuscript_core_results.csv, evidence IDs),
committed post-confirmation outputs (results/mssp_mitigation/) and adversarial-validation
outputs (results/mssp_adversarial/). No N-CMAPSS data are read and nothing is recomputed from
scores: every plotted or tabulated value is a committed value, a count of committed values, or
their range over detector runs. Every artefact gets a provenance sidecar listing the SHA-256 of
its inputs, and paper/mssp/evidence/ gets a SHA-256 manifest. Existing outputs are never
overwritten unless --rebuild is given (outputs are derived, not frozen evidence).

Figure plan (final six-figure plan, see docs/mssp/FINAL_STORY_LOCK.md):
1 study timeline; 2 frozen pooled phase FPRs (DS02 discovery vs DS03 confirmation);
3 between-phase disparity and nominal calibration error (P, C, C', Q); 4 matched healthy-flight
false-flag versus detection-delay comparison (supported anchors only) and locked-kappa burdens;
5 per-engine calibration transport (P, C, Q); 6 operating context and support distance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "paper/mssp"
FIG, TAB, EVI = PKG / "figures", PKG / "tables", PKG / "evidence"
CORE = ROOT / "paper/manuscript_core_results.csv"
MIT = ROOT / "results/mssp_mitigation"
ADV = ROOT / "results/mssp_adversarial"
DATASETS = ("ds02", "ds03")
FAMILIES = ("pca", "isolation_forest", "lstm_autoencoder")
FAMILY_LABEL = {"pca": "Residual PCA", "isolation_forest": "Isolation Forest", "lstm_autoencoder": "Past-only LSTM"}
FAMILY_MARKER = {"pca": "o", "isolation_forest": "s", "lstm_autoencoder": "^"}
ARMS = ("pooled", "phase_conditioned", "causal_regime")
ALL_ARMS = (*ARMS, "quantile_regression_W")
ARM_LABEL = {"pooled": "P", "phase_conditioned": "C", "causal_regime": "C′", "quantile_regression_W": "Q"}
ARM_COLOR = {"pooled": "#4d4d4d", "phase_conditioned": "#1f77b4", "causal_regime": "#ff7f0e",
             "quantile_regression_W": "#2ca02c"}
PHASES = ("climb", "cruise", "descent")
PHASE_COLOR = {"climb": "#2ca02c", "cruise": "#1f77b4", "descent": "#d62728"}
CLASS_MARKER = {1: "X", 2: "D", 3: "o"}
CALIBRATION_CLASSES = {"ds02": {3}, "ds03": {2, 3}}
ALPHA = 0.01
ANCHORS = (0.025, 0.05, 0.10, 0.15, 0.20)
WIDTH = 6.3

plt.rcParams.update({"font.size": 8.5, "axes.titlesize": 8.5, "axes.labelsize": 8.5, "legend.fontsize": 7.5,
                     "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "figure.dpi": 150, "savefig.dpi": 600,
                     "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                     "font.family": "DejaVu Sans"})


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


class Recorder:
    def __init__(self, rebuild):
        self.rebuild, self.inputs = rebuild, set()

    def read(self, path, **kwargs):
        self.inputs.add(Path(path))
        return pd.read_csv(path, float_precision="round_trip", **kwargs)

    def target(self, path):
        path = Path(path)
        if path.exists() and not self.rebuild:
            raise FileExistsError(f"{rel(path)} exists; use --rebuild to regenerate derived outputs")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def sidecar(self, outputs, note):
        record = {"outputs": {rel(o): sha256(o) for o in outputs},
                  "inputs": {rel(i): sha256(i) for i in sorted(self.inputs)},
                  "builder": rel(__file__), "builder_sha256": sha256(__file__), "note": note,
                  "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        first = Path(outputs[0])
        side = first.with_name(first.stem + ".provenance.json")
        side.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        self.inputs = set()
        return side


def save(rec, fig, name, note, folder=FIG):
    outputs = []
    for ext in ("pdf", "png"):
        path = rec.target(folder / f"{name}.{ext}")
        fig.savefig(path, bbox_inches="tight", dpi=600 if ext == "png" else None)
        outputs.append(path)
    plt.close(fig)
    rec.sidecar(outputs, note)


def adv(rec, dataset, folder, table):
    return rec.read(ADV / dataset / folder / f"{table}.csv")


def quality_frame(rec):
    frames = []
    for dataset in DATASETS:
        frames.append(adv(rec, dataset, "calibration_quality", "calibration_quality_metrics"))
        frames.append(adv(rec, dataset, "contextual_baseline", "baseline_calibration_quality"))
    return pd.concat(frames, ignore_index=True)


def family_handles(**kwargs):
    return [plt.Line2D([], [], marker=FAMILY_MARKER[f], linestyle="", color="white", markeredgecolor="black",
                       label=FAMILY_LABEL[f], **kwargs) for f in FAMILIES]


def arm_handles(arms):
    return [plt.Line2D([], [], marker="s", linestyle="", color=ARM_COLOR[a], markeredgecolor="black",
                       markeredgewidth=0.3, label=ARM_LABEL[a]) for a in arms]


def run_offsets(n, width=0.22):
    return np.linspace(-width / 2, width / 2, n) if n > 1 else np.zeros(1)


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig1_timeline(rec):
    fig = plt.figure(figsize=(WIDTH, 2.4))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    boxes = [
        ("DS02\ndiscovery", "exploratory:\nthree detectors,\ncorrection\nchallenge, cross-\nphase transfer", "#e8e8e8"),
        ("Protocol\nfreeze", "detectors,\ncorrection, phases,\ncalibration,\nendpoints and\nverdict rule fixed", "#d9d9d9"),
        ("DS03 one-shot\nconfirmation", "held-out engines;\npre-specified\npooled directional\npattern\nreproduced", "#c6dbef"),
        ("Post-confirmation\nprotocol v1.0", "P, C, C′ on the\nsame calibration\nengines; κ locked\nbefore abnormal-\nstate rows read", "#fdd0a2"),
        ("Adversarial\nvalidation", "nominal error,\nengine weighting,\nmatched false\nflags, support,\nbaseline Q", "#c7e9c0"),
    ]
    width, gap, left = 0.172, 0.029, 0.012
    for i, (title, body, color) in enumerate(boxes):
        x = left + i * (width + gap)
        ax.add_patch(FancyBboxPatch((x, 0.15), width, 0.6, boxstyle="round,pad=0.004,rounding_size=0.015",
                                    facecolor=color, edgecolor="#333333", linewidth=0.8))
        ax.text(x + width / 2, 0.665, title, ha="center", va="center", fontsize=7.2, fontweight="bold",
                linespacing=1.05)
        ax.text(x + width / 2, 0.39, body, ha="center", va="center", fontsize=6.6, linespacing=1.12)
        if i < len(boxes) - 1:
            ax.add_patch(FancyArrowPatch((x + width + 0.003, 0.45), (x + width + gap - 0.003, 0.45),
                                         arrowstyle="-|>", mutation_scale=8, color="#333333", linewidth=0.8))
    spans = ((left, left + 3 * width + 2 * gap, "Frozen discovery–confirmation evidence (cited unchanged)"),
             (left + 3 * (width + gap), left + 5 * width + 4 * gap, "Post-confirmation, exploratory"))
    for x0, x1, label in spans:
        ax.plot([x0, x1], [0.815, 0.815], color="#333333", linewidth=0.8)
        for xx in (x0, x1):
            ax.plot([xx, xx], [0.79, 0.815], color="#333333", linewidth=0.8)
        ax.text((x0 + x1) / 2, 0.875, label, ha="center", va="center", fontsize=7.0)
    ax.text(0.5, 0.06, "Each later stage was frozen before execution; none revises the DS03 verdict.",
            ha="center", va="center", fontsize=6.8, style="italic")
    save(rec, fig, "fig1_study_timeline", "Schematic; no data.")


def fig2_frozen_phase_fpr(rec):
    core = rec.read(CORE).set_index("manuscript_key")
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.4), sharey=True)
    ids = []
    titles = {"ds02": "(a) DS02: exploratory discovery", "ds03": "(b) DS03: frozen one-shot confirmation"}
    for ax, (tag, dataset) in zip(axes, (("D02", "ds02"), ("D03", "ds03"))):
        if dataset == "ds03":
            ax.set_facecolor("#f3f7fb")
        for j, (family, key) in enumerate((("pca", "PCA-SINGLE"), ("isolation_forest", "IF-MEAN"),
                                           ("lstm_autoencoder", "LSTM-MEAN"))):
            for k, phase in enumerate(PHASES):
                row = core.loc[f"{tag}-{key}-{phase}_fpr"]
                ids.append(row.evidence_id)
                x = j + (k - 1) * 0.27
                ax.bar(x, 100 * float(row.exact_value), width=0.25, color=PHASE_COLOR[phase],
                       edgecolor="black", linewidth=0.3, label=phase if j == 0 else None)
        ax.axhline(100 * ALPHA, color="black", linestyle="--", linewidth=0.8, label="nominal 1% (pooled target)")
        ax.set_xticks(range(3), ["Residual\nPCA", "Isolation Forest\n(seed mean)", "Past-only LSTM\n(seed mean)"])
        ax.set_title(titles[dataset])
    axes[0].set_ylabel("Healthy row-level FPR (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.05))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(rec, fig, "fig2_frozen_pooled_phase_fpr",
         "Frozen values from paper/manuscript_core_results.csv; evidence IDs: " + ",".join(ids)
         + ". IF and LSTM are frozen seed means.")


def fig3_calibration_quality(rec):
    q = quality_frame(rec)
    q = q[q.nominal_fpr == ALPHA]
    panels = (("spread", "all", "(a) A1 between-phase\ndisparity"),
              ("max_abs_error", "all", "(b) A2 maximum\nnominal error"),
              ("rms_error", "all", "(c) A3 RMS\nnominal error"),
              ("max_abs_error", "equal_engine", "(d) A2, audit engines\nweighted equally"))
    fig, axes = plt.subplots(2, 4, figsize=(WIDTH, 3.75), sharex=True)
    for r, dataset in enumerate(DATASETS):
        for c, (metric, unit, title) in enumerate(panels):
            ax = axes[r, c]
            part = q[(q.dataset == dataset) & (q.unit == unit)]
            for (detector, seed), run in part.groupby(["detector", "seed"]):
                values = [100 * float(run[run.scheme == a][metric].iloc[0]) for a in ALL_ARMS]
                ax.plot(range(len(ALL_ARMS)), values, color="#b0b0b0", linewidth=0.6, zorder=1)
                for i, a in enumerate(ALL_ARMS):
                    ax.scatter(i, values[i], marker=FAMILY_MARKER[detector], s=15, color=ARM_COLOR[a],
                               edgecolor="black", linewidth=0.3, zorder=2)
            ax.set_xticks(range(len(ALL_ARMS)), [ARM_LABEL[a] for a in ALL_ARMS])
            ax.set_xlim(-0.4, len(ALL_ARMS) - 0.6)
            ax.set_ylim(bottom=0)
            if r == 0:
                ax.set_title(title)
            if c == 0:
                ax.set_ylabel(f"{dataset.upper()}\npercentage points")
    fig.legend(handles=family_handles(), loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.04, 1, 1), h_pad=1.0, w_pad=0.6)
    save(rec, fig, "fig3_disparity_and_nominal_calibration",
         "Validation A at the 1% target; one line per detector run (7 per dataset). Q = continuous contextual "
         "quantile-regression baseline (healthy side). Row-pooled unless stated. All paired U1 intervals "
         "(arm minus P) include zero.")


def fig4_matched_tradeoff(rec):
    fig = plt.figure(figsize=(WIDTH, 4.0))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.5, 1], height_ratios=[1, 1], hspace=0.5, wspace=0.42)
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[1, 0])]
    ax_locked = fig.add_subplot(grid[:, 1])
    arm_shift = {"phase_conditioned": -0.17, "causal_regime": 0.17}
    ylims = []
    for ax, dataset in zip(axes, DATASETS):
        m = adv(rec, dataset, "matched_delay", "matched_false_flag_comparisons")
        m = m[(m.rule == "nearest") & (m.nominal_fpr == ALPHA) & m.supported]
        ax.axhline(0, color="black", linewidth=0.7, zorder=0)
        for i, anchor in enumerate(ANCHORS):
            for arm, shift in arm_shift.items():
                part = m[(m.anchor_ffr == anchor) & (m.arm == arm)].sort_values(["detector", "seed"])
                offsets = run_offsets(len(part), 0.2)
                for off, row in zip(offsets, part.itertuples()):
                    ax.scatter(i + shift + off, row.paired_lower_median_difference, marker=FAMILY_MARKER[row.detector],
                               s=15, color=ARM_COLOR[arm], edgecolor="black", linewidth=0.3, zorder=2)
            ylims.append(m.paired_lower_median_difference.abs().max())
        ax.set_xticks(range(len(ANCHORS)), [f"{100 * a:g}%" for a in ANCHORS])
        ax.set_xlim(-0.5, len(ANCHORS) - 0.5)
        ax.set_ylabel("Arm − P, paired median\ndelay difference (flights)")
        ax.set_title(f"({'ab'[DATASETS.index(dataset)]}) {dataset.upper()}: supported anchors only")
        ax.text(0.99, 0.04, "below 0 = earlier than P", ha="right", va="bottom", fontsize=6.5, color="#555555",
                transform=ax.transAxes)
    lim = 1.12 * max(ylims)
    for ax in axes:
        ax.set_ylim(-lim, lim)
    axes[1].set_xlabel("Matched realized healthy-flight false-flag rate")
    positions, labels = [], []
    for g, dataset in enumerate(DATASETS):
        locked = adv(rec, dataset, "matched_delay", "locked_operating_points")
        locked = locked[locked.nominal_fpr == ALPHA]
        base = adv(rec, dataset, "contextual_baseline", "baseline_flight_false_flags")
        base = base[(base.nominal_fpr == ALPHA) & (base.unit.astype(str) == "all")]
        for k, arm in enumerate(ALL_ARMS):
            x = g * 4.6 + k
            part = (base if arm == "quantile_regression_W" else locked[locked.scheme == arm])
            part = part.sort_values(["detector", "seed"])
            values = 100 * (part.false_flag_rate if arm == "quantile_regression_W" else part.ffr)
            offsets = run_offsets(len(part), 0.36)
            for off, (row, v) in zip(offsets, zip(part.itertuples(), values)):
                ax_locked.scatter(x + off, v, marker=FAMILY_MARKER[row.detector], s=14, color=ARM_COLOR[arm],
                                  edgecolor="black", linewidth=0.3, zorder=2)
            positions.append(x)
            labels.append(ARM_LABEL[arm])
        ax_locked.text(g * 4.6 + 1.5, -0.13, dataset.upper(), ha="center", va="top",
                       transform=ax_locked.get_xaxis_transform())
    ax_locked.axhline(5, color="black", linestyle="--", linewidth=0.8)
    ax_locked.set_xticks(positions, labels)
    ax_locked.set_ylim(bottom=0)
    ax_locked.set_ylabel("Realized false-flag rate at calibration κ (%)")
    ax_locked.set_title("(c) Operating points at κ")
    handles = arm_handles(ALL_ARMS) + family_handles()
    handles.append(plt.Line2D([], [], color="black", linestyle="--", linewidth=0.8, label="nominal 5% (κ design)"))
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.05))
    fig.subplots_adjust(bottom=0.2, top=0.94, left=0.12, right=0.98)
    save(rec, fig, "fig4_matched_false_flag_tradeoff",
         "Validation B at the 1% row target, nearest-anchor rule, supported anchors only (no interpolation). "
         "Counts above each group: earlier/tie/later runs. Panel (c): pooled realized FFR at the locked kappa "
         "(P, C, C') and at the calibration kappa of Q.")


def fig5_engine_transport(rec):
    q = quality_frame(rec)
    q = q[(q.nominal_fpr == ALPHA) & (q.weighting == "per_engine")]
    arms = ("pooled", "phase_conditioned", "quantile_regression_W")
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.75), gridspec_kw={"width_ratios": [3, 6]}, sharey=True)
    top = 100 * q[q.scheme.isin(arms)].max_abs_error.max() * 1.08
    for ax, dataset in zip(axes, DATASETS):
        part = q[q.dataset == dataset]
        classes = adv(rec, dataset, "support_transport", "support_engines").set_index("unit").flight_class
        units = sorted(part.unit.astype(int).unique())
        for k, unit in enumerate(units):
            absent = int(classes.loc[unit]) not in CALIBRATION_CLASSES[dataset]
            if absent:
                ax.add_patch(Rectangle((k - 0.45, 0), 0.9, top, color="#f2e6f7", zorder=0, linewidth=0))
            for a, arm in enumerate(arms):
                cell = part[(part.unit.astype(int) == unit) & (part.scheme == arm)].sort_values(["detector", "seed"])
                offsets = run_offsets(len(cell), 0.16)
                x0 = k + (a - 1) * 0.28
                for off, row in zip(offsets, cell.itertuples()):
                    ax.scatter(x0 + off, 100 * row.max_abs_error, marker=FAMILY_MARKER[row.detector], s=12,
                               color=ARM_COLOR[arm], edgecolor="black", linewidth=0.25, zorder=2)
            label = f"engine {unit}\nclass {int(classes.loc[unit])}" + ("*" if absent else "")
            ax.text(k, -0.05, label, ha="center", va="top", fontsize=7, transform=ax.get_xaxis_transform())
        ax.set_xticks([])
        ax.set_xlim(-0.55, len(units) - 0.45)
        ax.set_ylim(0, top)
        classes_text = ", ".join(str(c) for c in sorted(CALIBRATION_CLASSES[dataset]))
        noun = "class" if len(CALIBRATION_CLASSES[dataset]) == 1 else "classes"
        ax.set_title(f"({'ab'[DATASETS.index(dataset)]}) {dataset.upper()} (calibration: {noun} {classes_text})")
    axes[0].set_ylabel("Per-engine A2, max |FPR − α|\n(percentage points)")
    first = arm_handles(arms) + [Rectangle((0, 0), 1, 1, color="#f2e6f7",
                                           label="* flight class absent from this calibration set")]
    fig.legend(handles=first, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.035))
    fig.legend(handles=family_handles(), loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.13, 1, 1), w_pad=1.0)
    save(rec, fig, "fig5_engine_transport",
         "Per-engine A2 at the 1% target for every detector run (7 per engine) under P, C and Q; "
         "flight classes from support_engines.csv; calibration engines are class 3 (DS02) and classes 2, 3 (DS03).")


def fig6_support(rec):
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 2.65), gridspec_kw={"width_ratios": [1.25, 1, 1]})
    ax = axes[0]
    ticks, ticklabels = [], []
    for i, dataset in enumerate(DATASETS):
        effect = adv(rec, dataset, "support_transport", "calibration_phase_effect")
        effect = effect[(effect.nominal_fpr == ALPHA) & (effect.evaluation == "in_sample_pooled_tau")]
        audit = rec.read(MIT / dataset / "stage_d" / "healthy_phase_fpr_by_scheme.csv")
        audit = audit[(audit.nominal_fpr == ALPHA) & (audit.scheme == "pooled") & (audit.unit.astype(str) == "all")]
        for k, phase in enumerate(PHASES):
            x = i * 3.6 + k
            cal = effect.sort_values(["detector", "seed"])
            aud = audit[audit.phase == phase].sort_values(["detector", "seed"])
            for off, row in zip(run_offsets(len(cal), 0.22), cal.itertuples()):
                ax.scatter(x - 0.2 + off, 100 * getattr(row, f"{phase}_fpr"), marker=FAMILY_MARKER[row.detector],
                           s=12, facecolor="white", edgecolor=PHASE_COLOR[phase], linewidth=0.8, zorder=2)
            for off, row in zip(run_offsets(len(aud), 0.22), aud.itertuples()):
                ax.scatter(x + 0.2 + off, 100 * row.rate, marker=FAMILY_MARKER[row.detector], s=12,
                           color=PHASE_COLOR[phase], edgecolor="black", linewidth=0.25, zorder=2)
            ticks.append(x)
            ticklabels.append(phase)
        ax.text(i * 3.6 + 1, 4.2, dataset.upper(), ha="center", va="top", fontsize=7.5)
    ax.set_ylim(0, 4.3)
    ax.axhline(100 * ALPHA, color="black", linestyle="--", linewidth=0.8)
    ax.set_xticks(ticks, ticklabels, rotation=40, ha="right", rotation_mode="anchor", fontsize=7)
    ax.set_ylabel("Healthy FPR under P (%)")
    ax.set_title("(a) Calibration engines (open)\nand audit engines (filled)")
    for j, dataset in enumerate(DATASETS):
        ax = axes[j + 1]
        cells = adv(rec, dataset, "support_transport", "support_cells")
        rates = rec.read(MIT / dataset / "stage_d" / "healthy_phase_fpr_by_scheme.csv")
        rates = rates[(rates.nominal_fpr == ALPHA) & (rates.scheme == "phase_conditioned")
                      & (rates.unit.astype(str) != "all") & rates.phase.isin(PHASES)]
        err = rates.assign(unit=rates.unit.astype(int), err=np.abs(rates.rate - ALPHA)).groupby(["unit", "phase"]).err.mean()
        cells = cells.set_index(["unit", "phase"]).join(err).reset_index()
        assoc = adv(rec, dataset, "support_transport", "support_associations")
        rho = assoc[assoc.nominal_fpr == ALPHA].rho_dphase_vs_abs_error_C.median()
        top_error = cells.err.nlargest(3).min()
        for row in cells.itertuples():
            ax.scatter(row.d_phase_median, 100 * row.err, marker=CLASS_MARKER[row.flight_class],
                       color=PHASE_COLOR[row.phase], edgecolor="black", linewidth=0.3, s=26, zorder=2)
            if row.err >= top_error or row.d_phase_median > 0.3:
                ax.annotate(f"engine {row.unit}", (row.d_phase_median, 100 * row.err), fontsize=6,
                            xytext=(3, 2), textcoords="offset points")
        ax.set_xscale("log")
        ax.set_xlabel("Same-phase support distance\n(median, standardized W)")
        ax.set_title(f"({'bc'[j]}) {dataset.upper()} engine × phase cells\nmedian Spearman ρ = {rho:.2f}")
        if j == 0:
            ax.set_ylabel("|FPR − α| under C\n(pp, mean of 7 runs)")
    handles = [plt.Line2D([], [], marker="s", linestyle="", color=PHASE_COLOR[p], label=p) for p in PHASES]
    handles += [plt.Line2D([], [], marker=m, linestyle="", color="white", markeredgecolor="black",
                           label=f"flight class {c}") for c, m in CLASS_MARKER.items()]
    fig.legend(handles=handles, loc="lower center", ncol=6, frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout(rect=(0, 0.07, 1, 1), w_pad=1.2)
    save(rec, fig, "fig6_operating_context_and_support",
         "Validation C: (a) C0, pooled-threshold phase FPR in the calibration engines (in-sample) and in the "
         "audit engines, one marker per detector run; (b,c) support distance against |FPR - alpha| under C "
         "(mean over the 7 detector runs per cell). Median Spearman rho over runs from support_associations.csv. "
         "Descriptive; no p-values.")


# ---------------------------------------------------------------------------
# Tables and evidence
# ---------------------------------------------------------------------------

def tex_escape(value):
    text = str(value)
    for a, b in (("\\", r"\textbackslash{}"), ("_", r"\_"), ("%", r"\%"), ("&", r"\&"), ("#", r"\#")):
        text = text.replace(a, b)
    return text.replace("−", "$-$").replace("′", "$'$").replace("–", "--").replace("κ", r"$\kappa$")


def tex_header(name):
    """Headers may contain "\\n" line breaks, typeset with makecell; the CSV keeps a single line."""
    parts = str(name).split("\n")
    return tex_escape(parts[0]) if len(parts) == 1 else "\\makecell{" + "\\\\".join(tex_escape(p) for p in parts) + "}"


def write_table(rec, frame, name, caption, note, align=None):
    csv = rec.target(TAB / f"{name}.csv")
    flat = frame.rename(columns=lambda c: str(c).replace("\n", " "))
    flat = flat.apply(lambda col: col.map(lambda v: v.replace("–\n", "–").replace("\n", " ") if isinstance(v, str) else v))
    flat.to_csv(csv, index=False)
    tex = rec.target(TAB / f"{name}.tex")
    columns = align or ("l" * len(frame.columns))
    lines = [f"% {caption}", "\\begin{tabular}{" + columns + "}", "\\toprule",
             " & ".join(tex_header(c) for c in frame.columns) + " \\\\", "\\midrule"]
    previous = None
    for row in frame.itertuples(index=False):
        values = list(row)
        shown = list(values)
        if previous is not None and values[0] != previous:
            lines.append("\\midrule")
        elif previous is not None and align is None:
            shown[0] = ""
        previous = values[0]
        lines.append(" & ".join(tex_header(v) for v in shown) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    tex.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rec.sidecar([csv, tex], note)


def rng(values, scale=100, digits=2):
    values = np.asarray(values, dtype=float) * scale
    lo, hi = np.nanmin(values), np.nanmax(values)
    return f"{lo:.{digits}f}" if round(lo, digits) == round(hi, digits) else f"{lo:.{digits}f}–{hi:.{digits}f}"


def signed_range(values, digits=2):
    values = np.asarray(values, dtype=float)
    fmt = lambda v: f"{v:+.{digits}f}".replace("-", "−")  # noqa: E731
    lo, hi = np.nanmin(values), np.nanmax(values)
    return fmt(lo) if round(lo, digits) == round(hi, digits) else f"{fmt(lo)} to {fmt(hi)}"


def table1_design(rec):
    locks = {d: json.loads((MIT / d / "stage_l" / "mitigation_lock.json").read_text()) for d in DATASETS}
    records = {d: json.loads((MIT / d / "stage_e" / "stage_e_record.json").read_text()) for d in DATASETS}
    for d in DATASETS:
        rec.inputs.update({MIT / d / "stage_l" / "mitigation_lock.json", MIT / d / "stage_e" / "stage_e_record.json"})
    labels = {d: rec.read(MIT / d / "stage_b" / "label_structure.csv") for d in DATASETS}

    def engines(dataset, role):
        part = labels[dataset][labels[dataset].role == role].sort_values("unit")
        return ", ".join(f"{int(r.unit)} ({int(r.flight_class)})" for r in part.itertuples())

    def absent(dataset):
        frame = labels[dataset]
        present = set(frame[frame.role == "calibration"].flight_class)
        part = frame[(frame.role == "audit") & ~frame.flight_class.isin(present)].sort_values("unit")
        return ", ".join(f"{int(r.unit)} (class {int(r.flight_class)})" for r in part.itertuples())

    def flights(dataset, role):
        return int(labels[dataset][labels[dataset].role == role].healthy_flights.sum())

    for d, n_audit in (("ds02", 76), ("ds03", 148)):
        if flights(d, "calibration") != locks[d]["calibration_flights"] or flights(d, "audit") != n_audit:
            raise ValueError(f"{d}: healthy flight counts disagree with the calibration lock / plan N_h")

    rows = [
        ("Role", "exploratory discovery", "frozen one-shot confirmation (held-out official-test engines)"),
        ("Post-confirmation role", "reused for exploratory transport analyses", "reused for exploratory transport analyses"),
        ("Model-fitting engines (flight class)", engines("ds02", "model_fit"), engines("ds03", "model_fit")),
        ("Calibration engines (flight class)", engines("ds02", "calibration"), engines("ds03", "calibration")),
        ("Audit engines (flight class)", engines("ds02", "audit"), engines("ds03", "audit")),
        ("Audit engines of a class absent from calibration", absent("ds02"), absent("ds03")),
        ("Healthy calibration / audit flights", f"{flights('ds02', 'calibration')} / {flights('ds02', 'audit')}",
         f"{flights('ds03', 'calibration')} / {flights('ds03', 'audit')}"),
        ("Abnormal-state (hs = 0) rows read, once", f"{records['ds02']['abnormal_rows_read']:,}",
         f"{records['ds03']['abnormal_rows_read']:,}"),
        ("Phase labels", "retrospective climb/cruise/descent (P, C); past-only regimes (C′)",
         "retrospective climb/cruise/descent (P, C); past-only regimes (C′)"),
        ("Calibration arms compared", "P, C, C′; Q (healthy side only)", "P, C, C′; Q (healthy side only)"),
    ]
    frame = pd.DataFrame(rows, columns=["Item", "DS02", "DS03"])
    write_table(rec, frame, "table1_design", "Datasets, partitions, phase and calibration roles",
                "Engine roles, flight classes, flight counts and abnormal-row counts from committed records.",
                align=">{\\raggedright\\arraybackslash}p{0.25\\textwidth}>{\\raggedright\\arraybackslash}p{0.31\\textwidth}"
                      ">{\\raggedright\\arraybackslash}p{0.36\\textwidth}")


def table2_frozen(rec):
    core = rec.read(CORE).set_index("manuscript_key")
    rows = []
    for tag, label in (("D02", "DS02 (discovery)"), ("D03", "DS03 (confirmation)")):
        for key, family in (("PCA-SINGLE", "Residual PCA"), ("IF-MEAN", "Isolation Forest\n(seed mean)"),
                            ("LSTM-MEAN", "Past-only LSTM\n(seed mean)")):
            entry = {"Dataset": label, "Detector": family}
            ids = []
            for metric, head in (("climb_fpr", "Climb"), ("cruise_fpr", "Cruise"), ("descent_fpr", "Descent"),
                                 ("overall_fpr", "Overall"), ("descent_minus_climb", "Descent\n− climb"),
                                 ("descent_minus_cruise", "Descent\n− cruise"),
                                 ("worst_cross_phase_transfer_fpr", "Worst\ntransfer FPR")):
                row = core.loc[f"{tag}-{key}-{metric}"]
                entry[head] = row.display_rounded_value
                ids.append(row.evidence_id)
            entry["Evidence\nIDs"] = f"{min(ids)}–\n{max(ids)}"
            rows.append(entry)
    write_table(rec, pd.DataFrame(rows), "table2_frozen_pooled_calibration",
                "Frozen pooled-calibration audit at the 1% target",
                "Frozen display values and evidence IDs from paper/manuscript_core_results.csv (unchanged).")


def table3_quality(rec):
    q = quality_frame(rec)
    q = q[q.nominal_fpr == ALPHA]
    rows = []
    metrics = (("spread", "A1\ndisparity"), ("max_abs_error", "A2 max\nerror"), ("rms_error", "A3 RMS\nerror"),
               ("overall_abs_error", "A5 overall\nerror"))
    for dataset in DATASETS:
        pooled = q[(q.dataset == dataset) & (q.unit == "all") & (q.scheme == "pooled")].set_index(["detector", "seed"])
        for scheme in ALL_ARMS:
            part = q[(q.dataset == dataset) & (q.unit == "all") & (q.scheme == scheme)].set_index(["detector", "seed"])
            equal = q[(q.dataset == dataset) & (q.unit == "equal_engine") & (q.scheme == scheme)]
            entry = {"Dataset": dataset.upper(), "Arm": ARM_LABEL[scheme]}
            for metric, head in metrics:
                entry[head] = rng(part[metric])
            if scheme == "pooled":
                entry["Runs below P\n(A1/A2/A3/A5)"] = "reference"
            else:
                entry["Runs below P\n(A1/A2/A3/A5)"] = "/".join(
                    str(int((part[m] < pooled.loc[part.index, m]).sum())) for m, _ in metrics)
            entry["A2, equal-\nengine"] = rng(equal.max_abs_error)
            rows.append(entry)
    write_table(rec, pd.DataFrame(rows), "table3_calibration_quality",
                "Post-confirmation calibration quality at the 1% target",
                "Validation A outputs and the healthy-side Q baseline; percentage points, range over the 7 detector "
                "runs; counts of runs (of 7) in which the arm is below P.")


def table4_matched(rec):
    rows = []
    for dataset in DATASETS:
        m = adv(rec, dataset, "matched_delay", "matched_false_flag_comparisons")
        m = m[(m.rule == "nearest") & (m.nominal_fpr == ALPHA)]
        labels = adv(rec, dataset, "matched_delay", "matched_labels")
        labels = labels[labels.nominal_fpr == ALPHA]
        for arm in ("phase_conditioned", "causal_regime"):
            entry = {"Dataset": dataset.upper(), "Arm": ARM_LABEL[arm]}
            for anchor in ANCHORS:
                part = m[(m.arm == arm) & (m.anchor_ffr == anchor) & m.supported]
                d = part.paired_lower_median_difference
                entry[f"{100 * anchor:g}%"] = f"{int((d < 0).sum())}/{int((d == 0).sum())}/{int((d > 0).sum())}"
            part = labels[labels.arm == arm]
            counts = part.matched_label.value_counts()
            entry["Run labels\nE/M/=/L"] = "/".join(str(int(counts.get(k, 0))) for k in (
                "earlier at matched burden", "mixed", "equal", "later at matched burden"))
            entry["Locked FFR,\nP (%)"] = rng(part.locked_ffr_pooled, 100, 1)
            entry["Locked FFR,\narm (%)"] = rng(part.locked_ffr_arm, 100, 1)
            entry["Curve-mean\ndifference (flights)"] = signed_range(part.curve_mean_difference)
            rows.append(entry)
    write_table(rec, pd.DataFrame(rows), "table4_matched_false_flag_delay",
                "Detection delay at matched healthy-flight false-flag burden (1% row target)",
                "Validation B outputs (nearest-anchor rule, one-flight support tolerance, supported anchors only); "
                "anchor cells are earlier/tie/later run counts of the paired lower-median per-engine difference.")


def table5_engines(rec):
    q = quality_frame(rec)
    q = q[q.nominal_fpr == ALPHA]
    rows = []
    for dataset in DATASETS:
        classes = adv(rec, dataset, "support_transport", "support_engines").set_index("unit").flight_class
        paired = adv(rec, dataset, "calibration_quality", "calibration_quality_paired")
        paired = paired[(paired.nominal_fpr == ALPHA) & (paired.arm == "phase_conditioned")]
        part = q[q.dataset == dataset]
        units = sorted(part[part.weighting == "per_engine"].unit.astype(int).unique())
        for unit in units + ["equal"]:
            if unit == "equal":
                cell = part[part.unit == "equal_engine"]
                cats = paired[paired.weighting == "equal_engine"].category
                name, klass = "all (equal\nweight)", "–"
            else:
                cell = part[(part.weighting == "per_engine") & (part.unit.astype(str) == str(unit))]
                cats = paired[(paired.weighting == "per_engine") & (paired.unit.astype(str) == str(unit))].category
                c = int(classes.loc[unit])
                name, klass = str(unit), f"{c}" + (" (absent)" if c not in CALIBRATION_CLASSES[dataset] else "")
            piv = cell.pivot_table(index=["detector", "seed"], columns="scheme", values="max_abs_error")
            rows.append({"Dataset": dataset.upper(), "Engine": name, "Flight\nclass": klass,
                         "A2, P": rng(piv["pooled"]), "A2, C": rng(piv["phase_conditioned"]),
                         "C worse\nthan P": f"{int((piv['phase_conditioned'] > piv['pooled']).sum())}/7",
                         "C categories\n1/2/3/4": "/".join(str(int((cats == k).sum())) for k in (1, 2, 3, 4)),
                         "A2, Q": rng(piv["quantile_regression_W"]),
                         "Q worse\nthan P": f"{int((piv['quantile_regression_W'] > piv['pooled']).sum())}/7"})
    write_table(rec, pd.DataFrame(rows), "table5_engine_transport",
                "Cross-engine transport of pooled-level calibration gains (1% target)",
                "Per-engine and equal-engine A2 (percentage points, range over the 7 detector runs) under P, C and Q; "
                "run counts; Validation A categories for C against P.")


def evidence(rec):
    EVI.mkdir(parents=True, exist_ok=True)
    frames = []
    for dataset in DATASETS:
        q = adv(rec, dataset, "calibration_quality", "calibration_quality_metrics")
        frames.append(q.assign(source=f"results/mssp_adversarial/{dataset}/calibration_quality/calibration_quality_metrics.csv"))
        base = ADV / dataset / "contextual_baseline" / "baseline_calibration_quality.csv"
        frames.append(rec.read(base).assign(source=rel(base)))
    metrics = pd.concat(frames, ignore_index=True)
    out = rec.target(EVI / "adversarial_calibration_metrics.csv")
    metrics.to_csv(out, index=False)
    rec.sidecar([out], "Validation A metrics (A1-A7) for every dataset, run, target, arm, and weighting, with Q.")
    per_dataset = lambda folder, table: [ADV / d / folder / f"{table}.csv" for d in DATASETS]  # noqa: E731
    mitigation = lambda stage, table: [MIT / d / stage / f"{table}.csv" for d in DATASETS]  # noqa: E731
    copies = {
        "adversarial_calibration_paired.csv": per_dataset("calibration_quality", "calibration_quality_paired"),
        "adversarial_calibration_u1_ci.csv": per_dataset("calibration_quality", "calibration_quality_u1_ci"),
        "adversarial_matched_labels.csv": per_dataset("matched_delay", "matched_labels"),
        "adversarial_matched_comparisons.csv": per_dataset("matched_delay", "matched_false_flag_comparisons"),
        "adversarial_locked_operating_points.csv": per_dataset("matched_delay", "locked_operating_points"),
        "adversarial_operating_points.csv": per_dataset("matched_delay", "operating_points"),
        "adversarial_support_cells.csv": per_dataset("support_transport", "support_cells"),
        "adversarial_support_associations.csv": per_dataset("support_transport", "support_associations"),
        "adversarial_calibration_phase_effect.csv": per_dataset("support_transport", "calibration_phase_effect"),
        "adversarial_baseline_fits.csv": per_dataset("contextual_baseline", "baseline_fits"),
        "adversarial_baseline_phase_fpr.csv": per_dataset("contextual_baseline", "baseline_phase_fpr"),
        "adversarial_baseline_flight_false_flags.csv": per_dataset("contextual_baseline", "baseline_flight_false_flags"),
        "adversarial_robustness_classification.csv": [ADV / "summary/robustness_classification.csv"],
        "adversarial_denominator_audit.csv": [ADV / "summary/denominator_audit.csv"],
        "adversarial_error_decomposition.csv": [ADV / "summary/post_plan_error_decomposition.csv"],
        "mitigation_healthy_phase_fpr_by_scheme.csv": mitigation("stage_d", "healthy_phase_fpr_by_scheme"),
        "mitigation_healthy_flight_burden_by_scheme.csv": mitigation("stage_d", "healthy_flight_burden_by_scheme"),
        "mitigation_u1_bootstrap_ci.csv": mitigation("stage_d", "u1_bootstrap_ci"),
        "mitigation_detection_delay.csv": mitigation("stage_e", "detection_delay"),
        "mitigation_false_flags_with_delay.csv": mitigation("stage_e", "healthy_flight_false_flags_with_delay"),
        "mitigation_abnormal_alarm_rates.csv": mitigation("stage_e", "abnormal_alarm_rates"),
        "mitigation_guardrails.csv": mitigation("stage_e", "guardrails"),
        "mitigation_u2_bootstrap_ci.csv": mitigation("stage_e", "u2_bootstrap_ci"),
    }
    for name, sources in copies.items():
        parts = []
        for source in sources:
            frame = rec.read(source)
            if len(sources) > 1:
                dataset = source.relative_to(ROOT).parts[2]
                frame = frame.assign(source=rel(source))
                if "dataset" not in frame.columns:
                    frame.insert(0, "dataset", dataset)
            parts.append(frame)
        target = rec.target(EVI / name)
        pd.concat(parts, ignore_index=True).to_csv(target, index=False)
        rec.sidecar([target], f"Concatenation of {len(parts)} committed output table(s); values unchanged.")
    manifest = EVI / "SHA256SUMS"
    lines = [f"{sha256(p)}  {p.name}" for p in sorted(EVI.glob("*")) if p.is_file() and p.name != "SHA256SUMS"]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


BUILDERS = {"fig1": fig1_timeline, "fig2": fig2_frozen_phase_fpr, "fig3": fig3_calibration_quality,
            "fig4": fig4_matched_tradeoff, "fig5": fig5_engine_transport, "fig6": fig6_support,
            "table1": table1_design, "table2": table2_frozen, "table3": table3_quality, "table4": table4_matched,
            "table5": table5_engines, "evidence": evidence}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="Regenerate existing derived outputs")
    parser.add_argument("--only", default="", help="Comma-separated subset of " + ",".join(BUILDERS))
    args = parser.parse_args()
    rec = Recorder(args.rebuild)
    selected = [s for s in args.only.split(",") if s] or list(BUILDERS)
    for key in selected:
        BUILDERS[key](rec)
        print(f"built: {key}")


if __name__ == "__main__":
    main()
