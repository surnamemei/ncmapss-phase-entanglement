# Observed execution environment

The configured research interpreter was queried without loading the N-CMAPSS datasets or running training. On 2026-09-25 it reported Python 3.12.3, PyTorch 2.14.0+cu130, CUDA runtime 13.0, NVIDIA GeForce RTX 5090, scikit-learn 1.9.1, NumPy 2.5.3, pandas 3.0.6, SciPy 1.18.1, h5py 3.16.0, and Matplotlib 3.11.2. `torch.cuda.is_available()` was true. Package versions are pinned in `requirements-lock.txt`.

The CUDA-enabled PyTorch wheel must be selected for the host platform; the lock records the observed package build, not a cross-platform installation guarantee. Run the configured CUDA check before any authorized long GPU run. If CUDA is unavailable, stop; CPU fallback is not part of the validated protocol.

Reproducibility limits: the YAML files are audited snapshots of experimental constants, not a new parser wired into the validated scientific algorithms. This avoids altering the frozen protocol. Historical JSON/Markdown provenance may retain local absolute paths from the original machine; runtime dataset and output paths now accept environment overrides or guarded CLI arguments. Static leakage tests check source structure and split invariants, but they are not a substitute for a new full scientific reproduction. This cleanup intentionally performed no such reproduction.
