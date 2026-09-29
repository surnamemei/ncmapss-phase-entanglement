"""Extension orchestration: Phase L (calibration-only lock), Phase A (one-shot audit) and the DS02/DS03 reference work.

Protocol: docs/extension/GENERALIZATION_PROTOCOL.md section 10.
- Phase L reads only hs = 1 rows of fit and calibration engines.
- Phase A refuses to run without a committed, hash-verified lock. It creates the one-shot marker by
  exclusive create *before* the first official-test read.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import ext_calibration as xc
import ext_common as ec
import ext_cvae
import ext_endpoints as xe
import ext_models as xm
import final_validation as fv

CODE_FILES = ("src/ext_common.py", "src/ext_cvae.py", "src/ext_models.py", "src/ext_calibration.py",
              "src/ext_qfit.py", "src/ext_endpoints.py", "src/ext_pipeline.py", "src/ext_summary.py")
FROZEN_LSTM_DIRS = {"DS02": ec.ROOT / "results/final_validation/checkpoints",
                    "DS03": ec.ROOT / "results/confirmation_ds03/checkpoints"}
MITIGATION = ec.ROOT / "results/mssp_mitigation"
ADVERSARIAL = ec.ROOT / "results/mssp_adversarial"


def code_record():
    return {"git_head": ec.git_sha(), "protocol_sha256": ec.file_digest(ec.PROTOCOL),
            "cvae_spec_sha256": ec.file_digest(ec.CVAE_SPEC),
            "files": {name: ec.file_digest(ec.ROOT / name) for name in CODE_FILES}}


def common_healthy_cycles(family):
    """F3 duplicate check: per unit, the healthy cycles common to every subset of the family (DS05, DS06, DS07)."""
    meta = pd.read_csv(ec.ENGINE_METADATA)
    members = [k for k, f in ec.FAMILIES.items() if f == family]
    part = meta[meta.dataset.isin(members)]
    return {int(u): int(g.healthy_flights.min()) for u, g in part.groupby("unit")}


def duplicate_digests(subset, rows):
    if ec.FAMILIES[subset.key] != "F3":
        return {}
    common = common_healthy_cycles("F3")
    out = {}
    for unit in sorted(int(u) for u in np.unique(rows.meta.unit)):
        mask = (rows.meta.unit.to_numpy() == unit) & (rows.meta.cycle.to_numpy() <= common[unit]) & (
            rows.meta.healthy.to_numpy() == 1)
        out[str(unit)] = {"cycles": common[unit], "rows": int(mask.sum()),
                          "sha256": ec.array_fingerprint(rows.x[mask])}
    return out


# ---------------------------------------------------------------------------
# Calibration-side thresholds (shared by Phase L and the reference work)
# ---------------------------------------------------------------------------

def calibration_thresholds(subset, cal, cal_scores, log=print):
    cal_phase = cal.meta.phase_primary.to_numpy()
    starts, ends = xc.flight_bounds(cal.meta)
    scale = xc.q_scale(cal.w)
    features = xc.q_features(cal.w, scale)
    clock = time.time()
    q_fits = xc.fit_q_thresholds(features, cal_scores)
    log(f"{subset.key}: {len(q_fits)} quantile-regression fits in {time.time() - clock:.0f} s")
    runs, descriptive = {}, []
    for name, scores in cal_scores.items():
        run = ec.run_name(*name)
        runs[run] = {}
        for alpha in ec.TARGETS:
            taus = xc.quantile_taus(scores, cal_phase, alpha)
            q_values = xc.predict_q(features, q_fits[(name, alpha)])
            kappa, flag_rate, row_rate = {}, {}, {}
            for arm in ec.ARMS:
                exceed = scores > xc.row_thresholds(arm, taus, cal_phase, q_values)
                kappa[arm], flag_rate[arm], row_rate[arm] = {}, {}, {}
                for rule in ec.RULES:
                    alarm = xc.apply_rule(exceed, starts, ends, rule)
                    fraction = xc.flight_fraction(alarm, starts, ends)
                    kappa[arm][rule] = xc.kappa(fraction)
                    flag_rate[arm][rule] = float(np.mean(fraction > kappa[arm][rule]))
                    row_rate[arm][rule] = float(alarm.mean())
                for i, p in enumerate(xc.PHASES):
                    descriptive.append({"subset": subset.key, "detector": name[0], "seed": name[1],
                                        "nominal_fpr": alpha, "arm": arm, "phase": p,
                                        "calibration_rows": int(np.sum(cal_phase == i)),
                                        "in_sample_fpr": float(exceed[cal_phase == i].mean())})
            runs[run][str(alpha)] = {"tau": taus, "q_fit": q_fits[(name, alpha)], "kappa": kappa,
                                     "calibration_flight_false_flag_rate": flag_rate,
                                     "calibration_row_alarm_rate": row_rate}
    return runs, scale, pd.DataFrame(descriptive)


def composition_block(subset, cal, cal_scores):
    pool = {g: subset.classes[g] for g in subset.calibration}
    eligible = ec.composition_eligible(subset)
    if not eligible and subset.key != "DS02":
        return None
    volume = ec.composition_volume(subset)
    designs = xc.build_designs(pool, volume)
    if not eligible:  # DS02: one-class pool; volume designs only (descriptive)
        designs = [d for d in designs if set(d.codes) & {"A", "B", "V"}]
    thresholds = xc.design_thresholds(designs, cal.meta.unit.to_numpy(), cal.meta.phase_primary.to_numpy(),
                                      cal_scores)
    per_run = {}
    for (design, draw, name, alpha), taus in thresholds.items():
        per_run.setdefault(ec.run_name(*name), {})[f"{design}|{draw}|{alpha}"] = taus
    return {"eligible": eligible, "volume_N": volume, "draws": list(ec.COMPOSITION_DRAWS),
            "base_seed": ec.COMPOSITION_BASE_SEED, "pool_classes": {str(k): v for k, v in pool.items()},
            "designs": [d.as_record() for d in designs], "thresholds": per_run}


def calibration_rows_record(cal):
    phase = cal.meta.phase_primary.to_numpy()
    starts, _ = xc.flight_bounds(cal.meta)
    return {"total": int(len(phase)), "phase": {p: int(np.sum(phase == i)) for i, p in enumerate(xc.PHASES)},
            "engine": {str(int(u)): int(n) for u, n in zip(*np.unique(cal.meta.unit, return_counts=True))},
            "flights": int(len(starts))}


def precision_audit(models, cal):
    """CVAE float32 versus float64 scoring on the first 100,000 calibration rows (diagnostic only)."""
    import torch
    head = xm.Rows(cal.x[:100_000], cal.w[:100_000], cal.meta.iloc[:100_000], [], cal.descriptors[:100_000])
    out = {}
    for seed, fitted in models.cvaes.items():
        s32 = ext_cvae.score(fitted, head.x, head.descriptors, dtype=torch.float32)
        s64 = ext_cvae.score(fitted, head.x, head.descriptors, dtype=torch.float64)
        tau = np.quantile(s32, 0.99, method="higher")
        from scipy.stats import spearmanr
        out[str(seed)] = {"max_relative_difference": float(np.max(np.abs(s32 - s64) / np.maximum(np.abs(s64), 1e-12))),
                          "spearman": float(spearmanr(s32, s64).statistic),
                          "exceedance_count_float32": int(np.sum(s32 > tau)),
                          "exceedance_count_float64": int(np.sum(s64 > tau))}
    return out


def variance_floor_share(models, cal):
    import torch
    out = {}
    for seed, fitted in models.cvaes.items():
        model = fitted["model"]
        xs, cs = fitted["x_std"](cal.x), fitted["c_std"](cal.descriptors)
        near = total = 0
        with torch.no_grad():
            for start in range(0, len(xs), ext_cvae.SCORE_BATCH):
                xb = torch.from_numpy(xs[start:start + ext_cvae.SCORE_BATCH]).to(ext_cvae.DEVICE)
                cb = torch.from_numpy(cs[start:start + ext_cvae.SCORE_BATCH]).to(ext_cvae.DEVICE)
                mu_z, _ = model.encode(xb, cb)
                _, logvar = model.decode(mu_z, cb)
                span = ext_cvae.MAX_LOGVAR - ext_cvae.MIN_LOGVAR
                near += int(((logvar - ext_cvae.MIN_LOGVAR < 0.01 * span) | (ext_cvae.MAX_LOGVAR - logvar < 0.01 * span)).sum())
                total += logvar.numel()
        out[str(seed)] = near / total
    return out


# ---------------------------------------------------------------------------
# Phase L: calibration-only lock for a new subset
# ---------------------------------------------------------------------------

def phase_lock(key, log=print, command="python scripts/run_extension.py lock"):
    ec.verify_baseline()
    subset = ec.load_registry()[key]
    if subset.reference:
        raise ec.ExtensionError("Reference subsets use reference_work()")
    lock_dir = subset.out / "lock"
    if (lock_dir / "calibration_lock.json").exists():
        raise ec.ExtensionError(f"{key}: a calibration lock already exists")
    started, clock = ec.now_utc(), time.time()
    digest = ec.verify_input(subset)
    fv.configure_cuda_runtime()
    ec.append_access_log(key, "Healthy fit and calibration data first opened",
                         f"hs = 1 rows of fit {list(subset.fit)} and calibration {list(subset.calibration)}; "
                         "no official-test array", command=command)
    dev = xm.load_development_healthy(subset)
    log(f"{key}: {len(dev.meta)} healthy development rows loaded")
    models, _ = xm.fit_models(subset, dev, subset.out / "models", log=log)
    cal = xm.subset_rows(dev, subset.calibration)
    cal_scores = xm.score_all(models, cal)
    runs, scale, descriptive = calibration_thresholds(subset, cal, cal_scores, log=log)
    composition = composition_block(subset, cal, cal_scores)
    lock = {"protocol": "docs/extension/GENERALIZATION_PROTOCOL.md (FROZEN v1.0)", "subset": key,
            "status": "calibration-only; locked before any official-test array is read",
            "input_sha256": digest, "roles": subset.roles_record(), "targets": list(ec.TARGETS),
            "arms": list(ec.ARMS), "rules": list(ec.RULES), "calibration_rows": calibration_rows_record(cal),
            "models": {"files": models.files, "selected_epochs": models.selected_epochs},
            "calibration_fingerprints": xm.fingerprints(cal_scores), "q_scale": scale, "runs": runs,
            "composition": composition, "duplicate_digests_development": duplicate_digests(subset, dev),
            "cvae_precision_audit": precision_audit(models, cal),
            "cvae_variance_bound_share": variance_floor_share(models, cal), "code": code_record()}
    lock_sha = ec.write_json(lock_dir / "calibration_lock.json", lock)
    ec.write_csv(lock_dir / "training_history.csv", pd.DataFrame(models.history))
    ec.write_csv(lock_dir / "calibration_in_sample_phase_fpr.csv", descriptive)
    finished = ec.now_utc()
    ec.write_json(lock_dir / "lock_record.json", {"subset": key, "lock_sha256": lock_sha, "started_utc": started,
                                                  "locked_utc": finished, "seconds": round(time.time() - clock, 1),
                                                  "official_test_read": False})
    ec.append_access_log(key, "Calibration lock written", f"thresholds, kappa and composition locked; "
                         f"{round(time.time() - clock)} s", lock_sha=lock_sha[:12], command=command)
    ec.verify_baseline()
    return lock_sha


# ---------------------------------------------------------------------------
# Evaluation shared by Phase A and the reference work
# ---------------------------------------------------------------------------

def evaluate(subset, lock, models, cal, cal_scores, audit, audit_scores, out_dir, log=print):
    features = xc.q_features(audit.w, lock["q_scale"])
    q_all = {(name, alpha): xc.predict_q(features, lock["runs"][ec.run_name(*name)][str(alpha)]["q_fit"])
             for name in audit_scores for alpha in ec.TARGETS}
    healthy = audit.meta.healthy.to_numpy() == 1
    meta_h = audit.meta[healthy].reset_index(drop=True)
    scores_h = {name: values[healthy] for name, values in audit_scores.items()}
    q_h = {key: values[healthy] for key, values in q_all.items()}
    cal_starts, cal_ends = xc.flight_bounds(cal.meta)
    cal_features = xc.q_features(cal.w, lock["q_scale"])
    cal_q = {(name, alpha): xc.predict_q(cal_features, lock["runs"][ec.run_name(*name)][str(alpha)]["q_fit"])
             for name in cal_scores for alpha in ec.TARGETS}
    reference, cal_fractions = xe.calibration_reference(lock, cal_scores, cal.meta, cal_q, cal_starts, cal_ends)
    for (run, alpha, arm, rule), fraction in cal_fractions.items():  # kappa must reproduce the lock exactly
        if xc.kappa(fraction) != lock["runs"][run][str(alpha)]["kappa"][arm][rule]:
            raise ec.ExtensionError(f"Recomputed kappa differs from the lock: {run} {alpha} {arm} {rule}")
    flights = xe.audit_flights(audit.meta)
    tables = {}
    clock = time.time()
    tables.update(xe.healthy_tables(subset.key, lock, scores_h, meta_h, q_h))
    log(f"{subset.key}: healthy tables {time.time() - clock:.0f} s")
    clock = time.time()
    persistence = xe.persistence_and_flight_tables(subset.key, lock, audit_scores, audit.meta, q_all, flights,
                                                   reference)
    tables.update(persistence)
    log(f"{subset.key}: flight and persistence tables {time.time() - clock:.0f} s")
    clock = time.time()
    tables.update(xe.matched_tables(subset.key, persistence["flight_trajectories"], cal_fractions, lock))
    log(f"{subset.key}: matched tables {time.time() - clock:.0f} s")
    clock = time.time()
    tables.update(xe.composition_tables(subset.key, lock, scores_h, meta_h))
    log(f"{subset.key}: composition tables {time.time() - clock:.0f} s")
    clock = time.time()
    cal_meta = cal.meta.reset_index(drop=True)
    summary, replicates = xe.bootstrap_uext1(subset.key, cal_scores, cal_meta, scores_h, meta_h)
    tables["bootstrap_uext1_ci"] = summary
    tables["bootstrap_uext1_replicates_alpha_0.01"] = replicates
    log(f"{subset.key}: U-EXT1 bootstrap {time.time() - clock:.0f} s")
    tables["audit_flights"] = flights
    hashes = {name: ec.write_csv(Path(out_dir) / f"{name}.csv", frame) for name, frame in tables.items()}
    return tables, hashes


def score_audit(models, audit):
    """Score healthy and post-onset audit rows in separate calls, then restore file order (Amendment 3).

    This is the frozen convention: Stages C/D scored healthy rows alone and Stage E scored abnormal rows
    alone. LSTM scores depend at float32 rounding level on GPU batch composition, so scoring both
    together would not reproduce the frozen fingerprints. `hs` is constant within flights, so each call
    receives whole flights.
    """
    healthy = audit.meta.healthy.to_numpy() == 1
    combined = None
    for mask in (healthy, ~healthy):
        if not mask.any():
            continue
        part = xm.Rows(audit.x[mask], audit.w[mask], audit.meta[mask].reset_index(drop=True), [],
                       audit.descriptors[mask], audit.descriptor_names)
        scores = xm.score_all(models, part)
        if combined is None:
            combined = {name: np.full(len(audit.meta), np.nan) for name in scores}
        for name, values in scores.items():
            combined[name][mask] = values
    for name, values in combined.items():
        if not np.isfinite(values).all():
            raise ec.ExtensionError(f"score_audit left rows unscored for {name}")
    return combined


def verify_calibration(subset, lock, model_dir, frozen_lstm_dir=None):
    dev = xm.load_development_healthy(subset)
    cal = xm.subset_rows(dev, subset.calibration)
    models = xm.load_models(model_dir, lock["models"]["files"], frozen_lstm_dir=frozen_lstm_dir)
    cal_scores = xm.score_all(models, cal)
    if xm.fingerprints(cal_scores) != lock["calibration_fingerprints"]:
        raise ec.ExtensionError(f"{subset.key}: calibration scores do not reproduce the lock (stop rule)")
    return models, cal, cal_scores, dev


# ---------------------------------------------------------------------------
# Phase A: one-shot official audit of a new subset
# ---------------------------------------------------------------------------

def phase_audit(key, *, reproduction_only=False, log=print, command="python scripts/run_extension.py audit"):
    ec.verify_baseline()
    subset = ec.load_registry()[key]
    lock_path = subset.out / "lock" / "calibration_lock.json"
    record_path = subset.out / "lock" / "lock_record.json"
    if not (lock_path.exists() and record_path.exists()):
        raise ec.ExtensionError(f"{key}: no calibration lock; the official test may not be opened (stop rule)")
    if not (ec.git_tracked_and_clean(lock_path) and ec.git_tracked_and_clean(record_path)):
        raise ec.ExtensionError(f"{key}: the lock is not committed and clean; refusing to open the official test")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    lock_sha = ec.file_digest(lock_path)
    if lock_sha != record["lock_sha256"]:
        raise ec.ExtensionError(f"{key}: lock hash differs from its record (stop rule)")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    marker = subset.out / "audit" / "official_test_opened.json"
    if marker.exists() and not reproduction_only:
        raise ec.ExtensionError(f"{key}: the official audit already ran (one-shot marker exists)")
    if reproduction_only and not marker.exists():
        raise ec.ExtensionError(f"{key}: --reproduction-only needs a completed audit")
    out_dir = subset.out / ("audit" if not reproduction_only else f"reproduction_{ec.now_utc().replace(':', '')}")
    started, clock = ec.now_utc(), time.time()
    ec.verify_input(subset)
    fv.configure_cuda_runtime()
    models, cal, cal_scores, _ = verify_calibration(subset, lock, subset.out / "models")
    if not reproduction_only:
        ec.write_json(marker, {"status": "official_test_opened_once", "subset": key, "opened_utc": ec.now_utc(),
                               "calibration_lock_sha256": lock_sha, "git_head": ec.git_sha()})
        ec.append_access_log(key, "Official test sensor data first opened; abnormal rows first opened",
                             f"all rows of audit engines {list(subset.audit)}", lock_sha=lock_sha[:12], command=command)
    audit = xm.load_audit_rows(subset)
    log(f"{key}: {len(audit.meta)} official-test rows loaded ({int((audit.meta.healthy == 1).sum())} healthy)")
    audit_scores = score_audit(models, audit)
    tables, hashes = evaluate(subset, lock, models, cal, cal_scores, audit, audit_scores, out_dir, log=log)
    healthy = audit.meta.healthy.to_numpy() == 1
    ec.write_json(out_dir / "audit_record.json", {
        "subset": key, "calibration_lock_sha256": lock_sha, "reproduction_only": reproduction_only,
        "audit_rows": int(len(audit.meta)), "healthy_rows": int(healthy.sum()),
        "post_onset_rows": int((~healthy).sum()),
        "audit_fingerprints": {ec.run_name(*n): ec.array_fingerprint(v) for n, v in audit_scores.items()},
        "duplicate_digests_audit": duplicate_digests(subset, audit), "outputs_sha256": hashes,
        "started_utc": started, "finished_utc": ec.now_utc(), "seconds": round(time.time() - clock, 1),
        "code": code_record()})
    ec.append_access_log(key, "Official audit outputs written" + (" (reproduction only)" if reproduction_only else ""),
                         f"{len(hashes)} tables; {round(time.time() - clock)} s", lock_sha=lock_sha[:12], command=command)
    ec.verify_baseline()
    return hashes


# ---------------------------------------------------------------------------
# Reference work on DS02/DS03 (post-confirmation; shakedown of the audit code)
# ---------------------------------------------------------------------------

def _frozen_trajectory_check(key, lock, audit_scores, audit):
    """Residual runs: R0 alarm counts per flight under P and C must equal the committed Stage E trajectories."""
    traj = pd.read_csv(MITIGATION / key.lower() / "stage_e" / "flight_alarm_fraction_trajectories.csv")
    flights = xe.audit_flights(audit.meta)
    starts = flights.start.to_numpy()
    phase = audit.meta.phase_primary.to_numpy()
    checked = 0
    for name in ec.RESIDUAL_RUNS:
        run = ec.run_name(*name)
        for alpha in ec.TARGETS:
            taus = lock["runs"][run][str(alpha)]["tau"]
            for arm in ("pooled", "phase_conditioned"):
                alarm = audit_scores[name] > xc.row_thresholds(arm, taus, phase)
                counts = np.add.reduceat(alarm.astype(np.int64), starts)
                frozen = traj[(traj.detector == name[0]) & (traj.seed == name[1]) & (traj.nominal_fpr == alpha)
                              & (traj.scheme == arm)].sort_values("start")
                if not (np.array_equal(frozen.start.to_numpy(), starts)
                        and np.array_equal(frozen.alarms.to_numpy(), counts)):
                    raise ec.ExtensionError(f"{key}: Stage E trajectory not reproduced for {run} {alpha} {arm}")
                checked += 1
    return checked


def _frozen_q_check(key, tables):
    """Residual runs: Q healthy phase FPRs must equal the committed adversarial Part D table."""
    frozen = pd.read_csv(ADVERSARIAL / key.lower() / "contextual_baseline" / "baseline_phase_fpr.csv")
    ours = tables["phase_fpr"][(tables["phase_fpr"].arm == "quantile_regression_W")]
    frozen = frozen.assign(unit=frozen.unit.astype(str))
    ours = ours[ours.detector != "cvae"].assign(unit=ours.unit.astype(str))
    merged = ours.merge(frozen, on=["detector", "seed", "nominal_fpr", "unit", "phase"], suffixes=("", "_frozen"))
    if len(merged) != len(frozen) or not (merged.n == merged.n_frozen).all() or not (
            merged.alarms == merged.alarms_frozen).all():
        bad = merged[(merged.n != merged.n_frozen) | (merged.alarms != merged.alarms_frozen)]
        raise ec.ExtensionError(f"{key}: Q healthy-side counts differ from the adversarial Part D table "
                                f"({len(bad)} of {len(merged)} cells; {len(frozen)} frozen cells)")
    return int(len(merged))


def reference_work(key, log=print, command="python scripts/run_extension.py reference"):
    ec.verify_baseline()
    subset = ec.load_registry()[key]
    if not subset.reference:
        raise ec.ExtensionError("reference_work() is for DS02/DS03 only")
    root = subset.out
    if (root / "lock" / "calibration_lock.json").exists():
        raise ec.ExtensionError(f"{key}: reference lock already exists")
    started, clock = ec.now_utc(), time.time()
    digest = ec.verify_input(subset)
    fv.configure_cuda_runtime()
    ec.append_access_log(key, "Reference subset re-read (post-confirmation; data opened by the frozen study)",
                         "healthy development rows for CVAE training and rescoring", command=command)
    dev = xm.load_development_healthy(subset)
    models, _ = xm.fit_models(subset, dev, root / "models", frozen_lstm_dir=FROZEN_LSTM_DIRS[key], log=log)
    cal = xm.subset_rows(dev, subset.calibration)
    cal_scores = xm.score_all(models, cal)
    stage_c = json.loads((MITIGATION / key.lower() / "stage_c" / "score_fingerprints.json").read_text())
    ours = xm.fingerprints(cal_scores)
    for run in (ec.run_name(*n) for n in ec.RESIDUAL_RUNS):
        if ours[run] != stage_c[run]["calibration"]:
            raise ec.ExtensionError(f"{key}: calibration fingerprint of {run} differs from Stage C (stop rule)")
    runs, scale, descriptive = calibration_thresholds(subset, cal, cal_scores, log=log)
    frozen_lock = json.loads((MITIGATION / key.lower() / "stage_l" / "mitigation_lock.json").read_text())
    for run in (ec.run_name(*n) for n in ec.RESIDUAL_RUNS):
        for alpha in ec.TARGETS:
            ours_tau, frozen_tau = runs[run][str(alpha)]["tau"], frozen_lock["runs"][run][str(alpha)]["tau"]
            frozen_c = [frozen_tau["phase_conditioned"][p] for p in xc.PHASES]
            if ours_tau["pooled"] != frozen_tau["pooled"] or ours_tau["phase_conditioned"] != frozen_c:
                raise ec.ExtensionError(f"{key}: P/C thresholds of {run} {alpha} differ from the frozen lock")
    lock = {"protocol": "docs/extension/GENERALIZATION_PROTOCOL.md (FROZEN v1.0)", "subset": key,
            "status": "reference subset (post-confirmation); data previously opened by the frozen study",
            "input_sha256": digest, "roles": subset.roles_record(), "targets": list(ec.TARGETS),
            "arms": list(ec.ARMS), "rules": list(ec.RULES), "calibration_rows": calibration_rows_record(cal),
            "models": {"files": models.files, "selected_epochs": models.selected_epochs,
                       "frozen_lstm_dir": str(FROZEN_LSTM_DIRS[key].relative_to(ec.ROOT))},
            "calibration_fingerprints": ours, "q_scale": scale, "runs": runs,
            "composition": composition_block(subset, cal, cal_scores),
            "cvae_precision_audit": precision_audit(models, cal),
            "cvae_variance_bound_share": variance_floor_share(models, cal), "code": code_record(),
            "gates": {"stage_c_calibration_fingerprints": "equal (7 residual runs)",
                      "frozen_P_C_thresholds": "equal (7 residual runs x 3 targets)"}}
    lock_sha = ec.write_json(root / "lock" / "calibration_lock.json", lock)
    ec.write_csv(root / "lock" / "training_history.csv", pd.DataFrame(models.history))
    ec.write_csv(root / "lock" / "calibration_in_sample_phase_fpr.csv", descriptive)
    ec.write_json(root / "lock" / "lock_record.json", {"subset": key, "lock_sha256": lock_sha, "started_utc": started,
                                                       "locked_utc": ec.now_utc(), "reference": True})
    audit = xm.load_audit_rows(subset)
    audit_scores = score_audit(models, audit)
    healthy = audit.meta.healthy.to_numpy() == 1
    for run in (ec.run_name(*n) for n in ec.RESIDUAL_RUNS):
        name = tuple(run.split(":"))
        name = (name[0], int(name[1]))
        if ec.array_fingerprint(audit_scores[name][healthy]) != stage_c[run]["healthy_audit"]:
            raise ec.ExtensionError(f"{key}: healthy-audit fingerprint of {run} differs from Stage C (stop rule)")
    checked = _frozen_trajectory_check(key, lock, audit_scores, audit)
    tables, hashes = evaluate(subset, lock, models, cal, cal_scores, audit, audit_scores, root / "audit", log=log)
    q_cells = _frozen_q_check(key, tables)
    ec.write_json(root / "audit" / "audit_record.json", {
        "subset": key, "reference": True, "calibration_lock_sha256": lock_sha, "audit_rows": int(len(audit.meta)),
        "healthy_rows": int(healthy.sum()), "post_onset_rows": int((~healthy).sum()),
        "gates": {"stage_c_healthy_audit_fingerprints": "equal (7 residual runs)",
                  "stage_e_trajectory_alarm_counts": f"equal ({checked} run x target x arm checks)",
                  "adversarial_part_d_q_healthy_counts": f"equal ({q_cells} cells)"},
        "audit_fingerprints": {ec.run_name(*n): ec.array_fingerprint(v) for n, v in audit_scores.items()},
        "outputs_sha256": hashes, "started_utc": started, "finished_utc": ec.now_utc(),
        "seconds": round(time.time() - clock, 1), "code": code_record()})
    ec.append_access_log(key, "Reference outputs written", f"{len(hashes)} tables; gates passed",
                         lock_sha=lock_sha[:12], command=command)
    ec.verify_baseline()
    return hashes
