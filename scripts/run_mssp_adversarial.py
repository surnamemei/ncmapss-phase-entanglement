"""Guarded entry point for the MSSP adversarial validation (post-confirmation).

Implements docs/mssp/adversarial_validation_plan.md. The default is a dry run: nothing is
read, loaded, or written. With --execute, the chosen parts run per dataset on healthy rows
only (plus committed Stage E tables); no hs = 0 row is read. --summarize builds the
cross-dataset robustness, denominator, and verdict tables from existing part outputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PART_ORDER = ("A", "B", "C", "D")


def parse_parts(text):
    parts = []
    for piece in (p.strip().upper() for p in text.split(",") if p.strip()):
        if piece not in PART_ORDER:
            raise argparse.ArgumentTypeError(f"Unknown part: {piece}")
        if piece not in parts:
            parts.append(piece)
    return sorted(parts, key=PART_ORDER.index)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts", type=parse_parts, help="Comma-separated parts from A,B,C,D")
    parser.add_argument("--dataset", choices=("ds02", "ds03", "both"), default="both")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results/mssp_adversarial")
    parser.add_argument("--summarize", action="store_true")
    parser.add_argument("--decomposition", action="store_true",
                        help="Post-plan descriptive error decomposition (deviation Dev-1); committed tables only")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.parts and not args.summarize and not args.decomposition:
        parser.error("--parts, --summarize, or --decomposition is required")

    sys.path.insert(0, str(ROOT / "src"))
    import mssp_adversarial as ma
    import mssp_mitigation as mm

    print(f"Interpreter: {sys.executable}")
    print(f"Plan: {mm.rel(ma.PLAN)} (sha256 {ma.verify_plan()})")
    datasets = ("ds02", "ds03") if args.dataset == "both" else (args.dataset,)
    output_root = mm.guard_output(args.output_root)
    print(f"Output root: {mm.rel(output_root)}; parts: {args.parts}; datasets: {datasets}")
    if not args.execute:
        print("DRY RUN: nothing read, loaded, or written")
        return
    for key in datasets if args.parts else ():
        print(f"=== Parts {','.join(args.parts)}: {key} ===", flush=True)
        record = ma.run_dataset(mm.DATASETS[key], args.parts, output_root)
        print(json.dumps({part: value["details"] for part, value in record["parts"].items()},
                         indent=1, default=str)[:4000])
    if args.summarize:
        record = ma.summarize(output_root, datasets)
        print(json.dumps({k: record[k] for k in ("support_verdict", "support_summary", "d_decision")},
                         indent=1, default=str))
    if args.decomposition:
        table, digest = ma.write_decomposition(output_root, datasets)
        mm.write_json(output_root / "summary" / "post_plan_error_decomposition_record.json", {
            "deviation": "Dev-1 post-plan descriptive decomposition (see docs/mssp/FINAL_ADVERSARIAL_REVIEW.md)",
            "inputs": "results/mssp_mitigation/{ds02,ds03}/stage_d/healthy_phase_fpr_by_scheme.csv (committed)",
            "output_sha256": digest, "rows": int(len(table)), "finished_utc": mm.now_utc(),
            "provenance": ma.module_record()})
        print(f"Decomposition written ({len(table)} rows, sha256 {digest[:12]})")


if __name__ == "__main__":
    main()
