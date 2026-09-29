"""Adversarial validation of the MSSP post-confirmation analysis.

Implements docs/mssp/adversarial_validation_plan.md (frozen 2026-09-28, commit 39a5f81).
The frozen modules are imported unchanged. Healthy rows are rescored with the frozen
detectors through the unchanged `mssp_mitigation` code path, and the rescored vectors
must match the reproduction-gate fingerprints bit for bit. No `hs = 0` row is read:
abnormal-state information comes only from the committed Stage E flight- and row-count
tables. Every output is a new file under the output root.

Parts:
  A  calibration quality (A1-A7) and an extended U1 bootstrap
  B  flight-level operating characteristic on a calibration-only kappa grid; matched
     false-flag comparisons
  C  operating-support distances and their association with calibration error
  D  (conditional) quantile-regression contextual baseline, healthy side only
  R  target robustness and denominator audit (both datasets; see `summarize`)
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

import mssp_mitigation as mm
from mssp_mitigation import (  # noqa: F401  (re-exported frozen constants)
    ALTERNATIVES, FAMILIES, PHASES, PRIMARY_TARGET, REGIMES, RUNS, SCHEMES, TARGETS, GateError,
)

fv = mm.fv
ROOT = mm.ROOT
PLAN = ROOT / "docs/mssp/adversarial_validation_plan.md"
PLAN_SHA256 = "d993dd3f9e5ab28615f22e8559af4fe33548a853ddfce3ce765a9043bb217cfd"
MITIGATION_ROOT = ROOT / "results/mssp_mitigation"
DEFAULT_OUTPUT_ROOT = ROOT / "results/mssp_adversarial"

ARM_LABEL = {"pooled": "P", "phase_conditioned": "C", "causal_regime": "C' (past-only regime)"}
FIXED_KAPPA_GRID = np.geomspace(1e-4, 1.0, 400)
ANCHORS = (0.025, 0.05, 0.10, 0.15, 0.20)
CURVE_GRID = np.round(np.arange(0.025, 0.20 + 1e-9, 0.0025), 6)
DETECTED_WITHIN = (0, 1, 3, 5, 10)
SUPPORT_REFERENCE_QUANTILE = 0.95
W_NAMES = ("alt", "Mach", "TRA", "T2")
SLOPE_NAMES = tuple(f"slope120_{name}" for name in W_NAMES)
QR_STRIDE = 5
CATEGORY_NAMES = {
    1: "EQUALITY IMPROVES AND NOMINAL CALIBRATION IMPROVES",
    2: "EQUALITY IMPROVES BUT NOMINAL CALIBRATION DOES NOT",
    3: "MIXED",
    4: "CONDITIONING WORSENS BOTH",
}
ERROR_METRICS = ("spread", "max_abs_error", "rms_error", "mean_abs_error", "overall_abs_error")
EW_METRICS = ("spread", "max_abs_error", "rms_error", "mean_abs_error")
KEYS = ["dataset", "detector", "seed", "nominal_fpr"]


# ---------------------------------------------------------------------------
# Provenance and guards
# ---------------------------------------------------------------------------

def verify_plan():
    digest = mm.file_digest(PLAN)
    if digest != PLAN_SHA256:
        raise GateError(f"Adversarial validation plan changed after freeze: {digest}")
    return digest


def module_record():
    return {"plan": mm.rel(PLAN), "plan_sha256": verify_plan(),
            "module_sha256": mm.file_digest(Path(__file__)),
            "frozen_module_sha256": mm.file_digest(Path(mm.__file__)),
            "git": mm.git_record()}


def read_frozen_csv(dataset, stage, table):
    return pd.read_csv(MITIGATION_ROOT / dataset / f"stage_{stage}" / f"{table}.csv",
                       float_precision="round_trip")


def guard_adversarial_output(path):
    """Outputs may only go below results/mssp_adversarial (plan rule R1), never into frozen paths."""
    path = mm.guard_output(path)
    root = DEFAULT_OUTPUT_ROOT.resolve()
    if path != root and root not in path.parents:
        raise PermissionError(f"Adversarial outputs must stay below {mm.rel(root)}: {path}")
    return path


def assert_healthy_only(*frames):
    for frame in frames:
        if (frame.healthy.to_numpy() != 1).any():
            raise GateError("A loaded row is not hs = 1; abnormal rows must not be read")


def run_label(detector, seed):
    return f"{detector}:{seed}"


# ---------------------------------------------------------------------------
# Shared healthy context (rescored exactly as in Stages C/L/D)
# ---------------------------------------------------------------------------

def load_context(spec):
    """Rescore healthy rows and verify fingerprints, the lock, and the Stage D count tables."""
    fv.configure_cuda_runtime()
    inputs = mm.verify_inputs(spec)
    base = MITIGATION_ROOT / spec.key
    lock, lock_digest = mm.load_verified_lock(base)
    ctx = mm.prepare_healthy_context(spec)
    assert_healthy_only(ctx.cal_meta, ctx.test_meta)
    mm.verify_fingerprints(ctx, base)
    cal_regime = mm.causal_regime(ctx.cal_alt, ctx.cal_meta.unit.to_numpy(), ctx.cal_meta.cycle.to_numpy())
    test_regime = mm.causal_regime(ctx.test_alt, ctx.test_meta.unit.to_numpy(),
                                   ctx.test_meta.cycle.to_numpy())
    recomputed = mm.build_mitigation_lock(spec.key, ctx.cal_scores, ctx.cal_meta, cal_regime)
    if mm.canonical_json(recomputed) != mm.canonical_json(lock):
        raise GateError("Recomputed calibration lock differs from mitigation_lock.json")
    tables = mm.healthy_endpoint_tables(spec.key, lock, ctx.test_scores, ctx.test_meta, test_regime)
    check = compare_counts(tables["healthy_phase_fpr_by_scheme"],
                           read_frozen_csv(spec.key, "d", "healthy_phase_fpr_by_scheme"))
    return {"inputs": inputs, "lock": lock, "lock_sha256": lock_digest, "ctx": ctx,
            "cal_regime": cal_regime, "test_regime": test_regime, "stage_d_check": check}


def compare_counts(recomputed, committed):
    """Recomputed P/C/C' healthy count tables must equal the committed Stage D table exactly."""
    keys = ["dataset", "detector", "seed", "nominal_fpr", "scheme", "unit", "phase"]
    left = recomputed.assign(unit=recomputed.unit.astype(str)).sort_values(keys).reset_index(drop=True)
    right = committed.assign(unit=committed.unit.astype(str)).sort_values(keys).reset_index(drop=True)
    if len(left) != len(right):
        raise GateError(f"Stage D row count differs: {len(left)} != {len(right)}")
    for column in keys:
        if not (left[column].astype(str).to_numpy() == right[column].astype(str).to_numpy()).all():
            raise GateError(f"Stage D key column {column} differs")
    for column in ("n", "alarms"):
        if not (left[column].astype(np.int64).to_numpy() == right[column].astype(np.int64).to_numpy()).all():
            raise GateError(f"Stage D {column} differs from the committed table")
    rate_diff = float(np.nanmax(np.abs(left.rate.to_numpy(float) - right.rate.to_numpy(float))))
    if rate_diff != 0.0:
        raise GateError(f"Stage D rates differ by {rate_diff}")
    return {"rows_compared": int(len(left)), "max_abs_rate_difference": rate_diff, "exact": True}


# ---------------------------------------------------------------------------
# Part A: calibration quality
# ---------------------------------------------------------------------------

def calibration_errors(fpr_by_phase, overall, alpha):
    """A1-A5 from per-phase FPRs (climb, cruise, descent) and the overall FPR."""
    values = np.asarray(fpr_by_phase, dtype=np.float64)
    error = values - alpha
    return {"spread": float(values.max() - values.min()),
            "max_abs_error": float(np.max(np.abs(error))),
            "rms_error": float(math.sqrt(np.mean(error * error))),
            "mean_abs_error": float(np.mean(np.abs(error))),
            "overall_abs_error": float(abs(overall - alpha))}


def category(delta_spread, delta_max, delta_rms):
    """Plan section 2.1 category rule on arm-minus-pooled differences (negative = better)."""
    if delta_spread < 0 and delta_max < 0 and delta_rms < 0:
        return 1
    if delta_spread < 0 and delta_max >= 0 and delta_rms >= 0:
        return 2
    if delta_spread >= 0 and delta_max >= 0 and delta_rms >= 0:
        return 4
    return 3


def calibration_quality_table(rates):
    """Per-engine, row-pooled, and equal-engine-weighted A1-A7 for every run, target, and arm."""
    rows = []
    group_keys = ["dataset", "detector", "seed", "nominal_fpr", "scheme"]
    for keys, part in rates.groupby(group_keys, sort=False):
        base = dict(zip(group_keys, keys))
        alpha = float(base["nominal_fpr"])
        lookup = {(str(r.unit), r.phase): r for r in part.itertuples(index=False)}
        engines = sorted({str(u) for u in part.unit if str(u) != "all"}, key=int)
        for unit in engines + ["all"]:
            fpr = [float(lookup[(unit, p)].rate) for p in PHASES]
            total = lookup[(unit, "overall")]
            row = {**base, "unit": unit, "weighting": "row_pooled" if unit == "all" else "per_engine",
                   "rows": int(total.n), "alarms": int(total.alarms), "overall_fpr": float(total.rate)}
            for p, value in zip(PHASES, fpr):
                cell = lookup[(unit, p)]
                row[f"{p}_fpr"] = value
                row[f"{p}_rows"] = int(cell.n)
                row[f"{p}_alarms"] = int(cell.alarms)
                row[f"{p}_row_share"] = cell.n / total.n
                row[f"{p}_alarm_share"] = cell.alarms / total.alarms if total.alarms else float("nan")
                row[f"{p}_ratio_to_alpha"] = value / alpha
            row.update(calibration_errors(fpr, float(total.rate), alpha))
            rows.append(row)
        fpr_ew = [float(np.mean([lookup[(e, p)].rate for e in engines])) for p in PHASES]
        overall_ew = float(np.mean([lookup[(e, "overall")].rate for e in engines]))
        row = {**base, "unit": "equal_engine", "weighting": "equal_engine", "overall_fpr": overall_ew,
               **{f"{p}_fpr": v for p, v in zip(PHASES, fpr_ew)},
               **{f"{p}_ratio_to_alpha": v / alpha for p, v in zip(PHASES, fpr_ew)}}
        row.update(calibration_errors(fpr_ew, overall_ew, alpha))
        rows.append(row)
    return pd.DataFrame(rows)


def paired_quality_table(quality):
    """Arm-minus-pooled differences (negative = improvement) and the plan category."""
    keys = KEYS + ["unit", "weighting"]
    pooled = quality[quality.scheme == "pooled"].set_index(keys)
    rows = []
    for arm in ALTERNATIVES:
        part = quality[quality.scheme == arm].set_index(keys)
        for key, row in part.iterrows():
            ref = pooled.loc[key]
            entry = dict(zip(keys, key))
            entry["arm"] = arm
            for metric in ERROR_METRICS + ("overall_fpr",):
                entry[f"pooled_{metric}"] = float(ref[metric])
                entry[f"arm_{metric}"] = float(row[metric])
                entry[f"diff_{metric}"] = float(row[metric] - ref[metric])
            code = category(entry["diff_spread"], entry["diff_max_abs_error"], entry["diff_rms_error"])
            entry["category"] = code
            entry["category_name"] = CATEGORY_NAMES[code]
            rows.append(entry)
    return pd.DataFrame(rows)


def family_seed_means(quality):
    """Descriptive family arithmetic seed means (no interval is attached)."""
    metrics = [c for c in quality.columns if (c.endswith("_fpr") and c != "nominal_fpr") or c in ERROR_METRICS]
    frame = quality.assign(family=quality.detector)
    out = frame.groupby(["dataset", "family", "nominal_fpr", "scheme", "unit", "weighting"],
                        sort=False)[metrics].mean().reset_index()
    out["seeds"] = frame.groupby(["dataset", "family", "nominal_fpr", "scheme", "unit", "weighting"],
                                 sort=False).size().to_numpy()
    out["summary"] = "arithmetic seed mean; descriptive only; no interval"
    return out


def wording_verdicts(paired):
    """Plan section 2.1 wording rule per dataset x arm (row-pooled categories)."""
    rows = []
    pooled = paired[paired.weighting == "row_pooled"]
    engines = paired[paired.weighting == "per_engine"]
    for (dataset, arm), part in pooled.groupby(["dataset", "arm"], sort=False):
        counts = {alpha: int((part[part.nominal_fpr == alpha].category == 1).sum()) for alpha in TARGETS}
        runs = int((part.nominal_fpr == PRIMARY_TARGET).sum())
        spread_reduced = int((part[part.nominal_fpr == PRIMARY_TARGET].diff_spread < 0).sum())
        engine_part = engines[(engines.dataset == dataset) & (engines.arm == arm)
                              & (engines.nominal_fpr == PRIMARY_TARGET)]
        contradicted = 0
        engine_list = sorted(engine_part.unit.unique(), key=int)
        for unit in engine_list:
            if int((engine_part[engine_part.unit == unit].category == 1).sum()) < 4:
                contradicted += 1
        calibration_ok = (counts[PRIMARY_TARGET] >= 6 and counts[0.005] >= 5 and counts[0.02] >= 5
                          and contradicted < len(engine_list) / 2)
        if calibration_ok:
            wording = "improved nominal phase-wise calibration"
        elif spread_reduced >= 4:
            wording = "reduced between-phase disparity"
        else:
            wording = "no consistent reduction of between-phase disparity"
        rows.append({"dataset": dataset, "arm": arm, "runs": runs,
                     "category1_runs_alpha_0.005": counts[0.005],
                     "category1_runs_alpha_0.01": counts[PRIMARY_TARGET],
                     "category1_runs_alpha_0.02": counts[0.02],
                     "spread_reduced_runs_alpha_0.01": spread_reduced,
                     "engines_contradicting_category1": contradicted, "engines": len(engine_list),
                     "allowed_wording": wording})
    return pd.DataFrame(rows)


def engine_weights(flights, multiplicity):
    """Times each engine was drawn in an engine->flight replicate (flights per draw = n_e)."""
    units = np.array([unit for unit, _, _ in flights])
    engines, index = np.unique(units, return_inverse=True)
    per_engine = np.bincount(index, weights=multiplicity.astype(np.float64), minlength=len(engines))
    sizes = np.bincount(index, minlength=len(engines)).astype(np.float64)
    times = per_engine / sizes
    if not np.allclose(times, np.round(times)):
        raise GateError("Engine draw counts are not integral; resampling plan layout changed")
    return np.round(times), index


def extended_replicate(run, cal_multiplicity, test_multiplicity, alpha, flight_engine, n_engines,
                       engine_times):
    """U1 replicate with calibration-quality metrics (row-pooled and equal-engine)."""
    taus = run.views.taus(cal_multiplicity, 1 - alpha)
    weight = test_multiplicity[run.cell_flight].astype(np.float64)
    rows = np.bincount(run.cell_phase, weights=weight * run.sizes, minlength=3)
    cell_engine = flight_engine[run.cell_flight]
    engine_phase = cell_engine * 3 + run.cell_phase
    rows_e = np.bincount(engine_phase, weights=weight * run.sizes, minlength=n_engines * 3).reshape(n_engines, 3)
    drawn = engine_times > 0
    out, frozen_named = {}, {}
    for scheme in SCHEMES:
        above = run.counter.above(mm.cell_thresholds(scheme, taus, run.cell_phase, run.cell_regime))
        alarms = np.bincount(run.cell_phase, weights=weight * above, minlength=3)
        fpr = alarms / rows
        overall = alarms.sum() / rows.sum()
        metrics = calibration_errors(fpr, overall, alpha)
        out[f"{scheme}.overall_fpr"] = overall
        for i, phase in enumerate(PHASES):
            out[f"{scheme}.{phase}_fpr"] = fpr[i]
            out[f"{scheme}.{phase}_alarm_share"] = alarms[i] / alarms.sum() if alarms.sum() else float("nan")
        for name, value in metrics.items():
            out[f"{scheme}.{name}"] = value
        alarms_e = np.bincount(engine_phase, weights=weight * above, minlength=n_engines * 3).reshape(n_engines, 3)
        with np.errstate(invalid="ignore", divide="ignore"):
            fpr_e = alarms_e[drawn] / rows_e[drawn]
        ew = (engine_times[drawn, None] * fpr_e).sum(axis=0) / engine_times[drawn].sum()
        ew_metrics = calibration_errors(ew, float(np.mean(ew)), alpha)
        for name in EW_METRICS:
            out[f"{scheme}.ew_{name}"] = ew_metrics[name]
        frozen_named[f"{scheme}.overall_fpr"] = overall
        for i, phase in enumerate(PHASES):
            frozen_named[f"{scheme}.{phase}_fpr"] = fpr[i]
        frozen_named[f"{scheme}.spread"] = metrics["spread"]
        frozen_named[f"{scheme}.mpce"] = metrics["max_abs_error"]
    for arm in ALTERNATIVES:
        for name in ERROR_METRICS + ("overall_fpr",):
            out[f"diff_{name}.{arm}"] = out[f"{arm}.{name}"] - out[f"pooled.{name}"]
        for name in EW_METRICS:
            out[f"diff_ew_{name}.{arm}"] = out[f"{arm}.ew_{name}"] - out[f"pooled.ew_{name}"]
        frozen_named[f"delta_spread.{arm}"] = frozen_named["pooled.spread"] - frozen_named[f"{arm}.spread"]
        frozen_named[f"delta_mpce.{arm}"] = frozen_named["pooled.mpce"] - frozen_named[f"{arm}.mpce"]
    return out, frozen_named


def extended_u1(ctx, cal_regime, test_regime, committed_u1, *, replicates=mm.REPLICATES, seed=mm.U1_SEED):
    """Extended U1 on the frozen plans; frozen-named metrics must equal the committed U1 at 1%."""
    rng = np.random.default_rng(seed)
    cal_flights, cal_plans = fv.bootstrap_plans(ctx.cal_meta, replicates, rng)
    test_flights, test_plans = fv.bootstrap_plans(ctx.test_meta, replicates, rng)
    ones_cal = np.ones(len(cal_flights), dtype=np.int64)
    ones_test = np.ones(len(test_flights), dtype=np.int64)
    _, flight_engine = engine_weights(test_flights, ones_test)
    n_engines = int(flight_engine.max()) + 1
    cal_phase, test_phase = ctx.cal_meta.phase_primary.to_numpy(), ctx.test_meta.phase_primary.to_numpy()
    rows, worst = [], 0.0
    for name in RUNS:
        run = mm.U1Run(ctx.cal_scores[name], cal_phase, cal_regime, cal_flights,
                       ctx.test_scores[name], test_phase, test_regime, test_flights)
        for alpha in TARGETS:
            point, _ = extended_replicate(run, ones_cal, ones_test, alpha, flight_engine, n_engines,
                                          np.ones(n_engines))
            records, frozen_records = [], []
            for b in range(replicates):
                times, _ = engine_weights(test_flights, test_plans[b])
                record, frozen_named = extended_replicate(run, cal_plans[b], test_plans[b], alpha,
                                                          flight_engine, n_engines, times)
                records.append(record)
                frozen_records.append(frozen_named)
            if alpha == PRIMARY_TARGET:
                worst = max(worst, self_check_u1(name, frozen_records, committed_u1))
            for row in mm.summarize_replicates(records):
                rows.append({"detector": name[0], "seed": name[1], "nominal_fpr": alpha,
                             "bootstrap_unit": "engine_then_flight (frozen U1 plans)",
                             "threshold_reestimated": True, "point_estimate": point[row["metric"]], **row})
        print(f"Extended U1 complete: {name}", flush=True)
    return pd.DataFrame(rows), worst


def self_check_u1(name, frozen_records, committed_u1):
    summary = {row["metric"]: row for row in mm.summarize_replicates(frozen_records)}
    part = committed_u1[(committed_u1.detector == name[0]) & (committed_u1.seed == name[1])]
    worst, compared = 0.0, 0
    for row in part.itertuples(index=False):
        if row.metric not in summary:
            continue
        compared += 1
        for column in ("bootstrap_mean", "ci_lower_95", "ci_upper_95"):
            worst = max(worst, abs(float(summary[row.metric][column]) - float(getattr(row, column))))
    if compared < 20:
        raise GateError(f"U1 self-check compared only {compared} metrics for {name}")
    if worst > mm.BOOTSTRAP_ATOL:
        raise GateError(f"Extended U1 differs from the committed U1 by {worst} for {name}")
    return worst


def part_a(spec, context, out):
    rates = read_frozen_csv(spec.key, "d", "healthy_phase_fpr_by_scheme")
    quality = calibration_quality_table(rates)
    committed = read_frozen_csv(spec.key, "d", "healthy_stability_by_scheme")
    check = quality[quality.unit != "equal_engine"].merge(
        committed.assign(unit=committed.unit.astype(str)), on=KEYS + ["scheme", "unit"], suffixes=("", "_frozen"))
    mpce_diff = float(np.max(np.abs(check.max_abs_error - check.mpce)))
    spread_diff = float(np.max(np.abs(check.spread - check.spread_frozen)))
    if len(check) != len(committed) or mpce_diff > 1e-15 or spread_diff > 1e-15:
        raise GateError(f"A1/A2 do not reproduce the frozen spread/MPCE ({spread_diff}, {mpce_diff})")
    paired = paired_quality_table(quality)
    u1, worst = extended_u1(context["ctx"], context["cal_regime"], context["test_regime"],
                            read_frozen_csv(spec.key, "d", "u1_bootstrap_ci"))
    tables = {"calibration_quality_metrics": quality, "calibration_quality_paired": paired,
              "calibration_quality_family_means": family_seed_means(quality),
              "calibration_quality_u1_ci": u1}
    hashes = {name: mm.write_csv(out / f"{name}.csv", frame) for name, frame in tables.items()}
    return hashes, {"spread_reproduction_max_abs_diff": spread_diff, "mpce_reproduction_max_abs_diff": mpce_diff,
                    "extended_u1_self_check_max_abs_diff": worst}


# ---------------------------------------------------------------------------
# Part B: flight-level operating characteristic and matched false-flag comparisons
# ---------------------------------------------------------------------------

def calibration_flight_fractions(ctx, cal_regime, lock):
    """Healthy calibration-flight alarm fractions; their 0.95 higher quantile must equal kappa."""
    phase = ctx.cal_meta.phase_primary.to_numpy()
    starts, ends = mm.flight_bounds(ctx.cal_meta)
    rows = (ends - starts).astype(np.float64)
    units = ctx.cal_meta.unit.to_numpy()[starts].astype(int)
    cycles = ctx.cal_meta.cycle.to_numpy()[starts].astype(int)
    fractions, frames = {}, []
    for detector, seed in RUNS:
        entry = mm_entry(lock, detector, seed)
        for alpha in TARGETS:
            tau, kappa = entry[str(alpha)]["tau"], entry[str(alpha)]["kappa"]
            for scheme in SCHEMES:
                alarm = ctx.cal_scores[(detector, seed)] > mm.row_thresholds(scheme, tau, phase, cal_regime)
                counts = mm.flight_alarm_counts(alarm, starts)
                fraction = counts / rows
                if mm.q_higher(fraction, 1 - mm.FLIGHT_FALSE_FLAG_TARGET) != kappa[scheme]:
                    raise GateError(f"Recomputed kappa differs from the lock: {detector}:{seed} {alpha} {scheme}")
                fractions[(detector, seed, alpha, scheme)] = fraction
                frames.append(pd.DataFrame({"detector": detector, "seed": seed, "nominal_fpr": alpha,
                                            "scheme": scheme, "unit": units, "cycle": cycles,
                                            "rows": rows.astype(int), "alarms": counts,
                                            "alarm_fraction": fraction, "kappa_locked": kappa[scheme]}))
    return fractions, pd.concat(frames, ignore_index=True)


def mm_entry(lock, detector, seed):
    return lock["runs"][run_label(detector, seed)]


def verify_trajectories(traj, delays, lock):
    """Locked-kappa delays recomputed from the trajectory table must equal detection_delay.csv."""
    checked = 0
    index = delays.set_index(["detector", "seed", "nominal_fpr", "scheme", "unit"])
    for (detector, seed, alpha, scheme), part in traj.groupby(["detector", "seed", "nominal_fpr", "scheme"]):
        kappa = mm_entry(lock, detector, seed)[str(alpha)]["kappa"][scheme]
        if not np.all(part.kappa.to_numpy() == kappa):
            raise GateError("Trajectory kappa differs from the lock")
        flagged = part.alarm_fraction.to_numpy() > kappa
        if not np.array_equal(flagged, part.flagged.to_numpy(bool)):
            raise GateError("Trajectory flags do not reproduce from alarm fractions")
        for unit, unit_part in part.groupby("unit"):
            post = unit_part[unit_part.state == "post_onset"].sort_values("k")
            series = post.alarm_fraction.to_numpy() > kappa
            healthy = unit_part[unit_part.state == "healthy"].alarm_fraction.to_numpy() > kappa
            d1, d3 = mm.first_flag(series), mm.persistence_flag(series)
            row = index.loc[(detector, seed, alpha, scheme, unit)]
            same = (bool(row.censored) == bool(np.isinf(d1))
                    and (np.isinf(d1) or float(row.delay_flights) == d1)
                    and bool(row.persistence_censored) == bool(np.isinf(d3))
                    and (np.isinf(d3) or float(row.persistence_delay_flights) == d3)
                    and int(row.healthy_flagged) == int(healthy.sum())
                    and int(row.post_onset_flights) == len(post))
            if not same:
                raise GateError(f"Trajectory table does not reproduce detection_delay.csv at "
                                f"{detector}:{seed} {alpha} {scheme} engine {unit}")
            checked += 1
    return {"engine_rows_checked": checked, "exact": True}


def candidate_kappas(calibration_fraction):
    """Calibration-only grid: {0} U calibration-flight fractions U fixed log grid (data-free)."""
    sources = {}
    for value in FIXED_KAPPA_GRID:
        sources.setdefault(float(value), set()).add("fixed_grid")
    for value in np.unique(calibration_fraction):
        sources.setdefault(float(value), set()).add("calibration_flight_fraction")
    sources.setdefault(0.0, set()).add("zero")
    kappas = np.array(sorted(sources))
    return kappas, ["+".join(sorted(sources[k])) for k in kappas]


def first_exceedance(values, kappas, offset=0):
    """First index whose value exceeds each kappa (prefix-max search); inf when none."""
    if len(values) == 0:
        return np.full(len(kappas), np.inf)
    prefix = np.maximum.accumulate(np.asarray(values, dtype=np.float64))
    index = np.searchsorted(prefix, kappas, side="right").astype(np.float64)
    index[index >= len(values)] = np.inf
    return index + offset


def lower_median_rows(matrix):
    """Inverted-CDF (lower) median along axis 1; censored +inf values rank above observed ones."""
    ordered = np.sort(np.asarray(matrix, dtype=np.float64), axis=1)
    return ordered[:, int(math.ceil(0.5 * ordered.shape[1])) - 1]


def operating_characteristic(part, kappas, sources, engines):
    """Healthy false-flag rate and delay for each candidate kappa (one run, target, and arm)."""
    healthy = part[part.state == "healthy"]
    h_fraction, h_unit = healthy.alarm_fraction.to_numpy(), healthy.unit.to_numpy()
    n_healthy = len(h_fraction)
    ordered = np.sort(h_fraction)
    flagged = n_healthy - np.searchsorted(ordered, kappas, side="right")
    frame = {"kappa": kappas, "kappa_source": sources, "healthy_flights": n_healthy,
             "flagged_healthy": flagged, "ffr": flagged / n_healthy}
    delays, persistence = [], []
    for unit in engines:
        unit_healthy = np.sort(h_fraction[h_unit == unit])
        frame[f"ffr_engine_{unit}"] = (len(unit_healthy) - np.searchsorted(unit_healthy, kappas, side="right")) / max(len(unit_healthy), 1)
        post = part[(part.unit == unit) & (part.state == "post_onset")].sort_values("k").alarm_fraction.to_numpy()
        d1 = first_exceedance(post, kappas)
        pairs = np.minimum(post[1:], post[:-1]) if len(post) > 1 else np.empty(0)
        d3 = first_exceedance(pairs, kappas, offset=1)
        frame[f"delay_engine_{unit}"] = d1
        frame[f"persistence_delay_engine_{unit}"] = d3
        delays.append(d1)
        persistence.append(d3)
    delays, persistence = np.column_stack(delays), np.column_stack(persistence)
    frame["median_delay"] = lower_median_rows(delays)
    frame["median_persistence_delay"] = lower_median_rows(persistence)
    frame["engines_censored"] = np.isinf(delays).sum(axis=1)
    for d in DETECTED_WITHIN:
        frame[f"detected_within_{d}"] = (delays <= d).mean(axis=1)
    return pd.DataFrame(frame)


def distinct_points(curve, engines):
    """Collapse consecutive kappas with identical outcomes into one operating point."""
    outcome = ["flagged_healthy"] + [f"ffr_engine_{u}" for u in engines] + [
        f"delay_engine_{u}" for u in engines] + [f"persistence_delay_engine_{u}" for u in engines]
    values = curve[outcome].to_numpy(dtype=np.float64)
    change = np.r_[True, np.any(values[1:] != values[:-1], axis=1)]
    group = np.cumsum(change) - 1
    agg = {c: "first" for c in curve.columns if c not in ("kappa", "kappa_source")}
    points = curve.groupby(group).agg({**agg, "kappa": ["min", "max", "size"],
                                       "kappa_source": lambda s: "|".join(sorted(set("+".join(s).split("+"))))})
    points.columns = [c if isinstance(c, str) else (c[0] if c[1] in ("first", "<lambda>") else f"{c[0]}_{c[1]}")
                      for c in points.columns]
    points = points.rename(columns={"kappa_min": "kappa_low", "kappa_max": "kappa_high",
                                    "kappa_size": "candidates"})
    return points.reset_index(drop=True)


def match_anchor(points, anchor, n_healthy, rule="nearest"):
    """Operating point matched to a false-flag anchor; no interpolation or extrapolation."""
    ffr = points.ffr.to_numpy()
    tolerance = 1.0 / n_healthy + 1e-12
    if rule == "nearest":
        distance = np.abs(ffr - anchor)
        candidates = points[distance <= distance.min() + 1e-12]
    elif rule == "not_exceeding":
        candidates = points[ffr <= anchor + 1e-12]
        if candidates.empty:
            return None, False
        candidates = candidates[candidates.ffr >= candidates.ffr.max() - 1e-12]
    else:
        raise ValueError(rule)
    chosen = candidates.sort_values(["ffr", "kappa_high"], ascending=[True, False]).iloc[0]
    return chosen, bool(abs(float(chosen.ffr) - anchor) <= tolerance)


def paired_delay(arm_point, pooled_point, engines):
    arm = np.array([arm_point[f"delay_engine_{u}"] for u in engines], dtype=np.float64)
    pooled = np.array([pooled_point[f"delay_engine_{u}"] for u in engines], dtype=np.float64)
    diff = mm.delay_difference(arm, pooled)
    med_arm, med_pooled = mm.lower_median(arm), mm.lower_median(pooled)
    if np.isinf(med_arm) and np.isinf(med_pooled):
        median_difference = 0.0
    else:
        median_difference = med_arm - med_pooled
    return {"earlier": int(np.sum(diff < 0)), "same": int(np.sum(diff == 0)), "later": int(np.sum(diff > 0)),
            "paired_lower_median_difference": mm.lower_median(diff),
            "difference_of_median_delays": median_difference,
            "arm_median_delay": med_arm, "pooled_median_delay": med_pooled}


def run_label_from_differences(differences):
    """Plan section 2.2 label from paired median differences at supported anchors."""
    values = [d for d in differences if not (isinstance(d, float) and math.isnan(d))]
    if not values:
        return "not evaluable"
    negative, positive = sum(v < 0 for v in values), sum(v > 0 for v in values)
    if all(v == 0 for v in values):
        return "equal"
    if negative > len(values) / 2 and positive == 0:
        return "earlier at matched burden"
    if positive > len(values) / 2 and negative == 0:
        return "later at matched burden"
    return "mixed"


def curve_mean(points, n_healthy):
    medians, excluded = [], 0
    for x in CURVE_GRID:
        chosen, supported = match_anchor(points, float(x), n_healthy)
        if not supported:
            excluded += 1
            continue
        medians.append(float(chosen.median_delay))
    if not medians:
        return float("nan"), excluded
    return (float("inf") if np.isinf(medians).any() else float(np.mean(medians))), excluded


def pareto(arm_ffr, arm_delay, pooled_ffr, pooled_delay):
    better = (arm_ffr <= pooled_ffr) and (arm_delay <= pooled_delay)
    worse = (arm_ffr >= pooled_ffr) and (arm_delay >= pooled_delay)
    if better and worse:
        return "identical"
    if better:
        return "arm dominates"
    if worse:
        return "arm dominated"
    return "trade-off"


def part_b(spec, context, out):
    lock, ctx = context["lock"], context["ctx"]
    fractions, calibration_table = calibration_flight_fractions(ctx, context["cal_regime"], lock)
    traj = read_frozen_csv(spec.key, "e", "flight_alarm_fraction_trajectories")
    delays = read_frozen_csv(spec.key, "e", "detection_delay")
    trajectory_check = verify_trajectories(traj, delays, lock)
    engines = sorted(int(u) for u in delays[delays.eligible].unit.unique())
    healthy_counts = traj[(traj.state == "healthy")].groupby(["detector", "seed", "nominal_fpr", "scheme"]).size()
    n_healthy = int(healthy_counts.iloc[0])
    if not (healthy_counts == n_healthy).all():
        raise GateError("Healthy audit flight count differs across runs")
    curves, point_tables, matched, locked_rows, curve_rows = [], [], [], [], []
    for (detector, seed, alpha), part in traj.groupby(["detector", "seed", "nominal_fpr"], sort=False):
        points = {}
        for scheme in SCHEMES:
            arm_part = part[part.scheme == scheme]
            kappas, sources = candidate_kappas(fractions[(detector, seed, alpha, scheme)])
            curve = operating_characteristic(arm_part, kappas, sources, engines)
            base = {"dataset": spec.key, "detector": detector, "seed": seed, "nominal_fpr": alpha, "scheme": scheme}
            curves.append(curve.assign(**base))
            points[scheme] = distinct_points(curve, engines)
            point_tables.append(points[scheme].assign(**base))
            kappa = mm_entry(lock, detector, seed)[str(alpha)]["kappa"][scheme]
            locked = operating_characteristic(arm_part, np.array([kappa]), ["locked"], engines).iloc[0]
            mean_delay, excluded = curve_mean(points[scheme], n_healthy)
            post = arm_part[arm_part.state == "post_onset"]
            locked_rows.append({**base, "kappa_locked": kappa, "ffr": float(locked.ffr),
                                "median_delay": float(locked.median_delay),
                                "engines_censored": int(locked.engines_censored),
                                **{f"delay_engine_{u}": float(locked[f"delay_engine_{u}"]) for u in engines},
                                **{f"ffr_engine_{u}": float(locked[f"ffr_engine_{u}"]) for u in engines},
                                "mean_post_onset_alarm_fraction": float(post.alarm_fraction.mean()),
                                "median_post_onset_alarm_fraction": float(post.alarm_fraction.median())})
            curve_rows.append({**base, "curve_mean_median_delay_ffr_2.5_to_20": mean_delay,
                               "curve_grid_points_excluded": excluded,
                               "curve_grid_points": len(CURVE_GRID)})
        for arm in ALTERNATIVES:
            for rule in ("nearest", "not_exceeding"):
                for anchor in ANCHORS:
                    pooled_point, pooled_ok = match_anchor(points["pooled"], anchor, n_healthy, rule)
                    arm_point, arm_ok = match_anchor(points[arm], anchor, n_healthy, rule)
                    row = {"dataset": spec.key, "detector": detector, "seed": seed, "nominal_fpr": alpha,
                           "arm": arm, "rule": rule, "anchor_ffr": anchor, "healthy_flights": n_healthy,
                           "supported": bool(pooled_ok and arm_ok)}
                    if pooled_point is not None and arm_point is not None:
                        row.update({"pooled_ffr": float(pooled_point.ffr), "arm_ffr": float(arm_point.ffr),
                                    "ffr_mismatch_arm_minus_pooled": float(arm_point.ffr - pooled_point.ffr),
                                    "pooled_kappa_low": float(pooled_point.kappa_low),
                                    "pooled_kappa_high": float(pooled_point.kappa_high),
                                    "arm_kappa_low": float(arm_point.kappa_low),
                                    "arm_kappa_high": float(arm_point.kappa_high),
                                    **paired_delay(arm_point, pooled_point, engines),
                                    **{f"pooled_delay_engine_{u}": float(pooled_point[f"delay_engine_{u}"]) for u in engines},
                                    **{f"arm_delay_engine_{u}": float(arm_point[f"delay_engine_{u}"]) for u in engines},
                                    **{f"pooled_ffr_engine_{u}": float(pooled_point[f"ffr_engine_{u}"]) for u in engines},
                                    **{f"arm_ffr_engine_{u}": float(arm_point[f"ffr_engine_{u}"]) for u in engines},
                                    **{f"pooled_detected_within_{d}": float(pooled_point[f"detected_within_{d}"]) for d in DETECTED_WITHIN},
                                    **{f"arm_detected_within_{d}": float(arm_point[f"detected_within_{d}"]) for d in DETECTED_WITHIN},
                                    "pooled_engines_censored": int(pooled_point.engines_censored),
                                    "arm_engines_censored": int(arm_point.engines_censored)})
                    matched.append(row)
    matched = pd.DataFrame(matched)
    locked = pd.DataFrame(locked_rows)
    curve_summary = pd.DataFrame(curve_rows)
    labels = matched_labels(matched, locked, curve_summary)
    early = read_frozen_csv(spec.key, "e", "abnormal_alarm_rates")
    early = early[(early.window == "early_first_10") & (early.phase == "overall")]
    tables = {"calibration_flight_fractions": calibration_table,
              "operating_points": pd.concat(point_tables, ignore_index=True),
              "matched_false_flag_comparisons": matched, "locked_operating_points": locked,
              "curve_level_summary": curve_summary, "matched_labels": labels,
              "early_window_row_alarm_rates": early}
    hashes = {name: mm.write_csv(out / f"{name}.csv", frame) for name, frame in tables.items()}
    support = matched[(matched.rule == "nearest") & (matched.nominal_fpr == PRIMARY_TARGET)]
    supported_anchors = support.groupby(["detector", "seed", "arm"]).supported.sum()
    if (supported_anchors < 3).any():
        raise GateError("Fewer than 3 supported anchors at 1%: matched comparison would need extrapolation")
    return hashes, {"trajectory_reproduction": trajectory_check, "healthy_audit_flights": n_healthy,
                    "engines": engines, "min_supported_anchors_at_1pct": int(supported_anchors.min())}


def matched_labels(matched, locked, curve_summary):
    rows = []
    primary = matched[matched.rule == "nearest"]
    for (dataset, detector, seed, alpha, arm), part in primary.groupby(
            ["dataset", "detector", "seed", "nominal_fpr", "arm"], sort=False):
        supported = part[part.supported]
        label = run_label_from_differences(list(supported.paired_lower_median_difference.astype(float)))
        sensitivity = matched[(matched.rule == "not_exceeding") & (matched.dataset == dataset)
                              & (matched.detector == detector) & (matched.seed == seed)
                              & (matched.nominal_fpr == alpha) & (matched.arm == arm) & matched.supported]
        label_conservative = run_label_from_differences(list(sensitivity.paired_lower_median_difference.astype(float)))
        lk = locked[(locked.detector == detector) & (locked.seed == seed) & (locked.nominal_fpr == alpha)]
        arm_locked, pooled_locked = lk[lk.scheme == arm].iloc[0], lk[lk.scheme == "pooled"].iloc[0]
        cv = curve_summary[(curve_summary.detector == detector) & (curve_summary.seed == seed)
                           & (curve_summary.nominal_fpr == alpha)]
        arm_curve = float(cv[cv.scheme == arm].iloc[0]["curve_mean_median_delay_ffr_2.5_to_20"])
        pooled_curve = float(cv[cv.scheme == "pooled"].iloc[0]["curve_mean_median_delay_ffr_2.5_to_20"])
        locked_diff = arm_locked.median_delay - pooled_locked.median_delay if not (
            np.isinf(arm_locked.median_delay) and np.isinf(pooled_locked.median_delay)) else 0.0
        rows.append({"dataset": dataset, "detector": detector, "seed": seed, "nominal_fpr": alpha, "arm": arm,
                     "supported_anchors": int(len(supported)), "matched_label": label,
                     "matched_label_not_exceeding_rule": label_conservative,
                     "locked_ffr_pooled": float(pooled_locked.ffr), "locked_ffr_arm": float(arm_locked.ffr),
                     "locked_median_delay_pooled": float(pooled_locked.median_delay),
                     "locked_median_delay_arm": float(arm_locked.median_delay),
                     "locked_median_delay_difference": float(locked_diff),
                     "locked_pareto": pareto(arm_locked.ffr, arm_locked.median_delay,
                                             pooled_locked.ffr, pooled_locked.median_delay),
                     "curve_mean_pooled": pooled_curve, "curve_mean_arm": arm_curve,
                     "curve_mean_difference": (arm_curve - pooled_curve
                                               if np.isfinite(arm_curve) and np.isfinite(pooled_curve)
                                               else float("nan"))})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Part C: operating-support distances
# ---------------------------------------------------------------------------

def load_healthy_operating(spec):
    """Read A fully and W only for healthy (hs = 1) contiguous row blocks of both splits."""
    data = {}
    with h5py.File(spec.h5_path, "r") as h5:
        mm.check_schema(h5)
        for split in ("dev", "test"):
            a = h5[f"A_{split}"][:]
            mask = mm.healthy_selector(a)
            runs = mm.contiguous_runs(mask)
            w = mm.read_row_blocks(h5[f"W_{split}"], runs)
            meta = mm.build_meta(spec.key, a[mask], w)
            assert_healthy_only(meta)
            data[split] = (w, meta)
    return data


def operating_features(w, meta):
    """4-D static operating point and 8-D static + 120-s trailing slope (frozen descriptors)."""
    from phase3_dynamic import causal_descriptors
    descriptors, names = causal_descriptors(w, meta)
    columns = [names.index(n) for n in W_NAMES + SLOPE_NAMES]
    eight = descriptors[:, columns].astype(np.float64)
    return eight[:, :4], eight


def standardize(reference, *others):
    mean, sd = reference.mean(axis=0), reference.std(axis=0)
    sd[sd == 0] = 1.0
    return [(x - mean) / sd for x in (reference, *others)], {"mean": mean.tolist(), "sd": sd.tolist()}


def nearest_distance(reference, query):
    if len(query) == 0:
        return np.empty(0)
    return cKDTree(reference).query(query, k=1, workers=-1)[0]


def phase_distance(reference, reference_phase, query, query_phase):
    distance = np.full(len(query), np.nan)
    for i in range(3):
        mask = query_phase == i
        distance[mask] = nearest_distance(reference[reference_phase == i], query[mask])
    return distance


def cross_engine_reference(cal4, cal8, cal_phase, cal_units):
    """Same-phase (and any-phase) distance from each calibration engine to the other(s)."""
    rows, pieces = [], {"d_phase": [[], [], []], "d8_phase": [[], [], []], "d_all": []}
    units = np.unique(cal_units)
    for unit in units:
        mine, other = cal_units == unit, cal_units != unit
        d4 = phase_distance(cal4[other], cal_phase[other], cal4[mine], cal_phase[mine])
        d8 = phase_distance(cal8[other], cal_phase[other], cal8[mine], cal_phase[mine])
        dall = nearest_distance(cal4[other], cal4[mine])
        pieces["d_all"].append(dall)
        for i, p in enumerate(PHASES):
            sel = cal_phase[mine] == i
            pieces["d_phase"][i].append(d4[sel])
            pieces["d8_phase"][i].append(d8[sel])
            rows.append({"calibration_engine": int(unit), "phase": p, "rows": int(sel.sum()),
                         "d_phase_median": float(np.median(d4[sel])), "d_phase_p95": float(np.quantile(d4[sel], .95)),
                         "d8_phase_median": float(np.median(d8[sel])), "d8_phase_p95": float(np.quantile(d8[sel], .95)),
                         "d_all_median": float(np.median(dall[sel])), "d_all_p95": float(np.quantile(dall[sel], .95))})
    threshold = {"d_phase": [float(np.quantile(np.concatenate(pieces["d_phase"][i]), SUPPORT_REFERENCE_QUANTILE)) for i in range(3)],
                 "d8_phase": [float(np.quantile(np.concatenate(pieces["d8_phase"][i]), SUPPORT_REFERENCE_QUANTILE)) for i in range(3)],
                 "d_all": float(np.quantile(np.concatenate(pieces["d_all"]), SUPPORT_REFERENCE_QUANTILE))}
    return pd.DataFrame(rows), threshold


def outside_range(reference, reference_phase, query, query_phase):
    outside = np.zeros(len(query), dtype=bool)
    for i in range(3):
        mask = query_phase == i
        if not mask.any():
            continue
        ref = reference[reference_phase == i]
        if len(ref) == 0:
            outside[mask] = True
            continue
        lo, hi = ref.min(axis=0), ref.max(axis=0)
        outside[mask] = np.any((query[mask] < lo) | (query[mask] > hi), axis=1)
    return outside


def support_cell_table(dataset, meta, d_phase, d_all, d8_phase, beyond, outside):
    frame = pd.DataFrame({"unit": meta.unit.to_numpy().astype(int), "flight_class": meta.flight_class.to_numpy().astype(int),
                          "phase_id": meta.phase_primary.to_numpy(), "d_phase": d_phase, "d_all": d_all,
                          "d8_phase": d8_phase, "beyond_phase": beyond["d_phase"], "beyond_8": beyond["d8_phase"],
                          "beyond_all": beyond["d_all"], "outside_range": outside})
    rows = []
    for (unit, phase_id), part in frame.groupby(["unit", "phase_id"]):
        rows.append({"dataset": dataset, "unit": int(unit), "flight_class": int(part.flight_class.iloc[0]),
                     "phase": PHASES[int(phase_id)], "rows": int(len(part)),
                     **{f"{m}_{s}": float(np.quantile(part[m], q)) for m in ("d_phase", "d_all", "d8_phase")
                        for s, q in (("median", .5), ("p90", .9), ("p95", .95))},
                     "fraction_beyond_support_d_phase": float(part.beyond_phase.mean()),
                     "fraction_beyond_support_d8_phase": float(part.beyond_8.mean()),
                     "fraction_beyond_support_d_all": float(part.beyond_all.mean()),
                     "fraction_outside_phase_range": float(part.outside_range.mean())})
    return pd.DataFrame(rows), frame


def class_table(dataset, frame, cal_meta):
    cal_classes = sorted(int(c) for c in np.unique(cal_meta.flight_class))
    rows = []
    for (flight_class, phase_id), part in frame.groupby(["flight_class", "phase_id"]):
        rows.append({"dataset": dataset, "flight_class": int(flight_class), "phase": PHASES[int(phase_id)],
                     "in_calibration": int(flight_class) in cal_classes,
                     "engines": ";".join(str(u) for u in sorted(part.unit.unique())), "rows": int(len(part)),
                     "d_phase_median": float(part.d_phase.median()), "d_phase_p95": float(part.d_phase.quantile(.95)),
                     "d8_phase_median": float(part.d8_phase.median()),
                     "fraction_beyond_support_d_phase": float(part.beyond_phase.mean())})
    return pd.DataFrame(rows), cal_classes


def calibration_phase_effect(dataset, ctx, lock, cal_units):
    """C0: pooled-threshold phase FPR inside calibration engines (no support mismatch)."""
    phase, units = ctx.cal_meta.phase_primary.to_numpy(), ctx.cal_meta.unit.to_numpy()
    rows = []
    for detector, seed in RUNS:
        scores = ctx.cal_scores[(detector, seed)]
        for alpha in TARGETS:
            evaluations = [("in_sample_pooled_tau", mm_entry(lock, detector, seed)[str(alpha)]["tau"]["pooled"],
                            np.ones(len(scores), dtype=bool), "all_calibration")]
            for source in cal_units:
                tau = mm.q_higher(scores[units == source], 1 - alpha)
                for target in cal_units:
                    if target != source:
                        evaluations.append((f"cross_engine_{source}_to_{target}", tau, units == target, str(target)))
            for name, tau, mask, unit in evaluations:
                alarm = scores[mask] > tau
                fpr = [float(alarm[phase[mask] == i].mean()) for i in range(3)]
                rows.append({"dataset": dataset, "detector": detector, "seed": seed, "nominal_fpr": alpha,
                             "evaluation": name, "unit": unit, "overall_fpr": float(alarm.mean()),
                             **{f"{p}_fpr": v for p, v in zip(PHASES, fpr)},
                             **calibration_errors(fpr, float(alarm.mean()), alpha),
                             "highest_phase": PHASES[int(np.argmax(fpr))]})
    return pd.DataFrame(rows)


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.all(x == x[0]) or np.all(y == y[0]):
        return float("nan")
    return float(spearmanr(x, y).statistic)


def association_table(dataset, cells, rates):
    """C4: engine x phase Spearman associations per run and target, with leave-one-engine-out."""
    rows = []
    engine_rates = rates[(rates.unit.astype(str) != "all") & rates.phase.isin(PHASES)].copy()
    engine_rates["unit"] = engine_rates.unit.astype(int)
    for (detector, seed, alpha), part in engine_rates.groupby(["detector", "seed", "nominal_fpr"], sort=False):
        wide = part.pivot_table(index=["unit", "phase"], columns="scheme", values="rate").reset_index()
        merged = cells.merge(wide, on=["unit", "phase"], validate="one_to_one")
        error = {s: np.abs(merged[s].to_numpy() - alpha) for s in SCHEMES}
        signed_c = merged["phase_conditioned"].to_numpy() - alpha
        entry = {"dataset": dataset, "detector": detector, "seed": seed, "nominal_fpr": alpha, "cells": int(len(merged)),
                 "rho_dphase_vs_abs_error_C": spearman(merged.d_phase_median, error["phase_conditioned"]),
                 "rho_dphase_vs_abs_error_Cprime": spearman(merged.d_phase_median, error["causal_regime"]),
                 "rho_dall_vs_abs_error_P": spearman(merged.d_all_median, error["pooled"]),
                 "rho_dphase_vs_change_abs_error_P_to_C": spearman(merged.d_phase_median,
                                                                  error["phase_conditioned"] - error["pooled"]),
                 "rho_dphase_p95_vs_abs_error_C": spearman(merged.d_phase_p95, error["phase_conditioned"]),
                 "rho_d8phase_vs_abs_error_C": spearman(merged.d8_phase_median, error["phase_conditioned"]),
                 "rho_dphase_vs_signed_error_C": spearman(merged.d_phase_median, signed_c)}
        loeo = []
        for unit in sorted(merged.unit.unique()):
            keep = merged.unit.to_numpy() != unit
            loeo.append(spearman(merged.d_phase_median[keep], error["phase_conditioned"][keep]))
            entry[f"loeo_without_{unit}_rho_dphase_vs_abs_error_C"] = loeo[-1]
        entry["loeo_min"] = float(np.nanmin(loeo))
        entry["loeo_max"] = float(np.nanmax(loeo))
        rows.append(entry)
    return pd.DataFrame(rows)


def support_verdict(assoc_by_dataset, cells_by_dataset):
    """Plan section 2.3 C5 verdict from the 1% associations of both datasets."""
    summary, strong, partial, indeterminate = {}, True, False, False
    for dataset, assoc in assoc_by_dataset.items():
        primary = assoc[assoc.nominal_fpr == PRIMARY_TARGET]
        rho = primary.rho_dphase_vs_abs_error_C.to_numpy()
        positive = int(np.sum(rho > 0))
        median = float(np.nanmedian(rho))
        loeo_columns = [c for c in primary.columns if c.startswith("loeo_without_")]
        loeo_medians = {c: float(np.nanmedian(primary[c])) for c in loeo_columns}
        flips = [c for c, v in loeo_medians.items() if np.sign(v) != np.sign(median)]
        cells = cells_by_dataset[dataset]
        class1 = cells[cells.flight_class == 1]
        top = cells.sort_values("d_phase_median", ascending=False).head(len(class1))
        class1_most_distant = bool(len(class1) and (top.flight_class == 1).all())
        summary[dataset] = {"runs": int(len(rho)), "runs_rho_positive": positive, "median_rho": median,
                            "runs_rho_at_least_0.6": int(np.sum(rho >= 0.6)),
                            "loeo_median_rho": loeo_medians, "loeo_sign_flips": flips,
                            "class1_cells_most_distant": class1_most_distant}
        strong &= summary[dataset]["runs_rho_at_least_0.6"] >= 6 and not flips and class1_most_distant
        partial |= positive >= 5 and median >= 0.3
        indeterminate |= bool(flips)
    if indeterminate:
        verdict = "INDETERMINATE DUE TO SMALL ENGINE COUNT"
    elif strong:
        verdict = "SUPPORT-MISMATCH STRONGLY ORGANIZES THE FAILURES"
    elif partial:
        verdict = "PARTIAL EXPLANATION"
    else:
        verdict = "LITTLE EVIDENCE"
    return verdict, summary


def part_c(spec, context, out):
    ctx, lock = context["ctx"], context["lock"]
    data = load_healthy_operating(spec)
    dev_w, dev_meta = data["dev"]
    test_w, test_meta = data["test"]
    cal_mask = dev_meta.unit.isin(spec.cal_units).to_numpy()
    cal_w, cal_meta = dev_w[cal_mask], dev_meta[cal_mask].reset_index(drop=True)
    for mine, theirs in ((cal_meta, ctx.cal_meta), (test_meta, ctx.test_meta)):
        for column in ("unit", "cycle", "phase_primary", "healthy"):
            if not np.array_equal(mine[column].to_numpy(), theirs[column].to_numpy()):
                raise GateError(f"Operating rows do not align with the rescored rows ({column})")
    cal4, cal8 = operating_features(cal_w, cal_meta)
    test4, test8 = operating_features(test_w, test_meta)
    (cal4s, test4s), scale4 = standardize(cal4, test4)
    (cal8s, test8s), scale8 = standardize(cal8, test8)
    cal_phase, test_phase = cal_meta.phase_primary.to_numpy(), test_meta.phase_primary.to_numpy()
    d_phase = phase_distance(cal4s, cal_phase, test4s, test_phase)
    d8_phase = phase_distance(cal8s, cal_phase, test8s, test_phase)
    d_all = nearest_distance(cal4s, test4s)
    reference, threshold = cross_engine_reference(cal4s, cal8s, cal_phase, cal_meta.unit.to_numpy())
    beyond = {"d_phase": d_phase > np.asarray(threshold["d_phase"])[test_phase],
              "d8_phase": d8_phase > np.asarray(threshold["d8_phase"])[test_phase],
              "d_all": d_all > threshold["d_all"]}
    outside = outside_range(cal4s, cal_phase, test4s, test_phase)
    cells, frame = support_cell_table(spec.key, test_meta, d_phase, d_all, d8_phase, beyond, outside)
    classes, cal_classes = class_table(spec.key, frame, cal_meta)
    effect = calibration_phase_effect(spec.key, ctx, lock, spec.cal_units)
    rates = read_frozen_csv(spec.key, "d", "healthy_phase_fpr_by_scheme")
    assoc = association_table(spec.key, cells, rates)
    engines = frame.groupby("unit").agg(flight_class=("flight_class", "first"), rows=("d_phase", "size"),
                                        d_phase_median=("d_phase", "median"),
                                        fraction_beyond_support_d_phase=("beyond_phase", "mean"),
                                        fraction_outside_phase_range=("outside_range", "mean")).reset_index()
    engines.insert(0, "dataset", spec.key)
    tables = {"support_cells": cells, "support_flight_class": classes, "support_reference_calibration": reference,
              "calibration_phase_effect": effect, "support_associations": assoc, "support_engines": engines}
    hashes = {name: mm.write_csv(out / f"{name}.csv", frame_) for name, frame_ in tables.items()}
    return hashes, {"standardization_4d": scale4, "standardization_8d": scale8,
                    "support_reference_threshold_q95": threshold, "calibration_flight_classes": cal_classes,
                    "audit_rows": int(len(test_meta)), "calibration_rows": int(len(cal_meta)),
                    "operating_variables": list(W_NAMES), "dynamic_variables": list(SLOPE_NAMES)}


# ---------------------------------------------------------------------------
# Part D: quantile-regression contextual baseline (healthy side only)
# ---------------------------------------------------------------------------

def quadratic_surface(z):
    """Quadratic response surface of standardized W: 4 linear, 4 square, 6 interaction terms."""
    terms = [z[:, i] for i in range(4)] + [z[:, i] ** 2 for i in range(4)]
    terms += [z[:, i] * z[:, j] for i in range(4) for j in range(i + 1, 4)]
    return np.column_stack(terms)


def fit_quantile_threshold(features, scores, quantile, stride=QR_STRIDE):
    from sklearn.linear_model import QuantileRegressor
    index = np.arange(0, len(scores), stride)
    model = QuantileRegressor(quantile=quantile, alpha=0.0, fit_intercept=True, solver="highs")
    model.fit(features[index], scores[index])
    return model, int(len(index))


def part_d(spec, context, out):
    """Healthy-side evaluation of the continuous baseline; abnormal-side endpoints deferred (R2)."""
    ctx, lock = context["ctx"], context["lock"]
    data = load_healthy_operating(spec)
    dev_w, dev_meta = data["dev"]
    test_w, test_meta = data["test"]
    cal_mask = dev_meta.unit.isin(spec.cal_units).to_numpy()
    cal_w = dev_w[cal_mask]
    (cal_z, test_z), scale = standardize(np.asarray(cal_w[:, :4], np.float64), np.asarray(test_w[:, :4], np.float64))
    cal_x, test_x = quadratic_surface(cal_z), quadratic_surface(test_z)
    cal_starts, cal_ends = mm.flight_bounds(ctx.cal_meta)
    test_phase, units = ctx.test_meta.phase_primary.to_numpy(), ctx.test_meta.unit.to_numpy()
    starts, ends = mm.flight_bounds(ctx.test_meta)
    flight_units = units[starts]
    rate_rows, flag_rows, fits = [], [], []
    for detector, seed in RUNS:
        for alpha in TARGETS:
            clock = time.time()
            model, n_fit = fit_quantile_threshold(cal_x, ctx.cal_scores[(detector, seed)], 1 - alpha)
            cal_alarm = ctx.cal_scores[(detector, seed)] > model.predict(cal_x)
            fraction = mm.flight_alarm_counts(cal_alarm, cal_starts) / (cal_ends - cal_starts)
            kappa = mm.q_higher(fraction, 1 - mm.FLIGHT_FALSE_FLAG_TARGET)
            alarm = ctx.test_scores[(detector, seed)] > model.predict(test_x)
            base = {"dataset": spec.key, "detector": detector, "seed": seed, "nominal_fpr": alpha,
                    "scheme": "quantile_regression_W"}
            rate_rows += [{**base, "arm_status": "post-confirmation continuous contextual baseline (healthy side)", **r}
                          for r in mm.rate_records(alarm, units, test_phase)]
            audit_fraction = mm.flight_alarm_counts(alarm, starts) / (ends - starts)
            for name, mask in mm.unit_groups(flight_units):
                flag_rows.append({**base, "unit": name, "healthy_flights": int(mask.sum()),
                                  "flagged": int((audit_fraction[mask] > kappa).sum()),
                                  "false_flag_rate": float((audit_fraction[mask] > kappa).mean()), "kappa": kappa})
            fits.append({**base, "fit_rows": n_fit, "stride": QR_STRIDE,
                         "calibration_row_alarm_rate": float(cal_alarm.mean()), "kappa": kappa,
                         "coefficients": ";".join(f"{c:.6g}" for c in np.r_[model.intercept_, model.coef_]),
                         "seconds": round(time.time() - clock, 1)})
            print(f"QR baseline: {detector}:{seed} alpha={alpha} ({fits[-1]['seconds']} s)", flush=True)
    rates = pd.DataFrame(rate_rows)
    quality = calibration_quality_table(rates)
    tables = {"baseline_phase_fpr": rates, "baseline_calibration_quality": quality,
              "baseline_flight_false_flags": pd.DataFrame(flag_rows), "baseline_fits": pd.DataFrame(fits)}
    hashes = {name: mm.write_csv(out / f"{name}.csv", frame) for name, frame in tables.items()}
    return hashes, {"standardization": scale, "features": "quadratic response surface of standardized W (14 + intercept)",
                    "fit": f"QuantileRegressor(alpha=0, solver='highs') on every {QR_STRIDE}th calibration row",
                    "abnormal_endpoints": "not evaluated: abnormal-row scores were not retained; a new abnormal-row "
                                          "read needs author approval (plan rule R2)"}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

PARTS = {"A": ("calibration_quality", part_a), "B": ("matched_delay", part_b), "C": ("support_transport", part_c),
         "D": ("contextual_baseline", part_d)}


def run_dataset(spec, parts, output_root=DEFAULT_OUTPUT_ROOT):
    started, clock = mm.now_utc(), time.time()
    plan_digest = verify_plan()
    before = mm.verify_manifest()
    if not before["ok"]:
        raise GateError(f"Baseline manifest failed before execution: {before}")
    context = load_context(spec)
    record = {"dataset": spec.key, "plan_sha256": plan_digest, "parts": {}, "abnormal_rows_read": False,
              "stage_d_count_reproduction": context["stage_d_check"], "mitigation_lock_sha256": context["lock_sha256"],
              "timings": dict(context["ctx"].timings)}
    for part in parts:
        folder, function = PARTS[part]
        out = guard_adversarial_output(Path(output_root) / spec.key / folder)
        part_clock = time.time()
        hashes, details = function(spec, context, out)
        record["parts"][part] = {"folder": mm.rel(out), "outputs_sha256": hashes, "details": details,
                                 "seconds": round(time.time() - part_clock, 1)}
        print(f"Part {part} complete for {spec.key} ({record['parts'][part]['seconds']} s)", flush=True)
    after = mm.verify_manifest()
    if not after["ok"]:
        raise GateError(f"Baseline manifest failed after execution: {after}")
    record.update({"inputs": context["inputs"], "manifest_after": after, "started_utc": started,
                   "finished_utc": mm.now_utc(), "seconds": round(time.time() - clock, 1),
                   "environment": mm.environment_record(), "provenance": module_record()})
    name = "run_record_" + "".join(parts) + ".json"
    mm.write_json(Path(output_root) / spec.key / name, record)
    return record


# ---------------------------------------------------------------------------
# Part R and verdicts (both datasets; derived from Parts A-C outputs and committed tables)
# ---------------------------------------------------------------------------

def classify_direction(fractions):
    """Plan section 3 target-robustness class from the per-target fraction of runs holding."""
    p = {alpha: float(fractions[alpha]) for alpha in TARGETS}
    if p[PRIMARY_TARGET] <= 0.5:
        return "not supported at 1%"
    if all(v == 1.0 for v in p.values()):
        return "invariant"
    if np.mean(list(p.values())) >= 0.8 and all(v > 0.5 for v in p.values()):
        return "mostly invariant"
    if any(v < 0.5 for v in p.values()):
        return "reversed"
    return "target-sensitive"


def load_part(output_root, dataset, folder, table):
    return pd.read_csv(Path(output_root) / dataset / folder / f"{table}.csv", float_precision="round_trip")


def claim_frames(output_root, dataset):
    """Per run x target truth values of each robustness claim (definitions fixed before execution)."""
    paired = load_part(output_root, dataset, "calibration_quality", "calibration_quality_paired")
    quality = load_part(output_root, dataset, "calibration_quality", "calibration_quality_metrics")
    labels = load_part(output_root, dataset, "matched_delay", "matched_labels")
    locked = load_part(output_root, dataset, "matched_delay", "locked_operating_points")
    rates = read_frozen_csv(dataset, "e", "abnormal_alarm_rates")
    pooled = paired[paired.weighting == "row_pooled"]
    claims = []

    def add(claim, frame, holds):
        for row, value in zip(frame.itertuples(index=False), holds):
            claims.append({"dataset": dataset, "claim": claim, "detector": row.detector, "seed": row.seed,
                           "nominal_fpr": row.nominal_fpr, "holds": bool(value)})

    p_all = quality[(quality.scheme == "pooled") & (quality.unit == "all")]
    add("R1 descent is the highest pooled healthy-FPR phase (P)", p_all,
        (p_all.descent_fpr > p_all[["climb_fpr", "cruise_fpr"]].max(axis=1)).to_numpy())
    for arm, tag in (("phase_conditioned", "C"), ("causal_regime", "C'")):
        part = pooled[pooled.arm == arm]
        add(f"R2 {tag} reduces between-phase disparity (A1)", part, (part.diff_spread < 0).to_numpy())
        add(f"R3 {tag} reduces max-abs nominal calibration error (A2)", part, (part.diff_max_abs_error < 0).to_numpy())
        add(f"R4 {tag} reduces RMS nominal calibration error (A3)", part, (part.diff_rms_error < 0).to_numpy())
        add(f"R5 {tag} mainly redistributes: |overall FPR change| < 0.5 x |A1 change|", part,
            (np.abs(part.diff_overall_fpr) < 0.5 * np.abs(part.diff_spread)).to_numpy())
        overall = rates[(rates.window == "all_post_onset") & (rates.unit.astype(str) == "all") & (rates.phase == "overall")]
        wide = overall.pivot_table(index=["detector", "seed", "nominal_fpr"], columns="scheme", values="rate").reset_index()
        add(f"R6 {tag} abnormal-state row alarm-rate ratio >= 0.9", wide, (wide[arm] / wide["pooled"] >= 0.9).to_numpy())
        lab = labels[labels.arm == arm]
        add(f"R8 {tag} is not earlier than P at matched false-flag burden", lab,
            (lab.matched_label != "earlier at matched burden").to_numpy())
    for scheme, tag in (("pooled", "P"), ("phase_conditioned", "C"), ("causal_regime", "C'")):
        part = locked[locked.scheme == scheme]
        add(f"R7 realized pooled healthy-flight FFR exceeds nominal 5% ({tag})", part, (part.ffr > 0.05).to_numpy())
    return pd.DataFrame(claims)


def robustness_table(claims):
    rows = []
    for (dataset, claim), part in claims.groupby(["dataset", "claim"], sort=False):
        fractions = part.groupby("nominal_fpr").holds.mean()
        rows.append({"dataset": dataset, "claim": claim,
                     **{f"runs_holding_alpha_{a}": f"{int(part[part.nominal_fpr == a].holds.sum())}/"
                                                   f"{int((part.nominal_fpr == a).sum())}" for a in TARGETS},
                     "classification": classify_direction(fractions)})
    return pd.DataFrame(rows)


def denominator_audit(output_root, dataset):
    paired = load_part(output_root, dataset, "calibration_quality", "calibration_quality_paired")
    rows = []
    for metric in ("diff_spread", "diff_max_abs_error", "diff_rms_error"):
        pooled = paired[paired.weighting == "row_pooled"].set_index(KEYS + ["arm"])[metric]
        equal = paired[paired.weighting == "equal_engine"].set_index(KEYS + ["arm"])[metric]
        joined = pd.concat([pooled.rename("row_pooled"), equal.rename("equal_engine")], axis=1).dropna()
        agree = np.sign(joined.row_pooled) == np.sign(joined.equal_engine)
        rows.append({"dataset": dataset, "check": f"row-pooled vs equal-engine sign of {metric}",
                     "agreeing": int(agree.sum()), "compared": int(len(joined)),
                     "disagreements": ";".join(f"{k[1]}:{k[2]}@{k[3]}/{k[4]}" for k in joined.index[~agree.to_numpy()])})
    traj = read_frozen_csv(dataset, "e", "flight_alarm_fraction_trajectories")
    healthy = traj[traj.state == "healthy"]
    flight_mean = healthy.groupby(["detector", "seed", "nominal_fpr", "scheme"]).alarm_fraction.mean()
    quality = load_part(output_root, dataset, "calibration_quality", "calibration_quality_metrics")
    row_pooled = quality[quality.unit == "all"].set_index(["detector", "seed", "nominal_fpr", "scheme"]).overall_fpr
    for arm in ALTERNATIVES:
        f_diff = flight_mean.xs(arm, level="scheme") - flight_mean.xs("pooled", level="scheme")
        r_diff = row_pooled.xs(arm, level="scheme") - row_pooled.xs("pooled", level="scheme")
        joined = pd.concat([f_diff.rename("flight"), r_diff.rename("row")], axis=1)
        agree = np.sign(joined.flight) == np.sign(joined.row)
        rows.append({"dataset": dataset, "check": f"equal-flight vs row-pooled sign of overall healthy FPR change ({arm})",
                     "agreeing": int(agree.sum()), "compared": int(len(joined)),
                     "disagreements": ";".join(f"{k[0]}:{k[1]}@{k[2]}" for k in joined.index[~agree.to_numpy()])})
    burden = read_frozen_csv(dataset, "d", "healthy_flight_burden_by_scheme")
    burden = burden[(burden.unit.astype(str) == "all") & (burden.phase == "overall")].set_index(
        ["detector", "seed", "nominal_fpr", "scheme"]).fraction_flights_with_alarm
    flags = read_frozen_csv(dataset, "e", "healthy_flight_false_flags_with_delay")
    flags = flags[flags.unit.astype(str) == "all"].set_index(["detector", "seed", "nominal_fpr", "scheme"]).false_flag_rate
    for arm in ALTERNATIVES:
        any_diff = burden.xs(arm, level="scheme") - burden.xs("pooled", level="scheme")
        kappa_diff = flags.xs(arm, level="scheme") - flags.xs("pooled", level="scheme")
        joined = pd.concat([any_diff.rename("any_alarm"), kappa_diff.rename("kappa_ffr")], axis=1)
        agree = np.sign(joined.any_alarm) == np.sign(joined.kappa_ffr)
        rows.append({"dataset": dataset, "check": f"'healthy flights with any alarm' vs kappa FFR sign of change ({arm})",
                     "agreeing": int(agree.sum()), "compared": int(len(joined)),
                     "disagreements": ";".join(f"{k[0]}:{k[1]}@{k[2]}" for k in joined.index[~agree.to_numpy()]),
                     "any_alarm_range": f"{burden.min():.3f}-{burden.max():.3f}"})
    rates = read_frozen_csv(dataset, "e", "abnormal_alarm_rates")
    overall = rates[(rates.window == "all_post_onset") & (rates.unit.astype(str) == "all") & (rates.phase == "overall")]
    wide = overall.pivot_table(index=["detector", "seed", "nominal_fpr"], columns="scheme", values="rate")
    locked = load_part(output_root, dataset, "matched_delay", "locked_operating_points").set_index(
        ["detector", "seed", "nominal_fpr", "scheme"]).median_delay
    for arm in ALTERNATIVES:
        row_more = wide[arm] > wide["pooled"]
        earlier = (locked.xs(arm, level="scheme") < locked.xs("pooled", level="scheme")).reindex(row_more.index)
        agree = row_more == earlier
        rows.append({"dataset": dataset, "check": f"row abnormal alarm rate higher vs flight delay earlier ({arm})",
                     "agreeing": int(agree.sum()), "compared": int(len(agree)),
                     "disagreements": ";".join(f"{k[0]}:{k[1]}@{k[2]}" for k in agree.index[~agree.to_numpy()])})
    return pd.DataFrame(rows)


def seed_consistency(output_root, dataset):
    paired = load_part(output_root, dataset, "calibration_quality", "calibration_quality_paired")
    labels = load_part(output_root, dataset, "matched_delay", "matched_labels")
    rows = []
    pooled = paired[paired.weighting == "row_pooled"]
    for family in ("isolation_forest", "lstm_autoencoder"):
        for arm in ALTERNATIVES:
            for alpha in TARGETS:
                part = pooled[(pooled.detector == family) & (pooled.arm == arm) & (pooled.nominal_fpr == alpha)]
                entry = {"dataset": dataset, "family": family, "arm": arm, "nominal_fpr": alpha}
                for metric in ("diff_spread", "diff_max_abs_error", "diff_rms_error"):
                    mean_sign = np.sign(part[metric].mean())
                    entry[f"{metric}_seeds_agreeing_with_family_mean"] = f"{int((np.sign(part[metric]) == mean_sign).sum())}/{len(part)}"
                lab = labels[(labels.detector == family) & (labels.arm == arm) & (labels.nominal_fpr == alpha)]
                entry["matched_labels_by_seed"] = ";".join(f"{int(r.seed)}:{r.matched_label}" for r in lab.itertuples())
                rows.append(entry)
    return pd.DataFrame(rows)


def summarize(output_root=DEFAULT_OUTPUT_ROOT, datasets=("ds02", "ds03")):
    """Robustness, denominators, verdicts, and the D decision across both datasets."""
    out = guard_adversarial_output(Path(output_root) / "summary")
    claims = pd.concat([claim_frames(output_root, d) for d in datasets], ignore_index=True)
    robust = robustness_table(claims)
    denominators = pd.concat([denominator_audit(output_root, d) for d in datasets], ignore_index=True)
    seeds = pd.concat([seed_consistency(output_root, d) for d in datasets], ignore_index=True)
    paired = pd.concat([load_part(output_root, d, "calibration_quality", "calibration_quality_paired") for d in datasets],
                       ignore_index=True)
    wording = wording_verdicts(paired)
    labels = pd.concat([load_part(output_root, d, "matched_delay", "matched_labels") for d in datasets], ignore_index=True)
    label_counts = labels.groupby(["dataset", "nominal_fpr", "arm", "matched_label"]).size().rename("runs").reset_index()
    assoc = {d: load_part(output_root, d, "support_transport", "support_associations") for d in datasets}
    cells = {d: load_part(output_root, d, "support_transport", "support_cells") for d in datasets}
    verdict, support_summary = support_verdict(assoc, cells)
    primary = paired[(paired.weighting == "row_pooled") & (paired.arm == "phase_conditioned")
                     & (paired.nominal_fpr == PRIMARY_TARGET)]
    d_counts = primary.groupby("dataset").apply(lambda g: int((g.diff_spread < 0).sum()), include_groups=False)
    run_d = bool((d_counts >= 5).all())
    tables = {"claim_truth_values": claims, "robustness_classification": robust,
              "denominator_audit": denominators, "seed_consistency": seeds,
              "calibration_wording_verdicts": wording, "matched_label_counts": label_counts}
    hashes = {name: mm.write_csv(out / f"{name}.csv", frame) for name, frame in tables.items()}
    record = {"support_verdict": verdict, "support_summary": support_summary,
              "d_decision": {"C_spread_reduced_runs_at_1pct": {k: int(v) for k, v in d_counts.items()},
                             "run_contextual_baseline": run_d,
                             "rule": "C reduces A1 in >= 5 of 7 runs in every dataset at 1%"},
              "outputs_sha256": hashes, "finished_utc": mm.now_utc(), "provenance": module_record()}
    mm.write_json(out / "summary_record.json", record)
    return record


# ---------------------------------------------------------------------------
# Post-plan descriptive addition (deviation Dev-1, recorded in FINAL_ADVERSARIAL_REVIEW.md)
# ---------------------------------------------------------------------------

def error_decomposition(values, alpha):
    """Mean squared nominal error of an engine x phase grid = bias^2 + phase + engine + interaction.

    `values` is an (engines x phases) array of FPRs; each cell has equal weight, so this is
    an equal-engine, equal-phase description (not the row-pooled estimand).
    """
    y = np.asarray(values, dtype=np.float64) - alpha
    n_e, n_p = y.shape
    grand = y.mean()
    phase_means, engine_means = y.mean(axis=0), y.mean(axis=1)
    phase = n_e * np.sum((phase_means - grand) ** 2) / y.size
    engine = n_p * np.sum((engine_means - grand) ** 2) / y.size
    total_var = np.sum((y - grand) ** 2) / y.size
    interaction = total_var - phase - engine
    mse = float(np.mean(y * y))
    return {"mse": mse, "bias_sq": float(grand ** 2), "phase": float(phase), "engine": float(engine),
            "interaction": float(interaction)}


def decomposition_table(datasets=("ds02", "ds03")):
    rows = []
    for dataset in datasets:
        rates = read_frozen_csv(dataset, "d", "healthy_phase_fpr_by_scheme")
        cells = rates[(rates.unit.astype(str) != "all") & rates.phase.isin(PHASES)]
        for (detector, seed, alpha, scheme), part in cells.groupby(
                ["detector", "seed", "nominal_fpr", "scheme"], sort=False):
            grid = part.pivot_table(index="unit", columns="phase", values="rate")[list(PHASES)].to_numpy()
            parts = error_decomposition(grid, alpha)
            rows.append({"dataset": dataset, "detector": detector, "seed": seed, "nominal_fpr": alpha,
                         "scheme": scheme, "engines": grid.shape[0], **parts,
                         **{f"share_{k}": parts[k] / parts["mse"] for k in ("bias_sq", "phase", "engine", "interaction")}})
    return pd.DataFrame(rows)


def write_decomposition(output_root=DEFAULT_OUTPUT_ROOT, datasets=("ds02", "ds03")):
    out = guard_adversarial_output(Path(output_root) / "summary")
    table = decomposition_table(datasets)
    digest = mm.write_csv(out / "post_plan_error_decomposition.csv", table)
    return table, digest
