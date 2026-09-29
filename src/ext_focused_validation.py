"""Final focused validation (post hoc): docs/extension/FOCUSED_VALIDATION_PLAN.md (FROZEN v1.0).

Reads only healthy (hs = 1) official-test rows of the seven new subsets, in reproduction-only mode, with the
saved locked models (nothing is fitted), and writes only under results/extension/focused_validation/.
No pre-specified decision, lock or committed output changes. Components:
1. engine-specific sampling-noise floor: repeated 5-fold cross-fit over each audit engine's own healthy flights;
2. calibration-class-preserving U-EXT1 bootstrap (identical audit plans) and U-EXT2 recomputed from it;
3. per-engine local recalibration with K = 5 initial healthy flights and a K-matched noise reference.
Gates G1-G6 of the plan must pass; any failure raises ExtensionError (stop rule).
"""

from __future__ import annotations

import json
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import ext_calibration as xc
import ext_common as ec
import ext_endpoints as xe
import ext_models as xm
import ext_pipeline as xp
import ext_summary as xs
import final_validation as fv
import mssp_adversarial as ma
import mssp_mitigation as mm

PLAN = ec.DOCS / "FOCUSED_VALIDATION_PLAN.md"
PLAN_SHA256 = "f734cdf6b5b0ccd85a3d55c6a1774d66d7bccefcee53ced3865f5ba9807f7795"
CODE_FILES = ("src/ext_focused_validation.py", "scripts/run_focused_validation.py")
ALPHA = 0.01
FOLDS, R_CROSSFIT, K_LOCAL, R_LOCAL = 5, 200, 5, 200
SEED_CROSSFIT, SEED_CLASS_BOOT, SEED_LOCAL = 20261004, 20261003, 20261005
ARMS = ("pooled", "phase_conditioned", "quantile_regression_W")
LOCAL_ARMS = ("pooled", "phase_conditioned")
PHASE_NAMES = ("climb", "cruise", "descent")
REPLICATE_COLUMNS = ("pooled.ME_A2", "phase_conditioned.ME_A2", "pooled.pooled_A1", "pooled.pooled_A2", "diff_pooled_A1",
                     "diff_pooled_A2", "diff_ME_A2", "diff_WE_A2", "pooled.WE_A2")
WIDTH_METRICS = ("diff_pooled_A1", "diff_pooled_A2", "diff_ME_A2", "diff_WE_A2", "pooled.ME_A2",
                 "phase_conditioned.ME_A2", "pooled.WE_A2", "phase_conditioned.WE_A2")
RESIDUAL_MAJORITY, CVAE_MAJORITY = 4, 2


# ---------------------------------------------------------------------------
# Engine-level machinery (pure functions; unit-tested on synthetic data)
# ---------------------------------------------------------------------------

class EngineData:
    """One audit engine's healthy rows for one run: per-phase sorted views and a (flight, phase) cell counter."""

    def __init__(self, scores, phase, flight):
        self.scores = np.asarray(scores, dtype=np.float64)
        self.phase = np.asarray(phase, dtype=np.int64)
        self.flight = np.asarray(flight, dtype=np.int64)
        self.n_flights = int(self.flight.max()) + 1
        self.views = []
        for p in range(3):
            mask = self.phase == p
            order = np.argsort(self.scores[mask], kind="quicksort")
            self.views.append((self.scores[mask][order], self.flight[mask][order].astype(np.int16)))
        order = np.argsort(self.scores, kind="quicksort")
        self.pooled_view = (self.scores[order], self.flight[order].astype(np.int16))
        self.counter = mm.CellCounter(self.scores, self.flight * 3 + self.phase, self.n_flights * 3)
        self.sizes = self.counter.sizes.reshape(-1, 3)

    def phase_taus(self, multiplicity, q=1 - ALPHA):
        """Per-phase upper quantiles ('higher') over the flights with multiplicity 1."""
        return np.asarray([fv.weighted_higher_quantile(v, ids, multiplicity, q) for v, ids in self.views])

    def pooled_tau(self, multiplicity, q=1 - ALPHA):
        return fv.weighted_higher_quantile(*self.pooled_view, multiplicity, q)

    def cell_alarms(self, cell_thresholds):
        return self.counter.above(cell_thresholds).reshape(-1, 3)

    def a2(self, alarms, flight_mask):
        fpr = alarms[flight_mask].sum(axis=0) / self.sizes[flight_mask].sum(axis=0)
        return float(np.abs(fpr - ALPHA).max()), fpr

    def fixed_a2(self, phase_thresholds, flight_mask):
        return self.a2(self.cell_alarms(np.tile(np.asarray(phase_thresholds, dtype=np.float64), self.n_flights)),
                       flight_mask)


def crossfit_draws(engine, rng, repetitions=R_CROSSFIT, folds=FOLDS):
    """Component 1: out-of-fold A2 of per-phase self-calibration, one value per random fold assignment."""
    all_flights = np.ones(engine.n_flights, dtype=bool)
    out = np.empty(repetitions)
    for r in range(repetitions):
        thresholds = np.empty(engine.n_flights * 3)
        for fold in np.array_split(rng.permutation(engine.n_flights), folds):
            train = np.ones(engine.n_flights, dtype=np.int64)
            train[fold] = 0
            taus = engine.phase_taus(train)
            for p in range(3):
                thresholds[fold * 3 + p] = taus[p]
        out[r] = engine.a2(engine.cell_alarms(thresholds), all_flights)[0]
    return out


def local_recalibration(engine, fleet_taus, k=K_LOCAL):
    """Component 3: thresholds from the first k healthy flights, evaluated on the engine's remaining flights."""
    train = np.zeros(engine.n_flights, dtype=np.int64)
    train[:k] = 1
    evaluation = train == 0
    local = {"pooled": np.full(3, engine.pooled_tau(train)), "phase_conditioned": engine.phase_taus(train)}
    out = {}
    for arm in LOCAL_ARMS:
        out[f"local_A2|{arm}"], out[f"local_fpr|{arm}"] = engine.fixed_a2(local[arm], evaluation)
        out[f"fleet_eval_A2|{arm}"], out[f"fleet_eval_fpr|{arm}"] = engine.fixed_a2(fleet_taus[arm], evaluation)
    out["eval_flights"] = int(evaluation.sum())
    return out


def k_matched_draws(engine, rng, repetitions=R_LOCAL, k=K_LOCAL):
    """Component 3 reference: per-phase thresholds from k random flights, A2 on the engine's other flights."""
    out = np.empty(repetitions)
    for r in range(repetitions):
        train = np.zeros(engine.n_flights, dtype=np.int64)
        train[rng.choice(engine.n_flights, size=k, replace=False)] = 1
        out[r] = engine.fixed_a2(engine.phase_taus(train), train == 0)[0]
    return out


def class_preserving_plans(meta, classes, repetitions, rng):
    """Component 2: engine -> flight plans that keep every calibration class in every replicate."""
    flights = fv.flight_index(meta)
    engine_to_flights = {}
    for index, (unit, _, _) in enumerate(flights):
        engine_to_flights.setdefault(int(unit), []).append(index)
    by_class = {}
    for unit in sorted(engine_to_flights):
        by_class.setdefault(int(classes[str(unit)]), []).append(unit)
    plans = np.zeros((repetitions, len(flights)), dtype=np.int16)
    for b in range(repetitions):
        for cls in sorted(by_class):
            engines = np.asarray(by_class[cls])
            for engine in rng.choice(engines, size=len(engines), replace=True):
                members = np.asarray(engine_to_flights[int(engine)])
                np.add.at(plans[b], rng.choice(members, size=len(members), replace=True), 1)
    return flights, plans


def output_root():
    return ec.RESULTS / "focused_validation"  # resolved at call time


def majority_exceeds(flags, residual=True):
    return int(np.sum(flags)) >= (RESIDUAL_MAJORITY if residual else CVAE_MAJORITY)


# ---------------------------------------------------------------------------
# Workers (spawn pools; never fork a CUDA process)
# ---------------------------------------------------------------------------

def _engine_worker(task):
    (subset_index, run_index, name, unit, scores, phase, flight, fleet_taus) = task
    engine = EngineData(scores, phase, flight)
    all_flights = np.ones(engine.n_flights, dtype=bool)
    observed = {arm: engine.fixed_a2(fleet_taus[arm], all_flights) for arm in LOCAL_ARMS}
    draws = crossfit_draws(engine, np.random.default_rng([SEED_CROSSFIT, subset_index, run_index, unit]))
    local = local_recalibration(engine, fleet_taus)
    k_draws = k_matched_draws(engine, np.random.default_rng([SEED_LOCAL, subset_index, run_index, unit]))
    return {"name": name, "unit": unit, "n_flights": engine.n_flights, "observed": observed, "draws": draws,
            "local": local, "k_draws": k_draws}


def _bootstrap_worker(args):
    (name, cal_scores, cal_phase, cal_flights, test_scores, test_phase, test_flights, designs, test_plans,
     flight_engine, n_engines, engine_times_all) = args
    run = xe.BootstrapRun(cal_scores, cal_phase, cal_flights, test_scores, test_phase, test_flights)
    ones_cal = np.ones(len(cal_flights), dtype=np.int64)
    ones_test = np.ones(len(test_flights), dtype=np.int64)
    point = run.replicate(ones_cal, ones_test, ALPHA, flight_engine, n_engines, np.ones(n_engines))
    results = {}
    for design, cal_plans in designs.items():
        results[design] = [run.replicate(cal_plans[b], test_plans[b], ALPHA, flight_engine, n_engines,
                                         engine_times_all[b]) for b in range(len(cal_plans))]
    return name, point, results


def _pool(workers):
    return ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------

def gate_plan_and_code():
    """G2: plan hash and clean, tracked plan and code."""
    if ec.file_digest(PLAN) != PLAN_SHA256:
        raise ec.ExtensionError("Focused validation plan hash differs from the frozen value (stop rule)")
    for path in (PLAN,) + tuple(ec.ROOT / f for f in CODE_FILES):
        if not ec.git_tracked_and_clean(path):
            raise ec.ExtensionError(f"{path.relative_to(ec.ROOT)} is not committed and clean (stop rule)")


def gate_healthy_counts(key, lock, scores_h, meta_h, q_values):
    """G4: locked thresholds on the rescored healthy rows reproduce the committed phase and flight counts."""
    committed = pd.read_csv(ec.RESULTS / key / "audit" / "phase_fpr.csv")
    committed = committed[(committed.unit != "all") & committed.phase.isin(PHASE_NAMES)].copy()
    committed["unit"] = committed.unit.astype(int)
    trajectories = pd.read_csv(ec.RESULTS / key / "audit" / "flight_trajectories.csv")
    trajectories = trajectories[(trajectories.rule == "R0") & (trajectories.state == "healthy")]
    phase = meta_h.phase_primary.to_numpy()
    unit = meta_h.unit.to_numpy()
    flights = xe.audit_flights(meta_h)
    starts = flights.start.to_numpy()
    checked = 0
    for name, scores in scores_h.items():
        run = ec.run_name(*name)
        for alpha in ec.TARGETS:
            taus = lock["runs"][run][str(alpha)]["tau"]
            for arm in ARMS:
                alarm = scores > xc.row_thresholds(arm, taus, phase, q_values.get((name, alpha)))
                ours = pd.DataFrame({"unit": unit, "phase": np.asarray(PHASE_NAMES)[phase], "alarm": alarm})
                ours = ours.groupby(["unit", "phase"]).alarm.agg(["size", "sum"]).reset_index()
                ref = committed[(committed.detector == name[0]) & (committed.seed == name[1])
                                & (committed.nominal_fpr == alpha) & (committed.arm == arm)]
                merged = ours.merge(ref, on=["unit", "phase"], how="outer")
                if len(merged) != len(ref) or not ((merged["size"] == merged.n) & (merged["sum"] == merged.alarms)).all():
                    raise ec.ExtensionError(f"{key}: G4 phase counts not reproduced for {run} {alpha} {arm} (stop rule)")
                counts = np.add.reduceat(alarm.astype(np.int64), starts)
                frozen = trajectories[(trajectories.detector == name[0]) & (trajectories.seed == name[1])
                                      & (trajectories.nominal_fpr == alpha) & (trajectories.arm == arm)]
                frozen = frozen.sort_values(["unit", "cycle"])
                ours_f = flights.assign(alarms=counts).sort_values(["unit", "cycle"])
                if not (np.array_equal(frozen.unit.to_numpy(), ours_f.unit.to_numpy())
                        and np.array_equal(frozen.cycle.to_numpy(), ours_f.cycle.to_numpy())
                        and np.array_equal(frozen.alarms.to_numpy(), ours_f.alarms.to_numpy())):
                    raise ec.ExtensionError(f"{key}: G4 flight counts not reproduced for {run} {alpha} {arm} (stop rule)")
                checked += 1
    return checked


def gate_original_replicates(key, records_by_run):
    """G5: the original U-EXT1 design reproduces the committed alpha = 1% replicate table exactly."""
    committed = pd.read_csv(ec.RESULTS / key / "audit" / "bootstrap_uext1_replicates_alpha_0.01.csv",
                            float_precision="round_trip")
    for name, records in records_by_run.items():
        ref = committed[(committed.detector == name[0]) & (committed.seed == name[1])].sort_values("replicate")
        if len(ref) != len(records):
            raise ec.ExtensionError(f"{key}: G5 replicate count differs for {ec.run_name(*name)} (stop rule)")
        for column in REPLICATE_COLUMNS:
            ours = np.asarray([r[column] for r in records], dtype=np.float64)
            if not np.array_equal(ours, ref[column].to_numpy(dtype=np.float64)):
                raise ec.ExtensionError(f"{key}: G5 replicates differ for {ec.run_name(*name)} {column} (stop rule)")
    return len(records_by_run)


# ---------------------------------------------------------------------------
# Per-subset run
# ---------------------------------------------------------------------------

def run_subset(key, log=print, workers=10, command="python scripts/run_focused_validation.py subset"):
    ec.verify_baseline()                                                          # G1
    gate_plan_and_code()                                                          # G2
    subset = ec.load_registry()[key]
    if subset.reference or key not in ec.NEW_ORDER:
        raise ec.ExtensionError("The focused validation covers the seven new subsets only")
    s_index = list(ec.NEW_ORDER).index(key)
    out_dir = output_root() / key
    if (out_dir / "validation_record.json").exists():
        raise ec.ExtensionError(f"{key}: focused validation already ran (outputs exist)")
    lock_path, record_path = subset.out / "lock" / "calibration_lock.json", subset.out / "lock" / "lock_record.json"
    if not (ec.git_tracked_and_clean(lock_path) and ec.git_tracked_and_clean(record_path)):
        raise ec.ExtensionError(f"{key}: the lock is not committed and clean (stop rule)")
    lock_sha = ec.file_digest(lock_path)
    if lock_sha != json.loads(record_path.read_text(encoding="utf-8"))["lock_sha256"]:
        raise ec.ExtensionError(f"{key}: lock hash differs from its record (stop rule)")
    if not (subset.out / "audit" / "official_test_opened.json").exists():
        raise ec.ExtensionError(f"{key}: the official audit has not run")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    started, clock = ec.now_utc(), time.time()
    ec.verify_input(subset)
    fv.configure_cuda_runtime()
    models, cal, cal_scores, _ = xp.verify_calibration(subset, lock, subset.out / "models")   # G3
    ec.append_access_log(key, "Focused validation: official-test healthy rows re-read (reproduction only)",
                         f"hs = 1 rows of audit engines {list(subset.audit)}; no abnormal row; plan "
                         f"{PLAN_SHA256[:12]}", lock_sha=lock_sha[:12], command=command)
    audit = xm.load_audit_rows(subset, healthy_only=True)
    if not (audit.meta.healthy.to_numpy() == 1).all():
        raise ec.ExtensionError(f"{key}: a non-healthy row was loaded (stop rule)")
    meta_h = audit.meta.reset_index(drop=True)
    scores_h = xm.score_all(models, audit)
    features = xc.q_features(audit.w, lock["q_scale"])
    q_values = {(name, alpha): xc.predict_q(features, lock["runs"][ec.run_name(*name)][str(alpha)]["q_fit"])
                for name in scores_h for alpha in ec.TARGETS}
    g4 = gate_healthy_counts(key, lock, scores_h, meta_h, q_values)             # G4
    log(f"{key}: G1-G4 passed ({g4} run x target x arm count checks); {len(meta_h)} healthy audit rows")

    classes = lock["roles"]["classes"]
    cal_classes = {classes[str(u)] for u in lock["roles"]["calibration"]}
    unit = meta_h.unit.to_numpy()
    phase = meta_h.phase_primary.to_numpy()
    tasks = []
    for r_index, (name, scores) in enumerate(scores_h.items()):
        taus = lock["runs"][ec.run_name(*name)][str(ALPHA)]["tau"]
        fleet = {"pooled": np.full(3, taus["pooled"]), "phase_conditioned": np.asarray(taus["phase_conditioned"])}
        for e in sorted(set(int(u) for u in unit)):
            mask = unit == e
            cycles = meta_h.cycle.to_numpy()[mask]
            _, flight = np.unique(cycles, return_inverse=True)   # chronological flight index within the engine
            tasks.append((s_index, r_index, name, e, scores[mask], phase[mask], flight, fleet))
    clock_c = time.time()
    with _pool(workers) as pool:
        engine_results = list(pool.map(_engine_worker, tasks))
    log(f"{key}: components 1 and 3 in {time.time() - clock_c:.0f} s ({len(tasks)} engine-runs)")

    noise_rows, draw_rows, local_rows = [], [], []
    for res in engine_results:
        name, e = res["name"], res["unit"]
        base = {"subset": key, "family": ec.FAMILIES[key], "detector": name[0], "seed": name[1], "unit": e,
                "flight_class": int(classes[str(e)]), "class_in_calibration": classes[str(e)] in cal_classes,
                "healthy_flights": res["n_flights"]}
        nf50, nf95 = float(np.median(res["draws"])), float(np.quantile(res["draws"], 0.95))
        mask = unit == e
        observed = {arm: res["observed"][arm][0] for arm in LOCAL_ARMS}
        q_alarm = scores_h[name][mask] > q_values[(name, ALPHA)][mask]
        q_fpr = np.bincount(phase[mask], weights=q_alarm.astype(np.float64), minlength=3) / np.bincount(phase[mask], minlength=3)
        observed["quantile_regression_W"] = float(np.abs(q_fpr - ALPHA).max())
        for arm in ARMS:
            noise_rows.append({**base, "arm": arm, "observed_A2": observed[arm], "NF50": nf50, "NF95": nf95,
                               "exceeds_NF95": observed[arm] > nf95, "ratio_to_NF50": observed[arm] / nf50,
                               "excess_over_NF95": observed[arm] - nf95})
        for scheme, values in (("crossfit_5fold", res["draws"]), (f"k_matched_K{K_LOCAL}", res["k_draws"])):
            draw_rows.extend({"subset": key, "detector": name[0], "seed": name[1], "unit": e, "scheme": scheme,
                              "draw": i, "A2": float(v)} for i, v in enumerate(values))
        nfk50, nfk95 = float(np.median(res["k_draws"])), float(np.quantile(res["k_draws"], 0.95))
        for arm in LOCAL_ARMS:
            local, fleet = res["local"][f"local_A2|{arm}"], res["local"][f"fleet_eval_A2|{arm}"]
            local_rows.append({**base, "arm": arm, "K": K_LOCAL, "eval_flights": res["local"]["eval_flights"],
                               "fleet_eval_A2": fleet, "local_A2": local, "improvement": fleet - local,
                               "NFK50": nfk50, "NFK95": nfk95, "local_within_NFK95": local <= nfk95,
                               "fleet_within_NFK95": fleet <= nfk95, "NF95": nf95, "local_within_NF95": local <= nf95,
                               **{f"local_{p}_fpr": float(v) for p, v in zip(PHASE_NAMES, res["local"][f"local_fpr|{arm}"])}})

    # Component 2: original (G5) and class-preserving bootstraps, identical audit plans
    clock_b = time.time()
    cal_meta = cal.meta.reset_index(drop=True)
    rng = np.random.default_rng(ec.UEXT1_SEED)
    cal_flights, original_plans = fv.bootstrap_plans(cal_meta, ec.BOOTSTRAP_REPLICATES, rng)
    test_flights, test_plans = fv.bootstrap_plans(meta_h, ec.BOOTSTRAP_REPLICATES, rng)
    cp_flights, cp_plans = class_preserving_plans(cal_meta, classes, ec.BOOTSTRAP_REPLICATES,
                                                  np.random.default_rng([SEED_CLASS_BOOT, s_index]))
    if [f[:2] for f in cp_flights] != [f[:2] for f in cal_flights]:
        raise ec.ExtensionError(f"{key}: calibration flight indexing differs between designs")
    omitted = sum(len({classes[str(cal_flights[i][0])] for i in np.flatnonzero(plan)}) < len(cal_classes)
                  for plan in cp_plans)
    if omitted:
        raise ec.ExtensionError(f"{key}: a class-preserving replicate omits a calibration class")
    original_omits = int(sum(len({classes[str(cal_flights[i][0])] for i in np.flatnonzero(plan)}) < len(cal_classes)
                             for plan in original_plans))
    ones = np.ones(len(test_flights), dtype=np.int64)
    _, flight_engine = ma.engine_weights(test_flights, ones)
    n_engines = int(flight_engine.max()) + 1
    engine_times_all = [ma.engine_weights(test_flights, test_plans[b])[0] for b in range(ec.BOOTSTRAP_REPLICATES)]
    cal_phase = cal_meta.phase_primary.to_numpy()
    args = [(name, cal_scores[name], cal_phase, cal_flights, scores_h[name], phase, test_flights,
             {"original": original_plans, "class_preserving": cp_plans}, test_plans, flight_engine, n_engines,
             engine_times_all) for name in cal_scores]
    with _pool(workers) as pool:
        boot = list(pool.map(_bootstrap_worker, args))
    g5 = gate_original_replicates(key, {name: results["original"] for name, _, results in boot})   # G5
    ci_rows, cp_replicates = [], []
    committed_ci = pd.read_csv(ec.RESULTS / key / "audit" / "bootstrap_uext1_ci.csv", float_precision="round_trip")
    for name, point, results in boot:
        for design, records in results.items():
            for row in mm.summarize_replicates(records):
                width = row["ci_upper_95"] - row["ci_lower_95"]
                ci_rows.append({"subset": key, "family": ec.FAMILIES[key], "detector": name[0], "seed": name[1],
                                "design": design, "metric": row["metric"], "point_estimate": point[row["metric"]],
                                "ci_lower_95": row["ci_lower_95"], "ci_upper_95": row["ci_upper_95"], "width": width,
                                "includes_zero": row["ci_lower_95"] <= 0 <= row["ci_upper_95"]})
                if design == "original":
                    ref = committed_ci[(committed_ci.detector == name[0]) & (committed_ci.seed == name[1])
                                       & (committed_ci.nominal_fpr == ALPHA) & (committed_ci.metric == row["metric"])]
                    if len(ref) != 1 or ref.ci_lower_95.iloc[0] != row["ci_lower_95"] or ref.ci_upper_95.iloc[0] != row["ci_upper_95"]:
                        raise ec.ExtensionError(f"{key}: G5 interval not reproduced for {ec.run_name(*name)} {row['metric']}")
        cp_replicates.extend({"subset": key, "detector": name[0], "seed": name[1], "replicate": b,
                              **{c: rec[c] for c in REPLICATE_COLUMNS}} for b, rec in enumerate(results["class_preserving"]))
    log(f"{key}: component 2 in {time.time() - clock_b:.0f} s; G5 passed ({g5} runs); original design omitted a "
        f"calibration class in {original_omits} of {ec.BOOTSTRAP_REPLICATES} replicates")

    tables = {"engine_noise_floor": pd.DataFrame(noise_rows), "noise_floor_draws": pd.DataFrame(draw_rows),
              "local_recalibration": pd.DataFrame(local_rows), "bootstrap_class_preserving_ci": pd.DataFrame(ci_rows),
              "bootstrap_class_preserving_replicates_alpha_0.01": pd.DataFrame(cp_replicates)}
    hashes = {name: ec.write_csv(out_dir / f"{name}.csv", frame) for name, frame in tables.items()}
    ec.verify_baseline()                                                          # G1 (after)
    ec.write_json(out_dir / "validation_record.json", {
        "subset": key, "plan": "docs/extension/FOCUSED_VALIDATION_PLAN.md (FROZEN v1.0)", "plan_sha256": PLAN_SHA256,
        "status": "post hoc focused validation; healthy official-test rows only; reproduction only",
        "calibration_lock_sha256": lock_sha, "healthy_audit_rows": int(len(meta_h)),
        "gates": {"G1_baseline": "verified before and after", "G2_plan_and_code": "tracked, clean, plan hash equal",
                  "G3_calibration_fingerprints": "equal (10 runs)",
                  "G4_healthy_counts": f"equal ({g4} run x target x arm phase and flight count checks)",
                  "G5_original_replicates": f"equal ({g5} runs; alpha = 1% replicates and intervals)"},
        "original_design_replicates_omitting_a_class": original_omits,
        "parameters": {"alpha": ALPHA, "folds": FOLDS, "crossfit_repetitions": R_CROSSFIT, "K": K_LOCAL,
                       "k_matched_repetitions": R_LOCAL, "seeds": {"crossfit": SEED_CROSSFIT,
                                                                    "class_preserving": SEED_CLASS_BOOT,
                                                                    "k_matched": SEED_LOCAL}},
        "outputs_sha256": hashes, "started_utc": started, "finished_utc": ec.now_utc(),
        "seconds": round(time.time() - clock, 1),
        "code": {"git_head": ec.git_sha(), "files": {f: ec.file_digest(ec.ROOT / f) for f in CODE_FILES}}})
    ec.append_access_log(key, "Focused validation outputs written", f"{len(hashes)} tables; gates G1-G5 passed; "
                         f"{round(time.time() - clock)} s", lock_sha=lock_sha[:12], command=command)
    return hashes


# ---------------------------------------------------------------------------
# Summary (pre-declared interpretation, plan section 6)
# ---------------------------------------------------------------------------

def uext2_with(replicates_by_key=None):
    """U-EXT2 via the frozen routine; with replicates_by_key, the U-EXT1 replicates are substituted."""
    keys = list(ec.NEW_ORDER)
    original_read = xs.read

    def patched(key, table):
        if replicates_by_key is not None and table == "bootstrap_uext1_replicates_alpha_0.01":
            return replicates_by_key[key]
        return original_read(key, table)

    xs.read = patched
    try:
        ts, paired = xs.primary_tables(keys)
        return xs.uext2(ts, paired, keys)
    finally:
        xs.read = original_read


def summarize(log=print):
    keys = list(ec.NEW_ORDER)
    for key in keys:
        if not (output_root() / key / "validation_record.json").exists():
            raise ec.ExtensionError(f"Focused validation outputs missing for {key}")
    read = lambda key, table: pd.read_csv(output_root() / key / f"{table}.csv", float_precision="round_trip")  # noqa: E731
    noise = pd.concat([read(k, "engine_noise_floor") for k in keys], ignore_index=True)
    local = pd.concat([read(k, "local_recalibration") for k in keys], ignore_index=True)
    ci = pd.concat([read(k, "bootstrap_class_preserving_ci") for k in keys], ignore_index=True)

    # G6: the U-EXT2 routine reproduces the committed table from the committed replicates
    committed_u2 = pd.read_csv(ec.RESULTS / "summary" / "uext2_cross_dataset.csv", float_precision="round_trip")
    again = uext2_with(None)
    for column in ("point_median_over_families", "ci_lower_95", "ci_upper_95"):
        if not np.allclose(again[column].to_numpy(), committed_u2[column].to_numpy(), rtol=0, atol=1e-15):
            raise ec.ExtensionError(f"G6: U-EXT2 not reproduced ({column}) (stop rule)")
    cp_u2 = uext2_with({k: read(k, "bootstrap_class_preserving_replicates_alpha_0.01") for k in keys})
    u2 = committed_u2[["detector_family", "quantity", "point_median_over_families", "ci_lower_95", "ci_upper_95"]].merge(
        cp_u2[["detector_family", "quantity", "ci_lower_95", "ci_upper_95"]], on=["detector_family", "quantity"],
        suffixes=("_original", "_class_preserving"))
    u2["width_original"] = u2.ci_upper_95_original - u2.ci_lower_95_original
    u2["width_class_preserving"] = u2.ci_upper_95_class_preserving - u2.ci_lower_95_class_preserving
    u2["width_ratio"] = u2.width_class_preserving / u2.width_original
    u2["includes_zero_original"] = (u2.ci_lower_95_original <= 0) & (u2.ci_upper_95_original >= 0)
    u2["includes_zero_class_preserving"] = (u2.ci_lower_95_class_preserving <= 0) & (u2.ci_upper_95_class_preserving >= 0)

    # Component 1: engine classification (majority of runs above the engine's own NF95)
    residual = noise[noise.detector != "cvae"]
    cvae = noise[noise.detector == "cvae"]
    engine_rows = []
    for (key, e, arm), g in residual.groupby(["subset", "unit", "arm"]):
        c = cvae[(cvae.subset == key) & (cvae.unit == e) & (cvae.arm == arm)]
        engine_rows.append({"subset": key, "family": ec.FAMILIES[key], "unit": e, "arm": arm,
                            "flight_class": int(g.flight_class.iloc[0]),
                            "class_in_calibration": bool(g.class_in_calibration.iloc[0]),
                            "healthy_flights": int(g.healthy_flights.iloc[0]),
                            "observed_A2_median": float(g.observed_A2.median()), "NF50_median": float(g.NF50.median()),
                            "NF95_median": float(g.NF95.median()), "ratio_to_NF50_median": float(g.ratio_to_NF50.median()),
                            "excess_over_NF95_median": float(g.excess_over_NF95.median()),
                            "residual_runs_exceeding": int(g.exceeds_NF95.sum()),
                            "clearly_exceeds": majority_exceeds(g.exceeds_NF95.to_numpy()),
                            "cvae_runs_exceeding": int(c.exceeds_NF95.sum()),
                            "cvae_clearly_exceeds": majority_exceeds(c.exceeds_NF95.to_numpy(), residual=False)})
    engines = pd.DataFrame(engine_rows)
    family_rows = []
    for (fam, arm), g in engines.groupby(["family", "arm"]):
        family_rows.append({"family": fam, "arm": arm, "engines": len(g), "clearly_exceeding": int(g.clearly_exceeds.sum()),
                            "share": float(g.clearly_exceeds.mean()), "shows_excess": bool(g.clearly_exceeds.mean() >= 0.5),
                            "cvae_clearly_exceeding": int(g.cvae_clearly_exceeds.sum())})
    families = pd.DataFrame(family_rows)

    # Component 3: local recalibration per engine and family
    lres = local[local.detector != "cvae"]
    local_rows = []
    for (key, e, arm), g in lres.groupby(["subset", "unit", "arm"]):
        local_rows.append({"subset": key, "family": ec.FAMILIES[key], "unit": e, "arm": arm,
                           "flight_class": int(g.flight_class.iloc[0]),
                           "class_in_calibration": bool(g.class_in_calibration.iloc[0]),
                           "eval_flights": int(g.eval_flights.iloc[0]),
                           "fleet_eval_A2_median": float(g.fleet_eval_A2.median()),
                           "local_A2_median": float(g.local_A2.median()), "improvement_median": float(g.improvement.median()),
                           "runs_improved": int((g.improvement > 0).sum()), "NFK95_median": float(g.NFK95.median()),
                           "runs_local_within_NFK95": int(g.local_within_NFK95.sum()),
                           "brought_into_noise_range": majority_exceeds(g.local_within_NFK95.to_numpy()),
                           "runs_fleet_within_NFK95": int(g.fleet_within_NFK95.sum()),
                           "fleet_within_noise_range": majority_exceeds(g.fleet_within_NFK95.to_numpy()),
                           "runs_local_within_NF95": int(g.local_within_NF95.sum())})
    local_engines = pd.DataFrame(local_rows)
    local_families = local_engines.groupby(["family", "arm"]).agg(
        engines=("unit", "size"), improvement_median=("improvement_median", "median"),
        brought_into_noise=("brought_into_noise_range", "sum"), fleet_already_within=("fleet_within_noise_range", "sum"),
        local_A2_median=("local_A2_median", "median"), fleet_eval_A2_median=("fleet_eval_A2_median", "median")).reset_index()

    # Component 2: width comparison (per subset x metric; residual runs)
    wide = ci[ci.metric.isin(WIDTH_METRICS)].pivot_table(index=["subset", "family", "detector", "seed", "metric"],
                                                          columns="design", values=["width", "includes_zero"],
                                                          aggfunc="first")
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    wide = wide.reset_index()
    wide["width_ratio"] = wide.width_class_preserving / wide.width_original
    width_summary = wide[wide.detector != "cvae"].groupby(["subset", "metric"]).agg(
        runs=("width_ratio", "size"), median_width_ratio=("width_ratio", "median"),
        original_includes_zero=("includes_zero_original", "sum"),
        class_preserving_includes_zero=("includes_zero_class_preserving", "sum")).reset_index()
    width_summary["share_of_width_from_class_omission"] = 1 - width_summary.median_width_ratio

    # Pre-declared interpretation (plan section 6)
    fam_c = families[families.arm == "phase_conditioned"]
    n_excess_c = int(fam_c.shows_excess.sum())
    verdict = "STRENGTHENED" if n_excess_c >= 3 else ("NARROWED" if n_excess_c >= 1 else "WEAKENED")
    loc_c = local_engines[local_engines.arm == "phase_conditioned"]
    local_verdict = ("local correction possible" if loc_c.brought_into_noise_range.mean() > 0.5
                     else "not correctable with K = 5 healthy flights")
    summary = {
        "plan": "docs/extension/FOCUSED_VALIDATION_PLAN.md (FROZEN v1.0)", "plan_sha256": PLAN_SHA256,
        "status": "post hoc focused validation; pre-specified H1-H7 unchanged",
        "G6_uext2_reproduced": True,
        "component1": {arm: {"engines": int(len(g)), "clearly_exceeding": int(g.clearly_exceeds.sum()),
                             "share": float(g.clearly_exceeds.mean()),
                             "families_showing_excess": int(families[(families.arm == arm)].shows_excess.sum()),
                             "cvae_clearly_exceeding": int(g.cvae_clearly_exceeds.sum())}
                       for arm, g in engines.groupby("arm")},
        "transport_claim": verdict, "families_showing_excess_under_C": n_excess_c,
        "component3": {arm: {"engines": int(len(g)), "brought_into_noise_range": int(g.brought_into_noise_range.sum()),
                             "fleet_already_within_noise_range": int(g.fleet_within_noise_range.sum()),
                             "median_improvement": float(g.improvement_median.median()),
                             "engines_improved_majority": int((g.runs_improved >= RESIDUAL_MAJORITY).sum())}
                       for arm, g in local_engines.groupby("arm")},
        "local_recalibration_verdict": local_verdict,
        "component2": {"median_width_ratio_by_metric": {m: float(g.median_width_ratio.median())
                                                        for m, g in width_summary.groupby("metric")},
                       "uext2_width_ratio": {f"{r.detector_family}|{r.quantity}": float(r.width_ratio)
                                             for r in u2.itertuples()}},
    }
    out = output_root() / "summary"
    frames = {"engine_summary": engines, "family_summary": families, "local_engine_summary": local_engines,
              "local_family_summary": local_families, "bootstrap_width_comparison": width_summary,
              "bootstrap_width_by_run": wide, "uext2_original_vs_class_preserving": u2}
    hashes = {name: ec.write_csv(out / f"{name}.csv", frame) for name, frame in frames.items()}
    summary["outputs_sha256"] = hashes
    ec.write_json(out / "focused_validation_summary.json", summary)
    log(json.dumps({k: summary[k] for k in ("transport_claim", "families_showing_excess_under_C",
                                             "local_recalibration_verdict")}))
    return summary
