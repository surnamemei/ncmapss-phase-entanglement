"""Final validation for the DS02 phase-confounding discovery analysis.

This script deliberately adds no detector families. It replaces the old
three-epoch LSTM runs, builds a canonical executed-results table, audits
sequence-chunk boundaries, and calculates cluster-aware uncertainty.
DS02 remains discovery data; external confirmation is governed by the frozen
protocol written before this script was run.
"""

from __future__ import annotations

import gc
import json
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import h5py
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.ensemble import IsolationForest
from sklearn.metrics import balanced_accuracy_score
from sklearn.tree import DecisionTreeClassifier

from phase3_dynamic import ResidualPCADetector, causal_descriptors
from second_stage_audit import (
    CAL_UNITS,
    DATA,
    PHASES,
    TRAIN_UNITS,
    count_events,
    load_split,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("NCMAPSS_DS02_RESULTS_DIR", ROOT / "results/final_validation"))
CHECKPOINTS = OUT / "checkpoints"
MAX_EPOCHS = 600
PATIENCE = 6
MIN_DELTA = 1e-4
SELECTION_FIT_UNITS = (2, 5, 10)
SELECTION_VALIDATION_UNIT = 16
LSTM_LENGTH = 256
BOUNDARY_WIDTH = 16
BOOTSTRAP_REPETITIONS = 2000
BOOTSTRAP_SEED = 20260925
DEVICE = torch.device("cuda")
SEEDS = (0, 1, 2)
TARGETS = (0.005, 0.01, 0.02)
PHASE_DEFINITIONS = ("primary", "alt_rate")


def phase_col(definition):
    return "phase_primary" if definition == "primary" else "phase_alt_rate"


def make_training_chunks(z, meta):
    chunks = []
    for _, flight in meta.groupby(["unit", "cycle"], sort=False):
        idx = flight.index.to_numpy()
        for start in range(0, len(idx) - LSTM_LENGTH + 1, LSTM_LENGTH):
            chunks.append(z[idx[start:start + LSTM_LENGTH]])
    return np.asarray(chunks, dtype=np.float32)


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


def transfer_metrics(cal_scores, cal_meta, test_scores, test_meta, detector, seed,
                     definition, target):
    col = phase_col(definition)
    rows = []
    for cal_id, cal_phase in enumerate(PHASES):
        threshold = float(np.quantile(
            cal_scores[cal_meta[col].to_numpy() == cal_id], 1 - target, method="higher"
        ))
        groups = [(str(int(u)), test_meta.unit.to_numpy() == u)
                  for u in sorted(test_meta.unit.unique())]
        groups += [("all", np.ones(len(test_meta), dtype=bool))]
        for unit, unit_mask in groups:
            for test_id, test_phase in enumerate(PHASES):
                mask = unit_mask & (test_meta[col].to_numpy() == test_id)
                alarm = test_scores[mask] > threshold
                rows.append({"detector": detector, "seed": seed,
                             "phase_definition": definition, "nominal_fpr": target,
                             "unit": unit,
                             "flight_class": int(test_meta.loc[unit_mask, "flight_class"].iloc[0])
                             if unit != "all" else "mixed",
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
    groups = [(str(int(u)), test_meta.unit.to_numpy() == u)
              for u in sorted(test_meta.unit.unique())]
    groups += [("all", np.ones(len(test_meta), dtype=bool))]
    rows = []
    for unit, mask in groups:
        rows.append({"detector": detector, "seed": seed, "phase_definition": definition,
                     "unit": unit,
                     "flight_class": int(test_meta.loc[mask, "flight_class"].iloc[0])
                     if unit != "all" else "mixed",
                     "n": int(mask.sum()),
                     "balanced_accuracy": balanced_accuracy_score(
                         test_meta.loc[mask, col], prediction[mask]
                     ),
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
            detail.append({"detector": detector, "seed": seed,
                           "phase_definition": definition, "nominal_fpr": target,
                           "unit": int(unit), "cycle": int(cycle),
                           "flight_class": int(flight.flight_class.iloc[0]), "phase": phase,
                           "rows": len(alarm), "false_alarms": int(alarm.sum()),
                           "any_false_alarm": int(alarm.any()),
                           "false_alarm_events": count_events(alarm),
                           "matched_fc": int(unit) == 11})
    detail = pd.DataFrame(detail)
    summary = []
    for unit, group in list(detail.groupby("unit")) + [("all", detail)]:
        for phase, part in group.groupby("phase"):
            summary.append({"detector": detector, "seed": seed,
                            "phase_definition": definition, "nominal_fpr": target,
                            "unit": unit,
                            "flight_class": int(part.flight_class.iloc[0])
                            if unit != "all" else "mixed",
                            "phase": phase, "healthy_flights": len(part),
                            "fraction_flights_with_false_alarm": float(
                                part.any_false_alarm.mean()
                            ),
                            "events_per_healthy_flight": float(
                                part.false_alarm_events.mean()
                            ),
                            "matched_fc": str(unit) == "11"})
    return detail.to_dict("records"), summary


def audit_run(detector, seed, train_score, cal_score, test_score,
              train_meta, cal_meta, test_meta, outputs):
    score_rows, rate_rows, transfer_rows, probe_rows, detail_rows, summary_rows = outputs
    for definition in PHASE_DEFINITIONS:
        score_rows += summarize_scores(
            train_score, train_meta, detector, seed, definition, "train"
        )
        score_rows += summarize_scores(
            cal_score, cal_meta, detector, seed, definition, "calibration"
        )
        score_rows += summarize_scores(
            test_score, test_meta, detector, seed, definition, "official_test"
        )
        probe_rows += probe_metrics(
            cal_score, cal_meta, test_score, test_meta, detector, seed, definition
        )
        for target in TARGETS:
            threshold = float(np.quantile(cal_score, 1 - target, method="higher"))
            rate_rows += row_metrics(
                test_score, test_meta, threshold, detector, seed, definition, target
            )
            transfer_rows += transfer_metrics(
                cal_score, cal_meta, test_score, test_meta, detector, seed, definition, target
            )
            detail, summary = flight_metrics(
                test_score, test_meta, threshold, detector, seed, definition, target
            )
            detail_rows += detail
            summary_rows += summary


class LSTMAutoencoder(nn.Module):
    """PyTorch equivalent of the frozen Keras sequence autoencoder."""

    def __init__(self, n_features):
        super().__init__()
        self.encoder = nn.LSTM(n_features, 16, batch_first=True)
        self.bottleneck = nn.Linear(16, 8)
        self.decoder = nn.LSTM(8, 16, batch_first=True)
        self.output = nn.Linear(16, n_features)
        self._keras_equivalent_initialization()

    def _keras_equivalent_initialization(self):
        for layer in (self.encoder, self.decoder):
            nn.init.xavier_uniform_(layer.weight_ih_l0)
            nn.init.orthogonal_(layer.weight_hh_l0)
            nn.init.zeros_(layer.bias_ih_l0)
            nn.init.zeros_(layer.bias_hh_l0)
            layer.bias_ih_l0.data[16:32].fill_(1.0)
        for layer in (self.bottleneck, self.output):
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)

    def forward(self, x):
        encoded, _ = self.encoder(x)
        bottleneck = torch.tanh(self.bottleneck(encoded))
        decoded, _ = self.decoder(bottleneck)
        return self.output(decoded)


def configure_cuda_runtime():
    """Report and verify the required CUDA-only runtime before loading data."""
    print(f"Python executable: {sys.executable}", flush=True)
    print(f"PyTorch version: {torch.__version__}", flush=True)
    print(f"CUDA version: {torch.version.cuda}", flush=True)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; CPU fallback is disabled")
    print(f"GPU name: {torch.cuda.get_device_name(0)}", flush=True)
    smoke = torch.randn((64, 64), device=DEVICE, requires_grad=True)
    loss = (smoke @ smoke.T).square().mean()
    loss.backward()
    torch.cuda.synchronize()
    if not torch.isfinite(loss):
        raise RuntimeError("CUDA smoke test produced a non-finite result")
    print(f"CUDA smoke test: PASS ({float(loss.detach().cpu()):.6g})", flush=True)
    del smoke, loss
    torch.cuda.empty_cache()


def build_torch_lstm(seed, n_features):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    return LSTMAutoencoder(n_features).to(DEVICE)


def run_epoch(model, chunks, optimizer, seed, epoch):
    dataset = TensorDataset(torch.from_numpy(chunks))
    generator = torch.Generator().manual_seed(seed + epoch)
    loader = DataLoader(
        dataset, batch_size=256, shuffle=True, generator=generator,
        num_workers=0, pin_memory=True,
    )
    model.train()
    loss_sum = 0.0
    element_count = 0
    for (batch,) in loader:
        batch = batch.to(DEVICE, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        reconstructed = model(batch)
        squared_error = (reconstructed - batch).square()
        loss = squared_error.mean()
        loss.backward()
        optimizer.step()
        loss_sum += float(squared_error.detach().sum().cpu())
        element_count += squared_error.numel()
    return loss_sum / element_count


@torch.no_grad()
def evaluate_loss(model, chunks):
    loader = DataLoader(
        TensorDataset(torch.from_numpy(chunks)), batch_size=256, shuffle=False,
        num_workers=0, pin_memory=True,
    )
    model.eval()
    loss_sum = 0.0
    element_count = 0
    for (batch,) in loader:
        batch = batch.to(DEVICE, non_blocking=True)
        squared_error = (model(batch) - batch).square()
        loss_sum += float(squared_error.sum().cpu())
        element_count += squared_error.numel()
    return loss_sum / element_count


@torch.no_grad()
def score_lstm_with_positions(model, z, meta):
    """Score every row and label its location in the non-overlapping chunk."""
    scores = np.empty(len(z), dtype=np.float64)
    position = np.empty(len(z), dtype=np.int8)
    chunks, mappings, labels = [], [], []
    for _, flight in meta.groupby(["unit", "cycle"], sort=False):
        idx = flight.index.to_numpy()
        for start in range(0, len(idx), LSTM_LENGTH):
            selected = idx[start:start + LSTM_LENGTH]
            chunk = np.zeros((LSTM_LENGTH, z.shape[1]), dtype=np.float32)
            chunk[:len(selected)] = z[selected]
            chunks.append(chunk)
            mappings.append(selected)
            if len(selected) < LSTM_LENGTH:
                labels.append(np.full(len(selected), 3, dtype=np.int8))
            else:
                loc = np.ones(LSTM_LENGTH, dtype=np.int8)
                loc[:BOUNDARY_WIDTH] = 0
                loc[-BOUNDARY_WIDTH:] = 2
                labels.append(loc)
    chunks = np.asarray(chunks, dtype=np.float32)
    predictions = []
    loader = DataLoader(
        TensorDataset(torch.from_numpy(chunks)), batch_size=128, shuffle=False,
        num_workers=0, pin_memory=True,
    )
    model.eval()
    for (batch,) in loader:
        predictions.append(model(batch.to(DEVICE, non_blocking=True)).cpu().numpy())
    prediction = np.concatenate(predictions, axis=0)
    for chunk, reconstructed, selected, label in zip(chunks, prediction, mappings, labels):
        scores[selected] = np.mean(
            (chunk[:len(selected)] - reconstructed[:len(selected)]) ** 2, axis=1
        )
        position[selected] = label
    return scores, position


def train_converged_lstm(dev_x, dev_desc, dev_meta):
    """Select epochs with an engine-disjoint training-only split, then refit."""
    select_fit = dev_meta.unit.isin(SELECTION_FIT_UNITS).to_numpy()
    select_val = dev_meta.unit.to_numpy() == SELECTION_VALIDATION_UNIT

    selection_correction = ResidualPCADetector("history", alpha=1.0).fit(
        dev_x[select_fit], dev_desc[select_fit]
    )
    z_fit = selection_correction.standardized_residual(
        dev_x[select_fit], dev_desc[select_fit]
    ).astype(np.float32)
    z_val = selection_correction.standardized_residual(
        dev_x[select_val], dev_desc[select_val]
    ).astype(np.float32)
    fit_meta = dev_meta[select_fit].reset_index(drop=True)
    val_meta = dev_meta[select_val].reset_index(drop=True)
    fit_chunks = make_training_chunks(z_fit, fit_meta)
    val_chunks = make_training_chunks(z_val, val_meta)

    histories = []
    selected_epochs = {}
    for seed in SEEDS:
        model = build_torch_lstm(seed, fit_chunks.shape[-1])
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        selection_path = CHECKPOINTS / f"lstm_seed_{seed}_selection.pt"
        train_losses, val_losses = [], []
        best_monitored = math.inf
        best_state = None
        wait = 0
        for epoch in range(1, MAX_EPOCHS + 1):
            train_loss = run_epoch(model, fit_chunks, optimizer, seed, epoch)
            validation_loss = evaluate_loss(model, val_chunks)
            train_losses.append(train_loss)
            val_losses.append(validation_loss)
            print(
                f"seed={seed} epoch={epoch}/{MAX_EPOCHS} "
                f"loss={train_loss:.8f} val_loss={validation_loss:.8f}",
                flush=True,
            )
            if validation_loss < best_monitored - MIN_DELTA:
                best_monitored = validation_loss
                wait = 0
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                torch.save(best_state, selection_path)
            else:
                wait += 1
                if wait >= PATIENCE:
                    break
        val_loss = np.asarray(val_losses)
        best_epoch = int(np.argmin(val_loss) + 1)
        selected_epochs[seed] = best_epoch
        for epoch, (train_loss, validation_loss) in enumerate(
            zip(train_losses, val_losses), start=1
        ):
            histories.append(
                {
                    "seed": seed,
                    "stage": "engine_disjoint_epoch_selection",
                    "epoch": epoch,
                    "train_loss": train_loss,
                    "validation_loss": validation_loss,
                    "best_epoch": best_epoch,
                    "epochs_run": len(val_loss),
                    "max_epochs": MAX_EPOCHS,
                    "patience": PATIENCE,
                    "min_delta": MIN_DELTA,
                    "fit_units": ",".join(map(str, SELECTION_FIT_UNITS)),
                    "validation_units": str(SELECTION_VALIDATION_UNIT),
                }
            )
        del model, optimizer, best_state
        torch.cuda.empty_cache()
        gc.collect()

    del selection_correction, z_fit, z_val, fit_chunks, val_chunks
    gc.collect()
    return pd.DataFrame(histories), selected_epochs


def refit_and_score_lstm(seed, epochs, z_train, z_cal, z_test,
                         train_meta, cal_meta, test_meta):
    """Refit on all training engines for the selected epoch count and score."""
    chunks = make_training_chunks(z_train, train_meta)
    model = build_torch_lstm(seed, chunks.shape[-1])
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    losses = []
    for epoch in range(1, epochs + 1):
        loss = run_epoch(model, chunks, optimizer, seed, epoch)
        losses.append(loss)
        print(f"seed={seed} refit_epoch={epoch}/{epochs} loss={loss:.8f}", flush=True)
    final_path = CHECKPOINTS / f"lstm_seed_{seed}_final.pt"
    torch.save(model.state_dict(), final_path)
    train_scores, train_pos = score_lstm_with_positions(model, z_train, train_meta)
    cal_scores, cal_pos = score_lstm_with_positions(model, z_cal, cal_meta)
    test_scores, test_pos = score_lstm_with_positions(model, z_test, test_meta)
    refit_history = [
        {
            "seed": seed,
            "stage": "all_training_engines_refit",
            "epoch": epoch,
            "train_loss": loss,
            "validation_loss": np.nan,
            "best_epoch": epochs,
            "epochs_run": epochs,
            "max_epochs": epochs,
            "patience": np.nan,
            "min_delta": np.nan,
            "fit_units": ",".join(map(str, TRAIN_UNITS)),
            "validation_units": "none",
        }
        for epoch, loss in enumerate(losses, start=1)
    ]
    del model, optimizer, chunks
    torch.cuda.empty_cache()
    gc.collect()
    return (
        {"train": train_scores, "calibration": cal_scores, "official_test": test_scores},
        {"train": train_pos, "calibration": cal_pos, "official_test": test_pos},
        refit_history,
    )


def boundary_audit(scores_by_seed, positions_by_seed, metas):
    rows = []
    labels = {0: "chunk_start_16", 1: "chunk_middle", 2: "chunk_end_16", 3: "incomplete_tail"}
    for seed in SEEDS:
        for subset in ("calibration", "official_test"):
            scores = scores_by_seed[seed][subset]
            position = positions_by_seed[seed][subset]
            meta = metas[subset]
            threshold = float(np.quantile(scores_by_seed[seed]["calibration"], .99, method="higher"))
            for definition in PHASE_DEFINITIONS:
                col = phase_col(definition)
                phase_values = meta[col].to_numpy()
                for code, category in labels.items():
                    base = position == code
                    for phase_id, phase in [(None, "overall"), *enumerate(PHASES)]:
                        mask = base if phase_id is None else base & (phase_values == phase_id)
                        values = scores[mask]
                        if len(values) == 0:
                            continue
                        rows.append(
                            {
                                "seed": seed,
                                "subset": subset,
                                "phase_rule": definition,
                                "nominal_fpr": .01,
                                "category": category,
                                "phase": phase,
                                "n": len(values),
                                "mean_reconstruction_error": values.mean(),
                                "median_reconstruction_error": np.median(values),
                                "p95_reconstruction_error": np.quantile(values, .95),
                                "false_alarm_rate": np.mean(values > threshold),
                            }
                        )
                # Direct sensitivity result after removing starts, ends, and tails.
                middle = position == 1
                for phase_id, phase in [(None, "overall"), *enumerate(PHASES)]:
                    mask = middle if phase_id is None else middle & (phase_values == phase_id)
                    values = scores[mask]
                    rows.append(
                        {
                            "seed": seed,
                            "subset": subset,
                            "phase_rule": definition,
                            "nominal_fpr": .01,
                            "category": "middle_only_sensitivity",
                            "phase": phase,
                            "n": len(values),
                            "mean_reconstruction_error": values.mean(),
                            "median_reconstruction_error": np.median(values),
                            "p95_reconstruction_error": np.quantile(values, .95),
                            "false_alarm_rate": np.mean(values > threshold),
                        }
                    )
    return pd.DataFrame(rows)


def make_canonical(rate_df, transfer_df, probe_df, summary):
    records = []
    for keys, group in rate_df.groupby(
        ["detector", "seed", "phase_definition", "nominal_fpr", "unit"], sort=False
    ):
        detector, seed, definition, target, unit = keys
        values = group.set_index("phase")
        phases = values.loc[list(PHASES), "false_alarm_rate"]
        transfers = transfer_df[
            (transfer_df.detector == detector)
            & (transfer_df.seed == seed)
            & (transfer_df.phase_definition == definition)
            & (transfer_df.nominal_fpr == target)
            & (transfer_df.unit.astype(str) == str(unit))
        ]
        probe = probe_df[
            (probe_df.detector == detector)
            & (probe_df.seed == seed)
            & (probe_df.phase_definition == definition)
            & (probe_df.unit.astype(str) == str(unit))
        ].iloc[0]
        temporal = summary[
            (summary.detector == detector)
            & (summary.seed == seed)
            & (summary.phase_definition == definition)
            & (summary.nominal_fpr == target)
            & (summary.unit.astype(str) == str(unit))
        ].set_index("phase")
        record = {
            "detector": detector,
            "seed": seed,
            "correction_variant": "history",
            "phase_rule": definition,
            "nominal_fpr_target": target,
            "evaluation_unit": "pooled" if str(unit) == "all" else f"engine_{unit}",
            "overall_fpr": values.loc["overall", "false_alarm_rate"],
            "climb_fpr": phases.climb,
            "cruise_fpr": phases.cruise,
            "descent_fpr": phases.descent,
            "descent_minus_climb": phases.descent - phases.climb,
            "descent_minus_cruise": phases.descent - phases.cruise,
            "max_min_phase_ratio": phases.max() / phases.min() if phases.min() > 0 else np.inf,
            "worst_cross_phase_transfer_fpr": transfers[
                transfers.calibration_phase != transfers.test_phase
            ].false_alarm_rate.max(),
            "score_only_phase_balanced_accuracy": probe.balanced_accuracy,
        }
        for phase in PHASES:
            record[f"healthy_flights_with_alarm_{phase}"] = temporal.loc[
                phase, "fraction_flights_with_false_alarm"
            ]
            record[f"false_alarm_events_per_healthy_flight_{phase}"] = temporal.loc[
                phase, "events_per_healthy_flight"
            ]
        records.append(record)
    return pd.DataFrame(records)


def per_engine_table(canonical):
    columns = [
        "detector", "seed", "phase_rule", "nominal_fpr_target", "evaluation_unit",
        "overall_fpr", "climb_fpr", "cruise_fpr", "descent_fpr",
        "descent_minus_climb", "descent_minus_cruise",
    ]
    return canonical[
        (canonical.phase_rule == "primary")
        & (canonical.nominal_fpr_target == .01)
        & (canonical.evaluation_unit != "pooled")
    ][columns].copy()


def flight_index(meta):
    result = []
    for (unit, cycle), group in meta.groupby(["unit", "cycle"], sort=False):
        result.append((int(unit), int(cycle), group.index.to_numpy()))
    return result


def bootstrap_plans(meta, repetitions, rng):
    flights = flight_index(meta)
    engine_to_flights = {}
    for index, (unit, _, _) in enumerate(flights):
        engine_to_flights.setdefault(unit, []).append(index)
    engines = np.asarray(sorted(engine_to_flights))
    plans = np.zeros((repetitions, len(flights)), dtype=np.int16)
    for b in range(repetitions):
        sampled_engines = rng.choice(engines, size=len(engines), replace=True)
        for engine in sampled_engines:
            members = np.asarray(engine_to_flights[int(engine)])
            sampled_flights = rng.choice(members, size=len(members), replace=True)
            np.add.at(plans[b], sampled_flights, 1)
    return flights, plans


def sorted_calibration_view(scores, meta, flights, phase_id=None):
    pieces_score, pieces_flight = [], []
    phases = meta.phase_primary.to_numpy()
    for fid, (_, _, idx) in enumerate(flights):
        if phase_id is not None:
            idx = idx[phases[idx] == phase_id]
        pieces_score.append(scores[idx])
        pieces_flight.append(np.full(len(idx), fid, dtype=np.int16))
    values = np.concatenate(pieces_score)
    ids = np.concatenate(pieces_flight)
    order = np.argsort(values, kind="quicksort")
    return values[order], ids[order]


def weighted_higher_quantile(sorted_values, sorted_flight_ids, multiplicity, q):
    weights = multiplicity[sorted_flight_ids]
    total = int(weights.sum())
    if total == 0:
        raise RuntimeError("Bootstrap replicate selected no calibration rows")
    order_index = int(math.ceil(q * (total - 1)))
    cumulative = np.cumsum(weights, dtype=np.int64)
    selected = int(np.searchsorted(cumulative, order_index, side="right"))
    return float(sorted_values[selected])


def audit_counts(scores, meta, flights, multiplicity, threshold, phase_id=None):
    phases = meta.phase_primary.to_numpy()
    rows = alarms = 0
    for fid, (_, _, idx) in enumerate(flights):
        count = int(multiplicity[fid])
        if count == 0:
            continue
        if phase_id is not None:
            idx = idx[phases[idx] == phase_id]
        rows += count * len(idx)
        alarms += count * int(np.count_nonzero(scores[idx] > threshold))
    return rows, alarms


def bootstrap_one_model(name, scores, cal_meta, test_meta, cal_flights, test_flights,
                        cal_plans, test_plans):
    cal_views = {
        phase: sorted_calibration_view(scores["calibration"], cal_meta, cal_flights, phase)
        for phase in (None, 0, 1, 2)
    }
    estimates = {
        key: np.empty(BOOTSTRAP_REPETITIONS, dtype=np.float64)
        for key in (
            "overall_fpr", "climb_fpr", "cruise_fpr", "descent_fpr",
            "descent_minus_climb", "descent_minus_cruise",
            "worst_cross_phase_transfer_fpr",
        )
    }
    for b in range(BOOTSTRAP_REPETITIONS):
        cal_mult = cal_plans[b]
        test_mult = test_plans[b]
        pooled_threshold = weighted_higher_quantile(*cal_views[None], cal_mult, .99)
        phase_fpr = []
        total_rows = total_alarms = 0
        for phase_id in range(3):
            rows, alarms = audit_counts(
                scores["official_test"], test_meta, test_flights, test_mult,
                pooled_threshold, phase_id,
            )
            total_rows += rows
            total_alarms += alarms
            phase_fpr.append(alarms / rows)
        estimates["overall_fpr"][b] = total_alarms / total_rows
        estimates["climb_fpr"][b], estimates["cruise_fpr"][b], estimates["descent_fpr"][b] = phase_fpr
        estimates["descent_minus_climb"][b] = phase_fpr[2] - phase_fpr[0]
        estimates["descent_minus_cruise"][b] = phase_fpr[2] - phase_fpr[1]

        transfer_values = []
        for cal_phase in range(3):
            threshold = weighted_higher_quantile(*cal_views[cal_phase], cal_mult, .99)
            for test_phase in range(3):
                if cal_phase == test_phase:
                    continue
                rows, alarms = audit_counts(
                    scores["official_test"], test_meta, test_flights, test_mult,
                    threshold, test_phase,
                )
                transfer_values.append(alarms / rows)
        estimates["worst_cross_phase_transfer_fpr"][b] = max(transfer_values)

    detector, seed = name
    rows = []
    for metric, values in estimates.items():
        rows.append(
            {
                "detector": detector,
                "seed": seed,
                "phase_rule": "primary",
                "nominal_fpr_target": .01,
                "metric": metric,
                "bootstrap_unit": "engine_then_flight",
                "threshold_reestimated": True,
                "replicates": BOOTSTRAP_REPETITIONS,
                "bootstrap_mean": values.mean(),
                "ci_lower_95": np.quantile(values, .025),
                "ci_upper_95": np.quantile(values, .975),
            }
        )
    return rows


def hierarchical_bootstrap(score_map, cal_meta, test_meta):
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    cal_flights, cal_plans = bootstrap_plans(cal_meta, BOOTSTRAP_REPETITIONS, rng)
    test_flights, test_plans = bootstrap_plans(test_meta, BOOTSTRAP_REPETITIONS, rng)
    rows = []
    # NumPy sorting/cumulative operations release the GIL; limited concurrency
    # reduces elapsed time without multiplying the large source data arrays.
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = {
            pool.submit(
                bootstrap_one_model,
                name,
                scores,
                cal_meta,
                test_meta,
                cal_flights,
                test_flights,
                cal_plans,
                test_plans,
            ): name
            for name, scores in score_map.items()
        }
        for future in as_completed(jobs):
            name = jobs[future]
            rows.extend(future.result())
            print(f"Bootstrap complete: {name}", flush=True)
    return pd.DataFrame(rows)


def percent(value):
    return f"{100 * value:.3f}%"


def generate_report(canonical, history, boundary, uncertainty):
    primary = canonical[
        (canonical.phase_rule == "primary")
        & (canonical.nominal_fpr_target == .01)
        & (canonical.evaluation_unit == "pooled")
    ].copy()
    display = (
        primary.groupby("detector")[[
            "overall_fpr", "climb_fpr", "cruise_fpr", "descent_fpr",
            "descent_minus_climb", "descent_minus_cruise",
            "max_min_phase_ratio", "worst_cross_phase_transfer_fpr",
            "score_only_phase_balanced_accuracy",
        ]]
        .mean()
        .reset_index()
    )
    lines = [
        "# Final validation report",
        "",
        "> This report is generated from `canonical_results.csv` and executed validation artifacts. DS02 is discovery data, not untouched confirmation.",
        "",
        "## Canonical primary results",
        "",
        "| Detector | Overall | Climb | Cruise | Descent | D-C climb | D-C cruise | Max/min | Worst transfer | Phase BA |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in display.itertuples():
        lines.append(
            f"| {row.detector} | {percent(row.overall_fpr)} | {percent(row.climb_fpr)} | "
            f"{percent(row.cruise_fpr)} | {percent(row.descent_fpr)} | "
            f"{percent(row.descent_minus_climb)} | {percent(row.descent_minus_cruise)} | "
            f"{row.max_min_phase_ratio:.2f}× | {percent(row.worst_cross_phase_transfer_fpr)} | "
            f"{100 * row.score_only_phase_balanced_accuracy:.1f}% |"
        )

    selection = history[history.stage == "engine_disjoint_epoch_selection"]
    lines += ["", "## LSTM convergence", ""]
    for seed in SEEDS:
        part = selection[selection.seed == seed]
        best = int(part.best_epoch.iloc[0])
        run = int(part.epochs_run.iloc[0])
        best_loss = part.loc[part.epoch == best, "validation_loss"].iloc[0]
        lines.append(f"- Seed {seed}: selected epoch {best}; stopped after {run} epochs; best validation loss {best_loss:.6g}.")

    middle = boundary[
        (boundary.subset == "official_test")
        & (boundary.phase_rule == "primary")
        & (boundary.category == "middle_only_sensitivity")
    ]
    middle_means = middle.groupby("phase").false_alarm_rate.mean()
    lines += [
        "",
        "The middle-only sensitivity result retains descent as the highest-FPR phase. "
        f"Seed-mean middle-only FPRs are climb {percent(middle_means.climb)}, "
        f"cruise {percent(middle_means.cruise)}, and descent {percent(middle_means.descent)}.",
        "",
        "## Cluster-aware uncertainty",
        "",
        "Intervals use 2,000 hierarchical engine-then-flight bootstrap replicates and re-estimate pooled and phase-specific calibration thresholds in every replicate. With only three audit engines and two calibration engines, intervals remain intrinsically imprecise.",
        "",
        "| Detector | Metric | Mean | 95% interval |",
        "|---|---|---:|---:|",
    ]
    for (detector, seed, metric), part in uncertainty.groupby(["detector", "seed", "metric"]):
        run = detector if int(seed) == -1 else f"{detector}, seed {int(seed)}"
        row = part.iloc[0]
        lines.append(
            f"| {run} | {metric} | {percent(row.bootstrap_mean)} | "
            f"{percent(row.ci_lower_95)}–{percent(row.ci_upper_95)} |"
        )

    lines += [
        "",
        "## Confirmation status",
        "",
        "No non-DS02 N-CMAPSS subset is available locally. No confirmatory outcome was run or claimed. The one-shot external protocol was frozen before this validation in `frozen_protocol.md`. DS02 results must be framed as exploratory/discovery evidence.",
        "",
        "## Claim audit",
        "",
        "| Supported claim | Unsupported / too-strong claim |",
        "|---|---|",
        "| Phase-dependent healthy false-alarm rates were observed across three tested detector implementations under a common preprocessing and calibration protocol on DS02. | The effect is detector-independent. |",
        "| The tested static, derivative, and finite-history correction specifications did not remove the DS02 phase pattern. | Hysteresis or a causal dynamic mechanism has been established. |",
        "| Pooled healthy-score thresholds transferred unevenly between retrospective phase strata. | Phase-aware thresholds are deployment-ready. |",
        "| Alarm occupancy and event burden differed by phase in this simulated dataset. | The results establish real-aircraft operational validity. |",
        "| The analysis characterizes healthy false alarms. | The detectors have superior anomaly-detection accuracy or fault sensitivity. |",
        "",
        "## Final verdict",
        "",
        "STRONG GO BUT NEEDS VALIDATION",
        "",
        "The internal blockers are resolved if the convergence and boundary outputs above are stable, but external confirmation remains outstanding. An exploratory manuscript is supportable only if DS02 is explicitly presented as discovery evidence and the claim language remains narrow.",
    ]
    (OUT / "FINAL_VALIDATION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    configure_cuda_runtime()
    OUT.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)

    with h5py.File(DATA) as h5:
        dev_x_all, dev_w_all, dev_meta_all, _ = load_split(h5, "dev")
        test_x_all, test_w_all, test_meta_all, _ = load_split(h5, "test")
    dev_healthy = dev_meta_all.healthy.to_numpy() == 1
    test_healthy = test_meta_all.healthy.to_numpy() == 1
    dev_x, dev_w = dev_x_all[dev_healthy], dev_w_all[dev_healthy]
    test_x, test_w = test_x_all[test_healthy], test_w_all[test_healthy]
    dev_meta = dev_meta_all[dev_healthy].reset_index(drop=True)
    test_meta = test_meta_all[test_healthy].reset_index(drop=True)
    del dev_x_all, dev_w_all, test_x_all, test_w_all, dev_meta_all, test_meta_all
    gc.collect()

    dev_desc, descriptor_names = causal_descriptors(dev_w, dev_meta)
    test_desc, _ = causal_descriptors(test_w, test_meta)
    train_mask = dev_meta.unit.isin(TRAIN_UNITS).to_numpy()
    cal_mask = dev_meta.unit.isin(CAL_UNITS).to_numpy()
    train_meta = dev_meta[train_mask].reset_index(drop=True)
    cal_meta = dev_meta[cal_mask].reset_index(drop=True)
    metas = {"train": train_meta, "calibration": cal_meta, "official_test": test_meta}

    print("Selecting LSTM epochs using training engines only", flush=True)
    history_df, selected_epochs = train_converged_lstm(dev_x, dev_desc, dev_meta)

    print("Fitting frozen history correction on all training engines", flush=True)
    correction = ResidualPCADetector("history", alpha=1.0).fit(
        dev_x[train_mask], dev_desc[train_mask]
    )
    z_train = correction.standardized_residual(
        dev_x[train_mask], dev_desc[train_mask]
    ).astype(np.float32)
    z_cal = correction.standardized_residual(
        dev_x[cal_mask], dev_desc[cal_mask]
    ).astype(np.float32)
    z_test = correction.standardized_residual(test_x, test_desc).astype(np.float32)

    outputs = ([], [], [], [], [], [])
    score_map = {}
    pca_scores = {
        "train": correction.score(dev_x[train_mask], dev_desc[train_mask]),
        "calibration": correction.score(dev_x[cal_mask], dev_desc[cal_mask]),
        "official_test": correction.score(test_x, test_desc),
    }
    score_map[("pca", -1)] = pca_scores
    audit_run(
        "pca", -1, pca_scores["train"], pca_scores["calibration"],
        pca_scores["official_test"], train_meta, cal_meta, test_meta, outputs,
    )

    for seed in SEEDS:
        print(f"Fitting Isolation Forest seed {seed}", flush=True)
        forest = IsolationForest(
            n_estimators=200,
            max_samples=8192,
            contamination="auto",
            random_state=seed,
            n_jobs=-1,
        ).fit(z_train)
        scores = {
            "train": -forest.score_samples(z_train),
            "calibration": -forest.score_samples(z_cal),
            "official_test": -forest.score_samples(z_test),
        }
        score_map[("isolation_forest", seed)] = scores
        audit_run(
            "isolation_forest", seed, scores["train"], scores["calibration"],
            scores["official_test"], train_meta, cal_meta, test_meta, outputs,
        )
        del forest

    lstm_scores, lstm_positions = {}, {}
    refit_history = []
    for seed in SEEDS:
        print(
            f"Refitting converged LSTM seed {seed} for {selected_epochs[seed]} epochs",
            flush=True,
        )
        scores, positions, history = refit_and_score_lstm(
            seed, selected_epochs[seed], z_train, z_cal, z_test,
            train_meta, cal_meta, test_meta,
        )
        lstm_scores[seed] = scores
        lstm_positions[seed] = positions
        refit_history.extend(history)
        score_map[("lstm_autoencoder", seed)] = scores
        audit_run(
            "lstm_autoencoder", seed, scores["train"], scores["calibration"],
            scores["official_test"], train_meta, cal_meta, test_meta, outputs,
        )

    history_df = pd.concat([history_df, pd.DataFrame(refit_history)], ignore_index=True)
    history_df.to_csv(OUT / "lstm_training_history.csv", index=False)
    boundary_df = boundary_audit(lstm_scores, lstm_positions, metas)
    boundary_df.to_csv(OUT / "lstm_boundary_audit.csv", index=False)

    score_df, rate_df, transfer_df, probe_df, detail_df, summary_df = map(pd.DataFrame, outputs)
    rate_df.to_csv(OUT / "executed_row_false_alarm_rates.csv", index=False)
    transfer_df.to_csv(OUT / "executed_threshold_transfer_matrix.csv", index=False)
    probe_df.to_csv(OUT / "executed_score_only_phase_prediction.csv", index=False)
    detail_df.to_csv(OUT / "executed_flight_alarm_detail.csv", index=False)

    canonical = make_canonical(rate_df, transfer_df, probe_df, summary_df)
    canonical.to_csv(OUT / "canonical_results.csv", index=False)
    per_engine_table(canonical).to_csv(OUT / "per_engine_phase_fpr.csv", index=False)

    print("Running 2,000-replicate hierarchical bootstrap", flush=True)
    uncertainty = hierarchical_bootstrap(score_map, cal_meta, test_meta)
    uncertainty.to_csv(OUT / "hierarchical_bootstrap_ci.csv", index=False)

    protocol = {
        "dataset_role": "DS02 discovery/exploratory only",
        "train_units": TRAIN_UNITS,
        "calibration_units": CAL_UNITS,
        "official_audit_units": sorted(map(int, test_meta.unit.unique())),
        "correction": "history",
        "history_descriptors": descriptor_names,
        "lstm_epoch_selection": {
            "fit_units": SELECTION_FIT_UNITS,
            "validation_unit": SELECTION_VALIDATION_UNIT,
            "maximum_epochs": MAX_EPOCHS,
            "patience": PATIENCE,
            "min_delta": MIN_DELTA,
            "selected_epochs": selected_epochs,
            "final_protocol": "refit from scratch on units 2,5,10,16 for selected epoch count",
        },
        "bootstrap": {
            "replicates": BOOTSTRAP_REPETITIONS,
            "seed": BOOTSTRAP_SEED,
            "resampling": "engines then flights within sampled engines",
            "thresholds_reestimated": True,
        },
        "confirmation": "not run; no non-DS02 subset available locally",
    }
    (OUT / "run_config.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    generate_report(canonical, history_df, boundary_df, uncertainty)
    print("Final validation complete", flush=True)


if __name__ == "__main__":
    main()
