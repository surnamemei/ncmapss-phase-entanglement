"""Extension stage 1: no-peek metadata audit of N-CMAPSS subsets.

Reads only what docs/extension/SUBSET_SELECTION_LOCK.md (Part 1) allows:
- the HDF5 object tree, shapes, dtypes and chunk layout;
- the ``*_var`` name arrays;
- the full ``A_dev`` and ``A_test`` label arrays (unit, cycle, Fc, hs);
- the altitude column ``W[:, 0]``, for ``hs = 1`` rows only.

It never reads X_s, X_v, T, Y, the other W columns, any hs = 0 altitude, scores or rates. Every
partial read is logged. The criteria C1-C9 and the cohort rules are applied mechanically.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from confirm_frozen_ds03 import primary_phase  # noqa: E402  (frozen phase rule, imported unchanged)
from second_stage_audit import SENSORS, W_NAMES  # noqa: E402

DATA_DIR = ROOT / "N-CMAPSS"
OUT_DIR = ROOT / "docs/extension"
EXTRACTION_RECORD = OUT_DIR / "archive_extraction_record.json"
PRE_EXTENSION_TAG = "mssp-pre-extension-2026-09-28"
A_NAMES = ["unit", "cycle", "Fc", "hs"]
CANDIDATES = {  # key -> (file, token searched in project history)
    "DS01": ("N-CMAPSS_DS01-005.h5", "DS01"),
    "DS04": ("N-CMAPSS_DS04.h5", "DS04"),
    "DS05": ("N-CMAPSS_DS05.h5", "DS05"),
    "DS06": ("N-CMAPSS_DS06.h5", "DS06"),
    "DS07": ("N-CMAPSS_DS07.h5", "DS07"),
    "DS08a": ("N-CMAPSS_DS08a-009.h5", "DS08"),
    "DS08c": ("N-CMAPSS_DS08c-008.h5", "DS08"),
    "DS08d": ("N-CMAPSS_DS08d-010.h5", "DS08"),
}
REFERENCES = {"DS02": "N-CMAPSS_DS02-006.h5", "DS03": "N-CMAPSS_DS03-012.h5"}
ORDER = ["DS01", "DS02", "DS03", "DS04", "DS05", "DS06", "DS07", "DS08a", "DS08c", "DS08d"]
PHASE_COMPLETE_SHARE = 0.99
MIN_TEST_PHASE_ROWS = 1000
MIN_ENGINES = 3
HISTORY_PATHS = ("src", "scripts", "configs", "results", "tests")


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def contiguous_runs(mask):
    index = np.flatnonzero(mask)
    if index.size == 0:
        return []
    cuts = np.flatnonzero(np.diff(index) > 1) + 1
    return [(int(g[0]), int(g[-1]) + 1) for g in np.split(index, cuts)]


def names(h5, key):
    return [v.decode() if isinstance(v, bytes) else str(v) for v in h5[key][:]]


def tree(h5):
    entries = {}
    def visit(name, obj):
        if isinstance(obj, h5py.Dataset):
            entries[name] = {"shape": list(obj.shape), "dtype": str(obj.dtype),
                             "chunks": list(obj.chunks) if obj.chunks else None,
                             "compression": obj.compression}
    h5.visititems(visit)
    return entries


def history_mentions(token):
    """Commits reachable from the pre-extension tag that mention the subset in project code/results."""
    try:
        revs = subprocess.run(["git", "rev-list", PRE_EXTENSION_TAG], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.split()
    except subprocess.CalledProcessError as error:  # pragma: no cover - tag must exist
        raise RuntimeError("Pre-extension tag missing") from error
    hits = set()
    for start in range(0, len(revs), 50):
        result = subprocess.run(["git", "grep", "-l", "-i", token, *revs[start:start + 50], "--",
                                 *HISTORY_PATHS], cwd=ROOT, capture_output=True, text=True)
        hits.update(line.split(":", 1)[1] for line in result.stdout.split() if ":" in line)
    return sorted(hits)


def flight_table(a):
    """One row per flight in split order, with LS-2 and contiguity evidence."""
    unit, cycle, fc, hs = (a[:, i] for i in range(4))
    change = np.r_[True, (np.diff(unit) != 0) | (np.diff(cycle) != 0)]
    starts = np.flatnonzero(change)
    ends = np.r_[starts[1:], len(a)]
    frame = pd.DataFrame({"unit": unit[starts].astype(int), "cycle": cycle[starts].astype(int),
                          "fc": fc[starts].astype(int), "start": starts, "end": ends,
                          "rows": ends - starts})
    frame["hs_min"] = np.minimum.reduceat(hs, starts).astype(int)
    frame["hs_max"] = np.maximum.reduceat(hs, starts).astype(int)
    frame["fc_constant"] = (np.minimum.reduceat(fc, starts) == np.maximum.reduceat(fc, starts))
    return frame


def engine_checks(flights, split):
    rows = []
    for unit, part in flights.groupby("unit", sort=False):
        part = part.reset_index(drop=True)
        cycles = part.cycle.to_numpy()
        state = part.hs_min.to_numpy()
        ls2 = bool((part.hs_min == part.hs_max).all())
        diffs = np.diff(state)
        ls1 = bool(ls2 and state[0] == 1 and (diffs <= 0).all() and int((diffs != 0).sum()) <= 1)
        healthy = part[part.hs_min == 1]
        post = part[part.hs_max == 0]
        rows.append({
            "split": split, "unit": int(unit), "flight_class": int(part.fc.iloc[0]),
            "fc_constant": bool(part.fc_constant.all() and part.fc.nunique() == 1),
            "rows": int(part.rows.sum()), "flights": int(len(part)),
            "first_cycle": int(cycles[0]), "last_cycle": int(cycles[-1]),
            "cycles_contiguous": bool(len(cycles) == len(set(cycles.tolist()))
                                      and np.array_equal(cycles, np.arange(cycles[0], cycles[0] + len(cycles)))),
            "ls1": ls1, "ls2": ls2,
            "healthy_flights": int(len(healthy)), "post_onset_flights": int(len(post)),
            "healthy_rows": int(healthy.rows.sum()), "post_onset_rows": int(post.rows.sum()),
            "onset_cycle": int(post.cycle.iloc[0]) if len(post) else -1,
            "median_flight_rows": float(part.rows.median()),
        })
    return rows


def phase_feasibility(h5, split, a, flights):
    """Primary-phase segment sizes of healthy flights; reads W[:, 0] for hs = 1 rows only."""
    healthy_rows = a[:, 3] == 1
    runs = contiguous_runs(healthy_rows)
    alt = (np.concatenate([h5[f"W_{split}"][s:e, 0] for s, e in runs]).astype(np.float64)
           if runs else np.empty(0))
    meta = a[healthy_rows]
    labels = primary_phase(alt, meta[:, 0].astype(np.int16), meta[:, 1].astype(np.int16))
    healthy = flights[flights.hs_min == 1].reset_index(drop=True)
    offsets = np.r_[0, np.cumsum(healthy.rows.to_numpy())]
    records = []
    for i, row in healthy.iterrows():
        seg = labels[offsets[i]:offsets[i + 1]]
        seg_alt = alt[offsets[i]:offsets[i + 1]]
        counts = np.bincount(seg, minlength=3)
        span = float(seg_alt.max() - seg_alt.min()) if len(seg_alt) else 0.0
        records.append({"unit": int(row.unit), "cycle": int(row.cycle), "rows": int(row.rows),
                        "climb_rows": int(counts[0]), "cruise_rows": int(counts[1]),
                        "descent_rows": int(counts[2]), "altitude_span": span,
                        "phase_complete": bool(span > 0 and counts.min() > 0)})
    read = {"array": f"W_{split}", "column": 0, "rows_read": int(healthy_rows.sum()),
            "row_blocks": len(runs), "selection": "hs == 1 rows only"}
    return pd.DataFrame(records), read


def unopenable_record(key, filename, error):
    """C1 failure before any array is read: the file does not open as HDF5."""
    checks = {c: False for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8")}
    record = {"dataset": key, "file": filename, "reads": [], "tree": {}, "variables": {},
              "row_counts_dev": {}, "row_counts_test": {}, "dev_units": [], "test_units": [],
              "checks": checks, "open_error": str(error),
              "reasons": [f"C1: the file does not open as HDF5 ({error}); nothing was read"]}
    return record, pd.DataFrame(columns=["split", "unit", "flight_class", "healthy_rows",
                                         "healthy_flights", "post_onset_rows", "post_onset_flights"]), pd.DataFrame()


def audit_file(key, filename):
    path = DATA_DIR / filename
    record = {"dataset": key, "file": filename, "reads": []}
    checks, reasons = {}, []
    try:
        handle = h5py.File(path, "r")
    except OSError as error:
        return unopenable_record(key, filename, error)
    with handle as h5:
        record["tree"] = tree(h5)
        required = ["A_dev", "A_test", "W_dev", "W_test", "X_s_dev", "X_s_test", "A_var", "W_var", "X_s_var"]
        missing = [k for k in required if k not in h5]
        var_names = {k: names(h5, k) for k in h5.keys() if k.endswith("_var")}
        record["reads"].append({"arrays": sorted(var_names), "content": "variable-name arrays"})
        record["variables"] = var_names
        row_ok, width_ok = True, True
        for split in ("dev", "test"):
            counts = {p: h5[f"{p}_{split}"].shape[0] for p in ("A", "W", "X_s", "X_v", "T", "Y")
                      if f"{p}_{split}" in h5}
            record[f"row_counts_{split}"] = counts
            row_ok &= len(set(counts.values())) == 1
            for p in ("A", "W", "X_s", "X_v", "T"):
                if f"{p}_{split}" in h5 and f"{p}_var" in h5:
                    width_ok &= h5[f"{p}_{split}"].shape[1] == len(var_names[f"{p}_var"])
        a = {split: h5[f"A_{split}"][:] for split in ("dev", "test")}
        record["reads"].append({"arrays": ["A_dev", "A_test"], "content": "complete label arrays"})
        a_ok = all(np.isfinite(v).all() and np.array_equal(v, np.round(v)) for v in a.values())
        a_ok = a_ok and all(((v[:, 0] >= 1) & (v[:, 1] >= 1) & np.isin(v[:, 2], (1, 2, 3))
                             & np.isin(v[:, 3], (0, 1))).all() for v in a.values())
        checks["C1"] = bool(not missing and row_ok and width_ok and a_ok)
        if not checks["C1"]:
            reasons.append(f"C1: missing={missing} rows_consistent={row_ok} widths={width_ok} A_valid={a_ok}")
        checks["C2"] = var_names.get("X_s_var") == list(SENSORS)
        checks["C3"] = var_names.get("W_var") == list(W_NAMES)
        a_schema = var_names.get("A_var") == A_NAMES
        for cid in ("C2", "C3"):
            if not checks[cid]:
                reasons.append(f"{cid}: schema mismatch")
        engines, phases = [], []
        unit_blocks_ok, flights_ok = True, True
        split_units = {}
        for split in ("dev", "test"):
            ai = a[split].astype(np.int64)
            flights = flight_table(ai)
            unit_runs = (np.diff(ai[:, 0]) != 0).sum() + 1
            unit_blocks_ok &= unit_runs == len(np.unique(ai[:, 0]))
            flights_ok &= len(flights) == len(flights[["unit", "cycle"]].drop_duplicates())
            split_units[split] = sorted(int(u) for u in np.unique(ai[:, 0]))
            engines += engine_checks(flights, split)
            if checks["C1"] and checks["C3"]:
                table, read = phase_feasibility(h5, split, ai, flights)
                record["reads"].append(read)
                phases.append(table.assign(split=split))
    eng = pd.DataFrame(engines)
    ph = pd.concat(phases, ignore_index=True) if phases else pd.DataFrame()
    overlap = sorted(set(split_units["dev"]) & set(split_units["test"]))
    checks["C5"] = bool(unit_blocks_ok and flights_ok and not overlap and eng.cycles_contiguous.all()
                        and eng.fc_constant.all())
    if not checks["C5"]:
        reasons.append(f"C5: unit_blocks={unit_blocks_ok} flight_blocks={flights_ok} overlap={overlap} "
                       f"cycles={bool(eng.cycles_contiguous.all())} fc={bool(eng.fc_constant.all())}")
    dev, test = eng[eng.split == "dev"], eng[eng.split == "test"]
    test_healthy = test[test.healthy_flights >= 1]
    test_delay = test[(test.healthy_flights >= 1) & (test.post_onset_flights >= 1)]
    checks["C4"] = bool(a_schema and eng.ls1.all() and eng.ls2.all() and (dev.healthy_flights >= 1).all()
                        and len(test_delay) >= MIN_ENGINES)
    if not checks["C4"]:
        reasons.append(f"C4: A_var={a_schema} ls1_all={bool(eng.ls1.all())} ls2_all={bool(eng.ls2.all())} "
                       f"dev_healthy={bool((dev.healthy_flights >= 1).all())} "
                       f"test_engines_with_healthy_and_post_onset={len(test_delay)}")
    checks["C6"] = len(dev) >= MIN_ENGINES
    checks["C7"] = len(test_healthy) >= MIN_ENGINES
    for cid, n in (("C6", len(dev)), ("C7", len(test_healthy))):
        if not checks[cid]:
            reasons.append(f"{cid}: {n} engines")
    if len(ph):
        complete_share = float(ph.phase_complete.mean())
        per_engine = ph.groupby(["split", "unit"]).phase_complete.any()
        test_rows = ph[ph.split == "test"].groupby("unit")[["climb_rows", "cruise_rows", "descent_rows"]].sum()
        min_test_phase_rows = int(test_rows.min().min()) if len(test_rows) else 0
        checks["C8"] = bool(complete_share >= PHASE_COMPLETE_SHARE and per_engine.all()
                            and min_test_phase_rows >= MIN_TEST_PHASE_ROWS)
        record["phase_complete_share"] = complete_share
        record["min_test_engine_phase_rows"] = min_test_phase_rows
        if not checks["C8"]:
            reasons.append(f"C8: complete_share={complete_share:.4f} every_engine={bool(per_engine.all())} "
                           f"min_test_phase_rows={min_test_phase_rows}")
        rows_by_engine = ph.groupby(["split", "unit"])[["climb_rows", "cruise_rows", "descent_rows"]].sum()
        complete_by_engine = ph.groupby(["split", "unit"]).phase_complete.sum()
        eng = eng.merge(rows_by_engine.add_prefix("healthy_").reset_index(), on=["split", "unit"], how="left")
        eng = eng.merge(complete_by_engine.rename("phase_complete_healthy_flights").reset_index(),
                        on=["split", "unit"], how="left")
    else:
        checks["C8"] = False
        reasons.append("C8: phase feasibility not evaluable (C1 or C3 failed)")
    record["checks"] = checks
    record["reasons"] = reasons
    record["dev_units"], record["test_units"] = split_units["dev"], split_units["test"]
    return record, eng.assign(dataset=key), ph.assign(dataset=key) if len(ph) else ph


def cohort(checks):
    if all(checks[c] for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9")):
        return "PRIMARY GENERALIZATION COHORT"
    stress_ok = all(checks[c] for c in ("C1", "C2", "C3", "C5", "C6", "C8", "C9"))
    if stress_ok and checks.get("stress_test_engines", 0) >= 2:
        return "STRESS-TEST COHORT"
    return "EXCLUDED"


def main():
    started = now_utc()
    extraction = json.loads(EXTRACTION_RECORD.read_text(encoding="utf-8"))
    records, engines, phases = [], [], []
    for key in ORDER:
        is_candidate = key in CANDIDATES
        filename = CANDIDATES[key][0] if is_candidate else REFERENCES[key]
        record, eng, ph = audit_file(key, filename)
        file_info = extraction["hdf5_files"][filename]
        record["sha256"], record["md5"], record["bytes"] = file_info["sha256"], file_info["md5"], file_info["bytes"]
        if is_candidate:
            mentions = history_mentions(CANDIDATES[key][1])
            record["history_mentions"] = mentions
            record["checks"]["C9"] = bool(file_info["action"].startswith("extracted") and not mentions)
            if not record["checks"]["C9"]:
                record["reasons"].append(f"C9: history mentions {mentions}")
            test = eng[eng.split == "test"]
            record["checks"]["stress_test_engines"] = int((test.healthy_flights >= 1).sum())
            record["cohort"] = cohort(record["checks"])
        else:
            record["checks"]["C9"] = False
            record["cohort"] = "REFERENCE (already opened by the frozen study; not a candidate)"
        records.append(record)
        engines.append(eng.assign(dataset=key) if len(eng) else eng)
        phases.append(ph)
        print(f"{key}: {record['cohort']} {record['checks']} {record['reasons']}", flush=True)
    engine_table = pd.concat(engines, ignore_index=True)
    rows = []
    for r in records:
        e = engine_table[engine_table.dataset == r["dataset"]] if len(engine_table) else engine_table
        dev, test = e[e.split == "dev"], e[e.split == "test"]
        rows.append({
            "dataset": r["dataset"], "file": r["file"], "bytes": r["bytes"], "sha256": r["sha256"],
            "md5": r["md5"], "role": r["cohort"],
            "dev_units": " ".join(map(str, r["dev_units"])), "test_units": " ".join(map(str, r["test_units"])),
            "n_dev": len(dev), "n_test": len(test),
            "dev_classes": " ".join(f"{u}:{c}" for u, c in zip(dev.unit, dev.flight_class)),
            "test_classes": " ".join(f"{u}:{c}" for u, c in zip(test.unit, test.flight_class)),
            "rows_dev": r["row_counts_dev"].get("A"), "rows_test": r["row_counts_test"].get("A"),
            "healthy_rows_dev": int(dev.healthy_rows.sum()), "healthy_rows_test": int(test.healthy_rows.sum()),
            "post_onset_rows_test": int(test.post_onset_rows.sum()),
            "healthy_flights_dev": int(dev.healthy_flights.sum()), "healthy_flights_test": int(test.healthy_flights.sum()),
            "post_onset_flights_test": int(test.post_onset_flights.sum()),
            "phase_complete_share": r.get("phase_complete_share"),
            "min_test_engine_phase_rows": r.get("min_test_engine_phase_rows"),
            **{c: r["checks"].get(c) for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9")},
            "reasons": "; ".join(r["reasons"]),
            "x_s_var": " ".join(r["variables"].get("X_s_var", [])),
            "w_var": " ".join(r["variables"].get("W_var", [])),
            "other_arrays": " ".join(sorted(k for k in r["tree"] if not k.startswith(("A_", "W_", "X_s_")))),
        })
    audit = pd.DataFrame(rows)
    audit.to_csv(OUT_DIR / "subset_metadata_audit.csv", index=False)
    engine_table.to_csv(OUT_DIR / "subset_engine_metadata.csv", index=False)
    pd.concat([p for p in phases if len(p)], ignore_index=True).to_csv(
        ROOT / "results/extension/metadata/healthy_flight_phase_segments.csv", index=False)
    with (OUT_DIR / "subset_metadata_audit.json").open("x", encoding="utf-8") as stream:
        json.dump({"started_utc": started, "finished_utc": now_utc(),
                   "criteria": "docs/extension/SUBSET_SELECTION_LOCK.md Part 1",
                   "not_read": ["X_s", "X_v", "T", "Y", "W columns 1-3", "W column 0 for hs = 0 rows"],
                   "records": records}, stream, indent=1, default=str)
    print(audit[["dataset", "role", "n_dev", "n_test", "dev_classes", "test_classes"]].to_string(), flush=True)


if __name__ == "__main__":
    sys.exit(main())
