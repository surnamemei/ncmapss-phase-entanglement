"""Data-free tests of the CVAE baseline (CVAE_SPECIFICATION.md): synthetic behaviour, leakage, determinism."""

from __future__ import annotations

import ast
import inspect
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def synthetic(n_flights=40, rows=400, seed=0):
    from phase3_dynamic import causal_descriptors
    rng = np.random.default_rng(seed)
    ws, units, cycles = [], [], []
    for f in range(n_flights):
        t = np.linspace(0, 1, rows)
        alt = 30000 * np.clip(np.minimum(t / 0.2, (1 - t) / 0.25), 0, 1) + rng.normal(0, 20, rows)
        ws.append(np.column_stack([alt, 0.3 + alt / 60000, 60 + 10 * np.sin(5 * t), 520 - alt / 300]))
        units.append(np.full(rows, 1 + f // 10))
        cycles.append(np.full(rows, 1 + f % 10))
    w = np.vstack(ws)
    meta = pd.DataFrame({"unit": np.concatenate(units).astype(np.int16), "cycle": np.concatenate(cycles).astype(np.int16)})
    z = (w - w.mean(0)) / w.std(0)
    a = rng.normal(size=(4, 14))
    sd = 0.02 + 0.1 * (z[:, :1] > 0.5)
    x = np.tanh(z @ a) + sd * rng.normal(size=(len(w), 14))
    c, names = causal_descriptors(w, meta)
    return x, c, meta, names


class CVAE(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        if not torch.cuda.is_available():
            raise unittest.SkipTest("CUDA required (CPU fallback is disabled)")
        import ext_cvae
        cls.cv = ext_cvae
        cls.x, cls.c, cls.meta, cls.names = synthetic()
        fit = cls.meta.unit.to_numpy() <= 3
        cls.saved = ext_cvae.MAX_EPOCHS
        ext_cvae.MAX_EPOCHS = 25
        cls.selected, cls.history = ext_cvae.select_epochs(0, cls.x[fit], cls.c[fit], cls.x[~fit], cls.c[~fit],
                                                           log=lambda m: None)
        cls.fitted, _ = ext_cvae.refit(0, 20, cls.x[fit], cls.c[fit], log=lambda m: None)
        ext_cvae.MAX_EPOCHS = cls.saved

    def test_condition_is_the_32_causal_descriptors(self):
        self.assertEqual(self.c.shape[1], 32)
        self.assertEqual(self.names[:4], ["alt", "Mach", "TRA", "T2"])
        import ext_models as xm
        source = inspect.getsource(xm)
        self.assertIn("causal_descriptors(w, meta)", source)
        for call in ("ext_cvae.select_epochs(", "ext_cvae.refit("):
            self.assertIn(call, source)
        fit_source = inspect.getsource(xm.fit_models)
        self.assertIn("dev.descriptors[sel_mask]", fit_source)
        self.assertIn("dev.descriptors[val_mask]", fit_source)

    def test_no_labels_or_phases_as_inputs(self):
        params = list(inspect.signature(self.cv.score).parameters)
        self.assertEqual(params[:3], ["fitted", "x", "c"])
        for fn in (self.cv.select_epochs, self.cv.refit, self.cv.score):
            source = inspect.getsource(fn)
            for forbidden in ("phase", "healthy", "hs", "flight_class", "unit", "Fc"):
                self.assertNotRegex(source, rf"\b{forbidden}\b")

    def test_scores_deterministic_and_row_independent(self):
        s1 = self.cv.score(self.fitted, self.x, self.c)
        s2 = self.cv.score(self.fitted, self.x, self.c)
        np.testing.assert_array_equal(s1, s2)
        subset = self.cv.score(self.fitted, self.x[1000:1500], self.c[1000:1500])
        np.testing.assert_allclose(subset, s1[1000:1500], rtol=1e-5, atol=1e-5)

    def test_training_is_deterministic(self):
        fit = self.meta.unit.to_numpy() <= 3
        again, _ = self.cv.refit(0, 20, self.x[fit], self.c[fit], log=lambda m: None)
        for k, v in self.fitted["model"].state_dict().items():
            np.testing.assert_array_equal(v.cpu().numpy(), again["model"].state_dict()[k].cpu().numpy())

    def test_detects_synthetic_shift_and_variance_bounds(self):
        import torch
        rng = np.random.default_rng(3)
        normal = self.cv.score(self.fitted, self.x[-2000:], self.c[-2000:])
        shifted = self.x[-2000:] + rng.choice([-1, 1], size=(2000, 14)) * 0.3
        anomalous = self.cv.score(self.fitted, shifted, self.c[-2000:])
        auc = (anomalous[:, None] > normal[None, :]).mean()
        self.assertGreater(auc, 0.9)
        with torch.no_grad():
            z = torch.randn(64, self.cv.LATENT, device=self.cv.DEVICE) * 50
            c = torch.randn(64, 32, device=self.cv.DEVICE) * 50
            _, logvar = self.fitted["model"].decode(z, c)
        self.assertTrue(bool((logvar >= self.cv.MIN_LOGVAR - 1e-5).all() and (logvar <= self.cv.MAX_LOGVAR + 1e-5).all()))

    def test_amendment_2_numerical_safeguards(self):
        import torch
        self.assertEqual(self.cv.GRAD_CLIP, 1.0)
        self.assertIn("clip_grad_norm_(model.parameters(), GRAD_CLIP)", inspect.getsource(self.cv.train_epoch))
        with torch.no_grad():
            x = torch.randn(64, 14, device=self.cv.DEVICE) * 1e3
            c = torch.randn(64, 32, device=self.cv.DEVICE) * 1e3
            _, logvar_z = self.fitted["model"].encode(x, c)
        self.assertTrue(bool((logvar_z >= self.cv.ENC_MIN_LOGVAR - 1e-5).all()
                             and (logvar_z <= self.cv.ENC_MAX_LOGVAR + 1e-5).all()))

    def test_selection_history_and_epoch_rule(self):
        self.assertEqual(self.selected, int(np.argmin([h["validation_loss"] for h in self.history]) + 1))
        self.assertEqual((self.cv.PATIENCE, self.cv.MIN_DELTA), (6, 1e-4))
        self.assertEqual(self.saved, 600)

    def test_fit_models_uses_only_fit_pool_rows(self):
        import ext_models as xm
        tree = ast.parse(inspect.getsource(xm.fit_models))
        text = ast.unparse(tree)
        self.assertIn("subset.selection_fit", text)
        self.assertIn("subset.validation", text)
        self.assertIn("calibration engine in", text)
        self.assertIn("audit engine in model fitting", text)


class LSTMLoopEqualsFrozen(unittest.TestCase):
    """The re-implemented epoch selection and refit equal the frozen loops (writers redirected to a temp dir)."""

    @classmethod
    def setUpClass(cls):
        import torch
        if not torch.cuda.is_available():
            raise unittest.SkipTest("CUDA required")

    def test_equal_to_frozen_loop(self):
        import tempfile
        import confirm_frozen_ds03 as cf
        import ext_models as xm
        import torch
        from phase3_dynamic import causal_descriptors
        x, _, meta, _ = synthetic(n_flights=16, rows=520, seed=5)
        rng = np.random.default_rng(0)
        w = np.column_stack([rng.normal(size=len(x)).cumsum() for _ in range(4)])
        desc, _ = causal_descriptors(w, meta)
        x = x * 10 + 100
        saved = (cf.CHECKPOINTS, cf.MAX_EPOCHS, cf.SEEDS)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            try:
                cf.CHECKPOINTS, cf.MAX_EPOCHS, cf.SEEDS = Path(a), 3, (0,)
                frozen_rows, frozen_sel = cf.select_lstm_epochs(x, desc, meta, [1], 2)
                ours_rows, ours_sel = xm.select_lstm_epochs(x, desc, meta, [1], 2, b, seeds=(0,), max_epochs=3,
                                                            log=lambda m: None)
                self.assertEqual(frozen_sel, ours_sel)
                self.assertEqual([r["validation_loss"] for r in frozen_rows], [r["validation_loss"] for r in ours_rows])
                z = np.asarray(rng.normal(size=(len(x), 14)), dtype=np.float32)
                m1, _ = cf.refit_lstm(0, 2, z, meta)
                m2, _ = xm.refit_lstm(0, 2, z, meta, b, log=lambda m: None)
                for k, v in m1.state_dict().items():
                    self.assertTrue(torch.equal(v, m2.state_dict()[k]))
            finally:
                cf.CHECKPOINTS, cf.MAX_EPOCHS, cf.SEEDS = saved


if __name__ == "__main__":
    unittest.main()
