"""Provenance and source-whitelist checks for paper generation."""

import csv
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PaperPipelineGuards(unittest.TestCase):
    def test_no_obsolete_report_references(self):
        forbidden = ("phase3_report.md", "phase3_cross_detector_results.md",
                     "final_phase3_summary.md", "results/phase3_cross_detector/")
        for path in list((ROOT / "scripts").glob("build_paper_*.py")) + list((ROOT / "paper").glob("build_*.py")):
            code = path.read_text(encoding="utf-8")
            for name in forbidden:
                self.assertNotIn(name, code, str(path))

    def test_core_values_resolve_to_ledger(self):
        with (ROOT / "paper/evidence_ledger.csv").open(newline="", encoding="utf-8") as handle:
            ledger = {row["claim_id"]: row for row in csv.DictReader(handle)}
        with (ROOT / "paper/manuscript_core_results.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                evidence = ledger[row["evidence_id"]]
                self.assertEqual(row["exact_value"], evidence["exact_numeric_value"])
                self.assertEqual(row["original_source_csv"], evidence["source_csv"])

    def test_table_and_figure_dry_run_inputs(self):
        for name, func in (("build_paper_tables.py", "build_rows"),
                           ("build_paper_figures.py", "figure_data")):
            path = ROOT / "scripts" / name
            spec = importlib.util.spec_from_file_location(path.stem, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertGreater(len(getattr(module, func)()), 0)


if __name__ == "__main__":
    unittest.main()
