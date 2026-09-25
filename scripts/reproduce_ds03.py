"""Guarded entry point for the unchanged, one-shot DS03 confirmation code."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "results/final_validation/frozen_protocol.md"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(os.environ.get(
        "NCMAPSS_DS03_H5", ROOT / "N-CMAPSS/N-CMAPSS_DS03-012.h5")))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(f"Interpreter: {sys.executable}")
    print(f"Protocol: {PROTOCOL}")
    print(f"Dataset: {args.data.resolve()}")
    print("Existing validated code: src/confirm_frozen_ds03.py")
    if not args.execute:
        print("DRY RUN: no HDF5 content read, official-test access, or output written")
        return
    if args.output_dir is None:
        parser.error("--execute requires --output-dir pointing to a new directory")
    output = args.output_dir.resolve()
    if output.exists():
        parser.error(f"Refusing to overwrite output or one-shot marker: {output}")
    if not args.data.is_file() or not PROTOCOL.is_file():
        parser.error("Dataset or frozen protocol not found")
    env = os.environ.copy()
    env["NCMAPSS_DS03_H5"] = str(args.data.resolve())
    env["NCMAPSS_DS03_RESULTS_DIR"] = str(output)
    subprocess.run([sys.executable, str(ROOT / "src/confirm_frozen_ds03.py")],
                   check=True, env=env, cwd=ROOT)


if __name__ == "__main__":
    main()
