"""Data-free guards for the MSSP post-confirmation mitigation analysis.

No N-CMAPSS file is read: every data test uses synthetic arrays or a temporary
synthetic HDF5 file with the frozen schema.
"""

import inspect
import json
import math
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import final_validation as fv  # noqa: E402
import mssp_mitigation as mm  # noqa: E402
from confirm_frozen_ds03 import (  # noqa: E402
    calibration_thresholds,
    load_primary_split,
    transfer_with_locked_thresholds,
)
from second_stage_audit import SENSORS, W_NAMES, count_events, load_split  # noqa: E402


def flight_altitude(rows, rng):
    third = rows // 3
    climb = np.linspace(10000.0, 30000.0, third)
    cruise = 30000.0 + rng.normal(0.0, 3.0, third)
    descent = np.linspace(30000.0, 10000.0, rows - 2 * third)
    return np.r_[climb, cruise, descent]


def synthetic_split(units, healthy_flights, rng, flights=4, rows=300):
    a, w, x = [], [], []
    for unit in units:
        for cycle in range(1, flights + 1):
            hs = 1.0 if cycle <= healthy_flights[unit] else 0.0
            a.append(np.c_[np.full(rows, unit), np.full(rows, cycle), np.full(rows, 1.0),
                           np.full(rows, hs)])
            w.append(np.c_[flight_altitude(rows, rng), rng.uniform(0.2, 0.8, rows),
                           rng.uniform(20, 80, rows), rng.uniform(400, 520, rows)])
            x.append(rng.normal(size=(rows, len(SENSORS))))
    return np.vstack(a).astype(np.float64), np.vstack(w), np.vstack(x)


def write_synthetic_h5(path, rng):
    with h5py.File(path, "w") as h5:
        h5.create_dataset("A_var", data=np.array([b"unit", b"cycle", b"Fc", b"hs"]))
        h5.create_dataset("W_var", data=np.array([n.encode() for n in W_NAMES]))
        h5.create_dataset("X_s_var", data=np.array([n.encode() for n in SENSORS]))
        for split, units, healthy in (("dev", (1, 2), {1: 2, 2: 3}),
                                      ("test", (10, 11), {10: 1, 11: 2})):
            a, w, x = synthetic_split(units, healthy, rng)
            h5.create_dataset(f"A_{split}", data=a)
            h5.create_dataset(f"W_{split}", data=w)
            h5.create_dataset(f"X_s_{split}", data=x)


def synthetic_meta(units, flights, rows, rng, healthy_flights=None):
    parts = []
    for unit in units:
        for cycle in range(1, flights + 1):
            healthy = 1 if healthy_flights is None or cycle <= healthy_flights else 0
            phase = np.repeat([0, 1, 2], [rows // 3, rows // 3, rows - 2 * (rows // 3)])
            parts.append(pd.DataFrame({
                "unit": np.int16(unit), "cycle": np.int16(cycle), "flight_class": np.int8(1),
                "healthy": np.int8(healthy), "phase_primary": phase.astype(np.int8)}))
    meta = pd.concat(parts, ignore_index=True)
    return meta, rng.integers(0, 3, len(meta)).astype(np.int8)


class FrozenIsolation(unittest.TestCase):
    def test_baseline_manifest_verifies(self):
        result = mm.verify_manifest(allow_absent_ignored=True)
        self.assertEqual([], result["mismatched"])
        self.assertEqual([], result["missing"])
        self.assertEqual(186, result["entries"])

    def test_outputs_refuse_frozen_and_source_paths(self):
        for path in ("results/confirmation_ds03/x.json", "results/final_validation/checkpoints/x",
                     "paper/ress/x.tex", "src/x.py", "docs/x.md", "configs/x.yaml", "N-CMAPSS/x",
                     "results/second_stage/x.csv", "."):
            with self.assertRaises(PermissionError, msg=path):
                mm.guard_output(ROOT / path)
        with self.assertRaises(PermissionError):
            mm.guard_output(ROOT / "results")
        mm.guard_output(ROOT / "results/mssp_mitigation/ds03/stage_c/gate_report.json")

    def test_outputs_never_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run" / "x.json"
            mm.write_json(target, {"a": 1})
            with self.assertRaises(FileExistsError):
                mm.write_json(target, {"a": 2})

    def test_config_snapshot_matches_constants(self):
        text = (ROOT / "configs/mssp_mitigation.yaml").read_text(encoding="utf-8")
        values = {key: json.loads(value) for key, value in
                  re.findall(r"^([a-z0-9_]+): (.+)$", text, re.M)}
        expected = {
            "nominal_fpr_targets": list(mm.TARGETS), "primary_nominal_fpr_target": mm.PRIMARY_TARGET,
            "causal_regime_window_samples": mm.CAUSAL_WINDOW,
            "causal_regime_rate_limit": mm.CAUSAL_RATE_LIMIT,
            "flight_false_flag_target": mm.FLIGHT_FALSE_FLAG_TARGET,
            "early_window_flights": mm.EARLY_WINDOW_FLIGHTS,
            "normalized_life_bins": list(mm.LIFE_BINS), "persistence_flights": mm.PERSISTENCE_FLIGHTS,
            "pauc_max_fpr": mm.PAUC_MAX_FPR, "exceedance_multiple": mm.EXCEEDANCE_MULTIPLE,
            "guardrail_alarm_rate_ratio": mm.GUARDRAIL_RATIO,
            "guardrail_median_delay_increase_flights": mm.GUARDRAIL_DELAY_FLIGHTS,
            "u1_bootstrap_seed": mm.U1_SEED, "u2_bootstrap_seed": mm.U2_SEED,
            "bootstrap_replicates": mm.REPLICATES, "lstm_threshold_rtol": mm.LSTM_THRESHOLD_RTOL,
            "bootstrap_atol": mm.BOOTSTRAP_ATOL,
        }
        for key in ("ds02", "ds03"):
            spec = mm.DATASETS[key]
            expected[f"{key}_model_fit_engines"] = list(spec.fit_units)
            expected[f"{key}_calibration_engines"] = list(spec.cal_units)
            expected[f"{key}_audit_engines"] = list(spec.audit_units)
        self.assertEqual(expected, values)

    def test_splits_match_frozen_configs(self):
        for key, config, names in (
                ("ds02", "ds02_discovery.yaml", ("train_engines", "calibration_engines",
                                                 "official_audit_engines")),
                ("ds03", "ds03_confirmation.yaml", ("model_fit_engines",
                                                    "threshold_calibration_engines",
                                                    "official_test_engines"))):
            text = (ROOT / "configs" / config).read_text(encoding="utf-8")
            spec = mm.DATASETS[key]
            for name, units in zip(names, (spec.fit_units, spec.cal_units, spec.audit_units)):
                found = re.search(rf"^{name}: \[([^]]*)\]$", text, re.M).group(1)
                self.assertEqual(list(units), [int(v) for v in found.split(",")])
        self.assertEqual(0.99, 1 - mm.PRIMARY_TARGET)


class Sequencing(unittest.TestCase):
    def test_stage_e_marker_after_lock_before_abnormal_read(self):
        source = inspect.getsource(mm.stage_e)
        self.assertIn("authorize_abnormal_open", source.split("\n", 3)[1] + source.split("\n", 3)[2])
        self.assertLess(source.index("load_verified_lock("), source.index('"abnormal_rows_opened.json"'))
        self.assertLess(source.index("verify_fingerprints("), source.index('"abnormal_rows_opened.json"'))
        self.assertLess(source.index("canonical_json(recomputed)"), source.index('"abnormal_rows_opened.json"'))
        self.assertLess(source.index('"abnormal_rows_opened.json"'), source.index("load_abnormal_audit("))

    def test_gate_and_healthy_stages_never_open_abnormal_rows(self):
        for function in (mm.stage_b, mm.stage_c, mm.stage_l, mm.stage_d, mm.prepare_healthy_context,
                         mm.regenerate_ds02, mm.regenerate_ds03):
            self.assertNotIn("load_abnormal_audit", inspect.getsource(function), function.__name__)
        for function in (mm.stage_b, mm.stage_c):
            source = inspect.getsource(function)
            for name in ("build_mitigation_lock", "u1_bootstrap", "u2_bootstrap", "healthy_endpoint"):
                self.assertNotIn(name, source, function.__name__)
        stage_b = inspect.getsource(mm.stage_b)
        for name in ("load_healthy", "load_selected_rows", "read_row_blocks", "prepare_healthy_context"):
            self.assertNotIn(name, stage_b)

    def test_labels_are_not_detector_inputs(self):
        fit = inspect.getsource(mm.fit_detectors)
        self.assertIn(".fit(dev_x[fit_mask], dev_desc[fit_mask])", fit)
        self.assertIn(".fit(z_fit)", fit)
        score = inspect.getsource(mm.score_rows)
        self.assertIn("standardized_residual(x, descriptors)", score)
        self.assertIn("correction.score(x, descriptors)", score)
        for text in (fit, score):
            for label in ("healthy", "phase_primary", "flight_class", "regime"):
                self.assertNotIn(label, text)

    def test_dry_run_reads_nothing(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/run_mssp_mitigation.py"),
                                 "--stage", "gate"], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("DRY RUN", result.stdout)
        refused = subprocess.run([sys.executable, str(ROOT / "scripts/run_mssp_mitigation.py"),
                                  "--stage", "E"], capture_output=True, text=True, cwd=ROOT)
        self.assertNotEqual(0, refused.returncode)
        self.assertIn("authorize-abnormal-open", refused.stderr)


class Loaders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "synthetic.h5"
        write_synthetic_h5(self.path, np.random.default_rng(1))

    def tearDown(self):
        self.tmp.cleanup()

    def test_healthy_blocks_equal_frozen_ds03_loader(self):
        with h5py.File(self.path, "r") as h5:
            for split in ("dev", "test"):
                x_f, w_f, meta_f = load_primary_split(h5, split)
                x_n, w_n, meta_n, runs = mm.load_healthy("ds03", h5, split)
                np.testing.assert_array_equal(x_f, x_n)
                np.testing.assert_array_equal(w_f, w_n)
                pd.testing.assert_frame_equal(meta_f, meta_n)
                self.assertEqual(len(runs), 2)

    def test_healthy_blocks_equal_frozen_ds02_loader(self):
        with h5py.File(self.path, "r") as h5:
            for split in ("dev", "test"):
                x_all, w_all, meta_all, _ = load_split(h5, split)
                mask = meta_all.healthy.to_numpy() == 1
                x_n, w_n, meta_n, _ = mm.load_healthy("ds02", h5, split)
                np.testing.assert_array_equal(x_all[mask], x_n)
                np.testing.assert_array_equal(w_all[mask], w_n)
                pd.testing.assert_frame_equal(meta_all[mask].reset_index(drop=True), meta_n)

    def test_abnormal_loader_selects_audit_hs0_rows_only(self):
        spec = mm.DatasetSpec("ds03", "x", "X", "", (1,), (2,), (10, 11), "results/x", {})
        with h5py.File(self.path, "r") as h5:
            x_n, _, meta_n, _ = mm.load_abnormal_audit(spec, h5)
            a, x = h5["A_test"][:], h5["X_s_test"][:]
        mask = (a[:, 3] == 0) & np.isin(a[:, 0], (10, 11))
        np.testing.assert_array_equal(x[mask], x_n)
        self.assertTrue((meta_n.healthy == 0).all())

    def test_label_structure(self):
        with h5py.File(self.path, "r") as h5:
            table = mm.label_structure(h5["A_test"][:], "test", {10: "audit", 11: "audit"})
        row = table.set_index("unit").loc[10]
        self.assertEqual((1, 3, 2, 4), (row.healthy_flights, row.post_onset_flights,
                                        row.onset_cycle, row.eol_cycle))
        self.assertTrue(table.ls1_monotone_single_transition.all() and table.ls2_flight_constant.all())
        broken = np.array([[1, 1, 1, 1], [1, 1, 1, 0], [1, 2, 1, 1]], dtype=float)
        bad = mm.label_structure(broken, "test", {})
        self.assertFalse(bad.ls1_monotone_single_transition.iloc[0])
        self.assertFalse(bad.ls2_flight_constant.iloc[0])


class SchemesAndStatistics(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(7)

    def test_causal_regime_uses_only_past_altitude(self):
        alt = np.cumsum(self.rng.normal(0, 40, 600))
        units, cycles = np.ones(600, int), np.ones(600, int)
        labels = mm.causal_regime(alt, units, cycles)
        for cut in (1, 61, 250, 599):
            altered = alt.copy()
            altered[cut:] = self.rng.normal(0, 1e5, 600 - cut)
            np.testing.assert_array_equal(labels[:cut], mm.causal_regime(altered, units, cycles)[:cut])
        climb = mm.causal_regime(np.arange(200) * 10.0, np.ones(200, int), np.ones(200, int))
        self.assertEqual(1, climb[0])
        self.assertTrue((climb[1:] == 0).all())

    def test_phase_conditioned_equals_frozen_diagonal(self):
        cal_meta, cal_regime = synthetic_meta((4, 8), 3, 300, self.rng)
        test_meta, test_regime = synthetic_meta((10, 11, 12), 3, 300, self.rng)
        cal, test = self.rng.lognormal(size=len(cal_meta)), self.rng.lognormal(size=len(test_meta))
        frozen = calibration_thresholds(cal, cal_meta)
        for alpha in mm.TARGETS:
            tau = mm.scheme_taus(cal, cal_meta.phase_primary.to_numpy(), cal_regime, alpha)
            self.assertEqual(frozen[str(alpha)]["pooled"], tau["pooled"])
            for phase in fv.PHASES:
                self.assertEqual(frozen[str(alpha)][phase], tau["phase_conditioned"][phase])
            alarm = test > mm.row_thresholds("phase_conditioned", tau,
                                             test_meta.phase_primary.to_numpy(), test_regime)
            transfer = pd.DataFrame(transfer_with_locked_thresholds(
                test, test_meta, "pca", -1, alpha, frozen[str(alpha)]))
            diagonal = transfer[(transfer.unit == "all")
                                & (transfer.calibration_phase == transfer.test_phase)]
            for row in diagonal.itertuples():
                phase_id = fv.PHASES.index(row.test_phase)
                self.assertEqual(row.false_alarms,
                                 int(alarm[test_meta.phase_primary.to_numpy() == phase_id].sum()))

    def test_cell_counter_matches_brute_force(self):
        scores = np.round(self.rng.normal(size=5000), 2)
        cells = self.rng.integers(0, 40, size=5000)
        counter = mm.CellCounter(scores, cells, 45)
        thresholds = self.rng.normal(size=45)
        expected = [int(np.sum(scores[cells == c] > thresholds[c])) for c in range(45)]
        np.testing.assert_array_equal(expected, counter.above(thresholds))
        np.testing.assert_array_equal([int(np.sum(scores[cells == c] > 0.1)) for c in range(45)],
                                      counter.above(0.1))

    def test_delay_helpers(self):
        self.assertEqual(2.0, mm.first_flag([False, False, True, True]))
        self.assertTrue(math.isinf(mm.first_flag([False, False])))
        self.assertEqual(3.0, mm.persistence_flag([True, False, True, True]))
        self.assertTrue(math.isinf(mm.persistence_flag([True, False, True, False])))
        diff = mm.delay_difference([1, math.inf, math.inf, 2], [0, math.inf, 3, math.inf])
        np.testing.assert_array_equal([1, 0, math.inf, -math.inf], diff)
        self.assertEqual(2.0, mm.lower_median([4, 1, 2, 3]))
        self.assertTrue(math.isinf(mm.lower_median([1, math.inf, math.inf])))
        self.assertEqual(0, count_events(np.array([], dtype=bool)))

    def test_partial_auc(self):
        negative, positive = self.rng.normal(size=4000), self.rng.normal(1.0, 1.0, 1500)
        self.assertAlmostEqual(1.0, mm.partial_auc(np.zeros(100), np.ones(50)))
        self.assertAlmostEqual(0.01, mm.partial_auc(np.zeros(100), np.zeros(50)))
        values = np.r_[negative, positive]
        labels = np.r_[np.zeros(len(negative)), np.ones(len(positive))]
        order = np.argsort(-values)
        fpr = np.r_[0, np.cumsum(labels[order] == 0) / len(negative)]
        tpr = np.r_[0, np.cumsum(labels[order] == 1) / len(positive)]
        grid = np.linspace(0, 0.02, 20001)
        expected = np.trapezoid(np.interp(grid, fpr, tpr), grid) / 0.02
        self.assertAlmostEqual(expected, mm.partial_auc(negative, positive), places=4)

    def test_lock_matches_frozen_thresholds_and_flight_rule(self):
        cal_meta, cal_regime = synthetic_meta((4, 8), 12, 300, self.rng)
        scores = {("pca", -1): self.rng.lognormal(size=len(cal_meta))}
        lock = mm.build_mitigation_lock("synthetic", scores, cal_meta, cal_regime)
        frozen = calibration_thresholds(scores[("pca", -1)], cal_meta)
        view = mm.lock_threshold_view(lock)["pca:-1"]
        self.assertEqual(frozen, view)
        starts, ends = mm.flight_bounds(cal_meta)
        entry = lock["runs"]["pca:-1"]["0.01"]
        alarm = scores[("pca", -1)] > entry["tau"]["pooled"]
        fraction = mm.flight_alarm_counts(alarm, starts) / (ends - starts)
        self.assertEqual(float(np.quantile(fraction, 0.95, method="higher")), entry["kappa"]["pooled"])
        self.assertEqual(24, lock["calibration_flights"])
        self.assertEqual(math.ceil(0.95 * 23), lock["kappa_order_statistic_index"])


class Bootstraps(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(11)
        self.cal_meta, self.cal_regime = synthetic_meta((4, 8), 3, 120, self.rng)
        self.test_meta, self.test_regime = synthetic_meta((10, 11, 12), 3, 120, self.rng)
        self.name = ("pca", -1)
        self.cal = self.rng.lognormal(size=len(self.cal_meta))
        self.test = self.rng.lognormal(size=len(self.test_meta)) * np.where(
            self.test_meta.phase_primary.to_numpy() == 2, 1.3, 1.0)

    def test_u1_pooled_arm_equals_frozen_bootstrap(self):
        rng = np.random.default_rng(123)
        cal_flights, cal_plans = fv.bootstrap_plans(self.cal_meta, fv.BOOTSTRAP_REPETITIONS, rng)
        test_flights, test_plans = fv.bootstrap_plans(self.test_meta, fv.BOOTSTRAP_REPETITIONS, rng)
        frozen = pd.DataFrame(fv.bootstrap_one_model(
            self.name, {"calibration": self.cal, "official_test": self.test}, self.cal_meta,
            self.test_meta, cal_flights, test_flights, cal_plans, test_plans))
        mine = mm.u1_bootstrap({self.name: self.cal}, self.cal_meta, self.cal_regime,
                               {self.name: self.test}, self.test_meta, self.test_regime,
                               runs=[self.name], replicates=fv.BOOTSTRAP_REPETITIONS, seed=123)
        for row in frozen.itertuples():
            match = mine[mine.metric == f"pooled.{row.metric}"].iloc[0]
            for column in ("bootstrap_mean", "ci_lower_95", "ci_upper_95"):
                self.assertEqual(getattr(row, column), match[column], (row.metric, column))
        frozen_file = frozen.rename(columns={"nominal_fpr_target": "nominal_fpr"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frozen.csv"
            frozen_file.to_csv(path, index=False)
            self.assertEqual(0.0, mm.u1_frozen_self_check(mine, path))

    def test_u1_unit_weight_replicate_equals_point_estimates(self):
        cal_flights, _ = fv.bootstrap_plans(self.cal_meta, 1, np.random.default_rng(0))
        test_flights, _ = fv.bootstrap_plans(self.test_meta, 1, np.random.default_rng(0))
        phase_cal, phase_test = (self.cal_meta.phase_primary.to_numpy(),
                                 self.test_meta.phase_primary.to_numpy())
        run = mm.U1Run(self.cal, phase_cal, self.cal_regime, cal_flights,
                       self.test, phase_test, self.test_regime, test_flights)
        out = run.replicate(np.ones(len(cal_flights), dtype=np.int16),
                            np.ones(len(test_flights), dtype=np.int16))
        tau = mm.scheme_taus(self.cal, phase_cal, self.cal_regime, 0.01)
        for scheme in mm.SCHEMES:
            alarm = self.test > mm.row_thresholds(scheme, tau, phase_test, self.test_regime)
            rates = [alarm[phase_test == i].mean() for i in range(3)]
            self.assertAlmostEqual(alarm.mean(), out[f"{scheme}.overall_fpr"], places=12)
            self.assertAlmostEqual(max(rates) - min(rates), out[f"{scheme}.spread"], places=12)
            burden = pd.DataFrame(mm.flight_burden_records(alarm, self.test_meta))
            pooled = burden[burden.unit == "all"].set_index("phase")
            for phase in fv.PHASES:
                self.assertAlmostEqual(pooled.loc[phase, "fraction_flights_with_alarm"],
                                       out[f"{scheme}.flights_with_alarm_{phase}"], places=12)

    def test_u2_unit_weight_replicate_equals_point_estimates(self):
        cal_meta, cal_regime = synthetic_meta((4, 8), 10, 90, self.rng)
        audit_meta, audit_regime = synthetic_meta((10, 11, 12), 16, 90, self.rng, healthy_flights=4)
        cal = self.rng.lognormal(size=len(cal_meta))
        post = audit_meta.healthy.to_numpy() == 0
        cycles = audit_meta.cycle.to_numpy().astype(float)
        audit = self.rng.lognormal(size=len(audit_meta)) * np.where(post, 1.0 + 0.08 * cycles, 1.0)
        flights = mm.audit_flight_table(audit_meta)
        engines = [10, 11, 12]
        cal_flights, _ = fv.bootstrap_plans(cal_meta, 1, np.random.default_rng(0))
        run = mm.U2Run(cal, cal_meta.phase_primary.to_numpy(), cal_regime, cal_flights, audit,
                       audit_meta.phase_primary.to_numpy(), audit_regime, flights, engines)
        out = run.replicate(np.ones(len(cal_flights), dtype=np.int16),
                            np.ones(len(flights), dtype=np.int64), np.ones(3, dtype=np.int64))
        lock = mm.build_mitigation_lock("synthetic", {self.name: cal}, cal_meta, cal_regime)
        entry = lock["runs"]["pca:-1"]["0.01"]
        phase = audit_meta.phase_primary.to_numpy()
        early_rows = np.repeat(flights.early.to_numpy(), flights.rows.to_numpy())
        for scheme in mm.SCHEMES:
            alarm = audit > mm.row_thresholds(scheme, entry["tau"], phase, audit_regime)
            self.assertAlmostEqual(alarm[post].mean(), out[f"{scheme}.tpr"], places=12)
            self.assertAlmostEqual(alarm[early_rows].mean(), out[f"{scheme}.tpr_early"], places=12)
            self.assertEqual(entry["kappa"][scheme], out[f"{scheme}.kappa"])
            fraction = mm.flight_alarm_counts(alarm, flights.start.to_numpy()) / flights.rows
            flagged = (fraction > entry["kappa"][scheme]).to_numpy()
            healthy = (flights.state == "healthy").to_numpy()
            self.assertAlmostEqual(flagged[healthy].mean(), out[f"{scheme}.ffr"], places=12)
            delays = [mm.first_flag(flagged[((flights.unit == u) & ~healthy).to_numpy()])
                      for u in engines]
            self.assertEqual(mm.lower_median(delays), out[f"{scheme}.median_delay"])

    def test_endpoint_tables_smoke(self):
        cal_meta, cal_regime = synthetic_meta((4, 8), 6, 90, self.rng)
        audit_meta, audit_regime = synthetic_meta((10, 11, 12), 14, 90, self.rng, healthy_flights=3)
        post = audit_meta.healthy.to_numpy() == 0
        cal_scores = {run: self.rng.lognormal(size=len(cal_meta)) for run in mm.RUNS}
        audit_scores = {run: self.rng.lognormal(size=len(audit_meta)) * np.where(post, 1.5, 1.0)
                        for run in mm.RUNS}
        lock = mm.build_mitigation_lock("synthetic", cal_scores, cal_meta, cal_regime)
        healthy = ~post
        healthy_meta = audit_meta[healthy].reset_index(drop=True)
        healthy_scores = {run: values[healthy] for run, values in audit_scores.items()}
        tables = mm.healthy_endpoint_tables("synthetic", lock, healthy_scores, healthy_meta,
                                            audit_regime[healthy])
        paired = tables["healthy_paired_stability"]
        np.testing.assert_allclose(paired.spread_pooled - paired.spread, paired.delta_spread)
        rates = tables["healthy_phase_fpr_by_scheme"]
        pca = rates[(rates.detector == "pca") & (rates.nominal_fpr == 0.01) & (rates.scheme == "pooled")
                    & (rates.unit == "all") & (rates.phase == "overall")].iloc[0]
        tau = lock["runs"]["pca:-1"]["0.01"]["tau"]["pooled"]
        self.assertEqual(int(np.sum(healthy_scores[("pca", -1)] > tau)), pca.alarms)
        self.assertEqual(len(mm.RUNS) * len(mm.TARGETS) * len(mm.ALTERNATIVES),
                         len(tables["engine_sign_counts"]))
        self.assertTrue((tables["engine_sign_counts"].engines == 3).all())
        source = mm.calibration_source_table("synthetic", (4, 8), cal_scores, cal_meta, cal_regime,
                                             healthy_scores, healthy_meta, audit_regime[healthy])
        self.assertEqual({4, 8}, set(source.calibration_source_engine))
        feasibility = mm.regime_feasibility_table("synthetic", {
            "calibration_healthy": (cal_meta.phase_primary.to_numpy(), cal_regime)})
        self.assertAlmostEqual(1.0, feasibility.share_of_rows.sum())
        flights = mm.audit_flight_table(audit_meta)
        eligible = {"s1_s3_s4": [10, 11, 12], "s2": [10, 11, 12], "d": [10, 11, 12]}
        abnormal = mm.abnormal_endpoint_tables("synthetic", lock, cal_scores, cal_meta, cal_regime,
                                               audit_scores, audit_meta, audit_regime, flights, eligible)
        guardrails = abnormal["guardrails"]
        self.assertEqual(len(mm.FAMILIES) * len(mm.ALTERNATIVES), len(guardrails))
        delays = abnormal["detection_delay"]
        self.assertEqual(len(mm.RUNS) * 3 * 3 * 3, len(delays))
        self.assertTrue(set(abnormal["separability_pauc"].scheme) == set(mm.SCHEMES))
        reduced, family = mm.ir_h(paired, "phase_conditioned")
        self.assertEqual(set(mm.FAMILIES), set(family))
        self.assertIn("guardrails", mm.TEMPLATES[(reduced, True)])

    def test_combined_audit_rows_restore_split_order(self):
        meta = pd.DataFrame({"unit": np.int16([1] * 9), "cycle": np.int16([1, 1, 2, 2, 2, 3, 3, 4, 4]),
                             "healthy": np.int8([1, 1, 0, 0, 0, 1, 1, 0, 0])})
        healthy_blocks, abnormal_blocks = [(0, 2), (5, 7)], [(2, 5), (7, 9)]
        values = np.arange(9.0)
        h_index, a_index = np.r_[0:2, 5:7], np.r_[2:5, 7:9]
        scores, combined, alt = mm.combine_audit_rows(
            healthy_blocks, {"meta": meta.iloc[h_index].reset_index(drop=True),
                             "scores": {"x": values[h_index]}, "alt": values[h_index]},
            abnormal_blocks, {"meta": meta.iloc[a_index].reset_index(drop=True),
                              "scores": {"x": values[a_index]}, "alt": values[a_index]})
        np.testing.assert_array_equal(values, scores["x"])
        np.testing.assert_array_equal(values, alt)
        pd.testing.assert_frame_equal(meta, combined)

    def test_audit_engine_plans(self):
        meta, _ = synthetic_meta((10, 11, 12), 6, 30, self.rng, healthy_flights=2)
        flights = mm.audit_flight_table(meta)
        engine_plans, flight_plans = mm.audit_engine_plans(flights, [10, 11, 12], 50,
                                                           np.random.default_rng(3))
        self.assertTrue((engine_plans.sum(axis=1) == 3).all())
        per_engine = flights.groupby("unit").size().to_numpy()
        np.testing.assert_array_equal(engine_plans @ per_engine, flight_plans.sum(axis=1))


if __name__ == "__main__":
    unittest.main()
