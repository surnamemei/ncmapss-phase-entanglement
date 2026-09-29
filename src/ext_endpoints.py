"""Extension endpoints A-K, persistence P1-P5, composition evaluation and U-EXT1 (protocol sections 6-9, 11.1).

Every function receives locked thresholds. The only role of calibration data here is the bootstrap's
re-estimation of thresholds (U-EXT1) and the recomputation of locked quantities for verification.
"""

from __future__ import annotations

import math
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import ext_calibration as xc
import ext_common as ec
import final_validation as fv
import mssp_adversarial as ma
import mssp_mitigation as mm

PHASES = xc.PHASES
DETECTED_WITHIN = ma.DETECTED_WITHIN  # (0, 1, 3, 5, 10)
EARLY = mm.EARLY_WINDOW_FLIGHTS  # 10
METRIC_KEYS = ("spread", "max_abs_error", "rms_error", "mean_abs_error", "overall_abs_error")


# ---------------------------------------------------------------------------
# Calibration-quality metrics (A1-A3, ME, WE, EW)
# ---------------------------------------------------------------------------

def errors(fpr_by_phase, overall, alpha):
    return ma.calibration_errors(fpr_by_phase, overall, alpha)


def cell_counts(alarm, units, phase, engines):
    """alarms and rows per engine x phase (engine order = `engines`)."""
    n_e = len(engines)
    engines_array = np.asarray(engines, dtype=np.int64)
    units = np.asarray(units, dtype=np.int64)
    engine_index = np.searchsorted(engines_array, units)
    if len(units) and not np.array_equal(engines_array[np.minimum(engine_index, n_e - 1)], units):
        raise ec.ExtensionError("cell_counts: a row belongs to an engine outside the engine list")
    cell = engine_index * 3 + phase.astype(np.int64)
    rows = np.bincount(cell, minlength=n_e * 3).reshape(n_e, 3)
    alarms = np.bincount(cell, weights=np.asarray(alarm, dtype=np.float64), minlength=n_e * 3).reshape(n_e, 3)
    return alarms, rows


def quality_from_counts(alarms, rows, alpha):
    """Per-engine, pooled, equal-engine (EW), mean-engine (ME) and worst-engine (WE) metrics."""
    fpr_e = alarms / rows
    overall_e = alarms.sum(axis=1) / rows.sum(axis=1)
    per_engine = [errors(fpr_e[i], overall_e[i], alpha) for i in range(len(fpr_e))]
    pooled_fpr = alarms.sum(axis=0) / rows.sum(axis=0)
    pooled = errors(pooled_fpr, alarms.sum() / rows.sum(), alpha)
    ew_fpr = fpr_e.mean(axis=0)
    ew = errors(ew_fpr, float(overall_e.mean()), alpha)
    a2 = np.array([m["max_abs_error"] for m in per_engine])
    a3 = np.array([m["rms_error"] for m in per_engine])
    return {"fpr_e": fpr_e, "overall_e": overall_e, "per_engine": per_engine, "pooled_fpr": pooled_fpr,
            "pooled_overall": float(alarms.sum() / rows.sum()), "pooled": pooled, "ew_fpr": ew_fpr, "ew": ew,
            "me_a2": float(a2.mean()), "me_a3": float(a3.mean()), "we_a2": float(a2.max()),
            "we_engine": int(np.argmax(a2)), "a2_e": a2}


def summary_record(q):
    return {"pooled_A1": q["pooled"]["spread"], "pooled_A2": q["pooled"]["max_abs_error"],
            "pooled_A3": q["pooled"]["rms_error"], "pooled_overall_fpr": q["pooled_overall"],
            "pooled_overall_abs_error": q["pooled"]["overall_abs_error"],
            **{f"pooled_{p}_fpr": v for p, v in zip(PHASES, q["pooled_fpr"])},
            "ME_A2": q["me_a2"], "ME_A3": q["me_a3"], "WE_A2": q["we_a2"],
            "EW_A1": q["ew"]["spread"], "EW_A2": q["ew"]["max_abs_error"], "EW_A3": q["ew"]["rms_error"]}


# ---------------------------------------------------------------------------
# Healthy-side endpoints on the full calibration pool
# ---------------------------------------------------------------------------

def arm_thresholds(lock_run_alpha, arm, phase, q_threshold):
    taus = lock_run_alpha["tau"]
    return xc.row_thresholds(arm, taus, phase, q_threshold)


def healthy_tables(subset_key, lock, scores, meta, q_thresholds):
    """Phase FPR (B), quality (A1-A3), transport summaries (ME/WE/EW), paired comparisons and transfer (T)."""
    engines = sorted(int(u) for u in np.unique(meta.unit))
    units, phase = meta.unit.to_numpy(), meta.phase_primary.to_numpy()
    rates, quality_rows, summary_rows, paired_rows, engine_rows, transfer_rows = [], [], [], [], [], []
    for name, values in scores.items():
        run = ec.run_name(*name)
        for alpha in ec.TARGETS:
            entry = lock["runs"][run][str(alpha)]
            per_arm = {}
            for arm in ec.ARMS:
                threshold = arm_thresholds(entry, arm, phase, q_thresholds.get((name, alpha)))
                alarm = values > threshold
                alarms, rows = cell_counts(alarm, units, phase, engines)
                q = quality_from_counts(alarms, rows, alpha)
                per_arm[arm] = q
                base = {"subset": subset_key, "detector": name[0], "seed": name[1], "nominal_fpr": alpha, "arm": arm}
                for i, e in enumerate(engines):
                    for j, p in enumerate(PHASES):
                        rates.append({**base, "unit": e, "phase": p, "n": int(rows[i, j]),
                                      "alarms": int(alarms[i, j]), "rate": float(alarms[i, j] / rows[i, j])})
                    rates.append({**base, "unit": e, "phase": "overall", "n": int(rows[i].sum()),
                                  "alarms": int(alarms[i].sum()), "rate": float(q["overall_e"][i])})
                    quality_rows.append({**base, "unit": str(e), "weighting": "per_engine",
                                         "flight_class": None, "overall_fpr": float(q["overall_e"][i]),
                                         **{f"{p}_fpr": float(v) for p, v in zip(PHASES, q["fpr_e"][i])},
                                         **q["per_engine"][i]})
                for j, p in enumerate(PHASES):
                    rates.append({**base, "unit": "all", "phase": p, "n": int(rows[:, j].sum()),
                                  "alarms": int(alarms[:, j].sum()), "rate": float(q["pooled_fpr"][j])})
                rates.append({**base, "unit": "all", "phase": "overall", "n": int(rows.sum()),
                              "alarms": int(alarms.sum()), "rate": q["pooled_overall"]})
                quality_rows.append({**base, "unit": "all", "weighting": "row_pooled", "flight_class": None,
                                     "overall_fpr": q["pooled_overall"],
                                     **{f"{p}_fpr": float(v) for p, v in zip(PHASES, q["pooled_fpr"])}, **q["pooled"]})
                quality_rows.append({**base, "unit": "equal_engine", "weighting": "equal_engine", "flight_class": None,
                                     "overall_fpr": float(q["overall_e"].mean()),
                                     **{f"{p}_fpr": float(v) for p, v in zip(PHASES, q["ew_fpr"])}, **q["ew"]})
                summary_rows.append({**base, "engines": len(engines), **summary_record(q),
                                     "worst_engine": engines[q["we_engine"]]})
            for arm in ("phase_conditioned", "quantile_regression_W"):
                s, p0 = per_arm[arm], per_arm["pooled"]
                diff_a2 = s["a2_e"] - p0["a2_e"]
                cats = [ma.category(s["per_engine"][i]["spread"] - p0["per_engine"][i]["spread"],
                                    diff_a2[i], s["per_engine"][i]["rms_error"] - p0["per_engine"][i]["rms_error"])
                        for i in range(len(engines))]
                paired_rows.append({
                    "subset": subset_key, "detector": name[0], "seed": name[1], "nominal_fpr": alpha, "arm": arm,
                    "engines": len(engines),
                    "diff_pooled_A1": s["pooled"]["spread"] - p0["pooled"]["spread"],
                    "diff_pooled_A2": s["pooled"]["max_abs_error"] - p0["pooled"]["max_abs_error"],
                    "diff_pooled_A3": s["pooled"]["rms_error"] - p0["pooled"]["rms_error"],
                    "diff_pooled_overall_fpr": s["pooled_overall"] - p0["pooled_overall"],
                    "diff_ME_A2": s["me_a2"] - p0["me_a2"], "diff_WE_A2": s["we_a2"] - p0["we_a2"],
                    "diff_EW_A2": s["ew"]["max_abs_error"] - p0["ew"]["max_abs_error"],
                    "n_worse": int(np.sum(diff_a2 > 0)), "n_better": int(np.sum(diff_a2 < 0)),
                    "uniform_improvement": bool(np.all(diff_a2 < 0)),
                    "pooled_category": ma.category(s["pooled"]["spread"] - p0["pooled"]["spread"],
                                                   s["pooled"]["max_abs_error"] - p0["pooled"]["max_abs_error"],
                                                   s["pooled"]["rms_error"] - p0["pooled"]["rms_error"]),
                    "engine_categories": ";".join(f"{e}:{c}" for e, c in zip(engines, cats))})
                for i, e in enumerate(engines):
                    engine_rows.append({"subset": subset_key, "detector": name[0], "seed": name[1],
                                        "nominal_fpr": alpha, "arm": arm, "unit": e,
                                        "pooled_arm_A2": float(p0["a2_e"][i]), "arm_A2": float(s["a2_e"][i]),
                                        "diff_A2": float(diff_a2[i]),
                                        "diff_A1": s["per_engine"][i]["spread"] - p0["per_engine"][i]["spread"],
                                        "diff_A3": s["per_engine"][i]["rms_error"] - p0["per_engine"][i]["rms_error"],
                                        "category": cats[i]})
            taus = entry["tau"]["phase_conditioned"]
            for i, cal_phase in enumerate(PHASES):
                alarm = values > taus[i]
                alarms, rows = cell_counts(alarm, units, phase, engines)
                for j, test_phase in enumerate(PHASES):
                    transfer_rows.append({"subset": subset_key, "detector": name[0], "seed": name[1],
                                          "nominal_fpr": alpha, "calibration_phase": cal_phase,
                                          "test_phase": test_phase, "unit": "all", "n": int(rows[:, j].sum()),
                                          "alarms": int(alarms[:, j].sum()),
                                          "rate": float(alarms[:, j].sum() / rows[:, j].sum())})
                    for k, e in enumerate(engines):
                        transfer_rows.append({"subset": subset_key, "detector": name[0], "seed": name[1],
                                              "nominal_fpr": alpha, "calibration_phase": cal_phase,
                                              "test_phase": test_phase, "unit": str(e), "n": int(rows[k, j]),
                                              "alarms": int(alarms[k, j]), "rate": float(alarms[k, j] / rows[k, j])})
    return {"phase_fpr": pd.DataFrame(rates), "calibration_quality": pd.DataFrame(quality_rows),
            "transport_summary": pd.DataFrame(summary_rows), "paired_transport": pd.DataFrame(paired_rows),
            "paired_transport_engines": pd.DataFrame(engine_rows), "transfer_matrix": pd.DataFrame(transfer_rows)}


# ---------------------------------------------------------------------------
# Flight-level, persistence and abnormal-state endpoints (I, J, K; P1-P5)
# ---------------------------------------------------------------------------

def audit_flights(meta):
    return mm.audit_flight_table(meta)


def persistence_and_flight_tables(subset_key, lock, scores, meta, q_thresholds, flights, cal_reference):
    """Per run x target x arm x rule: flight fractions, locked-kappa flags, FFR, events, TPR, delays, PA2."""
    starts, ends = flights.start.to_numpy(), flights.end.to_numpy()
    units, phase = meta.unit.to_numpy(), meta.phase_primary.to_numpy()
    healthy_row = meta.healthy.to_numpy() == 1
    k_row = np.repeat(flights.k.to_numpy(), flights.rows.to_numpy())
    post_row = k_row >= 0
    early_row = post_row & (k_row < EARLY)
    engines = sorted(int(u) for u in np.unique(units))
    flight_unit = flights.unit.to_numpy()
    healthy_flight = (flights.state == "healthy").to_numpy()
    trajectories, ffr_rows, abnormal_rows, delay_rows, pa_rows = [], [], [], [], []
    for name, values in scores.items():
        run = ec.run_name(*name)
        for alpha in ec.TARGETS:
            entry = lock["runs"][run][str(alpha)]
            for arm in ec.ARMS:
                exceed = values > arm_thresholds(entry, arm, phase, q_thresholds.get((name, alpha)))
                for rule in ec.RULES:
                    alarm = xc.apply_rule(exceed, starts, ends, rule)
                    base = {"subset": subset_key, "detector": name[0], "seed": name[1], "nominal_fpr": alpha,
                            "arm": arm, "rule": rule}
                    kap = entry["kappa"][arm][rule]
                    counts = mm.flight_alarm_counts(alarm, starts)
                    fraction = counts / (ends - starts)
                    events = xc.flight_events(alarm, starts, ends)
                    flagged = fraction > kap
                    trajectories.append(pd.DataFrame({
                        **base, "unit": flight_unit, "cycle": flights.cycle.to_numpy(), "state": flights.state.to_numpy(),
                        "k": flights.k.to_numpy(), "rows": ends - starts, "alarms": counts, "alarm_fraction": fraction,
                        "events": events, "kappa": kap, "flagged": flagged}))
                    for label, mask in [(str(e), (flight_unit == e) & healthy_flight) for e in engines] + [
                            ("all", healthy_flight)]:
                        ffr_rows.append({**base, "unit": label, "healthy_flights": int(mask.sum()),
                                         "flagged": int(flagged[mask].sum()),
                                         "false_flag_rate": float(flagged[mask].mean()),
                                         "any_alarm_fraction": float((counts[mask] > 0).mean()),
                                         "events_per_healthy_flight": float(events[mask].mean()), "kappa": kap})
                    for window, window_mask in (("all_post_onset", post_row), ("early_first_10", early_row)):
                        for label, mask in [(str(e), window_mask & (units == e)) for e in engines] + [
                                ("all", window_mask)]:
                            abnormal_rows.append({**base, "window": window, "unit": label, "n": int(mask.sum()),
                                                  "alarms": int(alarm[mask].sum()),
                                                  "rate": float(alarm[mask].mean()) if mask.any() else float("nan")})
                    for e in engines:
                        post = np.flatnonzero((flight_unit == e) & ~healthy_flight)
                        post = post[np.argsort(flights.k.to_numpy()[post])]
                        series = flagged[post]
                        d1, d3 = mm.first_flag(series), mm.persistence_flag(series)
                        h = flagged[(flight_unit == e) & healthy_flight]
                        delay_rows.append({**base, "unit": e, "post_onset_flights": int(len(post)),
                                           "delay_flights": d1 if np.isfinite(d1) else float("nan"),
                                           "censored": bool(np.isinf(d1)),
                                           "two_flight_persistence_delay": d3 if np.isfinite(d3) else float("nan"),
                                           "healthy_flights": int(len(h)), "healthy_flagged": int(h.sum()),
                                           **{f"detected_within_{d}": bool(np.isfinite(d1) and d1 <= d)
                                              for d in DETECTED_WITHIN}, "kappa": kap})
                    r_cal = cal_reference[(run, alpha, arm, rule)]
                    alarms_c, rows_c = cell_counts(alarm[healthy_row], units[healthy_row], phase[healthy_row], engines)
                    rate = alarms_c / rows_c
                    pa2 = (np.abs(rate - r_cal).max(axis=1) / r_cal) if r_cal > 0 else np.full(len(engines), np.nan)
                    for i, e in enumerate(engines):
                        pa_rows.append({**base, "unit": e, "calibration_reference_rate": r_cal,
                                        **{f"{p}_persistent_rate": float(rate[i, j]) for j, p in enumerate(PHASES)},
                                        "PA2": float(pa2[i])})
    return {"flight_trajectories": pd.concat(trajectories, ignore_index=True),
            "flight_false_flags": pd.DataFrame(ffr_rows), "abnormal_alarm_rates": pd.DataFrame(abnormal_rows),
            "detection_delay": pd.DataFrame(delay_rows), "persistence_calibration": pd.DataFrame(pa_rows)}


def calibration_reference(lock_cal, scores, meta, q_thresholds, starts, ends):
    """Calibration-side quantities recomputed from locked thresholds (verification and PA2 reference)."""
    phase = meta.phase_primary.to_numpy()
    reference, fractions = {}, {}
    for name, values in scores.items():
        run = ec.run_name(*name)
        for alpha in ec.TARGETS:
            entry = lock_cal["runs"][run][str(alpha)]
            for arm in ec.ARMS:
                exceed = values > arm_thresholds(entry, arm, phase, q_thresholds.get((name, alpha)))
                for rule in ec.RULES:
                    alarm = xc.apply_rule(exceed, starts, ends, rule)
                    reference[(run, alpha, arm, rule)] = float(alarm.mean())
                    fractions[(run, alpha, arm, rule)] = xc.flight_fraction(alarm, starts, ends)
    return reference, fractions


# ---------------------------------------------------------------------------
# Matched operating points (frozen Part B per arm and rule)
# ---------------------------------------------------------------------------

def matched_tables(subset_key, trajectories, cal_fractions, lock):
    engines = sorted(int(u) for u in trajectories.unit.unique())
    healthy = trajectories[(trajectories.state == "healthy")]
    counts = healthy.groupby(["detector", "seed", "nominal_fpr", "arm", "rule"]).size()
    n_healthy = int(counts.iloc[0])
    if not (counts == n_healthy).all():
        raise ec.ExtensionError("Healthy audit flight count differs across runs")
    point_tables, matched, locked_rows, curve_rows = [], [], [], []
    for (detector, seed, alpha, rule), part in trajectories.groupby(["detector", "seed", "nominal_fpr", "rule"],
                                                                     sort=False):
        run = ec.run_name(detector, seed)
        points = {}
        for arm in ec.ARMS:
            arm_part = part[part.arm == arm]
            kappas, sources = ma.candidate_kappas(cal_fractions[(run, alpha, arm, rule)])
            curve = ma.operating_characteristic(arm_part, kappas, sources, engines)
            base = {"subset": subset_key, "detector": detector, "seed": seed, "nominal_fpr": alpha, "arm": arm,
                    "rule": rule}
            points[arm] = ma.distinct_points(curve, engines)
            point_tables.append(points[arm][["ffr", "median_delay", "engines_censored", "kappa_low", "kappa_high"]
                                            + [f"detected_within_{d}" for d in DETECTED_WITHIN]].assign(**base))
            kap = lock["runs"][run][str(alpha)]["kappa"][arm][rule]
            locked = ma.operating_characteristic(arm_part, np.array([kap]), ["locked"], engines).iloc[0]
            mean_delay, excluded = ma.curve_mean(points[arm], n_healthy)
            locked_rows.append({**base, "kappa_locked": kap, "ffr": float(locked.ffr),
                                "median_delay": float(locked.median_delay),
                                "engines_censored": int(locked.engines_censored),
                                **{f"delay_engine_{u}": float(locked[f"delay_engine_{u}"]) for u in engines},
                                **{f"ffr_engine_{u}": float(locked[f"ffr_engine_{u}"]) for u in engines}})
            curve_rows.append({**base, "curve_mean_median_delay_ffr_2.5_to_20": mean_delay,
                               "curve_grid_points_excluded": excluded, "curve_grid_points": len(ma.CURVE_GRID)})
        for arm in ("phase_conditioned", "quantile_regression_W"):
            for match_rule in ("nearest", "not_exceeding"):
                for anchor in ma.ANCHORS:
                    p_point, p_ok = ma.match_anchor(points["pooled"], anchor, n_healthy, match_rule)
                    a_point, a_ok = ma.match_anchor(points[arm], anchor, n_healthy, match_rule)
                    row = {"subset": subset_key, "detector": detector, "seed": seed, "nominal_fpr": alpha,
                           "rule": rule, "arm": arm, "match_rule": match_rule, "anchor_ffr": anchor,
                           "healthy_flights": n_healthy, "supported": bool(p_ok and a_ok)}
                    if p_point is not None and a_point is not None:
                        row.update({"pooled_ffr": float(p_point.ffr), "arm_ffr": float(a_point.ffr),
                                    **ma.paired_delay(a_point, p_point, engines),
                                    "pooled_engines_censored": int(p_point.engines_censored),
                                    "arm_engines_censored": int(a_point.engines_censored)})
                    matched.append(row)
    matched = pd.DataFrame(matched)
    curve = pd.DataFrame(curve_rows)
    labels = []
    for keys, part in matched[matched.match_rule == "nearest"].groupby(
            ["detector", "seed", "nominal_fpr", "rule", "arm"], sort=False):
        detector, seed, alpha, rule, arm = keys
        supported = part[part.supported]
        conservative = matched[(matched.match_rule == "not_exceeding") & (matched.detector == detector)
                               & (matched.seed == seed) & (matched.nominal_fpr == alpha) & (matched.rule == rule)
                               & (matched.arm == arm) & matched.supported]
        cv = curve[(curve.detector == detector) & (curve.seed == seed) & (curve.nominal_fpr == alpha)
                   & (curve.rule == rule)]
        arm_curve = float(cv[cv.arm == arm].iloc[0]["curve_mean_median_delay_ffr_2.5_to_20"])
        pooled_curve = float(cv[cv.arm == "pooled"].iloc[0]["curve_mean_median_delay_ffr_2.5_to_20"])
        labels.append({"subset": subset_key, "detector": detector, "seed": seed, "nominal_fpr": alpha, "rule": rule,
                       "arm": arm, "supported_anchors": int(len(supported)),
                       "evaluable": bool(len(supported) >= 3),
                       "matched_label": ma.run_label_from_differences(
                           list(supported.paired_lower_median_difference.astype(float))),
                       "matched_label_not_exceeding": ma.run_label_from_differences(
                           list(conservative.paired_lower_median_difference.astype(float))),
                       "curve_mean_pooled": pooled_curve, "curve_mean_arm": arm_curve,
                       "curve_mean_difference": (arm_curve - pooled_curve if np.isfinite(arm_curve)
                                                 and np.isfinite(pooled_curve) else float("nan"))})
    return {"matched_operating_points": pd.concat(point_tables, ignore_index=True),
            "matched_comparisons": matched, "matched_labels": pd.DataFrame(labels),
            "locked_operating_points": pd.DataFrame(locked_rows), "curve_level_summary": curve}


# ---------------------------------------------------------------------------
# Composition evaluation (locked design thresholds applied to healthy audit rows)
# ---------------------------------------------------------------------------

def composition_tables(subset_key, lock, scores, meta):
    comp = lock.get("composition")
    if not comp:
        return {}
    engines = sorted(int(u) for u in np.unique(meta.unit))
    units, phase = meta.unit.to_numpy(), meta.phase_primary.to_numpy()
    rows = []
    for name, values in scores.items():
        run = ec.run_name(*name)
        order = np.argsort(values, kind="stable")
        sorted_values = values[order]
        cells = (np.searchsorted(engines, units) * 3 + phase)[order]
        n_cells = len(engines) * 3
        size = np.bincount(cells, minlength=n_cells)
        for key, taus in comp["thresholds"][run].items():
            design, draw, alpha = key.split("|")
            for arm in ("pooled", "phase_conditioned"):
                if arm == "pooled":
                    above = size - np.bincount(cells[:np.searchsorted(sorted_values, taus["pooled"], side="right")],
                                               minlength=n_cells)
                else:
                    above = np.zeros(n_cells)
                    for j in range(3):
                        cut = np.searchsorted(sorted_values, taus["phase_conditioned"][j], side="right")
                        below = np.bincount(cells[:cut], minlength=n_cells)
                        above[j::3] = (size - below)[j::3]
                q = quality_from_counts(above.reshape(-1, 3).astype(float), size.reshape(-1, 3).astype(float),
                                        float(alpha))
                base = {"subset": subset_key, "detector": name[0], "seed": name[1], "design": design,
                        "draw": int(draw), "nominal_fpr": float(alpha), "arm": arm}
                rows.append({**base, "unit": "summary", **summary_record(q)})
                for i, e in enumerate(engines):
                    rows.append({**base, "unit": str(e), "A1": q["per_engine"][i]["spread"],
                                 "A2": q["per_engine"][i]["max_abs_error"], "A3": q["per_engine"][i]["rms_error"],
                                 **{f"{p}_fpr": float(v) for p, v in zip(PHASES, q["fpr_e"][i])}})
    return {"composition_metrics": pd.DataFrame(rows)}


# ---------------------------------------------------------------------------
# U-EXT1: per-subset engine -> flight bootstrap with re-estimated P and C thresholds
# ---------------------------------------------------------------------------

class BootstrapRun:
    def __init__(self, cal_scores, cal_phase, cal_flights, test_scores, test_phase, test_flights):
        self.views = [mm.sorted_view(cal_scores, None, cal_flights)] + [
            mm.sorted_view(cal_scores, cal_phase, cal_flights, i) for i in range(3)]
        n_flights = len(test_flights)
        flight_of_row = np.empty(len(test_scores), dtype=np.int64)
        for fid, (_, _, index) in enumerate(test_flights):
            flight_of_row[index] = fid
        cells = flight_of_row * 3 + test_phase.astype(np.int64)
        self.counter = mm.CellCounter(test_scores, cells, n_flights * 3)
        self.cell_flight = np.arange(n_flights * 3) // 3
        self.cell_phase = np.arange(n_flights * 3) % 3
        self.sizes = self.counter.sizes.astype(np.float64)

    def taus(self, multiplicity, q):
        values = [fv.weighted_higher_quantile(*view, multiplicity, q) for view in self.views]
        return values[0], np.asarray(values[1:])

    def replicate(self, cal_multiplicity, test_multiplicity, alpha, flight_engine, n_engines, engine_times):
        pooled_tau, phase_tau = self.taus(cal_multiplicity, 1 - alpha)
        weight = test_multiplicity[self.cell_flight].astype(np.float64)
        engine_phase = flight_engine[self.cell_flight] * 3 + self.cell_phase
        rows_e = np.bincount(engine_phase, weights=weight * self.sizes, minlength=n_engines * 3).reshape(n_engines, 3)
        drawn = engine_times > 0
        out = {}
        for arm, thresholds in (("pooled", np.full(len(self.cell_phase), pooled_tau)),
                                ("phase_conditioned", phase_tau[self.cell_phase])):
            above = self.counter.above(thresholds)
            alarms_e = np.bincount(engine_phase, weights=weight * above, minlength=n_engines * 3).reshape(n_engines, 3)
            pooled_fpr = alarms_e.sum(axis=0) / rows_e.sum(axis=0)
            pooled = errors(pooled_fpr, alarms_e.sum() / rows_e.sum(), alpha)
            fpr_e = alarms_e[drawn] / rows_e[drawn]
            times = engine_times[drawn]
            a2_e = np.abs(fpr_e - alpha).max(axis=1)
            ew_fpr = (times[:, None] * fpr_e).sum(axis=0) / times.sum()
            out[f"{arm}.pooled_A1"] = pooled["spread"]
            out[f"{arm}.pooled_A2"] = pooled["max_abs_error"]
            out[f"{arm}.pooled_A3"] = pooled["rms_error"]
            out[f"{arm}.pooled_overall_fpr"] = alarms_e.sum() / rows_e.sum()
            out[f"{arm}.ME_A2"] = float((times * a2_e).sum() / times.sum())
            out[f"{arm}.WE_A2"] = float(a2_e.max())
            out[f"{arm}.EW_A2"] = float(np.abs(ew_fpr - alpha).max())
        for metric in ("pooled_A1", "pooled_A2", "pooled_A3", "pooled_overall_fpr", "ME_A2", "WE_A2", "EW_A2"):
            out[f"diff_{metric}"] = out[f"phase_conditioned.{metric}"] - out[f"pooled.{metric}"]
        return out


def _bootstrap_worker(args):
    (name, cal_scores, cal_phase, cal_flights, test_scores, test_phase, test_flights, cal_plans, test_plans,
     flight_engine, n_engines, engine_times_all) = args
    run = BootstrapRun(cal_scores, cal_phase, cal_flights, test_scores, test_phase, test_flights)
    ones_cal = np.ones(len(cal_flights), dtype=np.int64)
    ones_test = np.ones(len(test_flights), dtype=np.int64)
    results = {}
    for alpha in ec.TARGETS:
        point = run.replicate(ones_cal, ones_test, alpha, flight_engine, n_engines, np.ones(n_engines))
        records = [run.replicate(cal_plans[b], test_plans[b], alpha, flight_engine, n_engines, engine_times_all[b])
                   for b in range(len(cal_plans))]
        results[alpha] = (point, records)
    return name, results


def bootstrap_uext1(subset_key, cal_scores, cal_meta, test_scores, test_meta, replicates=ec.BOOTSTRAP_REPLICATES,
                    workers=10):
    rng = np.random.default_rng(ec.UEXT1_SEED)
    cal_flights, cal_plans = fv.bootstrap_plans(cal_meta, replicates, rng)
    test_flights, test_plans = fv.bootstrap_plans(test_meta, replicates, rng)
    ones = np.ones(len(test_flights), dtype=np.int64)
    _, flight_engine = ma.engine_weights(test_flights, ones)
    n_engines = int(flight_engine.max()) + 1
    engine_times_all = [ma.engine_weights(test_flights, test_plans[b])[0] for b in range(replicates)]
    cal_phase, test_phase = cal_meta.phase_primary.to_numpy(), test_meta.phase_primary.to_numpy()
    args = [(name, cal_scores[name], cal_phase, cal_flights, test_scores[name], test_phase, test_flights,
             cal_plans, test_plans, flight_engine, n_engines, engine_times_all) for name in cal_scores]
    summary, replicate_rows = [], []
    context = multiprocessing.get_context("spawn")  # never fork a multi-threaded CUDA process
    with ProcessPoolExecutor(max_workers=min(workers, len(args)), mp_context=context) as pool:
        for name, results in pool.map(_bootstrap_worker, args):
            for alpha, (point, records) in results.items():
                for row in mm.summarize_replicates(records):
                    summary.append({"subset": subset_key, "detector": name[0], "seed": name[1],
                                    "nominal_fpr": alpha, "bootstrap_unit": "engine_then_flight (U-EXT1)",
                                    "threshold_reestimated": True, "point_estimate": point[row["metric"]], **row})
                if alpha == ec.PRIMARY_TARGET:
                    for b, record in enumerate(records):
                        replicate_rows.append({"subset": subset_key, "detector": name[0], "seed": name[1],
                                               "replicate": b, **{k: record[k] for k in (
                                                   "pooled.ME_A2", "phase_conditioned.ME_A2", "pooled.pooled_A1",
                                                   "pooled.pooled_A2", "diff_pooled_A1", "diff_pooled_A2",
                                                   "diff_ME_A2", "diff_WE_A2", "pooled.WE_A2")}})
    return pd.DataFrame(summary), pd.DataFrame(replicate_rows)
