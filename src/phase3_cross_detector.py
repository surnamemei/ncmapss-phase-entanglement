"""Phase 3B/3C: cross-detector replication and robustness checks."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.ensemble import IsolationForest
from sklearn.metrics import balanced_accuracy_score
from sklearn.tree import DecisionTreeClassifier

from second_stage_audit import (
    DATA, PHASES, TRAIN_UNITS, CAL_UNITS, SENSORS, load_split, count_events,
)
from phase3_dynamic import causal_descriptors, ResidualPCADetector


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/phase3_cross_detector"
FIG = ROOT / "figures/phase3"
SEEDS = (0, 1, 2)
TARGETS = (0.005, 0.01, 0.02)
PHASE_DEFINITIONS = ("primary", "alt_rate")
LSTM_LENGTH = 256
LSTM_EPOCHS = 3


def phase_col(definition):
    return "phase_primary" if definition == "primary" else "phase_alt_rate"


def make_training_chunks(z, meta):
    chunks = []
    for _, flight in meta.groupby(["unit", "cycle"], sort=False):
        idx = flight.index.to_numpy()
        for start in range(0, len(idx) - LSTM_LENGTH + 1, LSTM_LENGTH):
            chunks.append(z[idx[start:start + LSTM_LENGTH]])
    return np.asarray(chunks, dtype=np.float32)


def make_scoring_chunks(z, meta):
    chunks, mappings = [], []
    for _, flight in meta.groupby(["unit", "cycle"], sort=False):
        idx = flight.index.to_numpy()
        for start in range(0, len(idx), LSTM_LENGTH):
            selected = idx[start:start + LSTM_LENGTH]
            chunk = np.zeros((LSTM_LENGTH, z.shape[1]), dtype=np.float32)
            chunk[:len(selected)] = z[selected]
            chunks.append(chunk)
            mappings.append(selected)
    return np.asarray(chunks), mappings


def build_lstm(seed):
    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        pass
    inputs = tf.keras.Input(shape=(None, len(SENSORS)))
    encoded = tf.keras.layers.LSTM(16, return_sequences=True)(inputs)
    bottleneck = tf.keras.layers.Dense(8, activation="tanh", name="bottleneck")(encoded)
    decoded = tf.keras.layers.LSTM(16, return_sequences=True)(bottleneck)
    outputs = tf.keras.layers.Dense(len(SENSORS))(decoded)
    model = tf.keras.Model(inputs, outputs, name="causal_lstm_autoencoder")
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="mse")
    return model


def lstm_score(model, z, meta):
    scores = np.empty(len(z), dtype=np.float64)
    chunks, mappings = make_scoring_chunks(z, meta)
    prediction = model.predict(chunks, batch_size=128, verbose=0)
    for chunk, reconstructed, selected in zip(chunks, prediction, mappings):
        scores[selected] = np.mean((chunk[:len(selected)] - reconstructed[:len(selected)]) ** 2, axis=1)
    return scores


def summarize_scores(scores, meta, detector, seed, definition, subset):
    col = phase_col(definition)
    rows = []
    groups = [(str(int(u)), meta.unit.to_numpy() == u) for u in sorted(meta.unit.unique())]
    groups += [("all", np.ones(len(meta), dtype=bool))]
    for unit, unit_mask in groups:
        fc = int(meta.loc[unit_mask, "flight_class"].iloc[0]) if unit != "all" else "mixed"
        for phase_id, phase in enumerate(PHASES):
            values = scores[unit_mask & (meta[col].to_numpy() == phase_id)]
            rows.append({"detector": detector, "seed": seed, "phase_definition": definition,
                         "subset": subset, "unit": unit, "flight_class": fc, "phase": phase,
                         "n": len(values), "mean": values.mean(), "median": np.median(values),
                         "p90": np.quantile(values, .90), "p95": np.quantile(values, .95),
                         "p99": np.quantile(values, .99)})
    return rows


def row_metrics(scores, meta, threshold, detector, seed, definition, target):
    col = phase_col(definition)
    rows = []
    groups = [(str(int(u)), meta.unit.to_numpy() == u) for u in sorted(meta.unit.unique())]
    groups += [("all", np.ones(len(meta), dtype=bool))]
    for unit, unit_mask in groups:
        fc = int(meta.loc[unit_mask, "flight_class"].iloc[0]) if unit != "all" else "mixed"
        for phase_id, phase in [(None, "overall"), *enumerate(PHASES)]:
            mask = unit_mask if phase_id is None else unit_mask & (meta[col].to_numpy() == phase_id)
            alarm = scores[mask] > threshold
            rows.append({"detector": detector, "seed": seed, "phase_definition": definition,
                         "nominal_fpr": target, "unit": unit, "flight_class": fc, "phase": phase,
                         "n": int(mask.sum()), "false_alarms": int(alarm.sum()),
                         "false_alarm_rate": float(alarm.mean()), "threshold": threshold,
                         "matched_fc": unit == "11"})
    return rows


def transfer_metrics(cal_scores, cal_meta, test_scores, test_meta, detector, seed, definition, target):
    col = phase_col(definition)
    rows = []
    for cal_id, cal_phase in enumerate(PHASES):
        threshold = float(np.quantile(cal_scores[cal_meta[col].to_numpy() == cal_id], 1 - target, method="higher"))
        groups = [(str(int(u)), test_meta.unit.to_numpy() == u) for u in sorted(test_meta.unit.unique())]
        groups += [("all", np.ones(len(test_meta), dtype=bool))]
        for unit, unit_mask in groups:
            for test_id, test_phase in enumerate(PHASES):
                mask = unit_mask & (test_meta[col].to_numpy() == test_id)
                alarm = test_scores[mask] > threshold
                rows.append({"detector": detector, "seed": seed, "phase_definition": definition,
                             "nominal_fpr": target, "unit": unit,
                             "flight_class": int(test_meta.loc[unit_mask, "flight_class"].iloc[0]) if unit != "all" else "mixed",
                             "calibration_phase": cal_phase, "test_phase": test_phase,
                             "n": int(mask.sum()), "false_alarms": int(alarm.sum()),
                             "false_alarm_rate": float(alarm.mean()), "threshold": threshold,
                             "matched_fc": unit == "11"})
    return rows


def probe_metrics(cal_scores, cal_meta, test_scores, test_meta, detector, seed, definition):
    col = phase_col(definition)
    transform = lambda s: np.log10(np.maximum(s, 1e-15)).reshape(-1, 1)
    probe = DecisionTreeClassifier(max_depth=3, min_samples_leaf=1000,
                                   class_weight="balanced", random_state=0)
    probe.fit(transform(cal_scores), cal_meta[col].to_numpy())
    prediction = probe.predict(transform(test_scores))
    rows = []
    for unit, mask in [(str(int(u)), test_meta.unit.to_numpy() == u) for u in sorted(test_meta.unit.unique())] + [("all", np.ones(len(test_meta), dtype=bool))]:
        rows.append({"detector": detector, "seed": seed, "phase_definition": definition,
                     "unit": unit,
                     "flight_class": int(test_meta.loc[mask, "flight_class"].iloc[0]) if unit != "all" else "mixed",
                     "n": int(mask.sum()),
                     "balanced_accuracy": balanced_accuracy_score(test_meta.loc[mask, col], prediction[mask]),
                     "chance_balanced_accuracy": 1 / 3, "matched_fc": unit == "11"})
    return rows


def flight_metrics(scores, meta, threshold, detector, seed, definition, target):
    col = phase_col(definition)
    detail = []
    work = meta[["unit", "cycle", "flight_class", col]].copy()
    work["alarm"] = scores > threshold
    for (unit, cycle), flight in work.groupby(["unit", "cycle"], sort=False):
        for phase_id, phase in [(None, "overall"), *enumerate(PHASES)]:
            alarm = (flight.alarm.to_numpy() if phase_id is None else
                     flight.loc[flight[col] == phase_id, "alarm"].to_numpy())
            detail.append({"detector": detector, "seed": seed, "phase_definition": definition,
                           "nominal_fpr": target, "unit": int(unit), "cycle": int(cycle),
                           "flight_class": int(flight.flight_class.iloc[0]), "phase": phase,
                           "rows": len(alarm), "false_alarms": int(alarm.sum()),
                           "any_false_alarm": int(alarm.any()),
                           "false_alarm_events": count_events(alarm), "matched_fc": int(unit) == 11})
    detail = pd.DataFrame(detail)
    summary = []
    for unit, group in list(detail.groupby("unit")) + [("all", detail)]:
        for phase, part in group.groupby("phase"):
            summary.append({"detector": detector, "seed": seed, "phase_definition": definition,
                            "nominal_fpr": target, "unit": unit,
                            "flight_class": int(part.flight_class.iloc[0]) if unit != "all" else "mixed",
                            "phase": phase, "healthy_flights": len(part),
                            "fraction_flights_with_false_alarm": float(part.any_false_alarm.mean()),
                            "events_per_healthy_flight": float(part.false_alarm_events.mean()),
                            "matched_fc": str(unit) == "11"})
    return detail.to_dict("records"), summary


def bootstrap_fpr(detail_df, repetitions=500):
    """Cluster bootstrap whole flights; never resample timestamps."""
    rng = np.random.default_rng(20260925)
    rows = []
    for keys, group in detail_df.groupby(["detector", "seed", "phase_definition", "nominal_fpr", "phase"]):
        values = group[["rows", "false_alarms"]].to_numpy(dtype=np.float64)
        estimates = np.empty(repetitions)
        for b in range(repetitions):
            sampled = values[rng.integers(0, len(values), len(values))]
            estimates[b] = sampled[:, 1].sum() / sampled[:, 0].sum()
        detector, seed, definition, target, phase = keys
        rows.append({"detector": detector, "seed": seed, "phase_definition": definition,
                     "nominal_fpr": target, "phase": phase, "bootstrap_unit": "flight",
                     "repetitions": repetitions, "estimate": values[:, 1].sum() / values[:, 0].sum(),
                     "ci_lower_95": np.quantile(estimates, .025),
                     "ci_upper_95": np.quantile(estimates, .975)})
    return pd.DataFrame(rows)


def audit_run(detector, seed, train_score, cal_score, test_score,
              train_meta, cal_meta, test_meta, outputs):
    score_rows, rate_rows, transfer_rows, probe_rows, detail_rows, summary_rows = outputs
    for definition in PHASE_DEFINITIONS:
        score_rows += summarize_scores(train_score, train_meta, detector, seed, definition, "train")
        score_rows += summarize_scores(cal_score, cal_meta, detector, seed, definition, "calibration")
        score_rows += summarize_scores(test_score, test_meta, detector, seed, definition, "official_test")
        probe_rows += probe_metrics(cal_score, cal_meta, test_score, test_meta, detector, seed, definition)
        for target in TARGETS:
            threshold = float(np.quantile(cal_score, 1 - target, method="higher"))
            rate_rows += row_metrics(test_score, test_meta, threshold, detector, seed, definition, target)
            transfer_rows += transfer_metrics(cal_score, cal_meta, test_score, test_meta,
                                               detector, seed, definition, target)
            detail, summary = flight_metrics(test_score, test_meta, threshold, detector, seed, definition, target)
            detail_rows += detail
            summary_rows += summary


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    with h5py.File(DATA) as h5:
        dev_x_all, dev_w_all, dev_meta_all, _ = load_split(h5, "dev")
        test_x_all, test_w_all, test_meta_all, _ = load_split(h5, "test")
    dev_mask = dev_meta_all.healthy.to_numpy() == 1
    test_mask = test_meta_all.healthy.to_numpy() == 1
    dev_x, dev_w = dev_x_all[dev_mask], dev_w_all[dev_mask]
    test_x, test_w = test_x_all[test_mask], test_w_all[test_mask]
    dev_meta = dev_meta_all[dev_mask].reset_index(drop=True)
    test_meta = test_meta_all[test_mask].reset_index(drop=True)
    del dev_x_all, dev_w_all, test_x_all, test_w_all
    dev_desc, descriptor_names = causal_descriptors(dev_w, dev_meta)
    test_desc, _ = causal_descriptors(test_w, test_meta)
    train_mask = dev_meta.unit.isin(TRAIN_UNITS).to_numpy()
    cal_mask = dev_meta.unit.isin(CAL_UNITS).to_numpy()
    train_meta = dev_meta[train_mask].reset_index(drop=True)
    cal_meta = dev_meta[cal_mask].reset_index(drop=True)

    # Fit the chosen correction once on training engines. Every detector sees the
    # same standardized history-corrected residuals.
    correction = ResidualPCADetector("history", alpha=1.0).fit(dev_x[train_mask], dev_desc[train_mask])
    z_train = correction.standardized_residual(dev_x[train_mask], dev_desc[train_mask]).astype(np.float32)
    z_cal = correction.standardized_residual(dev_x[cal_mask], dev_desc[cal_mask]).astype(np.float32)
    z_test = correction.standardized_residual(test_x, test_desc).astype(np.float32)

    outputs = ([], [], [], [], [], [])
    # PCA is deterministic under full SVD.
    audit_run("pca", -1, correction.score(dev_x[train_mask], dev_desc[train_mask]),
              correction.score(dev_x[cal_mask], dev_desc[cal_mask]),
              correction.score(test_x, test_desc), train_meta, cal_meta, test_meta, outputs)

    for seed in SEEDS:
        print(f"Isolation Forest seed {seed}", flush=True)
        forest = IsolationForest(n_estimators=200, max_samples=8192, contamination="auto",
                                 random_state=seed, n_jobs=-1).fit(z_train)
        audit_run("isolation_forest", seed, -forest.score_samples(z_train),
                  -forest.score_samples(z_cal), -forest.score_samples(z_test),
                  train_meta, cal_meta, test_meta, outputs)

    chunks = make_training_chunks(z_train, train_meta)
    print(f"LSTM training chunks: {chunks.shape}", flush=True)
    histories = []
    for seed in SEEDS:
        print(f"LSTM autoencoder seed {seed}", flush=True)
        model = build_lstm(seed)
        history = model.fit(chunks, chunks, epochs=LSTM_EPOCHS, batch_size=256,
                            shuffle=True, verbose=0)
        histories.append({"seed": seed, **{f"loss_epoch_{i + 1}": value for i, value in enumerate(history.history["loss"])}})
        audit_run("lstm_autoencoder", seed, lstm_score(model, z_train, train_meta),
                  lstm_score(model, z_cal, cal_meta), lstm_score(model, z_test, test_meta),
                  train_meta, cal_meta, test_meta, outputs)
    del chunks

    score_df, rate_df, transfer_df, probe_df, detail_df, summary_df = map(pd.DataFrame, outputs)
    score_df.to_csv(OUT / "score_distributions.csv", index=False)
    rate_df.to_csv(OUT / "row_false_alarm_rates.csv", index=False)
    transfer_df.to_csv(OUT / "threshold_transfer_matrix.csv", index=False)
    probe_df.to_csv(OUT / "score_only_phase_prediction.csv", index=False)
    detail_df.to_csv(OUT / "flight_alarm_detail.csv", index=False)
    summary_df.to_csv(OUT / "flight_alarm_summary.csv", index=False)
    pd.DataFrame(histories).to_csv(OUT / "lstm_training_history.csv", index=False)
    bootstrap_fpr(detail_df).to_csv(OUT / "flight_bootstrap_fpr_ci.csv", index=False)

    # One-row-per-run comparison; family aggregates retain seed variability.
    comparison = []
    for (detector, seed, definition, target), group in rate_df.groupby(
            ["detector", "seed", "phase_definition", "nominal_fpr"]):
        pooled = group[group.unit == "all"].set_index("phase")
        phase_rates = pooled.loc[list(PHASES), "false_alarm_rate"]
        transfer = transfer_df[(transfer_df.detector == detector) & (transfer_df.seed == seed) &
                               (transfer_df.phase_definition == definition) &
                               (transfer_df.nominal_fpr == target) & (transfer_df.unit == "all")]
        probe = probe_df[(probe_df.detector == detector) & (probe_df.seed == seed) &
                         (probe_df.phase_definition == definition) & (probe_df.unit == "all")].iloc[0]
        flight = summary_df[(summary_df.detector == detector) & (summary_df.seed == seed) &
                            (summary_df.phase_definition == definition) &
                            (summary_df.nominal_fpr == target) & (summary_df.unit == "all")].set_index("phase")
        comparison.append({"detector": detector, "seed": seed, "phase_definition": definition,
                           "nominal_fpr": target, "overall_fpr": pooled.loc["overall", "false_alarm_rate"],
                           "climb_fpr": phase_rates.climb, "cruise_fpr": phase_rates.cruise,
                           "descent_fpr": phase_rates.descent,
                           "max_min_phase_fpr_ratio": phase_rates.max() / phase_rates.min(),
                           "worst_offdiagonal_transfer_fpr": transfer[transfer.calibration_phase != transfer.test_phase].false_alarm_rate.max(),
                           "score_only_phase_balanced_accuracy": probe.balanced_accuracy,
                           "climb_flights_with_alarm": flight.loc["climb", "fraction_flights_with_false_alarm"],
                           "cruise_flights_with_alarm": flight.loc["cruise", "fraction_flights_with_false_alarm"],
                           "descent_flights_with_alarm": flight.loc["descent", "fraction_flights_with_false_alarm"],
                           "events_per_flight": flight.loc["overall", "events_per_healthy_flight"]})
    comparison_df = pd.DataFrame(comparison)
    comparison_df.to_csv(OUT / "run_comparison.csv", index=False)
    family = (comparison_df.groupby(["detector", "phase_definition", "nominal_fpr"])
              .agg({column: ["mean", "min", "max"] for column in comparison_df.columns
                    if column not in ("detector", "seed", "phase_definition", "nominal_fpr")}).reset_index())
    family.columns = ["_".join([str(x) for x in col if x]) if isinstance(col, tuple) else col for col in family.columns]
    family.to_csv(OUT / "family_summary.csv", index=False)

    # Main 1% primary-phase figure using family means.
    main = comparison_df[(comparison_df.phase_definition == "primary") & (comparison_df.nominal_fpr == .01)]
    means = main.groupby("detector")[["climb_fpr", "cruise_fpr", "descent_fpr"]].mean()
    order = ["pca", "isolation_forest", "lstm_autoencoder"]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    xloc = np.arange(3)
    for i, phase in enumerate(PHASES):
        ax.bar(xloc + (i - 1) * .25, means.loc[order, f"{phase}_fpr"] * 100,
               width=.25, label=phase)
    ax.axhline(1, color="black", linestyle="--", linewidth=1)
    ax.set(xticks=xloc, xticklabels=["PCA", "Isolation Forest", "LSTM AE"],
           ylabel="Healthy false alarm rate (%)",
           title="Cross-detector phase FPR after causal history correction")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "cross_detector_phase_fpr.png", dpi=180)
    plt.close(fig)

    config = {"seeds": SEEDS, "nominal_fpr_targets": TARGETS,
              "phase_definitions": PHASE_DEFINITIONS,
              "correction": "history from Phase 3A", "history_descriptors": descriptor_names,
              "isolation_forest": {"n_estimators": 200, "max_samples": 8192},
              "lstm_autoencoder": {"causal": True, "layers": "LSTM16-Dense8-LSTM16-Dense14",
                                    "sequence_length": LSTM_LENGTH, "epochs": LSTM_EPOCHS,
                                    "batch_size": 256, "optimizer": "Adam 1e-3"},
              "bootstrap": {"unit": "flight", "repetitions": 500}}
    (OUT / "run_config.json").write_text(json.dumps(config, indent=2))
    print(main.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
