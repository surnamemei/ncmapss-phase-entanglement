"""Lightweight worker for the Q-arm linear programs (no torch import in worker processes).

`fit_quantile_threshold` is a verbatim copy of the frozen `mssp_adversarial.fit_quantile_threshold`
(adversarial plan, Part D). A test asserts that the two function bodies are identical.
"""

import numpy as np

QR_STRIDE = 5


def fit_quantile_threshold(features, scores, quantile, stride=QR_STRIDE):
    from sklearn.linear_model import QuantileRegressor
    index = np.arange(0, len(scores), stride)
    model = QuantileRegressor(quantile=quantile, alpha=0.0, fit_intercept=True, solver="highs")
    model.fit(features[index], scores[index])
    return model, int(len(index))


def fit_job(args):
    features, scores, quantile = args
    model, n_fit = fit_quantile_threshold(features, scores, quantile, stride=QR_STRIDE)
    return float(model.intercept_), [float(c) for c in model.coef_], n_fit
