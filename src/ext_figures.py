"""Extension figures from committed per-subset audit tables and summary tables (no data are read).

Every plotted value is a committed value or a median/range of committed values over detector runs. Each
figure gets a provenance sidecar listing the SHA-256 of its inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import ext_common as ec  # noqa: E402

FAMILY_LABEL = {"pca": "Residual PCA", "isolation_forest": "Isolation Forest", "lstm_autoencoder": "Past-only LSTM",
                "cvae": "CVAE"}
FAMILY_MARKER = {"pca": "o", "isolation_forest": "s", "lstm_autoencoder": "^", "cvae": "D"}
ARM_LABEL = {"pooled": "P", "phase_conditioned": "C", "quantile_regression_W": "Q"}
ARM_COLOR = {"pooled": "#4d4d4d", "phase_conditioned": "#1f77b4", "quantile_regression_W": "#2ca02c"}
PHASE_COLOR = {"climb": "#2ca02c", "cruise": "#1f77b4", "descent": "#d62728"}
RULE_COLOR = {"R0": "#4d4d4d", "R1": "#9467bd", "R2": "#8c564b"}
ALPHA = ec.PRIMARY_TARGET
WIDTH = 6.3

plt.rcParams.update({"font.size": 8.5, "axes.titlesize": 8.5, "axes.labelsize": 8.5, "legend.fontsize": 7.2,
                     "xtick.labelsize": 7.2, "ytick.labelsize": 7.2, "figure.dpi": 150, "savefig.dpi": 600,
                     "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                     "font.family": "DejaVu Sans"})


class Inputs:
    def __init__(self):
        self.paths = set()

    def read(self, key, table):
        path = ec.RESULTS / key / "audit" / f"{table}.csv"
        self.paths.add(path)
        return pd.read_csv(path)

    def summary(self, table):
        path = ec.RESULTS / "summary" / f"{table}.csv"
        self.paths.add(path)
        return pd.read_csv(path)

    def lock(self, key):
        path = ec.RESULTS / key / "lock" / "calibration_lock.json"
        self.paths.add(path)
        return json.loads(path.read_text(encoding="utf-8"))


def order_keys(include_reference=True):
    keys = list(ec.REFERENCE_ORDER) if include_reference else []
    return keys + list(ec.NEW_ORDER)


def label(key):
    return f"{key}\n({ec.FAMILIES[key]})"


def save(fig, out_dir, name, inputs):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    sidecar = {"figure": name, "inputs": {str(Path(p).resolve().relative_to(ec.ROOT)) if str(p).startswith(str(ec.ROOT))
                                          else str(p): ec.file_digest(p) for p in sorted(inputs.paths)}}
    (out_dir / f"{name}.provenance.json").write_text(json.dumps(sidecar, indent=1), encoding="utf-8")


def family_value(frame, value):
    """PCA value and seed means of IF, LSTM and CVAE."""
    return frame.groupby("detector")[value].mean()


def fig_phase_fpr(out_dir, inputs):
    keys = order_keys()
    fig, axes = plt.subplots(1, 4, figsize=(WIDTH, 2.6), sharey=True)
    for ax, detector in zip(axes, FAMILY_LABEL):
        for i, key in enumerate(keys):
            ts = inputs.read(key, "transport_summary")
            part = ts[(ts.nominal_fpr == ALPHA) & (ts.arm == "pooled") & (ts.detector == detector)]
            for j, phase in enumerate(("climb", "cruise", "descent")):
                values = 100 * part[f"pooled_{phase}_fpr"]
                ax.plot([i + (j - 1) * 0.18] * len(values), values, ".", color=PHASE_COLOR[phase], ms=3, alpha=0.8,
                        label=phase if (i == 0 and detector == "pca") else None)
        ax.axhline(100 * ALPHA, color="k", lw=0.7, ls="--")
        ax.axvspan(-0.5, len(ec.REFERENCE_ORDER) - 0.5, color="0.93", zorder=0)
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels(keys, rotation=90)
        ax.set_title(FAMILY_LABEL[detector])
        ax.set_yscale("log")
    axes[0].set_ylabel("Pooled healthy FPR under P (%)")
    axes[0].legend(loc="upper left", frameon=False)
    fig.tight_layout()
    save(fig, out_dir, "ext_fig1_phase_fpr_by_subset", inputs)


def fig_engine_transport(out_dir, inputs):
    keys = order_keys()
    fig, ax = plt.subplots(figsize=(WIDTH, 2.8))
    x = 0
    ticks, labels = [], []
    for key in keys:
        q = inputs.read(key, "calibration_quality")
        lock = inputs.lock(key)
        cal_classes = {lock["roles"]["classes"][str(u)] for u in lock["roles"]["calibration"]}
        part = q[(q.nominal_fpr == ALPHA) & (q.weighting == "per_engine") & (q.detector != "cvae")]
        engines = sorted(part.unit.astype(int).unique())
        for e in engines:
            covered = lock["roles"]["classes"][str(e)] in cal_classes
            for k, arm in enumerate(("pooled", "phase_conditioned", "quantile_regression_W")):
                values = 100 * part[(part.unit.astype(int) == e) & (part.arm == arm)].max_abs_error
                ax.vlines(x + (k - 1) * 0.22, values.min(), values.max(), color=ARM_COLOR[arm], lw=0.9)
                ax.plot(x + (k - 1) * 0.22, values.median(), "o" if covered else "x", color=ARM_COLOR[arm], ms=3.2)
            x += 1
        ticks.append(x - (len(engines) + 1) / 2)
        labels.append(key)
        ax.axvline(x, color="0.85", lw=0.6)
        x += 1
    ax.axhline(100 * 0.5 * ALPHA, color="k", lw=0.6, ls=":")
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    ax.set_yscale("log")
    ax.set_ylabel("Per-engine max |FPR − α| (pp)")
    handles = [plt.Line2D([], [], color=ARM_COLOR[a], marker="o", ls="", label=ARM_LABEL[a]) for a in ARM_COLOR]
    handles += [plt.Line2D([], [], color="0.3", marker="x", ls="", label="class absent from calibration")]
    ax.legend(handles=handles, ncol=4, frameon=False, loc="upper left")
    fig.tight_layout()
    save(fig, out_dir, "ext_fig2_engine_transport", inputs)


def fig_cvae(out_dir, inputs):
    keys = order_keys()
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.5), sharex=True)
    for ax, metric, title in ((axes[0], "ME_A2", "Mean per-engine max |FPR − α| (P)"),
                              (axes[1], "WE_A2", "Worst-engine max |FPR − α| (P)")):
        for i, key in enumerate(keys):
            ts = inputs.read(key, "transport_summary")
            part = ts[(ts.nominal_fpr == ALPHA) & (ts.arm == "pooled")]
            for j, detector in enumerate(FAMILY_LABEL):
                values = 100 * part[part.detector == detector][metric]
                ax.plot([i + (j - 1.5) * 0.15] * len(values), values, FAMILY_MARKER[detector], ms=3, mfc="none",
                        color="C" + str(j), label=FAMILY_LABEL[detector] if i == 0 else None)
        ax.axhline(100 * 0.5 * ALPHA, color="k", lw=0.6, ls=":")
        ax.set_yscale("log")
        ax.set_title(title)
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels(keys, rotation=90)
    axes[0].set_ylabel("pp")
    axes[0].legend(frameon=False, fontsize=6.5)
    fig.tight_layout()
    save(fig, out_dir, "ext_fig3_cvae_vs_residual", inputs)


def fig_composition(out_dir, inputs):
    engines = inputs.summary("composition_engine_effects")
    runs = inputs.summary("composition_run_summary")
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.6))
    keys = [k for k in ec.NEW_ORDER if k in set(engines.subset)]
    for k_arm, arm in enumerate(("pooled", "phase_conditioned")):
        part = engines[engines.arm == arm].groupby(["subset", "unit"]).delta_cov.median().reset_index()
        for i, key in enumerate(keys):
            values = 100 * part[part.subset == key].delta_cov
            axes[0].plot([i + (k_arm - 0.5) * 0.25] * len(values), values, "o", ms=3, color=ARM_COLOR[arm],
                         label=ARM_LABEL[arm] if i == 0 else None)
        rs = runs[runs.arm == arm]
        for i, key in enumerate(keys):
            values = 100 * rs[rs.subset == key].CE2_balanced_minus_mean_single
            axes[1].plot([i + (k_arm - 0.5) * 0.25] * len(values), values, "o", ms=2.5, color=ARM_COLOR[arm])
    for ax, title in ((axes[0], "Coverage effect per audit engine\n(uncovered − covered single-engine A2, pp)"),
                      (axes[1], "Class-balanced minus mean single-engine\nME-A2 per run (pp)")):
        ax.axhline(0, color="k", lw=0.6)
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels(keys, rotation=90)
        ax.set_title(title)
    axes[0].legend(frameon=False)
    fig.tight_layout()
    save(fig, out_dir, "ext_fig4_composition", inputs)


def fig_persistence(out_dir, inputs):
    we = inputs.summary("we_ffr")
    keys = [k for k in order_keys() if k in set(we.subset)]
    fig, ax = plt.subplots(figsize=(WIDTH, 2.4))
    part = we[(we.arm == "pooled") & (we.detector != "cvae")]
    for i, key in enumerate(keys):
        for j, rule in enumerate(("R0", "R1", "R2")):
            values = 100 * part[(part.subset == key) & (part.rule == rule)].WE_FFR
            ax.vlines(i + (j - 1) * 0.22, values.min(), values.max(), color=RULE_COLOR[rule], lw=0.9)
            ax.plot(i + (j - 1) * 0.22, values.median(), "o", ms=3, color=RULE_COLOR[rule],
                    label=rule if i == 0 else None)
    ax.axhline(10, color="k", lw=0.6, ls=":")
    ax.axhline(5, color="k", lw=0.6, ls="--")
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(keys)
    ax.set_ylabel("Worst-engine healthy-flight\nfalse-flag rate, P (%)")
    ax.legend(frameon=False, ncol=3)
    fig.tight_layout()
    save(fig, out_dir, "ext_fig5_persistence", inputs)


def fig_matched(out_dir, inputs):
    labels = inputs.summary("matched_labels_alpha_0.01")
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.4), sharey=True)
    categories = ["earlier at matched burden", "equal", "mixed", "later at matched burden", "not evaluable"]
    colors = ["#1f77b4", "#bbbbbb", "#ffbb78", "#d62728", "white"]
    for ax, arm in zip(axes, ("phase_conditioned", "quantile_regression_W")):
        part = labels[labels.arm == arm]
        bottom = np.zeros(3)
        for cat, color in zip(categories, colors):
            counts = np.array([(part[part.rule == r].matched_label == cat).sum() for r in ("R0", "R1", "R2")])
            ax.bar(range(3), counts, bottom=bottom, color=color, edgecolor="0.4", lw=0.4, label=cat)
            bottom += counts
        ax.set_xticks(range(3))
        ax.set_xticklabels(["R0", "R1", "R2"])
        ax.set_title(f"{ARM_LABEL[arm]} vs P (all new-subset runs, α = 1%)")
    axes[0].set_ylabel("detector runs")
    axes[1].legend(frameon=False, fontsize=6.3, loc="upper right")
    fig.tight_layout()
    save(fig, out_dir, "ext_fig6_matched_delay_labels", inputs)


def main(out_dir=None):
    out_dir = out_dir or (ec.RESULTS / "figures")
    for builder in (fig_phase_fpr, fig_engine_transport, fig_cvae, fig_composition, fig_persistence, fig_matched):
        builder(out_dir, Inputs())
    return out_dir


if __name__ == "__main__":
    print(main())
