"""Numerical and computational audit of the extension (brief section 18), from committed locks and records only."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

import ext_common as ec


def training_summary(key):
    history = pd.read_csv(ec.RESULTS / key / "lock" / "training_history.csv")
    rows = []
    for (detector, seed), part in history.groupby(["detector", "seed"]):
        selection = part[part.stage.str.contains("selection")]
        refit = part[part.stage.str.contains("refit")]
        row = {"subset": key, "detector": detector, "seed": int(seed)}
        if len(selection):
            row.update({"selection_epochs_run": int(selection.epoch.max()),
                        "selected_epoch": int(selection.best_epoch.iloc[0]),
                        "hit_600_ceiling": bool(selection.epoch.max() >= 600),
                        "first_validation_loss": float(selection.validation_loss.iloc[0]),
                        "best_validation_loss": float(selection.validation_loss.min()),
                        "final_selection_train_loss": float(selection.train_loss.iloc[-1])})
        if len(refit):
            losses = refit.train_loss.to_numpy()
            row.update({"refit_epochs": int(len(losses)), "refit_first_loss": float(losses[0]),
                        "refit_final_loss": float(losses[-1]),
                        "refit_largest_epoch_increase": float(np.max(np.diff(losses))) if len(losses) > 1 else 0.0,
                        "refit_all_finite": bool(np.isfinite(losses).all())})
        rows.append(row)
    return rows


def main():
    training, lock_rows = [], []
    for key in list(ec.NEW_ORDER) + list(ec.REFERENCE_ORDER):
        lock_path = ec.RESULTS / key / "lock" / "calibration_lock.json"
        if not lock_path.exists():
            continue
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        record = json.loads((ec.RESULTS / key / "lock" / "lock_record.json").read_text(encoding="utf-8"))
        audit_path = ec.RESULTS / key / "audit" / "audit_record.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
        training += training_summary(key)
        precision = lock.get("cvae_precision_audit", {})
        lock_rows.append({
            "subset": key, "family": ec.FAMILIES[key], "input_sha256": lock["input_sha256"],
            "lock_sha256": record["lock_sha256"], "lock_seconds": record.get("seconds"),
            "calibration_rows": lock["calibration_rows"]["total"], "calibration_flights": lock["calibration_rows"]["flights"],
            "model_files_hashed": len([k for k in lock["models"]["files"] if k != "timings"]),
            "timings": json.dumps(lock["models"]["files"].get("timings", {})),
            "cvae_precision_max_rel_diff": max((v["max_relative_difference"] for v in precision.values()), default=np.nan),
            "cvae_precision_min_spearman": min((v["spearman"] for v in precision.values()), default=np.nan),
            "cvae_precision_exceedance_changes": sum(abs(v["exceedance_count_float32"] - v["exceedance_count_float64"])
                                                     for v in precision.values()),
            "cvae_variance_bound_share": json.dumps({s: round(v, 4) for s, v in lock.get("cvae_variance_bound_share", {}).items()}),
            "audit_done": bool(audit), "audit_seconds": audit.get("seconds"),
            "audit_rows": audit.get("audit_rows"), "gates": json.dumps(audit.get("gates", lock.get("gates", {})))})
    out = ec.RESULTS / "summary"
    out.mkdir(parents=True, exist_ok=True)
    ec.write_csv(out / "numerical_audit_training.csv", pd.DataFrame(training))
    ec.write_csv(out / "numerical_audit_locks.csv", pd.DataFrame(lock_rows))
    return pd.DataFrame(training), pd.DataFrame(lock_rows)


if __name__ == "__main__":
    t, l = main()
    print(t.to_string())
    print(l.to_string())
