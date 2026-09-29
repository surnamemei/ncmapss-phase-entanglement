"""Post-confirmation mitigation analysis for the MSSP revision.

Implements docs/mssp/post_confirmation_mitigation_protocol.md (FROZEN v1.0). The
analysis compares the frozen pooled healthy calibration with phase-conditioned
calibration, plus a causal-regime secondary arm, on the frozen engine-disjoint
splits. The frozen DS02/DS03 modules are imported unchanged, and the detectors are
the frozen specifications: PCA and Isolation Forest are refitted
deterministically, while the LSTM weights are loaded and never trained. Every
output is a new file under the output root.

Stages:
  B  label structure
  C  reproduction gate
  L  calibration-only lock
  D  healthy endpoints
  E  abnormal-state endpoints (one-shot, explicit authorization)
  F  report
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import final_validation as fv  # noqa: E402  (sets CUBLAS_WORKSPACE_CONFIG before CUDA use)
import torch  # noqa: E402
from confirm_frozen_ds03 import (  # noqa: E402
    calibration_thresholds,
    canonical_table,
    choose_units,
    primary_phase,
    transfer_with_locked_thresholds,
)
from phase3_dynamic import ResidualPCADetector, causal_descriptors  # noqa: E402
from second_stage_audit import PHASES, SENSORS, W_NAMES, count_events, phase_labels  # noqa: E402
from sklearn.ensemble import IsolationForest  # noqa: E402


PROTOCOL = ROOT / "docs/mssp/post_confirmation_mitigation_protocol.md"
BASELINE_MANIFEST = ROOT / "docs/mssp/frozen_baseline.sha256"
CONFIG_SNAPSHOT = ROOT / "configs/mssp_mitigation.yaml"
REQUIREMENTS_LOCK = ROOT / "requirements-lock.txt"
DEFAULT_OUTPUT_ROOT = ROOT / "results/mssp_mitigation"

SEEDS = tuple(fv.SEEDS)
TARGETS = tuple(fv.TARGETS)
PRIMARY_TARGET = 0.01
RUNS = (("pca", -1),) + tuple(("isolation_forest", s) for s in SEEDS) + tuple(
    ("lstm_autoencoder", s) for s in SEEDS
)
FAMILIES = ("pca", "isolation_forest", "lstm_autoencoder")
SCHEMES = ("pooled", "phase_conditioned", "causal_regime")
ALTERNATIVES = ("phase_conditioned", "causal_regime")
ARM_STATUS = {
    "pooled": "frozen comparator (reproduced)",
    "phase_conditioned": "post-confirmation primary comparison",
    "causal_regime": "post-confirmation causal sensitivity/feasibility arm",
}
REGIMES = ("ascending", "level", "descending")
CAUSAL_WINDOW = 60
CAUSAL_RATE_LIMIT = 2.0
FLIGHT_FALSE_FLAG_TARGET = 0.05
EARLY_WINDOW_FLIGHTS = 10
LIFE_BINS = (0.0, 0.25, 0.5, 0.75, 1.0)
PERSISTENCE_FLIGHTS = 2
PAUC_MAX_FPR = 0.02
EXCEEDANCE_MULTIPLE = 2.0
GUARDRAIL_RATIO = 0.9
GUARDRAIL_DELAY_FLIGHTS = 1
U1_SEED = fv.BOOTSTRAP_SEED
U2_SEED = 20260927
REPLICATES = fv.BOOTSTRAP_REPETITIONS
LSTM_THRESHOLD_RTOL = 1e-6
BOOTSTRAP_ATOL = 1e-12
COUNT_COLUMNS = ("n", "false_alarms", "any_false_alarm", "false_alarm_events", "rows",
                 "healthy_flights")
FROZEN_BOOTSTRAP_METRICS = ("overall_fpr", "climb_fpr", "cruise_fpr", "descent_fpr",
                            "descent_minus_climb", "descent_minus_cruise",
                            "worst_cross_phase_transfer_fpr")
PASSING_GATE = ("PASS", "PASS_WITH_LSTM_TOLERANCE")


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    filename: str
    env_var: str
    md5: str
    fit_units: tuple
    cal_units: tuple
    audit_units: tuple
    frozen_dir: str
    frozen_files: dict

    @property
    def h5_path(self) -> Path:
        return Path(os.environ.get(self.env_var, ROOT / "N-CMAPSS" / self.filename))

    @property
    def frozen(self) -> Path:
        return ROOT / self.frozen_dir

    def roles(self) -> dict:
        roles = {unit: "model_fit" for unit in self.fit_units}
        roles.update({unit: "calibration" for unit in self.cal_units})
        roles.update({unit: "audit" for unit in self.audit_units})
        return roles


DATASETS = {
    "ds02": DatasetSpec(
        "ds02", "N-CMAPSS_DS02-006.h5", "NCMAPSS_DS02_H5", "61056251b36290e11371e017eed70eac",
        (2, 5, 10, 16), (18, 20), (11, 14, 15), "results/final_validation",
        {
            "rates": "executed_row_false_alarm_rates.csv",
            "transfer": "executed_threshold_transfer_matrix.csv",
            "probe": "executed_score_only_phase_prediction.csv",
            "detail": "executed_flight_alarm_detail.csv",
            "canonical": "canonical_results.csv",
            "per_engine": "per_engine_phase_fpr.csv",
            "boundary": "lstm_boundary_audit.csv",
            "bootstrap": "hierarchical_bootstrap_ci.csv",
        },
    ),
    "ds03": DatasetSpec(
        "ds03", "N-CMAPSS_DS03-012.h5", "NCMAPSS_DS03_H5", "a301cd2cfa9b7da6e6ec12051ded9afe",
        (1, 2, 3, 5, 6, 7, 9), (4, 8), (10, 11, 12, 13, 14, 15), "results/confirmation_ds03",
        {
            "lock": "calibration_lock.json",
            "rates": "row_false_alarm_rates.csv",
            "transfer": "threshold_transfer_matrix.csv",
            "detail": "flight_alarm_detail.csv",
            "summary": "flight_alarm_summary.csv",
            "canonical": "canonical_results.csv",
            "bootstrap": "hierarchical_bootstrap_ci.csv",
        },
    ),
}


class GateError(RuntimeError):
    """A pre-specified integrity or reproduction check failed; execution halts."""


# ---------------------------------------------------------------------------
# Provenance, hashing, and guarded output
# ---------------------------------------------------------------------------

PROTECTED = tuple((ROOT / name).resolve() for name in (
    ".git", "N-CMAPSS", "configs", "docs", "paper", "scripts", "src", "tests",
    "results/confirmation_ds03", "results/final_validation", "results/second_stage",
    "results/phase3_dynamic_correction", "results/phase3_cross_detector",
))


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path, algorithm="sha256", block=8 << 20):
    digest = hashlib.new(algorithm)
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(block), b""):
            digest.update(chunk)
    return digest.hexdigest()


def array_fingerprint(values):
    return sha256_bytes(np.ascontiguousarray(values, dtype=np.float64).tobytes())


def rel(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def guard_output(path):
    """Refuse output locations in frozen, source, documentation, or data paths."""
    path = Path(path).resolve()
    if path in (ROOT.resolve(), (ROOT / "results").resolve()):
        raise PermissionError(f"Output must be a dedicated subdirectory, not {path}")
    for protected in PROTECTED:
        if path == protected or protected in path.parents:
            raise PermissionError(f"Refusing to write inside protected path: {path}")
    return path


def _json_default(value):
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return rel(value)
    raise TypeError(f"Not JSON serializable: {type(value)!r}")


def write_new(path, text):
    """Create a file that must not already exist; return its SHA-256."""
    path = guard_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return sha256_bytes(text.encode("utf-8"))


def write_csv(path, frame):
    return write_new(path, frame.to_csv(index=False))


def write_json(path, payload):
    return write_new(path, json.dumps(payload, indent=2, default=_json_default) + "\n")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_json(payload):
    return json.dumps(payload, sort_keys=True, default=_json_default)


def verify_manifest(manifest=BASELINE_MANIFEST, *, allow_absent_ignored=False):
    """Check every frozen file against the baseline SHA-256 manifest."""
    entries = [line.split("  ", 1) for line in
               Path(manifest).read_text(encoding="utf-8").splitlines() if line.strip()]
    missing, mismatched, skipped = [], [], []
    for digest, name in entries:
        path = ROOT / name
        if not path.exists():
            (skipped if allow_absent_ignored and name.endswith(".pt") else missing).append(name)
            continue
        if file_digest(path) != digest:
            mismatched.append(name)
    return {
        "manifest": rel(manifest), "manifest_sha256": file_digest(manifest),
        "entries": len(entries), "missing": missing, "mismatched": mismatched,
        "skipped_absent_git_ignored": skipped, "ok": not missing and not mismatched,
    }


def environment_record():
    import matplotlib
    import scipy
    import sklearn

    observed = {
        "torch": torch.__version__, "scikit-learn": sklearn.__version__,
        "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
        "h5py": h5py.__version__, "matplotlib": matplotlib.__version__,
    }
    locked = {}
    for line in REQUIREMENTS_LOCK.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if "==" in line:
            name, version = line.split("==", 1)
            locked[name.strip()] = version.strip()
    available = bool(torch.cuda.is_available())
    return {
        "python": sys.version.split()[0], "executable": sys.executable,
        "platform": platform.platform(), "packages": observed, "requirements_lock": locked,
        "lock_mismatches": {name: {"lock": version, "observed": observed.get(name)}
                            for name, version in locked.items() if observed.get(name) != version},
        "cuda_runtime": torch.version.cuda, "cuda_available": available,
        "gpu": torch.cuda.get_device_name(0) if available else None,
        "cudnn": torch.backends.cudnn.version() if available else None,
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
    }


def git_record():
    def run(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                              check=False).stdout.strip()

    status = run("status", "--porcelain").splitlines()
    return {
        "head": run("rev-parse", "HEAD"), "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "modified_tracked": [line[3:] for line in status if not line.startswith("??")],
        "untracked": [line[3:] for line in status if line.startswith("??")],
    }


def provenance_record():
    return {
        "protocol": rel(PROTOCOL), "protocol_sha256": file_digest(PROTOCOL),
        "config_sha256": file_digest(CONFIG_SNAPSHOT),
        "module_sha256": file_digest(Path(__file__)), "git": git_record(),
    }


def verify_inputs(spec):
    """G2: frozen files and checkpoints against the manifest; HDF5 MD5 over raw bytes."""
    manifest = verify_manifest()
    if not manifest["ok"]:
        raise GateError(f"Baseline manifest failed: {manifest}")
    md5 = file_digest(spec.h5_path, "md5")
    if md5 != spec.md5:
        raise GateError(f"{spec.h5_path.name} MD5 {md5} != provenance {spec.md5}")
    return {"manifest": manifest, "h5_path": rel(spec.h5_path), "h5_md5": md5,
            "h5_bytes": spec.h5_path.stat().st_size}


# ---------------------------------------------------------------------------
# Stage B: label structure from A arrays only
# ---------------------------------------------------------------------------

def label_structure(a, split, roles):
    """Per-engine health-label structure from an A array (unit, cycle, Fc, hs)."""
    unit = a[:, 0].astype(np.int64)
    cycle = a[:, 1].astype(np.int64)
    flight_class = a[:, 2].astype(np.int64)
    hs_raw = a[:, 3]
    hs = hs_raw.astype(np.int8)
    change = np.flatnonzero(np.diff(unit) != 0) + 1
    starts, ends = np.r_[0, change], np.r_[change, len(unit)]
    block_units = pd.Series(unit[starts])
    repeated = set(block_units[block_units.duplicated()].tolist())
    records = []
    for start, end in zip(starts, ends):
        u = int(unit[start])
        h, c = hs[start:end], cycle[start:end]
        flight_starts = np.r_[0, np.flatnonzero(np.diff(c) != 0) + 1]
        f_min = np.minimum.reduceat(h, flight_starts)
        f_max = np.maximum.reduceat(h, flight_starts)
        flight_cycles = c[flight_starts]
        onset_index = np.flatnonzero(f_min == 0)
        records.append({
            "split": split, "unit": u, "role": roles.get(u, "unassigned"),
            "flight_class": int(flight_class[start]),
            "flight_class_constant": bool(np.all(flight_class[start:end] == flight_class[start])),
            "rows": int(end - start), "healthy_rows": int(np.sum(h == 1)),
            "abnormal_rows": int(np.sum(h == 0)), "flights": int(len(flight_starts)),
            "healthy_flights": int(np.sum(f_min == 1)),
            "post_onset_flights": int(len(flight_starts) - onset_index[0]) if len(onset_index) else 0,
            "mixed_flights": int(np.sum(f_min != f_max)),
            "first_cycle": int(flight_cycles[0]),
            "onset_cycle": int(flight_cycles[onset_index[0]]) if len(onset_index) else None,
            "eol_cycle": int(flight_cycles[-1]),
            "hs_binary": bool(np.isin(hs_raw[start:end], (0.0, 1.0)).all()),
            "ls1_monotone_single_transition": bool(h[0] == 1 and np.all(np.diff(h) <= 0)),
            "ls2_flight_constant": bool(np.all(f_min == f_max)),
            "ls3_cycles_contiguous": bool(np.all(np.diff(flight_cycles) == 1)),
            "flight_cycles_unique": bool(len(np.unique(flight_cycles)) == len(flight_cycles)),
            "engine_rows_contiguous": u not in repeated,
        })
    table = pd.DataFrame(records)
    valid = table.ls1_monotone_single_transition & table.hs_binary
    table["eligible_s1_s3_s4"] = valid & (table.post_onset_flights >= 1)
    table["eligible_s2"] = valid & (table.post_onset_flights >= EARLY_WINDOW_FLIGHTS)
    table["eligible_d"] = valid & (table.healthy_flights >= 1) & (table.post_onset_flights >= 1)
    table["delay_flag_mixed_flight"] = ~table.ls2_flight_constant
    return table


def ds02_cross_check(table):
    """Stage B DS02 labels must equal the tracked per-flight audit of all DS02 flights."""
    audit = pd.read_csv(ROOT / "results/cycle_phase_audit.csv")
    audit["healthy_flight"] = audit.healthy_rows == audit.rows
    expected = audit.groupby(["split", "unit"]).agg(
        rows=("rows", "sum"), healthy_rows=("healthy_rows", "sum"), flights=("cycle", "size"),
        healthy_flights=("healthy_flight", "sum"), eol_cycle=("cycle", "max"),
    ).reset_index()
    merged = table.merge(expected, on=["split", "unit"], suffixes=("", "_frozen"))
    columns = ("rows", "healthy_rows", "flights", "healthy_flights", "eol_cycle")
    return bool(len(merged) == len(table) == len(expected)
                and all((merged[c].astype(int) == merged[f"{c}_frozen"].astype(int)).all()
                        for c in columns))


def stage_b_checks(spec, table, schema, derived):
    dev, test = table[table.split == "dev"], table[table.split == "test"]
    checks = {
        "schema_A": schema["A_var"] == ["unit", "cycle", "Fc", "hs"],
        "schema_W": schema["W_var"] == list(W_NAMES),
        "schema_X_s": schema["X_s_var"] == list(SENSORS),
        "dev_units_equal_fit_plus_calibration":
            sorted(dev.unit) == sorted(spec.fit_units + spec.cal_units),
        "test_units_equal_audit": sorted(test.unit) == sorted(spec.audit_units),
        "hs_binary": bool(table.hs_binary.all()),
        "engine_rows_contiguous": bool(table.engine_rows_contiguous.all()),
        "flight_cycles_unique": bool(table.flight_cycles_unique.all()),
        "ls1_all_engines": bool(table.ls1_monotone_single_transition.all()),
        "ls2_all_engines": bool(table.ls2_flight_constant.all()),
    }
    required = list(checks)
    if derived is not None:
        plan = read_json(spec.frozen / "pre_audit_plan.json")
        checks["ds03_frozen_id_rule_matches_plan"] = all(
            derived[key] == plan[key] for key in (
                "development_units", "model_fit_units", "threshold_calibration_units",
                "epoch_selection_fit_units", "epoch_selection_validation_unit"))
        required.append("ds03_frozen_id_rule_matches_plan")
    if spec.key == "ds02":
        checks["ds02_matches_tracked_cycle_phase_audit"] = ds02_cross_check(table)
        required.append("ds02_matches_tracked_cycle_phase_audit")
    checks["informational_ls3_audit_cycles_contiguous"] = bool(test.ls3_cycles_contiguous.all())
    checks["informational_all_audit_engines_eligible_d"] = bool(test.eligible_d.all())
    checks["informational_all_audit_engines_eligible_s2"] = bool(test.eligible_s2.all())
    checks["required"] = required
    checks["ok"] = all(checks[name] for name in required)
    return checks


def stage_b(spec, output_root):
    """Label structure from A arrays only; no operating, sensor, or score data are read."""
    out = guard_output(Path(output_root) / spec.key / "stage_b")
    started, clock = now_utc(), time.time()
    inputs = verify_inputs(spec)
    with h5py.File(spec.h5_path, "r") as h5:
        schema = {key: [v.decode() for v in h5[key][:]] for key in ("A_var", "W_var", "X_s_var")}
        layout = {key: {"shape": list(h5[key].shape), "dtype": str(h5[key].dtype),
                        "chunks": list(h5[key].chunks) if h5[key].chunks else None,
                        "compression": h5[key].compression}
                  for split in ("dev", "test") for key in (f"A_{split}", f"W_{split}", f"X_s_{split}")}
        tables = [label_structure(h5[f"A_{split}"][:], split, spec.roles())
                  for split in ("dev", "test")]
        derived = None
        if spec.key == "ds03":
            dev_units, fit, cal, selection_fit, validation = choose_units(h5)
            derived = {"development_units": dev_units, "model_fit_units": fit,
                       "threshold_calibration_units": cal,
                       "epoch_selection_fit_units": selection_fit,
                       "epoch_selection_validation_unit": validation}
    table = pd.concat(tables, ignore_index=True)
    checks = stage_b_checks(spec, table, schema, derived)
    calibration = table[table.role == "calibration"]
    record = {
        "stage": "B", "dataset": spec.key, "started_utc": started, "finished_utc": now_utc(),
        "seconds": round(time.time() - clock, 1),
        "data_read": "A_dev and A_test (unit, cycle, Fc, hs) plus variable-name vectors only",
        "inputs": inputs, "schema": schema, "hdf5_layout": layout, "frozen_id_rule": derived,
        "healthy_calibration_flights": int(calibration.healthy_flights.sum()),
        "kappa_order_statistic_index": int(math.ceil(
            (1 - FLIGHT_FALSE_FLAG_TARGET) * (int(calibration.healthy_flights.sum()) - 1))),
        "checks": checks, "provenance": provenance_record(),
    }
    write_csv(out / "label_structure.csv", table)
    write_json(out / "stage_b_record.json", record)
    if not checks["ok"]:
        raise GateError(f"Stage B failed for {spec.key}: {checks}")
    return record


# ---------------------------------------------------------------------------
# Loaders: selected contiguous row blocks only
# ---------------------------------------------------------------------------

def contiguous_runs(mask):
    index = np.flatnonzero(mask)
    if index.size == 0:
        return []
    cuts = np.flatnonzero(np.diff(index) > 1) + 1
    return [(int(group[0]), int(group[-1]) + 1) for group in np.split(index, cuts)]


def read_row_blocks(dataset, runs):
    if not runs:
        return np.empty((0,) + tuple(dataset.shape[1:]), dtype=dataset.dtype)
    return np.concatenate([dataset[start:end] for start, end in runs], axis=0)


def check_schema(h5):
    for key, expected in (("A_var", ["unit", "cycle", "Fc", "hs"]), ("W_var", list(W_NAMES)),
                          ("X_s_var", list(SENSORS))):
        found = [v.decode() for v in h5[key][:]]
        if found != expected:
            raise GateError(f"{key} schema mismatch: {found}")


def build_meta(dataset_key, a, w):
    """Metadata with the frozen dtypes and phase code; phases are computed per flight."""
    units, cycles = a[:, 0].astype(np.int16), a[:, 1].astype(np.int16)
    columns = {"unit": units, "cycle": cycles, "flight_class": a[:, 2].astype(np.int8),
               "healthy": a[:, 3].astype(np.int8)}
    if dataset_key == "ds02":
        primary, alternative, _ = phase_labels(w[:, 0], units, cycles)
        columns["phase_primary"] = primary
        columns["phase_alt_rate"] = alternative
    else:
        columns["phase_primary"] = primary_phase(w[:, 0], units, cycles)
    return pd.DataFrame(columns)


def load_selected_rows(dataset_key, h5, split, select):
    """Read A fully, then W and X_s only for the selected contiguous row blocks."""
    check_schema(h5)
    a = h5[f"A_{split}"][:]
    mask = select(a)
    runs = contiguous_runs(mask)
    x = read_row_blocks(h5[f"X_s_{split}"], runs)
    w = read_row_blocks(h5[f"W_{split}"], runs)
    return x, w, build_meta(dataset_key, a[mask], w), runs


def healthy_selector(a):
    return a[:, 3].astype(np.int8) == 1


def load_healthy(dataset_key, h5, split):
    return load_selected_rows(dataset_key, h5, split, healthy_selector)


def load_abnormal_audit(spec, h5):
    def select(a):
        return (a[:, 3].astype(np.int8) == 0) & np.isin(a[:, 0].astype(np.int64), spec.audit_units)
    return load_selected_rows(spec.key, h5, "test", select)


# ---------------------------------------------------------------------------
# Causal regime (arm C'): current and past altitude of the same flight only
# ---------------------------------------------------------------------------

def causal_regime(alt, units, cycles, window=CAUSAL_WINDOW, limit=CAUSAL_RATE_LIMIT):
    """Label rows ascending (0), level (1), or descending (2) from a trailing altitude rate."""
    alt = np.asarray(alt, dtype=np.float64)
    labels = np.empty(len(alt), dtype=np.int8)
    boundary = np.flatnonzero((np.diff(units) != 0) | (np.diff(cycles) != 0)) + 1
    for start, end in zip(np.r_[0, boundary], np.r_[boundary, len(alt)]):
        z = alt[start:end]
        position = np.arange(len(z))
        lag = np.minimum(position, window)
        rate = np.zeros(len(z))
        moving = lag > 0
        rate[moving] = (z[moving] - z[position[moving] - lag[moving]]) / lag[moving]
        label = np.ones(len(z), dtype=np.int8)
        label[rate > limit] = 0
        label[rate < -limit] = 2
        labels[start:end] = label
    return labels


# ---------------------------------------------------------------------------
# Frozen detectors and scoring
# ---------------------------------------------------------------------------

@dataclass
class Detectors:
    correction: ResidualPCADetector
    forests: dict
    lstms: dict


def load_frozen_lstm(spec, seed):
    path = spec.frozen / "checkpoints" / f"lstm_seed_{seed}_final.pt"
    model = fv.build_torch_lstm(seed, len(SENSORS))
    model.load_state_dict(torch.load(path, map_location=fv.DEVICE, weights_only=True))
    model.eval()
    return model


def fit_detectors(spec, dev_x, dev_desc, fit_mask):
    """Frozen specifications: history correction + PCA, Isolation Forest refits, LSTM loads."""
    correction = ResidualPCADetector("history", alpha=1.0).fit(dev_x[fit_mask], dev_desc[fit_mask])
    z_fit = correction.standardized_residual(dev_x[fit_mask], dev_desc[fit_mask]).astype(np.float32)
    forests = {}
    for seed in SEEDS:
        forests[seed] = IsolationForest(
            n_estimators=200, max_samples=8192, contamination="auto",
            random_state=seed, n_jobs=-1,
        ).fit(z_fit)
    lstms = {seed: load_frozen_lstm(spec, seed) for seed in SEEDS}
    return Detectors(correction, forests, lstms), z_fit


def score_rows(detectors, x, descriptors, meta, z=None):
    """Score rows with every frozen detector run, in the frozen run order."""
    if z is None:
        z = detectors.correction.standardized_residual(x, descriptors).astype(np.float32)
    scores = {("pca", -1): detectors.correction.score(x, descriptors)}
    for seed in SEEDS:
        scores[("isolation_forest", seed)] = -detectors.forests[seed].score_samples(z)
    positions = {}
    for seed in SEEDS:
        scores[("lstm_autoencoder", seed)], positions[seed] = fv.score_lstm_with_positions(
            detectors.lstms[seed], z, meta)
    return scores, positions


@dataclass
class HealthyContext:
    spec: DatasetSpec
    descriptor_names: list
    train_meta: pd.DataFrame
    cal_meta: pd.DataFrame
    test_meta: pd.DataFrame
    cal_alt: np.ndarray
    test_alt: np.ndarray
    train_scores: dict
    cal_scores: dict
    test_scores: dict
    positions: dict
    detectors: Detectors
    blocks: dict
    timings: dict


def prepare_healthy_context(spec, *, score_train=False):
    """Load healthy rows as contiguous blocks, refit/load the frozen detectors, and score."""
    timings, clock = {}, time.time()
    with h5py.File(spec.h5_path, "r") as h5:
        dev_x, dev_w, dev_meta, dev_blocks = load_healthy(spec.key, h5, "dev")
        test_x, test_w, test_meta, test_blocks = load_healthy(spec.key, h5, "test")
    timings["load_healthy_blocks"] = round(time.time() - clock, 1)
    clock = time.time()
    dev_desc, names = causal_descriptors(dev_w, dev_meta)
    test_desc, test_names = causal_descriptors(test_w, test_meta)
    if names != test_names:
        raise GateError("Descriptor names differ between splits")
    fit_mask = dev_meta.unit.isin(spec.fit_units).to_numpy()
    cal_mask = dev_meta.unit.isin(spec.cal_units).to_numpy()
    train_meta = dev_meta[fit_mask].reset_index(drop=True)
    cal_meta = dev_meta[cal_mask].reset_index(drop=True)
    detectors, z_fit = fit_detectors(spec, dev_x, dev_desc, fit_mask)
    timings["fit_detectors"] = round(time.time() - clock, 1)
    clock = time.time()
    cal_scores, cal_positions = score_rows(detectors, dev_x[cal_mask], dev_desc[cal_mask], cal_meta)
    test_scores, test_positions = score_rows(detectors, test_x, test_desc, test_meta)
    train_scores = train_positions = None
    if score_train:
        train_scores, train_positions = score_rows(
            detectors, dev_x[fit_mask], dev_desc[fit_mask], train_meta, z=z_fit)
    timings["score_healthy_rows"] = round(time.time() - clock, 1)
    return HealthyContext(
        spec=spec, descriptor_names=names, train_meta=train_meta, cal_meta=cal_meta,
        test_meta=test_meta, cal_alt=dev_w[cal_mask][:, 0].copy(), test_alt=test_w[:, 0].copy(),
        train_scores=train_scores, cal_scores=cal_scores, test_scores=test_scores,
        positions={"train": train_positions, "calibration": cal_positions,
                   "official_test": test_positions},
        detectors=detectors, blocks={"dev": dev_blocks, "test": test_blocks}, timings=timings,
    )


def score_fingerprints(ctx):
    return {f"{detector}:{seed}": {
        "calibration": array_fingerprint(ctx.cal_scores[(detector, seed)]),
        "healthy_audit": array_fingerprint(ctx.test_scores[(detector, seed)]),
    } for detector, seed in RUNS}


def verify_fingerprints(ctx, dataset_root):
    """G6: rescored healthy vectors must equal the gate's vectors bit for bit."""
    gate = read_json(Path(dataset_root) / "stage_c" / "gate_report.json")
    if gate["overall_status"] not in PASSING_GATE:
        raise GateError(f"Reproduction gate did not pass: {gate['overall_status']}")
    expected = read_json(Path(dataset_root) / "stage_c" / "score_fingerprints.json")
    if score_fingerprints(ctx) != expected:
        raise GateError("Rescored healthy vectors differ from the reproduction-gate fingerprints")
    return gate


# ---------------------------------------------------------------------------
# Stage C: reproduction gate (frozen assembly code re-run on recomputed scores)
# ---------------------------------------------------------------------------

def regenerate_ds03(ctx):
    locked = {f"{d}:{s}": calibration_thresholds(scores, ctx.cal_meta)
              for (d, s), scores in ctx.cal_scores.items()}
    rate_rows, transfer_rows, detail_rows, summary_rows = [], [], [], []
    for (detector, seed), scores in ctx.test_scores.items():
        thresholds = locked[f"{detector}:{seed}"]
        for target in TARGETS:
            t = thresholds[str(target)]
            rate_rows.extend(fv.row_metrics(
                scores, ctx.test_meta, t["pooled"], detector, seed, "primary", target))
            transfer_rows.extend(transfer_with_locked_thresholds(
                scores, ctx.test_meta, detector, seed, target, t))
            detail, summary = fv.flight_metrics(
                scores, ctx.test_meta, t["pooled"], detector, seed, "primary", target)
            detail_rows.extend(detail)
            summary_rows.extend(summary)
    rates = pd.DataFrame(rate_rows).drop(columns="matched_fc")
    transfers = pd.DataFrame(transfer_rows).drop(columns="matched_fc")
    details = pd.DataFrame(detail_rows).drop(columns="matched_fc")
    summaries = pd.DataFrame(summary_rows).drop(columns="matched_fc")
    canonical = canonical_table(rates, transfers, summaries)
    score_map = {name: {"calibration": ctx.cal_scores[name], "official_test": ctx.test_scores[name]}
                 for name in ctx.test_scores}
    uncertainty = fv.hierarchical_bootstrap(score_map, ctx.cal_meta, ctx.test_meta)
    return {"rates": rates, "transfer": transfers, "detail": details, "summary": summaries,
            "canonical": canonical, "bootstrap": uncertainty}, locked


def regenerate_ds02(ctx):
    outputs = ([], [], [], [], [], [])
    score_map, lstm_scores, lstm_positions = {}, {}, {}
    for detector, seed in RUNS:
        name = (detector, seed)
        scores = {"train": ctx.train_scores[name], "calibration": ctx.cal_scores[name],
                  "official_test": ctx.test_scores[name]}
        score_map[name] = scores
        fv.audit_run(detector, seed, scores["train"], scores["calibration"],
                     scores["official_test"], ctx.train_meta, ctx.cal_meta, ctx.test_meta, outputs)
        if detector == "lstm_autoencoder":
            lstm_scores[seed] = scores
            lstm_positions[seed] = {subset: ctx.positions[subset][seed]
                                    for subset in ("train", "calibration", "official_test")}
    metas = {"train": ctx.train_meta, "calibration": ctx.cal_meta, "official_test": ctx.test_meta}
    boundary = fv.boundary_audit(lstm_scores, lstm_positions, metas)
    _, rates, transfers, probes, details, summaries = map(pd.DataFrame, outputs)
    canonical = fv.make_canonical(rates, transfers, probes, summaries)
    uncertainty = fv.hierarchical_bootstrap(score_map, ctx.cal_meta, ctx.test_meta)
    return {"rates": rates, "transfer": transfers, "probe": probes, "detail": details,
            "canonical": canonical, "per_engine": fv.per_engine_table(canonical),
            "boundary": boundary, "bootstrap": uncertainty}, None


REGENERATORS = {"ds02": regenerate_ds02, "ds03": regenerate_ds03}


def compare_table(name, regenerated, frozen_path, *, sort_keys=None, atol=0.0, lstm_only=False):
    """Cell-by-cell comparison after round-trip parsing; byte identity is also reported."""
    text = regenerated.to_csv(index=False)
    frozen_bytes = Path(frozen_path).read_bytes()
    result = {
        "table": name, "frozen_file": rel(frozen_path),
        "frozen_sha256": sha256_bytes(frozen_bytes),
        "regenerated_sha256": sha256_bytes(text.encode("utf-8")),
        "byte_identical": text.encode("utf-8") == frozen_bytes,
    }
    left = pd.read_csv(io.StringIO(text), float_precision="round_trip")
    right = pd.read_csv(frozen_path, float_precision="round_trip")
    result["rows_regenerated"], result["rows_frozen"] = len(left), len(right)
    if list(left.columns) != list(right.columns) or len(left) != len(right):
        result.update(status="fail", reason="columns or row count differ",
                      columns_regenerated=list(left.columns), columns_frozen=list(right.columns))
        return result, None
    if sort_keys:
        left = left.sort_values(sort_keys, kind="mergesort").reset_index(drop=True)
        right = right.sort_values(sort_keys, kind="mergesort").reset_index(drop=True)
    if "detector" in right.columns:
        lstm_rows = (right["detector"].astype(str) == "lstm_autoencoder").to_numpy()
    else:
        lstm_rows = np.full(len(right), lstm_only)
    status, summary, records = "exact", {}, []
    for column in right.columns:
        a, b = left[column], right[column]
        numeric = pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b)
        if numeric:
            av, bv = a.to_numpy(dtype=np.float64), b.to_numpy(dtype=np.float64)
            with np.errstate(invalid="ignore"):
                difference = np.abs(av - bv)
            equal = (av == bv) | (np.isnan(av) & np.isnan(bv))
            if atol > 0:
                equal |= difference <= atol
        else:
            equal = (a.astype(str) == b.astype(str)).to_numpy()
        bad = np.flatnonzero(~equal)
        if bad.size == 0:
            if numeric and atol > 0 and np.any(difference > 0):
                summary[column] = {"cells_nonzero_within_atol": int(np.sum(difference > 0)),
                                   "max_abs_diff": float(np.nanmax(difference))}
                status = "within_atol" if status == "exact" else status
            continue
        entry = {"cells": int(bad.size)}
        tolerated = False
        if numeric:
            scale = np.maximum(np.abs(bv[bad]), np.finfo(np.float64).tiny)
            relative = difference[bad] / scale
            entry.update(max_abs_diff=float(np.nanmax(difference[bad])),
                         max_rel_diff=float(np.nanmax(relative)))
            tolerated = (atol == 0 and column not in COUNT_COLUMNS
                         and bool(np.all(lstm_rows[bad]))
                         and bool(np.nanmax(relative) <= LSTM_THRESHOLD_RTOL))
        summary[column] = entry
        if not tolerated:
            status = "fail"
        elif status in ("exact", "within_atol"):
            status = "lstm_tolerance"
        for row in bad[:25]:
            records.append({"table": name, "column": column, "row": int(row),
                            "regenerated": a.iloc[row], "frozen": b.iloc[row]})
    result.update(status=status, mismatched_columns=summary)
    return result, (pd.DataFrame(records) if records else None)


def compare_threshold_sets(recomputed, frozen):
    """Compare {run: {target: {pooled, climb, cruise, descent}}} threshold sets."""
    rows, status = [], "exact"
    if set(recomputed) != set(frozen):
        return "fail", pd.DataFrame([{"error": "run keys differ"}])
    for key in frozen:
        detector = key.split(":")[0]
        for target, entry in frozen[key].items():
            for name, value in entry.items():
                new = float(recomputed[key][target][name])
                absolute = abs(new - float(value))
                relative = absolute / abs(float(value)) if value else absolute
                exact = new == float(value)
                if not exact:
                    if detector == "lstm_autoencoder" and relative <= LSTM_THRESHOLD_RTOL:
                        status = "lstm_tolerance" if status == "exact" else status
                    else:
                        status = "fail"
                rows.append({"run": key, "nominal_fpr": target, "threshold": name,
                             "frozen": float(value), "recomputed": new, "exact": exact,
                             "abs_diff": absolute, "rel_diff": relative})
    return status, pd.DataFrame(rows)


def frozen_thresholds(spec):
    """Frozen pooled and per-phase calibration thresholds per run and target."""
    if spec.key == "ds03":
        return read_json(spec.frozen / spec.frozen_files["lock"])
    rates = pd.read_csv(spec.frozen / spec.frozen_files["rates"], float_precision="round_trip")
    transfer = pd.read_csv(spec.frozen / spec.frozen_files["transfer"], float_precision="round_trip")
    result = {}
    for detector, seed in RUNS:
        entry = {}
        for target in TARGETS:
            r = rates[(rates.detector == detector) & (rates.seed == seed)
                      & (rates.phase_definition == "primary") & (rates.nominal_fpr == target)
                      & (rates.unit.astype(str) == "all") & (rates.phase == "overall")]
            values = {"pooled": float(r.threshold.iloc[0])}
            for phase in PHASES:
                t = transfer[(transfer.detector == detector) & (transfer.seed == seed)
                             & (transfer.phase_definition == "primary")
                             & (transfer.nominal_fpr == target)
                             & (transfer.unit.astype(str) == "all")
                             & (transfer.calibration_phase == phase)
                             & (transfer.test_phase == phase)]
                values[phase] = float(t.threshold.iloc[0])
            entry[str(target)] = values
        result[f"{detector}:{seed}"] = entry
    return result


def gate_markdown(report):
    lines = [
        f"# Reproduction gate: {report['dataset'].upper()}",
        "",
        f"Overall status: **{report['overall_status']}**",
        "",
        f"Protocol {report['provenance']['protocol']} (SHA-256 "
        f"`{report['provenance']['protocol_sha256'][:16]}…`), git "
        f"`{report['provenance']['git']['head'][:12]}` on `{report['provenance']['git']['branch']}`.",
        f"Started {report['started_utc']}; finished {report['finished_utc']} "
        f"({report['seconds']} s).",
        "",
        "## Data read",
        "",
        f"- {report['data_read']}",
        f"- Healthy rows scored: calibration {report['rows']['calibration']:,}; "
        f"healthy audit {report['rows']['healthy_audit']:,}"
        + (f"; model-fit {report['rows']['model_fit']:,}" if report['rows'].get('model_fit') else "")
        + ".",
        f"- Abnormal (hs = 0) rows read: {report['abnormal_rows_read']}.",
        f"- HDF5 MD5 `{report['inputs']['h5_md5']}` matches provenance; baseline manifest "
        f"{report['inputs']['manifest']['entries']} files verified before the run and "
        f"{'verified' if report['manifest_after']['ok'] else 'FAILED'} after it.",
        "",
        "## Frozen tables regenerated with the unchanged frozen assembly code",
        "",
        "| Table | Frozen file | Rows | Status | Byte-identical |",
        "|---|---|---:|---|---|",
    ]
    for item in report["tables"]:
        lines.append(f"| {item['table']} | `{item['frozen_file']}` | {item['rows_frozen']} | "
                     f"{item['status']} | {'yes' if item['byte_identical'] else 'no'} |")
    if report.get("threshold_lock"):
        lock = report["threshold_lock"]
        lines += ["", "## Calibration thresholds against the frozen lock", "",
                  f"`{lock['frozen_file']}`: {lock['values_compared']} values, status "
                  f"**{lock['status']}**, exact {lock['exact_values']}/{lock['values_compared']}."]
    lines += ["", "## Environment", "",
              f"- Python {report['environment']['python']} ({report['environment']['executable']})",
              f"- GPU {report['environment']['gpu']}; CUDA {report['environment']['cuda_runtime']}; "
              f"cuDNN {report['environment']['cudnn']}",
              f"- Package mismatches against requirements-lock.txt: "
              f"{report['environment']['lock_mismatches'] or 'none'}",
              "", "No mitigation endpoint, flight threshold, or lock was computed in this stage.", ""]
    return "\n".join(lines)


def stage_c(spec, output_root):
    """Reproduction gate on healthy rows only (G1-G4); writes the gate report and fingerprints."""
    base = Path(output_root) / spec.key
    stage_b_record = base / "stage_b" / "stage_b_record.json"
    if not stage_b_record.exists() or not read_json(stage_b_record)["checks"]["ok"]:
        raise GateError(f"Stage B must pass before Stage C for {spec.key}")
    out = guard_output(base / "stage_c")
    started, clock = now_utc(), time.time()
    fv.configure_cuda_runtime()
    environment = environment_record()
    inputs = verify_inputs(spec)
    ctx = prepare_healthy_context(spec, score_train=spec.key == "ds02")
    regenerated, locked = REGENERATORS[spec.key](ctx)
    tables, mismatch_frames = [], []
    for name, frame in regenerated.items():
        filename = spec.frozen_files.get(name)
        if filename is None:
            continue
        result, mismatches = compare_table(
            name, frame, spec.frozen / filename,
            sort_keys=["detector", "seed", "metric"] if name == "bootstrap" else None,
            atol=BOOTSTRAP_ATOL if name == "bootstrap" else 0.0,
            lstm_only=name == "boundary")
        tables.append(result)
        if mismatches is not None:
            mismatch_frames.append(mismatches)
    statuses = [item["status"] for item in tables]
    threshold_report, threshold_table = None, None
    if locked is not None:
        lock_status, threshold_table = compare_threshold_sets(locked, frozen_thresholds(spec))
        statuses.append(lock_status)
        threshold_report = {
            "frozen_file": rel(spec.frozen / spec.frozen_files["lock"]), "status": lock_status,
            "values_compared": int(len(threshold_table)),
            "exact_values": int(threshold_table["exact"].sum()),
        }
    if any(status == "fail" for status in statuses):
        overall = "FAIL"
    elif all(status in ("exact", "within_atol") for status in statuses):
        overall = "PASS"
    else:
        overall = "PASS_WITH_LSTM_TOLERANCE"
    fingerprints = score_fingerprints(ctx)
    manifest_after = verify_manifest()
    report = {
        "stage": "C", "dataset": spec.key, "overall_status": overall,
        "started_utc": started, "finished_utc": now_utc(), "seconds": round(time.time() - clock, 1),
        "data_read": ("A arrays fully; W and X_s only as contiguous healthy (hs = 1) row blocks "
                      "of the development and official-test splits"),
        "abnormal_rows_read": False,
        "healthy_blocks": {split: [list(block) for block in blocks]
                           for split, blocks in ctx.blocks.items()},
        "rows": {"calibration": int(len(ctx.cal_meta)), "healthy_audit": int(len(ctx.test_meta)),
                 "model_fit": int(len(ctx.train_meta)) if ctx.train_scores is not None else None},
        "descriptor_names": ctx.descriptor_names, "timings_seconds": ctx.timings,
        "tables": tables, "threshold_lock": threshold_report, "environment": environment,
        "inputs": inputs, "manifest_after": manifest_after, "provenance": provenance_record(),
    }
    write_json(out / "gate_report.json", report)
    write_json(out / "score_fingerprints.json", fingerprints)
    if threshold_table is not None:
        write_csv(out / "threshold_comparison.csv", threshold_table)
    if mismatch_frames:
        write_csv(out / "mismatches.csv", pd.concat(mismatch_frames, ignore_index=True))
    write_new(out / "GATE_REPORT.md", gate_markdown(report))
    if overall == "FAIL" or not manifest_after["ok"]:
        raise GateError(f"Reproduction gate failed for {spec.key}; see {rel(out)}")
    return report


# ---------------------------------------------------------------------------
# Scheme thresholds, alarms, and flight statistics (pure functions)
# ---------------------------------------------------------------------------

def q_higher(values, q):
    values = np.asarray(values)
    if values.size == 0:
        raise GateError("Empty reference set for a calibration quantile")
    return float(np.quantile(values, q, method="higher"))


def scheme_taus(scores, phase, regime, alpha):
    q = 1 - alpha
    return {
        "pooled": q_higher(scores, q),
        "phase_conditioned": {name: q_higher(scores[phase == i], q)
                              for i, name in enumerate(PHASES)},
        "causal_regime": {name: q_higher(scores[regime == i], q)
                          for i, name in enumerate(REGIMES)},
    }


def row_thresholds(scheme, tau, phase, regime):
    if scheme == "pooled":
        return np.full(len(phase), tau["pooled"], dtype=np.float64)
    if scheme == "phase_conditioned":
        return np.asarray([tau["phase_conditioned"][p] for p in PHASES], dtype=np.float64)[phase]
    if scheme == "causal_regime":
        return np.asarray([tau["causal_regime"][r] for r in REGIMES], dtype=np.float64)[regime]
    raise ValueError(f"Unknown scheme: {scheme}")


def flight_bounds(meta):
    unit, cycle = meta.unit.to_numpy(), meta.cycle.to_numpy()
    boundary = np.flatnonzero((np.diff(unit) != 0) | (np.diff(cycle) != 0)) + 1
    return np.r_[0, boundary].astype(np.int64), np.r_[boundary, len(meta)].astype(np.int64)


def flight_alarm_counts(alarm, starts):
    return np.add.reduceat(np.asarray(alarm, dtype=np.int64), starts)


def lower_median(values):
    """Inverted-CDF median: always an observed value, so censored +/-inf never averages."""
    return float(np.quantile(np.asarray(values, dtype=np.float64), 0.5, method="inverted_cdf"))


def first_flag(flagged):
    hits = np.flatnonzero(flagged)
    return float(hits[0]) if hits.size else math.inf


def persistence_flag(flagged, run=PERSISTENCE_FLIGHTS):
    flagged = np.asarray(flagged, dtype=bool)
    for k in range(run - 1, len(flagged)):
        if flagged[k - run + 1:k + 1].all():
            return float(k)
    return math.inf


def delay_difference(delay_scheme, delay_pooled):
    """D_S - D_P with both-censored = 0, only-S-censored = +inf, only-P-censored = -inf."""
    delay_scheme = np.asarray(delay_scheme, dtype=np.float64)
    delay_pooled = np.asarray(delay_pooled, dtype=np.float64)
    with np.errstate(invalid="ignore"):
        difference = delay_scheme - delay_pooled
    difference[np.isinf(delay_scheme) & np.isinf(delay_pooled)] = 0.0
    return difference


def calibration_p_values(scores, labels, cal_scores, cal_labels, values):
    """Arm calibration p-value (1 + #{reference >= s}) / (1 + n_reference)."""
    p = np.full(len(scores), np.nan)
    for value in values:
        if value is None:
            reference, mask = np.sort(cal_scores), np.ones(len(scores), dtype=bool)
        else:
            reference, mask = np.sort(cal_scores[cal_labels == value]), labels == value
        greater_equal = len(reference) - np.searchsorted(reference, scores[mask], side="left")
        p[mask] = (1 + greater_equal) / (1 + len(reference))
    return p


def partial_auc(negative, positive, max_fpr=PAUC_MAX_FPR):
    """Normalized area under the trapezoidal ROC up to max_fpr (higher statistic = abnormal)."""
    values = np.concatenate([negative, positive]).astype(np.float64)
    labels = np.r_[np.zeros(len(negative), dtype=bool), np.ones(len(positive), dtype=bool)]
    order = np.argsort(-values, kind="stable")
    values, labels = values[order], labels[order]
    group_end = np.r_[np.flatnonzero(values[1:] != values[:-1]), len(values) - 1]
    tp = np.cumsum(labels)[group_end]
    fp = np.cumsum(~labels)[group_end]
    fpr = np.r_[0.0, fp / len(negative)]
    tpr = np.r_[0.0, tp / len(positive)]
    beyond = np.flatnonzero(fpr > max_fpr)
    if beyond.size == 0:
        x, y = fpr, tpr
    else:
        i = int(beyond[0])
        edge = tpr[i - 1] + (tpr[i] - tpr[i - 1]) * (max_fpr - fpr[i - 1]) / (fpr[i] - fpr[i - 1])
        x, y = np.r_[fpr[:i], max_fpr], np.r_[tpr[:i], edge]
    return float(np.trapezoid(y, x) / max_fpr)


# ---------------------------------------------------------------------------
# Stage L: calibration-only lock (tau and kappa for every run, target, and arm)
# ---------------------------------------------------------------------------

def build_mitigation_lock(dataset, cal_scores, cal_meta, cal_regime):
    phase = cal_meta.phase_primary.to_numpy()
    starts, ends = flight_bounds(cal_meta)
    rows = ends - starts
    n_flights = int(len(starts))
    lock = {
        "protocol": "docs/mssp/post_confirmation_mitigation_protocol.md (FROZEN v1.0)",
        "dataset": dataset,
        "status": "calibration-only; locked before any abnormal sensor row is opened",
        "schemes": list(SCHEMES), "phases": list(PHASES), "regimes": list(REGIMES),
        "targets": list(TARGETS), "flight_false_flag_target": FLIGHT_FALSE_FLAG_TARGET,
        "calibration_units": sorted(int(u) for u in np.unique(cal_meta.unit)),
        "calibration_rows": {
            "total": int(len(phase)),
            "phase": {p: int(np.sum(phase == i)) for i, p in enumerate(PHASES)},
            "regime": {r: int(np.sum(cal_regime == i)) for i, r in enumerate(REGIMES)},
        },
        "calibration_flights": n_flights,
        "kappa_order_statistic_index": int(math.ceil((1 - FLIGHT_FALSE_FLAG_TARGET) * (n_flights - 1))),
        "runs": {},
    }
    for (detector, seed), scores in cal_scores.items():
        entry = {}
        for alpha in TARGETS:
            tau = scheme_taus(scores, phase, cal_regime, alpha)
            kappa, flag_rate, row_rate = {}, {}, {}
            for scheme in SCHEMES:
                alarm = scores > row_thresholds(scheme, tau, phase, cal_regime)
                fraction = flight_alarm_counts(alarm, starts) / rows
                kappa[scheme] = q_higher(fraction, 1 - FLIGHT_FALSE_FLAG_TARGET)
                flag_rate[scheme] = float(np.mean(fraction > kappa[scheme]))
                row_rate[scheme] = float(np.mean(alarm))
            entry[str(alpha)] = {"tau": tau, "kappa": kappa,
                                 "calibration_flight_false_flag_rate": flag_rate,
                                 "calibration_row_alarm_rate": row_rate}
        lock["runs"][f"{detector}:{seed}"] = entry
    return lock


def lock_threshold_view(lock):
    """Pooled and per-phase tau from a mitigation lock, in the frozen threshold-set layout."""
    return {key: {target: {"pooled": values["tau"]["pooled"],
                           **{p: values["tau"]["phase_conditioned"][p] for p in PHASES}}
                  for target, values in entry.items()}
            for key, entry in lock["runs"].items()}


def load_verified_lock(dataset_root):
    lock_path = Path(dataset_root) / "stage_l" / "mitigation_lock.json"
    record = read_json(Path(dataset_root) / "stage_l" / "lock_record.json")
    digest = file_digest(lock_path)
    if digest != record["mitigation_lock_sha256"]:
        raise GateError("mitigation_lock.json does not match its recorded SHA-256")
    return read_json(lock_path), digest


def stage_l(spec, output_root):
    base = Path(output_root) / spec.key
    out = guard_output(base / "stage_l")
    started, clock = now_utc(), time.time()
    fv.configure_cuda_runtime()
    inputs = verify_inputs(spec)
    ctx = prepare_healthy_context(spec)
    gate = verify_fingerprints(ctx, base)
    cal_regime = causal_regime(ctx.cal_alt, ctx.cal_meta.unit.to_numpy(), ctx.cal_meta.cycle.to_numpy())
    lock = build_mitigation_lock(spec.key, ctx.cal_scores, ctx.cal_meta, cal_regime)
    status, table = compare_threshold_sets(lock_threshold_view(lock), frozen_thresholds(spec))
    if status == "fail":
        raise GateError(f"Lock thresholds differ from the frozen thresholds for {spec.key}")
    digest = write_json(out / "mitigation_lock.json", lock)
    write_csv(out / "lock_vs_frozen_thresholds.csv", table)
    write_json(out / "lock_record.json", {
        "stage": "L", "dataset": spec.key, "mitigation_lock_sha256": digest,
        "frozen_threshold_status": status, "gate_status": gate["overall_status"],
        "started_utc": started, "finished_utc": now_utc(), "seconds": round(time.time() - clock, 1),
        "data_read": "healthy calibration and healthy audit row blocks only (fingerprint check)",
        "abnormal_rows_read": False, "inputs": inputs, "provenance": provenance_record(),
    })
    return lock


# ---------------------------------------------------------------------------
# Vectorized bootstrap machinery
# ---------------------------------------------------------------------------

class CellCounter:
    """Count scores above per-cell thresholds using global ranks and one search."""

    def __init__(self, scores, cells, n_cells):
        scores = np.asarray(scores, dtype=np.float64)
        cells = np.asarray(cells, dtype=np.int64)
        order = np.argsort(scores, kind="stable")
        self.sorted_scores = scores[order]
        rank = np.empty(len(scores), dtype=np.int64)
        rank[order] = np.arange(len(scores), dtype=np.int64)
        self.stride = np.int64(len(scores) + 1)
        self.keys = np.sort(cells * self.stride + rank)
        self.n_cells = int(n_cells)
        self.offsets = np.arange(self.n_cells, dtype=np.int64) * self.stride
        self.base = np.searchsorted(self.keys, self.offsets)
        self.sizes = np.bincount(cells, minlength=self.n_cells).astype(np.int64)

    def above(self, thresholds):
        thresholds = np.broadcast_to(np.asarray(thresholds, dtype=np.float64), (self.n_cells,))
        at_or_below = np.searchsorted(self.sorted_scores, thresholds, side="right").astype(np.int64)
        return self.sizes - (np.searchsorted(self.keys, self.offsets + at_or_below) - self.base)


def sorted_view(scores, labels, flights, value=None):
    """Generalized frozen `sorted_calibration_view` for any per-row label."""
    pieces, ids = [], []
    for flight_id, (_, _, index) in enumerate(flights):
        if value is not None:
            index = index[labels[index] == value]
        pieces.append(scores[index])
        ids.append(np.full(len(index), flight_id, dtype=np.int16))
    values = np.concatenate(pieces)
    flight_ids = np.concatenate(ids)
    order = np.argsort(values, kind="quicksort")
    return values[order], flight_ids[order]


def flight_cells(flights, n_rows, phase, regime):
    flight_of_row = np.empty(n_rows, dtype=np.int64)
    for flight_id, (_, _, index) in enumerate(flights):
        flight_of_row[index] = flight_id
    return (flight_of_row * 3 + phase.astype(np.int64)) * 3 + regime.astype(np.int64)


class CalibrationViews:
    def __init__(self, scores, phase, regime, flights):
        self.pooled = sorted_view(scores, None, flights)
        self.phase = [sorted_view(scores, phase, flights, i) for i in range(3)]
        self.regime = [sorted_view(scores, regime, flights, i) for i in range(3)]

    def taus(self, multiplicity, q):
        return {
            "pooled": fv.weighted_higher_quantile(*self.pooled, multiplicity, q),
            "phase_conditioned": np.array([fv.weighted_higher_quantile(*v, multiplicity, q)
                                           for v in self.phase]),
            "causal_regime": np.array([fv.weighted_higher_quantile(*v, multiplicity, q)
                                       for v in self.regime]),
        }


def cell_thresholds(scheme, taus, cell_phase, cell_regime):
    if scheme == "pooled":
        return np.full(len(cell_phase), taus["pooled"])
    if scheme == "phase_conditioned":
        return taus["phase_conditioned"][cell_phase]
    return taus["causal_regime"][cell_regime]


class U1Run:
    """Paired healthy bootstrap for one detector run (plans reproduce the frozen procedure)."""

    def __init__(self, cal_scores, cal_phase, cal_regime, cal_flights,
                 test_scores, test_phase, test_regime, test_flights):
        self.views = CalibrationViews(cal_scores, cal_phase, cal_regime, cal_flights)
        n_flights = len(test_flights)
        cells = flight_cells(test_flights, len(test_scores), test_phase, test_regime)
        self.counter = CellCounter(test_scores, cells, n_flights * 9)
        index = np.arange(n_flights * 9)
        self.cell_flight, self.cell_phase, self.cell_regime = index // 9, (index // 3) % 3, index % 3
        self.sizes = self.counter.sizes.astype(np.float64)

    def replicate(self, cal_multiplicity, test_multiplicity, alpha=PRIMARY_TARGET):
        taus = self.views.taus(cal_multiplicity, 1 - alpha)
        weight = test_multiplicity[self.cell_flight].astype(np.float64)
        rows = np.bincount(self.cell_phase, weights=weight * self.sizes, minlength=3)
        flight_weight = test_multiplicity.astype(np.float64)
        out = {}
        for scheme in SCHEMES:
            above = self.counter.above(cell_thresholds(scheme, taus, self.cell_phase, self.cell_regime))
            alarms = np.bincount(self.cell_phase, weights=weight * above, minlength=3)
            fpr = alarms / rows
            out[f"{scheme}.overall_fpr"] = alarms.sum() / rows.sum()
            for i, phase in enumerate(PHASES):
                out[f"{scheme}.{phase}_fpr"] = fpr[i]
            out[f"{scheme}.descent_minus_climb"] = fpr[2] - fpr[0]
            out[f"{scheme}.descent_minus_cruise"] = fpr[2] - fpr[1]
            out[f"{scheme}.spread"] = fpr.max() - fpr.min()
            out[f"{scheme}.mpce"] = np.abs(fpr - alpha).max()
            any_alarm = above.reshape(-1, 3, 3).sum(axis=2) > 0
            for i, phase in enumerate(PHASES):
                out[f"{scheme}.flights_with_alarm_{phase}"] = (
                    (flight_weight * any_alarm[:, i]).sum() / flight_weight.sum())
        for scheme in ALTERNATIVES:
            out[f"delta_spread.{scheme}"] = out["pooled.spread"] - out[f"{scheme}.spread"]
            out[f"delta_mpce.{scheme}"] = out["pooled.mpce"] - out[f"{scheme}.mpce"]
        transfer = []
        for i in range(3):
            above = self.counter.above(np.full(len(self.cell_phase), taus["phase_conditioned"][i]))
            alarms = np.bincount(self.cell_phase, weights=weight * above, minlength=3)
            transfer += [alarms[j] / rows[j] for j in range(3) if j != i]
        out["pooled.worst_cross_phase_transfer_fpr"] = max(transfer)
        return out


def summarize_replicates(records, method_for=lambda metric: "linear"):
    rows = []
    for metric in records[0]:
        values = np.array([record[metric] for record in records], dtype=np.float64)
        method = method_for(metric)
        rows.append({
            "metric": metric, "replicates": len(values),
            "bootstrap_mean": float(np.mean(values)),
            "bootstrap_median": float(np.quantile(values, 0.5, method="inverted_cdf")),
            "ci_lower_95": float(np.quantile(values, .025, method=method)),
            "ci_upper_95": float(np.quantile(values, .975, method=method)),
            "ci_method": f"percentile ({method})",
        })
    return rows


def u1_bootstrap(cal_scores, cal_meta, cal_regime, test_scores, test_meta, test_regime,
                 *, runs=RUNS, replicates=REPLICATES, seed=U1_SEED, alpha=PRIMARY_TARGET):
    rng = np.random.default_rng(seed)
    cal_flights, cal_plans = fv.bootstrap_plans(cal_meta, replicates, rng)
    test_flights, test_plans = fv.bootstrap_plans(test_meta, replicates, rng)
    rows = []
    for name in runs:
        run = U1Run(cal_scores[name], cal_meta.phase_primary.to_numpy(), cal_regime, cal_flights,
                    test_scores[name], test_meta.phase_primary.to_numpy(), test_regime, test_flights)
        records = [run.replicate(cal_plans[b], test_plans[b], alpha) for b in range(replicates)]
        for row in summarize_replicates(records):
            rows.append({"detector": name[0], "seed": name[1], "nominal_fpr": alpha,
                         "bootstrap_unit": "engine_then_flight", "threshold_reestimated": True,
                         **row})
        print(f"U1 complete: {name}", flush=True)
    return pd.DataFrame(rows)


def u1_frozen_self_check(u1, frozen_path):
    """Pooled-arm U1 summaries must equal the frozen bootstrap CSV within 1e-12."""
    frozen = pd.read_csv(frozen_path, float_precision="round_trip")
    worst = 0.0
    for row in frozen.itertuples(index=False):
        match = u1[(u1.detector == row.detector) & (u1.seed == row.seed)
                   & (u1.metric == f"pooled.{row.metric}")]
        if len(match) != 1:
            raise GateError(f"U1 self-check: missing {row.detector}/{row.seed}/{row.metric}")
        for column in ("bootstrap_mean", "ci_lower_95", "ci_upper_95"):
            worst = max(worst, abs(float(match[column].iloc[0]) - float(getattr(row, column))))
    if worst > BOOTSTRAP_ATOL:
        raise GateError(f"U1 pooled arm differs from the frozen bootstrap by {worst}")
    return worst


class U2Run:
    """Paired abnormal-state and delay bootstrap for one detector run."""

    def __init__(self, cal_scores, cal_phase, cal_regime, cal_flights,
                 audit_scores, audit_phase, audit_regime, flights, engines):
        self.views = CalibrationViews(cal_scores, cal_phase, cal_regime, cal_flights)
        cal_cells = flight_cells(cal_flights, len(cal_scores), cal_phase, cal_regime)
        self.cal_counter = CellCounter(cal_scores, cal_cells, len(cal_flights) * 9)
        self.cal_rows = np.array([len(index) for _, _, index in cal_flights], dtype=np.float64)
        audit_flights = [(None, None, np.arange(s, e)) for s, e in zip(flights.start, flights.end)]
        cells = flight_cells(audit_flights, len(audit_scores), audit_phase, audit_regime)
        self.counter = CellCounter(audit_scores, cells, len(flights) * 9)
        self.rows = flights.rows.to_numpy(dtype=np.float64)
        self.post = (flights.state == "post_onset").to_numpy()
        self.early = flights.early.to_numpy(dtype=bool)
        self.healthy = (flights.state == "healthy").to_numpy()
        unit_array, k_array = flights.unit.to_numpy(), flights.k.to_numpy()
        self.post_order = []
        for unit in engines:
            members = np.flatnonzero((unit_array == unit) & self.post)
            self.post_order.append(members[np.argsort(k_array[members], kind="stable")])
        cal_index = np.arange(len(cal_flights) * 9)
        self.cal_phase, self.cal_regime = (cal_index // 3) % 3, cal_index % 3
        index = np.arange(len(flights) * 9)
        self.cell_phase, self.cell_regime = (index // 3) % 3, index % 3

    def replicate(self, cal_multiplicity, flight_multiplicity, engine_multiplicity,
                  alpha=PRIMARY_TARGET):
        taus = self.views.taus(cal_multiplicity, 1 - alpha)
        w = flight_multiplicity.astype(np.float64)
        out, delays = {}, {}
        for scheme in SCHEMES:
            cal_alarms = self.cal_counter.above(
                cell_thresholds(scheme, taus, self.cal_phase, self.cal_regime)).reshape(-1, 9).sum(1)
            fraction = cal_alarms / self.cal_rows
            order = np.argsort(fraction, kind="quicksort")
            kappa = fv.weighted_higher_quantile(fraction[order], order, cal_multiplicity,
                                                1 - FLIGHT_FALSE_FLAG_TARGET)
            alarms = self.counter.above(
                cell_thresholds(scheme, taus, self.cell_phase, self.cell_regime)).reshape(-1, 9).sum(1)
            flagged = alarms / self.rows > kappa
            post, early, healthy = self.post, self.early, self.healthy
            out[f"{scheme}.tpr"] = (w[post] * alarms[post]).sum() / (w[post] * self.rows[post]).sum()
            out[f"{scheme}.tpr_early"] = ((w[early] * alarms[early]).sum()
                                          / (w[early] * self.rows[early]).sum())
            out[f"{scheme}.ffr"] = (w[healthy] * flagged[healthy]).sum() / w[healthy].sum()
            delays[scheme] = np.array([first_flag(flagged[index]) for index in self.post_order])
            out[f"{scheme}.median_delay"] = lower_median(np.repeat(delays[scheme], engine_multiplicity))
            out[f"{scheme}.kappa"] = kappa
        for scheme in ALTERNATIVES:
            out[f"delta_tpr.{scheme}"] = out[f"{scheme}.tpr"] - out["pooled.tpr"]
            out[f"ratio_tpr.{scheme}"] = out[f"{scheme}.tpr"] / out["pooled.tpr"]
            out[f"ratio_tpr_early.{scheme}"] = out[f"{scheme}.tpr_early"] / out["pooled.tpr_early"]
            out[f"delta_ffr.{scheme}"] = out[f"{scheme}.ffr"] - out["pooled.ffr"]
            difference = delay_difference(delays[scheme], delays["pooled"])
            out[f"median_delta_delay.{scheme}"] = lower_median(np.repeat(difference, engine_multiplicity))
        return out


def audit_engine_plans(flights, engines, replicates, rng):
    """Engines with replacement; flights with replacement within healthy and post-onset segments."""
    healthy = {u: flights.index[(flights.unit == u) & (flights.state == "healthy")].to_numpy()
               for u in engines}
    post = {u: flights.index[(flights.unit == u) & (flights.state == "post_onset")].to_numpy()
            for u in engines}
    engine_plans = np.zeros((replicates, len(engines)), dtype=np.int64)
    flight_plans = np.zeros((replicates, len(flights)), dtype=np.int64)
    for b in range(replicates):
        for e in rng.choice(len(engines), size=len(engines), replace=True):
            engine_plans[b, e] += 1
            for members in (healthy[engines[e]], post[engines[e]]):
                if len(members):
                    np.add.at(flight_plans[b], rng.choice(members, size=len(members), replace=True), 1)
    return engine_plans, flight_plans


def u2_method(metric):
    return "inverted_cdf" if "delay" in metric else "linear"


def u2_bootstrap(cal_scores, cal_meta, cal_regime, audit_scores, audit_meta, audit_regime,
                 flights, engines, *, runs=RUNS, replicates=REPLICATES, seed=U2_SEED,
                 alpha=PRIMARY_TARGET):
    rng = np.random.default_rng(seed)
    cal_flights, cal_plans = fv.bootstrap_plans(cal_meta, replicates, rng)
    engine_plans, flight_plans = audit_engine_plans(flights, engines, replicates, rng)
    rows = []
    for name in runs:
        run = U2Run(cal_scores[name], cal_meta.phase_primary.to_numpy(), cal_regime, cal_flights,
                    audit_scores[name], audit_meta.phase_primary.to_numpy(), audit_regime,
                    flights, engines)
        records = [run.replicate(cal_plans[b], flight_plans[b], engine_plans[b], alpha)
                   for b in range(replicates)]
        for row in summarize_replicates(records, u2_method):
            rows.append({"detector": name[0], "seed": name[1], "nominal_fpr": alpha,
                         "bootstrap_unit": "calibration engine->flight; audit engine->segment flights",
                         "threshold_reestimated": True, **row})
        print(f"U2 complete: {name}", flush=True)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Stage D: healthy endpoints (H, E, D2, C' feasibility, U1)
# ---------------------------------------------------------------------------

def unit_groups(units):
    return [(str(int(u)), units == u) for u in sorted(np.unique(units))] + [
        ("all", np.ones(len(units), dtype=bool))]


def rate_records(alarm, units, phase):
    records = []
    for name, mask in unit_groups(units):
        for phase_id, phase_name in ((None, "overall"), *enumerate(PHASES)):
            selected = mask if phase_id is None else mask & (phase == phase_id)
            n, k = int(selected.sum()), int(alarm[selected].sum())
            records.append({"unit": name, "phase": phase_name, "n": n, "alarms": k,
                            "rate": k / n if n else float("nan")})
    return records


def stability(rate_by_phase, alpha):
    values = np.array([rate_by_phase[p] for p in PHASES], dtype=np.float64)
    return {"spread": float(values.max() - values.min()),
            "mpce": float(np.max(np.abs(values - alpha))),
            "descent_minus_climb": float(values[2] - values[0]),
            "descent_minus_cruise": float(values[2] - values[1])}


def flight_burden_records(alarm, meta):
    starts, ends = flight_bounds(meta)
    phase, units = meta.phase_primary.to_numpy(), meta.unit.to_numpy()
    detail = []
    for start, end in zip(starts, ends):
        segment, segment_phase = alarm[start:end], phase[start:end]
        entry = {"unit": int(units[start])}
        for phase_id, name in ((None, "overall"), *enumerate(PHASES)):
            part = segment if phase_id is None else segment[segment_phase == phase_id]
            entry[f"any_{name}"] = int(part.any())
            entry[f"events_{name}"] = count_events(part)
        detail.append(entry)
    detail = pd.DataFrame(detail)
    records = []
    for name, part in [(str(u), g) for u, g in detail.groupby("unit")] + [("all", detail)]:
        for phase_name in ("overall", *PHASES):
            records.append({"unit": name, "phase": phase_name, "flights": int(len(part)),
                            "fraction_flights_with_alarm": float(part[f"any_{phase_name}"].mean()),
                            "events_per_flight": float(part[f"events_{phase_name}"].mean())})
    return records


def flight_flag_records(alarm, meta, kappa):
    starts, ends = flight_bounds(meta)
    fraction = flight_alarm_counts(alarm, starts) / (ends - starts)
    flagged = fraction > kappa
    units = meta.unit.to_numpy()[starts]
    records = []
    for name, mask in unit_groups(units):
        pairs = 0
        for unit in (np.unique(units) if name == "all" else [int(name)]):
            f = flagged[units == unit]
            pairs += int(np.sum(f[1:] & f[:-1]))
        records.append({"unit": name, "flights": int(mask.sum()), "flagged": int(flagged[mask].sum()),
                        "false_flag_rate": float(flagged[mask].mean()),
                        "consecutive_flagged_pairs": pairs})
    return records


def healthy_endpoint_tables(dataset, lock, test_scores, test_meta, test_regime):
    phase, units = test_meta.phase_primary.to_numpy(), test_meta.unit.to_numpy()
    rates, stab, shares, burden, flags = [], [], [], [], []
    for detector, seed in RUNS:
        scores = test_scores[(detector, seed)]
        entry = lock["runs"][f"{detector}:{seed}"]
        for alpha in TARGETS:
            tau, kappa = entry[str(alpha)]["tau"], entry[str(alpha)]["kappa"]
            for scheme in SCHEMES:
                alarm = scores > row_thresholds(scheme, tau, phase, test_regime)
                base = {"dataset": dataset, "detector": detector, "seed": seed,
                        "nominal_fpr": alpha, "scheme": scheme, "arm_status": ARM_STATUS[scheme]}
                table = rate_records(alarm, units, phase)
                rates += [{**base, **row} for row in table]
                lookup = {(row["unit"], row["phase"]): row for row in table}
                for name in dict.fromkeys(row["unit"] for row in table):
                    values = {p: lookup[(name, p)]["rate"] for p in PHASES}
                    stab.append({**base, "unit": name,
                                 "overall_fpr": lookup[(name, "overall")]["rate"],
                                 **stability(values, alpha)})
                total = lookup[("all", "overall")]
                for p in PHASES:
                    shares.append({**base, "phase": p,
                                   "alarm_share": (lookup[("all", p)]["alarms"] / total["alarms"]
                                                   if total["alarms"] else float("nan")),
                                   "row_share": lookup[("all", p)]["n"] / total["n"]})
                burden += [{**base, **row} for row in flight_burden_records(alarm, test_meta)]
                flags += [{**base, "kappa": kappa[scheme], **row}
                          for row in flight_flag_records(alarm, test_meta, kappa[scheme])]
    rates, stab = pd.DataFrame(rates), pd.DataFrame(stab)
    keys = ["dataset", "detector", "seed", "nominal_fpr", "unit"]
    pooled = stab[stab.scheme == "pooled"][keys + ["spread", "mpce"]]
    paired = stab[stab.scheme != "pooled"].merge(pooled, on=keys, suffixes=("", "_pooled"))
    paired["delta_spread"] = paired.spread_pooled - paired.spread
    paired["delta_mpce"] = paired.mpce_pooled - paired.mpce
    engines = rates[(rates.unit != "all") & rates.phase.isin(PHASES)]
    hetero = []
    for (dataset_, detector, seed, alpha, scheme), part in engines.groupby(
            ["dataset", "detector", "seed", "nominal_fpr", "scheme"], sort=False):
        for p in PHASES:
            values = part[part.phase == p].rate.to_numpy()
            hetero.append({"dataset": dataset_, "detector": detector, "seed": seed,
                           "nominal_fpr": alpha, "scheme": scheme, "phase": p,
                           "engine_range": float(values.max() - values.min()),
                           "engine_sd": float(np.std(values, ddof=1)) if len(values) > 1 else float("nan"),
                           "engine_max": float(values.max())})
        hetero.append({"dataset": dataset_, "detector": detector, "seed": seed, "nominal_fpr": alpha,
                       "scheme": scheme, "phase": "all_engine_phase_cells",
                       "engine_max": float(part.rate.max()),
                       "exceedance_cells_above_2alpha": int(np.sum(part.rate > EXCEEDANCE_MULTIPLE * alpha)),
                       "cells": int(len(part))})
    per_engine = paired[paired.unit != "all"]
    signs = per_engine.groupby(["dataset", "detector", "seed", "nominal_fpr", "scheme"]).agg(
        engines=("unit", "size"), engines_spread_reduced=("delta_spread", lambda v: int(np.sum(v > 0))),
        engines_mpce_reduced=("delta_mpce", lambda v: int(np.sum(v > 0)))).reset_index()
    return {"healthy_phase_fpr_by_scheme": rates, "healthy_stability_by_scheme": stab,
            "healthy_paired_stability": paired, "engine_heterogeneity": pd.DataFrame(hetero),
            "engine_sign_counts": signs, "healthy_alarm_share": pd.DataFrame(shares),
            "healthy_flight_burden_by_scheme": pd.DataFrame(burden),
            "healthy_flight_false_flags": pd.DataFrame(flags)}


def calibration_source_table(dataset, cal_units, cal_scores, cal_meta, cal_regime,
                             test_scores, test_meta, test_regime):
    """E4: thresholds of each arm estimated from one calibration engine alone."""
    cal_phase, cal_unit = cal_meta.phase_primary.to_numpy(), cal_meta.unit.to_numpy()
    phase, units = test_meta.phase_primary.to_numpy(), test_meta.unit.to_numpy()
    rows = []
    for source in cal_units:
        mask = cal_unit == source
        for detector, seed in RUNS:
            for alpha in TARGETS:
                tau = scheme_taus(cal_scores[(detector, seed)][mask], cal_phase[mask],
                                  cal_regime[mask], alpha)
                for scheme in SCHEMES:
                    alarm = test_scores[(detector, seed)] > row_thresholds(scheme, tau, phase, test_regime)
                    table = rate_records(alarm, units, phase)
                    lookup = {(row["unit"], row["phase"]): row["rate"] for row in table}
                    for name in dict.fromkeys(row["unit"] for row in table):
                        rows.append({"dataset": dataset, "calibration_source_engine": int(source),
                                     "detector": detector, "seed": seed, "nominal_fpr": alpha,
                                     "scheme": scheme, "unit": name,
                                     "overall_fpr": lookup[(name, "overall")],
                                     **{f"{p}_fpr": lookup[(name, p)] for p in PHASES},
                                     **stability({p: lookup[(name, p)] for p in PHASES}, alpha)})
    return pd.DataFrame(rows)


def regime_feasibility_table(dataset, subsets):
    rows = []
    for subset, (phase, regime) in subsets.items():
        for i, p in enumerate(PHASES):
            in_phase = int(np.sum(phase == i))
            for j, r in enumerate(REGIMES):
                n = int(np.sum((phase == i) & (regime == j)))
                rows.append({"dataset": dataset, "subset": subset, "retrospective_phase": p,
                             "causal_regime": r, "rows": n, "share_of_rows": n / len(phase),
                             "share_within_phase": n / in_phase if in_phase else float("nan")})
    return pd.DataFrame(rows)


def stage_d(spec, output_root):
    base = Path(output_root) / spec.key
    lock, lock_digest = load_verified_lock(base)
    out = guard_output(base / "stage_d")
    started, clock = now_utc(), time.time()
    fv.configure_cuda_runtime()
    inputs = verify_inputs(spec)
    ctx = prepare_healthy_context(spec)
    verify_fingerprints(ctx, base)
    cal_regime = causal_regime(ctx.cal_alt, ctx.cal_meta.unit.to_numpy(), ctx.cal_meta.cycle.to_numpy())
    test_regime = causal_regime(ctx.test_alt, ctx.test_meta.unit.to_numpy(), ctx.test_meta.cycle.to_numpy())
    recomputed = build_mitigation_lock(spec.key, ctx.cal_scores, ctx.cal_meta, cal_regime)
    if canonical_json(recomputed) != canonical_json(lock):
        raise GateError("Recomputed calibration lock differs from mitigation_lock.json")
    tables = healthy_endpoint_tables(spec.key, lock, ctx.test_scores, ctx.test_meta, test_regime)
    tables["calibration_source_sensitivity"] = calibration_source_table(
        spec.key, spec.cal_units, ctx.cal_scores, ctx.cal_meta, cal_regime,
        ctx.test_scores, ctx.test_meta, test_regime)
    tables["causal_regime_feasibility"] = regime_feasibility_table(spec.key, {
        "calibration_healthy": (ctx.cal_meta.phase_primary.to_numpy(), cal_regime),
        "audit_healthy": (ctx.test_meta.phase_primary.to_numpy(), test_regime)})
    u1 = u1_bootstrap(ctx.cal_scores, ctx.cal_meta, cal_regime,
                      ctx.test_scores, ctx.test_meta, test_regime)
    worst = u1_frozen_self_check(u1, spec.frozen / spec.frozen_files["bootstrap"])
    tables["u1_bootstrap_ci"] = u1
    hashes = {name: write_csv(out / f"{name}.csv", frame) for name, frame in tables.items()}
    write_json(out / "stage_d_record.json", {
        "stage": "D", "dataset": spec.key, "mitigation_lock_sha256": lock_digest,
        "u1_frozen_self_check_max_abs_diff": worst, "outputs_sha256": hashes,
        "started_utc": started, "finished_utc": now_utc(), "seconds": round(time.time() - clock, 1),
        "abnormal_rows_read": False, "inputs": inputs, "provenance": provenance_record(),
    })
    return tables


# ---------------------------------------------------------------------------
# Stage E: abnormal-state endpoints (one-shot, explicit authorization)
# ---------------------------------------------------------------------------

def audit_flight_table(meta):
    starts, ends = flight_bounds(meta)
    healthy = meta.healthy.to_numpy()
    table = pd.DataFrame({
        "unit": meta.unit.to_numpy()[starts].astype(int),
        "cycle": meta.cycle.to_numpy()[starts].astype(int),
        "start": starts, "end": ends, "rows": ends - starts,
        "state": np.where(np.minimum.reduceat(healthy, starts) == 1, "healthy", "post_onset"),
    })
    table["k"] = -1
    for _, part in table[table.state == "post_onset"].groupby("unit", sort=False):
        table.loc[part.index, "k"] = np.arange(len(part))
    post_counts = table[table.state == "post_onset"].groupby("unit").size()
    table["post_onset_flights"] = table.unit.map(post_counts).fillna(0).astype(int)
    table["u"] = np.where(table.k >= 0, table.k / table.post_onset_flights.clip(lower=1), np.nan)
    table["early"] = (table.k >= 0) & (table.k < EARLY_WINDOW_FLIGHTS)
    return table


def combine_audit_rows(healthy_blocks, healthy, abnormal_blocks, abnormal):
    """Merge healthy and abnormal audit rows back into original split row order."""
    def indices(blocks):
        return np.concatenate([np.arange(s, e) for s, e in blocks]) if blocks else np.empty(0, int)
    order = np.argsort(np.r_[indices(healthy_blocks), indices(abnormal_blocks)], kind="stable")
    meta = pd.concat([healthy["meta"], abnormal["meta"]], ignore_index=True).iloc[order]
    scores = {name: np.r_[healthy["scores"][name], abnormal["scores"][name]][order]
              for name in healthy["scores"]}
    alt = np.r_[healthy["alt"], abnormal["alt"]][order]
    return scores, meta.reset_index(drop=True), alt


def abnormal_endpoint_tables(dataset, lock, cal_scores, cal_meta, cal_regime,
                             audit_scores, audit_meta, audit_regime, flights, eligible):
    phase, units = audit_meta.phase_primary.to_numpy(), audit_meta.unit.to_numpy()
    k_row = np.repeat(flights.k.to_numpy(), flights.rows.to_numpy())
    u_row = np.repeat(flights.u.to_numpy(), flights.rows.to_numpy())
    post_row = k_row >= 0
    in_s = np.isin(units, eligible["s1_s3_s4"])
    in_s2 = np.isin(units, eligible["s2"])
    quartile = np.digitize(np.nan_to_num(u_row, nan=-1.0), LIFE_BINS[1:-1])
    rates, trajectories, delays, flags = [], [], [], []
    for detector, seed in RUNS:
        scores = audit_scores[(detector, seed)]
        entry = lock["runs"][f"{detector}:{seed}"]
        for alpha in TARGETS:
            tau, kappa = entry[str(alpha)]["tau"], entry[str(alpha)]["kappa"]
            for scheme in SCHEMES:
                alarm = scores > row_thresholds(scheme, tau, phase, audit_regime)
                base = {"dataset": dataset, "detector": detector, "seed": seed,
                        "nominal_fpr": alpha, "scheme": scheme, "arm_status": ARM_STATUS[scheme]}
                windows = [("all_post_onset", post_row & in_s), ("early_first_10", post_row & in_s2 & (k_row < EARLY_WINDOW_FLIGHTS))]
                windows += [(f"life_q{q + 1}", post_row & in_s & (quartile == q)) for q in range(4)]
                for window, mask in windows:
                    for row in rate_records(alarm[mask], units[mask], phase[mask]):
                        rates.append({**base, "window": window, **row})
                counts = flight_alarm_counts(alarm, flights.start.to_numpy())
                fraction = counts / flights.rows.to_numpy()
                flagged = fraction > kappa[scheme]
                trajectories.append(flights.assign(**base, alarms=counts, alarm_fraction=fraction,
                                                   kappa=kappa[scheme], flagged=flagged))
                healthy_flights = (flights.state == "healthy").to_numpy()
                for name, mask in unit_groups(flights.unit.to_numpy()):
                    selected = mask & healthy_flights
                    flags.append({**base, "unit": name, "healthy_flights": int(selected.sum()),
                                  "flagged": int(flagged[selected].sum()),
                                  "false_flag_rate": float(flagged[selected].mean()) if selected.any() else float("nan"),
                                  "kappa": kappa[scheme]})
                for unit in sorted(np.unique(flights.unit)):
                    post = flights[(flights.unit == unit) & (flights.state == "post_onset")].sort_values("k")
                    healthy_f = flagged[((flights.unit == unit) & (flights.state == "healthy")).to_numpy()]
                    series = flagged[post.index.to_numpy()]
                    eligible_d = unit in eligible["d"]
                    d1, d3 = first_flag(series), persistence_flag(series)
                    delays.append({**base, "unit": int(unit), "eligible": eligible_d,
                                   "post_onset_flights": int(len(post)),
                                   "delay_flights": d1 if np.isfinite(d1) else float("nan"),
                                   "censored": bool(np.isinf(d1)),
                                   "persistence_delay_flights": d3 if np.isfinite(d3) else float("nan"),
                                   "persistence_censored": bool(np.isinf(d3)),
                                   "healthy_flights": int(len(healthy_f)),
                                   "healthy_flagged": int(healthy_f.sum()),
                                   "healthy_consecutive_flagged_pairs": int(np.sum(healthy_f[1:] & healthy_f[:-1])),
                                   "kappa": kappa[scheme]})
    delays = pd.DataFrame(delays)
    pauc = separability_table(dataset, cal_scores, cal_meta, cal_regime, audit_scores,
                              audit_meta, audit_regime, post_row & in_s,
                              post_row & in_s2 & (k_row < EARLY_WINDOW_FLIGHTS))
    return {"abnormal_alarm_rates": pd.DataFrame(rates),
            "flight_alarm_fraction_trajectories": pd.concat(trajectories, ignore_index=True),
            "detection_delay": delays, "healthy_flight_false_flags_with_delay": pd.DataFrame(flags),
            "separability_pauc": pauc,
            "guardrails": guardrail_table(dataset, pd.DataFrame(rates), delays)}


def separability_table(dataset, cal_scores, cal_meta, cal_regime, audit_scores, audit_meta,
                       audit_regime, positive_all, positive_early):
    phase = audit_meta.phase_primary.to_numpy()
    negative = (audit_meta.healthy.to_numpy() == 1)
    cal_phase = cal_meta.phase_primary.to_numpy()
    rows = []
    for detector, seed in RUNS:
        s, c = audit_scores[(detector, seed)], cal_scores[(detector, seed)]
        statistics = {
            "pooled": -calibration_p_values(s, phase, c, cal_phase, [None]),
            "phase_conditioned": -calibration_p_values(s, phase, c, cal_phase, range(3)),
            "causal_regime": -calibration_p_values(s, audit_regime, c, cal_regime, range(3)),
        }
        for scheme, statistic in statistics.items():
            for window, positive in (("all_post_onset", positive_all), ("early_first_10", positive_early)):
                rows.append({"dataset": dataset, "detector": detector, "seed": seed, "scheme": scheme,
                             "arm_status": ARM_STATUS[scheme], "window": window,
                             "negatives": int(negative.sum()), "positives": int(positive.sum()),
                             "normalized_pauc_fpr_0_to_0.02": partial_auc(
                                 statistic[negative], statistic[positive])})
    return pd.DataFrame(rows)


def guardrail_table(dataset, rates, delays, alpha=PRIMARY_TARGET):
    """IR-S interpretive guardrails (not non-inferiority margins) per family and arm."""
    pooled_rows = rates[(rates.unit == "all") & (rates.phase == "overall") & (rates.nominal_fpr == alpha)]
    rows = []
    for family in FAMILIES:
        runs = [r for r in RUNS if r[0] == family]
        for scheme in ALTERNATIVES:
            def seed_mean(window, arm):
                part = pooled_rows[(pooled_rows.detector == family) & (pooled_rows.scheme == arm)
                                   & (pooled_rows.window == window)]
                return float(part.rate.mean())
            ratio_all = seed_mean("all_post_onset", scheme) / seed_mean("all_post_onset", "pooled")
            ratio_early = seed_mean("early_first_10", scheme) / seed_mean("early_first_10", "pooled")
            d = delays[(delays.detector == family) & (delays.nominal_fpr == alpha) & delays.eligible]
            per_engine, censored_one_side = [], []
            for unit in sorted(d.unit.unique()):
                diffs = []
                for detector, seed in runs:
                    def delay(arm):
                        row = d[(d.seed == seed) & (d.unit == unit) & (d.scheme == arm)].iloc[0]
                        return math.inf if row.censored else float(row.delay_flights)
                    ds, dp = delay(scheme), delay("pooled")
                    diffs.append(float(delay_difference([ds], [dp])[0]))
                    if np.isinf(ds) != np.isinf(dp):
                        censored_one_side.append(f"{detector}:{seed}:engine_{unit}")
                per_engine.append(lower_median(diffs))
            change = lower_median(per_engine) if per_engine else float("nan")
            met = bool(ratio_all >= GUARDRAIL_RATIO and ratio_early >= GUARDRAIL_RATIO
                       and change <= GUARDRAIL_DELAY_FLIGHTS)
            rows.append({"dataset": dataset, "family": family, "scheme": scheme, "nominal_fpr": alpha,
                         "alarm_rate_ratio_all_post_onset": ratio_all,
                         "alarm_rate_ratio_early_first_10": ratio_early,
                         "family_median_delay_change_flights": change,
                         "engines_censored_under_one_arm": ";".join(censored_one_side),
                         "guardrails_met": met,
                         "guardrail_note": "interpretive guardrail, not a non-inferiority margin"})
    return pd.DataFrame(rows)


def stage_e(spec, output_root, *, authorize_abnormal_open=False):
    if not authorize_abnormal_open:
        raise PermissionError("Stage E requires explicit author approval (--authorize-abnormal-open)")
    base = Path(output_root) / spec.key
    lock, lock_digest = load_verified_lock(base)
    out = guard_output(base / "stage_e")
    started, clock = now_utc(), time.time()
    fv.configure_cuda_runtime()
    inputs = verify_inputs(spec)
    ctx = prepare_healthy_context(spec)
    verify_fingerprints(ctx, base)
    cal_regime = causal_regime(ctx.cal_alt, ctx.cal_meta.unit.to_numpy(), ctx.cal_meta.cycle.to_numpy())
    recomputed = build_mitigation_lock(spec.key, ctx.cal_scores, ctx.cal_meta, cal_regime)
    if canonical_json(recomputed) != canonical_json(lock):
        raise GateError("Recomputed calibration lock differs from mitigation_lock.json")
    label_table = pd.read_csv(base / "stage_b" / "label_structure.csv")
    audit_labels = label_table[label_table.role == "audit"]
    eligible = {"s1_s3_s4": audit_labels[audit_labels.eligible_s1_s3_s4].unit.tolist(),
                "s2": audit_labels[audit_labels.eligible_s2].unit.tolist(),
                "d": audit_labels[audit_labels.eligible_d].unit.tolist()}
    write_json(out / "abnormal_rows_opened.json", {
        "status": "abnormal_audit_rows_opened_once", "dataset": spec.key, "opened_utc": now_utc(),
        "mitigation_lock_sha256": lock_digest, "provenance": provenance_record()})
    with h5py.File(spec.h5_path, "r") as h5:
        ab_x, ab_w, ab_meta, ab_blocks = load_abnormal_audit(spec, h5)
    ab_desc, _ = causal_descriptors(ab_w, ab_meta)
    ab_scores, _ = score_rows(ctx.detectors, ab_x, ab_desc, ab_meta)
    audit_scores, audit_meta, audit_alt = combine_audit_rows(
        ctx.blocks["test"], {"meta": ctx.test_meta, "scores": ctx.test_scores, "alt": ctx.test_alt},
        ab_blocks, {"meta": ab_meta, "scores": ab_scores, "alt": ab_w[:, 0]})
    audit_regime = causal_regime(audit_alt, audit_meta.unit.to_numpy(), audit_meta.cycle.to_numpy())
    flights = audit_flight_table(audit_meta)
    tables = abnormal_endpoint_tables(spec.key, lock, ctx.cal_scores, ctx.cal_meta, cal_regime,
                                      audit_scores, audit_meta, audit_regime, flights, eligible)
    # U2 resamples only delay-eligible engines; flights of other engines keep zero multiplicity.
    engines = sorted(int(u) for u in eligible["d"])
    u2_flights = flights.assign(early=flights.early & flights.unit.isin(eligible["s2"]))
    tables["u2_bootstrap_ci"] = u2_bootstrap(
        ctx.cal_scores, ctx.cal_meta, cal_regime, audit_scores, audit_meta, audit_regime,
        u2_flights, engines)
    hashes = {name: write_csv(out / f"{name}.csv", frame) for name, frame in tables.items()}
    write_json(out / "stage_e_record.json", {
        "stage": "E", "dataset": spec.key, "mitigation_lock_sha256": lock_digest,
        "abnormal_rows_read": int(len(ab_meta)), "abnormal_blocks": [list(b) for b in ab_blocks],
        "eligible_engines": eligible, "outputs_sha256": hashes, "started_utc": started,
        "finished_utc": now_utc(), "seconds": round(time.time() - clock, 1),
        "inputs": inputs, "provenance": provenance_record(),
    })
    return tables


# ---------------------------------------------------------------------------
# Stage F: report (IR-H, IR-S, IR-T)
# ---------------------------------------------------------------------------

TEMPLATES = {
    (True, True): ("reduced the healthy phase-FPR spread relative to pooled calibration at the 1% "
                   "target, and abnormal-state alarm rate and detection delay stayed within the "
                   "pre-specified interpretive guardrails; intervals were wide with {n} audit engines."),
    (True, False): ("reduced the healthy phase-FPR spread relative to pooled calibration at the 1% "
                    "target, but abnormal-state alarm rate and/or detection delay fell outside the "
                    "pre-specified interpretive guardrails for {families}."),
    (False, True): ("did not consistently reduce the healthy phase-FPR spread at the 1% target; "
                    "abnormal-state alarm rate and detection delay stayed within the pre-specified "
                    "interpretive guardrails."),
    (False, False): ("did not consistently reduce the healthy phase-FPR spread at the 1% target, and "
                     "abnormal-state alarm rate and/or detection delay fell outside the pre-specified "
                     "interpretive guardrails for {families}."),
}


def ir_h(paired, scheme, alpha=PRIMARY_TARGET):
    pooled = paired[(paired.unit == "all") & (paired.scheme == scheme) & (paired.nominal_fpr == alpha)]
    family = {f: float(pooled[pooled.detector == f].delta_spread.mean()) for f in FAMILIES}
    return all(value > 0 for value in family.values()), family


def stage_f(output_root, datasets):
    out = guard_output(Path(output_root) / "stage_f")
    lines = ["# Post-confirmation mitigation report", "",
             "Post-confirmation, exploratory analysis. The frozen DS03 confirmation verdict and "
             "numbers are unchanged and are cited only through the frozen evidence ledger.", ""]
    summary = {}
    for key in datasets:
        base = Path(output_root) / key
        paired = pd.read_csv(base / "stage_d" / "healthy_paired_stability.csv")
        guardrails = pd.read_csv(base / "stage_e" / "guardrails.csv")
        n_engines = len(DATASETS[key].audit_units)
        lines += [f"## {key.upper()}", ""]
        for scheme in ALTERNATIVES:
            reduced, family = ir_h(paired, scheme)
            g = guardrails[guardrails.scheme == scheme]
            failing = g[~g.guardrails_met.astype(bool)].family.tolist()
            sentence = TEMPLATES[(reduced, not failing)].format(n=n_engines, families=", ".join(failing))
            label = ("Phase-conditioned calibration" if scheme == "phase_conditioned"
                     else "Causal-regime calibration (sensitivity/feasibility arm)")
            lines += [f"**{label}.** In this post-confirmation, exploratory analysis of simulated "
                      f"N-CMAPSS {key.upper()} data with retrospective (oracle) phase labels, "
                      f"{label[0].lower() + label[1:]} {sentence}", "",
                      "| Family | Mean ΔR (pp) | Alarm-rate ratio (all) | Alarm-rate ratio (early) | "
                      "Median delay change (flights) | Guardrails met |",
                      "|---|---:|---:|---:|---:|---|"]
            for f in FAMILIES:
                row = g[g.family == f].iloc[0]
                lines.append(f"| {f} | {100 * family[f]:+.3f} | {row.alarm_rate_ratio_all_post_onset:.3f} | "
                             f"{row.alarm_rate_ratio_early_first_10:.3f} | "
                             f"{row.family_median_delay_change_flights:+.0f} | {row.guardrails_met} |")
            lines.append("")
            summary[f"{key}:{scheme}"] = {"spread_reduced": reduced, "families_outside_guardrails": failing}
    lines += ["Guardrails are interpretive, not non-inferiority margins; full estimates and intervals "
              "are in the stage D and E tables.", ""]
    write_new(out / "MITIGATION_REPORT.md", "\n".join(lines))
    manifest = verify_manifest()
    write_json(out / "run_manifest.json", {"datasets": list(datasets), "summary": summary,
                                           "manifest": manifest, "environment": environment_record(),
                                           "provenance": provenance_record(), "finished_utc": now_utc()})
    if not manifest["ok"]:
        raise GateError("Baseline manifest failed after Stage F")
    return summary


STAGES = {"B": stage_b, "C": stage_c, "L": stage_l, "D": stage_d}


# ---------------------------------------------------------------------------
# Synthetic benchmark (no data access)
# ---------------------------------------------------------------------------

def synthetic_rows(units, flights_per_unit, rows_per_flight, rng, healthy_flights=None):
    records = []
    for unit in units:
        for cycle in range(1, flights_per_unit + 1):
            healthy = 1 if healthy_flights is None or cycle <= healthy_flights else 0
            phase = np.repeat([0, 1, 2], [rows_per_flight // 3, rows_per_flight // 3,
                                          rows_per_flight - 2 * (rows_per_flight // 3)])
            records.append(pd.DataFrame({"unit": np.int16(unit), "cycle": np.int16(cycle),
                                         "flight_class": np.int8(1), "healthy": np.int8(healthy),
                                         "phase_primary": phase.astype(np.int8)}))
    meta = pd.concat(records, ignore_index=True)
    regime = rng.integers(0, 3, len(meta)).astype(np.int8)
    return meta, regime


def benchmark_u2(replicates=20, rows_per_flight=9000, seed=0):
    """Time U1 and U2 on synthetic arrays of DS03-like shape and extrapolate to 2,000 x 7 runs."""
    rng = np.random.default_rng(seed)
    cal_meta, cal_regime = synthetic_rows((4, 8), 30, rows_per_flight, rng)
    audit_meta, audit_regime = synthetic_rows(range(10, 16), 70, rows_per_flight, rng, healthy_flights=25)
    name = ("pca", -1)
    cal_scores = {name: rng.lognormal(size=len(cal_meta))}
    audit_scores = {name: rng.lognormal(size=len(audit_meta)) + 0.5 * (audit_meta.healthy.to_numpy() == 0)}
    flights = audit_flight_table(audit_meta)
    engines = sorted(flights.unit.unique())
    healthy_meta = audit_meta[audit_meta.healthy == 1].reset_index(drop=True)
    healthy_scores = {name: audit_scores[name][audit_meta.healthy.to_numpy() == 1]}
    timings = {}
    clock = time.time()
    u1_bootstrap(cal_scores, cal_meta, cal_regime, healthy_scores, healthy_meta,
                 audit_regime[audit_meta.healthy.to_numpy() == 1], runs=[name], replicates=replicates)
    timings["u1_seconds_per_run_2000"] = (time.time() - clock) / replicates * REPLICATES
    clock = time.time()
    u2_bootstrap(cal_scores, cal_meta, cal_regime, audit_scores, audit_meta, audit_regime,
                 flights, engines, runs=[name], replicates=replicates)
    timings["u2_seconds_per_run_2000"] = (time.time() - clock) / replicates * REPLICATES
    timings["u1_minutes_7_runs"] = timings["u1_seconds_per_run_2000"] * len(RUNS) / 60
    timings["u2_minutes_7_runs"] = timings["u2_seconds_per_run_2000"] * len(RUNS) / 60
    timings["shape"] = {"calibration_rows": len(cal_meta), "audit_rows": len(audit_meta),
                        "audit_flights": len(flights), "replicates_timed": replicates}
    return timings
