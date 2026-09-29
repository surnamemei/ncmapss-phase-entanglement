"""Condition-aware representation baseline for the extension: one pre-specified conditional VAE.

Specification: docs/extension/CVAE_SPECIFICATION.md (frozen before any real training).

Inputs:
- x: the 14 measured ``X_s`` channels, standardized with the mean and SD of the model's own
  training rows;
- c: the 32 finite-history operating descriptors of the frozen residual pipeline
  (``phase3_dynamic.causal_descriptors``: ``W`` and its past-only derivatives, window means, SDs
  and slopes, all reset at flight boundaries), standardized the same way.

Phase labels, health labels, flight class and engine identity are never inputs.

Model:
- encoder q(z | x, c) and decoder p(x | z, c), each two fully connected hidden layers (128, ReLU);
- latent dimension 4 with a standard normal prior;
- heteroscedastic Gaussian decoder, with the log-variance softly bounded to [log 1e-4, log 1e2].

Anomaly score: the conditional Gaussian negative log-likelihood of x at the posterior-mean latent
code, s(x, c) = -log N(x; mu_theta(mu_phi(x, c), c), diag sigma^2_theta(mu_phi(x, c), c)). This is a
deterministic single-point form of the reconstruction probability, and it does not depend on other
rows in the batch.
"""

from __future__ import annotations

import math
import os
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")  # required for deterministic cuBLAS (as final_validation)

import numpy as np
import torch
from torch import nn

DEVICE = torch.device("cuda")
HIDDEN = 128
LATENT = 4
MIN_LOGVAR = math.log(1e-4)
MAX_LOGVAR = math.log(1e2)
ENC_MIN_LOGVAR = math.log(1e-8)  # Amendment 2: numerical safeguard against exp overflow
ENC_MAX_LOGVAR = math.log(1e2)
GRAD_CLIP = 1.0  # Amendment 2: global gradient-norm clip before every Adam step
BATCH = 4096
LEARNING_RATE = 1e-3
MAX_EPOCHS = 600  # frozen LSTM epoch-selection rule (final_validation)
PATIENCE = 6
MIN_DELTA = 1e-4
SCORE_BATCH = 65536
LOG_2PI = math.log(2.0 * math.pi)


class ConditionalVAE(nn.Module):
    def __init__(self, n_x, n_c, hidden=HIDDEN, latent=LATENT):
        super().__init__()
        self.n_x, self.n_c, self.latent = n_x, n_c, latent
        self.encoder = nn.Sequential(
            nn.Linear(n_x + n_c, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 2 * latent))
        self.decoder = nn.Sequential(
            nn.Linear(latent + n_c, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 2 * n_x))

    def encode(self, x, c):
        mu, raw = self.encoder(torch.cat([x, c], dim=1)).chunk(2, dim=1)
        return mu, soft_bound(raw, ENC_MIN_LOGVAR, ENC_MAX_LOGVAR)

    def decode(self, z, c):
        mu, raw = self.decoder(torch.cat([z, c], dim=1)).chunk(2, dim=1)
        return mu, soft_bound(raw, MIN_LOGVAR, MAX_LOGVAR)


def soft_bound(raw, low, high):
    """Smooth bounding of a log-variance to [low, high] (max - softplus(max - raw), then min + softplus(. - min))."""
    value = high - nn.functional.softplus(high - raw)
    return low + nn.functional.softplus(value - low)


def gaussian_nll(x, mu, logvar):
    """Per-row negative log-likelihood of a diagonal Gaussian (summed over channels)."""
    return 0.5 * (((x - mu) ** 2) * torch.exp(-logvar) + logvar + LOG_2PI).sum(dim=1)


def kl_standard_normal(mu, logvar):
    return 0.5 * (mu ** 2 + torch.exp(logvar) - 1.0 - logvar).sum(dim=1)


def build_cvae(seed, n_x, n_c):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    return ConditionalVAE(n_x, n_c).to(DEVICE)


class Standardizer:
    """Mean/SD standardization estimated on the model's own training rows only."""

    def __init__(self, values):
        values = np.asarray(values, dtype=np.float64)
        self.mean = values.mean(axis=0)
        self.std = values.std(axis=0)
        self.std[self.std == 0] = 1.0

    def __call__(self, values):
        return ((np.asarray(values, dtype=np.float64) - self.mean) / self.std).astype(np.float32)

    def state(self):
        return {"mean": self.mean.tolist(), "std": self.std.tolist()}

    @classmethod
    def from_state(cls, state):
        obj = cls.__new__(cls)
        obj.mean, obj.std = np.asarray(state["mean"]), np.asarray(state["std"])
        return obj


def train_epoch(model, optimizer, x, c, seed, epoch):
    """One pass over all training rows in a seeded order with one reparameterized sample per row."""
    model.train()
    order = torch.randperm(len(x), generator=torch.Generator().manual_seed(seed * 1_000_003 + epoch))
    noise = torch.Generator(device=DEVICE).manual_seed(seed * 1_000_003 + epoch)
    total, count = 0.0, 0
    for start in range(0, len(x), BATCH):
        index = order[start:start + BATCH].to(DEVICE)
        xb, cb = x[index], c[index]
        mu_z, logvar_z = model.encode(xb, cb)
        eps = torch.randn(mu_z.shape, generator=noise, device=DEVICE)
        z = mu_z + torch.exp(0.5 * logvar_z) * eps
        mu_x, logvar_x = model.decode(z, cb)
        loss_rows = gaussian_nll(xb, mu_x, logvar_x) + kl_standard_normal(mu_z, logvar_z)
        loss = loss_rows.mean()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
        optimizer.step()
        total += float(loss_rows.detach().sum())
        count += len(index)
    return total / count


@torch.no_grad()
def evaluation_loss(model, x, c):
    """Deterministic surrogate of the negative ELBO: NLL at the posterior mean plus the KL term."""
    model.eval()
    total, count = 0.0, 0
    for start in range(0, len(x), SCORE_BATCH):
        xb, cb = x[start:start + SCORE_BATCH], c[start:start + SCORE_BATCH]
        mu_z, logvar_z = model.encode(xb, cb)
        mu_x, logvar_x = model.decode(mu_z, cb)
        total += float((gaussian_nll(xb, mu_x, logvar_x) + kl_standard_normal(mu_z, logvar_z)).sum())
        count += len(xb)
    return total / count


def to_device(array):
    return torch.from_numpy(np.ascontiguousarray(array, dtype=np.float32)).to(DEVICE)


def select_epochs(seed, x_fit, c_fit, x_val, c_val, log=print):
    """Engine-disjoint epoch selection: train on selection-fit rows, monitor validation-engine rows."""
    x_std, c_std = Standardizer(x_fit), Standardizer(c_fit)
    xf, cf = to_device(x_std(x_fit)), to_device(c_std(c_fit))
    xv, cv = to_device(x_std(x_val)), to_device(c_std(c_val))
    model = build_cvae(seed, xf.shape[1], cf.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    history, best, wait = [], float("inf"), 0
    for epoch in range(1, MAX_EPOCHS + 1):
        clock = time.time()
        train_loss = train_epoch(model, optimizer, xf, cf, seed, epoch)
        val_loss = evaluation_loss(model, xv, cv)
        if not (math.isfinite(train_loss) and math.isfinite(val_loss)):
            raise FloatingPointError(f"Non-finite CVAE loss at seed {seed}, epoch {epoch}")
        history.append({"seed": seed, "stage": "engine_disjoint_epoch_selection", "epoch": epoch,
                        "train_loss": train_loss, "validation_loss": val_loss,
                        "seconds": round(time.time() - clock, 3)})
        if epoch == 1 or epoch % 20 == 0:
            log(f"cvae selection seed={seed} epoch={epoch} loss={train_loss:.5f} val={val_loss:.5f}")
        if val_loss < best - MIN_DELTA:
            best, wait = val_loss, 0
        else:
            wait += 1
            if wait >= PATIENCE:
                break
    losses = [h["validation_loss"] for h in history]
    selected = int(np.argmin(losses) + 1)
    for h in history:
        h.update({"best_epoch": selected, "epochs_run": len(history), "max_epochs": MAX_EPOCHS,
                  "patience": PATIENCE, "min_delta": MIN_DELTA})
    del model, optimizer, xf, cf, xv, cv
    torch.cuda.empty_cache()
    return selected, history


def refit(seed, epochs, x_fit, c_fit, log=print):
    """Refit on all fit-pool rows for the selected number of epochs (no validation data)."""
    x_std, c_std = Standardizer(x_fit), Standardizer(c_fit)
    xf, cf = to_device(x_std(x_fit)), to_device(c_std(c_fit))
    model = build_cvae(seed, xf.shape[1], cf.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    history = []
    for epoch in range(1, epochs + 1):
        clock = time.time()
        loss = train_epoch(model, optimizer, xf, cf, seed, epoch)
        if not math.isfinite(loss):
            raise FloatingPointError(f"Non-finite CVAE refit loss at seed {seed}, epoch {epoch}")
        history.append({"seed": seed, "stage": "all_fit_engines_refit", "epoch": epoch, "train_loss": loss,
                        "validation_loss": float("nan"), "seconds": round(time.time() - clock, 3),
                        "best_epoch": epochs, "epochs_run": epochs})
        if epoch == 1 or epoch % 20 == 0 or epoch == epochs:
            log(f"cvae refit seed={seed} epoch={epoch}/{epochs} loss={loss:.5f}")
    del optimizer, xf, cf
    torch.cuda.empty_cache()
    model.eval()
    return {"model": model, "x_std": x_std, "c_std": c_std, "seed": seed, "epochs": epochs}, history


@torch.no_grad()
def score(fitted, x, c, dtype=torch.float32):
    """Row-wise anomaly score (float64 output); independent of batch composition."""
    model = fitted["model"]
    model.eval()
    xs, cs = fitted["x_std"](x), fitted["c_std"](c)
    out = np.empty(len(xs), dtype=np.float64)
    for start in range(0, len(xs), SCORE_BATCH):
        xb = torch.from_numpy(xs[start:start + SCORE_BATCH]).to(DEVICE, dtype)
        cb = torch.from_numpy(cs[start:start + SCORE_BATCH]).to(DEVICE, dtype)
        m = model.to(dtype)
        mu_z, _ = m.encode(xb, cb)
        mu_x, logvar_x = m.decode(mu_z, cb)
        out[start:start + len(xb)] = gaussian_nll(xb, mu_x, logvar_x).double().cpu().numpy()
    model.to(torch.float32)
    return out


def state(fitted):
    return {"state_dict": {k: v.detach().cpu() for k, v in fitted["model"].state_dict().items()},
            "x_std": fitted["x_std"].state(), "c_std": fitted["c_std"].state(),
            "seed": fitted["seed"], "epochs": fitted["epochs"],
            "n_x": fitted["model"].n_x, "n_c": fitted["model"].n_c}


def load(payload):
    model = build_cvae(payload["seed"], payload["n_x"], payload["n_c"])
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return {"model": model, "x_std": Standardizer.from_state(payload["x_std"]),
            "c_std": Standardizer.from_state(payload["c_std"]), "seed": payload["seed"],
            "epochs": payload["epochs"]}
