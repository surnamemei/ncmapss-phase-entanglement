"""Execute the frozen DS03 external-confirmation protocol once."""

from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import IsolationForest

from final_validation import (
    BOOTSTRAP_REPETITIONS,
    BOOTSTRAP_SEED,
    LSTM_LENGTH,
    MAX_EPOCHS,
    MIN_DELTA,
    PATIENCE,
    PHASES,
    SEEDS,
    TARGETS,
    build_torch_lstm,
    configure_cuda_runtime,
    evaluate_loss,
    flight_metrics,
    hierarchical_bootstrap,
    make_training_chunks,
    row_metrics,
    run_epoch,
    score_lstm_with_positions,
)
from phase3_dynamic import ResidualPCADetector, causal_descriptors
from second_stage_audit import SENSORS, W_NAMES


ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("NCMAPSS_DS03_H5", ROOT / "N-CMAPSS/N-CMAPSS_DS03-012.h5"))
OUT = Path(os.environ.get("NCMAPSS_DS03_RESULTS_DIR", ROOT / "results/confirmation_ds03"))
CHECKPOINTS = OUT / "checkpoints"
ATTEMPT = OUT / "official_test_opened.json"


def primary_phase(alt, units, cycles):
    labels = np.empty(len(alt), dtype=np.int8)
    boundary = np.flatnonzero((np.diff(units) != 0) | (np.diff(cycles) != 0)) + 1
    starts, ends = np.r_[0, boundary], np.r_[boundary, len(alt)]
    for start, end in zip(starts, ends):
        flight_alt = alt[start:end]
        cutoff = flight_alt.min() + .90 * (flight_alt.max() - flight_alt.min())
        cruise = np.flatnonzero(flight_alt >= cutoff)
        first, last = int(cruise[0]), int(cruise[-1])
        labels[start:start + first] = 0
        labels[start + first:start + last + 1] = 1
        labels[start + last + 1:end] = 2
    return labels


def load_primary_split(h5, split):
    a = h5[f"A_{split}"][:]
    w = h5[f"W_{split}"][:]
    x = h5[f"X_s_{split}"][:]
    units, cycles = a[:, 0].astype(np.int16), a[:, 1].astype(np.int16)
    meta = pd.DataFrame({
        "unit": units,
        "cycle": cycles,
        "flight_class": a[:, 2].astype(np.int8),
        "healthy": a[:, 3].astype(np.int8),
        "phase_primary": primary_phase(w[:, 0], units, cycles),
    })
    healthy = meta.healthy.to_numpy() == 1
    return x[healthy], w[healthy], meta[healthy].reset_index(drop=True)


def choose_units(h5):
    dev_units = sorted(map(int, np.unique(h5["A_dev"][:, 0])))
    if len(dev_units) < 4:
        raise RuntimeError("Insufficient development engines for frozen split")
    calibration = dev_units[3::4]
    if len(calibration) < 2:
        calibration = dev_units[-2:]
    fit = [unit for unit in dev_units if unit not in calibration]
    if len(fit) < 2:
        raise RuntimeError("Insufficient fit engines for engine-disjoint validation")
    validation = fit[-1]
    selection_fit = fit[:-1]
    return dev_units, fit, calibration, selection_fit, validation


def preflight():
    """Inspect HDF5 structure only; never materialize dataset array contents."""
    if ATTEMPT.exists():
        raise RuntimeError("The one-shot official-test marker already exists")
    if not DATA.exists():
        raise FileNotFoundError(DATA)
    with h5py.File(DATA) as h5:
        required = (
            "A_dev", "W_dev", "X_s_dev", "A_test", "W_test", "X_s_test",
            "A_var", "W_var", "X_s_var",
        )
        for key in required:
            if key not in h5:
                raise RuntimeError(f"DS03 is missing {key}")
        metadata = {
            key: {"shape": list(h5[key].shape), "dtype": str(h5[key].dtype)}
            for key in required
        }
        for split in ("dev", "test"):
            rows = h5[f"A_{split}"].shape[0]
            if h5[f"A_{split}"].shape != (rows, 4):
                raise RuntimeError(f"Invalid A_{split} shape")
            if h5[f"W_{split}"].shape != (rows, 4):
                raise RuntimeError(f"Invalid W_{split} shape")
            if h5[f"X_s_{split}"].shape != (rows, len(SENSORS)):
                raise RuntimeError(f"Invalid X_s_{split} shape")
        for key, count in (("A_var", 4), ("W_var", 4), ("X_s_var", len(SENSORS))):
            if h5[key].shape != (count,):
                raise RuntimeError(f"Invalid {key} shape")
    print(f"Metadata-only preflight complete: {metadata}", flush=True)
    return metadata


def scan_development():
    """Read development IDs and schema labels; lock the frozen engine split."""
    if ATTEMPT.exists():
        raise RuntimeError("The one-shot official-test marker already exists")
    with h5py.File(DATA) as h5:
        if [v.decode() for v in h5["A_var"][:]] != ["unit", "cycle", "Fc", "hs"]:
            raise RuntimeError("DS03 A schema does not match frozen protocol")
        if [v.decode() for v in h5["W_var"][:]] != W_NAMES:
            raise RuntimeError("DS03 W schema does not match frozen protocol")
        if [v.decode() for v in h5["X_s_var"][:]] != SENSORS:
            raise RuntimeError("DS03 sensor schema does not match frozen protocol")
        dev_units, fit, calibration, selection_fit, validation = choose_units(h5)
    OUT.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    plan = {
        "source": "NASA official N-CMAPSS Data Set 2 archive",
        "dataset": DATA.name,
        "development_units": dev_units,
        "model_fit_units": fit,
        "threshold_calibration_units": calibration,
        "epoch_selection_fit_units": selection_fit,
        "epoch_selection_validation_unit": validation,
        "epoch_selection_rule": {
            "maximum_epochs": MAX_EPOCHS,
            "patience": PATIENCE,
            "min_delta": MIN_DELTA,
        },
        "phase": "primary retrospective 90% within-flight altitude",
        "targets": TARGETS,
        "seeds": SEEDS,
        "bootstrap_replicates": BOOTSTRAP_REPETITIONS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "oracle_healthy_only": True,
    }
    plan_path = OUT / "pre_audit_plan.json"
    if plan_path.exists():
        previous = json.loads(plan_path.read_text(encoding="utf-8"))
        if previous != json.loads(json.dumps(plan)):
            raise RuntimeError("The preregistered confirmation plan has changed")
    else:
        plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"Pre-audit split locked: {plan}", flush=True)
    return plan


def select_lstm_epochs(x, descriptors, meta, fit_units, validation_unit):
    fit_mask = meta.unit.isin(fit_units).to_numpy()
    val_mask = meta.unit.to_numpy() == validation_unit
    correction = ResidualPCADetector("history", alpha=1.0).fit(
        x[fit_mask], descriptors[fit_mask]
    )
    z_fit = correction.standardized_residual(x[fit_mask], descriptors[fit_mask]).astype(np.float32)
    z_val = correction.standardized_residual(x[val_mask], descriptors[val_mask]).astype(np.float32)
    fit_chunks = make_training_chunks(z_fit, meta[fit_mask].reset_index(drop=True))
    val_chunks = make_training_chunks(z_val, meta[val_mask].reset_index(drop=True))
    rows, selected = [], {}
    for seed in SEEDS:
        model = build_torch_lstm(seed, len(SENSORS))
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        train_losses, val_losses = [], []
        best_monitored, wait = float("inf"), 0
        for epoch in range(1, MAX_EPOCHS + 1):
            train_loss = run_epoch(model, fit_chunks, optimizer, seed, epoch)
            val_loss = evaluate_loss(model, val_chunks)
            train_losses.append(train_loss)
            val_losses.append(val_loss)
            if epoch == 1 or epoch % 20 == 0:
                print(
                    f"selection seed={seed} epoch={epoch} loss={train_loss:.7f} "
                    f"val_loss={val_loss:.7f}", flush=True,
                )
            if val_loss < best_monitored - MIN_DELTA:
                best_monitored, wait = val_loss, 0
                torch.save(
                    {key: value.detach().cpu() for key, value in model.state_dict().items()},
                    CHECKPOINTS / f"lstm_seed_{seed}_selection.pt",
                )
            else:
                wait += 1
                if wait >= PATIENCE:
                    break
        best_epoch = int(np.argmin(val_losses) + 1)
        selected[seed] = best_epoch
        for epoch, (train_loss, val_loss) in enumerate(zip(train_losses, val_losses), 1):
            rows.append({
                "seed": seed,
                "stage": "engine_disjoint_epoch_selection",
                "epoch": epoch,
                "train_loss": train_loss,
                "validation_loss": val_loss,
                "best_epoch": best_epoch,
                "epochs_run": len(val_losses),
                "max_epochs": MAX_EPOCHS,
                "patience": PATIENCE,
                "min_delta": MIN_DELTA,
                "fit_units": ",".join(map(str, fit_units)),
                "validation_units": str(validation_unit),
            })
        del model, optimizer
        torch.cuda.empty_cache()
    del correction, z_fit, z_val, fit_chunks, val_chunks
    gc.collect()
    return rows, selected


def refit_lstm(seed, epochs, z_train, train_meta):
    chunks = make_training_chunks(z_train, train_meta)
    model = build_torch_lstm(seed, len(SENSORS))
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    history = []
    for epoch in range(1, epochs + 1):
        loss = run_epoch(model, chunks, optimizer, seed, epoch)
        if epoch == 1 or epoch % 20 == 0 or epoch == epochs:
            print(f"refit seed={seed} epoch={epoch}/{epochs} loss={loss:.7f}", flush=True)
        history.append((epoch, loss))
    torch.save(model.state_dict(), CHECKPOINTS / f"lstm_seed_{seed}_final.pt")
    rows = [{
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
        "fit_units": ",".join(map(str, sorted(train_meta.unit.unique()))),
        "validation_units": "none",
    } for epoch, loss in history]
    del chunks, optimizer
    return model, rows


def calibration_thresholds(scores, meta):
    phases = meta.phase_primary.to_numpy()
    result = {}
    for target in TARGETS:
        result[str(target)] = {
            "pooled": float(np.quantile(scores, 1 - target, method="higher")),
            **{
                phase: float(np.quantile(scores[phases == index], 1 - target,
                                         method="higher"))
                for index, phase in enumerate(PHASES)
            },
        }
    return result


def transfer_with_locked_thresholds(scores, meta, detector, seed, target, thresholds):
    rows = []
    phases = meta.phase_primary.to_numpy()
    groups = [(str(int(unit)), meta.unit.to_numpy() == unit)
              for unit in sorted(meta.unit.unique())]
    groups.append(("all", np.ones(len(meta), dtype=bool)))
    for cal_phase in PHASES:
        threshold = thresholds[cal_phase]
        for unit, unit_mask in groups:
            for phase_id, test_phase in enumerate(PHASES):
                mask = unit_mask & (phases == phase_id)
                alarm = scores[mask] > threshold
                rows.append({
                    "detector": detector, "seed": seed,
                    "phase_definition": "primary", "nominal_fpr": target,
                    "unit": unit,
                    "flight_class": int(meta.loc[unit_mask, "flight_class"].iloc[0])
                    if unit != "all" else "mixed",
                    "calibration_phase": cal_phase, "test_phase": test_phase,
                    "n": int(mask.sum()), "false_alarms": int(alarm.sum()),
                    "false_alarm_rate": float(alarm.mean()), "threshold": threshold,
                    "matched_fc": False,
                })
    return rows


def canonical_table(rate_df, transfer_df, summary_df):
    records = []
    for keys, group in rate_df.groupby(
        ["detector", "seed", "nominal_fpr", "unit"], sort=False
    ):
        detector, seed, target, unit = keys
        values = group.set_index("phase")
        transfers = transfer_df[
            (transfer_df.detector == detector)
            & (transfer_df.seed == seed)
            & (transfer_df.nominal_fpr == target)
            & (transfer_df.unit.astype(str) == str(unit))
        ]
        flights = summary_df[
            (summary_df.detector == detector)
            & (summary_df.seed == seed)
            & (summary_df.nominal_fpr == target)
            & (summary_df.unit.astype(str) == str(unit))
        ].set_index("phase")
        record = {
            "detector": detector, "seed": seed, "phase_rule": "primary",
            "nominal_fpr_target": target,
            "evaluation_unit": "pooled" if str(unit) == "all" else f"engine_{unit}",
            "overall_fpr": values.loc["overall", "false_alarm_rate"],
            "climb_fpr": values.loc["climb", "false_alarm_rate"],
            "cruise_fpr": values.loc["cruise", "false_alarm_rate"],
            "descent_fpr": values.loc["descent", "false_alarm_rate"],
            "descent_minus_climb": values.loc["descent", "false_alarm_rate"]
            - values.loc["climb", "false_alarm_rate"],
            "descent_minus_cruise": values.loc["descent", "false_alarm_rate"]
            - values.loc["cruise", "false_alarm_rate"],
            "worst_cross_phase_transfer_fpr": transfers[
                transfers.calibration_phase != transfers.test_phase
            ].false_alarm_rate.max(),
        }
        for phase in PHASES:
            record[f"healthy_flights_with_alarm_{phase}"] = flights.loc[
                phase, "fraction_flights_with_false_alarm"
            ]
            record[f"false_alarm_events_per_healthy_flight_{phase}"] = flights.loc[
                phase, "events_per_healthy_flight"
            ]
        records.append(record)
    return pd.DataFrame(records)


def confirmation_report(canonical, uncertainty, plan, selected):
    primary = canonical[
        (canonical.nominal_fpr_target == .01)
        & (canonical.evaluation_unit == "pooled")
    ]
    directional = {}
    for detector in ("pca", "isolation_forest", "lstm_autoencoder"):
        group = primary[primary.detector == detector]
        directional[detector] = {
            "descent_minus_climb": float(group.descent_minus_climb.mean()),
            "descent_minus_cruise": float(group.descent_minus_cruise.mean()),
        }
    reproduced = all(
        value > 0 for metrics in directional.values() for value in metrics.values()
    )
    lines = [
        "# One-shot DS03 confirmation",
        "",
        "Source: official NASA N-CMAPSS DS03. Healthy-state (`hs = 1`) rows only; "
        "this is an oracle restriction. The phase rule uses each complete flight's "
        "altitude trace retrospectively.",
        "",
        "The official test arrays were opened once, after all model fitting and "
        "calibration thresholds were locked.",
        "",
        "## Frozen split and LSTM selection",
        "",
        f"Model-fitting units: {plan['model_fit_units']}; threshold-calibration "
        f"units: {plan['threshold_calibration_units']}.",
        f"LSTM epoch-selection fit units: {plan['epoch_selection_fit_units']}; "
        f"validation unit: {plan['epoch_selection_validation_unit']}.",
        f"Selected epochs: {selected}.",
        "",
        "## Primary 1% pooled result",
        "",
        "| Detector | Seed | Overall | Climb | Cruise | Descent | Descent−climb | "
        "Descent−cruise |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in primary.itertuples(index=False):
        lines.append(
            f"| {row.detector} | {row.seed} | {row.overall_fpr:.3%} | "
            f"{row.climb_fpr:.3%} | {row.cruise_fpr:.3%} | {row.descent_fpr:.3%} | "
            f"{row.descent_minus_climb:.3%} | {row.descent_minus_cruise:.3%} |"
        )
    lines.extend([
        "", "## Frozen directional interpretation", "",
        "REPRODUCED" if reproduced else "NOT REPRODUCED",
        "",
        "The rule requires positive pooled descent−climb and descent−cruise "
        "for PCA and for seed means of Isolation Forest and LSTM.",
        "",
        "No hyperparameter was changed after opening the official test arrays.", "",
    ])
    if any(epoch == MAX_EPOCHS for epoch in selected.values()):
        lines.insert(
            lines.index("## Primary 1% pooled result"),
            "At least one LSTM seed reached the frozen 600-epoch ceiling; "
            "this is a convergence limitation, not a reason to alter the "
            "confirmatory training budget.",
        )
    for detector, metrics in directional.items():
        lines.append(
            f"- {detector}: descent−climb {metrics['descent_minus_climb']:.3%}; "
            f"descent−cruise {metrics['descent_minus_cruise']:.3%}."
        )
    lines.extend([
        "", "## Per-engine heterogeneity at the primary target", "",
        "| Detector | Seed | Engine | Climb | Cruise | Descent | Descent−climb | "
        "Descent−cruise |",
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ])
    per_engine = canonical[
        (canonical.nominal_fpr_target == .01)
        & (canonical.evaluation_unit != "pooled")
    ]
    for row in per_engine.itertuples(index=False):
        lines.append(
            f"| {row.detector} | {row.seed} | {row.evaluation_unit} | "
            f"{row.climb_fpr:.3%} | {row.cruise_fpr:.3%} | "
            f"{row.descent_fpr:.3%} | {row.descent_minus_climb:.3%} | "
            f"{row.descent_minus_cruise:.3%} |"
        )
    exceptions = per_engine[
        (per_engine.descent_minus_climb <= 0)
        | (per_engine.descent_minus_cruise <= 0)
    ]
    lines.extend([
        "", f"Per-engine directional exceptions: {len(exceptions)} of {len(per_engine)} "
        "detector/seed/engine rows. Every exception is visible in the table above.",
        "", "## Hierarchical uncertainty", "",
        "Intervals resample engines, then flights within engines, with calibration "
        "thresholds re-estimated in each of 2,000 replicates.", "",
        "| Detector | Seed | Difference | Bootstrap mean | 95% interval |",
        "|---|---:|---|---:|---:|",
    ])
    interval_rows = uncertainty[uncertainty.metric.isin(
        ["descent_minus_climb", "descent_minus_cruise"]
    )]
    for row in interval_rows.itertuples(index=False):
        lines.append(
            f"| {row.detector} | {row.seed} | {row.metric} | "
            f"{row.bootstrap_mean:.3%} | {row.ci_lower_95:.3%}–"
            f"{row.ci_upper_95:.3%} |"
        )
    lines.extend([
        "", "All targets, the full cross-phase transfer matrix, and flight alarm "
        "burden are in the accompanying CSV files.", "",
    ])
    (OUT / "CONFIRMATION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return reproduced


def main():
    configure_cuda_runtime()
    preflight()
    plan = scan_development()
    with h5py.File(DATA) as h5:
        dev_x, dev_w, dev_meta = load_primary_split(h5, "dev")
    print(f"Healthy development rows: {len(dev_meta)}", flush=True)
    dev_descriptors, names = causal_descriptors(dev_w, dev_meta)
    fit_mask = dev_meta.unit.isin(plan["model_fit_units"]).to_numpy()
    cal_mask = dev_meta.unit.isin(plan["threshold_calibration_units"]).to_numpy()
    train_meta = dev_meta[fit_mask].reset_index(drop=True)
    cal_meta = dev_meta[cal_mask].reset_index(drop=True)

    history, selected = select_lstm_epochs(
        dev_x, dev_descriptors, dev_meta,
        plan["epoch_selection_fit_units"], plan["epoch_selection_validation_unit"],
    )
    correction = ResidualPCADetector("history", alpha=1.0).fit(
        dev_x[fit_mask], dev_descriptors[fit_mask]
    )
    z_train = correction.standardized_residual(
        dev_x[fit_mask], dev_descriptors[fit_mask]
    ).astype(np.float32)
    z_cal = correction.standardized_residual(
        dev_x[cal_mask], dev_descriptors[cal_mask]
    ).astype(np.float32)
    models = {}
    cal_scores = {}
    cal_scores[("pca", -1)] = correction.score(
        dev_x[cal_mask], dev_descriptors[cal_mask]
    )
    for seed in SEEDS:
        forest = IsolationForest(
            n_estimators=200, max_samples=8192, contamination="auto",
            random_state=seed, n_jobs=-1,
        ).fit(z_train)
        models[("isolation_forest", seed)] = forest
        cal_scores[("isolation_forest", seed)] = -forest.score_samples(z_cal)
    for seed in SEEDS:
        lstm, refit = refit_lstm(seed, selected[seed], z_train, train_meta)
        history.extend(refit)
        models[("lstm_autoencoder", seed)] = lstm
        cal_scores[("lstm_autoencoder", seed)], _ = score_lstm_with_positions(
            lstm, z_cal, cal_meta
        )
    pd.DataFrame(history).to_csv(OUT / "lstm_training_history.csv", index=False)
    locked = {
        f"{detector}:{seed}": calibration_thresholds(scores, cal_meta)
        for (detector, seed), scores in cal_scores.items()
    }
    (OUT / "calibration_lock.json").write_text(json.dumps(locked, indent=2), encoding="utf-8")
    print("All model fits and calibration thresholds locked", flush=True)

    with ATTEMPT.open("x", encoding="utf-8") as marker:
        json.dump({"status": "official_test_opened_once", "dataset": DATA.name}, marker)
    with h5py.File(DATA) as h5:
        test_x, test_w, test_meta = load_primary_split(h5, "test")
    print(f"Healthy official-test rows: {len(test_meta)}", flush=True)
    test_descriptors, _ = causal_descriptors(test_w, test_meta)
    z_test = correction.standardized_residual(test_x, test_descriptors).astype(np.float32)
    test_scores = {("pca", -1): correction.score(test_x, test_descriptors)}
    for (detector, seed), model in models.items():
        if detector == "isolation_forest":
            test_scores[(detector, seed)] = -model.score_samples(z_test)
        else:
            test_scores[(detector, seed)], _ = score_lstm_with_positions(
                model, z_test, test_meta
            )
    rate_rows, transfer_rows, detail_rows, summary_rows = [], [], [], []
    for (detector, seed), scores in test_scores.items():
        thresholds = locked[f"{detector}:{seed}"]
        for target in TARGETS:
            t = thresholds[str(target)]
            rate_rows.extend(row_metrics(
                scores, test_meta, t["pooled"], detector, seed, "primary", target
            ))
            transfer_rows.extend(transfer_with_locked_thresholds(
                scores, test_meta, detector, seed, target, t
            ))
            detail, summary = flight_metrics(
                scores, test_meta, t["pooled"], detector, seed, "primary", target
            )
            detail_rows.extend(detail)
            summary_rows.extend(summary)
    rates = pd.DataFrame(rate_rows).drop(columns="matched_fc")
    transfers = pd.DataFrame(transfer_rows).drop(columns="matched_fc")
    details = pd.DataFrame(detail_rows).drop(columns="matched_fc")
    summaries = pd.DataFrame(summary_rows).drop(columns="matched_fc")
    rates.to_csv(OUT / "row_false_alarm_rates.csv", index=False)
    transfers.to_csv(OUT / "threshold_transfer_matrix.csv", index=False)
    details.to_csv(OUT / "flight_alarm_detail.csv", index=False)
    summaries.to_csv(OUT / "flight_alarm_summary.csv", index=False)
    canonical = canonical_table(rates, transfers, summaries)
    canonical.to_csv(OUT / "canonical_results.csv", index=False)
    print("Running frozen hierarchical bootstrap", flush=True)
    score_map = {
        name: {"calibration": cal_scores[name], "official_test": test_scores[name]}
        for name in test_scores
    }
    uncertainty = hierarchical_bootstrap(score_map, cal_meta, test_meta)
    uncertainty.to_csv(OUT / "hierarchical_bootstrap_ci.csv", index=False)
    reproduced = confirmation_report(canonical, uncertainty, plan, selected)
    (OUT / "run_config.json").write_text(json.dumps({
        **plan,
        "selected_epochs": selected,
        "descriptors": names,
        "official_test_units": sorted(map(int, test_meta.unit.unique())),
        "directional_pattern_reproduced": reproduced,
    }, indent=2), encoding="utf-8")
    print(f"One-shot confirmation complete: reproduced={reproduced}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--metadata-only", action="store_true")
    mode.add_argument("--scan-development", action="store_true")
    arguments = parser.parse_args()
    if arguments.metadata_only:
        preflight()
    elif arguments.scan_development:
        preflight()
        scan_development()
    else:
        main()
