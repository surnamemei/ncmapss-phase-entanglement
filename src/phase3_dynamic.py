"""Phase 3A: causal dynamic operating-condition correction."""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from second_stage_audit import (
    DATA, PHASES, PCA_COMPONENTS, RIDGE_ALPHA, SENSORS, W_NAMES,
    TRAIN_UNITS, CAL_UNITS, TEST_UNITS, load_split, row_rates,
    score_summary, transfer_rates, phase_probe, flight_metrics,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/phase3_dynamic_correction"
FIG = ROOT / "figures/phase3"
SCHEMES = ("static", "static_derivative", "history")
WINDOWS = (30, 120)
CHUNK = 100_000


def causal_descriptors(w, meta):
    """Build causal features independently within every flight."""
    n = len(w)
    derivative = np.zeros_like(w, dtype=np.float32)
    means = {window: np.empty_like(w, dtype=np.float32) for window in WINDOWS}
    stds = {window: np.empty_like(w, dtype=np.float32) for window in WINDOWS}
    slopes = {window: np.empty_like(w, dtype=np.float32) for window in WINDOWS}
    unit, cycle = meta.unit.to_numpy(), meta.cycle.to_numpy()
    boundaries = np.flatnonzero((np.diff(unit) != 0) | (np.diff(cycle) != 0)) + 1
    starts, ends = np.r_[0, boundaries], np.r_[boundaries, n]
    for start, end in zip(starts, ends):
        z = w[start:end]
        derivative[start + 1:end] = np.diff(z, axis=0)
        csum = np.vstack([np.zeros((1, z.shape[1])), np.cumsum(z, axis=0, dtype=np.float64)])
        csq = np.vstack([np.zeros((1, z.shape[1])), np.cumsum(z * z, axis=0, dtype=np.float64)])
        idx = np.arange(len(z))
        for window in WINDOWS:
            left = np.maximum(idx - window + 1, 0)
            count = (idx - left + 1)[:, None]
            mean = (csum[idx + 1] - csum[left]) / count
            variance = np.maximum((csq[idx + 1] - csq[left]) / count - mean * mean, 0)
            means[window][start:end] = mean
            stds[window][start:end] = np.sqrt(variance)
            elapsed = np.maximum(idx - left, 1)[:, None]
            slopes[window][start:end] = (z - z[left]) / elapsed
    blocks = [w.astype(np.float32), derivative]
    names = list(W_NAMES) + [f"d_{name}" for name in W_NAMES]
    for window in WINDOWS:
        blocks.extend([means[window], stds[window], slopes[window]])
        names.extend([f"mean{window}_{name}" for name in W_NAMES])
        names.extend([f"std{window}_{name}" for name in W_NAMES])
        names.extend([f"slope{window}_{name}" for name in W_NAMES])
    result = np.concatenate(blocks, axis=1)
    assert np.isfinite(result).all() and result.shape[1] == len(names) == 32
    return result, names


class CausalOperatingRegressor:
    """Ridge on cubic static terms plus additive dynamic terms and W*dW."""

    def __init__(self, scheme, alpha=RIDGE_ALPHA):
        self.scheme = scheme
        self.alpha = alpha
        self.n_descriptors = {"static": 4, "static_derivative": 8, "history": 32}[scheme]
        self.scaler = StandardScaler()
        self.poly = PolynomialFeatures(3, include_bias=False)

    def _basis(self, descriptors):
        z = self.scaler.transform(descriptors[:, :self.n_descriptors])
        static = self.poly.transform(z[:, :4])
        if self.n_descriptors == 4:
            return static
        extra = z[:, 4:]
        # Interact instantaneous state with dW only; all dynamic descriptors also
        # enter linearly and quadratically. This fixed basis is used for every split.
        state_derivative = (z[:, :4, None] * z[:, None, 4:8]).reshape(len(z), -1)
        return np.concatenate([static, extra, extra * extra, state_derivative], axis=1)

    def fit(self, descriptors, y):
        view = descriptors[:, :self.n_descriptors]
        self.scaler.fit(view)
        self.poly.fit(np.zeros((1, 4)))
        p = self._basis(view[:1]).shape[1]
        xtx = np.zeros((p + 1, p + 1), dtype=np.float64)
        xty = np.zeros((p + 1, y.shape[1]), dtype=np.float64)
        for start in range(0, len(y), CHUNK):
            phi = self._basis(view[start:start + CHUNK]).astype(np.float64, copy=False)
            design = np.concatenate([np.ones((len(phi), 1)), phi], axis=1)
            xtx += design.T @ design
            xty += design.T @ y[start:start + CHUNK]
        penalty = np.eye(p + 1) * self.alpha
        penalty[0, 0] = 0
        self.coef = np.linalg.solve(xtx + penalty, xty)
        return self

    def predict(self, descriptors):
        result = np.empty((len(descriptors), len(SENSORS)), dtype=np.float64)
        for start in range(0, len(descriptors), CHUNK):
            phi = self._basis(descriptors[start:start + CHUNK]).astype(np.float64, copy=False)
            result[start:start + len(phi)] = self.coef[0] + phi @ self.coef[1:]
        return result


class ResidualPCADetector:
    def __init__(self, scheme, alpha=RIDGE_ALPHA):
        self.scheme = scheme
        self.regression = CausalOperatingRegressor(scheme, alpha)

    def fit(self, x, descriptors):
        self.regression.fit(descriptors, x)
        residual = x - self.regression.predict(descriptors)
        self.residual_scaler = StandardScaler().fit(residual)
        z = self.residual_scaler.transform(residual)
        self.pca = PCA(n_components=PCA_COMPONENTS, svd_solver="full").fit(z)
        self.explained_variance = float(self.pca.explained_variance_ratio_.sum())
        return self

    def standardized_residual(self, x, descriptors):
        residual = x - self.regression.predict(descriptors)
        return self.residual_scaler.transform(residual)

    def contributions(self, x, descriptors):
        z = self.standardized_residual(x, descriptors)
        reconstructed = self.pca.inverse_transform(self.pca.transform(z))
        return (z - reconstructed) ** 2

    def score(self, x, descriptors):
        return self.contributions(x, descriptors).mean(axis=1)


def metric_summary(rates_df, transfer_df, probe_df, flight_df):
    rows = []
    for scheme in SCHEMES:
        for phase_definition in ("primary", "alt_rate"):
            rates = rates_df[(rates_df.detector == scheme) & (rates_df.phase_definition == phase_definition) &
                             (rates_df.subset == "official_test") & (rates_df.unit == "all")].set_index("phase")
            phase_rates = rates.loc[list(PHASES), "false_alarm_rate"]
            transfer = transfer_df[(transfer_df.detector == scheme) &
                                   (transfer_df.phase_definition == phase_definition) & (transfer_df.unit == "all")]
            probe = probe_df[(probe_df.detector == scheme) &
                             (probe_df.phase_definition == phase_definition) & (probe_df.unit == "all")].iloc[0]
            flight = flight_df[(flight_df.detector == scheme) &
                               (flight_df.phase_definition == phase_definition) & (flight_df.unit == "all")].set_index("phase")
            rows.append({
                "correction": scheme, "phase_definition": phase_definition,
                "overall_fpr": rates.loc["overall", "false_alarm_rate"],
                "climb_fpr": phase_rates.climb, "cruise_fpr": phase_rates.cruise,
                "descent_fpr": phase_rates.descent,
                "max_min_phase_fpr_ratio": phase_rates.max() / phase_rates.min(),
                "worst_offdiagonal_transfer_fpr": transfer[transfer.calibration_phase != transfer.test_phase].false_alarm_rate.max(),
                "score_only_phase_balanced_accuracy": probe.balanced_accuracy,
                "climb_flights_with_alarm": flight.loc["climb", "fraction_flights_with_false_alarm"],
                "cruise_flights_with_alarm": flight.loc["cruise", "fraction_flights_with_false_alarm"],
                "descent_flights_with_alarm": flight.loc["descent", "fraction_flights_with_false_alarm"],
                "events_per_flight": flight.loc["overall", "events_per_healthy_flight"],
            })
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    with h5py.File(DATA) as h5:
        dev_x_all, dev_w_all, dev_meta_all, _ = load_split(h5, "dev")
        test_x_all, test_w_all, test_meta_all, _ = load_split(h5, "test")
    dev_mask = dev_meta_all.healthy.to_numpy() == 1
    test_mask = test_meta_all.healthy.to_numpy() == 1
    dev_x, dev_w = dev_x_all[dev_mask], dev_w_all[dev_mask]
    test_x, test_w = test_x_all[test_mask], test_w_all[test_mask]
    dev_meta = dev_meta_all[dev_mask].reset_index(drop=True)
    test_meta = test_meta_all[test_mask].reset_index(drop=True)
    del dev_x_all, dev_w_all, test_x_all, test_w_all
    dev_desc, descriptor_names = causal_descriptors(dev_w, dev_meta)
    test_desc, test_names = causal_descriptors(test_w, test_meta)
    assert descriptor_names == test_names
    train_mask = dev_meta.unit.isin(TRAIN_UNITS).to_numpy()
    cal_mask = dev_meta.unit.isin(CAL_UNITS).to_numpy()
    train_meta = dev_meta[train_mask].reset_index(drop=True)
    cal_meta = dev_meta[cal_mask].reset_index(drop=True)

    # Expanded dynamic bases need stronger shrinkage. Choose it using only a
    # held-out training engine and sensor prediction error, never anomaly scores.
    alpha_rows = []
    chosen_alpha = {"static": RIDGE_ALPHA}
    inner_fit = dev_meta.unit.isin((2, 5, 10)).to_numpy()
    inner_check = dev_meta.unit.to_numpy() == 16
    scale = dev_x[inner_fit].std(axis=0)
    for scheme in ("static_derivative", "history"):
        for alpha in (1.0, 100.0, 10_000.0, 1_000_000.0):
            candidate = CausalOperatingRegressor(scheme, alpha).fit(dev_desc[inner_fit], dev_x[inner_fit])
            error = dev_x[inner_check] - candidate.predict(dev_desc[inner_check])
            normalized_mse = float(np.mean((error / scale) ** 2))
            alpha_rows.append({"correction": scheme, "alpha": alpha,
                               "training_units": "2,5,10", "heldout_training_unit": 16,
                               "normalized_sensor_mse": normalized_mse})
        scheme_rows = [r for r in alpha_rows if r["correction"] == scheme]
        chosen_alpha[scheme] = min(scheme_rows, key=lambda r: r["normalized_sensor_mse"])["alpha"]
    pd.DataFrame(alpha_rows).to_csv(OUT / "training_only_ridge_selection.csv", index=False)

    score_rows, rate_rows, transfer_rows, probe_rows = [], [], [], []
    flight_detail_rows, flight_summary_rows, regression_rows = [], [], []
    sensor_rows, correlation_rows = [], []
    saved = {}
    for scheme in SCHEMES:
        print(f"Fitting {scheme}", flush=True)
        model = ResidualPCADetector(scheme, chosen_alpha[scheme]).fit(dev_x[train_mask], dev_desc[train_mask])
        scheme_scores = {
            "train": model.score(dev_x[train_mask], dev_desc[train_mask]),
            "calibration": model.score(dev_x[cal_mask], dev_desc[cal_mask]),
            "official_test": model.score(test_x, test_desc),
        }
        saved[scheme] = {"model": model, "scores": scheme_scores}
        for subset, x, descriptors in [("train", dev_x[train_mask], dev_desc[train_mask]),
                                       ("calibration", dev_x[cal_mask], dev_desc[cal_mask]),
                                       ("official_test", test_x, test_desc)]:
            expected = model.regression.predict(descriptors)
            for j, sensor in enumerate(SENSORS):
                error = x[:, j] - expected[:, j]
                regression_rows.append({"correction": scheme, "subset": subset, "sensor": sensor,
                                        "rmse": np.sqrt(np.mean(error * error)),
                                        "r2": 1 - np.sum(error * error) / np.sum((x[:, j] - x[:, j].mean()) ** 2)})
        for phase_definition in ("primary", "alt_rate"):
            threshold = float(np.quantile(scheme_scores["calibration"], .99, method="higher"))
            for subset, scores, meta in [("train", scheme_scores["train"], train_meta),
                                         ("calibration", scheme_scores["calibration"], cal_meta),
                                         ("official_test", scheme_scores["official_test"], test_meta)]:
                score_rows += score_summary(scores, meta, scheme, phase_definition, subset)
                rate_rows += row_rates(scores, meta, threshold, scheme, phase_definition, subset)
            transfer_rows += transfer_rates(scheme_scores["calibration"], cal_meta,
                                             scheme_scores["official_test"], test_meta,
                                             scheme, phase_definition)
            probe_rows += phase_probe(scheme_scores["calibration"], cal_meta,
                                      scheme_scores["official_test"], test_meta,
                                      scheme, phase_definition)
            detail, summary = flight_metrics(scheme_scores["official_test"], test_meta,
                                             threshold, scheme, phase_definition)
            flight_detail_rows += detail
            flight_summary_rows += summary

        if scheme == "history":
            contributions = model.contributions(test_x, test_desc)
            for phase_id, phase in enumerate(PHASES):
                mask = test_meta.phase_primary.to_numpy() == phase_id
                phase_contribution = contributions[mask].mean(axis=0)
                for j, sensor in enumerate(SENSORS):
                    sensor_rows.append({"phase": phase, "sensor": sensor,
                                        "mean_squared_reconstruction_error": phase_contribution[j],
                                        "fraction_of_total": phase_contribution[j] / phase_contribution.sum()})
            log_score = np.log10(np.maximum(scheme_scores["official_test"], 1e-15))
            for j, name in enumerate(descriptor_names):
                rho, pvalue = spearmanr(test_desc[:, j], log_score)
                correlation_rows.append({"descriptor": name, "spearman_rho": rho, "p_value_descriptive_only": pvalue})

    scores_df = pd.DataFrame(score_rows)
    rates_df = pd.DataFrame(rate_rows)
    transfer_df = pd.DataFrame(transfer_rows)
    probe_df = pd.DataFrame(probe_rows)
    flight_summary_df = pd.DataFrame(flight_summary_rows)
    scores_df.to_csv(OUT / "score_distributions.csv", index=False)
    rates_df.to_csv(OUT / "row_false_alarm_rates.csv", index=False)
    transfer_df.to_csv(OUT / "threshold_transfer_matrix.csv", index=False)
    probe_df.to_csv(OUT / "score_only_phase_prediction.csv", index=False)
    pd.DataFrame(flight_detail_rows).to_csv(OUT / "flight_alarm_detail.csv", index=False)
    flight_summary_df.to_csv(OUT / "flight_alarm_summary.csv", index=False)
    pd.DataFrame(regression_rows).to_csv(OUT / "regression_metrics.csv", index=False)
    pd.DataFrame(sensor_rows).to_csv(OUT / "history_sensor_error_contributions.csv", index=False)
    pd.DataFrame(correlation_rows).sort_values("spearman_rho", key=np.abs, ascending=False).to_csv(
        OUT / "history_score_descriptor_correlations.csv", index=False)
    comparison = metric_summary(rates_df, transfer_df, probe_df, flight_summary_df)
    comparison.to_csv(OUT / "correction_comparison.csv", index=False)

    # Phase-wise standardized residual plots for the six most phase-sensitive sensors.
    history_model = saved["history"]["model"]
    z = history_model.standardized_residual(test_x, test_desc)
    contribution = pd.DataFrame(sensor_rows).pivot(index="sensor", columns="phase", values="mean_squared_reconstruction_error")
    top = (contribution.descent - contribution.climb).abs().nlargest(6).index.tolist()
    rng = np.random.default_rng(0)
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharey=False)
    for ax, sensor in zip(axes.flat, top):
        j = SENSORS.index(sensor)
        data = []
        for phase_id in range(3):
            values = z[test_meta.phase_primary.to_numpy() == phase_id, j]
            data.append(rng.choice(values, min(5000, len(values)), replace=False))
        ax.boxplot(data, labels=PHASES, showfliers=False)
        ax.set_title(sensor)
        ax.set_ylabel("Standardized residual")
    fig.suptitle("History-corrected healthy residuals by phase (official test)")
    fig.tight_layout()
    fig.savefig(FIG / "history_residuals_by_phase.png", dpi=180)
    plt.close(fig)

    primary = comparison[comparison.phase_definition == "primary"].set_index("correction").loc[list(SCHEMES)]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    xloc = np.arange(3)
    width = .25
    for i, phase in enumerate(PHASES):
        ax.bar(xloc + (i - 1) * width, primary[f"{phase}_fpr"] * 100, width=width, label=phase)
    ax.axhline(1, color="black", linestyle="--", linewidth=1)
    ax.set(xticks=xloc, xticklabels=["static", "+ derivative", "+ causal history"],
           ylabel="Healthy false alarm rate (%)", title="Dynamic operating correction comparison")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "dynamic_correction_fpr.png", dpi=180)
    plt.close(fig)

    config = {
        "windows_seconds": WINDOWS, "causal": True,
        "descriptors": descriptor_names,
        "regression_basis": "cubic instantaneous W; linear and squared added descriptors; W*dW interactions",
        "ridge_alpha": chosen_alpha, "pca_components": PCA_COMPONENTS,
        "ridge_selection": "dynamic schemes selected by normalized sensor MSE on training unit 16 after fitting units 2,5,10",
        "selection_for_phase3b": "history correction, selected a priori as the most comprehensive causal correction",
        "pca_explained_variance": {scheme: saved[scheme]["model"].explained_variance for scheme in SCHEMES},
    }
    (OUT / "run_config.json").write_text(json.dumps(config, indent=2))
    print(comparison.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
