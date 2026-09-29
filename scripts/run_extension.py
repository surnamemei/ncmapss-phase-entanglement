"""Guarded command-line entry point for the extension (GENERALIZATION_PROTOCOL.md section 10).

Stages:
- lock <subset>: Phase L, the calibration-only lock of a new subset (no official-test array is read);
- reference <DS02|DS03>: post-confirmation reference work and audit-code shakedown;
- audit <subset>: Phase A, the one-shot official audit. It needs a committed lock.
  `--reproduction-only` recomputes into a new directory after the audit has run;
- summary: cross-dataset summaries and hypothesis decisions (after all audits).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import ext_common as ec  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage", choices=("lock", "reference", "audit", "summary"))
    parser.add_argument("subset", nargs="?")
    parser.add_argument("--reproduction-only", action="store_true")
    args = parser.parse_args()
    command = " ".join(["python scripts/run_extension.py", args.stage] + ([args.subset] if args.subset else [])
                       + (["--reproduction-only"] if args.reproduction_only else []))

    def log(message):
        print(f"[{ec.now_utc()}] {message}", flush=True)

    if args.stage == "summary":
        import ext_summary
        ext_summary.main(log=log)
        return 0
    import ext_pipeline as xp
    if args.stage == "lock":
        if args.subset not in ec.NEW_ORDER:
            parser.error(f"lock needs one of {ec.NEW_ORDER}")
        xp.phase_lock(args.subset, log=log, command=command)
    elif args.stage == "reference":
        if args.subset not in ec.REFERENCE_ORDER:
            parser.error(f"reference needs one of {ec.REFERENCE_ORDER}")
        xp.reference_work(args.subset, log=log, command=command)
    elif args.stage == "audit":
        if args.subset not in ec.NEW_ORDER:
            parser.error(f"audit needs one of {ec.NEW_ORDER}")
        position = ec.NEW_ORDER.index(args.subset)
        for earlier in ec.NEW_ORDER[:position]:  # frozen audit order
            if not (ec.RESULTS / earlier / "audit" / "official_test_opened.json").exists():
                raise ec.ExtensionError(f"Frozen audit order: {earlier} must be audited before {args.subset}")
        for subset in ec.NEW_ORDER:  # every lock must exist before any audit
            if not (ec.RESULTS / subset / "lock" / "lock_record.json").exists():
                raise ec.ExtensionError(f"All new-cohort locks must exist before any audit ({subset} missing)")
        xp.phase_audit(args.subset, reproduction_only=args.reproduction_only, log=log, command=command)
    return 0


if __name__ == "__main__":
    sys.exit(main())
