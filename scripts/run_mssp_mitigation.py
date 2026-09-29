"""Guarded entry point for the MSSP post-confirmation mitigation analysis.

The default is a dry run: it reads no HDF5 content, loads no model, and writes no
output. Data-touching stages need --execute. Stage E (abnormal-state rows) also
needs --authorize-abnormal-open, which is given only on explicit author approval,
and a hash-verified calibration-only lock. See
docs/mssp/post_confirmation_mitigation_protocol.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE_ORDER = ("B", "C", "L", "D", "E", "F")
ALIASES = {"gate": ("B", "C")}


def parse_stages(text):
    stages = []
    for part in (piece.strip() for piece in text.split(",") if piece.strip()):
        for stage in ALIASES.get(part.lower(), (part.upper(),)):
            if stage not in STAGE_ORDER:
                raise argparse.ArgumentTypeError(f"Unknown stage: {part}")
            if stage not in stages:
                stages.append(stage)
    return sorted(stages, key=STAGE_ORDER.index)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=parse_stages,
                        help="Comma-separated stages from B,C,L,D,E,F; 'gate' means B,C")
    parser.add_argument("--dataset", choices=("ds02", "ds03", "both"), default="both")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results/mssp_mitigation")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--authorize-abnormal-open", action="store_true",
                        help="Stage E only; requires explicit author approval")
    parser.add_argument("--benchmark", action="store_true",
                        help="Time the U1/U2 bootstraps on synthetic arrays; reads no data")
    args = parser.parse_args()
    if not args.stage and not args.benchmark:
        parser.error("--stage or --benchmark is required")
    if args.stage and "E" in args.stage and not args.authorize_abnormal_open:
        parser.error("Stage E requires --authorize-abnormal-open (explicit author approval)")
    if args.authorize_abnormal_open and (not args.stage or "E" not in args.stage):
        parser.error("--authorize-abnormal-open is only valid with Stage E")

    sys.path.insert(0, str(ROOT / "src"))
    import mssp_mitigation as mm

    print(f"Interpreter: {sys.executable}")
    print(f"Protocol: {mm.rel(mm.PROTOCOL)} (sha256 {mm.file_digest(mm.PROTOCOL)})")
    if args.benchmark:
        print(json.dumps(mm.benchmark_u2(), indent=2))
        return
    datasets = ("ds02", "ds03") if args.dataset == "both" else (args.dataset,)
    output_root = mm.guard_output(args.output_root)
    print(f"Output root: {mm.rel(output_root)}")
    print(f"Stages: {','.join(args.stage)}; datasets: {','.join(datasets)}")
    if not args.execute:
        print("DRY RUN: no HDF5 content read, no model loaded, no output written")
        return
    before = mm.verify_manifest()
    if not before["ok"]:
        sys.exit(f"Baseline manifest failed before execution: {before}")
    for stage in args.stage:
        if stage == "F":
            mm.stage_f(output_root, datasets)
            continue
        for key in datasets:
            spec = mm.DATASETS[key]
            print(f"=== Stage {stage}: {key} ===", flush=True)
            if stage == "E":
                mm.stage_e(spec, output_root, authorize_abnormal_open=True)
            else:
                mm.STAGES[stage](spec, output_root)
    after = mm.verify_manifest()
    print(f"Baseline manifest after run: {'verified' if after['ok'] else 'FAILED'} "
          f"({after['entries']} files)")
    if not after["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
