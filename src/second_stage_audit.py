"""Second-stage falsification audit for N-CMAPSS DS02.

Compares the original raw-sensor PCA detector with a detector fitted to sensor
residuals after a training-only operating-condition regression on W.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.metrics import balanced_accuracy_score, r2_score
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.tree import DecisionTreeClassifier


ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("NCMAPSS_DS02_H5", ROOT / "N-CMAPSS/N-CMAPSS_DS02-006.h5"))
OUT = ROOT / "results/second_stage"
FIG = ROOT / "figures/second_stage"
SENSORS = ["T24", "T30", "T48", "T50", "P15", "P2", "P21", "P24",
           "Ps30", "P40", "P50", "Nf", "Nc", "Wf"]
W_NAMES = ["alt", "Mach", "TRA", "T2"]
PHASES = ("climb", "cruise", "descent")
TRAIN_UNITS = (2, 5, 10, 16)
CAL_UNITS = (18, 20)
TEST_UNITS = (11, 14, 15)
FC3_DEV = (2, 5, 10, 16, 18, 20)
PCA_COMPONENTS = 5
RIDGE_ALPHA = 1.0


def phase_labels(alt, units, cycles):
    """Return original and predeclared altitude-rate sensitivity labels."""
    primary = np.empty(len(alt), dtype=np.int8)
    alternative = np.empty(len(alt), dtype=np.int8)
    boundary = np.flatnonzero((np.diff(units) != 0) | (np.diff(cycles) != 0)) + 1
    starts, ends = np.r_[0, boundary], np.r_[boundary, len(alt)]
    audit = []
    for start, end in zip(starts, ends):
        z = alt[start:end]
        lo, hi = float(z.min()), float(z.max())
        # Original: first/last crossing of 90% of the within-flight altitude range.
        top = np.flatnonzero(z >= lo + .90 * (hi - lo))
        p_first, p_last = int(top[0]), int(top[-1])
        primary[start:start + p_first] = 0
        primary[start + p_first:start + p_last + 1] = 1
        primary[start + p_last + 1:end] = 2
        # Sensitivity rule: 85% altitude plus stable centered 60-s altitude rate.
        # N-CMAPSS is sampled at 1 Hz. Edge values use the nearest available point.
        half = 30
        left = np.maximum(np.arange(len(z)) - half, 0)
        right = np.minimum(np.arange(len(z)) + half, len(z) - 1)
        rate = (z[right] - z[left]) / np.maximum(right - left, 1)
        stable_top = np.flatnonzero(
            (z >= lo + .85 * (hi - lo)) & (np.abs(rate) <= 2.0)
        )
        if stable_top.size == 0:
            raise RuntimeError(f"No alternative cruise rows for unit {units[start]}, cycle {cycles[start]}")
        a_first, a_last = int(stable_top[0]), int(stable_top[-1])
        alternative[start:start + a_first] = 0
        alternative[start + a_first:start + a_last + 1] = 1
        alternative[start + a_last + 1:end] = 2
        audit.append({
            "unit": int(units[start]), "cycle": int(cycles[start]), "rows": end - start,
            "alt_min": lo, "alt_max": hi,
            "primary_climb_rows": p_first, "primary_cruise_rows": p_last - p_first + 1,
            "primary_descent_rows": end - start - p_last - 1,
            "alternative_climb_rows": a_first, "alternative_cruise_rows": a_last - a_first + 1,
            "alternative_descent_rows": end - start - a_last - 1,
        })
    return primary, alternative, pd.DataFrame(audit)


def load_split(h5, split):
    a = h5[f"A_{split}"][:]
    w = h5[f"W_{split}"][:]
    x = h5[f"X_s_{split}"][:]
    assert [v.decode() for v in h5["A_var"][:]] == ["unit", "cycle", "Fc", "hs"]
    assert [v.decode() for v in h5["W_var"][:]] == W_NAMES
    assert [v.decode() for v in h5["X_s_var"][:]] == SENSORS
    units, cycles = a[:, 0].astype(np.int16), a[:, 1].astype(np.int16)
    primary, alternative, phase_audit = phase_labels(w[:, 0], units, cycles)
    meta = pd.DataFrame({
        "unit": units, "cycle": cycles, "flight_class": a[:, 2].astype(np.int8),
        "healthy": a[:, 3].astype(np.int8), "phase_primary": primary,
        "phase_alt_rate": alternative,
    })
    for unit in np.unique(units):
        state = meta.loc[meta.unit == unit, "healthy"].to_numpy()
        assert state[0] == 1 and np.all(np.diff(state) <= 0)
    phase_audit.insert(0, "split", split)
    return x, w, meta, phase_audit


def select(data, meta, units):
    mask = (meta.healthy.to_numpy() == 1) & meta.unit.isin(units).to_numpy()
    return data[mask], meta.loc[mask].reset_index(drop=True)


class RawDetector:
    def fit(self, x, _w):
        self.scaler = StandardScaler().fit(x)
        z = self.scaler.transform(x)
        self.pca = PCA(n_components=PCA_COMPONENTS, svd_solver="full").fit(z)
        self.explained_variance = float(self.pca.explained_variance_ratio_.sum())
        return self

    def score(self, x, _w):
        z = self.scaler.transform(x)
        return np.mean((z - self.pca.inverse_transform(self.pca.transform(z))) ** 2, axis=1)


class CorrectedDetector:
    def fit(self, x, w):
        self.w_scaler = StandardScaler().fit(w)
        self.poly = PolynomialFeatures(degree=3, include_bias=False)
        phi = self.poly.fit_transform(self.w_scaler.transform(w))
        self.regression = Ridge(alpha=RIDGE_ALPHA).fit(phi, x)
        residual = x - self.regression.predict(phi)
        del phi
        self.residual_scaler = StandardScaler().fit(residual)
        z = self.residual_scaler.transform(residual)
        self.pca = PCA(n_components=PCA_COMPONENTS, svd_solver="full").fit(z)
        self.explained_variance = float(self.pca.explained_variance_ratio_.sum())
        return self

    def residual(self, x, w):
        phi = self.poly.transform(self.w_scaler.transform(w))
        return x - self.regression.predict(phi)

    def score(self, x, w):
        z = self.residual_scaler.transform(self.residual(x, w))
        return np.mean((z - self.pca.inverse_transform(self.pca.transform(z))) ** 2, axis=1)

    def expected(self, w):
        return self.regression.predict(self.poly.transform(self.w_scaler.transform(w)))


def score_summary(scores, meta, detector, phase_definition, subset):
    phase_col = "phase_primary" if phase_definition == "primary" else "phase_alt_rate"
    frame = meta[["unit", "flight_class", phase_col]].copy()
    frame["score"] = scores
    rows = []
    groups = [(str(int(u)), g) for u, g in frame.groupby("unit")] + [("all", frame)]
    for unit, unit_frame in groups:
        for phase_id, group in unit_frame.groupby(phase_col):
            s = group.score.to_numpy()
            rows.append({
                "detector": detector, "phase_definition": phase_definition, "subset": subset,
                "unit": unit, "flight_class": int(group.flight_class.iloc[0]) if unit != "all" else "mixed",
                "phase": PHASES[int(phase_id)], "n": len(s), "mean": s.mean(),
                "median": np.median(s), "p90": np.quantile(s, .90),
                "p95": np.quantile(s, .95), "p99": np.quantile(s, .99),
            })
    return rows


def row_rates(scores, meta, threshold, detector, phase_definition, subset):
    phase_col = "phase_primary" if phase_definition == "primary" else "phase_alt_rate"
    rows = []
    groups = [(str(int(u)), meta.unit.to_numpy() == u) for u in sorted(meta.unit.unique())]
    groups += [("all", np.ones(len(meta), dtype=bool))]
    for unit, unit_mask in groups:
        fc = int(meta.loc[unit_mask, "flight_class"].iloc[0]) if unit != "all" else "mixed"
        for phase_id, phase in [(None, "overall"), *enumerate(PHASES)]:
            mask = unit_mask if phase_id is None else unit_mask & (meta[phase_col].to_numpy() == phase_id)
            alarms = scores[mask] > threshold
            rows.append({
                "detector": detector, "phase_definition": phase_definition, "subset": subset,
                "unit": unit, "flight_class": fc, "phase": phase, "n": int(mask.sum()),
                "false_alarms": int(alarms.sum()), "false_alarm_rate": float(alarms.mean()),
                "threshold": threshold,
            })
    return rows


def transfer_rates(cal_scores, cal_meta, audit_scores, audit_meta, detector, phase_definition):
    phase_col = "phase_primary" if phase_definition == "primary" else "phase_alt_rate"
    rows = []
    for cal_id, cal_phase in enumerate(PHASES):
        threshold = float(np.quantile(cal_scores[cal_meta[phase_col].to_numpy() == cal_id], .99, method="higher"))
        groups = [(str(int(u)), audit_meta.unit.to_numpy() == u) for u in sorted(audit_meta.unit.unique())]
        groups += [("all", np.ones(len(audit_meta), dtype=bool))]
        for unit, unit_mask in groups:
            fc = int(audit_meta.loc[unit_mask, "flight_class"].iloc[0]) if unit != "all" else "mixed"
            for test_id, test_phase in enumerate(PHASES):
                mask = unit_mask & (audit_meta[phase_col].to_numpy() == test_id)
                alarms = audit_scores[mask] > threshold
                rows.append({
                    "detector": detector, "phase_definition": phase_definition,
                    "unit": unit, "flight_class": fc, "calibration_phase": cal_phase,
                    "test_phase": test_phase, "threshold": threshold, "n": int(mask.sum()),
                    "false_alarms": int(alarms.sum()), "false_alarm_rate": float(alarms.mean()),
                })
    return rows


def phase_probe(cal_scores, cal_meta, audit_scores, audit_meta, detector, phase_definition):
    phase_col = "phase_primary" if phase_definition == "primary" else "phase_alt_rate"
    transform = lambda s: np.log10(np.maximum(s, 1e-15)).reshape(-1, 1)
    probe = DecisionTreeClassifier(max_depth=3, min_samples_leaf=1000,
                                   class_weight="balanced", random_state=0)
    probe.fit(transform(cal_scores), cal_meta[phase_col].to_numpy())
    pred = probe.predict(transform(audit_scores))
    rows = []
    for unit, mask in [(str(int(u)), audit_meta.unit.to_numpy() == u) for u in sorted(audit_meta.unit.unique())] + [("all", np.ones(len(audit_meta), dtype=bool))]:
        truth = audit_meta.loc[mask, phase_col].to_numpy()
        rows.append({
            "detector": detector, "phase_definition": phase_definition, "unit": unit,
            "flight_class": int(audit_meta.loc[mask, "flight_class"].iloc[0]) if unit != "all" else "mixed",
            "n": int(mask.sum()), "balanced_accuracy": balanced_accuracy_score(truth, pred[mask]),
            "chance_balanced_accuracy": 1 / 3,
        })
    return rows


def count_events(alarm):
    return int(np.sum(alarm & ~np.r_[False, alarm[:-1]]))


def flight_metrics(scores, meta, threshold, detector, phase_definition, subset="official_test"):
    phase_col = "phase_primary" if phase_definition == "primary" else "phase_alt_rate"
    detail = []
    work = meta[["unit", "cycle", "flight_class", phase_col]].copy()
    work["alarm"] = scores > threshold
    for (unit, cycle), flight in work.groupby(["unit", "cycle"], sort=False):
        alarm = flight.alarm.to_numpy()
        detail.append({
            "detector": detector, "phase_definition": phase_definition, "subset": subset,
            "unit": int(unit), "cycle": int(cycle), "flight_class": int(flight.flight_class.iloc[0]),
            "phase": "overall", "rows": len(flight), "false_alarms": int(alarm.sum()),
            "any_false_alarm": int(alarm.any()), "false_alarm_events": count_events(alarm),
        })
        for phase_id, phase in enumerate(PHASES):
            part = flight[flight[phase_col] == phase_id].alarm.to_numpy()
            detail.append({
                "detector": detector, "phase_definition": phase_definition, "subset": subset,
                "unit": int(unit), "cycle": int(cycle), "flight_class": int(flight.flight_class.iloc[0]),
                "phase": phase, "rows": len(part), "false_alarms": int(part.sum()),
                "any_false_alarm": int(part.any()), "false_alarm_events": count_events(part),
            })
    detail = pd.DataFrame(detail)
    summary = []
    for unit, group in list(detail.groupby("unit")) + [("all", detail)]:
        for phase, part in group.groupby("phase"):
            summary.append({
                "detector": detector, "phase_definition": phase_definition, "subset": subset,
                "unit": unit, "flight_class": int(part.flight_class.iloc[0]) if unit != "all" else "mixed",
                "phase": phase, "healthy_flights": len(part),
                "flights_with_false_alarm": int(part.any_false_alarm.sum()),
                "fraction_flights_with_false_alarm": float(part.any_false_alarm.mean()),
                "false_alarm_events": int(part.false_alarm_events.sum()),
                "events_per_healthy_flight": float(part.false_alarm_events.mean()),
            })
    return detail.to_dict("records"), summary


def fit_pair(train_x, train_w, targets):
    detectors = {"raw_pca": RawDetector().fit(train_x, train_w),
                 "condition_corrected_pca": CorrectedDetector().fit(train_x, train_w)}
    return detectors, {name: {key: model.score(x, w) for key, (x, w) in targets.items()}
                       for name, model in detectors.items()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    with h5py.File(DATA) as h5:
        dev_x_all, dev_w_all, dev_meta_all, dev_phase_audit = load_split(h5, "dev")
        test_x_all, test_w_all, test_meta_all, test_phase_audit = load_split(h5, "test")
    healthy_dev = dev_meta_all.healthy.to_numpy() == 1
    healthy_test = test_meta_all.healthy.to_numpy() == 1
    dev_x, dev_w, dev_meta = dev_x_all[healthy_dev], dev_w_all[healthy_dev], dev_meta_all[healthy_dev].reset_index(drop=True)
    test_x, test_w, test_meta = test_x_all[healthy_test], test_w_all[healthy_test], test_meta_all[healthy_test].reset_index(drop=True)
    del dev_x_all, dev_w_all, test_x_all, test_w_all
    pd.concat([dev_phase_audit, test_phase_audit]).to_csv(OUT / "phase_definition_audit.csv", index=False)

    membership = pd.concat([
        dev_meta_all.groupby(["unit", "flight_class"]).agg(rows=("healthy", "size"), healthy_rows=("healthy", "sum")).reset_index().assign(source="development"),
        test_meta_all.groupby(["unit", "flight_class"]).agg(rows=("healthy", "size"), healthy_rows=("healthy", "sum")).reset_index().assign(source="official_test"),
    ], ignore_index=True)
    membership.to_csv(OUT / "unit_flight_class_membership.csv", index=False)

    train_mask = dev_meta.unit.isin(TRAIN_UNITS).to_numpy()
    cal_mask = dev_meta.unit.isin(CAL_UNITS).to_numpy()
    train_x, train_w = dev_x[train_mask], dev_w[train_mask]
    cal_x, cal_w, cal_meta = dev_x[cal_mask], dev_w[cal_mask], dev_meta[cal_mask].reset_index(drop=True)
    detectors, scores = fit_pair(train_x, train_w, {
        "train": (train_x, train_w), "calibration": (cal_x, cal_w), "official_test": (test_x, test_w)
    })

    # Operating regression quality and support are audits only; no test information enters fitting.
    corrected = detectors["condition_corrected_pca"]
    regression_rows = []
    for subset, x, w in [("train", train_x, train_w), ("calibration", cal_x, cal_w), ("official_test", test_x, test_w)]:
        prediction = corrected.expected(w)
        for j, sensor in enumerate(SENSORS):
            regression_rows.append({"subset": subset, "sensor": sensor,
                                    "r2": r2_score(x[:, j], prediction[:, j]),
                                    "rmse": float(np.sqrt(np.mean((x[:, j] - prediction[:, j]) ** 2)))})
    pd.DataFrame(regression_rows).to_csv(OUT / "operating_regression_metrics.csv", index=False)
    support_rows = []
    for j, name in enumerate(W_NAMES):
        low, high = train_w[:, j].min(), train_w[:, j].max()
        for subset, w in [("calibration", cal_w), ("official_test", test_w)]:
            support_rows.append({"descriptor": name, "subset": subset, "train_min": low, "train_max": high,
                                 "subset_min": w[:, j].min(), "subset_max": w[:, j].max(),
                                 "fraction_outside_train_range": float(np.mean((w[:, j] < low) | (w[:, j] > high)))})
    pd.DataFrame(support_rows).to_csv(OUT / "operating_support_audit.csv", index=False)

    score_rows, rate_rows, transfer_rows, probe_rows, flight_detail, flight_summary = [], [], [], [], [], []
    thresholds = {}
    for detector, detector_scores in scores.items():
        for phase_definition in ("primary", "alt_rate"):
            threshold = float(np.quantile(detector_scores["calibration"], .99, method="higher"))
            thresholds[(detector, phase_definition)] = threshold
            for subset, meta in [("train", dev_meta[train_mask].reset_index(drop=True)),
                                 ("calibration", cal_meta), ("official_test", test_meta)]:
                score_rows += score_summary(detector_scores[subset], meta, detector, phase_definition, subset)
                rate_rows += row_rates(detector_scores[subset], meta, threshold, detector, phase_definition, subset)
            transfer_rows += transfer_rates(detector_scores["calibration"], cal_meta,
                                             detector_scores["official_test"], test_meta,
                                             detector, phase_definition)
            probe_rows += phase_probe(detector_scores["calibration"], cal_meta,
                                      detector_scores["official_test"], test_meta,
                                      detector, phase_definition)
            detail, summary = flight_metrics(detector_scores["official_test"], test_meta, threshold,
                                             detector, phase_definition)
            flight_detail += detail
            flight_summary += summary
    scores_df, rates_df = pd.DataFrame(score_rows), pd.DataFrame(rate_rows)
    transfer_df, probe_df = pd.DataFrame(transfer_rows), pd.DataFrame(probe_rows)
    scores_df.to_csv(OUT / "score_distributions.csv", index=False)
    rates_df.to_csv(OUT / "row_false_alarm_rates.csv", index=False)
    transfer_df.to_csv(OUT / "threshold_transfer_matrix.csv", index=False)
    probe_df.to_csv(OUT / "score_only_phase_prediction.csv", index=False)
    pd.DataFrame(flight_detail).to_csv(OUT / "flight_alarm_detail.csv", index=False)
    pd.DataFrame(flight_summary).to_csv(OUT / "flight_alarm_summary.csv", index=False)
    # In DS02 official test data each Fc is represented by exactly one unit; retain
    # an explicit Fc table so this limitation cannot be hidden by pooled results.
    per_fc = (rates_df[(rates_df.subset == "official_test") & (rates_df.unit != "all")]
              .groupby(["detector", "phase_definition", "flight_class", "phase"], as_index=False)
              .agg(n=("n", "sum"), false_alarms=("false_alarms", "sum")))
    per_fc["false_alarm_rate"] = per_fc.false_alarms / per_fc.n
    per_fc.to_csv(OUT / "per_flight_class_row_fpr.csv", index=False)
    flight_summary_df = pd.DataFrame(flight_summary)
    per_fc_flight = (flight_summary_df[flight_summary_df.unit != "all"]
                     .groupby(["detector", "phase_definition", "flight_class", "phase"], as_index=False)
                     .agg(healthy_flights=("healthy_flights", "sum"),
                          flights_with_false_alarm=("flights_with_false_alarm", "sum"),
                          false_alarm_events=("false_alarm_events", "sum")))
    per_fc_flight["fraction_flights_with_false_alarm"] = (
        per_fc_flight.flights_with_false_alarm / per_fc_flight.healthy_flights)
    per_fc_flight["events_per_healthy_flight"] = (
        per_fc_flight.false_alarm_events / per_fc_flight.healthy_flights)
    per_fc_flight.to_csv(OUT / "per_flight_class_flight_metrics.csv", index=False)

    # Direct comparison on all official test engines with the original phase rule.
    comparison = []
    for detector in detectors:
        r = rates_df[(rates_df.detector == detector) & (rates_df.phase_definition == "primary") &
                     (rates_df.subset == "official_test") & (rates_df.unit == "all")].set_index("phase")
        phase_rates = r.loc[list(PHASES), "false_alarm_rate"]
        t = transfer_df[(transfer_df.detector == detector) & (transfer_df.phase_definition == "primary") &
                        (transfer_df.unit == "all")]
        offdiag = t[t.calibration_phase != t.test_phase].false_alarm_rate.max()
        accuracy = probe_df[(probe_df.detector == detector) & (probe_df.phase_definition == "primary") &
                            (probe_df.unit == "all")].balanced_accuracy.iloc[0]
        comparison.append({
            "detector": detector, "overall_healthy_fpr": r.loc["overall", "false_alarm_rate"],
            "climb_fpr": phase_rates.climb, "cruise_fpr": phase_rates.cruise,
            "descent_fpr": phase_rates.descent,
            "max_min_phase_fpr_ratio": phase_rates.max() / phase_rates.min(),
            "worst_offdiagonal_transfer_fpr": offdiag,
            "score_only_phase_balanced_accuracy": accuracy,
        })
    comparison_df = pd.DataFrame(comparison)
    comparison_df.to_csv(OUT / "raw_vs_corrected_comparison.csv", index=False)

    sensitivity = []
    for detector in detectors:
        for phase_definition in ("primary", "alt_rate"):
            r = rates_df[(rates_df.detector == detector) & (rates_df.phase_definition == phase_definition) &
                         (rates_df.subset == "official_test") & (rates_df.unit == "all")].set_index("phase")
            phase_rates = r.loc[list(PHASES), "false_alarm_rate"]
            t = transfer_df[(transfer_df.detector == detector) & (transfer_df.phase_definition == phase_definition) &
                            (transfer_df.unit == "all")]
            p = probe_df[(probe_df.detector == detector) & (probe_df.phase_definition == phase_definition) &
                         (probe_df.unit == "all")].balanced_accuracy.iloc[0]
            sensitivity.append({"detector": detector, "phase_definition": phase_definition,
                                "climb_fpr": phase_rates.climb, "cruise_fpr": phase_rates.cruise,
                                "descent_fpr": phase_rates.descent,
                                "max_min_phase_fpr_ratio": phase_rates.max() / phase_rates.min(),
                                "worst_offdiagonal_transfer_fpr": t[t.calibration_phase != t.test_phase].false_alarm_rate.max(),
                                "score_only_phase_balanced_accuracy": p})
    pd.DataFrame(sensitivity).to_csv(OUT / "phase_sensitivity_summary.csv", index=False)

    # Same-Fc engine-held-out audits: four train engines, separate calibration, one audit engine.
    folds = []
    for audit_index, audit_unit in enumerate(FC3_DEV):
        calibration_unit = FC3_DEV[(audit_index + 1) % len(FC3_DEV)]
        fold_train_units = tuple(u for u in FC3_DEV if u not in (audit_unit, calibration_unit))
        fold_train = dev_meta.unit.isin(fold_train_units).to_numpy()
        fold_cal = (dev_meta.unit.to_numpy() == calibration_unit)
        fold_audit = (dev_meta.unit.to_numpy() == audit_unit)
        fold_detectors, fold_scores = fit_pair(dev_x[fold_train], dev_w[fold_train], {
            "cal": (dev_x[fold_cal], dev_w[fold_cal]), "audit": (dev_x[fold_audit], dev_w[fold_audit])})
        audit_meta = dev_meta[fold_audit].reset_index(drop=True)
        calibration_meta = dev_meta[fold_cal].reset_index(drop=True)
        for detector in fold_detectors:
            threshold = float(np.quantile(fold_scores[detector]["cal"], .99, method="higher"))
            phase_rates = []
            for phase_id in range(3):
                mask = audit_meta.phase_primary.to_numpy() == phase_id
                phase_rates.append(float(np.mean(fold_scores[detector]["audit"][mask] > threshold)))
            overall_alarm = fold_scores[detector]["audit"] > threshold
            transfer = transfer_rates(fold_scores[detector]["cal"], calibration_meta,
                                      fold_scores[detector]["audit"], audit_meta, detector, "primary")
            transfer = pd.DataFrame(transfer)
            probe = phase_probe(fold_scores[detector]["cal"], calibration_meta,
                                fold_scores[detector]["audit"], audit_meta, detector, "primary")[0]
            _, temporal = flight_metrics(fold_scores[detector]["audit"], audit_meta, threshold,
                                         detector, "primary", "matched_fc_fold")
            temporal_overall = next(x for x in temporal if x["unit"] == "all" and x["phase"] == "overall")
            folds.append({
                "audit_unit": audit_unit, "flight_class": 3, "calibration_units": str(calibration_unit),
                "training_units": ",".join(map(str, fold_train_units)), "detector": detector,
                "overall_fpr": float(overall_alarm.mean()), "climb_fpr": phase_rates[0],
                "cruise_fpr": phase_rates[1], "descent_fpr": phase_rates[2],
                "max_min_phase_fpr_ratio": max(phase_rates) / min(phase_rates) if min(phase_rates) > 0 else np.inf,
                "worst_offdiagonal_transfer_fpr": transfer[transfer.calibration_phase != transfer.test_phase].false_alarm_rate.max(),
                "score_only_phase_balanced_accuracy": probe["balanced_accuracy"],
                "fraction_flights_with_false_alarm": temporal_overall["fraction_flights_with_false_alarm"],
                "events_per_healthy_flight": temporal_overall["events_per_healthy_flight"],
            })
    # Add official matched-Fc unit 11 from the main split.
    unit11 = test_meta.unit.to_numpy() == 11
    for detector in detectors:
        threshold = thresholds[(detector, "primary")]
        phase_rates = [float(np.mean(scores[detector]["official_test"][unit11 & (test_meta.phase_primary.to_numpy() == p)] > threshold)) for p in range(3)]
        transfer = transfer_df[(transfer_df.detector == detector) & (transfer_df.phase_definition == "primary") & (transfer_df.unit == "11")]
        probe = probe_df[(probe_df.detector == detector) & (probe_df.phase_definition == "primary") & (probe_df.unit == "11")].iloc[0]
        temporal = pd.DataFrame(flight_summary)
        temporal = temporal[(temporal.detector == detector) & (temporal.phase_definition == "primary") &
                            (temporal.unit.astype(str) == "11") & (temporal.phase == "overall")].iloc[0]
        folds.append({
            "audit_unit": 11, "flight_class": 3, "calibration_units": "18,20",
            "training_units": "2,5,10,16", "detector": detector,
            "overall_fpr": float(np.mean(scores[detector]["official_test"][unit11] > threshold)),
            "climb_fpr": phase_rates[0], "cruise_fpr": phase_rates[1], "descent_fpr": phase_rates[2],
            "max_min_phase_fpr_ratio": max(phase_rates) / min(phase_rates),
            "worst_offdiagonal_transfer_fpr": transfer[transfer.calibration_phase != transfer.test_phase].false_alarm_rate.max(),
            "score_only_phase_balanced_accuracy": probe.balanced_accuracy,
            "fraction_flights_with_false_alarm": temporal.fraction_flights_with_false_alarm,
            "events_per_healthy_flight": temporal.events_per_healthy_flight,
        })
    pd.DataFrame(folds).to_csv(OUT / "matched_fc_engine_audits.csv", index=False)

    config = {
        "data": str(DATA), "train_units": TRAIN_UNITS, "calibration_units": CAL_UNITS,
        "official_test_units": TEST_UNITS, "detector_sensor_inputs": SENSORS,
        "operating_regression_inputs": W_NAMES,
        "operating_regression": "standardized W; complete degree-3 polynomial with interactions; multi-output ridge",
        "ridge_alpha_fixed": RIDGE_ALPHA, "pca_components": PCA_COMPONENTS,
        "primary_phase": "first/last crossing of 90% within-flight altitude range",
        "alternative_phase": "first/last row above 85% altitude range with |centered 60-s altitude rate| <= 2 ft/s",
        "threshold": "higher empirical 99th percentile of pooled healthy calibration rows",
        "temporal_event": "start of a contiguous run of above-threshold rows within a flight or phase segment",
        "pca_explained_variance": {name: model.explained_variance for name, model in detectors.items()},
    }
    (OUT / "run_config.json").write_text(json.dumps(config, indent=2))

    # Compact figures.
    plot = rates_df[(rates_df.phase_definition == "primary") & (rates_df.subset == "official_test") &
                    (rates_df.unit == "all") & rates_df.phase.isin(PHASES)]
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    x = np.arange(3)
    for i, detector in enumerate(("raw_pca", "condition_corrected_pca")):
        values = plot[plot.detector == detector].set_index("phase").loc[list(PHASES)].false_alarm_rate * 100
        ax.bar(x + (i - .5) * .34, values, width=.34, label=detector.replace("_", " "))
    ax.axhline(1, color="black", linestyle="--", linewidth=1)
    ax.set(xticks=x, xticklabels=PHASES, ylabel="Healthy false alarm rate (%)",
           title="Official test: raw versus operating-condition-corrected PCA")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "raw_vs_corrected_fpr.png", dpi=180)
    plt.close(fig)

    corrected_transfer = transfer_df[(transfer_df.detector == "condition_corrected_pca") &
                                     (transfer_df.phase_definition == "primary") & (transfer_df.unit == "all")]
    matrix = corrected_transfer.pivot(index="calibration_phase", columns="test_phase", values="false_alarm_rate").loc[list(PHASES), list(PHASES)] * 100
    fig, ax = plt.subplots(figsize=(6, 4.5))
    im = ax.imshow(matrix, cmap="magma", vmin=0)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{matrix.iloc[i, j]:.2f}%", ha="center", va="center",
                    color="black" if matrix.iloc[i, j] > .65 * matrix.to_numpy().max() else "white")
    ax.set(xticks=range(3), xticklabels=PHASES, yticks=range(3), yticklabels=PHASES,
           xlabel="Audit phase", ylabel="Calibration phase",
           title="Condition-corrected PCA threshold transfer")
    fig.colorbar(im, ax=ax, label="Healthy false alarm rate (%)")
    fig.tight_layout()
    fig.savefig(FIG / "corrected_threshold_transfer.png", dpi=180)
    plt.close(fig)

    print("\nRAW VS CORRECTED\n", comparison_df.to_string(index=False))
    print("\nPHASE SENSITIVITY\n", pd.DataFrame(sensitivity).to_string(index=False))
    print("\nMATCHED FC3 AUDITS\n", pd.DataFrame(folds).to_string(index=False))


if __name__ == "__main__":
    main()
