"""Integrity checks for the public v1.1.0 snapshot (branch public-v1.1.0).

No N-CMAPSS data are read. The public snapshot leaves out the submission administration, LaTeX build logs, model
checkpoints and the private git history; scripts/run_public_tests.py lists the inherited tests that check that
material. These tests re-check what still applies to the snapshot: the release manifest, every distributed frozen
file, the frozen plans and protocols, the preprint and supplement hashes, the terminology, titles and author metadata
of the manuscript packages, the release metadata, and the absence of raw data, binaries and credentials. They also
run the inherited synthetic end-to-end tests of the one-shot runners through the public frozen-baseline gate.
"""

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import ext_common as ec  # noqa: E402
import test_extension_pipeline  # noqa: E402
import test_focused_validation  # noqa: E402

EXT, PRE = ROOT / "paper/mssp_extended", ROOT / "paper/mssp"
RELEASE = ROOT / "docs/release/v1.1.0"
MANIFEST, NOTES = RELEASE / "PUBLIC_RELEASE_MANIFEST.sha256", RELEASE / "RELEASE_NOTES.md"
README, CITATION, ZENODO = ROOT / "README.md", ROOT / "CITATION.cff", ROOT / ".zenodo.json"
BASELINE = ROOT / "docs/mssp/frozen_baseline.sha256"
SOURCE_COMMIT = "54b25ee0934a2c0570428f1e84894603ea1a0f70"  # private provenance commit the snapshot was cut from
RELEASE_TITLE = "v1.1.0 — Calibration Transport Manuscript and Reproducibility Release"
PREPRINT_NOTICE = ("The manuscript provided in this repository is an author preprint and has not undergone peer review "
                   "for the current journal submission. If a version of record is later published, this repository "
                   "will link to the publisher DOI.")
LICENSE_SCOPE = ("The MIT License applies to project-authored software and code. Manuscript text and figures are "
                 "© 2026 Jinghang Mei and are not offered under the MIT License unless explicitly stated otherwise.")

# Frozen-baseline entries that the public snapshot deliberately does not distribute.
CHECKPOINTS = {f"results/{run}/checkpoints/lstm_seed_{seed}_{kind}.pt"
               for run in ("final_validation", "confirmation_ds03") for seed in range(3) for kind in ("final", "selection")}
RESS_ADMIN = {f"paper/submission/{name}" for name in (
    "RESS_SUBMISSION_CHECKLIST.md", "ai_assistance_note.md", "author_contributions.md", "author_metadata.md",
    "code_availability.md", "code_availability_final.md", "competing_interest_final.txt", "cover_letter.md",
    "cover_letter_final.md", "credit_author_statement.md", "data_availability.md", "data_availability_final.md",
    "declaration_of_interests.md", "final_submission_audit.md", "funding_statement.md", "funding_statement_final.txt",
    "generative_ai_declaration.md", "graphical_abstract_plan.md", "ress_conversion_audit.md")}

# The only differences from the private source commit, apart from the files left out.
PUBLIC_CHANGES = {
    "README.md",
    ".zenodo.json",
    ".gitignore",
    ".github/workflows/tests.yml",
    "paper/mssp_extended/README.md",
    "docs/release/v1.1.0/RELEASE_NOTES.md",
    "tests/test_mssp_adversarial.py",
}
PUBLIC_ADDITIONS = {"docs/release/v1.1.0/PUBLIC_RELEASE_MANIFEST.sha256", "scripts/run_public_tests.py",
                    "tests/test_public_release.py"}

NOT_DISTRIBUTED = (  # path patterns that must never appear in the public snapshot
    r"(^|/)submission_bundle/", r"(^|/)cover_letter/", r"(^|/)declarations/", r"(^|/)SUBMISSION_[A-Z_]+\.md$",
    r"FINAL_SUBMISSION_", r"READINESS", r"Highlights\.docx$", r"(^|/)N-CMAPSS/", r"(^|/)(checkpoints|models)/",
    r"\.(h5|hdf5|zip|7z|tar|gz|pt|pth|ckpt|keras|npy|npz|pkl|pickle|joblib|safetensors|onnx)$", r"\.log$",
    r"(^|/)__pycache__/", r"(^|/)(tmp|temp|cache)/", r"(^|/)\.env$", r"\.(pem|key|p12|pfx)$")
MAGIC = {b"\x89HDF\r\n\x1a\n": "HDF5", b"PK\x03\x04": "ZIP archive (including PyTorch checkpoints and .docx)",
         b"\x93NUMPY": "NumPy array", **{bytes([0x80, v]): "pickle" for v in (2, 3, 4, 5)}}
SECRETS = {
    "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "AWS access key": r"\b(AKIA|ASIA)[0-9A-Z]{16}\b",
    "GitHub token": r"\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b",
    "Slack token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b",
    "API key": r"\bsk-(ant-)?[A-Za-z0-9_-]{20,}\b",
    "Google API key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "credential assignment": r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\s*[:=]\s*"
                             r"['\"][^'\"\s]{8,}['\"]",
    "URL with credentials": r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s:@]+@",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def has_ref(ref):
    return git("rev-parse", "--verify", "--quiet", ref).returncode == 0


def manifest_entries():
    return {path: digest for digest, path in
            (line.split("  ", 1) for line in MANIFEST.read_text(encoding="utf-8").splitlines())}


def flat(text):
    return " ".join(text.split())


def pdf_text(path):
    return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout


def draft_title(package):
    text = (package / "manuscript_mssp_draft.md").read_text(encoding="utf-8")
    return re.search(r"^# (.+)$", text, flags=re.M).group(1).strip()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def baseline_status():
    """Entries of the 186-file frozen-baseline manifest: (count, changed distributed entries, absent entries)."""
    entries = [line.split("  ", 1) for line in BASELINE.read_text(encoding="utf-8").splitlines() if line.strip()]
    absent = {path for _, path in entries if not (ROOT / path).exists()}
    changed = [path for digest, path in entries if path not in absent and sha256(ROOT / path) != digest]
    return len(entries), changed, absent


def public_baseline_gate():
    """The runners' frozen-baseline gate on the public snapshot: every distributed entry must verify, and the absent
    entries must be exactly the documented checkpoints and RESS submission-administration files."""
    count, changed, absent = baseline_status()
    if count != 186 or changed or absent != CHECKPOINTS | RESS_ADMIN:
        raise ec.ExtensionError(f"Public frozen-baseline gate failed: changed {changed}, absent {sorted(absent)}")
    return True


class PublicGate:
    """Run an inherited synthetic end-to-end test unchanged, with the frozen-baseline gate of the one-shot runners
    (ext_common.verify_baseline) replaced by the public gate for the duration of the test."""

    def setUp(self):
        self.addCleanup(setattr, ec, "verify_baseline", ec.verify_baseline)
        ec.verify_baseline = public_baseline_gate
        super().setUp()


class ReleaseManifest(unittest.TestCase):
    def test_every_distributed_file_is_listed_once_with_its_hash(self):
        lines = MANIFEST.read_text(encoding="utf-8").splitlines()
        entries = manifest_entries()
        self.assertEqual([line.split("  ", 1)[1] for line in lines], sorted(entries), "one sorted entry per file")
        own = MANIFEST.relative_to(ROOT).as_posix()
        self.assertNotIn(own, entries)
        for path, digest in entries.items():
            self.assertEqual(sha256(ROOT / path), digest, path)
        tracked = git("ls-files", "-z")
        if tracked.returncode == 0:
            self.assertEqual(set(entries), {p for p in tracked.stdout.split("\0") if p} - {own})

    def test_no_submission_material_raw_data_or_binaries(self):
        for path in manifest_entries():
            for pattern in NOT_DISTRIBUTED:
                self.assertIsNone(re.search(pattern, path), f"{path} matches {pattern}")
            head = (ROOT / path).read_bytes()[:8]
            for magic, kind in MAGIC.items():
                self.assertFalse(head.startswith(magic), f"{path} is a {kind} file")

    def test_no_credentials_in_text_files(self):
        patterns = {name: re.compile(p) for name, p in SECRETS.items()}
        for path in manifest_entries():
            data = (ROOT / path).read_bytes()
            if path.endswith((".pdf", ".png")) or b"\0" in data[:4096]:
                continue
            text = data.decode("utf-8", errors="replace")
            for name, pattern in patterns.items():
                self.assertIsNone(pattern.search(text), f"{path}: {name}")


class FrozenRecords(unittest.TestCase):
    def test_distributed_frozen_baseline_entries_verify_and_absences_are_documented(self):
        # Replaces the inherited full-manifest checks: the 186-file manifest also lists the git-ignored LSTM
        # checkpoints and the RESS submission-administration files, which are not distributed.
        count, changed, absent = baseline_status()
        self.assertEqual(count, 186)
        self.assertEqual(changed, [])
        self.assertEqual(absent, CHECKPOINTS | RESS_ADMIN)
        self.assertEqual(count - len(absent), 155)
        self.assertTrue(public_baseline_gate())

    def test_frozen_plans_protocols_and_freeze_record(self):
        sys.path.insert(0, str(ROOT / "src"))
        import mssp_adversarial as ma
        self.assertEqual(ma.verify_plan(), ma.PLAN_SHA256)
        record = (ROOT / "docs/mssp/FREEZE_RECORD.md").read_text(encoding="utf-8")
        rows = re.findall(r"`([^`]+)`\s*\|\s*`([0-9a-f]{64})`", record)
        self.assertEqual(len(rows), 6)
        for path, digest in rows:
            self.assertEqual(sha256(ROOT / path), digest, path)
        protocol = sha256(ROOT / "docs/extension/GENERALIZATION_PROTOCOL.md")
        cvae = sha256(ROOT / "docs/extension/CVAE_SPECIFICATION.md")
        locks = sorted((ROOT / "results/extension").glob("*/lock/calibration_lock.json"))
        self.assertEqual(len(locks), 9)
        for lock in locks:
            code = json.loads(lock.read_text(encoding="utf-8"))["code"]
            self.assertEqual((code["protocol_sha256"], code["cvae_spec_sha256"]), (protocol, cvae), lock.parent.parent.name)

    def test_frozen_packages_match_their_tags_when_available(self):
        # Replaces the inherited tag comparisons, which also count the files that are not distributed. Only
        # deletions (material left out of the snapshot) may differ; every distributed file must be identical.
        present = [path for _, path in (line.split("  ", 1) for line in BASELINE.read_text(encoding="utf-8").splitlines())
                   if (ROOT / path).exists()]
        checks = {
            "v1.0.0": present,
            "ress-submission-2026-09-25": ["paper/ress", "paper/submission"],
            "mssp-pre-extension-2026-09-28": [
                "paper/mssp/manuscript_mssp_draft.md", "paper/mssp/latex", "paper/mssp/supplement", "paper/mssp/figures",
                "paper/mssp/tables", "paper/ress", "paper/submission", "results/final_validation",
                "results/confirmation_ds03", "results/mssp_mitigation", "results/mssp_adversarial"],
        }
        available = [tag for tag in checks if has_ref(f"refs/tags/{tag}")]
        if not available:
            self.skipTest("the frozen tags are not available in this clone")
        for tag in available:
            result = git("diff", "--name-status", "--no-renames", "--diff-filter=d", tag, "HEAD", "--", *checks[tag])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "", f"distributed files differ from {tag}")

    def test_snapshot_equals_the_private_source_commit_apart_from_documented_changes(self):
        if not has_ref(SOURCE_COMMIT + "^{commit}"):
            self.skipTest("the private source commit is not available in this clone")
        changed = {}
        for line in git("diff", "--name-status", "--no-renames", SOURCE_COMMIT, "HEAD").stdout.splitlines():
            status, path = line.split("\t", 1)
            changed.setdefault(status, set()).add(path)
        self.assertEqual(set(changed) - {"A", "M", "D"}, set())
        self.assertEqual(changed.get("M", set()), PUBLIC_CHANGES)
        self.assertEqual(changed.get("A", set()), PUBLIC_ADDITIONS)


class Preprint(unittest.TestCase):
    def test_preprint_and_supplement_hashes(self):
        notes, readme = NOTES.read_text(encoding="utf-8"), README.read_text(encoding="utf-8")
        preprint, supplement, part_b = EXT / "latex/main.pdf", EXT / "supplement/supplement.pdf", PRE / "supplement/supplement.pdf"
        for path in (preprint, supplement):
            self.assertIn(sha256(path), notes, path.name)
            self.assertIn(sha256(path), readme, path.name)
        record = json.loads((EXT / "supplement/supplement.provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(record["outputs"]["paper/mssp_extended/supplement/supplement.pdf"], sha256(supplement))
        self.assertEqual(record["inputs"]["paper/mssp/supplement/supplement.pdf"], sha256(part_b))
        frozen = json.loads((PRE / "supplement/supplement.provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(frozen["outputs"]["paper/mssp/supplement/supplement.pdf"], sha256(part_b))

    def test_final_uncertainty_terminology(self):
        # test_mssp_extended_manuscript.LimitsAndWording.test_final_uncertainty_terminology without the cover letter
        ambiguous = ("noise floor", "noise-floor", "self-calibration floor", "cross-fitted floor", "noise references")
        draft = re.sub(r"<!--.*?-->", "", (EXT / "manuscript_mssp_draft.md").read_text(encoding="utf-8"), flags=re.S).lower()
        supplement_a = flat(pdf_text(EXT / "supplement/supplement.pdf")).lower().split(
            "part b. supplement of the pre-extension study", 1)[0]
        for document, name in ((draft, "draft"), (flat(pdf_text(EXT / "latex/main.pdf")).lower(), "PDF"),
                               (supplement_a, "supplement A")):
            for term in ambiguous:
                self.assertNotIn(term, document, f"{term!r} in {name}")
        self.assertIn("cross-fitted self-calibration reference", draft)
        self.assertIn("engine-specific sampling and self-calibration references", draft)

    def test_titles_consistent_across_documents(self):
        # the inherited title checks without the cover letters, checklists and submission file lists
        final, pre = draft_title(EXT), draft_title(PRE)
        for path in (EXT / "latex/main.tex", EXT / "supplement/supplement.tex", README, NOTES):
            self.assertIn(final, flat(path.read_text(encoding="utf-8")), path.name)
        self.assertIn(final, json.loads(ZENODO.read_text(encoding="utf-8"))["description"])
        for path in (PRE / "latex/main.tex", PRE / "supplement/supplement.tex", README, NOTES):
            self.assertIn(pre, flat(path.read_text(encoding="utf-8")), path.name)

    def test_author_metadata_consistent(self):
        # the inherited author checks without the cover letters
        cff = CITATION.read_text(encoding="utf-8")
        zenodo = json.loads(ZENODO.read_text(encoding="utf-8"))
        for package in (EXT, PRE):
            author = load(package / "build_latex.py", f"public_release_{package.name}_build_latex").AUTHOR
            tex = (package / "latex/main.tex").read_text(encoding="utf-8")
            for field in ("name", "email", "orcid"):
                self.assertIn(author[field], tex, f"{package.name}: {field}")
            self.assertIn(f"https://orcid.org/{author['orcid']}", cff)
            self.assertEqual(zenodo["creators"][0]["orcid"], author["orcid"])
        self.assertIn("family-names: Mei", cff)

    def test_ai_declaration_in_the_draft(self):
        # test_mssp_extended_manuscript.Consistency.test_declarations_exported_from_the_draft, without the exports
        ai = (EXT / "manuscript_mssp_draft.md").read_text(encoding="utf-8").split("## Declaration of generative AI", 1)[1]
        self.assertIn("takes full responsibility", ai)
        self.assertIn("Claude Opus 5.5", ai)


class ReleaseMetadata(unittest.TestCase):
    def test_preprint_notice_and_license_scope_verbatim(self):
        zenodo_notes = json.loads(ZENODO.read_text(encoding="utf-8"))["notes"]
        for text, name in ((README.read_text(encoding="utf-8"), "README"), (NOTES.read_text(encoding="utf-8"), "notes"),
                           (zenodo_notes, ".zenodo.json notes")):
            self.assertIn(PREPRINT_NOTICE, text, name)
            self.assertIn(LICENSE_SCOPE, text, name)

    def test_release_notes_state_the_release(self):
        notes = flat(NOTES.read_text(encoding="utf-8"))
        self.assertTrue(notes.startswith("# " + RELEASE_TITLE))
        for statement in ("multi-subset N-CMAPSS calibration-transport audit", "DS02 discovery",
                          "frozen DS03 confirmation", "seven additional", "frozen extension protocol", "PCA",
                          "Isolation Forest", "past-only LSTM", "condition-aware CVAE", "calibration-fleet coverage",
                          "cross-engine transport", "matched false-flag evaluation", "final engine-specific validation",
                          "Raw NASA data are not redistributed", "not a peer-reviewed version of record"):
            self.assertIn(statement.lower(), notes.lower(), statement)

    def test_citation_and_archive_metadata(self):
        cff = CITATION.read_text(encoding="utf-8")
        for field in ("cff-version: 1.2.0", "version: 1.1.0", "license: MIT", "family-names: Mei",
                      "given-names: Jinghang", "repository-code: https://github.com/surnamemei/ncmapss-phase-entanglement"):
            self.assertIn(field, cff)
        zenodo = json.loads(ZENODO.read_text(encoding="utf-8"))
        self.assertEqual((zenodo["version"], zenodo["upload_type"], zenodo["license"], zenodo["access_right"]),
                         ("1.1.0", "software", "MIT", "open"))
        self.assertEqual(zenodo["title"], re.search(r'^title: "(.+)"$', cff, flags=re.M).group(1))
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(license_text.startswith("MIT License"))
        self.assertIn("Copyright (c) 2026 Jinghang Mei", license_text)


# The inherited synthetic end-to-end tests of the one-shot runners, unchanged but behind the public gate (they need CUDA
# and are skipped without it). scripts/run_public_tests.py does not run the originals, whose first gate checks the
# complete manifest.
class ExtensionEndToEndThroughPublicGate(PublicGate, test_extension_pipeline.EndToEndSynthetic):
    pass


class ExtensionSummaryThroughPublicGate(PublicGate, test_extension_pipeline.SummaryOnSyntheticCohort):
    pass


class FocusedValidationEndToEndThroughPublicGate(PublicGate, test_focused_validation.EndToEndSynthetic):
    pass


if __name__ == "__main__":
    unittest.main()
