"""Shakedown cross-check: extension outputs on DS02/DS03 must reproduce the committed frozen tables.

For the frozen arms (P, C), the frozen rule (R0) and the seven residual runs, every overlapping quantity
of the extension code is compared cell by cell with:
- post-confirmation Stage D and Stage E (`results/mssp_mitigation/`);
- adversarial Parts A and B (`results/mssp_adversarial/`).

Counts must be equal; floats must agree within 1e-12. Any mismatch is a code defect that must be fixed
(and the reference work rerun) before the first new-cohort audit (protocol section 10, shakedown).
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import ext_common as ec

MIT = ec.ROOT / "results/mssp_mitigation"
ADV = ec.ROOT / "results/mssp_adversarial"
FROZEN_ARMS = ("pooled", "phase_conditioned")
ATOL = 1e-12


def ours(key, table):
    frame = pd.read_csv(ec.RESULTS / key / "audit" / f"{table}.csv")
    return frame[frame.detector != "cvae"]


def compare(name, left, right, keys, exact=(), close=()):
    left = left.copy()
    right = right.copy()
    for frame in (left, right):
        for column in keys:
            frame[column] = frame[column].astype(str)
    merged = left.merge(right, on=list(keys), suffixes=("_ext", "_frozen"), how="inner")
    problems = []
    if len(merged) != len(right):
        problems.append(f"{len(right)} frozen rows but {len(merged)} matched")
    for column in exact:
        a, b = merged[f"{column}_ext"], merged[f"{column}_frozen"]
        bad = ~((a == b) | (a.isna() & b.isna()))
        if bad.any():
            problems.append(f"{column}: {int(bad.sum())} mismatches")
    for column in close:
        a = merged[f"{column}_ext"].astype(float).to_numpy()
        b = merged[f"{column}_frozen"].astype(float).to_numpy()
        same = np.isclose(a, b, rtol=0, atol=ATOL) | (np.isnan(a) & np.isnan(b)) | (a == b)
        if not same.all():
            problems.append(f"{column}: {int((~same).sum())} mismatches (max |diff| "
                            f"{np.nanmax(np.abs(a - b)[~same]) if (~same).any() else 0:.3g})")
    return {"check": name, "rows_compared": int(len(merged)), "status": "PASS" if not problems else "FAIL",
            "problems": problems}


def check_subset(key):
    lower = key.lower()
    results = []
    # 1. Healthy phase FPR under P and C (Stage D)
    frozen = pd.read_csv(MIT / lower / "stage_d" / "healthy_phase_fpr_by_scheme.csv")
    frozen = frozen[frozen.scheme.isin(FROZEN_ARMS)].rename(columns={"scheme": "arm"})
    mine = ours(key, "phase_fpr")
    results.append(compare("stage_d healthy_phase_fpr_by_scheme (P, C)", mine[mine.arm.isin(FROZEN_ARMS)], frozen,
                           ["detector", "seed", "nominal_fpr", "arm", "unit", "phase"], exact=("n", "alarms"),
                           close=("rate",)))
    # 2. Calibration-quality metrics (adversarial Part A)
    frozen = pd.read_csv(ADV / lower / "calibration_quality" / "calibration_quality_metrics.csv")
    frozen = frozen[frozen.scheme.isin(FROZEN_ARMS)].rename(columns={"scheme": "arm"})
    mine = ours(key, "calibration_quality")
    results.append(compare("adversarial calibration_quality_metrics (P, C)", mine[mine.arm.isin(FROZEN_ARMS)], frozen,
                           ["detector", "seed", "nominal_fpr", "arm", "unit", "weighting"],
                           close=("spread", "max_abs_error", "rms_error", "mean_abs_error", "overall_abs_error",
                                  "climb_fpr", "cruise_fpr", "descent_fpr")))
    # 3. Healthy-flight false flags at locked kappa, R0 (Stage E)
    frozen = pd.read_csv(MIT / lower / "stage_e" / "healthy_flight_false_flags_with_delay.csv")
    frozen = frozen[frozen.scheme.isin(FROZEN_ARMS)].rename(columns={"scheme": "arm"})
    mine = ours(key, "flight_false_flags")
    mine = mine[(mine.rule == "R0") & mine.arm.isin(FROZEN_ARMS)]
    results.append(compare("stage_e healthy_flight_false_flags (P, C; R0)", mine, frozen,
                           ["detector", "seed", "nominal_fpr", "arm", "unit"], exact=("healthy_flights", "flagged"),
                           close=("false_flag_rate", "kappa")))
    # 4. Detection delay at locked kappa, R0 (Stage E)
    frozen = pd.read_csv(MIT / lower / "stage_e" / "detection_delay.csv")
    frozen = frozen[frozen.scheme.isin(FROZEN_ARMS)].rename(columns={"scheme": "arm"})
    mine = ours(key, "detection_delay")
    mine = mine[(mine.rule == "R0") & mine.arm.isin(FROZEN_ARMS)].rename(
        columns={"two_flight_persistence_delay": "persistence_delay_flights"})
    results.append(compare("stage_e detection_delay (P, C; R0)", mine, frozen,
                           ["detector", "seed", "nominal_fpr", "arm", "unit"],
                           exact=("censored", "post_onset_flights", "healthy_flights", "healthy_flagged"),
                           close=("delay_flights", "persistence_delay_flights")))
    # 5. Abnormal-state alarm rates, overall phase, R0 (Stage E)
    frozen = pd.read_csv(MIT / lower / "stage_e" / "abnormal_alarm_rates.csv")
    frozen = frozen[frozen.scheme.isin(FROZEN_ARMS) & (frozen.phase == "overall")
                    & frozen.window.isin(["all_post_onset", "early_first_10"])].rename(columns={"scheme": "arm"})
    mine = ours(key, "abnormal_alarm_rates")
    mine = mine[(mine.rule == "R0") & mine.arm.isin(FROZEN_ARMS)]
    results.append(compare("stage_e abnormal_alarm_rates (P, C; R0; overall)", mine, frozen,
                           ["detector", "seed", "nominal_fpr", "arm", "window", "unit"], exact=("n", "alarms"),
                           close=("rate",)))
    # 6. Curve-level matched summary and matched comparisons, R0 (adversarial Part B)
    frozen = pd.read_csv(ADV / lower / "matched_delay" / "curve_level_summary.csv")
    frozen = frozen[frozen.scheme.isin(FROZEN_ARMS)].rename(columns={"scheme": "arm"})
    mine = ours(key, "curve_level_summary")
    mine = mine[(mine.rule == "R0") & mine.arm.isin(FROZEN_ARMS)]
    results.append(compare("adversarial curve_level_summary (P, C; R0)", mine, frozen,
                           ["detector", "seed", "nominal_fpr", "arm"],
                           exact=("curve_grid_points_excluded",), close=("curve_mean_median_delay_ffr_2.5_to_20",)))
    frozen = pd.read_csv(ADV / lower / "matched_delay" / "matched_false_flag_comparisons.csv")
    frozen = frozen[frozen.arm == "phase_conditioned"].rename(columns={"rule": "match_rule"})
    mine = ours(key, "matched_comparisons")
    mine = mine[(mine.rule == "R0") & (mine.arm == "phase_conditioned")]
    results.append(compare("adversarial matched_false_flag_comparisons (C vs P; R0)", mine, frozen,
                           ["detector", "seed", "nominal_fpr", "arm", "match_rule", "anchor_ffr"],
                           exact=("supported", "earlier", "same", "later"),
                           close=("pooled_ffr", "arm_ffr", "paired_lower_median_difference",
                                  "difference_of_median_delays", "arm_median_delay", "pooled_median_delay")))
    frozen = pd.read_csv(ADV / lower / "matched_delay" / "matched_labels.csv")
    frozen = frozen[frozen.arm == "phase_conditioned"]
    mine = ours(key, "matched_labels")
    mine = mine[(mine.rule == "R0") & (mine.arm == "phase_conditioned")].rename(
        columns={"matched_label_not_exceeding": "matched_label_not_exceeding_rule"})
    results.append(compare("adversarial matched_labels (C vs P; R0)", mine, frozen,
                           ["detector", "seed", "nominal_fpr", "arm"],
                           exact=("supported_anchors", "matched_label", "matched_label_not_exceeding_rule"),
                           close=("curve_mean_pooled", "curve_mean_arm")))
    return results


def main(keys=ec.REFERENCE_ORDER):
    report = {key: check_subset(key) for key in keys}
    status = all(r["status"] == "PASS" for rows in report.values() for r in rows)
    for key, rows in report.items():
        for r in rows:
            print(f"{key} {r['status']:4s} {r['check']} ({r['rows_compared']} rows) {'; '.join(r['problems'])}")
    return status, report


if __name__ == "__main__":
    ok, report = main()
    out = ec.RESULTS / "shakedown"
    out.mkdir(parents=True, exist_ok=True)
    ec.write_json(out / f"shakedown_check_{ec.now_utc().replace(':', '')}.json",
                  {"all_pass": ok, "report": report, "git_head": ec.git_sha()})
    sys.exit(0 if ok else 1)
