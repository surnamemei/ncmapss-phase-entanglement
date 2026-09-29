"""Extension stage 1: flight-profile sharing between engines and subsets (metadata only).

Uses only results/extension/metadata/healthy_flight_phase_segments.csv, which the metadata audit
derived from hs = 1 altitude traces. A flight signature is (rows, climb rows, cruise rows, descent
rows, altitude span rounded to 1e-3). Two engines share a *profile sequence* when their healthy
flights, aligned by cycle, have identical signatures for every overlapping cycle.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEGMENTS = ROOT / "results/extension/metadata/healthy_flight_phase_segments.csv"
OUT_PAIRS = ROOT / "docs/extension/profile_sharing_engine_pairs.csv"
OUT_DATASETS = ROOT / "docs/extension/profile_sharing_by_dataset.csv"
HISTORICAL = ("DS02", "DS03")


def signatures(frame):
    frame = frame.copy()
    frame["signature"] = list(zip(frame.rows, frame.climb_rows, frame.cruise_rows, frame.descent_rows,
                                  frame.altitude_span.round(3)))
    return frame


def engine_pairs(frame):
    seq = frame.sort_values(["dataset", "split", "unit", "cycle"]).groupby(["dataset", "split", "unit"]).signature.apply(list)
    keys = list(seq.index)
    rows = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            sa, sb = seq[a], seq[b]
            overlap = min(len(sa), len(sb))
            aligned = sum(x == y for x, y in zip(sa[:overlap], sb[:overlap]))
            shared = len(set(sa) & set(sb))
            if shared == 0:
                continue
            rows.append({"dataset_a": a[0], "split_a": a[1], "unit_a": a[2], "dataset_b": b[0], "split_b": b[1],
                         "unit_b": b[2], "healthy_flights_a": len(sa), "healthy_flights_b": len(sb),
                         "aligned_identical_flights": aligned, "aligned_overlap": overlap,
                         "shared_flight_signatures": shared,
                         "identical_profile_sequence": aligned == overlap and overlap >= 5,
                         "same_dataset": a[0] == b[0]})
    return pd.DataFrame(rows)


def dataset_summary(frame):
    owners = frame.groupby("signature").apply(lambda g: set(zip(g.dataset, g.split, g.unit)), include_groups=False)
    records = []
    for dataset, part in frame.groupby("dataset"):
        other = [any(o[0] != dataset for o in owners[s]) for s in part.signature]
        historical = [any(o[0] in HISTORICAL for o in owners[s]) for s in part.signature]
        same = [any(o[0] == dataset and (o[1], o[2]) != (sp, u) for o in owners[s])
                for s, sp, u in zip(part.signature, part.split, part.unit)]
        records.append({"dataset": dataset, "healthy_flights": len(part),
                        "distinct_signatures": part.signature.nunique(),
                        "share_signature_in_other_subset": sum(other) / len(part),
                        "share_signature_in_DS02_or_DS03": (sum(historical) / len(part)
                                                            if dataset not in HISTORICAL else float("nan")),
                        "share_signature_in_other_engine_same_subset": sum(same) / len(part)})
    return pd.DataFrame(records)


def main():
    frame = signatures(pd.read_csv(SEGMENTS))
    pairs = engine_pairs(frame)
    pairs.to_csv(OUT_PAIRS, index=False)
    summary = dataset_summary(frame)
    summary.to_csv(OUT_DATASETS, index=False)
    identical = pairs[pairs.identical_profile_sequence]
    print(summary.round(3).to_string(index=False))
    print(identical[["dataset_a", "split_a", "unit_a", "dataset_b", "split_b", "unit_b",
                     "aligned_identical_flights", "aligned_overlap"]].to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
