"""Guarded entry point for the final focused validation (docs/extension/FOCUSED_VALIDATION_PLAN.md, FROZEN v1.0).

Stages:
- subset <key>: components 1-3 for one new subset (healthy official-test rows only; reproduction only);
- summary: engine and family summaries, bootstrap width comparison, U-EXT2 recomputation and the
  pre-declared interpretation (after all seven subsets);
- all: every subset in the frozen order, then the summary.

This is post hoc and final: it changes no pre-specified decision, and nothing runs after it.
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
    parser.add_argument("stage", choices=("subset", "summary", "all"))
    parser.add_argument("subset", nargs="?")
    args = parser.parse_args()

    def log(message):
        print(f"[{ec.now_utc()}] {message}", flush=True)

    import ext_focused_validation as fvx
    if args.stage == "subset":
        if args.subset not in ec.NEW_ORDER:
            parser.error(f"subset needs one of {ec.NEW_ORDER}")
        fvx.run_subset(args.subset, log=log,
                       command=f"python scripts/run_focused_validation.py subset {args.subset}")
    elif args.stage == "summary":
        fvx.summarize(log=log)
    else:
        for key in ec.NEW_ORDER:
            fvx.run_subset(key, log=log, command="python scripts/run_focused_validation.py all")
        fvx.summarize(log=log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
