"""Calibration arms, persistence rules, flight thresholds and composition designs (protocol sections 5 and 7).

All functions are pure. They receive calibration-side arrays only, except `apply_*`, which applies
locked thresholds to any rows.
"""

from __future__ import annotations

import itertools
import math
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import numpy as np

import ext_common as ec
import ext_qfit
import mssp_adversarial as ma
import mssp_mitigation as mm

PHASES = ("climb", "cruise", "descent")
FLIGHT_FALSE_FLAG_TARGET = mm.FLIGHT_FALSE_FLAG_TARGET  # 0.05 (frozen D-3)
Q_STRIDE = ma.QR_STRIDE  # 5 (frozen adversarial Part D)
Q_WORKERS = int(os.environ.get("NCMAPSS_Q_WORKERS", "10"))


# ---------------------------------------------------------------------------
# Row thresholds: P, C (quantiles) and Q (continuous context)
# ---------------------------------------------------------------------------

def quantile_taus(scores, phase, alpha):
    q = 1 - alpha
    return {"pooled": mm.q_higher(scores, q),
            "phase_conditioned": [mm.q_higher(scores[phase == i], q) for i in range(3)]}


def q_scale(cal_w):
    """Calibration mean and SD of W (frozen `mssp_adversarial.standardize` arithmetic)."""
    w = np.asarray(cal_w[:, :4], dtype=np.float64)
    mean, sd = w.mean(axis=0), w.std(axis=0)
    sd[sd == 0] = 1.0
    return {"mean": mean.tolist(), "sd": sd.tolist()}


def q_features(w, scale):
    z = (np.asarray(w[:, :4], dtype=np.float64) - np.asarray(scale["mean"])) / np.asarray(scale["sd"])
    return ma.quadratic_surface(z)


def fit_q_thresholds(features, score_map, targets=ec.TARGETS, workers=Q_WORKERS):
    """One frozen-specification linear program per run x target, in parallel processes."""
    jobs = [(name, alpha) for name in score_map for alpha in targets]
    args = [(features, score_map[name], 1 - alpha) for name, alpha in jobs]
    context = multiprocessing.get_context("spawn")  # never fork a multi-threaded CUDA process
    with ProcessPoolExecutor(max_workers=min(workers, len(args)), mp_context=context) as pool:
        results = list(pool.map(ext_qfit.fit_job, args))
    return {(name, alpha): {"intercept": intercept, "coef": coef, "fit_rows": n_fit, "stride": Q_STRIDE}
            for (name, alpha), (intercept, coef, n_fit) in zip(jobs, results)}


def predict_q(features, entry):
    """Locked Q threshold per row; the same arithmetic is used in the lock and the audit."""
    return entry["intercept"] + features @ np.asarray(entry["coef"], dtype=np.float64)


def row_thresholds(arm, taus, phase, q_values=None):
    if arm == "pooled":
        return np.full(len(phase), taus["pooled"], dtype=np.float64)
    if arm == "phase_conditioned":
        return np.asarray(taus["phase_conditioned"], dtype=np.float64)[phase]
    if arm == "quantile_regression_W":
        return np.asarray(q_values, dtype=np.float64)
    raise ValueError(arm)


# ---------------------------------------------------------------------------
# Alarm-persistence rules (R0, R1, R2) and flight statistics
# ---------------------------------------------------------------------------

def flight_bounds(meta):
    return mm.flight_bounds(meta)


def position_in_flight(starts, ends, n):
    position = np.arange(n, dtype=np.int64)
    first = np.repeat(starts, ends - starts)
    return position - first, first


def apply_rule(exceed, starts, ends, rule):
    """Row alarm indicator under a persistence rule; windows never cross a flight boundary."""
    e = np.asarray(exceed, dtype=bool)
    if rule == "R0":
        return e.copy()
    width, need = {"R1": (3, 3), "R2": (5, 3)}[rule]
    n = len(e)
    _, first = position_in_flight(starts, ends, n)
    prefix = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(e, out=prefix[1:])
    index = np.arange(n, dtype=np.int64)
    left = np.maximum(first, index - width + 1)
    return (prefix[index + 1] - prefix[left]) >= need


def flight_fraction(alarm, starts, ends):
    return mm.flight_alarm_counts(alarm, starts) / (ends - starts)


def flight_events(alarm, starts, ends):
    """Number of maximal alarm runs per flight."""
    a = np.asarray(alarm, dtype=bool)
    previous = np.zeros(len(a), dtype=bool)
    previous[1:] = a[:-1]
    previous[starts] = False
    rising = a & ~previous
    return np.add.reduceat(rising.astype(np.int64), starts)


def kappa(fraction):
    return mm.q_higher(fraction, 1 - FLIGHT_FALSE_FLAG_TARGET)


# ---------------------------------------------------------------------------
# Composition designs (protocol section 7): metadata and calibration data only
# ---------------------------------------------------------------------------

@dataclass
class Design:
    name: str
    codes: tuple
    members: dict           # engine -> rows taken (None = all rows, the full volume)
    classes: tuple
    volume: str = "N"
    notes: str = ""
    record: dict = field(default_factory=dict)

    def as_record(self):
        return {"name": self.name, "codes": list(self.codes), "members": {str(k): v for k, v in self.members.items()},
                "classes": list(self.classes), "volume": self.volume, "notes": self.notes}


def _split(total, engines):
    engines = sorted(engines)
    base, remainder = divmod(total, len(engines))
    return {g: base + (1 if i < remainder else 0) for i, g in enumerate(engines)}


def _balanced(total, by_class):
    per_class = _split(total, sorted(by_class))
    members = {}
    for k, engines in by_class.items():
        members.update(_split(per_class[k], engines))
    return members


def build_designs(pool_classes, volume):
    """pool_classes: {engine: flight class} of the calibration pool; volume: N rows."""
    pool = sorted(pool_classes)
    classes = sorted(set(pool_classes.values()))
    by_class = {k: [g for g in pool if pool_classes[g] == k] for k in classes}
    rep = {k: min(by_class[k]) for k in classes}
    designs = []
    for g in pool:
        codes = ["A"]
        if len(classes) == 2 and rep[pool_classes[g]] == g:
            codes.append("D")  # 2-class pool: leave-one-class-out equals the other class's representative
        designs.append(Design(f"single_{g}", tuple(codes), {g: volume}, (pool_classes[g],)))
    for k in classes:
        if len(by_class[k]) >= 2:
            designs.append(Design(f"same_class_{k}", ("B",), _split(volume, by_class[k]), (k,)))
    for k, l in itertools.combinations(classes, 2):
        codes = ["C"]
        if len(classes) == 3:
            codes.append("D")
        if len(classes) == 2:
            codes.append("E")
        designs.append(Design(f"mixed_{k}{l}", tuple(codes), _split(volume, [rep[k], rep[l]]), (k, l)))
    if len(classes) >= 3:
        designs.append(Design("balanced", ("E",), _split(volume, [rep[k] for k in classes]), tuple(classes)))
    if any(len(v) >= 2 for v in by_class.values()) and len(classes) >= 2:
        designs.append(Design("balanced_all_engines", ("E+",), _balanced(volume, by_class), tuple(classes)))
    for g in pool:
        designs.append(Design(f"full_{g}", ("V",), {g: None}, (pool_classes[g],), volume="full"))
    designs.append(Design("full_pool", ("V",), {g: None for g in pool}, tuple(classes), volume="full",
                          notes="identical to the primary full calibration"))
    for design in designs:
        taken = sum(v for v in design.members.values() if v is not None)
        if design.volume == "N" and taken != volume:
            raise ec.ExtensionError(f"Design {design.name} is not row-count matched ({taken} != {volume})")
    return designs


def engine_permutations(cal_units, draws=ec.COMPOSITION_DRAWS):
    """Nested, common subsamples: a fixed permutation of each engine's calibration rows per draw."""
    units = np.asarray(cal_units)
    index = {int(g): np.flatnonzero(units == g) for g in np.unique(units)}
    return {(r, g): rows[np.random.default_rng([ec.COMPOSITION_BASE_SEED, r, g]).permutation(len(rows))]
            for r in draws for g, rows in index.items()}, index


def design_rows(design, permutations, index, draw):
    parts = []
    for g, n in sorted(design.members.items()):
        if n is None:
            parts.append(index[g])
        else:
            if n > len(index[g]):
                raise ec.ExtensionError(f"Design {design.name}: engine {g} has fewer than {n} rows")
            parts.append(permutations[(draw, g)][:n])
    return np.sort(np.concatenate(parts))


def design_thresholds(designs, cal_units, cal_phase, score_map, targets=ec.TARGETS, draws=ec.COMPOSITION_DRAWS):
    """P and C thresholds per design x draw x run x target (full-volume designs use draw -1)."""
    permutations, index = engine_permutations(cal_units, draws)
    out = {}
    for design in designs:
        design_draws = (-1,) if design.volume == "full" else draws
        for r in design_draws:
            rows = design_rows(design, permutations, index, max(r, 0))
            phase = cal_phase[rows]
            for name, scores in score_map.items():
                values = scores[rows]
                for alpha in targets:
                    out[(design.name, r, name, alpha)] = quantile_taus(values, phase, alpha)
    return out
