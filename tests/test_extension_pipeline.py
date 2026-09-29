"""Data-free tests for the extension pipeline (GENERALIZATION_PROTOCOL.md section 21). No N-CMAPSS data are read."""

from __future__ import annotations

import ast
import functools
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import ext_calibration as xc  # noqa: E402
import ext_common as ec  # noqa: E402
import ext_endpoints as xe  # noqa: E402
import ext_summary as xs  # noqa: E402
import extension_synthetic as syn  # noqa: E402
import mssp_adversarial as ma  # noqa: E402

PROTOCOL_ROLES = {  # GENERALIZATION_PROTOCOL.md section 3 (R-ALLOC applied to metadata)
    "DS01": ((1, 2, 3), 3, (4, 5, 6)), "DS04": ((1, 2, 4), 4, (3, 5, 6)), "DS05": ((1, 2, 4), 4, (3, 5, 6)),
    "DS06": ((1, 2, 4), 4, (3, 5, 6)), "DS07": ((1, 2, 4), 4, (3, 5, 6)), "DS08a": ((1, 2, 4), 4, (3, 5, 6, 7, 8, 9)),
    "DS08c": ((1, 2, 6), 6, (3, 4, 5)),
}
PROTOCOL_VOLUME = {"DS01": 78000, "DS04": 96000, "DS05": 78000, "DS06": 66000, "DS07": 78000, "DS08a": 60000,
                   "DS03": 102000}


class Patch:
    def __init__(self):
        self.saved = []

    def __call__(self, obj, name, value):
        self.saved.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def undo(self):
        for obj, name, value in reversed(self.saved):
            setattr(obj, name, value)
        self.saved.clear()


class Allocation(unittest.TestCase):
    def test_registry_matches_protocol_table(self):
        registry = ec.load_registry()
        for key, (fit, validation, calibration) in PROTOCOL_ROLES.items():
            s = registry[key]
            self.assertEqual((s.fit, s.validation, s.calibration), (fit, validation, calibration), key)
            self.assertTrue(s.assert_disjoint())
            self.assertFalse(set(s.audit) & (set(s.fit) | set(s.calibration)))
        self.assertEqual(registry["DS02"].calibration, (18, 20))
        self.assertEqual(registry["DS03"].fit, (1, 2, 3, 5, 6, 7, 9))

    def test_allocation_is_metadata_only_and_deterministic(self):
        params = list(inspect.signature(ec.allocate).parameters)
        self.assertEqual(params, ["dev_engines"])
        engines = [(3, 2), (1, 1), (2, 3), (6, 2), (5, 3), (4, 1)]
        self.assertEqual(ec.allocate(engines), ec.allocate(list(reversed(engines))))
        self.assertEqual(ec.allocate(engines)["calibration"], (4, 5, 6))

    def test_composition_volumes_and_eligibility(self):
        registry = ec.load_registry()
        for key, volume in PROTOCOL_VOLUME.items():
            self.assertEqual(ec.composition_volume(registry[key]), volume, key)
        self.assertFalse(ec.composition_eligible(registry["DS08c"]))
        self.assertFalse(ec.composition_eligible(registry["DS02"]))
        self.assertTrue(all(ec.composition_eligible(registry[k]) for k in ("DS01", "DS04", "DS05", "DS08a", "DS03")))


class PersistenceRules(unittest.TestCase):
    @staticmethod
    def brute(e, starts, ends, rule):
        out = np.zeros(len(e), dtype=bool)
        for s, t in zip(starts, ends):
            for i in range(s, t):
                window = e[max(s, i - {"R0": 0, "R1": 2, "R2": 4}[rule]):i + 1]
                out[i] = window[-1] if rule == "R0" else (window.sum() >= 3 and (rule == "R2" or len(window) == 3))
        return out

    def test_rules_match_brute_force_and_never_cross_flights(self):
        rng = np.random.default_rng(0)
        for _ in range(50):
            lengths = rng.integers(1, 30, size=rng.integers(1, 6))
            ends = np.cumsum(lengths)
            starts = np.r_[0, ends[:-1]]
            e = rng.random(ends[-1]) < rng.uniform(0.1, 0.9)
            for rule in ec.RULES:
                np.testing.assert_array_equal(xc.apply_rule(e, starts, ends, rule), self.brute(e, starts, ends, rule))

    def test_flight_boundary_resets(self):
        e = np.array([1, 1, 1, 1, 1, 1], dtype=bool)
        starts, ends = np.array([0, 2]), np.array([2, 6])
        np.testing.assert_array_equal(xc.apply_rule(e, starts, ends, "R1"), [0, 0, 0, 0, 1, 1])
        np.testing.assert_array_equal(xc.apply_rule(e, starts, ends, "R2"), [0, 0, 0, 0, 1, 1])

    def test_events_count_maximal_runs_within_flights(self):
        a = np.array([1, 1, 0, 1, 1, 1, 0, 0, 1], dtype=bool)
        starts, ends = np.array([0, 4]), np.array([4, 9])
        np.testing.assert_array_equal(xc.flight_events(a, starts, ends), [2, 2])


class Composition(unittest.TestCase):
    def test_designs_are_row_count_matched_and_class_balanced(self):
        for pool, volume in (({4: 1, 5: 3, 6: 2}, 78000), ({3: 2, 5: 3, 6: 3}, 96000),
                             ({3: 1, 5: 2, 6: 3, 7: 2, 8: 2, 9: 1}, 60000), ({4: 2, 8: 3}, 102000)):
            designs = xc.build_designs(pool, volume)
            for d in designs:
                if d.volume == "N":
                    self.assertEqual(sum(d.members.values()), volume, d.name)
                    per_class = {}
                    for g, n in d.members.items():
                        per_class[pool[g]] = per_class.get(pool[g], 0) + n
                    if set(d.codes) & {"E", "E+"}:
                        self.assertLessEqual(max(per_class.values()) - min(per_class.values()), 1, d.name)
            names = {d.name for d in designs}
            self.assertTrue({f"single_{g}" for g in pool} <= names)
            self.assertTrue({f"full_{g}" for g in pool} | {"full_pool"} <= names)

    def test_designs_use_metadata_only(self):
        self.assertEqual(list(inspect.signature(xc.build_designs).parameters), ["pool_classes", "volume"])
        self.assertEqual(list(inspect.signature(xc.design_thresholds).parameters)[:4],
                         ["designs", "cal_units", "cal_phase", "score_map"])

    def test_subsamples_are_nested_deterministic_and_calibration_only(self):
        units = np.repeat([4, 5, 6], [500, 700, 600])
        perms, index = xc.engine_permutations(units)
        perms2, _ = xc.engine_permutations(units)
        for key in perms:
            np.testing.assert_array_equal(perms[key], perms2[key])
        pool = {4: 1, 5: 3, 6: 2}
        designs = {d.name: d for d in xc.build_designs(pool, 240)}
        single = set(xc.design_rows(designs["single_4"], perms, index, 0))
        mixed = set(xc.design_rows(designs["mixed_12"], perms, index, 0))
        self.assertTrue({r for r in mixed if units[r] == 4} <= single)
        self.assertEqual(len(xc.design_rows(designs["balanced"], perms, index, 3)), 240)


class QuantileRegressionParity(unittest.TestCase):
    def test_worker_copy_equals_frozen_function(self):
        import ext_qfit
        frozen = inspect.getsource(ma.fit_quantile_threshold).split("\n", 1)[1]
        ours = inspect.getsource(ext_qfit.fit_quantile_threshold).split("\n", 1)[1]
        self.assertEqual(frozen, ours)
        self.assertEqual(ext_qfit.QR_STRIDE, ma.QR_STRIDE)

    def test_features_match_frozen_standardize(self):
        rng = np.random.default_rng(2)
        cal, test = rng.normal(size=(500, 4)) * [1e4, 0.1, 10, 20], rng.normal(size=(300, 4)) * [1e4, 0.1, 10, 20]
        (cal_z, test_z), _ = ma.standardize(cal, test)
        scale = xc.q_scale(cal)
        np.testing.assert_array_equal(xc.q_features(cal, scale), ma.quadratic_surface(cal_z))
        np.testing.assert_array_equal(xc.q_features(test, scale), ma.quadratic_surface(test_z))


class Metrics(unittest.TestCase):
    def test_quality_metrics(self):
        alarms = np.array([[1.0, 2.0, 10.0], [0.0, 1.0, 1.0]])
        rows = np.array([[100.0, 100.0, 100.0], [100.0, 100.0, 50.0]])
        q = xe.quality_from_counts(alarms, rows, 0.01)
        fpr = alarms / rows
        a2 = np.abs(fpr - 0.01).max(axis=1)
        self.assertAlmostEqual(q["me_a2"], a2.mean())
        self.assertAlmostEqual(q["we_a2"], a2.max())
        pooled = alarms.sum(0) / rows.sum(0)
        self.assertAlmostEqual(q["pooled"]["max_abs_error"], np.abs(pooled - 0.01).max())
        self.assertAlmostEqual(q["ew"]["max_abs_error"], np.abs(fpr.mean(0) - 0.01).max())
        self.assertAlmostEqual(q["pooled"]["spread"], pooled.max() - pooled.min())

    def test_matched_comparison_never_extrapolates(self):
        points = pd.DataFrame({"ffr": [0.0, 0.3], "kappa_high": [1.0, 0.1], "median_delay": [5.0, 1.0]})
        chosen, supported = ma.match_anchor(points, 0.10, 100)
        self.assertFalse(supported)
        self.assertEqual(ma.run_label_from_differences([]), "not evaluable")


class Bootstrap(unittest.TestCase):
    def test_uext1_point_equals_direct_metrics(self):
        rng = np.random.default_rng(1)
        def meta(units, flights, n):
            rows = [(u, c) for u in units for c in range(1, flights + 1) for _ in range(n)]
            m = pd.DataFrame(rows, columns=["unit", "cycle"])
            m["phase_primary"] = np.tile(np.repeat([0, 1, 2], [n // 3, n // 3, n - 2 * (n // 3)]), len(units) * flights)
            return m
        cal_meta, test_meta = meta([4, 5], 3, 90), meta([7, 8, 9], 3, 90)
        cal, test = rng.normal(size=len(cal_meta)), rng.normal(size=len(test_meta)) + 0.2
        run = xe.BootstrapRun(cal, cal_meta.phase_primary.to_numpy(), __import__("final_validation").flight_index(cal_meta),
                              test, test_meta.phase_primary.to_numpy(),
                              __import__("final_validation").flight_index(test_meta))
        flights = __import__("final_validation").flight_index(test_meta)
        _, engine = ma.engine_weights(flights, np.ones(len(flights), dtype=np.int64))
        point = run.replicate(np.ones(6, dtype=np.int64), np.ones(9, dtype=np.int64), 0.01, engine, 3, np.ones(3))
        taus = xc.quantile_taus(cal, cal_meta.phase_primary.to_numpy(), 0.01)
        for arm in ("pooled", "phase_conditioned"):
            alarm = test > xc.row_thresholds(arm, taus, test_meta.phase_primary.to_numpy())
            a, r = xe.cell_counts(alarm, test_meta.unit.to_numpy(), test_meta.phase_primary.to_numpy(), [7, 8, 9])
            q = xe.quality_from_counts(a, r, 0.01)
            self.assertAlmostEqual(point[f"{arm}.ME_A2"], q["me_a2"])
            self.assertAlmostEqual(point[f"{arm}.WE_A2"], q["we_a2"])
            self.assertAlmostEqual(point[f"{arm}.pooled_A2"], q["pooled"]["max_abs_error"])

    def test_cross_dataset_hierarchy_resamples_families_then_subsets(self):
        source = inspect.getsource(xs.uext2)
        self.assertIn("family_list", source)
        self.assertLess(source.index("sampled = [family_list"), source.index("chosen = [[members"))
        self.assertLess(source.index("chosen = [[members"), source.index("picks = [[(s, int(rng.integers(0, n_rep)))"))
        values = {"A": 1.0, "B": 3.0, "C": 5.0, "D": 10.0}
        self.assertEqual(xs.family_statistic(values, [["A"], ["B", "C"], ["D"]]), 4.0)

    def test_family_majority(self):
        patch = Patch()
        patch(ec, "FAMILIES", {**ec.FAMILIES})
        try:
            held = xs.family_holds({"DS05": True, "DS06": True, "DS07": False, "DS01": False})
            self.assertTrue(held["F3"])
            self.assertFalse(held["F1"])
        finally:
            patch.undo()


class Gating(unittest.TestCase):
    def test_phase_lock_never_reads_official_test(self):
        import ext_pipeline as xp
        source = inspect.getsource(xp.phase_lock)
        self.assertNotIn("load_audit_rows", source)
        load_dev = inspect.getsource(__import__("ext_models").load_development_healthy)
        self.assertIn('"dev"', load_dev)
        self.assertNotIn('"test"', load_dev)

    def test_marker_is_written_before_the_first_official_test_read(self):
        import ext_pipeline as xp
        tree = ast.parse(inspect.getsource(xp.phase_audit))
        calls = [(n.lineno, ast.unparse(n.func)) for n in ast.walk(tree) if isinstance(n, ast.Call)]
        marker = min(line for line, name in calls if name == "ec.write_json")
        read = min(line for line, name in calls if name == "xm.load_audit_rows")
        self.assertLess(marker, read)

    def test_audit_scoring_separates_healthy_and_post_onset_rows(self):
        import ext_models as xm
        import ext_pipeline as xp
        meta = pd.DataFrame({"unit": [7, 7, 7, 7, 8, 8], "cycle": [1, 1, 2, 2, 1, 2], "healthy": [1, 1, 0, 0, 1, 0],
                             "phase_primary": [0, 1, 0, 1, 0, 1]})
        rows = xm.Rows(np.arange(6.0)[:, None], np.zeros((6, 4)), meta, [], np.zeros((6, 32)), [])
        calls = []

        def fake_score_all(models, part):
            calls.append(part.meta.healthy.unique().tolist())
            return {("pca", -1): part.x[:, 0] * 10}

        saved = xm.score_all
        xm.score_all = fake_score_all
        try:
            scores = xp.score_audit(None, rows)
        finally:
            xm.score_all = saved
        self.assertEqual(calls, [[1], [0]])
        np.testing.assert_array_equal(scores[("pca", -1)], np.arange(6.0) * 10)

    def test_protected_paths_refused(self):
        for path in ("results/confirmation_ds03/x.csv", "results/mssp_mitigation/ds02/y.json", "paper/ress/z"):
            with self.assertRaises(ec.ExtensionError):
                ec.guard_path(ROOT / path)

    def test_frozen_baseline_unchanged(self):
        self.assertTrue(ec.verify_baseline())


class EndToEndSynthetic(unittest.TestCase):
    """Phase L -> committed-lock gate -> one-shot Phase A on a synthetic N-CMAPSS-shaped HDF5 file."""

    @classmethod
    def setUpClass(cls):
        import torch
        if not torch.cuda.is_available():
            raise unittest.SkipTest("CUDA required (CPU fallback is disabled)")

    def setUp(self):
        import ext_cvae
        import ext_models as xm
        import ext_pipeline as xp
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = Patch()
        syn.install(self.patch, self.tmp.name)
        self.patch(ec, "VOLUME_QUANTUM", 60)
        self.patch(ec, "append_access_log", lambda *a, **k: None)
        self.patch(ext_cvae, "MAX_EPOCHS", 3)
        self.patch(xm, "select_lstm_epochs", functools.partial(xm.select_lstm_epochs, max_epochs=3))
        self.patch(xe, "bootstrap_uext1", functools.partial(xe.bootstrap_uext1, replicates=12, workers=2))
        self.patch(xc, "Q_WORKERS", 4)
        self.xp = xp

    def tearDown(self):
        self.patch.undo()
        self.tmp.cleanup()

    def test_lock_then_one_shot_audit(self):
        key = "DS99"
        self.xp.phase_lock(key, log=lambda m: None)
        lock_dir = ec.RESULTS / key / "lock"
        lock = json.loads((lock_dir / "calibration_lock.json").read_text())
        self.assertEqual(lock["roles"]["calibration"], [4, 5, 6])
        self.assertFalse((ec.RESULTS / key / "audit").exists())
        self.assertIn("single_4", {d["name"] for d in lock["composition"]["designs"]})
        with self.assertRaises(ec.ExtensionError):  # the lock is not committed to git
            self.xp.phase_audit(key, log=lambda m: None)
        self.patch(ec, "git_tracked_and_clean", lambda path: True)
        self.xp.phase_audit(key, log=lambda m: None)
        audit = ec.RESULTS / key / "audit"
        self.assertTrue((audit / "official_test_opened.json").exists())
        for table in ("transport_summary", "paired_transport", "flight_false_flags", "matched_labels",
                      "composition_metrics", "persistence_calibration", "bootstrap_uext1_ci"):
            frame = pd.read_csv(audit / f"{table}.csv")
            self.assertGreater(len(frame), 0, table)
        summary = pd.read_csv(audit / "transport_summary.csv")
        self.assertEqual(set(summary.arm), set(ec.ARMS))
        self.assertEqual(len(summary), 10 * 3 * 3)
        with self.assertRaises(ec.ExtensionError):  # one-shot: a second audit is refused
            self.xp.phase_audit(key, log=lambda m: None)
        with self.assertRaises(ec.ExtensionError):  # a second lock is refused
            self.xp.phase_lock(key, log=lambda m: None)
        record = json.loads((audit / "audit_record.json").read_text())
        for name, digest in record["outputs_sha256"].items():
            self.assertEqual(ec.file_digest(audit / f"{name}.csv"), digest)


class SummaryOnSyntheticCohort(unittest.TestCase):
    """The pre-specified decision code runs end to end on a synthetic six-subset, five-family cohort."""

    @classmethod
    def setUpClass(cls):
        import torch
        if not torch.cuda.is_available():
            raise unittest.SkipTest("CUDA required (CPU fallback is disabled)")

    def setUp(self):
        import ext_cvae
        import ext_models as xm
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = Patch()
        syn.install_cohort(self.patch, self.tmp.name)
        self.patch(ec, "VOLUME_QUANTUM", 60)
        self.patch(ec, "append_access_log", lambda *a, **k: None)
        self.patch(ec, "git_tracked_and_clean", lambda path: True)
        self.patch(ext_cvae, "MAX_EPOCHS", 2)
        self.patch(xm, "select_lstm_epochs", functools.partial(xm.select_lstm_epochs, max_epochs=2))
        self.patch(xe, "bootstrap_uext1", functools.partial(xe.bootstrap_uext1, replicates=10, workers=2))
        self.patch(xs, "uext2", functools.partial(xs.uext2, replicates=50))
        self.patch(xs, "composition_bootstrap", functools.partial(xs.composition_bootstrap, replicates=50))

    def tearDown(self):
        self.patch.undo()
        self.tmp.cleanup()

    def test_decisions(self):
        import ext_pipeline as xp
        for key in ec.NEW_ORDER:
            xp.phase_lock(key, log=lambda m: None)
        for key in ec.NEW_ORDER:
            xp.phase_audit(key, log=lambda m: None)
        decisions = xs.main(log=lambda m: None)
        for h in ("H1", "H2", "H3", "H4", "H5", "H6"):
            self.assertIn("verdict", decisions[h], h)
        self.assertIn(decisions["original_story"]["class"],
                      ("GENERALIZED", "PARTIALLY GENERALIZED", "CONFIGURATION-SPECIFIC", "REFUTED"))
        self.assertIn(decisions["matrix_stories"]["headline"],
                      ("M-A", "M-B", "M-C", "M-D", "M-E", "M-C + M-B", "MIXED"))
        self.assertEqual(set(decisions["rescope_flags"]), set("ABCDEF"))
        self.assertEqual(set(decisions["H4"]["subset_supports"]), {"DS91", "DS92", "DS93", "DS96", "DS94"})
        boot = pd.read_csv(ec.RESULTS / "summary" / "uext2_cross_dataset.csv")
        self.assertTrue((boot.top_level_units == 5).all())


if __name__ == "__main__":
    unittest.main()
