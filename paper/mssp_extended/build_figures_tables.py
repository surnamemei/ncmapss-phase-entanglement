"""Build the extended manuscript's figures, tables and evidence files from committed extension outputs.

Inputs are read-only:
- per-subset lock and audit tables (`results/extension/<subset>/`);
- cross-dataset summaries and decisions (`results/extension/summary/`);
- the metadata audit (`docs/extension/`).

No N-CMAPSS data are read and nothing is recomputed from scores. Every plotted or tabulated value is a
committed value, or a median or range of committed values over detector runs. Each artefact gets a
provenance sidecar with the SHA-256 of its inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "paper/mssp_extended"
FIG, TAB, EVI = PKG / "figures", PKG / "tables", PKG / "evidence"
EXT = ROOT / "results/extension"
SUM = EXT / "summary"
REF = ("DS02", "DS03")
NEW = ("DS01", "DS04", "DS05", "DS06", "DS07", "DS08a", "DS08c")
ALL = REF + NEW
FAMILY = {"DS02": "ref.", "DS03": "ref.", "DS01": "F1", "DS04": "F2", "DS05": "F3", "DS06": "F3", "DS07": "F3",
          "DS08a": "F4", "DS08c": "F5"}
DETECTORS = ("pca", "isolation_forest", "lstm_autoencoder", "cvae")
DET_LABEL = {"pca": "Residual PCA", "isolation_forest": "Isolation Forest", "lstm_autoencoder": "Past-only LSTM",
             "cvae": "CVAE"}
DET_MARKER = {"pca": "o", "isolation_forest": "s", "lstm_autoencoder": "^", "cvae": "D"}
DET_COLOR = {"pca": "#1b9e77", "isolation_forest": "#7570b3", "lstm_autoencoder": "#d95f02", "cvae": "#e7298a"}
ARMS = ("pooled", "phase_conditioned", "quantile_regression_W")
ARM_LABEL = {"pooled": "P", "phase_conditioned": "C", "quantile_regression_W": "Q"}
ARM_COLOR = {"pooled": "#4d4d4d", "phase_conditioned": "#1f77b4", "quantile_regression_W": "#2ca02c"}
PHASES = ("climb", "cruise", "descent")
PHASE_COLOR = {"climb": "#2ca02c", "cruise": "#1f77b4", "descent": "#d62728"}
RULE_COLOR = {"R0": "#4d4d4d", "R1": "#9467bd", "R2": "#8c564b"}
ALPHA = 0.01
WIDTH = 6.3

plt.rcParams.update({"font.size": 8.5, "axes.titlesize": 8.5, "axes.labelsize": 8.5, "legend.fontsize": 7.2,
                     "xtick.labelsize": 7.2, "ytick.labelsize": 7.2, "figure.dpi": 150, "savefig.dpi": 600,
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

    def json(self, path):
        self.inputs.add(Path(path))
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def audit(self, key, table):
        return self.read(EXT / key / "audit" / f"{table}.csv")

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
        first.with_name(first.stem + ".provenance.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        self.inputs = set()


def save(rec, fig, name, note):
    outputs = []
    for ext in ("pdf", "png"):
        path = rec.target(FIG / f"{name}.{ext}")
        fig.savefig(path, bbox_inches="tight", dpi=600 if ext == "png" else None)
        outputs.append(path)
    plt.close(fig)
    rec.sidecar(outputs, note)


def shade_reference(ax, n_ref=len(REF)):
    ax.axvspan(-0.5, n_ref - 0.5, color="0.93", zorder=0)


def subset_ticks(ax, keys=ALL):
    ax.set_xticks(range(len(keys)), [f"{k}\n{FAMILY[k]}" for k in keys])


def locks(rec):
    return {k: rec.json(EXT / k / "lock" / "calibration_lock.json") for k in ALL}


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig1_design(rec):
    fig = plt.figure(figsize=(WIDTH, 2.7))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    stages = [("DS02 discovery", "exploratory: three\nresidual detectors,\ncross-phase transfer", "#e8e8e8"),
              ("DS03 one-shot\nconfirmation", "frozen protocol;\npooled directional\npattern reproduced", "#c6dbef"),
              ("Post-confirmation\nanalyses (DS02, DS03)", "P, C, C′, Q; nominal\nerror; engine weighting;\nmatched false flags", "#fdd0a2"),
              ("Frozen multi-subset\nextension", "7 new subsets, 30 audit\nengines; CVAE; fleet\ncomposition; persistence", "#c7e9c0")]
    width, gap, left, y0, h = 0.215, 0.03, 0.03, 0.43, 0.46
    for i, (title, body, color) in enumerate(stages):
        x = left + i * (width + gap)
        ax.add_patch(FancyBboxPatch((x, y0), width, h, boxstyle="round,pad=0.004,rounding_size=0.015",
                                    facecolor=color, edgecolor="#333333", linewidth=0.8))
        ax.text(x + width / 2, y0 + h - 0.1, title, ha="center", va="center", fontsize=7.2, fontweight="bold",
                linespacing=1.05)
        ax.text(x + width / 2, y0 + 0.14, body, ha="center", va="center", fontsize=6.5, linespacing=1.12)
        if i < len(stages) - 1:
            ax.add_patch(FancyArrowPatch((x + width + 0.003, y0 + h / 2), (x + width + gap - 0.003, y0 + h / 2),
                                         arrowstyle="-|>", mutation_scale=8, color="#333333", linewidth=0.8))
    ax.text(0.5, 0.95, "Each stage frozen before its outcomes were computed; no later stage revises the DS03 verdict",
            ha="center", va="center", fontsize=6.9, style="italic")
    families = [("F1", "DS01", "4"), ("F2", "DS04", "4"), ("F3", "DS05 · DS06 · DS07\n(one fleet, same missions)", "3 × 4"),
                ("F4", "DS08a", "6"), ("F5", "DS08c", "4")]
    fw, fg, fl = 0.172, 0.019, 0.03
    for i, (fam, subsets, engines) in enumerate(families):
        x = fl + i * (fw + fg)
        ax.add_patch(FancyBboxPatch((x, 0.03), fw, 0.27, boxstyle="round,pad=0.004,rounding_size=0.012",
                                    facecolor="#f4fbf2", edgecolor="#4f7f47", linewidth=0.7))
        ax.text(x + fw / 2, 0.205, f"{fam}: {subsets}", ha="center", va="center", fontsize=6.3, linespacing=1.1)
        ax.text(x + fw / 2, 0.075, f"audit engines {engines}", ha="center", va="center", fontsize=6.1, color="#333333")
    ax.text(0.5, 0.355, "Fleet families (top-level unit of cross-dataset counts); DS08d excluded (unreadable HDF5)",
            ha="center", va="center", fontsize=6.7)
    save(rec, fig, "fig1_study_design", "Schematic; counts from docs/extension/SUBSET_SELECTION_LOCK.md.")


def fig2_pooled_phase_fpr(rec):
    fig, axes = plt.subplots(1, 4, figsize=(WIDTH, 2.7), sharey=True)
    for ax, det in zip(axes, DETECTORS):
        shade_reference(ax)
        for i, key in enumerate(ALL):
            ts = rec.audit(key, "transport_summary")
            part = ts[(ts.nominal_fpr == ALPHA) & (ts.arm == "pooled") & (ts.detector == det)]
            for j, phase in enumerate(PHASES):
                values = 100 * part[f"pooled_{phase}_fpr"].to_numpy()
                x = i + (j - 1) * 0.24
                ax.vlines(x, values.min(), min(values.max(), 4.3), color=PHASE_COLOR[phase], lw=0.8)
                ax.plot(x, values.mean(), "o", ms=2.6, color=PHASE_COLOR[phase],
                        label=phase if (i == 0 and det == "pca") else None)
                if values.max() > 4.3:
                    ax.annotate(f"↑{values.max():.1f}", (x, 4.3), xytext=(0, 1), textcoords="offset points",
                                ha="center", va="bottom", fontsize=5.6, color=PHASE_COLOR[phase])
        ax.axhline(100 * ALPHA, color="black", lw=0.7, ls="--")
        ax.set_title(DET_LABEL[det])
        ax.set_xticks(range(len(ALL)), ALL, rotation=90)
        ax.set_ylim(0, 4.3)
    axes[0].set_ylabel("Pooled healthy FPR under P (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    save(rec, fig, "fig2_pooled_phase_fpr", "Seed mean (point) and seed range (bar); α = 1%; shaded: DS02/DS03 reference.")


def fig3_engine_transport(rec):
    lk = locks(rec)
    noise = rec.read(ROOT / "paper/mssp_extended/evidence/post_hoc_engine_noise.csv")
    noise_q95 = noise[noise.arm == "pooled"].groupby(["subset", "unit"]).null_A2_q95.median()
    fig, ax = plt.subplots(figsize=(WIDTH, 2.9))
    x, ticks = 0, []
    for key in ALL:
        pe = rec.audit(key, "paired_transport_engines")
        pe = pe[(pe.nominal_fpr == ALPHA) & (pe.detector != "cvae")]
        classes = lk[key]["roles"]["classes"]
        cal_classes = {classes[str(u)] for u in lk[key]["roles"]["calibration"]}
        start = x
        for unit in sorted(pe.unit.unique()):
            covered = classes[str(unit)] in cal_classes
            if (key, unit) in noise_q95.index:  # post hoc approximate sampling reference (NEW subsets only)
                ax.hlines(100 * noise_q95[(key, unit)], x - 0.42, x + 0.42, color="0.6", lw=2.4, alpha=0.55, zorder=1)
            p_values = 100 * pe[(pe.unit == unit) & (pe.arm == "phase_conditioned")].pooled_arm_A2
            series = {"pooled": p_values,
                      "phase_conditioned": 100 * pe[(pe.unit == unit) & (pe.arm == "phase_conditioned")].arm_A2,
                      "quantile_regression_W": 100 * pe[(pe.unit == unit) & (pe.arm == "quantile_regression_W")].arm_A2}
            for k, arm in enumerate(ARMS):
                v = series[arm]
                xx = x + (k - 1) * 0.24
                ax.vlines(xx, v.min(), v.max(), color=ARM_COLOR[arm], lw=0.8)
                ax.plot(xx, v.median(), "o" if covered else "x", ms=3.2 if covered else 4.0, color=ARM_COLOR[arm],
                        mew=1.0)
            x += 1
        ticks.append(((start + x - 1) / 2, key))
        if key in REF:
            ax.axvspan(start - 0.5, x - 0.5, color="0.93", zorder=0)
        ax.axvline(x - 0.5 + 0.5, color="0.8", lw=0.5)
        x += 1
    ax.axhline(50 * ALPHA, color="black", lw=0.7, ls=":")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xticks([t for t, _ in ticks], [k for _, k in ticks])
    ax.set_xlim(-0.8, x - 0.7)
    ax.set_ylabel("Per-engine max |FPR − α| (pp)")
    handles = [plt.Line2D([], [], color=ARM_COLOR[a], marker="o", ls="", label=f"arm {ARM_LABEL[a]}") for a in ARMS]
    handles += [plt.Line2D([], [], color="0.3", marker="x", ls="", label="class absent from calibration"),
                plt.Line2D([], [], color="black", ls=":", label="material line (0.5 pp)"),
                plt.Line2D([], [], color="0.6", lw=2.4, alpha=0.55, label="sampling reference (post hoc)")]
    ax.legend(handles=handles, ncol=6, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.13), fontsize=6.3)
    fig.tight_layout()
    save(rec, fig, "fig3_engine_transport", "Median (marker) and range (bar) over the 7 residual runs; α = 1%. Grey tick: "
         "post hoc 95th percentile of the A2 of a perfectly calibrated engine (median over runs, arm P).")


def fig4_composition(rec):
    engines = rec.read(SUM / "composition_engine_effects.csv")
    runs = rec.read(SUM / "composition_run_summary.csv")
    keys = [k for k in NEW if k in set(engines.subset)]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.6))
    for k_arm, arm in enumerate(("pooled", "phase_conditioned")):
        med = engines[engines.arm == arm].groupby(["subset", "unit"]).delta_cov.median().reset_index()
        for i, key in enumerate(keys):
            v = 100 * med[med.subset == key].delta_cov
            axes[0].plot(np.full(len(v), i + (k_arm - 0.5) * 0.3), v, "o", ms=3, color=ARM_COLOR[arm], alpha=0.85,
                         label=f"arm {ARM_LABEL[arm]}" if i == 0 else None)
        r = runs[runs.arm == arm]
        for i, key in enumerate(keys):
            v = 100 * r[r.subset == key].CE2_balanced_minus_mean_single
            axes[1].plot(np.full(len(v), i + (k_arm - 0.5) * 0.3), v, "o", ms=2.5, color=ARM_COLOR[arm], alpha=0.85)
    axes[0].set_title("(a) Coverage effect per audit engine\n(other-class minus same-class calibration, pp)")
    axes[1].set_title("(b) Class-balanced minus mean single-engine\nmean per-engine error, per run (pp)")
    for ax in axes:
        ax.axhline(0, color="black", lw=0.6)
        ax.set_xticks(range(len(keys)), [f"{k}\n{FAMILY[k]}" for k in keys])
    axes[0].legend(frameon=False, loc="upper left")
    fig.tight_layout()
    save(rec, fig, "fig4_composition", "Fixed calibration volume N; draw means; α = 1%. Positive in (a) = coverage helps.")


def fig5_cvae(rec):
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.6), sharex=True)
    for ax, metric, title in ((axes[0], "ME_A2", "(a) Mean per-engine max |FPR − α| under P"),
                              (axes[1], "WE_A2", "(b) Worst-engine max |FPR − α| under P")):
        shade_reference(ax)
        for i, key in enumerate(ALL):
            ts = rec.audit(key, "transport_summary")
            part = ts[(ts.nominal_fpr == ALPHA) & (ts.arm == "pooled")]
            for j, det in enumerate(DETECTORS):
                v = 100 * part[part.detector == det][metric]
                ax.plot(np.full(len(v), i + (j - 1.5) * 0.17), v, DET_MARKER[det], ms=3, mfc="none",
                        color=DET_COLOR[det], label=DET_LABEL[det] if i == 0 else None)
        ax.axhline(50 * ALPHA, color="black", lw=0.6, ls=":")
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_title(title)
        ax.set_xticks(range(len(ALL)), ALL, rotation=90)
    axes[0].set_ylabel("pp")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.03))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(rec, fig, "fig5_cvae_vs_residual", "Individual runs (PCA one run; three seeds otherwise); α = 1%.")


def fig6_persistence_delay(rec):
    frames = []
    for key in ALL:
        ff = rec.audit(key, "flight_false_flags")
        ff = ff[(ff.nominal_fpr == ALPHA) & (ff.unit.astype(str) != "all")]
        frames.append(ff.groupby(["subset", "detector", "seed", "arm", "rule"]).false_flag_rate.max()
                      .rename("WE_FFR").reset_index())
    we = pd.concat(frames, ignore_index=True)
    labels = rec.read(SUM / "matched_labels_alpha_0.01.csv")
    null = {r["subset"]: r for r in rec.json(ROOT / "paper/mssp_extended/evidence/post_hoc_checks.json")["we_ffr_null"]}
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.6), gridspec_kw={"width_ratios": [1.55, 1]})
    part = we[(we.arm == "pooled") & (we.detector != "cvae")]
    ax = axes[0]
    shade_reference(ax)
    for i, key in enumerate(ALL):
        if key in null:  # post hoc: worst engine of a perfectly calibrated fleet (median to 95th percentile)
            ax.fill_between([i - 0.42, i + 0.42], 100 * null[key]["null_median"], 100 * null[key]["null_q95"],
                            color="0.6", alpha=0.35, lw=0, zorder=0, label="perfect-calibration reference (post hoc)" if key == NEW[0] else None)
        for j, rule in enumerate(("R0", "R1", "R2")):
            v = 100 * part[(part.subset == key) & (part.rule == rule)].WE_FFR
            xx = i + (j - 1) * 0.24
            ax.vlines(xx, v.min(), v.max(), color=RULE_COLOR[rule], lw=0.8)
            ax.plot(xx, v.median(), "o", ms=2.8, color=RULE_COLOR[rule], label=rule if i == 0 else None)
    ax.axhline(5, color="black", lw=0.6, ls="--")
    ax.axhline(10, color="black", lw=0.6, ls=":")
    ax.set_xticks(range(len(ALL)), ALL, rotation=90)
    ax.set_ylabel("Worst-engine healthy-flight\nfalse-flag rate under P (%)")
    ax.set_title("(a) Persistence rules at locked κ")
    ax.set_ylim(-3, 82)
    ax.legend(frameon=False, ncol=2, loc="upper left", fontsize=6.0)
    ax = axes[1]
    cats = ["earlier at matched burden", "equal", "mixed", "later at matched burden"]
    colors = ["#1f77b4", "#c7c7c7", "#ffbb78", "#d62728"]
    residual = labels[(labels.detector != "cvae") & labels.subset.isin(NEW)]
    groups = [(arm, rule) for arm in ("phase_conditioned", "quantile_regression_W") for rule in ("R0", "R1", "R2")]
    bottom = np.zeros(len(groups))
    for cat, color in zip(cats, colors):
        counts = np.array([((residual.arm == a) & (residual.rule == r) & (residual.matched_label == cat)).sum()
                           for a, r in groups])
        ax.bar(range(len(groups)), counts, bottom=bottom, color=color, edgecolor="0.3", lw=0.3, label=cat)
        bottom += counts
    ax.set_xticks(range(len(groups)), [f"{ARM_LABEL[a]}\n{r}" for a, r in groups])
    ax.set_ylabel("residual runs (of 49)")
    ax.set_title("(b) Delay versus P at matched burden")
    ax.legend(frameon=False, fontsize=6.0, loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=2)
    fig.tight_layout()
    save(rec, fig, "fig6_persistence_and_delay", "Median (marker) and range (bar) over 7 residual runs; α = 1%. Grey band: "
         "post hoc median-to-95th-percentile worst-engine rate of a perfectly calibrated fleet.")


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def tex_escape(value):
    text = str(value)
    for a, b in (("\\", r"\textbackslash{}"), ("_", r"\_"), ("%", r"\%"), ("&", r"\&"), ("#", r"\#")):
        text = text.replace(a, b)
    return text.replace("−", "$-$").replace("–", "--").replace("κ", r"$\kappa$").replace("≥", r"$\geq$").replace(
        "×", r"$\times$").replace("α", r"$\alpha$")


def tex_header(name):
    parts = str(name).split("\n")
    return tex_escape(parts[0]) if len(parts) == 1 else "\\makecell{" + "\\\\".join(tex_escape(p) for p in parts) + "}"


def write_table(rec, frame, name, caption, note, align=None, rule_after=()):
    csv = rec.target(TAB / f"{name}.csv")
    flat = frame.rename(columns=lambda c: str(c).replace("\n", " "))
    flat = flat.apply(lambda col: col.map(lambda v: v.replace("\n", " ") if isinstance(v, str) else v))
    flat.to_csv(csv, index=False)
    tex = rec.target(TAB / f"{name}.tex")
    columns = align or ("l" * len(frame.columns))
    lines = [f"% {caption}", "\\begin{tabular}{" + columns + "}", "\\toprule",
             " & ".join(tex_header(c) for c in frame.columns) + " \\\\", "\\midrule"]
    for i, row in enumerate(frame.itertuples(index=False)):
        lines.append(" & ".join(tex_header(v) for v in row) + " \\\\")
        if i in rule_after:
            lines.append("\\midrule")
    lines += ["\\bottomrule", "\\end{tabular}"]
    tex.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rec.sidecar([csv, tex], note)


def pp(value, digits=2):
    return f"{100 * value:.{digits}f}"


def table1_design(rec):
    lk = locks(rec)
    rows = []
    for key in ALL:
        roles = lk[key]["roles"]
        cls = roles["classes"]
        fmt = lambda units: ", ".join(f"{u} ({cls[str(u)]})" for u in units)  # noqa: E731
        record = rec.json(EXT / key / "audit" / "audit_record.json")
        comp = lk[key].get("composition")
        rows.append({"Subset": key, "Family": FAMILY[key], "Fit engines\n(class)": fmt(roles["fit"]),
                     "Calibration\nengines (class)": fmt(roles["calibration"]),
                     "Audit engines (class)": fmt(roles["audit"]),
                     "Healthy / post-onset\naudit rows": f"{record['healthy_rows']:,} / {record['post_onset_rows']:,}",
                     "Composition\nvolume N": (f"{comp['volume_N']:,}" if comp and comp.get("eligible") else "–")})
    frame = pd.DataFrame(rows)
    write_table(rec, frame, "table1_subsets_roles", "Subsets, fleet families and engine roles", "From committed locks and audit records.",
                align=">{\\raggedright\\arraybackslash}p{0.07\\textwidth}l>{\\raggedright\\arraybackslash}p{0.14\\textwidth}"
                      ">{\\raggedright\\arraybackslash}p{0.17\\textwidth}>{\\raggedright\\arraybackslash}p{0.2\\textwidth}"
                      "rr", rule_after=(1,))


def table2_pooled(rec):
    order = rec.read(SUM / "phase_ordering_pooled.csv")
    rows = []
    for key in ALL:
        ts = rec.audit(key, "transport_summary")
        p = ts[(ts.nominal_fpr == ALPHA) & (ts.arm == "pooled")]
        highest = p[[f"pooled_{ph}_fpr" for ph in PHASES]].idxmax(axis=1).str.split("_").str[1]
        o = order[order.subset == key]
        if len(o):  # new subsets: must agree with the committed phase-ordering summary
            assert sorted(highest) == sorted(o.highest_phase), key
        row = {"Subset": key, "Family": FAMILY[key],
               "Highest phase under P\n(runs of 10)": ", ".join(f"{ph} {int((highest == ph).sum())}" for ph in PHASES
                                                                if int((highest == ph).sum()))}
        for det in DETECTORS:
            row[f"{DET_LABEL[det].replace('Residual ', '').replace('Past-only ', '').replace('Isolation Forest', 'IF')}\npooled A2 (pp)"] = \
                pp(p[p.detector == det].pooled_A2.mean())
        material = all(p[p.detector == d].pooled_A2.mean() >= 0.5 * ALPHA for d in DETECTORS[:3])
        row["Material\n(H1 rule)"] = "yes" if material else "no"
        rows.append(row)
    write_table(rec, pd.DataFrame(rows), "table2_pooled_calibration", "Pooled calibration across subsets",
                "Pooled A2 = max over phases of |FPR − α| pooled over audit engines; seed means for IF, LSTM and CVAE; α = 1%.",
                align="ll>{\\raggedright\\arraybackslash}p{0.2\\textwidth}rrrrl", rule_after=(1,))


def table3_transport(rec):
    rows = []
    for key in ALL:
        pt = rec.audit(key, "paired_transport")
        pt = pt[pt.nominal_fpr == ALPHA]
        ts = rec.audit(key, "transport_summary")
        ts = ts[(ts.nominal_fpr == ALPHA) & (ts.detector != "cvae")]
        c, q = pt[pt.arm == "phase_conditioned"], pt[pt.arm == "quantile_regression_W"]
        med = lambda arm, m: pp(ts[ts.arm == arm][m].median())  # noqa: E731
        rows.append({"Subset": key, "C: pooled A1\nreduced": f"{int((c.diff_pooled_A1 < 0).sum())}/10",
                     "C: all engines\nimproved": f"{int(c.uniform_improvement.sum())}/10",
                     "C: ≥1 engine\nworse": f"{int((c.n_worse >= 1).sum())}/10",
                     "Q: all engines\nimproved": f"{int(q.uniform_improvement.sum())}/10",
                     "Q: ≥1 engine\nworse": f"{int((q.n_worse >= 1).sum())}/10",
                     "ME-A2 (pp)\nP / C / Q": f"{med('pooled', 'ME_A2')} / {med('phase_conditioned', 'ME_A2')} / "
                                             f"{med('quantile_regression_W', 'ME_A2')}",
                     "WE-A2 (pp)\nP / C / Q": f"{med('pooled', 'WE_A2')} / {med('phase_conditioned', 'WE_A2')} / "
                                             f"{med('quantile_regression_W', 'WE_A2')}"})
    write_table(rec, pd.DataFrame(rows), "table3_transport",
                "Transport of context-conditioned calibration",
                "Counts over 10 detector runs (7 residual + 3 CVAE); ME-A2/WE-A2 = median over the 7 residual runs; α = 1%.",
                align="lrrrrrcc", rule_after=(1,))


def table4_decisions(rec):
    dec = rec.json(SUM / "decisions.json")
    h1, h2, h3, h4, h5, h6 = (dec[h] for h in ("H1", "H2", "H3", "H4", "H5", "H6"))
    boot = rec.read(SUM / "composition_bootstrap.csv").set_index("arm")
    eff = lambda arm: (f"{100 * boot.loc[arm, 'point']:.2f} pp ({100 * boot.loc[arm, 'ci_lower_95']:.2f} to "  # noqa: E731
                       f"{100 * boot.loc[arm, 'ci_upper_95']:.2f})").replace("-", "−")
    rows = [
        ("H1 conditional miscalibration under P", "material pooled error (≥ 0.5α) for PCA, IF and LSTM in a subset; ≥ 3/5 families",
         f"{h1['families_holding']}/5 families", h1["verdict"]),
        ("H2 C reduces pooled disparity", "≥ 80% of 70 cells and ≥ 4/5 families", f"{100 * h2['share_cells_disparity_reduced']:.0f}% of cells; "
         f"{h2['families_holding']}/5 families", h2["verdict"]),
        ("H3 no uniform per-engine improvement", "share of cells with every engine improved < 0.5 (C and Q)",
         f"C {100 * h3['C']['U']:.0f}%; Q {100 * h3['Q']['U']:.0f}%", h3["verdict"]),
        ("H4 calibration-class coverage", "coverage effect > 0 in ≥ 7/10 runs (P and C) and balance check, ≥ 3/4 families",
         f"coverage {h4['families_supporting_coverage']}/4; balance {h4['families_passing_balance']}/4; "
         f"median effect P {eff('pooled')}, C {eff('phase_conditioned')}",
         h4["verdict"] + " (beyond volume; weak under P)"),
        ("H5 CVAE does not guarantee transport", "worst-engine error ≥ 0.5α in most CVAE runs, ≥ 3/5 families",
         f"{h5['families_WE_material_majority']}/5 families; substantial improvement {h5['families_substantially_improves_b']}/5",
         h5["verdict"]),
        ("H6 failures persist under persistence", "worst-engine false-flag rate ≥ 10% in most residual cells, ≥ 3/5 families, R1 and R2",
         f"R0 {h6['families_with_flight_level_problem']['R0']}/5; R1 {h6['families_with_flight_level_problem']['R1']}/5; "
         f"R2 {h6['families_with_flight_level_problem']['R2']}/5", h6["verdict"]),
        ("H7 delay at matched burden", "C 'earlier' in ≥ 5/7 residual runs with lower curve mean", "met in 0/7 subsets (any rule)",
         "no delay advantage"),
        ("Original story", "components S1–S5 by family (Amendment 1)",
         ", ".join(f"{k} {v}/5" for k, v in dec["original_story"]["family_counts"].items()), dec["original_story"]["class"]),
        ("Interpretation matrix", "Stories M-A to M-E", "triggered " + ", ".join(dec["matrix_stories"]["triggered"]),
         dec["matrix_stories"]["headline"]),
    ]
    frame = pd.DataFrame(rows, columns=["Hypothesis", "Pre-specified rule (abridged)", "Observed", "Decision"])
    write_table(rec, frame, "table4_decisions", "Pre-specified decisions on the new cohort",
                "From results/extension/summary/decisions.json; α = 1%; families F1–F5.",
                align=">{\\raggedright\\arraybackslash}p{0.2\\textwidth}>{\\raggedright\\arraybackslash}p{0.3\\textwidth}"
                      ">{\\raggedright\\arraybackslash}p{0.27\\textwidth}>{\\raggedright\\arraybackslash}p{0.15\\textwidth}")


def signed_pp(value):
    """Signed percentage points to 2 decimals; values that round to zero print as 0.00 (no signed zero)."""
    text = f"{100 * value:+.2f}"
    return "0.00" if float(text) == 0 else text.replace("-", "−")


def table5_composition(rec):
    lk = locks(rec)
    runs = rec.read(SUM / "composition_run_summary.csv")
    engines = rec.read(SUM / "composition_engine_effects.csv")
    rows = []
    for key in NEW:
        comp = lk[key].get("composition")
        if not comp or not comp.get("eligible"):
            continue
        cls = sorted(set(comp["pool_classes"].values()))
        for arm in ("pooled", "phase_conditioned"):
            r = runs[(runs.subset == key) & (runs.arm == arm)]
            e = engines[(engines.subset == key) & (engines.arm == arm)].groupby("unit").delta_cov.median()
            v = engines[(engines.subset == key) & (engines.arm == arm)].groupby("unit").delta_vol_uncovered.median()
            first = arm == "pooled"
            rows.append({"Subset": key if first else "", "Family": FAMILY[key] if first else "",
                         "N (rows)": f"{comp['volume_N']:,}" if first else "",
                         "Pool\nclasses": ", ".join(map(str, cls)) if first else "", "Arm": ARM_LABEL[arm],
                         "Coverage effect\n> 0 (runs)": f"{int(r.supports_coverage.sum())}/10",
                         "Median coverage\neffect (pp)": signed_pp(e.median()),
                         "Median volume\neffect (pp)": signed_pp(v.median()),
                         "Balanced better\n(runs)": f"{int(r.balance_check.sum())}/10"})
    write_table(rec, pd.DataFrame(rows), "table5_composition", "Calibration-fleet composition at fixed volume",
                "Coverage = other-class minus same-class single-engine A2 per audit engine (positive = coverage helps); "
                "volume = gain from full versus N rows of an other-class engine; α = 1%.",
                align="llrllrrrr", rule_after=(1, 3, 5, 7, 9))


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

def evidence(rec):
    EVI.mkdir(parents=True, exist_ok=True)
    for path in sorted(SUM.glob("*.csv")) + [SUM / "decisions.json", ROOT / "docs/extension/EXTENSION_EVIDENCE_LEDGER.csv"]:
        target = rec.target(EVI / path.name)
        target.write_bytes(path.read_bytes())
    # Per-design composition metrics (27 MB) stay in results/extension/<subset>/audit/composition_metrics.csv only;
    # the composition summaries used by the article are copied above.
    for table in ("transport_summary", "paired_transport_engines", "flight_false_flags", "matched_labels",
                  "bootstrap_uext1_ci"):
        parts = [rec.audit(k, table).assign(source=f"results/extension/{k}/audit/{table}.csv") for k in ALL
                 if (EXT / k / "audit" / f"{table}.csv").exists()]
        target = rec.target(EVI / f"extension_{table}.csv")
        pd.concat(parts, ignore_index=True).to_csv(target, index=False)
    lines = [f"{sha256(p)}  {p.name}" for p in sorted(EVI.glob("*")) if p.is_file() and p.name != "SHA256SUMS"]
    (EVI / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


BUILDERS = {"fig1": fig1_design, "fig2": fig2_pooled_phase_fpr, "fig3": fig3_engine_transport, "fig4": fig4_composition,
            "fig5": fig5_cvae, "fig6": fig6_persistence_delay, "table1": table1_design, "table2": table2_pooled,
            "table3": table3_transport, "table4": table4_decisions, "table5": table5_composition, "evidence": evidence}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    rec = Recorder(args.rebuild)
    for key in [s for s in args.only.split(",") if s] or list(BUILDERS):
        BUILDERS[key](rec)
        print(f"built: {key}")


if __name__ == "__main__":
    main()
