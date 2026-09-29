"""Synthetic N-CMAPSS-shaped HDF5 files and registries for data-free extension tests (no real data is read)."""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

SENSORS = ["T24", "T30", "T48", "T50", "P15", "P2", "P21", "P24", "Ps30", "P40", "P50", "Nf", "Nc", "Wf"]
W_NAMES = ["alt", "Mach", "TRA", "T2"]
ROWS_BY_CLASS = {1: 300, 2: 380, 3: 460}


def flight_w(n, rng, flight_class):
    t = np.linspace(0.0, 1.0, n)
    top = {1: 18000.0, 2: 28000.0, 3: 35000.0}[flight_class]
    alt = top * np.clip(np.minimum(t / 0.25, (1.0 - t) / 0.3), 0.0, 1.0) + rng.normal(0.0, 30.0, n)
    alt = np.maximum(alt, 0.0)
    mach = 0.25 + 0.5 * alt / 35000.0 + rng.normal(0.0, 0.005, n)
    tra = 55.0 + 25.0 * np.sin(5.0 * t + rng.uniform(0.0, 3.0)) + rng.normal(0.0, 0.3, n)
    t2 = 518.0 - 3.5 * alt / 1000.0 + rng.normal(0.0, 0.2, n)
    return np.column_stack([alt, mach, tra, t2])


def sensors(w, degradation, rng, mixing):
    z = (w - np.array([15000.0, 0.45, 55.0, 470.0])) / np.array([12000.0, 0.2, 20.0, 40.0])
    base = np.tanh(z @ mixing[0]) + 0.3 * (z ** 2) @ mixing[1]
    noise = (0.02 + 0.05 * (z[:, :1] > 0.5)) * rng.normal(size=base.shape)
    return 500.0 + 50.0 * (base + noise + degradation * mixing[2])


def write_subset(path, dev_units, test_units, flights=6, healthy=3, seed=0):
    """dev_units / test_units: {unit: flight class}. Every engine: `healthy` hs = 1 flights, then hs = 0 flights."""
    rng = np.random.default_rng(seed)
    mixing = (rng.normal(size=(4, 14)), rng.normal(size=(4, 14)) * 0.3, rng.normal(size=14))
    with h5py.File(path, "w") as h5:
        for split, units in (("dev", dev_units), ("test", test_units)):
            a_rows, w_rows, x_rows = [], [], []
            for unit, flight_class in sorted(units.items()):
                for cycle in range(1, flights + 1):
                    n = ROWS_BY_CLASS[flight_class] + int(rng.integers(0, 20))
                    w = flight_w(n, rng, flight_class)
                    hs = 1 if cycle <= healthy else 0
                    degradation = 0.0 if hs else 0.4 * (cycle - healthy)
                    x_rows.append(sensors(w, degradation, rng, mixing))
                    w_rows.append(w)
                    a_rows.append(np.column_stack([np.full(n, unit), np.full(n, cycle), np.full(n, flight_class),
                                                   np.full(n, hs)]).astype(np.float64))
            a, w, x = np.vstack(a_rows), np.vstack(w_rows), np.vstack(x_rows)
            h5.create_dataset(f"A_{split}", data=a, chunks=True)
            h5.create_dataset(f"W_{split}", data=w, chunks=True)
            h5.create_dataset(f"X_s_{split}", data=x, chunks=True)
            h5.create_dataset(f"X_v_{split}", data=np.zeros((len(a), 2)))
            h5.create_dataset(f"T_{split}", data=np.zeros((len(a), 2)))
            h5.create_dataset(f"Y_{split}", data=np.zeros((len(a), 1)))
        h5.create_dataset("A_var", data=np.array([b"unit", b"cycle", b"Fc", b"hs"]))
        h5.create_dataset("W_var", data=np.array([n.encode() for n in W_NAMES]))
        h5.create_dataset("X_s_var", data=np.array([n.encode() for n in SENSORS]))
        h5.create_dataset("X_v_var", data=np.array([b"v1", b"v2"]))
        h5.create_dataset("T_var", data=np.array([b"t1", b"t2"]))


def engine_metadata(path, key, h5_path):
    rows = []
    with h5py.File(h5_path, "r") as h5:
        for split in ("dev", "test"):
            a = h5[f"A_{split}"][:]
            for unit in np.unique(a[:, 0]):
                part = a[a[:, 0] == unit]
                healthy = part[part[:, 3] == 1]
                rows.append({"split": split, "unit": int(unit), "flight_class": int(part[0, 2]),
                             "healthy_rows": int(len(healthy)), "healthy_flights": int(len(np.unique(healthy[:, 1]))),
                             "dataset": key})
    pd.DataFrame(rows).to_csv(path, index=False)


def install(monkey, tmp, key="DS99", dev_units=None, test_units=None, **kwargs):
    """Point ext_common at a synthetic subset. `monkey` is a callable (obj, name, value) that records originals."""
    import ext_common as ec
    dev_units = dev_units or {1: 1, 2: 3, 3: 2, 4: 1, 5: 3, 6: 2}
    test_units = test_units or {7: 1, 8: 2, 9: 1, 10: 3}
    tmp = Path(tmp)
    h5_path = tmp / f"{key}.h5"
    write_subset(h5_path, dev_units, test_units, **kwargs)
    meta_path = tmp / "engine_metadata.csv"
    engine_metadata(meta_path, key, h5_path)
    record = tmp / "extraction.json"
    record.write_text(json.dumps({"hdf5_files": {h5_path.name: {"sha256": ec.file_digest(h5_path)}}}))
    monkey(ec, "DATA_DIR", tmp)
    monkey(ec, "RESULTS", tmp / "results")
    monkey(ec, "ENGINE_METADATA", meta_path)
    monkey(ec, "EXTRACTION_RECORD", record)
    monkey(ec, "NEW_ORDER", (key,))
    monkey(ec, "REFERENCE_ORDER", ())
    monkey(ec, "FILES", {**ec.FILES, key: h5_path.name})
    monkey(ec, "FAMILIES", {**ec.FAMILIES, key: "F9"})
    return h5_path


COHORT = {  # synthetic analogues of the real cohort structure: key -> (family, dev classes, test classes, seed)
    "DS91": ("F1", {1: 1, 2: 3, 3: 2, 4: 1, 5: 3, 6: 2}, {7: 1, 8: 2, 9: 1, 10: 3}, 1),
    "DS92": ("F2", {1: 2, 2: 3, 3: 2, 4: 3, 5: 3, 6: 3}, {7: 2, 8: 2, 9: 2, 10: 3}, 2),
    "DS93": ("F3", {1: 2, 2: 3, 3: 2, 4: 1, 5: 1, 6: 3}, {7: 2, 8: 1, 9: 3, 10: 1}, 3),
    "DS96": ("F3", {1: 2, 2: 3, 3: 2, 4: 1, 5: 1, 6: 3}, {7: 2, 8: 1, 9: 3, 10: 1}, 6),
    "DS94": ("F4", {1: 1, 2: 3, 3: 1, 4: 2, 5: 2, 6: 3, 7: 2, 8: 2, 9: 1}, {10: 1, 11: 2, 12: 3, 13: 3, 14: 3, 15: 1}, 4),
    "DS95": ("F5", {1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2}, {7: 2, 8: 2, 9: 2, 10: 2}, 5),
}


def install_cohort(monkey, tmp, **subset_kwargs):
    """subset_kwargs (e.g. flights, healthy) pass through to write_subset; defaults are unchanged."""
    import ext_common as ec
    tmp = Path(tmp)
    frames, record, files, families = [], {}, dict(ec.FILES), dict(ec.FAMILIES)
    for key, (family, dev, test, seed) in COHORT.items():
        h5_path = tmp / f"{key}.h5"
        write_subset(h5_path, dev, test, seed=seed, **subset_kwargs)
        engine_metadata(tmp / f"{key}.csv", key, h5_path)
        frames.append(pd.read_csv(tmp / f"{key}.csv"))
        record[h5_path.name] = {"sha256": ec.file_digest(h5_path)}
        files[key], families[key] = h5_path.name, family
    pd.concat(frames).to_csv(tmp / "engine_metadata.csv", index=False)
    (tmp / "extraction.json").write_text(json.dumps({"hdf5_files": record}))
    monkey(ec, "DATA_DIR", tmp)
    monkey(ec, "RESULTS", tmp / "results")
    monkey(ec, "ENGINE_METADATA", tmp / "engine_metadata.csv")
    monkey(ec, "EXTRACTION_RECORD", tmp / "extraction.json")
    monkey(ec, "NEW_ORDER", tuple(COHORT))
    monkey(ec, "REFERENCE_ORDER", ())
    monkey(ec, "FILES", files)
    monkey(ec, "FAMILIES", families)
