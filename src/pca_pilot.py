"""Healthy-only, unit-disjoint DS02 PCA phase-calibration falsification pilot."""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "N-CMAPSS/N-CMAPSS_DS02-006.h5"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
TRAIN_UNITS = (2, 5, 10, 16)
VAL_UNITS = (18, 20)
TEST_UNITS = (11, 14, 15)
PHASES = ("climb", "cruise", "descent")
ALT_FRACTION = 0.90
N_COMPONENTS = 5
NAMES = {
    "A_var": ["unit", "cycle", "Fc", "hs"],
    "W_var": ["alt", "Mach", "TRA", "T2"],
    "X_s_var": ["T24", "T30", "T48", "T50", "P15", "P2", "P21", "P24", "Ps30", "P40", "P50", "Nf", "Nc", "Wf"],
    "X_v_var": ["T40", "P30", "P45", "W21", "W22", "W25", "W31", "W32", "W48", "W50", "SmFan", "SmLPC", "SmHPC", "phi"],
    "T_var": ["fan_eff_mod", "fan_flow_mod", "LPC_eff_mod", "LPC_flow_mod", "HPC_eff_mod", "HPC_flow_mod", "HPT_eff_mod", "HPT_flow_mod", "LPT_eff_mod", "LPT_flow_mod"],
}


def inspect_and_metadata(h5: h5py.File, split: str):
    for key, names in NAMES.items():
        assert [v.decode() for v in h5[key][:]] == names, key
    a = h5[f"A_{split}"][:]
    alt = h5[f"W_{split}"][:, 0]
    assert a.shape[0] == alt.size == h5[f"X_s_{split}"].shape[0]
    assert set(np.unique(a[:, 3])) == {0.0, 1.0}
    units = a[:, 0].astype(np.int16)
    cycles = a[:, 1].astype(np.int16)
    fc = a[:, 2].astype(np.int8)
    hs = a[:, 3].astype(np.int8)
    assert np.all(np.isfinite(alt))
    phase = np.empty(a.shape[0], dtype=np.int8)
    boundary = np.flatnonzero((np.diff(units) != 0) | (np.diff(cycles) != 0)) + 1
    starts = np.r_[0, boundary]
    ends = np.r_[boundary, len(a)]
    cycle_rows = []
    for start, end in zip(starts, ends):
        curve = alt[start:end]
        low, high = float(curve.min()), float(curve.max())
        assert high > low
        near_top = np.flatnonzero(curve >= low + ALT_FRACTION * (high - low))
        first, last = int(near_top[0]), int(near_top[-1])
        phase[start:start + first] = 0
        phase[start + first:start + last + 1] = 1
        phase[start + last + 1:end] = 2
        cycle_rows.append({"split": split, "unit": int(units[start]), "cycle": int(cycles[start]),
                           "flight_class": int(fc[start]), "rows": end - start,
                           "alt_min": low, "alt_max": high,
                           "climb_rows": first, "cruise_rows": last - first + 1,
                           "descent_rows": end - start - last - 1,
                           "healthy_rows": int(hs[start:end].sum())})
    # Every unit starts healthy and then transitions at most once to degraded.
    for unit in np.unique(units):
        state = hs[units == unit]
        assert state[0] == 1 and np.all(np.diff(state) <= 0), unit
    meta = pd.DataFrame({"unit": units, "cycle": cycles, "flight_class": fc,
                         "healthy": hs, "phase": phase})
    return meta, pd.DataFrame(cycle_rows), alt


def healthy_data(h5: h5py.File, split: str, meta: pd.DataFrame, selected_units):
    mask = (meta.healthy.to_numpy() == 1) & meta.unit.isin(selected_units).to_numpy()
    indices = np.flatnonzero(mask)
    assert len(indices) > 0
    cuts = np.flatnonzero(np.diff(indices) > 1) + 1
    groups = np.split(indices, cuts)
    dataset = h5[f"X_s_{split}"]
    x = np.concatenate([dataset[int(g[0]):int(g[-1]) + 1]
                        for g in groups], axis=0)
    assert np.isfinite(x).all()
    return x, meta.loc[mask].reset_index(drop=True)


def score_pca(x, scaler, pca):
    z = scaler.transform(x)
    reconstructed = pca.inverse_transform(pca.transform(z))
    return np.mean((z - reconstructed) ** 2, axis=1, dtype=np.float64)


def summarize(scores, meta, name):
    frame = meta.copy()
    frame["score"] = scores
    rows = []
    for (unit, phase), group in frame.groupby(["unit", "phase"]):
        s = group.score.to_numpy()
        rows.append({"subset": name, "unit": int(unit), "flight_class": int(group.flight_class.iloc[0]),
                     "phase": PHASES[int(phase)], "n": len(s), "mean": float(s.mean()),
                     "median": float(np.median(s)), "p90": float(np.quantile(s, .9)),
                     "p95": float(np.quantile(s, .95)), "p99": float(np.quantile(s, .99))})
    for phase, group in frame.groupby("phase"):
        s = group.score.to_numpy()
        rows.append({"subset": name, "unit": "all", "flight_class": "mixed" if name == "test" else 3,
                     "phase": PHASES[int(phase)], "n": len(s), "mean": float(s.mean()),
                     "median": float(np.median(s)), "p90": float(np.quantile(s, .9)),
                     "p95": float(np.quantile(s, .95)), "p99": float(np.quantile(s, .99))})
    return pd.DataFrame(rows)


def rates(scores, meta, threshold, name):
    rows = []
    for unit in [*sorted(meta.unit.unique()), "all"]:
        unit_mask = np.ones(len(scores), dtype=bool) if unit == "all" else meta.unit.to_numpy() == unit
        for phase_num, phase_name in enumerate(PHASES):
            mask = unit_mask & (meta.phase.to_numpy() == phase_num)
            n = int(mask.sum())
            rows.append({"subset": name, "unit": unit,
                         "flight_class": "mixed" if unit == "all" and name == "test" else
                         (3 if unit == "all" else int(meta.flight_class[unit_mask].iloc[0])),
                         "phase": phase_name, "n": n,
                         "false_alarms": int(np.sum(scores[mask] > threshold)),
                         "false_alarm_rate": float(np.mean(scores[mask] > threshold)) if n else np.nan,
                         "threshold": threshold})
    return pd.DataFrame(rows)


def make_figures(cycles, alt, val_scores, val_meta, test_scores, test_meta, threshold, transfer):
    FIGURES.mkdir(exist_ok=True)
    # Show the actual heuristic on the first healthy development flight.
    c = cycles[(cycles.unit == 2) & (cycles.cycle == 1)].iloc[0]
    n = int(c.rows)
    y = alt[:n]
    cuts = [0, int(c.climb_rows), int(c.climb_rows + c.cruise_rows), n]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    colors = ["#7a9e9f", "#d9a441", "#577590"]
    for p in range(3):
        ax.axvspan(cuts[p], cuts[p + 1], color=colors[p], alpha=.19, label=PHASES[p])
    ax.plot(np.arange(n), y, color="#263238", linewidth=.7)
    ax.set(xlabel="Sample within flight", ylabel="Altitude (ft)", title="Unit 2, cycle 1: altitude based phase heuristic")
    ax.legend(ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "phase_heuristic.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for p, color in enumerate(colors):
        s = np.sort(test_scores[test_meta.phase.to_numpy() == p])
        # Deterministically thin only the plotted points.
        sample = s[np.linspace(0, len(s) - 1, min(2000, len(s))).astype(int)]
        ax.plot(sample, 1 - np.linspace(0, 1, len(sample)), color=color, label=PHASES[p])
    ax.axvline(threshold, color="black", linestyle="--", linewidth=1, label="Pooled validation 99th percentile")
    ax.set(xscale="log", yscale="log", xlabel="PCA reconstruction score", ylabel="Fraction exceeding score",
           title="Healthy held-out test score tails")
    ax.set_ylim(1e-4, 1)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "score_tails.png", dpi=180)
    plt.close(fig)

    far = rates(test_scores, test_meta, threshold, "test")
    far = far[far.unit != "all"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    positions = np.arange(3)
    for p, color in enumerate(colors):
        values = [far[(far.unit == u) & (far.phase == PHASES[p])].false_alarm_rate.iloc[0] * 100
                  for u in TEST_UNITS]
        ax.bar(positions + (p - 1) * .25, values, width=.24, color=color, label=PHASES[p])
    ax.axhline(1, color="black", linestyle="--", linewidth=1)
    ax.set(xticks=positions, xticklabels=[f"{u} (Fc {f})" for u, f in zip(TEST_UNITS, (3, 1, 2))],
           xlabel="Held-out test unit", ylabel="Healthy false alarm rate (%)",
           title="Pooled validation threshold transferred to unseen engines")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "false_alarm_rates.png", dpi=180)
    plt.close(fig)

    matrix = transfer[transfer.unit == "all"].pivot(index="calibration_phase", columns="test_phase", values="false_alarm_rate")
    matrix = matrix.loc[list(PHASES), list(PHASES)] * 100
    fig, ax = plt.subplots(figsize=(6, 4.5))
    image = ax.imshow(matrix, cmap="magma", aspect="auto", vmin=0, vmax=max(5, float(np.nanmax(matrix))))
    for i in range(3):
        for j in range(3):
            value = matrix.iloc[i, j]
            label = f"{value:.3f}%" if value < .01 else f"{value:.2f}%"
            ax.text(j, i, label, ha="center", va="center",
                    color="black" if value > .65 * float(np.nanmax(matrix)) else "white")
    ax.set(xticks=range(3), xticklabels=PHASES, yticks=range(3), yticklabels=PHASES,
           xlabel="Audit test phase", ylabel="Validation calibration phase",
           title="99th percentile threshold transfer")
    fig.colorbar(image, ax=ax, label="Healthy false alarm rate (%)")
    fig.tight_layout()
    fig.savefig(FIGURES / "threshold_transfer.png", dpi=180)
    plt.close(fig)


def main():
    RESULTS.mkdir(exist_ok=True)
    with h5py.File(DATA) as h5:
        dev_meta, dev_cycles, dev_alt = inspect_and_metadata(h5, "dev")
        test_meta_all, test_cycles, _ = inspect_and_metadata(h5, "test")
        assert set(dev_meta.unit.unique()) == set(TRAIN_UNITS + VAL_UNITS)
        assert set(test_meta_all.unit.unique()) == set(TEST_UNITS)
        assert set(dev_meta.flight_class.unique()) == {3}
        train_x, train_meta = healthy_data(h5, "dev", dev_meta, TRAIN_UNITS)
        val_x, val_meta = healthy_data(h5, "dev", dev_meta, VAL_UNITS)
        test_x, test_meta = healthy_data(h5, "test", test_meta_all, TEST_UNITS)
    cycles = pd.concat([dev_cycles, test_cycles], ignore_index=True)
    cycles.to_csv(RESULTS / "cycle_phase_audit.csv", index=False)
    schema = {"file": str(DATA), "datasets": {}, "variables": NAMES,
              "healthy_encoding": 1, "phase_altitude_fraction": ALT_FRACTION,
              "train_units": TRAIN_UNITS, "validation_units": VAL_UNITS, "official_test_units": TEST_UNITS}
    with h5py.File(DATA) as h5:
        for key in h5:
            schema["datasets"][key] = {"shape": h5[key].shape, "dtype": str(h5[key].dtype)}
    (RESULTS / "schema_audit.json").write_text(json.dumps(schema, indent=2))

    scaler = StandardScaler().fit(train_x)
    z_train = scaler.transform(train_x)
    pca = PCA(n_components=N_COMPONENTS, svd_solver="full").fit(z_train)
    train_score = score_pca(train_x, scaler, pca)
    val_score = score_pca(val_x, scaler, pca)
    test_score = score_pca(test_x, scaler, pca)
    assert np.isfinite(val_score).all() and np.isfinite(test_score).all()
    summaries = pd.concat([summarize(train_score, train_meta, "train"),
                           summarize(val_score, val_meta, "validation"),
                           summarize(test_score, test_meta, "test")], ignore_index=True)
    summaries.to_csv(RESULTS / "score_distributions.csv", index=False)
    threshold = float(np.quantile(val_score, .99, method="higher"))
    far = pd.concat([rates(val_score, val_meta, threshold, "validation"),
                     rates(test_score, test_meta, threshold, "test")], ignore_index=True)
    far.to_csv(RESULTS / "phase_false_alarm_rates.csv", index=False)
    # Preserve flight-level alarm clustering; rows are not independent trials.
    flight = test_meta.copy()
    flight["alarm"] = test_score > threshold
    flight = flight.groupby(["unit", "cycle", "flight_class", "phase"], as_index=False).agg(
        n=("alarm", "size"), false_alarms=("alarm", "sum"))
    flight["phase"] = flight.phase.map(dict(enumerate(PHASES)))
    flight["false_alarm_rate"] = flight.false_alarms / flight.n
    flight.to_csv(RESULTS / "phase_flight_audit.csv", index=False)
    transfer_rows = []
    for calibration_phase, phase_name in enumerate(PHASES):
        calibration_score = val_score[val_meta.phase.to_numpy() == calibration_phase]
        phase_threshold = float(np.quantile(calibration_score, .99, method="higher"))
        for unit in [*TEST_UNITS, "all"]:
            unit_mask = (test_meta.unit.to_numpy() == unit) if unit != "all" else np.ones(len(test_score), dtype=bool)
            for test_phase, test_name in enumerate(PHASES):
                mask = unit_mask & (test_meta.phase.to_numpy() == test_phase)
                transfer_rows.append({"unit": unit, "calibration_phase": phase_name,
                                      "test_phase": test_name, "threshold": phase_threshold,
                                      "n": int(mask.sum()), "false_alarms": int(np.sum(test_score[mask] > phase_threshold)),
                                      "false_alarm_rate": float(np.mean(test_score[mask] > phase_threshold))})
    transfer = pd.DataFrame(transfer_rows)
    transfer.to_csv(RESULTS / "threshold_transfer_matrix.csv", index=False)

    # A small one-dimensional supervised probe, fitted on validation engines only.
    transform = lambda s: np.log10(np.maximum(s, 1e-12)).reshape(-1, 1)
    probe = DecisionTreeClassifier(max_depth=3, min_samples_leaf=1000,
                                   class_weight="balanced", random_state=0)
    probe.fit(transform(val_score), val_meta.phase.to_numpy())
    predictions = probe.predict(transform(test_score))
    phase_prediction_rows = []
    for unit in [*TEST_UNITS, "all"]:
        mask = test_meta.unit.to_numpy() == unit if unit != "all" else np.ones(len(test_score), dtype=bool)
        truth = test_meta.phase.to_numpy()[mask]
        pred = predictions[mask]
        matrix = confusion_matrix(truth, pred, labels=[0, 1, 2])
        phase_prediction_rows.append({"unit": unit, "n": int(mask.sum()),
                                      "balanced_accuracy": float(balanced_accuracy_score(truth, pred)),
                                      "chance_balanced_accuracy": 1 / 3,
                                      **{f"recall_{PHASES[i]}": float(matrix[i, i] / matrix[i].sum()) for i in range(3)}})
    pd.DataFrame(phase_prediction_rows).to_csv(RESULTS / "score_only_phase_prediction.csv", index=False)

    config = {"train_healthy_rows": len(train_x), "validation_healthy_rows": len(val_x),
              "test_healthy_rows": len(test_x), "pca_components": N_COMPONENTS,
              "pca_explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
              "pooled_validation_threshold": threshold,
              "detector_inputs": NAMES["X_s_var"],
              "phase_probe": "depth-3 balanced decision tree on log10(score), trained on validation engines"}
    (RESULTS / "run_config.json").write_text(json.dumps(config, indent=2))
    make_figures(dev_cycles, dev_alt, val_score, val_meta, test_score, test_meta, threshold, transfer)
    print(json.dumps(config, indent=2))
    print("\nHeld-out test false alarm rates:\n", far[far.subset == "test"].to_string(index=False))
    print("\nScore-only phase prediction:\n", pd.DataFrame(phase_prediction_rows).to_string(index=False))


if __name__ == "__main__":
    main()
