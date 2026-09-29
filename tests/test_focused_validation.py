"""Data-free tests for the final focused validation (docs/extension/FOCUSED_VALIDATION_PLAN.md). No N-CMAPSS data."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import ext_focused_validation as fvx  # noqa: E402


def identical_flights(n_flights, per_phase=1000):
    """Every flight has scores 0..per_phase-1 in each phase (known quantiles)."""
    scores, phase, flight = [], [], []
    for f in range(n_flights):
        for p in range(3):
            scores.append(np.arange(per_phase, dtype=np.float64))
            phase.append(np.full(per_phase, p))
            flight.append(np.full(per_phase, f))
    return np.concatenate(scores), np.concatenate(phase), np.concatenate(flight)


class Plan(unittest.TestCase):
    def test_plan_hash_constant_matches_the_frozen_plan(self):
        digest = hashlib.sha256(fvx.PLAN.read_bytes()).hexdigest()
        self.assertEqual(digest, fvx.PLAN_SHA256)

    def test_frozen_parameters(self):
        self.assertEqual((fvx.ALPHA, fvx.FOLDS, fvx.R_CROSSFIT, fvx.K_LOCAL, fvx.R_LOCAL), (0.01, 5, 200, 5, 200))
        self.assertEqual((fvx.SEED_CROSSFIT, fvx.SEED_CLASS_BOOT, fvx.SEED_LOCAL), (20261004, 20261003, 20261005))


class EngineMachinery(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.n_flights = 12
        sizes = rng.integers(300, 900, size=(self.n_flights, 3))
        scores, phase, flight = [], [], []
        for f in range(self.n_flights):
            for p in range(3):
                scores.append(rng.gamma(2.0 + p, 1.0 + 0.1 * f, size=sizes[f, p]))
                phase.append(np.full(sizes[f, p], p))
                flight.append(np.full(sizes[f, p], f))
        self.scores, self.phase, self.flight = map(np.concatenate, (scores, phase, flight))
        self.engine = fvx.EngineData(self.scores, self.phase, self.flight)

    def test_phase_and_pooled_quantiles_equal_numpy_higher(self):
        train = np.zeros(self.n_flights, dtype=np.int64)
        train[[0, 3, 4, 9]] = 1
        rows = np.isin(self.flight, [0, 3, 4, 9])
        taus = self.engine.phase_taus(train)
        for p in range(3):
            self.assertEqual(taus[p], np.quantile(self.scores[rows & (self.phase == p)], 0.99, method="higher"))
        self.assertEqual(self.engine.pooled_tau(train), np.quantile(self.scores[rows], 0.99, method="higher"))

    def test_fixed_a2_matches_direct_count(self):
        taus = np.array([3.0, 4.0, 5.0])
        mask = np.ones(self.n_flights, dtype=bool)
        mask[:2] = False
        a2, fpr = self.engine.fixed_a2(taus, mask)
        rows = self.flight >= 2
        direct = [np.mean(self.scores[rows & (self.phase == p)] > taus[p]) for p in range(3)]
        np.testing.assert_allclose(fpr, direct, rtol=0, atol=1e-15)
        self.assertAlmostEqual(a2, max(abs(v - 0.01) for v in direct), places=15)

    def test_crossfit_is_seeded_and_uses_out_of_fold_thresholds(self):
        a = fvx.crossfit_draws(self.engine, np.random.default_rng([1, 2]), repetitions=5)
        b = fvx.crossfit_draws(self.engine, np.random.default_rng([1, 2]), repetitions=5)
        np.testing.assert_array_equal(a, b)
        self.assertTrue(np.all(a >= 0))

    def test_class_preserving_plans_keep_every_class(self):
        rows = []
        for unit, cls, n in ((3, 1, 4), (5, 2, 3), (7, 2, 5), (9, 3, 2)):
            for cycle in range(1, n + 1):
                rows += [{"unit": unit, "cycle": cycle}] * 3
        meta = pd.DataFrame(rows)
        classes = {"3": 1, "5": 2, "7": 2, "9": 3}
        flights, plans = fvx.class_preserving_plans(meta, classes, 300, np.random.default_rng(4))
        unit_of_flight = np.array([f[0] for f in flights])
        for plan in plans:
            drawn = {classes[str(u)] for u in unit_of_flight[plan > 0]}
            self.assertEqual(drawn, {1, 2, 3})
            self.assertEqual(plan[unit_of_flight == 3].sum(), 4)   # single-engine classes keep their engine
            self.assertEqual(plan[unit_of_flight == 9].sum(), 2)
        both = [(plan[unit_of_flight == 5].sum() > 0, plan[unit_of_flight == 7].sum() > 0) for plan in plans]
        self.assertTrue(any(a and not b for a, b in both) and any(b and not a for a, b in both))


class KnownAnswers(unittest.TestCase):
    """Identical flights: every per-phase 0.99 'higher' quantile is 990, so every held-out FPR is 0.9%."""

    def setUp(self):
        self.engine = fvx.EngineData(*identical_flights(10))

    def test_crossfit_and_k_matched_floors(self):
        np.testing.assert_allclose(fvx.crossfit_draws(self.engine, np.random.default_rng(0), repetitions=3),
                                   0.001, rtol=0, atol=1e-15)
        np.testing.assert_allclose(fvx.k_matched_draws(self.engine, np.random.default_rng(0), repetitions=3),
                                   0.001, rtol=0, atol=1e-15)

    def test_local_recalibration_uses_first_k_and_evaluates_the_rest(self):
        fleet = {"pooled": np.full(3, 500.0), "phase_conditioned": np.array([100.0, 995.0, 999.0])}
        out = fvx.local_recalibration(self.engine, fleet, k=5)
        self.assertEqual(out["eval_flights"], 5)
        self.assertAlmostEqual(out["local_A2|phase_conditioned"], 0.001, places=15)
        self.assertAlmostEqual(out["local_A2|pooled"], 0.001, places=15)
        self.assertAlmostEqual(out["fleet_eval_A2|pooled"], abs(499 / 1000 - 0.01), places=15)
        self.assertAlmostEqual(out["fleet_eval_A2|phase_conditioned"], abs(899 / 1000 - 0.01), places=15)


class EndToEndSynthetic(unittest.TestCase):
    """Locks, audits and summary on the synthetic cohort, then the focused validation with gates G1-G6 live."""

    @classmethod
    def setUpClass(cls):
        import torch
        if not torch.cuda.is_available():
            raise unittest.SkipTest("CUDA required (CPU fallback is disabled)")

    def test_focused_validation_runs_and_gates_hold(self):
        import functools
        import json
        import tempfile

        sys.path.insert(0, str(ROOT / "tests"))
        import ext_calibration as xc
        import ext_common as ec
        import ext_cvae
        import ext_endpoints as xe
        import ext_models as xm
        import ext_pipeline as xp
        import ext_summary as xs
        import extension_synthetic as syn

        saved = []

        def patch(obj, name, value):
            saved.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)

        tmp = tempfile.TemporaryDirectory()
        try:
            syn.install_cohort(patch, tmp.name, flights=14, healthy=10)
            patch(ec, "VOLUME_QUANTUM", 60)
            patch(ec, "append_access_log", lambda *a, **k: None)
            patch(ec, "git_tracked_and_clean", lambda path: True)
            patch(ext_cvae, "MAX_EPOCHS", 2)
            patch(xm, "select_lstm_epochs", functools.partial(xm.select_lstm_epochs, max_epochs=2))
            patch(ec, "BOOTSTRAP_REPLICATES", 12)
            patch(xe, "bootstrap_uext1", functools.partial(xe.bootstrap_uext1, replicates=12, workers=2))
            patch(xs, "uext2", functools.partial(xs.uext2, replicates=40))
            patch(xs, "composition_bootstrap", functools.partial(xs.composition_bootstrap, replicates=40))
            patch(xc, "Q_WORKERS", 4)
            for key in ec.NEW_ORDER:
                xp.phase_lock(key, log=lambda m: None)
            for key in ec.NEW_ORDER:
                xp.phase_audit(key, log=lambda m: None)
            xs.main(log=lambda m: None)
            for key in ec.NEW_ORDER:
                fvx.run_subset(key, log=lambda m: None, workers=4)
                with self.assertRaises(ec.ExtensionError):  # outputs are written once
                    fvx.run_subset(key, log=lambda m: None, workers=4)
            summary = fvx.summarize(log=lambda m: None)
            self.assertIn(summary["transport_claim"], ("STRENGTHENED", "NARROWED", "WEAKENED"))
            self.assertTrue(summary["G6_uext2_reproduced"])
            root = fvx.output_root()
            for key in ec.NEW_ORDER:
                record = json.loads((root / key / "validation_record.json").read_text())
                self.assertTrue(record["gates"]["G5_original_replicates"].startswith("equal"))
                noise = pd.read_csv(root / key / "engine_noise_floor.csv")
                self.assertEqual(set(noise.arm), set(fvx.ARMS))
                local = pd.read_csv(root / key / "local_recalibration.csv")
                self.assertTrue((local.eval_flights == 10 - fvx.K_LOCAL).all())
                ci = pd.read_csv(root / key / "bootstrap_class_preserving_ci.csv")
                self.assertEqual(set(ci.design), {"original", "class_preserving"})
        finally:
            for obj, name, value in reversed(saved):
                setattr(obj, name, value)
            tmp.cleanup()


class Rules(unittest.TestCase):
    def test_majority_rules(self):
        self.assertTrue(fvx.majority_exceeds([True] * 4 + [False] * 3))
        self.assertFalse(fvx.majority_exceeds([True] * 3 + [False] * 4))
        self.assertTrue(fvx.majority_exceeds([True, True, False], residual=False))
        self.assertFalse(fvx.majority_exceeds([True, False, False], residual=False))


if __name__ == "__main__":
    unittest.main()
