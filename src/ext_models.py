"""Detector fitting, saving, loading and scoring for the extension (protocol section 4).

Frozen components are imported unchanged:
- the history correction and PCA (`phase3_dynamic.ResidualPCADetector`) and `causal_descriptors`;
- the LSTM architecture, training epoch, loss and scoring (`final_validation`);
- the healthy-block loader (`mssp_mitigation.load_selected_rows`).

The LSTM epoch-selection and refit loops are re-implemented here only because the frozen versions in
`confirm_frozen_ds03` write checkpoints into the frozen DS03 directory. A test checks that they are
equal to the frozen loop on synthetic data.
"""

from __future__ import annotations

import gc
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import IsolationForest

import ext_common as ec
import ext_cvae
import final_validation as fv
import mssp_mitigation as mm
from phase3_dynamic import ResidualPCADetector, causal_descriptors
from second_stage_audit import SENSORS

IF_TREES, IF_MAX_SAMPLES = 200, 8192


# ---------------------------------------------------------------------------
# Loading (healthy development blocks; audit rows only through the gated Phase A)
# ---------------------------------------------------------------------------

@dataclass
class Rows:
    x: np.ndarray
    w: np.ndarray
    meta: pd.DataFrame
    blocks: list
    descriptors: np.ndarray = None
    descriptor_names: list = field(default_factory=list)


def _finish(x, w, meta, blocks, expected_units, label):
    if not (np.isfinite(x).all() and np.isfinite(w).all()):
        raise ec.ExtensionError(f"{label}: non-finite sensor or operating values (stop rule)")
    found = set(int(u) for u in np.unique(meta.unit))
    if found != set(expected_units):
        raise ec.ExtensionError(f"{label}: loaded engines {sorted(found)} differ from roles {sorted(expected_units)}")
    descriptors, names = causal_descriptors(w, meta)
    return Rows(x, w, meta, blocks, descriptors, names)


def load_development_healthy(subset):
    """hs = 1 rows of the fit and calibration pools only; audit engines are never touched."""
    units = np.asarray(sorted(set(subset.fit) | set(subset.calibration)), dtype=np.int64)
    if set(units.tolist()) & set(subset.audit):
        raise ec.ExtensionError(f"{subset.key}: an audit engine is in the development selection")

    def select(a):
        return (a[:, 3].astype(np.int8) == 1) & np.isin(a[:, 0].astype(np.int64), units)

    with h5py.File(subset.path, "r") as h5:
        x, w, meta, blocks = mm.load_selected_rows(subset.mm_key, h5, "dev", select)
    return _finish(x, w, meta, blocks, units, f"{subset.key} development")


def load_audit_rows(subset, *, healthy_only=False):
    """All (or healthy-only) official-test rows of the audit engines. Callers must hold a verified lock."""
    units = np.asarray(sorted(subset.audit), dtype=np.int64)

    def select(a):
        mask = np.isin(a[:, 0].astype(np.int64), units)
        return mask & (a[:, 3].astype(np.int8) == 1) if healthy_only else mask

    with h5py.File(subset.path, "r") as h5:
        x, w, meta, blocks = mm.load_selected_rows(subset.mm_key, h5, "test", select)
    return _finish(x, w, meta, blocks, units, f"{subset.key} audit")


def subset_rows(rows, units):
    mask = rows.meta.unit.isin(units).to_numpy()
    return Rows(rows.x[mask], rows.w[mask], rows.meta[mask].reset_index(drop=True), [], rows.descriptors[mask],
                rows.descriptor_names)


# ---------------------------------------------------------------------------
# LSTM: frozen architecture and training step; loops mirror confirm_frozen_ds03
# ---------------------------------------------------------------------------

def select_lstm_epochs(x, descriptors, meta, fit_units, validation_unit, checkpoint_dir, seeds=ec.SEEDS,
                       max_epochs=fv.MAX_EPOCHS, patience=fv.PATIENCE, min_delta=fv.MIN_DELTA, log=print):
    """Mirror of `confirm_frozen_ds03.select_lstm_epochs`, writing checkpoints to the extension directory."""
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    fit_mask = meta.unit.isin(fit_units).to_numpy()
    val_mask = meta.unit.to_numpy() == validation_unit
    correction = ResidualPCADetector("history", alpha=1.0).fit(x[fit_mask], descriptors[fit_mask])
    z_fit = correction.standardized_residual(x[fit_mask], descriptors[fit_mask]).astype(np.float32)
    z_val = correction.standardized_residual(x[val_mask], descriptors[val_mask]).astype(np.float32)
    fit_chunks = fv.make_training_chunks(z_fit, meta[fit_mask].reset_index(drop=True))
    val_chunks = fv.make_training_chunks(z_val, meta[val_mask].reset_index(drop=True))
    rows, selected = [], {}
    for seed in seeds:
        model = fv.build_torch_lstm(seed, len(SENSORS))
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        train_losses, val_losses = [], []
        best_monitored, wait = float("inf"), 0
        for epoch in range(1, max_epochs + 1):
            train_loss = fv.run_epoch(model, fit_chunks, optimizer, seed, epoch)
            val_loss = fv.evaluate_loss(model, val_chunks)
            if not (np.isfinite(train_loss) and np.isfinite(val_loss)):
                raise ec.ExtensionError(f"Non-finite LSTM loss at seed {seed}, epoch {epoch} (stop rule)")
            train_losses.append(train_loss)
            val_losses.append(val_loss)
            if epoch == 1 or epoch % 20 == 0:
                log(f"lstm selection seed={seed} epoch={epoch} loss={train_loss:.7f} val_loss={val_loss:.7f}")
            if val_loss < best_monitored - min_delta:
                best_monitored, wait = val_loss, 0
                torch.save({key: value.detach().cpu() for key, value in model.state_dict().items()},
                           checkpoint_dir / f"lstm_seed_{seed}_selection.pt")
            else:
                wait += 1
                if wait >= patience:
                    break
        best_epoch = int(np.argmin(val_losses) + 1)
        selected[seed] = best_epoch
        for epoch, (train_loss, val_loss) in enumerate(zip(train_losses, val_losses), 1):
            rows.append({"detector": "lstm_autoencoder", "seed": seed, "stage": "engine_disjoint_epoch_selection",
                         "epoch": epoch, "train_loss": train_loss, "validation_loss": val_loss,
                         "best_epoch": best_epoch, "epochs_run": len(val_losses), "max_epochs": max_epochs,
                         "patience": patience, "min_delta": min_delta,
                         "fit_units": ",".join(map(str, fit_units)), "validation_units": str(validation_unit)})
        del model, optimizer
        torch.cuda.empty_cache()
    del correction, z_fit, z_val, fit_chunks, val_chunks
    gc.collect()
    return rows, selected


def refit_lstm(seed, epochs, z_train, train_meta, checkpoint_dir, log=print):
    """Mirror of `confirm_frozen_ds03.refit_lstm`, writing to the extension directory."""
    chunks = fv.make_training_chunks(z_train, train_meta)
    model = fv.build_torch_lstm(seed, len(SENSORS))
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    history = []
    for epoch in range(1, epochs + 1):
        loss = fv.run_epoch(model, chunks, optimizer, seed, epoch)
        if not np.isfinite(loss):
            raise ec.ExtensionError(f"Non-finite LSTM refit loss at seed {seed}, epoch {epoch} (stop rule)")
        if epoch == 1 or epoch % 20 == 0 or epoch == epochs:
            log(f"lstm refit seed={seed} epoch={epoch}/{epochs} loss={loss:.7f}")
        history.append((epoch, loss))
    torch.save(model.state_dict(), Path(checkpoint_dir) / f"lstm_seed_{seed}_final.pt")
    rows = [{"detector": "lstm_autoencoder", "seed": seed, "stage": "all_fit_engines_refit", "epoch": epoch,
             "train_loss": loss, "validation_loss": np.nan, "best_epoch": epochs, "epochs_run": epochs,
             "max_epochs": epochs, "patience": np.nan, "min_delta": np.nan,
             "fit_units": ",".join(map(str, sorted(train_meta.unit.unique()))), "validation_units": "none"}
            for epoch, loss in history]
    del chunks, optimizer
    return model, rows


def load_lstm(path, seed):
    model = fv.build_torch_lstm(seed, len(SENSORS))
    model.load_state_dict(torch.load(path, map_location=fv.DEVICE, weights_only=True))
    model.eval()
    return model


# ---------------------------------------------------------------------------
# All detectors
# ---------------------------------------------------------------------------

@dataclass
class Models:
    correction: ResidualPCADetector
    forests: dict
    lstms: dict
    cvaes: dict
    files: dict = field(default_factory=dict)
    selected_epochs: dict = field(default_factory=dict)
    history: list = field(default_factory=list)


def fit_models(subset, dev, model_dir, *, frozen_lstm_dir=None, log=print):
    """Fit every detector on fit-pool healthy rows only (protocol section 4)."""
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    meta = dev.meta
    if set(int(u) for u in meta.unit) & set(subset.audit):
        raise ec.ExtensionError(f"{subset.key}: audit engine in model fitting (stop rule)")
    fit_mask = meta.unit.isin(subset.fit).to_numpy()
    sel_mask = meta.unit.isin(subset.selection_fit).to_numpy()
    val_mask = meta.unit.to_numpy() == subset.validation
    for label, mask in (("fit", fit_mask), ("selection", sel_mask | val_mask)):
        if set(int(u) for u in meta.unit[mask]) & set(subset.calibration):
            raise ec.ExtensionError(f"{subset.key}: calibration engine in {label} rows (stop rule)")
    timings, clock = {}, time.time()
    x_fit, d_fit = dev.x[fit_mask], dev.descriptors[fit_mask]
    train_meta = meta[fit_mask].reset_index(drop=True)
    correction = ResidualPCADetector("history", alpha=1.0).fit(x_fit, d_fit)
    z_fit = correction.standardized_residual(x_fit, d_fit).astype(np.float32)
    forests = {seed: IsolationForest(n_estimators=IF_TREES, max_samples=IF_MAX_SAMPLES, contamination="auto",
                                     random_state=seed, n_jobs=-1).fit(z_fit) for seed in ec.SEEDS}
    timings["correction_pca_iforest_seconds"] = round(time.time() - clock, 1)
    history, selected = [], {}
    clock = time.time()
    if frozen_lstm_dir is None:
        rows, lstm_epochs = select_lstm_epochs(dev.x, dev.descriptors, meta, subset.selection_fit, subset.validation,
                                               model_dir, log=log)
        history += rows
        lstms = {}
        for seed in ec.SEEDS:
            lstms[seed], refit_rows = refit_lstm(seed, lstm_epochs[seed], z_fit, train_meta, model_dir, log=log)
            lstms[seed].eval()
            history += refit_rows
        selected["lstm_autoencoder"] = lstm_epochs
    else:
        lstms = {seed: load_lstm(Path(frozen_lstm_dir) / f"lstm_seed_{seed}_final.pt", seed) for seed in ec.SEEDS}
        selected["lstm_autoencoder"] = "frozen checkpoints loaded"
    timings["lstm_seconds"] = round(time.time() - clock, 1)
    clock = time.time()
    cvaes, cvae_epochs = {}, {}
    for seed in ec.SEEDS:
        epochs, rows = ext_cvae.select_epochs(seed, dev.x[sel_mask], dev.descriptors[sel_mask], dev.x[val_mask],
                                              dev.descriptors[val_mask], log=log)
        for row in rows:
            row.update({"detector": "cvae", "fit_units": ",".join(map(str, subset.selection_fit)),
                        "validation_units": str(subset.validation)})
        history += rows
        fitted, rows = ext_cvae.refit(seed, epochs, x_fit, d_fit, log=log)
        for row in rows:
            row.update({"detector": "cvae", "fit_units": ",".join(map(str, subset.fit)), "validation_units": "none"})
        history += rows
        cvaes[seed], cvae_epochs[seed] = fitted, epochs
    selected["cvae"] = cvae_epochs
    timings["cvae_seconds"] = round(time.time() - clock, 1)
    models = Models(correction, forests, lstms, cvaes, selected_epochs=selected, history=history)
    models.files = save_models(models, model_dir, frozen_lstm=frozen_lstm_dir is not None)
    models.files["timings"] = timings
    return models, z_fit


def save_models(models, model_dir, *, frozen_lstm=False):
    model_dir = Path(model_dir)
    files = {}
    with (model_dir / "correction.pkl").open("xb") as stream:
        pickle.dump(models.correction, stream, protocol=5)
    files["correction"] = "correction.pkl"
    for seed, forest in models.forests.items():
        name = f"isolation_forest_seed_{seed}.pkl"
        with (model_dir / name).open("xb") as stream:
            pickle.dump(forest, stream, protocol=5)
        files[f"isolation_forest:{seed}"] = name
    if not frozen_lstm:
        for seed in models.lstms:
            files[f"lstm_autoencoder:{seed}"] = f"lstm_seed_{seed}_final.pt"
    for seed, fitted in models.cvaes.items():
        name = f"cvae_seed_{seed}_final.pt"
        path = model_dir / name
        if path.exists():
            raise FileExistsError(path)
        torch.save(ext_cvae.state(fitted), path)
        files[f"cvae:{seed}"] = name
    return {key: {"file": name, "sha256": ec.file_digest(model_dir / name)} for key, name in files.items()}


def load_models(model_dir, files, *, frozen_lstm_dir=None):
    model_dir = Path(model_dir)
    for key, entry in files.items():
        if key == "timings":
            continue
        if ec.file_digest(model_dir / entry["file"]) != entry["sha256"]:
            raise ec.ExtensionError(f"Model file hash differs from the lock: {entry['file']} (stop rule)")
    with (model_dir / "correction.pkl").open("rb") as stream:
        correction = pickle.load(stream)
    forests = {}
    for seed in ec.SEEDS:
        with (model_dir / f"isolation_forest_seed_{seed}.pkl").open("rb") as stream:
            forests[seed] = pickle.load(stream)
    source = Path(frozen_lstm_dir) if frozen_lstm_dir else model_dir
    lstms = {seed: load_lstm(source / f"lstm_seed_{seed}_final.pt", seed) for seed in ec.SEEDS}
    cvaes = {seed: ext_cvae.load(torch.load(model_dir / f"cvae_seed_{seed}_final.pt", map_location="cpu",
                                            weights_only=False)) for seed in ec.SEEDS}
    return Models(correction, forests, lstms, cvaes, files=files)


def score_all(models, rows, z=None):
    """Score rows with all 10 runs in protocol order (float64 scores)."""
    if z is None:
        z = models.correction.standardized_residual(rows.x, rows.descriptors).astype(np.float32)
    scores = {("pca", -1): models.correction.score(rows.x, rows.descriptors)}
    for seed in ec.SEEDS:
        scores[("isolation_forest", seed)] = -models.forests[seed].score_samples(z)
    for seed in ec.SEEDS:
        scores[("lstm_autoencoder", seed)], _ = fv.score_lstm_with_positions(models.lstms[seed], z, rows.meta)
    for seed in ec.SEEDS:
        scores[("cvae", seed)] = ext_cvae.score(models.cvaes[seed], rows.x, rows.descriptors)
    for name, values in scores.items():
        if not np.isfinite(values).all():
            raise ec.ExtensionError(f"Non-finite scores for {name} (stop rule)")
    return {name: np.asarray(values, dtype=np.float64) for name, values in scores.items()}


def fingerprints(scores):
    return {ec.run_name(*name): ec.array_fingerprint(values) for name, values in scores.items()}
