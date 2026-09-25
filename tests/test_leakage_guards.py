"""Lightweight static guards; no HDF5 or model training is performed."""

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / "src" / name).read_text(encoding="utf-8")


def block(name, function):
    tree = ast.parse(source(name))
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef)
                and item.name == function)
    return ast.get_source_segment(source(name), node)


def config_list(name, key):
    text = (ROOT / "configs" / name).read_text(encoding="utf-8")
    match = re.search(rf"^{key}: \[([^]]*)\]$", text, re.M)
    if match is None:
        raise AssertionError(f"Missing config key: {key}")
    return {int(item.strip()) for item in match.group(1).split(",")}


class LeakageGuards(unittest.TestCase):
    def test_engine_sets_disjoint(self):
        for config in ("ds02_discovery.yaml", "ds03_confirmation.yaml"):
            train = config_list(config, "train_engines" if config.startswith("ds02")
                                else "model_fit_engines")
            cal = config_list(config, "calibration_engines" if config.startswith("ds02")
                              else "threshold_calibration_engines")
            test = config_list(config, "official_audit_engines" if config.startswith("ds02")
                               else "official_test_engines")
            self.assertFalse(train & cal or train & test or cal & test)
            fit = config_list(config, "epoch_selection_fit_engines")
            match = re.search(r"^epoch_selection_validation_engine: (\d+)$",
                              (ROOT / "configs" / config).read_text(encoding="utf-8"), re.M)
            self.assertIsNotNone(match)
            val = int(match.group(1))
            self.assertTrue(fit <= train)
            self.assertIn(val, train)
            self.assertNotIn(val, fit | cal | test)

    def test_scaler_regression_fit_uses_only_fit_engines(self):
        ds02 = block("final_validation.py", "main")
        ds03 = block("confirm_frozen_ds03.py", "main")
        self.assertIn("dev_meta.unit.isin(TRAIN_UNITS)", ds02)
        self.assertIn("dev_x[train_mask], dev_desc[train_mask]", ds02)
        self.assertIn("dev_meta.unit.isin(plan[\"model_fit_units\"])", ds03)
        self.assertIn("dev_x[fit_mask], dev_descriptors[fit_mask]", ds03)
        regressor = source("phase3_dynamic.py")
        self.assertIn("self.scaler.fit(view)", regressor)
        self.assertIn("self.regression.fit(descriptors, x)", regressor)

    def test_epoch_selection_excludes_calibration(self):
        ds02 = block("final_validation.py", "train_converged_lstm")
        ds03 = block("confirm_frozen_ds03.py", "select_lstm_epochs")
        self.assertIn("SELECTION_FIT_UNITS", ds02)
        self.assertIn("SELECTION_VALIDATION_UNIT", ds02)
        self.assertNotIn("CAL_UNITS", ds02)
        self.assertNotIn("threshold_calibration_units", ds03)
        main = block("confirm_frozen_ds03.py", "main")
        self.assertLess(main.index("select_lstm_epochs("), main.index("calibration_thresholds("))

    def test_official_test_materialization_after_marker(self):
        main = block("confirm_frozen_ds03.py", "main")
        self.assertLess(main.index('ATTEMPT.open("x"'),
                        main.index('load_primary_split(h5, "test")'))
        self.assertLess(main.index("calibration_lock.json"), main.index('ATTEMPT.open("x"'))
        preflight = block("confirm_frozen_ds03.py", "preflight")
        self.assertNotIn("[:]", preflight)
        self.assertNotIn("load_primary_split", preflight)

    def test_labels_not_detector_inputs(self):
        ds02 = block("second_stage_audit.py", "load_split")
        ds03 = block("confirm_frozen_ds03.py", "load_primary_split")
        for code in (ds02, ds03):
            self.assertIn('h5[f"X_s_{split}"][:]', code)
            self.assertIn('"healthy"', code)
            self.assertIn('"phase_primary"', code)
        self.assertIn("return x[healthy], w[healthy], meta[healthy]", ds03)
        self.assertIn("dev_x[fit_mask], dev_descriptors[fit_mask]",
                      block("confirm_frozen_ds03.py", "main"))
        self.assertNotIn("meta[[\"phase_primary\"", block("confirm_frozen_ds03.py", "main"))
        self.assertNotIn("meta[[\"healthy\"", block("confirm_frozen_ds03.py", "main"))


if __name__ == "__main__":
    unittest.main()
