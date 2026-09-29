"""Post hoc checks prompted by the internal hostile review (docs/extension/EXTENSION_HOSTILE_REVIEW.md).

These analyses were NOT pre-specified. They were computed after all outcomes, from committed extension outputs
only (results/extension/), to answer reviewer questions. They re-open no official-test array, fit nothing, and
change no pre-specified decision (results/extension/summary/decisions.json stands as recorded).

New cohort, residual runs (PCA, IF seeds 0-2, LSTM seeds 0-2), alpha = 1%, locked thresholds:
1. Worst-engine healthy-flight false-flag rate (WE-FFR) under perfect calibration: each audit engine's healthy
   flights flagged independently with probability p, where p = 0.05 exactly or p ~ Beta(n - k + 1, k) for the
   empirical 'higher' 0.95 quantile of n exchangeable calibration flights (k = ceil(0.95 n)).
2. Approximate per-engine noise floor for A2: each phase FPR equal to alpha, with a binomial standard error
   inflated by the engine's flight-clustered design effect, estimated from its per-flight alarm counts at the
   locked threshold (R0). Conservative, because the design effect includes true between-flight variation.
3. Signed worst-phase errors (over- vs under-alarming) of material per-engine errors (A2 >= 0.5 alpha).
4. Engine-level improvement of C and Q over P: mean share of engines improved per cell, against the
   coin-flip expectation for 'every engine improved'.
5. Flight-level attribution of the largest covered-class failure (DS08a engine 14) and the calibration altitude
   envelope (healthy-flight altitude span from the metadata audit).
6. Class-balanced design against the best (not only the mean) single-engine design.
7. A two-consecutive-flight confirmation rule at the locked kappa (not pre-specified): worst-engine healthy
   confirmed-alert rate and median delay (pipeline column two_flight_persistence_delay).
8. Early abnormal-state sensitivity: row alarm rate over the first 10 post-onset flights under P.
9. Recorded-mission sharing between audit engines and calibration engines of the same or another class
   (healthy-flight signatures from the metadata audit, docs/extension/profile_sharing_engine_pairs.csv).
10. CVAE mean per-engine error against the median (not only the best) residual detector family.
11. Design-based probability that an engine-level bootstrap replicate of the calibration pool omits a class.
12. Coverage effect by audit-engine class, and DS04 runs in which every audit engine stayed within 0.5 alpha.

Output: paper/mssp_extended/evidence/post_hoc_checks.json (summary) and post_hoc_engine_noise.csv.
"""

from __future__ import annotations

import json
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "results/extension"
OUT = ROOT / "paper/mssp_extended/evidence"
NEW = ("DS01", "DS04", "DS05", "DS06", "DS07", "DS08a", "DS08c")
FAMILY = {"DS01": "F1", "DS04": "F2", "DS05": "F3", "DS06": "F3", "DS07": "F3", "DS08a": "F4", "DS08c": "F5"}
PHASES = ("climb", "cruise", "descent")
ARMS = ("pooled", "phase_conditioned", "quantile_regression_W")
ALPHA = 0.01
DRAWS = 200_000
SEED = 20260930


def audit(key, table):
    return pd.read_csv(EXT / key / "audit" / f"{table}.csv", float_precision="round_trip")


def residual(frame):
    return frame[(frame.detector != "cvae") & (frame.nominal_fpr == ALPHA)]


def we_ffr_null(rng):
    locks = pd.read_csv(EXT / "summary/numerical_audit_locks.csv").set_index("subset")
    rows = []
    for key in NEW:
        ff = residual(audit(key, "flight_false_flags"))
        ff = ff[(ff.arm == "pooled") & (ff.unit.astype(str) != "all")]  # engines only, not the fleet aggregate
        flights = ff[(ff.rule == "R0") & (ff.detector == "pca")].set_index("unit").healthy_flights
        n_cal = int(locks.loc[key, "calibration_flights"])
        k = ceil(0.95 * n_cal)
        p = rng.beta(n_cal - k + 1, k, size=DRAWS)
        worst = np.max(np.stack([rng.binomial(int(n), p) / n for n in flights.values]), axis=0)
        exact = np.max(np.stack([rng.binomial(int(n), 0.05, size=DRAWS) / n for n in flights.values]), axis=0)
        row = {"subset": key, "family": FAMILY[key], "engines": int(len(flights)), "flights_min": int(flights.min()),
               "flights_max": int(flights.max()), "calibration_flights": n_cal,
               "null_median": float(np.median(worst)), "null_q95": float(np.quantile(worst, 0.95)),
               "null_p_ge_10pct": float((worst >= 0.10).mean()), "null_exact_median": float(np.median(exact)),
               "null_exact_p_ge_10pct": float((exact >= 0.10).mean())}
        for rule in ("R0", "R1", "R2"):
            w = ff[ff.rule == rule].groupby(["detector", "seed"]).false_flag_rate.max()
            row[f"observed_median_{rule}"] = float(w.median())
            row[f"observed_share_ge_10pct_{rule}"] = float((w >= 0.10).mean())
            row[f"observed_share_above_null_q95_{rule}"] = float((w > np.quantile(worst, 0.95)).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def a2_noise(rng):
    rows = []
    for key in NEW:
        tr = residual(audit(key, "flight_trajectories"))
        tr = tr[(tr.rule == "R0") & (tr.state == "healthy")]
        ph = residual(audit(key, "phase_fpr"))
        ph = ph[(ph.unit != "all") & ph.phase.isin(PHASES)].copy()
        ph["unit"] = ph.unit.astype(int)
        for (det, seed, arm), g in tr.groupby(["detector", "seed", "arm"]):
            for unit, e in g.groupby("unit"):
                n, a = e.rows.to_numpy(float), e.alarms.to_numpy(float)
                flights, p = len(n), a.sum() / n.sum()
                se_cluster = np.sqrt(flights / (flights - 1) * np.sum((a - p * n) ** 2)) / n.sum()
                deff = (se_cluster / np.sqrt(max(p, 1e-12) * (1 - p) / n.sum())) ** 2
                pe = ph[(ph.detector == det) & (ph.seed == seed) & (ph.arm == arm) & (ph.unit == unit)].set_index("phase")
                pe = pe.loc[list(PHASES)]
                se_phase = np.sqrt(deff * ALPHA * (1 - ALPHA) / pe.n.to_numpy(float))
                null = np.abs(rng.standard_normal((20_000, 3)) * se_phase).max(axis=1)
                signed = pe.rate.to_numpy(float) - ALPHA
                worst = int(np.argmax(np.abs(signed)))
                rows.append({"subset": key, "family": FAMILY[key], "detector": det, "seed": int(seed), "arm": arm,
                             "unit": int(unit), "healthy_flights": flights, "design_effect": deff,
                             "se_overall_fpr": se_cluster, "null_A2_median": float(np.median(null)),
                             "null_A2_q95": float(np.quantile(null, 0.95)),
                             "null_p_material": float((null >= 0.5 * ALPHA).mean()),
                             "observed_A2": float(abs(signed[worst])), "worst_phase": PHASES[worst],
                             "worst_sign": "over" if signed[worst] > 0 else "under"})
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {"status": "post hoc; prompted by the internal hostile review; descriptive; pre-specified decisions unchanged",
               "alpha": ALPHA, "runs": "new cohort, residual runs (7 per subset)", "seed": SEED}

    null = we_ffr_null(rng)
    summary["we_ffr_null"] = null.to_dict(orient="records")
    summary["we_ffr_null_range"] = {"median_min": float(null.null_median.min()), "median_max": float(null.null_median.max()),
                                    "p_ge_10pct_min": float(null.null_p_ge_10pct.min()),
                                    "p_ge_10pct_max": float(null.null_p_ge_10pct.max())}

    noise = a2_noise(rng)
    noise.to_csv(OUT / "post_hoc_engine_noise.csv", index=False)
    by_arm = {}
    for arm, g in noise.groupby("arm"):
        material = g[g.observed_A2 >= 0.5 * ALPHA]
        by_arm[arm] = {"engine_runs": int(len(g)), "null_p_material_mean": float(g.null_p_material.mean()),
                       "observed_share_material": float((g.observed_A2 >= 0.5 * ALPHA).mean()),
                       "observed_share_above_null_q95": float((g.observed_A2 > g.null_A2_q95).mean()),
                       "null_A2_median_median": float(g.null_A2_median.median()),
                       "se_overall_fpr_median": float(g.se_overall_fpr.median()),
                       "material_share_under_alarming": float((material.worst_sign == "under").mean())}
    summary["a2_noise_by_arm"] = by_arm
    summary["a2_noise_by_subset_pooled"] = {
        k: {"null_p_material_mean": float(g.null_p_material.mean()),
            "observed_share_above_null_q95": float((g.observed_A2 > g.null_A2_q95).mean()),
            "material_share_under_alarming": float((g[g.observed_A2 >= 0.5 * ALPHA].worst_sign == "under").mean())}
        for k, g in noise[noise.arm == "pooled"].groupby("subset")}
    summary["se_overall_fpr_range"] = {"min": float(noise.se_overall_fpr.quantile(0.05)),
                                       "max": float(noise.se_overall_fpr.quantile(0.95))}

    pt = pd.concat([residual(audit(k, "paired_transport")).assign(subset=k) for k in NEW])
    pt_all = pd.concat([audit(k, "paired_transport").assign(subset=k) for k in NEW])
    pt_all = pt_all[pt_all.nominal_fpr == ALPHA]
    summary["engine_improvement"] = {
        arm: {"mean_share_engines_improved": float((g.n_better / g.engines).mean()),
              "share_cells_every_engine_improved": float(g.uniform_improvement.mean()),
              "coin_flip_expectation": float((0.5 ** g.engines).mean()), "cells": int(len(g))}
        for arm, g in pt_all.groupby("arm")}
    summary["engine_improvement_residual"] = {
        arm: {"mean_share_engines_improved": float((g.n_better / g.engines).mean()), "cells": int(len(g))}
        for arm, g in pt.groupby("arm")}

    tr = residual(audit("DS08a", "flight_trajectories"))
    t = tr[(tr.rule == "R0") & (tr.state == "healthy") & (tr.arm == "pooled") & (tr.unit == 14)]
    per_flight = t.groupby("cycle").agg(rows=("rows", "first"), alarms=("alarms", "median"))
    top = int(per_flight.alarms.idxmax())
    rest = per_flight.drop(index=top)
    seg_all = pd.read_csv(EXT / "metadata/healthy_flight_phase_segments.csv")
    seg = seg_all[seg_all.dataset == "DS08a"]
    roles = json.loads((EXT / "DS08a/lock/calibration_lock.json").read_text())["roles"]
    span = seg.set_index(["unit", "cycle"]).altitude_span
    cal_max = float(seg[seg.unit.isin(roles["calibration"])].altitude_span.max())
    summary["ds08a_engine14"] = {
        "flight": top, "healthy_flights": int(len(per_flight)), "share_of_healthy_alarms": float(per_flight.alarms[top] / per_flight.alarms.sum()),
        "fpr_all_flights": float(per_flight.alarms.sum() / per_flight.rows.sum()),
        "fpr_without_flight": float(rest.alarms.sum() / rest.rows.sum()),
        "flight_altitude_span_ft": float(span[(14, top)]),
        "fit_max_altitude_span_ft": float(seg[seg.unit.isin(roles["fit"])].altitude_span.max()),
        "calibration_max_altitude_span_ft": cal_max,
        "audit_flights_above_calibration_span": int((seg[(seg.split == "test")].altitude_span > cal_max).sum()),
        "note": "median over the 7 residual runs of per-flight healthy alarms under P at alpha = 1% (R0)"}

    runs = pd.read_csv(EXT / "summary/composition_run_summary.csv")
    runs = runs[runs.subset.isin(NEW) & (runs.detector != "cvae")]
    summary["balanced_design"] = {
        arm: {"residual_runs": int(len(g)), "better_than_mean_single": int((g.CE2_balanced_minus_mean_single < 0).sum()),
              "better_than_best_single": int((g.CE2_balanced_minus_best_single < 0).sum())}
        for arm, g in runs.groupby("arm")}

    confirm = {}
    for arm in ARMS:
        rows = []
        for key in NEW:
            trk = residual(audit(key, "flight_trajectories"))
            trk = trk[(trk.rule == "R0") & (trk.arm == arm) & (trk.state == "healthy")].sort_values(["detector", "seed", "unit", "cycle"])
            dd = residual(audit(key, "detection_delay"))
            dd = dd[(dd.rule == "R0") & (dd.arm == arm)]
            for (det, seed), g in trk.groupby(["detector", "seed"]):
                single, two = [], []
                for _, e in g.groupby("unit"):
                    f = e.flagged.to_numpy(bool)
                    single.append(f.mean())
                    two.append((f[1:] & f[:-1]).mean() if len(f) > 1 else 0.0)
                d = dd[(dd.detector == det) & (dd.seed == seed)]
                rows.append({"we_single": max(single), "we_two": max(two), "delay_single": float(d.delay_flights.median()),
                             "delay_two": float(d.two_flight_persistence_delay.median()),
                             "censored_two": int(d.two_flight_persistence_delay.isna().sum())})
        frame = pd.DataFrame(rows)
        confirm[arm] = {"residual_runs": int(len(frame)), "we_single_median": float(frame.we_single.median()),
                        "we_single_ge_10pct": int((frame.we_single >= 0.10).sum()),
                        "we_two_median": float(frame.we_two.median()), "we_two_zero": int((frame.we_two == 0).sum()),
                        "we_two_ge_10pct": int((frame.we_two >= 0.10).sum()),
                        "median_delay_single": float(frame.delay_single.median()),
                        "median_delay_two": float(frame.delay_two.median()), "censored_engines_two": int(frame.censored_two.sum())}
    summary["two_flight_confirmation"] = confirm

    ab = pd.concat([residual(audit(k, "abnormal_alarm_rates")).assign(subset=k) for k in NEW])
    ab = ab[(ab.rule == "R0") & (ab.arm == "pooled") & (ab.window == "early_first_10")]
    rates = ab.groupby(["subset", "detector", "seed"]).apply(lambda x: x.alarms.sum() / x.n.sum())
    summary["early_sensitivity_pooled"] = {"min": float(rates.min()), "median": float(rates.median()), "max": float(rates.max())}

    pairs = pd.read_csv(ROOT / "docs/extension/profile_sharing_engine_pairs.csv")
    pairs = pairs[pairs.same_dataset]
    share = []
    for key in NEW:
        roles_k = json.loads((EXT / key / "lock/calibration_lock.json").read_text())["roles"]
        cls = roles_k["classes"]
        for unit in roles_k["audit"]:
            for cal in roles_k["calibration"]:
                m = pairs[(pairs.dataset_a == key) & (((pairs.unit_a == unit) & (pairs.unit_b == cal)) |
                                                      ((pairs.unit_a == cal) & (pairs.unit_b == unit)))]
                flights = int(seg_all[(seg_all.dataset == key) & (seg_all.unit == unit)].shape[0])
                shared = int(m.shared_flight_signatures.iloc[0]) if len(m) else 0
                share.append({"subset": key, "audit_class": cls[str(unit)], "same_class": cls[str(unit)] == cls[str(cal)],
                              "share": shared / flights})
    share = pd.DataFrame(share)
    same = share[share.same_class]
    summary["mission_sharing"] = {
        "same_class_by_audit_class": {int(c): {"min": float(g.share.min()), "max": float(g.share.max())}
                                      for c, g in same.groupby("audit_class")},
        "other_class_max": float(share[~share.same_class].share.max())}

    ts = pd.read_csv(EXT / "summary/transport_summary_alpha_0.01.csv")
    fam = ts[(ts.arm == "pooled") & ts.subset.isin(NEW)].groupby(["subset", "detector"]).ME_A2.mean().unstack()
    resid = fam[["pca", "isolation_forest", "lstm_autoencoder"]]
    vs_best = (fam.cvae - resid.min(axis=1)).groupby(lambda k: FAMILY[k]).mean()
    vs_median = (fam.cvae - resid.median(axis=1)).groupby(lambda k: FAMILY[k]).mean()
    summary["cvae_vs_residual"] = {"median_over_families_vs_best": float(vs_best.median()),
                                   "median_over_families_vs_median": float(vs_median.median()),
                                   "family_vs_median": {f: float(v) for f, v in vs_median.items()}}

    from itertools import product
    drop = {}
    for key in NEW:
        roles_k = json.loads((EXT / key / "lock/calibration_lock.json").read_text())["roles"]
        cls = [roles_k["classes"][str(u)] for u in roles_k["calibration"]]
        n = len(cls)
        drop[key] = sum({cls[i] for i in s} != set(cls) for s in product(range(n), repeat=n)) / n ** n
    summary["bootstrap_class_omission_probability"] = drop

    eff = pd.read_csv(EXT / "summary/composition_engine_effects.csv")
    eff = eff[eff.subset.isin(NEW) & (eff.detector != "cvae")]
    per_engine = eff.groupby(["subset", "arm", "unit", "flight_class"]).delta_cov.median().reset_index()
    summary["coverage_by_audit_class"] = {arm: {int(c): float(v) for c, v in g.groupby("flight_class").delta_cov.median().items()}
                                          for arm, g in per_engine.groupby("arm")}

    pe = residual(audit("DS04", "paired_transport_engines"))
    within = {}
    for arm in ("phase_conditioned", "quantile_regression_W"):
        g = pe[pe.arm == arm].groupby(["detector", "seed"])
        within[arm] = int(g.apply(lambda x: bool((x.arm_A2 < 0.5 * ALPHA).all())).sum())
    within["pooled"] = int(pe[pe.arm == "phase_conditioned"].groupby(["detector", "seed"]).apply(
        lambda x: bool((x.pooled_arm_A2 < 0.5 * ALPHA).all())).sum())
    summary["ds04_runs_every_engine_within_material_line"] = within

    (OUT / "post_hoc_checks.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("we_ffr_null",)}, indent=1)[:6000])


if __name__ == "__main__":
    main()
