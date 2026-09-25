"""Read-only consistency checks for the frozen presentation package."""

from __future__ import annotations

import csv
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class SubmissionPackageGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.core = rows(PAPER / "manuscript_core_results.csv")
        cls.ledger = {row["claim_id"]: row for row in rows(PAPER / "evidence_ledger.csv")}
        cls.clean = (PAPER / "manuscript_submission.md").read_text(encoding="utf-8")
        cls.internal = (PAPER / "manuscript_submission_internal.md").read_text(encoding="utf-8")

    def test_exactly_four_main_figures_and_three_tables(self) -> None:
        figures = PAPER / "figures"
        for extension in ("png", "svg", "provenance.json"):
            self.assertEqual(4, len(list(figures.glob(f"figure_*.{extension}"))))
        self.assertEqual(3, len(list((PAPER / "tables").glob("table_*.md"))))

    def test_phase_figures_reconcile_to_core(self) -> None:
        definitions = (
            ("DS02 discovery", "figure_2_ds02_phase_fpr.svg"),
            ("DS03 confirmation", "figure_4_ds03_phase_fpr.svg"),
        )
        for dataset, filename in definitions:
            svg = (PAPER / "figures" / filename).read_text(encoding="utf-8")
            subset = [
                row for row in self.core
                if row["dataset"] == dataset
                and row["selection_group"] == "frozen primary pooled endpoint"
                and row["metric"] in {"climb_fpr", "cruise_fpr", "descent_fpr"}
                and row["seed_or_aggregation"] in {"-1", "mean(seeds 0,1,2)"}
            ]
            self.assertEqual(9, len(subset))
            for row in subset:
                self.assertEqual(row["exact_value"], self.ledger[row["evidence_id"]]["exact_numeric_value"])
                self.assertIn(row["display_rounded_value"], svg)

    def test_transfer_heatmap_reconciles_to_executed_csv(self) -> None:
        source = ROOT / "results/final_validation/executed_threshold_transfer_matrix.csv"
        transfer = [
            row for row in rows(source)
            if row["detector"] == "pca" and row["seed"] == "-1"
            and row["phase_definition"] == "primary" and row["nominal_fpr"] == "0.01"
            and row["unit"] == "all"
        ]
        self.assertEqual(9, len(transfer))
        svg = (PAPER / "figures/figure_3_cross_phase_transfer.svg").read_text(encoding="utf-8")
        for row in transfer:
            self.assertIn(f"{float(row['false_alarm_rate']) * 100:.3f}%", svg)

    def test_provenance_and_manuscript_distinction(self) -> None:
        for sidecar in (PAPER / "figures").glob("figure_*.provenance.json"):
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual("scripts/build_submission_package.py", metadata["generation_script"])
            for claim_id in metadata["evidence_ids"]:
                self.assertIn(claim_id, self.ledger)
            for source in metadata["source_paths"]:
                self.assertTrue((ROOT / source).exists(), source)
        self.assertIn("<!-- evidence:", self.internal)
        self.assertNotIn("<!-- evidence:", self.clean)
        self.assertEqual(4, self.clean.count("**Fig. "))
        self.assertEqual(3, self.clean.count("**Table "))
        self.assertIn(
            "The detectors are unsupervised with respect to fault labels; supplied health-state annotations are used only to select healthy samples for retrospective fitting, calibration, and evaluation.",
            self.clean,
        )

    def test_claim_wording_and_units(self) -> None:
        self.assertNotRegex(self.clean, re.compile(r"25[–-]35%|detector-independent|universally confirmed", re.I))
        self.assertIn("600-epoch ceiling", self.clean)
        self.assertIn("descent-minus-climb", self.clean)
        self.assertIn("percentage points", self.clean)
        self.assertIn("DS02 exploratory", self.clean)
        self.assertIn("DS03 confirmatory", self.clean)


if __name__ == "__main__":
    unittest.main()
