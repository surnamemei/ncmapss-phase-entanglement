"""Shared registry, engine allocation, guarded I/O and access logging for the extension.

Protocol: docs/extension/GENERALIZATION_PROTOCOL.md (FROZEN v1.0). Nothing here reads sensor values.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DATA_DIR = ROOT / "N-CMAPSS"
RESULTS = Path(os.environ.get("NCMAPSS_EXTENSION_RESULTS", ROOT / "results/extension"))
DOCS = ROOT / "docs/extension"
PROTOCOL = DOCS / "GENERALIZATION_PROTOCOL.md"
CVAE_SPEC = DOCS / "CVAE_SPECIFICATION.md"
ACCESS_LOG = DOCS / "OUTCOME_ACCESS_LOG.md"
EXTRACTION_RECORD = DOCS / "archive_extraction_record.json"
ENGINE_METADATA = DOCS / "subset_engine_metadata.csv"
BASELINE_MANIFEST = ROOT / "docs/mssp/frozen_baseline.sha256"

NEW_ORDER = ("DS01", "DS04", "DS05", "DS06", "DS07", "DS08a", "DS08c")
REFERENCE_ORDER = ("DS02", "DS03")
FAMILIES = {"DS01": "F1", "DS04": "F2", "DS05": "F3", "DS06": "F3", "DS07": "F3", "DS08a": "F4",
            "DS08c": "F5", "DS02": "F0a", "DS03": "F0b"}
FILES = {"DS01": "N-CMAPSS_DS01-005.h5", "DS02": "N-CMAPSS_DS02-006.h5", "DS03": "N-CMAPSS_DS03-012.h5",
         "DS04": "N-CMAPSS_DS04.h5", "DS05": "N-CMAPSS_DS05.h5", "DS06": "N-CMAPSS_DS06.h5",
         "DS07": "N-CMAPSS_DS07.h5", "DS08a": "N-CMAPSS_DS08a-009.h5", "DS08c": "N-CMAPSS_DS08c-008.h5"}
FROZEN_ROLES = {  # DS02/DS03: the frozen study's roles (configs/*.yaml), unchanged
    "DS02": {"fit": (2, 5, 10, 16), "selection_fit": (2, 5, 10), "validation": 16, "calibration": (18, 20),
             "audit": (11, 14, 15)},
    "DS03": {"fit": (1, 2, 3, 5, 6, 7, 9), "selection_fit": (1, 2, 3, 5, 6, 7), "validation": 9,
             "calibration": (4, 8), "audit": (10, 11, 12, 13, 14, 15)},
}
TARGETS = (0.005, 0.01, 0.02)
PRIMARY_TARGET = 0.01
SEEDS = (0, 1, 2)
RUNS = (("pca", -1),) + tuple(("isolation_forest", s) for s in SEEDS) + tuple(
    ("lstm_autoencoder", s) for s in SEEDS) + tuple(("cvae", s) for s in SEEDS)
RESIDUAL_RUNS = RUNS[:7]
CVAE_RUNS = RUNS[7:]
ARMS = ("pooled", "phase_conditioned", "quantile_regression_W")
ARM_LABEL = {"pooled": "P", "phase_conditioned": "C", "quantile_regression_W": "Q"}
RULES = ("R0", "R1", "R2")
COMPOSITION_BASE_SEED = 20260930
COMPOSITION_DRAWS = (0, 1, 2, 3, 4)
UEXT1_SEED = 20260929
COMPOSITION_BOOT_SEED = 20261001
UEXT2_SEED = 20261002
BOOTSTRAP_REPLICATES = 2000
VOLUME_QUANTUM = 6000


class ExtensionError(RuntimeError):
    """A pre-specified stop rule (protocol section 18) fired; execution halts."""


def run_name(detector, seed):
    return f"{detector}:{seed}"


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_digest(path, algorithm="sha256", block=8 << 20):
    digest = hashlib.new(algorithm)
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(block), b""):
            digest.update(chunk)
    return digest.hexdigest()


def array_fingerprint(values):
    return hashlib.sha256(np.ascontiguousarray(values, dtype=np.float64).tobytes()).hexdigest()


def git_sha():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def git_tracked_and_clean(path):
    """True if the file is committed and unmodified in the working tree."""
    try:
        rel = str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return False
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=ROOT, capture_output=True).returncode == 0
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=ROOT).returncode == 0
    return tracked and clean


PROTECTED = tuple((ROOT / p).resolve() for p in (
    "results/final_validation", "results/confirmation_ds03", "results/mssp_mitigation",
    "results/mssp_adversarial", "paper/ress", "paper/submission", "src/final_validation.py",
    "src/confirm_frozen_ds03.py", "src/mssp_mitigation.py", "src/mssp_adversarial.py", "configs"))


def guard_path(path):
    resolved = Path(path).resolve()
    for protected in PROTECTED:
        if resolved == protected or protected in resolved.parents:
            raise ExtensionError(f"Refusing to write inside a frozen path: {resolved}")
    return resolved


def write_new_bytes(path, data):
    path = guard_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:  # exclusive create: never overwrite
        stream.write(data)
    return hashlib.sha256(data).hexdigest()


def write_json(path, payload):
    return write_new_bytes(path, (json.dumps(payload, indent=1, sort_keys=True, default=_json_default) + "\n").encode())


def write_csv(path, frame):
    return write_new_bytes(path, frame.to_csv(index=False, lineterminator="\n").encode())


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (set, tuple)):
        return list(value)
    raise TypeError(f"Not JSON serializable: {type(value)}")


def canonical_json(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_json_default)


def append_access_log(subset, event, detail, lock_sha="—", command="—"):
    line = f"| {now_utc()} | {subset} | {event} | {detail} | `{git_sha()[:7]}` | {lock_sha} | `{command}` |\n"
    with ACCESS_LOG.open("a", encoding="utf-8") as stream:
        stream.write(line)


def verify_baseline():
    result = subprocess.run(["sha256sum", "-c", "--quiet", str(BASELINE_MANIFEST.relative_to(ROOT))], cwd=ROOT,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise ExtensionError(f"Frozen baseline manifest failed:\n{result.stdout}{result.stderr}")
    return True


# ---------------------------------------------------------------------------
# Engine allocation (R-ALLOC, protocol section 3): metadata only
# ---------------------------------------------------------------------------

def allocate(dev_engines):
    """dev_engines: iterable of (unit, flight_class). Returns the protocol R-ALLOC roles."""
    engines = sorted((int(u), int(k)) for u, k in dev_engines)
    classes = sorted({k for _, k in engines})
    members = {k: [u for u, c in engines if c == k] for k in classes}
    fit = [min(members[k]) for k in classes]
    calibration = [max(members[k]) for k in classes if len(members[k]) >= 2]
    for unit, _ in engines:
        if unit in fit or unit in calibration:
            continue
        (fit if len(fit) < 3 else calibration).append(unit)
    fit, calibration = sorted(fit), sorted(calibration)
    if len(fit) < 3:
        raise ExtensionError("R-ALLOC: fewer than 3 fit engines")
    validation = max(fit)
    return {"fit": tuple(fit), "selection_fit": tuple(u for u in fit if u != validation), "validation": validation,
            "calibration": tuple(calibration)}


@dataclass(frozen=True)
class Subset:
    key: str
    filename: str
    family: str
    fit: tuple
    selection_fit: tuple
    validation: int
    calibration: tuple
    audit: tuple
    classes: dict = field(default_factory=dict)
    reference: bool = False

    @property
    def path(self):
        return DATA_DIR / self.filename

    @property
    def mm_key(self):
        return self.key.lower()

    @property
    def out(self):
        return RESULTS / self.key

    def assert_disjoint(self):
        fit, cal, audit = set(self.fit), set(self.calibration), set(self.audit)
        if fit & cal or fit & audit or cal & audit:
            raise ExtensionError(f"{self.key}: engine roles overlap")
        if self.validation not in fit or set(self.selection_fit) != fit - {self.validation}:
            raise ExtensionError(f"{self.key}: selection roles inconsistent")
        return True

    def roles_record(self):
        return {"fit": list(self.fit), "selection_fit": list(self.selection_fit), "validation": self.validation,
                "calibration": list(self.calibration), "audit": list(self.audit),
                "classes": {str(k): v for k, v in sorted(self.classes.items())}, "family": self.family,
                "reference": self.reference}


def load_registry():
    meta = pd.read_csv(ENGINE_METADATA)
    registry = {}
    for key in NEW_ORDER + REFERENCE_ORDER:
        part = meta[meta.dataset == key]
        dev = part[part.split == "dev"]
        test = part[part.split == "test"]
        classes = {int(u): int(c) for u, c in zip(part.unit, part.flight_class)}
        if key in FROZEN_ROLES:
            roles = FROZEN_ROLES[key]
            audit = roles["audit"]
        else:
            roles = allocate(zip(dev.unit, dev.flight_class))
            audit = tuple(sorted(int(u) for u in test.unit))
        subset = Subset(key, FILES[key], FAMILIES[key], tuple(roles["fit"]), tuple(roles["selection_fit"]),
                        int(roles["validation"]), tuple(roles["calibration"]), tuple(audit), classes,
                        reference=key in REFERENCE_ORDER)
        subset.assert_disjoint()
        registry[key] = subset
    return registry


def expected_sha256(filename):
    record = json.loads(EXTRACTION_RECORD.read_text(encoding="utf-8"))
    return record["hdf5_files"][filename]["sha256"]


def verify_input(subset):
    digest = file_digest(subset.path)
    if digest != expected_sha256(subset.filename):
        raise ExtensionError(f"{subset.key}: HDF5 SHA-256 differs from the extraction record")
    return digest


def composition_volume(subset):
    rows = pd.read_csv(ENGINE_METADATA)
    part = rows[(rows.dataset == subset.key) & rows.unit.isin(subset.calibration) & (rows.split == "dev")]
    smallest = int(part.healthy_rows.min())
    volume = (smallest // 2 // VOLUME_QUANTUM) * VOLUME_QUANTUM
    if volume < VOLUME_QUANTUM:
        raise ExtensionError(f"{subset.key}: fair row-count matching impossible (N < {VOLUME_QUANTUM})")
    return volume


def composition_eligible(subset):
    return len({subset.classes[u] for u in subset.calibration}) >= 2
