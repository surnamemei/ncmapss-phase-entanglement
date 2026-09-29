"""Run the data-free test suite of the public v1.1.0 snapshot.

The public snapshot leaves out the submission administration, LaTeX build logs, model checkpoints and the private
git history (tags). The inherited suites contain a fixed set of tests that check exactly that material, and three
synthetic end-to-end tests whose one-shot runners stop at the complete frozen-manifest gate. They are listed below with
the reason, and they are not run as inherited. Every other test in tests/ runs unchanged, together with
tests/test_public_release.py, which re-checks against this snapshot the parts of the listed tests that still apply and
runs the three end-to-end tests unchanged behind the public gate. The runner stops if the list names a test that does
not exist, so the list cannot drift silently from the suite.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ADMIN = "submission administration (cover letter, declarations, upload bundle, checklists, Highlights .docx) is not distributed"
RECHECKED = "; the applicable checks are repeated in tests/test_public_release.py"
LOG = "LaTeX build logs are build artifacts and are not distributed"
MANIFEST = ("the frozen-baseline manifest lists 12 git-ignored LSTM checkpoints and 19 RESS submission-administration "
            "files that are not distributed; tests/test_public_release.py verifies every distributed entry and the "
            "exact set of absent ones")
HISTORY = ("the private git tags and history are not part of the public snapshot; tests/test_public_release.py "
           "compares with them when they are available")
PRE_RELEASE = ("asserts the pre-release state (no v1.1.0 tag; release notes 'prepared, not published'); replaced by "
               "the release-metadata checks in tests/test_public_release.py")
GATE = ("the one-shot runner's first gate verifies the complete frozen-baseline manifest, which lists files that are "
        "not distributed, so the runner stops as designed; tests/test_public_release.py runs this test unchanged "
        "behind the public gate (every distributed entry verified, the absent ones exactly the documented set)")

NOT_APPLICABLE = {
    "test_mssp_extended_manuscript.BuiltArtifacts.test_cover_letter_is_one_page_and_names_the_manuscript": ADMIN,
    "test_mssp_extended_manuscript.BuiltArtifacts.test_upload_bundle_manifest_and_copies": ADMIN,
    "test_mssp_extended_manuscript.LimitsAndWording.test_highlights_word_file_matches_text": ADMIN,
    "test_mssp_extended_manuscript.LimitsAndWording.test_final_uncertainty_terminology": ADMIN + RECHECKED,
    "test_mssp_extended_manuscript.LayoutAndRendering.test_layout_log_is_clean": LOG,
    "test_mssp_extended_manuscript.Consistency.test_title_consistent_across_documents": ADMIN + RECHECKED,
    "test_mssp_extended_manuscript.Consistency.test_author_metadata_consistent": ADMIN + RECHECKED,
    "test_mssp_extended_manuscript.Consistency.test_cover_letter_is_one_page_without_declarations": ADMIN,
    "test_mssp_extended_manuscript.Consistency.test_declarations_exported_from_the_draft": ADMIN + RECHECKED,
    "test_mssp_extended_manuscript.Consistency.test_release_metadata_prepared_not_published": PRE_RELEASE,
    "test_mssp_extended_manuscript.Consistency.test_upload_bundle_matches_the_documented_file_list": ADMIN,
    "test_mssp_extended_manuscript.FrozenBoundaries.test_frozen_tags_exist": HISTORY,
    "test_mssp_extended_manuscript.FrozenBoundaries.test_frozen_baseline_manifest_verifies": MANIFEST,
    "test_mssp_extended_manuscript.FrozenBoundaries.test_pre_extension_packages_are_unchanged": HISTORY,
    "test_mssp_manuscript.NumbersAndWording.test_highlights_word_file_matches_text": ADMIN,
    "test_mssp_manuscript.Consistency.test_title_consistent_across_documents": ADMIN + RECHECKED,
    "test_mssp_manuscript.Consistency.test_author_email_and_orcid_consistent": ADMIN + RECHECKED,
    "test_mssp_manuscript.Consistency.test_cover_letter_is_one_page_without_declarations": ADMIN,
    "test_mssp_manuscript.Provenance.test_frozen_baseline_unchanged": MANIFEST,
    "test_mssp_manuscript.Provenance.test_ress_package_unchanged": HISTORY,
    "test_extension_pipeline.Gating.test_frozen_baseline_unchanged": MANIFEST,
    "test_extension_pipeline.EndToEndSynthetic.test_lock_then_one_shot_audit": GATE,
    "test_extension_pipeline.SummaryOnSyntheticCohort.test_decisions": GATE,
    "test_focused_validation.EndToEndSynthetic.test_focused_validation_runs_and_gates_hold": GATE,
    "test_mssp_adversarial.LeakageAndProvenance.test_plan_frozen_and_manifest_intact": MANIFEST,
    "test_mssp_mitigation.FrozenIsolation.test_baseline_manifest_verifies": MANIFEST,
}


def iter_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true", help="print one line per test")
    args = parser.parse_args()
    in_git = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT, capture_output=True,
                            text=True).stdout.strip() == "true"
    if not in_git:
        sys.exit("run from a git checkout of the public release (some tests read the committed tree)")
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT / "tests"))
    selected, deselected = unittest.TestSuite(), []
    for test in iter_tests(tests):
        if test.id() in NOT_APPLICABLE:
            deselected.append(test.id())
        else:
            selected.addTest(test)
    unknown = sorted(set(NOT_APPLICABLE) - set(deselected))
    if unknown:
        sys.exit("NOT_APPLICABLE names tests that do not exist:\n  " + "\n  ".join(unknown))
    print(f"Not run as inherited: {len(deselected)} tests (reasons below).")
    for test_id in sorted(deselected):
        print(f"  {test_id}\n      {NOT_APPLICABLE[test_id]}")
    print(f"Running {selected.countTestCases()} tests.", flush=True)
    result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(selected)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
