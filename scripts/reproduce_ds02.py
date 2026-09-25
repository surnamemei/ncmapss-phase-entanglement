"""Guarded entry point for the existing DS02 exploratory analyses.

Default is a read-only plan. An actual run requires --execute and a NEW output
root so canonical executed artifacts cannot be silently overwritten.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(os.environ.get(
        "NCMAPSS_DS02_H5", ROOT / "N-CMAPSS/N-CMAPSS_DS02-006.h5")))
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--include-correction-comparison", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(f"Interpreter: {sys.executable}")
    print(f"Dataset: {args.data.resolve()}")
    print("Existing validated code: src/final_validation.py")
    if args.include_correction_comparison:
        print("Also: src/phase3_dynamic.py (DS02 exploratory comparison)")
    if not args.execute:
        print("DRY RUN: no HDF5 content read, model fit, or output written")
        return
    if args.output_root is None:
        parser.error("--execute requires --output-root pointing to a new directory")
    output = args.output_root.resolve()
    if output.exists():
        parser.error(f"Refusing to overwrite existing output root: {output}")
    if not args.data.is_file():
        parser.error(f"Dataset not found: {args.data}")
    env = os.environ.copy()
    env["NCMAPSS_DS02_H5"] = str(args.data.resolve())
    env["NCMAPSS_DS02_RESULTS_DIR"] = str(output / "final_validation")
    env["NCMAPSS_DS02_CORRECTION_DIR"] = str(output / "phase3_dynamic_correction")
    env["NCMAPSS_DS02_FIGURES_DIR"] = str(output / "figures/phase3")
    if args.include_correction_comparison:
        subprocess.run([sys.executable, str(ROOT / "src/phase3_dynamic.py")],
                       check=True, env=env, cwd=ROOT)
    subprocess.run([sys.executable, str(ROOT / "src/final_validation.py")],
                   check=True, env=env, cwd=ROOT)


if __name__ == "__main__":
    main()
