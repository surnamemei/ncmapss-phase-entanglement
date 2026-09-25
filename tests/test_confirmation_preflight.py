"""Synthetic checks for the one-shot DS03 audit assembly (no dataset reads)."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from confirm_frozen_ds03 import (
    calibration_thresholds,
    canonical_table,
    primary_phase,
    transfer_with_locked_thresholds,
)
from final_validation import flight_metrics, row_metrics


class ConfirmationPreflightTest(unittest.TestCase):
    def test_primary_phase_and_locked_metric_assembly(self):
        altitude = np.array([0, 50, 100, 100, 50, 0] * 2)
        units = np.array([10] * 6 + [11] * 6)
        cycles = np.ones(12, dtype=int)
        phase = primary_phase(altitude, units, cycles)
        np.testing.assert_array_equal(phase, [0, 0, 1, 1, 2, 2] * 2)
        meta = pd.DataFrame({
            "unit": units,
            "cycle": cycles,
            "flight_class": [1] * 12,
            "phase_primary": phase,
        })
        scores = np.array([.1, .2, .3, .4, .5, .6, .2, .3, .4, .5, .6, .7])
        calibration = calibration_thresholds(scores, meta)
        target = .01
        locked = calibration[str(target)]
        rates = pd.DataFrame(row_metrics(
            scores, meta, locked["pooled"], "pca", -1, "primary", target
        ))
        transfers = pd.DataFrame(transfer_with_locked_thresholds(
            scores, meta, "pca", -1, target, locked
        ))
        _, summary = flight_metrics(
            scores, meta, locked["pooled"], "pca", -1, "primary", target
        )
        canonical = canonical_table(rates, transfers, pd.DataFrame(summary))
        self.assertEqual(len(canonical), 3)
        self.assertEqual(set(canonical.evaluation_unit),
                         {"engine_10", "engine_11", "pooled"})
        self.assertTrue(np.isfinite(canonical.select_dtypes(include="number")).all().all())


if __name__ == "__main__":
    unittest.main()
