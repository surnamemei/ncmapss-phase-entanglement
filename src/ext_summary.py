"""Cross-dataset summaries and pre-specified decisions (protocol sections 11.2, 11.3 and 13-16, with Amendment 1).

Written and committed before any new-subset outcome existed. Every decision is a mechanical count rule
on committed per-subset tables. Nothing is significance-tested.
"""

from __future__ import annotations

import json
from collections import Counter

import numpy as np
import pandas as pd

import ext_common as ec

ALPHA = ec.PRIMARY_TARGET
MATERIAL = 0.5 * ALPHA
NEW_FAMILIES = ("F1", "F2", "F3", "F4", "F5")
COMPOSITION_FAMILIES = ("F1", "F2", "F3", "F4")
RESIDUAL_FAMILIES = ("pca", "isolation_forest", "lstm_autoencoder")
WE_FFR_PROBLEM = 0.10
PA2_MATERIAL = 0.5


def read(key, table):
    return pd.read_csv(ec.RESULTS / key / "audit" / f"{table}.csv")


def read_lock(key):
    return json.loads((ec.RESULTS / key / "lock" / "calibration_lock.json").read_text(encoding="utf-8"))


def stack(table, keys):
    return pd.concat([read(k, table) for k in keys], ignore_index=True)


def family_holds(subset_flags):
    """A family holds a statement if a strict majority of its subsets do."""
    by_family = {}
    for subset, flag in subset_flags.items():
        by_family.setdefault(ec.FAMILIES[subset], []).append(bool(flag))
    return {f: sum(v) > len(v) / 2 for f, v in by_family.items()}


def count_families(subset_flags, families=NEW_FAMILIES):
    held = family_holds(subset_flags)
    return int(sum(held.get(f, False) for f in families)), held


def seed_mean(frame, value, keys=("subset", "detector")):
    return frame.groupby(list(keys))[value].mean()


# ---------------------------------------------------------------------------
# H1-H3, H5-H7 and the original-story components
# ---------------------------------------------------------------------------

def primary_tables(keys):
    ts = stack("transport_summary", keys)
    paired = stack("paired_transport", keys)
    return ts[ts.nominal_fpr == ALPHA], paired[paired.nominal_fpr == ALPHA]


def h1(ts, keys):
    pooled = ts[ts.arm == "pooled"]
    means = seed_mean(pooled, "pooled_A2")
    holds, detail = {}, {}
    for key in keys:
        values = {fam: float(means[(key, fam)]) for fam in RESIDUAL_FAMILIES}
        holds[key] = all(v >= MATERIAL for v in values.values())
        detail[key] = values
    n, fam = count_families(holds)
    verdict = "SUPPORTED" if n >= 3 else ("WEAK" if n >= 1 else "NOT SUPPORTED")
    ordering = []
    for row in pooled.itertuples(index=False):
        fprs = {p: getattr(row, f"pooled_{p}_fpr") for p in ("climb", "cruise", "descent")}
        ordering.append({"subset": row.subset, "detector": row.detector, "seed": row.seed,
                         "highest_phase": max(fprs, key=fprs.get), "lowest_phase": min(fprs, key=fprs.get), **fprs})
    return {"verdict": verdict, "families_holding": n, "family_holds": fam, "subset_holds": holds,
            "subset_family_means_pooled_A2_P": detail}, pd.DataFrame(ordering)


def h2(paired, keys):
    c = paired[paired.arm == "phase_conditioned"]
    share = float((c.diff_pooled_A1 < 0).mean())
    subset_holds = {k: int((c[c.subset == k].diff_pooled_A1 < 0).sum()) >= 7 for k in keys}
    n, fam = count_families(subset_holds)
    if share >= 0.8 and n >= 4:
        verdict = "SUPPORTED"
    elif share >= 0.5:
        verdict = "PARTIAL"  # Amendment 1
    else:
        verdict = "NOT SUPPORTED"
    return {"verdict": verdict, "cells": int(len(c)), "share_cells_disparity_reduced": share,
            "families_holding": n, "family_holds": fam, "subset_holds": subset_holds,
            "share_cells_any_engine_worse": float((c.n_worse >= 1).mean())}


def h3(paired, keys):
    out = {}
    for arm, label in (("phase_conditioned", "C"), ("quantile_regression_W", "Q")):
        part = paired[paired.arm == arm]
        share = float(part.uniform_improvement.mean())
        verdict = "SURVIVES" if share < 0.5 else ("REFUTED" if share >= 0.8 else "MIXED")
        by_family = part.assign(family=part.subset.map(ec.FAMILIES)).groupby("family").uniform_improvement.mean()
        out[label] = {"U": share, "verdict": verdict, "cells": int(len(part)),
                      "U_residual": float(part[part.detector != "cvae"].uniform_improvement.mean()),
                      "U_cvae": float(part[part.detector == "cvae"].uniform_improvement.mean()),
                      "U_by_family": by_family.to_dict(),
                      "share_cells_any_engine_worse": float((part.n_worse >= 1).mean())}
    out["verdict"] = "SURVIVES" if out["C"]["verdict"] == out["Q"]["verdict"] == "SURVIVES" else (
        "REFUTED" if "REFUTED" in (out["C"]["verdict"], out["Q"]["verdict"]) else "MIXED")
    return out


def h5(ts, keys):
    pooled = ts[ts.arm == "pooled"]
    a1 = seed_mean(pooled, "pooled_A1")
    me = seed_mean(pooled, "ME_A2")
    detail, a_flags, b_flags, c_flags, survive_flags = {}, {}, {}, {}, {}
    for key in keys:
        cv = pooled[(pooled.subset == key) & (pooled.detector == "cvae")]
        best_residual_me = min(float(me[(key, f)]) for f in RESIDUAL_FAMILIES)
        min_residual_a1 = min(float(a1[(key, f)]) for f in RESIDUAL_FAMILIES)
        a_flags[key] = float(cv.pooled_A1.mean()) < min_residual_a1
        b_flags[key] = bool((cv.ME_A2 <= 0.5 * best_residual_me).all())
        c_flags[key] = bool((cv.WE_A2 < MATERIAL).all())
        survive_flags[key] = int((cv.WE_A2 >= MATERIAL).sum()) >= 2
        detail[key] = {"cvae_seed_ME_A2": cv.ME_A2.tolist(), "cvae_seed_WE_A2": cv.WE_A2.tolist(),
                       "cvae_mean_pooled_A1": float(cv.pooled_A1.mean()), "best_residual_ME_A2": best_residual_me,
                       "min_residual_pooled_A1": min_residual_a1}
    n_a, fa = count_families(a_flags)
    n_b, fb = count_families(b_flags)
    n_c, fc = count_families(c_flags)
    n_s, fs = count_families(survive_flags)
    verdict = "SURVIVES" if n_s >= 3 else ("REFUTED" if n_c >= 4 else "MIXED")
    return {"verdict": verdict, "families_reduces_phase_dependence_a": n_a, "families_substantially_improves_b": n_b,
            "families_solves_c": n_c, "families_WE_material_majority": n_s,
            "family_flags": {"a": fa, "b": fb, "c": fc, "survives": fs}, "subset_detail": detail}


def we_ffr_table(keys):
    ff = stack("flight_false_flags", keys)
    ff = ff[(ff.nominal_fpr == ALPHA) & (ff.unit != "all")]
    return ff.groupby(["subset", "detector", "seed", "arm", "rule"]).false_flag_rate.max().rename("WE_FFR").reset_index()


def we_pa2_table(keys):
    pa = stack("persistence_calibration", keys)
    pa = pa[pa.nominal_fpr == ALPHA]
    return pa.groupby(["subset", "detector", "seed", "arm", "rule"]).PA2.max().rename("WE_PA2").reset_index()


def h6(keys):
    we = we_ffr_table(keys)
    residual = we[(we.arm == "pooled") & (we.detector != "cvae")]
    problem, absorbed_share = {}, {}
    for rule in ec.RULES:
        part = residual[residual.rule == rule]
        problem[rule] = {k: int((part[part.subset == k].WE_FFR >= WE_FFR_PROBLEM).sum()) >= 4 for k in keys}
        fam = part.assign(family=part.subset.map(ec.FAMILIES)).groupby("family").WE_FFR.apply(
            lambda s: float((s < WE_FFR_PROBLEM).mean()))
        absorbed_share[rule] = fam.to_dict()
    n_problem = {rule: count_families(problem[rule])[0] for rule in ec.RULES}
    survives = n_problem["R1"] >= 3 and n_problem["R2"] >= 3
    absorbs = any(sum(v >= 0.8 for f, v in absorbed_share[rule].items() if f in NEW_FAMILIES) >= 4
                  for rule in ("R1", "R2")) and n_problem["R0"] >= 3
    verdict = "SURVIVES" if survives else ("PERSISTENCE ABSORBS" if absorbs else "MIXED")
    pa = we_pa2_table(keys)
    pa_res = pa[(pa.arm == "pooled") & (pa.detector != "cvae")]
    return {"verdict": verdict, "families_with_flight_level_problem": n_problem,
            "family_share_cells_WE_FFR_below_0.10": absorbed_share,
            "share_residual_cells_WE_PA2_material": {r: float((pa_res[pa_res.rule == r].WE_PA2 >= PA2_MATERIAL).mean())
                                                    for r in ec.RULES}}, we, pa


def h7(keys):
    labels = stack("matched_labels", keys)
    labels = labels[labels.nominal_fpr == ALPHA]
    out = {}
    for arm in ("phase_conditioned", "quantile_regression_W"):
        for rule in ec.RULES:
            part = labels[(labels.arm == arm) & (labels.rule == rule)]
            improves = {}
            for key in keys:
                sub = part[part.subset == key]
                residual = sub[sub.detector != "cvae"]
                cv = sub[sub.detector == "cvae"]
                earlier = lambda f: int(((f.matched_label == "earlier at matched burden")  # noqa: E731
                                         & (f.curve_mean_difference < 0)).sum())
                improves[key] = {"residual_runs_earlier_lower_curve": earlier(residual),
                                 "residual_improves": earlier(residual) >= 5,
                                 "cvae_improves": earlier(cv) == 3,
                                 "evaluable_runs": int(sub.evaluable.sum()), "labels": Counter(sub.matched_label)}
            out[f"{arm}|{rule}"] = improves
    return out, labels


# ---------------------------------------------------------------------------
# H4: composition (CE1-CE5)
# ---------------------------------------------------------------------------

def composition_analysis(key):
    lock = read_lock(key)
    comp = lock["composition"]
    pool = {int(g): int(k) for g, k in comp["pool_classes"].items()}
    classes = lock["roles"]["classes"]
    cm = read(key, "composition_metrics")
    cm = cm[cm.nominal_fpr == ALPHA]
    engine = cm[cm.unit != "summary"].assign(unit=lambda f: f.unit.astype(int))
    engine = engine.groupby(["detector", "seed", "arm", "design", "unit"]).A2.mean()
    summary = cm[cm.unit == "summary"].groupby(["detector", "seed", "arm", "design"]).ME_A2.mean()
    designs = {d["name"]: d for d in comp["designs"]}
    balanced = "balanced" if "balanced" in designs else next(n for n, d in designs.items() if "E" in d["codes"])
    engine_rows, run_rows = [], []
    for (detector, seed, arm), _ in summary.groupby(level=[0, 1, 2]):
        deltas = []
        for e in sorted(set(engine.xs((detector, seed, arm), level=[0, 1, 2]).index.get_level_values("unit"))):
            k = classes[str(e)]
            covered = [g for g in pool if pool[g] == k]
            uncovered = [g for g in pool if pool[g] != k]
            if not covered or not uncovered:
                continue
            a2 = lambda design: float(engine[(detector, seed, arm, design, e)])  # noqa: E731
            d_cov = np.mean([a2(f"single_{g}") for g in uncovered]) - np.mean([a2(f"single_{g}") for g in covered])
            d_vol = np.mean([a2(f"single_{g}") - a2(f"full_{g}") for g in uncovered])
            loo = np.nan
            if len(set(pool.values())) == 3 and "balanced" in designs:
                others = sorted(c for c in set(pool.values()) if c != k)
                loo = a2(f"mixed_{others[0]}{others[1]}") - a2("balanced")
            deltas.append(d_cov)
            engine_rows.append({"subset": key, "detector": detector, "seed": seed, "arm": arm, "unit": e,
                                "flight_class": k, "delta_cov": d_cov, "delta_vol_uncovered": d_vol,
                                "delta_leave_class_out": loo})
        singles = [float(summary[(detector, seed, arm, f"single_{g}")]) for g in pool]
        me_bal = float(summary[(detector, seed, arm, balanced)])
        run_rows.append({"subset": key, "detector": detector, "seed": seed, "arm": arm,
                         "eligible_engines": len(deltas), "median_delta_cov": float(np.median(deltas)),
                         "supports_coverage": bool(np.median(deltas) > 0), "balanced_design": balanced,
                         "ME_A2_balanced": me_bal, "mean_ME_A2_single": float(np.mean(singles)),
                         "min_ME_A2_single": float(np.min(singles)),
                         "CE2_balanced_minus_mean_single": me_bal - float(np.mean(singles)),
                         "CE2_balanced_minus_best_single": me_bal - float(np.min(singles)),
                         "balance_check": bool(me_bal < np.mean(singles))})
    ce4 = []
    for name, d in designs.items():
        if "B" not in d["codes"]:
            continue
        members = set(map(int, d["members"]))
        for other, od in designs.items():
            if set(od["codes"]) & {"C", "E", "E+"} and od["volume"] == "N" and len(od["members"]) == len(members) \
                    and members & set(map(int, od["members"])):
                for (detector, seed, arm), value in summary.xs(name, level="design").items():
                    ce4.append({"subset": key, "detector": detector, "seed": seed, "arm": arm, "same_class_design": name,
                                "mixed_design": other,
                                "ME_A2_same_class_minus_mixed": float(value - summary[(detector, seed, arm, other)])})
    return pd.DataFrame(engine_rows), pd.DataFrame(run_rows), pd.DataFrame(ce4)


def h4(keys):
    eligible = [k for k in keys if read_lock(k).get("composition") and read_lock(k)["composition"]["eligible"]]
    engines, runs, ce4 = [], [], []
    for key in eligible:
        e, r, c = composition_analysis(key)
        engines.append(e)
        runs.append(r)
        ce4.append(c)
    engines, runs = pd.concat(engines, ignore_index=True), pd.concat(runs, ignore_index=True)
    ce4 = pd.concat(ce4, ignore_index=True) if ce4 else pd.DataFrame()
    supports, balance = {}, {}
    for key in eligible:
        part = runs[runs.subset == key]
        supports[key] = all(int(part[part.arm == arm].supports_coverage.sum()) >= 7 for arm in ("pooled", "phase_conditioned"))
        balance[key] = all(int(part[part.arm == arm].balance_check.sum()) >= 7 for arm in ("pooled", "phase_conditioned"))
    n_sup, fam_sup = count_families(supports, COMPOSITION_FAMILIES)
    n_bal, fam_bal = count_families(balance, COMPOSITION_FAMILIES)
    verdict = "SUPPORTED" if (n_sup >= 3 and n_bal >= 3) else ("NOT SUPPORTED" if n_sup <= 1 else "PARTIAL")
    qual = {}
    for arm in ("pooled", "phase_conditioned"):
        part = engines[engines.arm == arm].assign(family=lambda f: f.subset.map(ec.FAMILIES))
        fam_cov = part.groupby("family").delta_cov.median()
        fam_vol = part.groupby("family").delta_vol_uncovered.median()
        qual[arm] = {"family_median_delta_cov": fam_cov.to_dict(), "family_median_delta_vol": fam_vol.to_dict(),
                     "median_over_families_delta_cov": float(fam_cov.median()),
                     "weak": bool(fam_cov.median() < 0.0025),
                     "beyond_volume_families": int(sum(fam_cov[f] > fam_vol[f] for f in fam_cov.index
                                                       if f in COMPOSITION_FAMILIES))}
    beyond = all(qual[a]["beyond_volume_families"] >= 3 for a in qual)
    return {"verdict": verdict, "families_supporting_coverage": n_sup, "families_passing_balance": n_bal,
            "family_supports": fam_sup, "family_balance": fam_bal, "subset_supports": supports,
            "subset_balance": balance, "qualifiers": qual, "beyond_volume": beyond,
            "weak": any(qual[a]["weak"] for a in qual), "dataset_specific": n_sup <= 2}, engines, runs, ce4


# ---------------------------------------------------------------------------
# Stories, original-story class, rescope flags
# ---------------------------------------------------------------------------

def original_story(ts, paired, keys, h1r, h4r, h7r):
    c = paired[paired.arm == "phase_conditioned"]
    q = ts[(ts.arm == "quantile_regression_W")]
    comps = {"S1": h1r["subset_holds"],
             "S2": {k: int((c[c.subset == k].diff_pooled_A1 < 0).sum()) >= 7 for k in keys},
             "S3": {k: int((c[c.subset == k].n_worse >= 1).sum()) >= 6 for k in keys},
             "S4": {k: not h7r["phase_conditioned|R0"][k]["residual_improves"] for k in keys},
             "S5": {k: int((q[q.subset == k].WE_A2 >= MATERIAL).sum()) >= 6 for k in keys}}
    reversal = {k: int((c[c.subset == k].diff_pooled_A1 > 0).sum()) >= 6 for k in keys}
    counts = {name: count_families(flags)[0] for name, flags in comps.items()}
    n_rev = count_families(reversal)[0]
    if counts["S1"] == 0 or counts["S3"] == 0 or n_rev >= 3:  # Amendment 1
        klass = "REFUTED"
    elif (counts["S1"] >= 4 and counts["S2"] >= 4 and counts["S3"] >= 4 and counts["S4"] >= 4
          and counts["S5"] >= 3 and h4r["verdict"] in ("SUPPORTED", "PARTIAL")):
        klass = "GENERALIZED"
    elif counts["S1"] >= 3 and counts["S3"] >= 3:
        klass = "PARTIALLY GENERALIZED"
    else:
        klass = "CONFIGURATION-SPECIFIC"
    return {"class": klass, "family_counts": counts, "families_disparity_reversal": n_rev,
            "subset_components": comps}


def stories(ts, keys, h1r, h4r, h5r, h6r):
    triggered = []
    if h1r["families_holding"] <= 2:
        triggered.append("M-E")
    if h5r["families_substantially_improves_b"] >= 4 and h5r["families_solves_c"] >= 3:
        triggered.append("M-A")
    if h4r["verdict"] == "SUPPORTED" and h4r["beyond_volume"]:
        triggered.append("M-B")
    broad = True
    for family in RESIDUAL_FAMILIES + ("cvae",):
        for arm in ec.ARMS:
            part = ts[(ts.detector == family) & (ts.arm == arm)]
            flags = {k: (part[part.subset == k].WE_A2 >= MATERIAL).sum() > len(part[part.subset == k]) / 2 for k in keys}
            if count_families(flags)[0] < 3:
                broad = False
    if broad:
        triggered.append("M-C")
    if h6r["verdict"] == "PERSISTENCE ABSORBS":
        triggered.append("M-D")
    if "M-E" in triggered:
        headline = "M-E"
    elif "M-A" in triggered:
        headline = "M-A"
    elif "M-C" in triggered and "M-B" in triggered:
        headline = "M-C + M-B"
    elif "M-C" in triggered or "M-B" in triggered:
        headline = "M-C" if "M-C" in triggered else "M-B"
    elif "M-D" in triggered:
        headline = "M-D"
    else:
        headline = "MIXED"
    return {"triggered": triggered, "headline": headline, "broad_failure_all_detectors_arms": broad}


def rescope_flags(ts, paired, keys, h1r, h4r, h5r, h6r, ordering):
    c = paired[paired.arm == "phase_conditioned"]
    flags = {"A": h1r["families_holding"] <= 2, "B": h5r["verdict"] == "REFUTED",
             "C": h6r["verdict"] == "PERSISTENCE ABSORBS", "D": h4r["verdict"] == "NOT SUPPORTED"}
    reversal = {k: int((c[c.subset == k].diff_pooled_A1 > 0).sum()) >= 6 for k in keys}
    residual_order = ordering[ordering.detector != "cvae"]
    descent_lowest = {}
    for key in keys:
        part = residual_order[residual_order.subset == key]
        fam_lowest = {}
        for family in RESIDUAL_FAMILIES:
            rows = part[part.detector == family]
            means = rows[["climb", "cruise", "descent"]].mean()
            fam_lowest[family] = means.idxmin() == "descent"
        descent_lowest[key] = all(fam_lowest.values())
    flags["E"] = count_families(reversal)[0] >= 3 or count_families(descent_lowest)[0] >= 3
    reversal_ew = {k: int((((c.subset == k) & (c.diff_pooled_A2 < 0)
                            & ((c.diff_ME_A2 > 0) | (c.diff_EW_A2 > 0)))).sum()) >= 6 for k in keys}
    flags["F"] = count_families(reversal_ew)[0] >= 3
    return flags


# ---------------------------------------------------------------------------
# Cross-dataset (U-EXT2) and composition bootstraps
# ---------------------------------------------------------------------------

def subset_family_replicates(keys):
    """Per subset: replicate x detector-family arrays of the U-EXT2 quantities (seed means within replicate)."""
    out = {}
    for key in keys:
        rep = read(key, "bootstrap_uext1_replicates_alpha_0.01")
        values = {}
        for family in RESIDUAL_FAMILIES + ("cvae",):
            part = rep[rep.detector == family]
            means = part.groupby("replicate")[["diff_pooled_A1", "diff_pooled_A2", "diff_ME_A2", "pooled.ME_A2"]].mean()
            values[family] = means.sort_index()
        best_residual = np.minimum.reduce([values[f]["pooled.ME_A2"].to_numpy() for f in RESIDUAL_FAMILIES])
        values["cvae_minus_best_residual_ME_A2_P"] = values["cvae"]["pooled.ME_A2"].to_numpy() - best_residual
        out[key] = values
    return out


def point_values(ts, paired, keys):
    point = {}
    for key in keys:
        entry = {}
        for family in RESIDUAL_FAMILIES + ("cvae",):
            c = paired[(paired.subset == key) & (paired.detector == family) & (paired.arm == "phase_conditioned")]
            entry[family] = {"diff_pooled_A1": float(c.diff_pooled_A1.mean()),
                             "diff_pooled_A2": float(c.diff_pooled_A2.mean()), "diff_ME_A2": float(c.diff_ME_A2.mean())}
        pooled = ts[(ts.subset == key) & (ts.arm == "pooled")]
        best = min(float(pooled[pooled.detector == f].ME_A2.mean()) for f in RESIDUAL_FAMILIES)
        entry["cvae_minus_best_residual_ME_A2_P"] = float(pooled[pooled.detector == "cvae"].ME_A2.mean()) - best
        point[key] = entry
    return point


def family_statistic(values_by_subset, families):
    """Median over families of the family-mean subset value."""
    fam_means = [np.mean([values_by_subset[s] for s in members]) for members in families]
    return float(np.median(fam_means))


def uext2(ts, paired, keys, replicates=ec.BOOTSTRAP_REPLICATES):
    rng = np.random.default_rng(ec.UEXT2_SEED)
    reps = subset_family_replicates(keys)
    point = point_values(ts, paired, keys)
    families = {}
    for key in keys:
        families.setdefault(ec.FAMILIES[key], []).append(key)
    family_list = [families[f] for f in NEW_FAMILIES if f in families]
    quantities = [(f, m) for f in RESIDUAL_FAMILIES + ("cvae",) for m in ("diff_pooled_A1", "diff_pooled_A2", "diff_ME_A2")]
    quantities.append(("cvae_minus_best_residual_ME_A2_P", None))
    draws = {q: [] for q in quantities}
    n_rep = len(next(iter(reps.values()))["pca"])
    for _ in range(replicates):
        sampled = [family_list[i] for i in rng.integers(0, len(family_list), size=len(family_list))]
        chosen = [[members[j] for j in rng.integers(0, len(members), size=len(members))] for members in sampled]
        picks = [[(s, int(rng.integers(0, n_rep))) for s in members] for members in chosen]
        for q in quantities:
            fam_values = []
            for members in picks:
                if q[1] is None:
                    vals = [reps[s][q[0]][b] for s, b in members]
                else:
                    vals = [float(reps[s][q[0]][q[1]].iloc[b]) for s, b in members]
                fam_values.append(np.mean(vals))
            draws[q].append(float(np.median(fam_values)))
    rows = []
    for q in quantities:
        if q[1] is None:
            by_subset = {k: point[k][q[0]] for k in keys}
        else:
            by_subset = {k: point[k][q[0]][q[1]] for k in keys}
        est = family_statistic(by_subset, family_list)
        values = np.asarray(draws[q])
        rows.append({"detector_family": q[0], "quantity": q[1] or q[0], "point_median_over_families": est,
                     "ci_lower_95": float(np.quantile(values, 0.025)), "ci_upper_95": float(np.quantile(values, 0.975)),
                     "replicates": replicates, "top_level_units": len(family_list),
                     "hierarchy": "family -> subset -> U-EXT1 replicate (engine -> flight)",
                     "subsets_negative": int(sum(v < 0 for v in by_subset.values())), "subsets": len(by_subset)})
    return pd.DataFrame(rows)


def composition_bootstrap(engines, replicates=ec.BOOTSTRAP_REPLICATES):
    rng = np.random.default_rng(ec.COMPOSITION_BOOT_SEED)
    rows = []
    for arm in ("pooled", "phase_conditioned"):
        per_engine = engines[engines.arm == arm].groupby(["subset", "unit"]).delta_cov.median()
        tree = {}
        for (subset, unit), value in per_engine.items():
            tree.setdefault(ec.FAMILIES[subset], {}).setdefault(subset, []).append(value)
        fams = [tree[f] for f in COMPOSITION_FAMILIES if f in tree]

        def statistic(fam_sample):
            fam_medians = []
            for subsets in fam_sample:
                pooled = [v for values in subsets for v in values]
                fam_medians.append(np.median(pooled))
            return float(np.median(fam_medians))

        point = statistic([list(f.values()) for f in fams])
        draws = []
        for _ in range(replicates):
            sample = []
            for i in rng.integers(0, len(fams), size=len(fams)):
                subsets = list(fams[i].values())
                chosen = [subsets[j] for j in rng.integers(0, len(subsets), size=len(subsets))]
                sample.append([[vals[j] for j in rng.integers(0, len(vals), size=len(vals))] for vals in chosen])
            draws.append(statistic(sample))
        rows.append({"arm": arm, "statistic": "median over families of family-median engine CE1 (median over runs)",
                     "point": point, "ci_lower_95": float(np.quantile(draws, 0.025)),
                     "ci_upper_95": float(np.quantile(draws, 0.975)), "replicates": replicates,
                     "engines": int(len(per_engine)), "families": len(fams)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(log=print):
    keys = list(ec.NEW_ORDER)
    for key in keys + list(ec.REFERENCE_ORDER):
        if not (ec.RESULTS / key / "audit" / "audit_record.json").exists():
            raise ec.ExtensionError(f"Audit outputs missing for {key}")
    ts, paired = primary_tables(keys)
    h1r, ordering = h1(ts, keys)
    h2r = h2(paired, keys)
    h3r = h3(paired, keys)
    h4r, comp_engines, comp_runs, comp_ce4 = h4(keys)
    h5r = h5(ts, keys)
    h6r, we_ffr, we_pa2 = h6(keys)
    h7r, labels = h7(keys)
    orig = original_story(ts, paired, keys, h1r, h4r, h7r)
    st = stories(ts, keys, h1r, h4r, h5r, h6r)
    flags = rescope_flags(ts, paired, keys, h1r, h4r, h5r, h6r, ordering)
    boot = uext2(ts, paired, keys)
    comp_boot = composition_bootstrap(comp_engines)
    if ec.REFERENCE_ORDER:
        ref_ts, ref_paired = primary_tables(list(ec.REFERENCE_ORDER))
    else:
        ref_ts, ref_paired = ts.iloc[:0], paired.iloc[:0]
    decisions = {"protocol": "GENERALIZATION_PROTOCOL.md v1.0 + Amendment 1", "alpha": ALPHA,
                 "H1": h1r, "H2": h2r, "H3": h3r, "H4": h4r, "H5": h5r, "H6": h6r,
                 "H7": json.loads(json.dumps(h7r, default=lambda o: dict(o))),
                 "original_story": orig, "matrix_stories": st, "rescope_flags": flags}
    out = ec.RESULTS / "summary"  # resolved at call time
    out.mkdir(parents=True, exist_ok=True)
    ec.write_json(out / "decisions.json", decisions)
    for name, frame in {"transport_summary_alpha_0.01": pd.concat([ts, ref_ts]),
                        "paired_transport_alpha_0.01": pd.concat([paired, ref_paired]),
                        "phase_ordering_pooled": ordering, "we_ffr": we_ffr, "we_pa2": we_pa2,
                        "matched_labels_alpha_0.01": labels, "composition_engine_effects": comp_engines,
                        "composition_run_summary": comp_runs, "composition_ce4": comp_ce4,
                        "uext2_cross_dataset": boot, "composition_bootstrap": comp_boot}.items():
        ec.write_csv(out / f"{name}.csv", frame)
    log(json.dumps({k: decisions[k]["verdict"] for k in ("H1", "H2", "H3", "H4", "H5", "H6")}))
    log(json.dumps({"original": orig["class"], "stories": st, "flags": flags}))
    return decisions
