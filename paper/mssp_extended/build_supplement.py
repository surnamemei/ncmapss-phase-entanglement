"""Build the supplementary material of the extended MSSP manuscript (PDF).

Part A (multi-subset extension) formats committed extension outputs: results/extension/ (protocol
docs/extension/GENERALIZATION_PROTOCOL.md v1.0 with Amendments 1-3) and docs/extension/. Every table is a
view of committed CSV/JSON values (fractions shown as percentages or percentage points); nothing is
recomputed from scores and no N-CMAPSS file is read.
Part B is the committed pre-extension MSSP supplement (paper/mssp/supplement/supplement.pdf: frozen
DS02/DS03 discovery and confirmation, post-confirmation and adversarial-validation analyses), included
unchanged page by page.

Output: paper/mssp_extended/supplement/{supplement.tex, supplement.pdf, supplement.provenance.json}.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/mssp_extended/supplement"
EXT = ROOT / "results/extension"
SUM = EXT / "summary"
DOCS = ROOT / "docs/extension"
PRE_SUPP = ROOT / "paper/mssp/supplement/supplement.pdf"
NEW = ("DS01", "DS04", "DS05", "DS06", "DS07", "DS08a", "DS08c")
REF = ("DS02", "DS03")
ALL = REF + NEW
FAMILY = {"DS02": "ref.", "DS03": "ref.", "DS01": "F1", "DS04": "F2", "DS05": "F3", "DS06": "F3", "DS07": "F3",
          "DS08a": "F4", "DS08c": "F5"}
DET = {"pca": "PCA", "isolation_forest": "IF", "lstm_autoencoder": "LSTM", "cvae": "CVAE"}
ARM = {"pooled": "P", "phase_conditioned": "C", "quantile_regression_W": "Q"}
RULES = ("R0", "R1", "R2")
ALPHA = 0.01
MINUS = "−"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Inputs:
    def __init__(self):
        self.used = set()

    def csv(self, path):
        self.used.add(Path(path))
        return pd.read_csv(path, float_precision="round_trip")

    def json(self, path):
        self.used.add(Path(path))
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def audit(self, key, table):
        return self.csv(EXT / key / "audit" / f"{table}.csv")

    def all_audit(self, table, keys=ALL):
        return pd.concat([self.audit(k, table).assign(subset=k) for k in keys], ignore_index=True)


def run_label(det, seed):
    return DET[det] if int(seed) < 0 else f"{DET[det]} s{int(seed)}"


def pp(x, d=2):
    return "--" if pd.isna(x) else f"{100 * x:.{d}f}".replace("-", MINUS)


def spp(x, d=2):
    if pd.isna(x):
        return "--"
    text = f"{100 * x:+.{d}f}"
    return "0.00" if float(text) == 0 else text.replace("-", MINUS)


def pct(x, d=1):
    return "--" if pd.isna(x) else f"{100 * x:.{d}f}"


def tex_escape(text):
    text = str(text)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"), ("$", r"\$")):
        text = text.replace(a, b)
    return text


def longtable(frame, caption, label, align=None, note=None, size=r"\footnotesize", rule_between=None):
    """A booktabs longtable; header cells may contain '\\n' for line breaks. rule_between: column whose change adds a rule."""
    align = align or ("l" * len(frame.columns))
    head = " & ".join(r"\makecell[b]{" + tex_escape(c).replace("\n", r"\\") + "}" for c in frame.columns) + r" \\"
    lines = [r"{" + size, r"\setlength{\tabcolsep}{3.5pt}", r"\begin{longtable}{" + align + "}",
             r"\caption{" + caption + r"}\label{" + label + r"}\\", r"\toprule", head, r"\midrule", r"\endfirsthead",
             r"\toprule", head, r"\midrule", r"\endhead", r"\bottomrule", r"\endfoot"]
    previous = None
    for _, row in frame.iterrows():
        if rule_between is not None and previous is not None and row[rule_between] != previous:
            lines.append(r"\midrule")
        previous = row[rule_between] if rule_between is not None else None
        lines.append(" & ".join(tex_escape(v) for v in row.values) + r" \\")
    lines += [r"\end{longtable}"]
    if note:
        lines += [r"\vspace{-0.6em}", r"\noindent{\scriptsize " + note + "}"]
    lines += ["}", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def s_cohort(inp):
    meta = inp.csv(DOCS / "subset_metadata_audit.csv")
    rows = []
    for _, r in meta.iterrows():
        excluded = str(r.role).startswith("EXCLUDED")
        crit = "C1 fails; not opened" if excluded else "".join("✓" if r[f"C{i}"] is True or r[f"C{i}"] == "True" else "✗" for i in range(1, 10)) \
            if not pd.isna(r.get("C1")) else "--"
        rows.append({"Subset": r.dataset, "Role": str(r.role).split(" (")[0].replace("PRIMARY GENERALIZATION COHORT", "primary cohort"),
                     "Dev engines\n(unit:class)": r.dev_classes if not pd.isna(r.dev_classes) else "--",
                     "Test engines\n(unit:class)": r.test_classes if not pd.isna(r.test_classes) else "--",
                     "Healthy flights\ndev / test": "--" if excluded or pd.isna(r.healthy_flights_dev) else
                     f"{int(r.healthy_flights_dev)} / {int(r.healthy_flights_test)}",
                     "Post-onset\nflights (test)": "--" if excluded or pd.isna(r.post_onset_flights_test) else f"{int(r.post_onset_flights_test)}",
                     "Min. test engine\nrows per phase": "--" if pd.isna(r.min_test_engine_phase_rows) else f"{int(r.min_test_engine_phase_rows):,}",
                     "C1--C9": crit.replace("✓", "y").replace("✗", "n")})
    frame = pd.DataFrame(rows)
    return longtable(frame, "Candidate subsets, metadata-only eligibility audit (C1--C9 of the subset selection lock; y = pass, "
                     "n = fail). DS02 and DS03 fail C9 by construction (opened by the frozen study) and are references. "
                     "DS08d fails C1 (the official file is 32 bytes shorter than its HDF5 superblock declares) and was not opened.",
                     "tab:cohort", align="llp{3.2cm}p{2.6cm}rrrl",
                     note="Source: docs/extension/subset\\_metadata\\_audit.csv (labels, variable names and healthy-row altitude only).")


def s_roles(inp):
    rows = []
    for key in ALL:
        lock = inp.json(EXT / key / "lock" / "calibration_lock.json")
        roles, cls = lock["roles"], lock["roles"]["classes"]
        fmt = lambda units: ", ".join(f"{u} ({cls[str(u)]})" for u in units)  # noqa: E731
        comp = lock.get("composition") or {}
        rows.append({"Subset": key, "Family": FAMILY[key], "Fit (class)": fmt(roles["fit"]),
                     "Validation": str(roles.get("validation", "--")), "Calibration (class)": fmt(roles["calibration"]),
                     "Audit (class)": fmt(roles["audit"]),
                     "Composition N": f"{comp['volume_N']:,}" if comp.get("eligible") else "not eligible"})
    return longtable(pd.DataFrame(rows), "Engine roles (R-ALLOC for new subsets; frozen roles for DS02 and DS03).", "tab:roles",
                     align="llp{2.7cm}lp{2.6cm}p{3.4cm}l",
                     note="Source: results/extension/$\\langle$subset$\\rangle$/lock/calibration\\_lock.json.")


def s_locks(inp):
    locks = inp.csv(SUM / "numerical_audit_locks.csv")
    rows = []
    for _, r in locks.iterrows():
        vb = json.loads(r.cvae_variance_bound_share) if isinstance(r.cvae_variance_bound_share, str) else {}
        rows.append({"Subset": r.subset, "Calibration\nrows / flights": f"{int(r.calibration_rows):,} / {int(r.calibration_flights)}",
                     "Lock (s)": "--" if pd.isna(r.lock_seconds) else f"{r.lock_seconds:,.0f}", "Audit (s)": "--" if pd.isna(r.audit_seconds) else f"{r.audit_seconds:,.0f}",
                     "Audit rows": "--" if pd.isna(r.audit_rows) else f"{int(r.audit_rows):,}",
                     "CVAE float64 check:\nmin Spearman": f"{r.cvae_precision_min_spearman:.6f}",
                     "CVAE exceedance\nchanges": str(int(r.cvae_precision_exceedance_changes)),
                     "CVAE variance-bound share\n(seeds 0/1/2)": " / ".join(f"{100 * float(vb[s]):.1f}%" for s in ("0", "1", "2")) if vb else "--"})
    return longtable(pd.DataFrame(rows), "Calibration locks, compute and CVAE numerical checks. The float64 check rescored calibration "
                     "rows in double precision; the variance-bound share is the fraction of decoder outputs within 1\\% of the lower "
                     "log-variance bound. For the references DS02 and DS03 the audit time is the whole reference rerun (CVAE training, "
                     "lock and audit; the frozen residual models are refitted or loaded).", "tab:locks", align="lrrrrrrr",
                     note="Source: results/extension/summary/numerical\\_audit\\_locks.csv.")


def s_training(inp):
    tr = inp.csv(SUM / "numerical_audit_training.csv")
    rows = [{"Subset": r.subset, "Detector": run_label(r.detector, r.seed), "Selection\nepochs run": int(r.selection_epochs_run),
             "Selected\nepoch": int(r.selected_epoch), "Hit 600": "yes" if r.hit_600_ceiling else "no",
             "Best validation\nloss": f"{r.best_validation_loss:.4g}", "Refit\nepochs": int(r.refit_epochs),
             "Refit final\nloss": f"{r.refit_final_loss:.4g}", "Refit\nfinite": "yes" if r.refit_all_finite else "no"}
            for _, r in tr.iterrows()]
    return longtable(pd.DataFrame(rows), "Epoch selection and refit of the LSTM and CVAE (selection on the validation engine, "
                     "refit on the full fit pool). DS02/DS03 LSTM checkpoints are frozen and not retrained.", "tab:training",
                     align="llrrlrrrl", rule_between="Subset",
                     note="Source: results/extension/summary/numerical\\_audit\\_training.csv. Losses are per-row negative "
                          "log-likelihoods (CVAE) or mean squared errors (LSTM) on the standardized scale.")


def s_transport_runs(inp):
    ts = inp.all_audit("transport_summary")
    ts = ts[ts.nominal_fpr == ALPHA]
    rows = []
    for _, r in ts.iterrows():
        rows.append({"Subset": r.subset, "Run": run_label(r.detector, r.seed), "Arm": ARM[r.arm],
                     "Climb\nFPR (%)": pct(r.pooled_climb_fpr, 2), "Cruise\nFPR (%)": pct(r.pooled_cruise_fpr, 2),
                     "Descent\nFPR (%)": pct(r.pooled_descent_fpr, 2), "Pooled\nA1 (pp)": pp(r.pooled_A1),
                     "Pooled\nA2 (pp)": pp(r.pooled_A2), "ME-A2\n(pp)": pp(r.ME_A2), "WE-A2\n(pp)": pp(r.WE_A2),
                     "EW-A2\n(pp)": pp(r.EW_A2), "Worst\nengine": str(int(r.worst_engine))})
    return longtable(pd.DataFrame(rows), "Row-pooled phase FPRs and transport metrics for every subset, detector run and arm at "
                     "the 1\\% target (P pooled, C retrospective phase-conditioned, Q continuous context).", "tab:transport",
                     align="lllrrrrrrrrr", rule_between="Subset",
                     note="Source: results/extension/$\\langle$subset$\\rangle$/audit/transport\\_summary.csv. A1 = max minus min phase "
                          "FPR; A2 = max over phases of |FPR − α|; ME-A2 = mean over audit engines of per-engine A2; WE-A2 = worst "
                          "engine; EW-A2 = A2 of the equal-engine average FPR.")


def s_paired(inp):
    pt = inp.all_audit("paired_transport")
    pt = pt[pt.nominal_fpr == ALPHA]
    rows = []
    for _, r in pt.iterrows():
        rows.append({"Subset": r.subset, "Run": run_label(r.detector, r.seed), "Arm − P": ARM[r.arm],
                     "ΔA1 (pp)": spp(r.diff_pooled_A1), "ΔA2 (pp)": spp(r.diff_pooled_A2), "ΔME-A2 (pp)": spp(r.diff_ME_A2),
                     "ΔWE-A2 (pp)": spp(r.diff_WE_A2), "ΔEW-A2 (pp)": spp(r.diff_EW_A2),
                     "Engines worse\n/ better / all": f"{int(r.n_worse)} / {int(r.n_better)} / {int(r.engines)}",
                     "All engines\nimproved": "yes" if r.uniform_improvement else "no"})
    return longtable(pd.DataFrame(rows), "Paired comparisons of C and Q against P for every detector run at the 1\\% target "
                     "(negative differences favour the conditioned arm).", "tab:paired", align="lllrrrrrcl", rule_between="Subset",
                     note="Source: results/extension/$\\langle$subset$\\rangle$/audit/paired\\_transport.csv.")


def s_engines(inp):
    pe = inp.all_audit("paired_transport_engines")
    pe = pe[pe.nominal_fpr == ALPHA]
    rows = []
    for key in ALL:
        lock = inp.json(EXT / key / "lock" / "calibration_lock.json")
        cls = lock["roles"]["classes"]
        cal_cls = {cls[str(u)] for u in lock["roles"]["calibration"]}
        part = pe[pe.subset == key]
        for unit in sorted(part.unit.unique()):
            e = part[part.unit == unit]
            res, cv = e[e.detector != "cvae"], e[e.detector == "cvae"]
            rc, rq = res[res.arm == "phase_conditioned"], res[res.arm == "quantile_regression_W"]
            cc, cq = cv[cv.arm == "phase_conditioned"], cv[cv.arm == "quantile_regression_W"]
            rng = lambda s: f"{pp(s.median())} [{pp(s.min())}, {pp(s.max())}]"  # noqa: E731
            rows.append({"Subset": key, "Engine\n(class)": f"{unit} ({cls[str(unit)]})",
                         "Class in\ncalibration": "yes" if cls[str(unit)] in cal_cls else "no",
                         "Residual A2 under P (pp)\nmedian [range]": rng(rc.pooled_arm_A2),
                         "under C (pp)": rng(rc.arm_A2), "under Q (pp)": rng(rq.arm_A2),
                         "Residual runs\nworse: C / Q": f"{int((rc.diff_A2 > 0).sum())}/7 / {int((rq.diff_A2 > 0).sum())}/7",
                         "CVAE A2 P / C / Q\n(pp, seed median)": f"{pp(cc.pooled_arm_A2.median())} / {pp(cc.arm_A2.median())} / "
                                                                  f"{pp(cq.arm_A2.median())}",
                         "CVAE seeds\nworse: C / Q": f"{int((cc.diff_A2 > 0).sum())}/3 / {int((cq.diff_A2 > 0).sum())}/3"})
    return longtable(pd.DataFrame(rows), "Per-engine nominal calibration error A2 at the 1\\% target for every audit engine: "
                     "residual runs (PCA, IF and LSTM seeds; median and range over the seven runs) and CVAE seeds.", "tab:engines",
                     align="llllllcll", rule_between="Subset", size=r"\scriptsize",
                     note="Source: results/extension/$\\langle$subset$\\rangle$/audit/paired\\_transport\\_engines.csv.")


def s_uext1(inp):
    ci = inp.all_audit("bootstrap_uext1_ci")
    ci = ci[(ci.nominal_fpr == ALPHA) & ci.metric.isin(["diff_pooled_A1", "diff_pooled_A2", "diff_ME_A2"])]
    rows = []
    for (key, det, seed), g in ci.groupby(["subset", "detector", "seed"], sort=False):
        row = {"Subset": key, "Run": run_label(det, seed)}
        for metric, name in (("diff_pooled_A1", "ΔA1 (C − P)"), ("diff_pooled_A2", "ΔA2 (C − P)"), ("diff_ME_A2", "ΔME-A2 (C − P)")):
            r = g[g.metric == metric].iloc[0]
            row[name + "\npp [95% interval]"] = f"{spp(r.point_estimate)} [{spp(r.ci_lower_95)}, {spp(r.ci_upper_95)}]"
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame["_order"] = frame.Subset.map({k: i for i, k in enumerate(ALL)})
    frame = frame.sort_values(["_order"], kind="stable").drop(columns="_order")
    return longtable(frame, "Per-subset hierarchical bootstrap U-EXT1 (engine then flight, 2,000 replicates, thresholds "
                     "re-estimated in every replicate) for C minus P at the 1\\% target.", "tab:uext1", align="llccc",
                     rule_between="Subset",
                     note="Source: results/extension/$\\langle$subset$\\rangle$/audit/bootstrap\\_uext1\\_ci.csv. Percentile intervals; "
                          "Q has point estimates only (the quantile-regression fit is not repeated per replicate).")


def s_uext2(inp):
    ux = inp.csv(SUM / "uext2_cross_dataset.csv")
    name = {"diff_pooled_A1": "ΔA1 (C − P)", "diff_pooled_A2": "ΔA2 (C − P)", "diff_ME_A2": "ΔME-A2 (C − P)",
            "cvae_minus_best_residual_ME_A2_P": "CVAE − best residual ME-A2 (P)"}
    rows = [{"Detector family": DET.get(r.detector_family, "CVAE vs residual"), "Quantity": name[r.quantity],
             "Median over families (pp)": spp(r.point_median_over_families),
             "95% interval (pp)": f"[{spp(r.ci_lower_95)}, {spp(r.ci_upper_95)}]",
             "Subsets negative": f"{int(r.subsets_negative)}/{int(r.subsets)}"} for _, r in ux.iterrows()]
    return longtable(pd.DataFrame(rows), "Cross-dataset hierarchical bootstrap U-EXT2 (family, then subset, then a U-EXT1 "
                     "replicate; 2,000 replicates; five top-level units, so intervals are crude) at the 1\\% target.", "tab:uext2",
                     align="llrrr", note="Source: results/extension/summary/uext2\\_cross\\_dataset.csv.")


def s_targets(inp):
    ts = inp.all_audit("transport_summary")
    ts = ts[ts.detector != "cvae"]
    rows = []
    for key in ALL:
        for arm in ARM:
            part = ts[(ts.subset == key) & (ts.arm == arm)]
            row = {"Subset": key, "Arm": ARM[arm]}
            for a in (0.005, 0.01, 0.02):
                p = part[part.nominal_fpr == a]
                row[f"α = {100 * a:g}%\npooled A2 / ME-A2 (pp)"] = f"{pp(p.pooled_A2.median())} / {pp(p.ME_A2.median())}"
                row[f"α = {100 * a:g}%\nME-A2 / α"] = f"{p.ME_A2.median() / a:.2f}"
            rows.append(row)
    return longtable(pd.DataFrame(rows), "Target sensitivity: medians over the seven residual runs of pooled A2 and ME-A2 at "
                     "the 0.5\\%, 1\\% and 2\\% targets, with ME-A2 relative to α.", "tab:targets", align="llcrcrcr",
                     rule_between="Subset", note="Source: results/extension/$\\langle$subset$\\rangle$/audit/transport\\_summary.csv.")


def s_composition(inp):
    runs = inp.csv(SUM / "composition_run_summary.csv")
    rows = []
    for _, r in runs.iterrows():
        rows.append({"Subset": r.subset, "Run": run_label(r.detector, r.seed), "Arm": ARM[r.arm],
                     "Eligible\nengines": int(r.eligible_engines), "Median Δcov\n(pp)": spp(r.median_delta_cov),
                     "Supports\ncoverage": "yes" if r.supports_coverage else "no",
                     "ME-A2 balanced\n(pp)": pp(r.ME_A2_balanced), "Mean ME-A2\nsingle (pp)": pp(r.mean_ME_A2_single),
                     "Balanced −\nbest single (pp)": spp(r.CE2_balanced_minus_best_single),
                     "Balance\ncheck": "yes" if r.balance_check else "no"})
    frame = pd.DataFrame(rows)
    order = {k: i for i, k in enumerate(ALL)}
    frame = frame.assign(_o=frame.Subset.map(order)).sort_values(["_o"], kind="stable").drop(columns="_o")
    return longtable(frame, "Calibration-fleet composition at fixed volume N, per detector run and arm (1\\% target; draw means "
                     "over five nested subsamples). Δcov is the within-engine coverage effect CE1 (positive = calibrating on the "
                     "engine's own class transports better); the balance check compares the class-balanced design with the mean "
                     "single-engine design.", "tab:composition", align="lllrrlrrrl", rule_between="Subset",
                     note="Source: results/extension/summary/composition\\_run\\_summary.csv. DS03 is a reference; DS02 and "
                          "DS08c are not composition-eligible (single-class calibration pools).")


def s_composition_extra(inp):
    boot = inp.csv(SUM / "composition_bootstrap.csv")
    rows = [{"Arm": ARM[r.arm], "Statistic": r.statistic, "Point (pp)": spp(r.point),
             "95% interval (pp)": f"[{spp(r.ci_lower_95)}, {spp(r.ci_upper_95)}]", "Engines": int(r.engines),
             "Families": int(r.families)} for _, r in boot.iterrows()]
    text = longtable(pd.DataFrame(rows), "Composition bootstrap (family, then subset, then audit engine; 2,000 replicates) of "
                     "the median over families of the family-median per-engine coverage effect (1\\% target).", "tab:compboot",
                     align="lp{6.5cm}rrrr", note="Source: results/extension/summary/composition\\_bootstrap.csv.")
    ce4 = inp.csv(SUM / "composition_ce4.csv")
    rows = []
    for (key, arm, same, mixed), g in ce4.groupby(["subset", "arm", "same_class_design", "mixed_design"]):
        res = g[g.detector != "cvae"].ME_A2_same_class_minus_mixed
        rows.append({"Subset": key, "Arm": ARM[arm], "Same-class design": same, "Mixed design": mixed,
                     "Residual median (pp)": spp(res.median()), "Residual runs\nsame-class worse": f"{int((res > 0).sum())}/{len(res)}",
                     "CVAE median (pp)": spp(g[g.detector == "cvae"].ME_A2_same_class_minus_mixed.median())})
    text += longtable(pd.DataFrame(rows), "CE4, engine count versus class coverage: ME-A2 of a two-engine same-class design minus "
                      "a two-engine mixed-class design sharing one engine (1\\% target; positive = the mixed design transports "
                      "better).", "tab:ce4", align="llllrrr", rule_between="Subset",
                      note="Source: results/extension/summary/composition\\_ce4.csv.")
    return text


def s_persistence(inp):
    ff = inp.all_audit("flight_false_flags")
    ff = ff[ff.nominal_fpr == ALPHA]
    we = ff.groupby(["subset", "detector", "seed", "arm", "rule"]).false_flag_rate.max().rename("WE_FFR").reset_index()
    pooled = ff.groupby(["subset", "detector", "seed", "arm", "rule"]).apply(
        lambda g: g.flagged.sum() / g.healthy_flights.sum()).rename("FFR").reset_index()
    ev = ff.groupby(["subset", "detector", "seed", "arm", "rule"]).apply(
        lambda g: (g.events_per_healthy_flight * g.healthy_flights).sum() / g.healthy_flights.sum()).rename("EV").reset_index()
    pc = inp.all_audit("persistence_calibration")
    pc = pc[pc.nominal_fpr == ALPHA]
    wpa = pc.groupby(["subset", "detector", "seed", "arm", "rule"]).PA2.max().rename("WE_PA2").reset_index()
    frame = we.merge(pooled).merge(ev).merge(wpa)
    rows = []
    for key in ALL:
        for arm in ARM:
            for rule in RULES:
                part = frame[(frame.subset == key) & (frame.arm == arm) & (frame.rule == rule)]
                res, cv = part[part.detector != "cvae"], part[part.detector == "cvae"]
                rows.append({"Subset": key, "Arm": ARM[arm], "Rule": rule,
                             "Pooled FFR (%)\nresidual median": pct(res.FFR.median()),
                             "WE-FFR (%) residual\nmedian [range]": f"{pct(res.WE_FFR.median())} [{pct(res.WE_FFR.min())}, {pct(res.WE_FFR.max())}]",
                             "Residual runs\nWE-FFR ≥ 10%": f"{int((res.WE_FFR >= 0.10).sum())}/7",
                             "Events per healthy\nflight (median)": f"{res.EV.median():.1f}",
                             "WE-PA2\n(median)": f"{res.WE_PA2.median():.2f}",
                             "CVAE WE-FFR (%)\nseed median": pct(cv.WE_FFR.median())})
    return longtable(pd.DataFrame(rows), "Alarm persistence at the locked κ (1\\% target): pooled and worst-engine healthy-flight "
                     "false-flag rates (nominal 5\\%), alarm events per healthy flight and the worst-engine persistence "
                     "calibration error PA2 (relative to the calibration-set persistent-alarm rate).", "tab:persistence",
                     align="lllrlrrrr", rule_between="Subset",
                     note="Source: results/extension/$\\langle$subset$\\rangle$/audit/flight\\_false\\_flags.csv and "
                          "persistence\\_calibration.csv. R0 single row; R1 three consecutive rows; R2 three of five rows.")


def s_matched(inp):
    ml = inp.all_audit("matched_labels")
    ml = ml[ml.nominal_fpr == ALPHA]
    short = {"earlier at matched burden": "earlier", "later at matched burden": "later", "equal": "equal", "mixed": "mixed"}
    rows = []
    for key in ALL:
        for arm in ("phase_conditioned", "quantile_regression_W"):
            for rule in RULES:
                part = ml[(ml.subset == key) & (ml.arm == arm) & (ml.rule == rule)]
                res, cv = part[part.detector != "cvae"], part[part.detector == "cvae"]
                ev = res[res.evaluable.astype(str) == "True"]
                counts = ev.matched_label.map(short).value_counts()
                rows.append({"Subset": key, "Arm vs P": ARM[arm], "Rule": rule, "Evaluable\nresidual runs": f"{len(ev)}/7",
                             "Earlier": int(counts.get("earlier", 0)), "Equal": int(counts.get("equal", 0)),
                             "Later": int(counts.get("later", 0)), "Mixed": int(counts.get("mixed", 0)),
                             "Lower curve\nmean": int((ev.curve_mean_difference < 0).sum()),
                             "CVAE labels": ", ".join(short.get(x, "n/e") if str(e) == "True" else "n/e"
                                                      for x, e in zip(cv.matched_label, cv.evaluable))})
    return longtable(pd.DataFrame(rows), "Matched-burden detection delay (frozen adversarial Part B per rule; 1\\% target): "
                     "pre-specified labels of C and Q against P over the residual runs, the number of runs with a lower curve-level "
                     "mean delay, and the CVAE seeds' labels.", "tab:matched", align="lllrrrrrrl", rule_between="Subset",
                     note="Source: results/extension/$\\langle$subset$\\rangle$/audit/matched\\_labels.csv. n/e = not evaluable "
                          "(fewer than 3 of 5 anchors supported for both arms).")


def s_abnormal(inp):
    ab = inp.all_audit("abnormal_alarm_rates")
    ab = ab[(ab.nominal_fpr == ALPHA) & (ab.rule == "R0")]
    rows = []
    for key in ALL:
        for arm in ARM:
            part = ab[(ab.subset == key) & (ab.arm == arm)]
            row = {"Subset": key, "Arm": ARM[arm]}
            for window, name in (("all_post_onset", "all post-onset flights"), ("early_first_10", "first 10 post-onset flights")):
                w = part[part.window == window]
                if w.empty:
                    row[f"Abnormal-state row alarm rate (%)\n{name}"] = "--"
                    continue
                g = w.groupby(["detector", "seed"]).apply(lambda x: x.alarms.sum() / x.n.sum()).rename("rate").reset_index()
                res, cv = g[g.detector != "cvae"].rate, g[g.detector == "cvae"].rate
                row[f"Abnormal-state row alarm rate (%)\n{name}"] = f"{pct(res.median())} [{pct(res.min())}, {pct(res.max())}]; CVAE {pct(cv.median())}"
            rows.append(row)
    return longtable(pd.DataFrame(rows), "Abnormal-state ($hs = 0$) row alarm rates at the locked thresholds (1\\% target, R0): "
                     "residual median [range] over seven runs, and the CVAE seed median. These rates are relative to the simulated "
                     "onset label, not to a discrete fault event.", "tab:abnormal", align="llll", rule_between="Subset",
                     note="Source: results/extension/$\\langle$subset$\\rangle$/audit/abnormal\\_alarm\\_rates.csv.")


def s_reference_gates(inp):
    rows = []
    for key in REF:
        rec = inp.json(EXT / key / "audit" / "audit_record.json")
        for gate, result in (rec.get("gates") or {}).items():
            rows.append({"Subset": key, "Reproduction gate": gate.replace("_", " "), "Result": str(result)})
    return longtable(pd.DataFrame(rows), "Reference-run reproduction gates (DS02 and DS03 rescored with the extension code "
                     "before any new-subset audit; Amendment 3).", "tab:gates", align="lp{7cm}p{5.5cm}",
                     note="Source: results/extension/DS02/audit/audit\\_record.json and DS03/audit/audit\\_record.json.")


def s_post_hoc(inp):
    """Post hoc checks (article Section 4.9): formatted from paper/mssp_extended/evidence/post_hoc_checks.json."""
    ph = inp.json(ROOT / "paper/mssp_extended/evidence/post_hoc_checks.json")
    noise = inp.csv(ROOT / "paper/mssp_extended/evidence/post_hoc_engine_noise.csv")
    rows = [{"Subset": r["subset"], "Engines": r["engines"], "Healthy flights\nper engine": f"{r['flights_min']}–{r['flights_max']}",
             "Calibration\nflights": r["calibration_flights"],
             "Null WE-FFR (%)\nmedian / 95th pct.": f"{pct(r['null_median'])} / {pct(r['null_q95'])}",
             "Null P(WE-FFR\n≥ 10%)": f"{r['null_p_ge_10pct']:.2f}",
             "Observed median (%)\nR0 / R1 / R2": " / ".join(pct(r[f"observed_median_{x}"]) for x in RULES),
             "Runs above null\n95th pct. R0 / R1 / R2": " / ".join(f"{round(7 * r[f'observed_share_above_null_q95_{x}'])}/7" for x in RULES)}
            for r in ph["we_ffr_null"]]
    text = longtable(pd.DataFrame(rows), "Post hoc: worst-engine healthy-flight false-flag rate (WE-FFR) under P against a "
                     "perfect-calibration reference (each healthy flight flagged independently with probability p, "
                     "p drawn from the exceedance distribution of the empirical 0.95 quantile of the calibration flights; "
                     "residual runs, 1\\% target).", "tab:posthoc_ffr", align="lrrrrrrr",
                     note="Source: paper/mssp\\_extended/evidence/post\\_hoc\\_checks.json (post\\_hoc\\_checks.py).")
    rows = []
    for (key, arm), g in noise.groupby(["subset", "arm"], sort=False):
        mat = g[g.observed_A2 >= 0.5 * ALPHA]
        rows.append({"Subset": key, "Arm": ARM[arm], "Median design\neffect": f"{g.design_effect.median():.0f}",
                     "Median SE of engine\nFPR (pp)": pp(g.se_overall_fpr.median()),
                     "Null P(A2 ≥\n0.5 pp)": f"{g.null_p_material.mean():.2f}",
                     "Observed share\nA2 ≥ 0.5 pp": f"{(g.observed_A2 >= 0.5 * ALPHA).mean():.2f}",
                     "Observed share above\nnull 95th pct.": f"{(g.observed_A2 > g.null_A2_q95).mean():.2f}",
                     "Material errors\nunder-alarming": "--" if mat.empty else f"{(mat.worst_sign == 'under').mean():.2f}"})
    order = {k: i for i, k in enumerate(NEW)}
    frame = pd.DataFrame(rows).assign(_o=lambda f: f.Subset.map(order)).sort_values(["_o"], kind="stable").drop(columns="_o")
    text += longtable(frame, "Post hoc: approximate sampling reference for per-engine A2 (each phase FPR equal to α with a "
                      "binomial standard error inflated by the engine's flight-clustered design effect at the locked threshold; "
                      "engine–run pairs of the residual runs, 1\\% target, R0). The design effect includes true between-flight "
                      "variation, so the reference is conservative.", "tab:posthoc_a2", align="llrrrrrr", rule_between="Subset",
                      note="Source: paper/mssp\\_extended/evidence/post\\_hoc\\_engine\\_noise.csv.")
    tf = ph["two_flight_confirmation"]
    rows = [{"Arm": ARM[a], "WE-FFR single\nflight (median %)": pct(v["we_single_median"]),
             "Runs ≥ 10%\nsingle": f"{v['we_single_ge_10pct']}/{v['residual_runs']}",
             "WE two-flight\nconfirmed (median %)": pct(v["we_two_median"]),
             "Runs at 0 /\n≥ 10% (two-flight)": f"{v['we_two_zero']} / {v['we_two_ge_10pct']}",
             "Median delay (flights)\nsingle → two-flight": f"{v['median_delay_single']:g} → {v['median_delay_two']:g}"}
            for a, v in tf.items()]
    text += longtable(pd.DataFrame(rows), "Post hoc: two-consecutive-flight confirmation at the locked κ (not pre-specified; "
                      "R0 rows, residual runs, 1\\% target): worst-engine healthy confirmed-alert rate and median detection "
                      "delay.", "tab:posthoc_confirm", align="lrrrrr",
                      note="Source: paper/mssp\\_extended/evidence/post\\_hoc\\_checks.json; delays from detection\\_delay.csv "
                           "(two\\_flight\\_persistence\\_delay).")
    return text


def s_focused_validation(inp):
    """Final focused validation (article Sections 3.10 and 4.8): results/extension/focused_validation/summary."""
    root = EXT / "focused_validation" / "summary"
    note = "Source: results/extension/focused\\_validation/summary/{} (plan docs/extension/FOCUSED\\_VALIDATION\\_PLAN.md)."
    eng = inp.csv(root / "engine_summary.csv")
    order = {k: i for i, k in enumerate(NEW)}
    eng = eng.assign(_o=eng.subset.map(order), _a=eng.arm.map({a: i for i, a in enumerate(ARM)})).sort_values(["_o", "unit", "_a"])
    rows = [{"Subset": r.subset, "Engine\n(class)": f"{r.unit} ({r.flight_class})",
             "Class in\ncalibration": "yes" if r.class_in_calibration else "no", "Healthy\nflights": int(r.healthy_flights),
             "Arm": ARM[r.arm], "Observed A2\n(pp)": pp(r.observed_A2_median), "NF50\n(pp)": pp(r.NF50_median),
             "NF95\n(pp)": pp(r.NF95_median), "Residual runs\nabove NF95": f"{int(r.residual_runs_exceeding)}/7",
             "Clearly\nexceeds": "yes" if r.clearly_exceeds else "no", "CVAE runs\nabove NF95": f"{int(r.cvae_runs_exceeding)}/3"}
            for r in eng.itertuples()]
    text = longtable(pd.DataFrame(rows), "Final focused validation, component 1: fleet-calibrated per-engine A2 against the "
                     "engine's own cross-fitted self-calibration reference (medians over the seven residual runs; 5-fold "
                     "cross-fit, 200 repetitions; 1\\% target). The reference describes what calibrating on the engine's own "
                     "flights achieves and understates flight-to-flight sampling noise (article Section 3.10).",
                     "tab:fv_noise", align="lllrlrrrrlr", rule_between="Subset", note=note.format("engine\\_summary.csv"))
    loc = inp.csv(root / "local_engine_summary.csv")
    loc = loc.assign(_o=loc.subset.map(order)).sort_values(["_o", "unit", "arm"])
    rows = [{"Subset": r.subset, "Engine\n(class)": f"{r.unit} ({r.flight_class})", "Arm": ARM[r.arm],
             "Evaluation\nflights": int(r.eval_flights), "Fleet A2\n(pp)": pp(r.fleet_eval_A2_median),
             "Local A2\n(pp)": pp(r.local_A2_median), "Change\n(pp)": spp(r.improvement_median),
             "Runs\nimproved": f"{int(r.runs_improved)}/7", "NF95\\textsuperscript{K}\n(pp)": pp(r.NFK95_median),
             "Local within\nNF95K (runs)": f"{int(r.runs_local_within_NFK95)}/7",
             "Fleet within\nNF95K (runs)": f"{int(r.runs_fleet_within_NFK95)}/7",
             "Local within\nNF95 (runs)": f"{int(r.runs_local_within_NF95)}/7"} for r in loc.itertuples()]
    frame = pd.DataFrame(rows)
    frame.columns = [c.replace("NF95\\textsuperscript{K}", "NF95K") for c in frame.columns]
    text += longtable(frame, "Final focused validation, component 3: local recalibration on each audit engine's first five "
                      "healthy flights, evaluated on its remaining healthy flights (medians over the seven residual runs; "
                      "1\\% target). Change = fleet minus local A2 (positive = local better); NF95K = 95th percentile of the "
                      "matched reference from 200 random five-flight subsets.", "tab:fv_local", align="lllrrrrrrrrr",
                      rule_between="Subset", size=r"\scriptsize", note=note.format("local\\_engine\\_summary.csv"))
    width = inp.csv(root / "bootstrap_width_comparison.csv")
    width = width.assign(_o=width.subset.map(order)).sort_values(["_o", "metric"])
    rows = [{"Subset": r.subset, "Metric": r.metric, "Width ratio\n(class-preserving / original)": f"{r.median_width_ratio:.3f}",
             "Share of width from\nclass omission": f"{100 * r.share_of_width_from_class_omission:.0f}%",
             "Runs including zero\noriginal / class-preserving": f"{int(r.original_includes_zero)}/7 / "
                                                                  f"{int(r.class_preserving_includes_zero)}/7"}
            for r in width.itertuples()]
    text += longtable(pd.DataFrame(rows), "Final focused validation, component 2: per-subset bootstrap intervals with "
                      "calibration engines resampled within flight class against the original U-EXT1 design (identical audit "
                      "plans; medians over the seven residual runs; 1\\% target).", "tab:fv_width", align="llrrr",
                      rule_between="Subset", note=note.format("bootstrap\\_width\\_comparison.csv"))
    u2 = inp.csv(root / "uext2_original_vs_class_preserving.csv")
    rows = [{"Detector family": DET.get(r.detector_family, "CVAE vs residual"), "Quantity": r.quantity,
             "Median over\nfamilies (pp)": spp(r.point_median_over_families),
             "Original interval\n(pp)": f"[{spp(r.ci_lower_95_original)}, {spp(r.ci_upper_95_original)}]",
             "Class-preserving\ninterval (pp)": f"[{spp(r.ci_lower_95_class_preserving)}, {spp(r.ci_upper_95_class_preserving)}]",
             "Width ratio": f"{r.width_ratio:.2f}"} for r in u2.itertuples()]
    text += longtable(pd.DataFrame(rows), "Final focused validation, component 2: cross-dataset (U-EXT2) intervals recomputed "
                      "from the class-preserving replicates with the same routine and seed.", "tab:fv_uext2", align="llrrrr",
                      note=note.format("uext2\\_original\\_vs\\_class\\_preserving.csv"))
    return text


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

PREAMBLE = r"""\documentclass[10pt]{article}
\usepackage[a4paper,margin=1.8cm]{geometry}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern,amsmath,booktabs,longtable,makecell,pdfpages,array}
\usepackage[hidelinks]{hyperref}
\DeclareUnicodeCharacter{2212}{\ensuremath{-}}
\DeclareUnicodeCharacter{03B1}{\ensuremath{\alpha}}
\DeclareUnicodeCharacter{03BA}{\ensuremath{\kappa}}
\DeclareUnicodeCharacter{0394}{\ensuremath{\Delta}}
\DeclareUnicodeCharacter{2265}{\ensuremath{\geq}}
\DeclareUnicodeCharacter{2264}{\ensuremath{\leq}}
\DeclareUnicodeCharacter{2192}{\ensuremath{\rightarrow}}
\DeclareUnicodeCharacter{00D7}{\ensuremath{\times}}
\renewcommand{\thetable}{S\arabic{table}}
\setlength{\LTcapwidth}{\textwidth}
\title{Supplementary material\\[4pt]\large False-Alarm Calibration Transport Across Engines in Full-Flight Aero-Engine
Anomaly Detection: A Multi-Subset Audit of Context Conditioning and Calibration-Fleet Coverage}
\author{Jinghang Mei}
\date{}
\begin{document}
\maketitle
"""

INTRO = r"""\noindent\textbf{Contents.} Part A reports the frozen multi-subset extension (Sections 3--4 of the article): cohort
eligibility, engine roles, locks and numerical checks, every detector run's phase FPRs and transport metrics, per-engine
errors, bootstrap intervals, target sensitivity, calibration-fleet composition, alarm persistence, matched-burden delay,
abnormal-state alarm rates, the reference reproduction gates, the post hoc checks of Section 4.9 and the final focused validation of Section 4.8. Part B reproduces, unchanged, the supplement of the
pre-extension study: the frozen DS02 discovery and one-shot DS03 confirmation, the post-confirmation analyses and the
adversarial validation, which Section 4.1 of the article summarizes.

\noindent\textbf{Conventions.} FPRs are healthy ($hs = 1$) row-level false-positive rates; pp = percentage points. Runs:
PCA (one run), Isolation Forest (IF), past-only LSTM and CVAE (seeds s0--s2). Arms: P pooled; C retrospective
phase-conditioned (uses complete-flight phases); Q continuous-context quantile regression (adversarial control). Families:
F1 = DS01, F2 = DS04, F3 = DS05--DS07, F4 = DS08a, F5 = DS08c; DS02 and DS03 are references and decide no hypothesis.
Machine-readable values: results/extension/ and paper/mssp\_extended/evidence/ (with SHA-256 sums); every number in the
article is traced in docs/extension/EXTENSION\_EVIDENCE\_LEDGER.csv.

\noindent\textbf{Amendments} (docs/extension/AMENDMENTS.md; each preceded every affected outcome). (1) Two classification
rules (original-story class and H2 verdict) were completed so that every outcome configuration has a class; no threshold
changed. (2) After a stop rule fired on a non-finite CVAE training loss (DS01), the encoder log-variance was bounded and
gradients were clipped at norm 1.0 for every subset and seed; the DS01 lock was rerun from scratch. (3) Healthy and
post-onset audit rows are scored in separate calls, as in the frozen stages, after the first DS03 reference attempt failed a
reproduction gate at float32 rounding level; the reference work was rerun and passed before any new-subset audit.
"""


def build(inp):
    parts = [PREAMBLE, r"\section*{Part A. Multi-subset extension}", INTRO, r"\clearpage",
             r"\subsection*{A.1 Cohort, roles, locks and training}", s_cohort(inp), s_roles(inp), s_locks(inp), s_training(inp),
             r"\clearpage", r"\subsection*{A.2 Calibration transport (1\% target)}", s_transport_runs(inp), s_paired(inp),
             s_engines(inp), r"\subsection*{A.3 Uncertainty and target sensitivity}", s_uext1(inp), s_uext2(inp), s_targets(inp),
             r"\subsection*{A.4 Calibration-fleet composition}", s_composition(inp), s_composition_extra(inp),
             r"\subsection*{A.5 Alarm persistence, matched-burden delay and abnormal-state alarm rates}", s_persistence(inp),
             s_matched(inp), s_abnormal(inp), r"\subsection*{A.6 Reference reproduction}", s_reference_gates(inp),
             r"\subsection*{A.7 Post hoc checks (article Section 4.9; not pre-specified)}", s_post_hoc(inp),
             r"\subsection*{A.8 Final focused validation (article Sections 3.10 and 4.8; post hoc)}",
             s_focused_validation(inp),
             r"\clearpage", r"\section*{Part B. Supplement of the pre-extension study (included unchanged)}",
             r"\noindent The following pages reproduce, unchanged, the committed pre-extension supplement (SHA-256 \texttt{" + sha256(PRE_SUPP)[:16] + r"\ldots}); its table and figure numbers are its own. Source file:\\ \url{paper/mssp/supplement/supplement.pdf}.",
             r"\includepdf[pages=-]{../../mssp/supplement/supplement.pdf}", r"\end{document}"]
    inp.used.add(PRE_SUPP)
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-compile", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    inp = Inputs()
    tex = build(inp)
    (OUT / "supplement.tex").write_text(tex, encoding="utf-8")
    if not args.no_compile:
        for _ in range(3):
            result = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "supplement.tex"], cwd=OUT,
                                    capture_output=True, text=True, errors="replace")
            if result.returncode != 0:
                print(result.stdout[-4000:])
                sys.exit(1)
    record = {"inputs": {str(p.relative_to(ROOT)): sha256(p) for p in sorted(inp.used)},
              "outputs": {str(p.relative_to(ROOT)): sha256(p) for p in (OUT / "supplement.tex", OUT / "supplement.pdf")
                          if p.exists()},
              "builder": str(Path(__file__).resolve().relative_to(ROOT)), "builder_sha256": sha256(Path(__file__).resolve()),
              "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (OUT / "supplement.provenance.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'supplement.tex'}; inputs {len(inp.used)}")


if __name__ == "__main__":
    main()
