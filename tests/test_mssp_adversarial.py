"""Data-free guards for the MSSP adversarial validation (docs/mssp/adversarial_validation_plan.md).

No N-CMAPSS file is read. Tests use synthetic arrays, the frozen code, and committed CSV/JSON
outputs under results/ (which they re-derive deterministically where possible).
"""

import inspect
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mssp_adversarial as ma  # noqa: E402
import mssp_mitigation as mm  # noqa: E402
from second_stage_audit import phase_labels  # noqa: E402

RESULTS = ROOT / "results/mssp_adversarial"


def synthetic_trajectory(rng, engines=(1, 2, 3), healthy=10, post=15):
    rows = []
    for unit in engines:
        rows += [{"unit": unit, "state": "healthy", "k": -1, "alarm_fraction": rng.uniform(0, .05)}
                 for _ in range(healthy)]
        rows += [{"unit": unit, "state": "post_onset", "k": k, "alarm_fraction": rng.uniform(0, .02 + .01 * k)}
                 for k in range(post)]
    return pd.DataFrame(rows)


class Formulas(unittest.TestCase):
    def test_calibration_error_formulas(self):
        m = ma.calibration_errors([0.005, 0.01, 0.03], 0.012, 0.01)
        self.assertAlmostEqual(m["spread"], 0.025)
        self.assertAlmostEqual(m["max_abs_error"], 0.02)
        self.assertAlmostEqual(m["rms_error"], math.sqrt((0.005 ** 2 + 0 + 0.02 ** 2) / 3))
        self.assertAlmostEqual(m["mean_abs_error"], 0.025 / 3)
        self.assertAlmostEqual(m["overall_abs_error"], 0.002)

    def test_spread_can_shrink_while_calibration_worsens(self):
        """The attack-A scenario: equal phases far from alpha."""
        wide, flat = ma.calibration_errors([0.009, 0.01, 0.011], .01, .01), ma.calibration_errors([.03, .03, .03], .03, .01)
        self.assertLess(flat["spread"], wide["spread"])
        self.assertGreater(flat["max_abs_error"], wide["max_abs_error"])

    def test_category_rule(self):
        self.assertEqual(ma.category(-1, -1, -1), 1)
        self.assertEqual(ma.category(-1, 0, 1), 2)
        self.assertEqual(ma.category(-1, -1, 1), 3)
        self.assertEqual(ma.category(1, -1, 1), 3)
        self.assertEqual(ma.category(0, 0, 0), 4)

    def test_decomposition_components(self):
        pure_phase = np.array([[0.005, 0.01, 0.03]] * 3)
        parts = ma.error_decomposition(pure_phase, 0.01)
        self.assertAlmostEqual(parts["engine"], 0.0)
        self.assertAlmostEqual(parts["interaction"], 0.0)
        self.assertAlmostEqual(parts["mse"], parts["bias_sq"] + parts["phase"])
        pure_engine = np.array([[0.02] * 3, [0.01] * 3, [0.0] * 3])
        parts = ma.error_decomposition(pure_engine, 0.01)
        self.assertAlmostEqual(parts["phase"], 0.0)
        self.assertAlmostEqual(parts["mse"], parts["engine"])

    def test_robustness_classification(self):
        self.assertEqual(ma.classify_direction({0.005: 1, 0.01: 1, 0.02: 1}), "invariant")
        self.assertEqual(ma.classify_direction({0.005: 6 / 7, 0.01: 1, 0.02: 5 / 7}), "mostly invariant")
        self.assertEqual(ma.classify_direction({0.005: 2 / 7, 0.01: 1, 0.02: 1}), "reversed")
        self.assertEqual(ma.classify_direction({0.005: 4 / 7, 0.01: 5 / 7, 0.02: 4 / 7}), "target-sensitive")
        self.assertEqual(ma.classify_direction({0.005: 1, 0.01: 3 / 7, 0.02: 1}), "not supported at 1%")


class Weighting(unittest.TestCase):
    def rates(self):
        rows = []
        for scheme in ("pooled", "phase_conditioned", "causal_regime"):
            for unit, scale, n in (("1", 1.0, 1000), ("2", 3.0, 100)):
                for phase, base in (("climb", .002), ("cruise", .005), ("descent", .02)):
                    rate = base * scale if scheme == "pooled" else .01 * scale
                    rows.append({"dataset": "x", "detector": "pca", "seed": -1, "nominal_fpr": .01, "scheme": scheme,
                                 "unit": unit, "phase": phase, "n": n, "alarms": round(rate * n), "rate": rate})
                rows.append({"dataset": "x", "detector": "pca", "seed": -1, "nominal_fpr": .01, "scheme": scheme,
                             "unit": unit, "phase": "overall", "n": 3 * n,
                             "alarms": sum(r["alarms"] for r in rows[-3:]), "rate": sum(r["alarms"] for r in rows[-3:]) / (3 * n)})
            for phase in ("climb", "cruise", "descent", "overall"):
                part = [r for r in rows if r["scheme"] == scheme and r["phase"] == phase and r["unit"] != "all"]
                n, k = sum(r["n"] for r in part), sum(r["alarms"] for r in part)
                rows.append({"dataset": "x", "detector": "pca", "seed": -1, "nominal_fpr": .01, "scheme": scheme,
                             "unit": "all", "phase": phase, "n": n, "alarms": k, "rate": k / n})
        return pd.DataFrame(rows)

    def test_row_pooled_and_equal_engine_differ(self):
        quality = ma.calibration_quality_table(self.rates())
        c = quality[quality.scheme == "phase_conditioned"].set_index("unit")
        self.assertAlmostEqual(c.loc["equal_engine", "climb_fpr"], (0.01 + 0.03) / 2)
        self.assertAlmostEqual(c.loc["all", "climb_fpr"], (10 + 3) / 1100)
        self.assertNotAlmostEqual(c.loc["all", "rms_error"], c.loc["equal_engine", "rms_error"])
        paired = ma.paired_quality_table(quality)
        self.assertEqual(set(paired.weighting), {"row_pooled", "per_engine", "equal_engine"})

    def test_engine_weights_recover_draw_counts(self):
        flights = [(1, 0, None), (1, 1, None), (2, 0, None), (2, 1, None), (2, 2, None)]
        multiplicity = np.array([2, 2, 3, 0, 3])  # engine 1 drawn twice, engine 2 twice
        times, index = ma.engine_weights(flights, multiplicity)
        self.assertEqual(times.tolist(), [2.0, 2.0])
        self.assertEqual(index.tolist(), [0, 0, 1, 1, 1])


class OperatingCharacteristic(unittest.TestCase):
    def test_matches_brute_force(self):
        rng = np.random.default_rng(1)
        part = synthetic_trajectory(rng)
        kappas, sources = ma.candidate_kappas(rng.uniform(0, .05, 32))
        curve = ma.operating_characteristic(part, kappas, sources, [1, 2, 3])
        healthy = part[part.state == "healthy"].alarm_fraction.to_numpy()
        for i in rng.choice(len(kappas), 40, replace=False):
            kappa = kappas[i]
            self.assertEqual(curve.flagged_healthy.iloc[i], int((healthy > kappa).sum()))
            delays = []
            for unit in (1, 2, 3):
                post = part[(part.unit == unit) & (part.state == "post_onset")].sort_values("k").alarm_fraction.to_numpy()
                flagged = post > kappa
                self.assertEqual(curve[f"delay_engine_{unit}"].iloc[i], mm.first_flag(flagged))
                self.assertEqual(curve[f"persistence_delay_engine_{unit}"].iloc[i], mm.persistence_flag(flagged))
                delays.append(mm.first_flag(flagged))
            self.assertEqual(curve.median_delay.iloc[i], mm.lower_median(delays))

    def test_candidate_grid_is_calibration_only(self):
        kappas, sources = ma.candidate_kappas(np.array([0.3, 0.1, 0.1]))
        self.assertIn(0.0, kappas)
        self.assertTrue(np.all(np.isin(ma.FIXED_KAPPA_GRID, kappas)))
        self.assertEqual(len(kappas), len(ma.FIXED_KAPPA_GRID) + 3)
        self.assertEqual(list(inspect.signature(ma.candidate_kappas).parameters), ["calibration_fraction"])
        source = inspect.getsource(ma.candidate_kappas)
        for forbidden in ("post_onset", "abnormal", "audit", "state"):
            self.assertNotIn(forbidden, source)

    def test_matching_rules_and_no_extrapolation(self):
        points = pd.DataFrame({"ffr": [0.0, 0.02, 0.04, 0.30], "kappa_high": [1.0, .5, .4, .1],
                               "kappa_low": [.9, .45, .35, .05], "median_delay": [9.0, 5.0, 4.0, 1.0]})
        chosen, ok = ma.match_anchor(points, 0.03, 50)          # tie 0.02/0.04 -> lower FFR
        self.assertEqual(float(chosen.ffr), 0.02)
        self.assertTrue(ok)
        chosen, ok = ma.match_anchor(points, 0.15, 50)          # nearest is 0.04 but 0.11 away
        self.assertFalse(ok)
        chosen, ok = ma.match_anchor(points, 0.035, 50, "not_exceeding")
        self.assertEqual(float(chosen.ffr), 0.02)
        chosen, ok = ma.match_anchor(points.iloc[1:], 0.01, 50, "not_exceeding")
        self.assertIsNone(chosen)
        self.assertFalse(ok)

    def test_labels(self):
        self.assertEqual(ma.run_label_from_differences([-1.0, -2.0, 0.0]), "earlier at matched burden")
        self.assertEqual(ma.run_label_from_differences([1.0, 1.0, math.inf]), "later at matched burden")
        self.assertEqual(ma.run_label_from_differences([1.0, -1.0]), "mixed")
        self.assertEqual(ma.run_label_from_differences([0.0, 0.0]), "equal")
        self.assertEqual(ma.pareto(.1, 2, .2, 3), "arm dominates")
        self.assertEqual(ma.pareto(.3, 2, .2, 3), "trade-off")


class SupportDistance(unittest.TestCase):
    def test_phase_distance_matches_brute_force(self):
        rng = np.random.default_rng(2)
        ref, query = rng.normal(size=(300, 4)), rng.normal(size=(50, 4))
        ref_phase, query_phase = rng.integers(0, 3, 300), rng.integers(0, 3, 50)
        d = ma.phase_distance(ref, ref_phase, query, query_phase)
        for i in range(50):
            same = ref[ref_phase == query_phase[i]]
            self.assertAlmostEqual(d[i], np.min(np.linalg.norm(same - query[i], axis=1)))

    def test_outside_range_and_standardize(self):
        ref = np.array([[0.0, 0.0], [1.0, 1.0]])
        (z_ref, z_q), scale = ma.standardize(ref, np.array([[0.5, 0.5], [2.0, 0.5]]))
        self.assertTrue(np.allclose(z_ref.mean(axis=0), 0))
        outside = ma.outside_range(z_ref, np.array([0, 0]), z_q, np.array([0, 0]))
        self.assertEqual(outside.tolist(), [False, True])

    def test_association_is_rank_based_on_cells(self):
        self.assertAlmostEqual(ma.spearman([1, 2, 3, 4], [10, 20, 30, 45]), 1.0)
        self.assertTrue(math.isnan(ma.spearman([1, 1, 1], [1, 2, 3])))


class PhaseVersusPastOnlyRegime(unittest.TestCase):
    def flight(self, tail):
        return np.r_[np.linspace(0, 30000, 600), np.full(1200, 30000.0), tail]

    def test_past_only_regime_ignores_future_and_phase_does_not(self):
        early = self.flight(np.linspace(30000, 0, 600))
        late = self.flight(np.r_[np.full(300, 30000.0), np.linspace(30000, 0, 300)])
        units, cycles = np.ones(1800 + 600, dtype=np.int16), np.ones(1800 + 600, dtype=np.int16)
        r1 = mm.causal_regime(early, units, cycles)
        r2 = mm.causal_regime(late, units, cycles)
        self.assertTrue(np.array_equal(r1[:1800], r2[:1800]))   # identical past -> identical labels
        p1, _, _ = phase_labels(early, units, cycles)
        p2, _, _ = phase_labels(late, units, cycles)
        self.assertFalse(np.array_equal(p1[:1800], p2[:1800]) and np.array_equal(p1, p2))
        self.assertFalse(np.array_equal(p1, p2))                # retrospective labels use the future


class LeakageAndProvenance(unittest.TestCase):
    def test_no_abnormal_loader_or_selector(self):
        source = inspect.getsource(ma)
        self.assertNotIn("load_abnormal_audit", source)
        self.assertNotIn("stage_e(", source)
        self.assertIn("mm.healthy_selector(a)", inspect.getsource(ma.load_healthy_operating))
        with self.assertRaises(mm.GateError):
            ma.assert_healthy_only(pd.DataFrame({"healthy": np.array([1, 0], dtype=np.int8)}))

    def test_baseline_uses_operating_descriptors_only(self):
        source = inspect.getsource(ma.part_d)
        self.assertIn("quadratic_surface", source)
        self.assertNotIn("phase_primary.to_numpy()[", source.split("fit_quantile_threshold")[0][-400:])
        self.assertEqual(ma.quadratic_surface(np.zeros((5, 4))).shape, (5, 14))

    def test_plan_frozen_and_manifest_intact(self):
        self.assertEqual(ma.verify_plan(), ma.PLAN_SHA256)
        self.assertTrue(mm.verify_manifest()["ok"])

    def test_output_guard_protects_frozen_paths(self):
        for path in (ROOT / "results/mssp_mitigation/x", ROOT / "results/confirmation_ds03/x", ROOT / "paper/ress/x",
                     ROOT / "results/final_validation/x", ROOT / "docs/mssp/x"):
            with self.assertRaises(PermissionError):
                ma.guard_adversarial_output(path)
        self.assertEqual(ma.guard_adversarial_output(ROOT / "results/mssp_adversarial/x"),
                         (ROOT / "results/mssp_adversarial/x").resolve())

    def test_outside_range_skips_phases_without_rows(self):
        ref, q = np.array([[0.0], [1.0]]), np.array([[2.0]])
        self.assertEqual(ma.outside_range(ref, np.array([0, 0]), q, np.array([0])).tolist(), [True])
        self.assertEqual(ma.outside_range(ref, np.array([0, 0]), q, np.array([1])).tolist(), [True])


@unittest.skipUnless((RESULTS / "ds02/run_record_ABC.json").exists(), "adversarial outputs not present")
class CommittedOutputs(unittest.TestCase):
    """Re-derive committed outputs from committed inputs; verify recorded exactness checks."""

    def test_run_records_report_exact_reproduction(self):
        for dataset in ("ds02", "ds03"):
            record = json.loads((RESULTS / dataset / "run_record_ABC.json").read_text())
            self.assertFalse(record["abnormal_rows_read"])
            self.assertTrue(record["stage_d_count_reproduction"]["exact"])
            self.assertEqual(record["parts"]["A"]["details"]["extended_u1_self_check_max_abs_diff"], 0.0)
            self.assertTrue(record["parts"]["B"]["details"]["trajectory_reproduction"]["exact"])
            self.assertTrue(record["manifest_after"]["ok"])
            self.assertEqual(record["plan_sha256"], ma.PLAN_SHA256)

    def test_baseline_records_healthy_side_only(self):
        for dataset in ("ds02", "ds03"):
            record = json.loads((RESULTS / dataset / "run_record_D.json").read_text())
            self.assertFalse(record["abnormal_rows_read"])
            self.assertIn("not evaluated", record["parts"]["D"]["details"]["abnormal_endpoints"])
            fits = pd.read_csv(RESULTS / dataset / "contextual_baseline/baseline_fits.csv")
            self.assertEqual(len(fits), 21)
            self.assertTrue(np.all(np.abs(fits.calibration_row_alarm_rate - fits.nominal_fpr) < 0.001))

    def test_manuscript_numbers_and_terminology(self):
        import subprocess
        result = subprocess.run([sys.executable, str(ROOT / "paper/mssp/verify_draft_numbers.py")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])

    def test_part_a_derivation_is_deterministic(self):
        for dataset in ("ds02", "ds03"):
            rates = ma.read_frozen_csv(dataset, "d", "healthy_phase_fpr_by_scheme")
            again = ma.calibration_quality_table(rates)
            committed = pd.read_csv(RESULTS / dataset / "calibration_quality/calibration_quality_metrics.csv",
                                    float_precision="round_trip")
            self.assertEqual(len(again), len(committed))
            for column in ("spread", "max_abs_error", "rms_error", "mean_abs_error", "overall_abs_error"):
                self.assertTrue(np.array_equal(again[column].to_numpy(), committed[column].to_numpy()), column)

    def test_part_b_operating_points_rederive(self):
        dataset = "ds02"
        fractions = pd.read_csv(RESULTS / dataset / "matched_delay/calibration_flight_fractions.csv",
                                float_precision="round_trip")
        traj = ma.read_frozen_csv(dataset, "e", "flight_alarm_fraction_trajectories")
        points = pd.read_csv(RESULTS / dataset / "matched_delay/operating_points.csv", float_precision="round_trip")
        key = ("isolation_forest", 1, 0.01, "phase_conditioned")
        cal = fractions[(fractions.detector == key[0]) & (fractions.seed == key[1]) & (fractions.nominal_fpr == key[2])
                        & (fractions.scheme == key[3])].alarm_fraction.to_numpy()
        part = traj[(traj.detector == key[0]) & (traj.seed == key[1]) & (traj.nominal_fpr == key[2]) & (traj.scheme == key[3])]
        kappas, sources = ma.candidate_kappas(cal)
        again = ma.distinct_points(ma.operating_characteristic(part, kappas, sources, [11, 14, 15]), [11, 14, 15])
        committed = points[(points.detector == key[0]) & (points.seed == key[1]) & (points.nominal_fpr == key[2])
                           & (points.scheme == key[3])].reset_index(drop=True)
        self.assertEqual(len(again), len(committed))
        for column in ("ffr", "median_delay"):
            self.assertTrue(
                np.array_equal(
                    again[column].to_numpy(),
                    committed[column].to_numpy()
                ),
                column
            )

        for column in ("kappa_low", "kappa_high"):
            np.testing.assert_allclose(
                again[column].to_numpy(dtype=np.float64),
                committed[column].to_numpy(dtype=np.float64),
                rtol=0.0,
                atol=1e-15,
                err_msg=column,
            )


if __name__ == "__main__":
    unittest.main()
