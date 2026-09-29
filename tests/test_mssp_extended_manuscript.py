"""QA for the extended MSSP manuscript package (paper/mssp_extended/).

No N-CMAPSS data are read. The tests check that every cited number re-derives from the committed extension
outputs, that the built LaTeX, PDF, supplement, cover letter and upload bundle are in sync with their sources,
that every figure and table matches its provenance record, and that the frozen packages are untouched.
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
PKG = ROOT / "paper/mssp_extended"
DRAFT = PKG / "manuscript_mssp_draft.md"
PAGE_LIMIT = 25
FROZEN_TAGS = ("v1.0.0", "ress-submission-2026-09-25", "mssp-pre-extension-2026-09-28")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pdf_pages(path):
    info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", info).group(1))


def load(name):
    """Import a package script under a unique module name (paper/mssp has scripts with the same names)."""
    spec = importlib.util.spec_from_file_location(f"mssp_extended_{name}", PKG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


class NumbersAndWording(unittest.TestCase):
    def test_every_cited_number_rederives_and_wording_rules_hold(self):
        result = subprocess.run([sys.executable, str(PKG / "verify_numbers.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        self.assertIn("all checks passed", result.stdout)

    def test_post_hoc_checks_reproduce_exactly(self):
        paths = [PKG / "evidence/post_hoc_checks.json", PKG / "evidence/post_hoc_engine_noise.csv"]
        before = [sha256(p) for p in paths]
        result = subprocess.run([sys.executable, str(PKG / "post_hoc_checks.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertEqual([sha256(p) for p in paths], before, "post hoc checks are not deterministic or are out of date")
        summary = json.loads(paths[0].read_text(encoding="utf-8"))
        self.assertTrue(summary["status"].startswith("post hoc"))

    def test_post_hoc_material_is_labelled_in_the_draft(self):
        text = DRAFT.read_text(encoding="utf-8")
        validation = text.split("### 4.8 Final focused validation (post hoc)", 1)[1].split("### 4.9", 1)[0]
        self.assertIn("reproduction gates passed", validation)
        self.assertIn("pre-declared rule", validation)
        other = text.split("### 4.9 Other post hoc checks", 1)[1].split("## 5. Discussion", 1)[0]
        self.assertIn("were not pre-specified", other)
        self.assertIn("change no decision in Table 4", other)
        methods = text.split("### 3.10 Final focused validation (post hoc)", 1)[1].split("### 3.11", 1)[0]
        self.assertIn("frozen as a separate plan", methods)
        for pre in text.split("### 4.8 Final focused validation", 1)[0].split("## 4. Results", 1)[1].split("### ")[1:]:
            # pre-specified sections may cite post hoc numbers only by pointing to Section 4.8 or 4.9
            if "Section 4.8" not in pre and "Section 4.9" not in pre and "Sections 4.8" not in pre:
                self.assertNotIn("post hoc", pre.lower())

    def test_bibliography_holds_exactly_the_cited_keys(self):
        text = re.sub(r"<!--.*?-->", "", DRAFT.read_text(encoding="utf-8"), flags=re.S)
        cited = set(re.findall(r"\[(N?\d+)\]", text))
        for a, b, _, d in re.findall(r"\[(N?)(\d+)\]–\[(N?)(\d+)\]", text):
            cited.update(a + str(k) for k in range(int(b), int(d) + 1))
        keys = {k if k.startswith("N") else f"ref{k}" for k in cited}
        bib = set(re.findall(r"@\w+\{([^,]+),", (PKG / "latex/references_mssp.bib").read_text(encoding="utf-8")))
        self.assertEqual(bib, keys)


class BuiltArtifacts(unittest.TestCase):
    def test_main_tex_is_in_sync_with_the_draft(self):
        builder = load("build_latex")
        document, highlights = builder.convert(DRAFT.read_text(encoding="utf-8"))
        self.assertEqual((PKG / "latex/main.tex").read_text(encoding="utf-8"), document)
        self.assertEqual((PKG / "latex/highlights.txt").read_text(encoding="utf-8"), "\n".join(highlights) + "\n")

    def test_pdf_within_page_limit_without_undefined_references(self):
        self.assertLessEqual(pdf_pages(PKG / "latex/main.pdf"), PAGE_LIMIT)
        text = subprocess.run(["pdftotext", str(PKG / "latex/main.pdf"), "-"], capture_output=True, text=True).stdout
        self.assertNotIn("??", text)
        self.assertIn("Calibration Transport", text)

    def test_every_figure_and_table_is_cited_built_and_matches_provenance(self):
        builder = load("build_latex")
        text = DRAFT.read_text(encoding="utf-8")
        for number, name in builder.FIGURES.items():
            self.assertRegex(text, rf"Fig\. {number}[a-z]?\b")
            self.assertTrue((PKG / "figures" / f"{name}.pdf").exists(), name)
        for number, name in builder.TABLES.items():
            self.assertRegex(text, rf"Table {number}\b")
            self.assertTrue((PKG / "tables" / f"{name}.tex").exists(), name)
        records = sorted((PKG / "figures").glob("*.provenance.json")) + sorted((PKG / "tables").glob("*.provenance.json"))
        self.assertEqual(len(records), len(builder.FIGURES) + len(builder.TABLES))
        current_builder = sha256(PKG / "build_figures_tables.py")
        for record_path in records:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["builder_sha256"], current_builder, record_path.name)
            for rel, digest in {**record["inputs"], **record["outputs"]}.items():
                self.assertEqual(sha256(ROOT / rel), digest, f"{record_path.name}: {rel}")

    def test_evidence_checksums(self):
        for line in (PKG / "evidence/SHA256SUMS").read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            self.assertEqual(sha256(PKG / "evidence" / name), digest, name)

    def test_supplement_matches_provenance_and_includes_the_committed_pre_extension_supplement(self):
        record = json.loads((PKG / "supplement/supplement.provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(record["builder_sha256"], sha256(PKG / "build_supplement.py"))
        for rel, digest in {**record["inputs"], **record["outputs"]}.items():
            self.assertEqual(sha256(ROOT / rel), digest, rel)
        committed = subprocess.run(["git", "show", "HEAD:paper/mssp/supplement/supplement.pdf"], cwd=ROOT,
                                   capture_output=True, check=True).stdout
        self.assertEqual(hashlib.sha256(committed).hexdigest(), sha256(ROOT / "paper/mssp/supplement/supplement.pdf"))
        self.assertGreater(pdf_pages(PKG / "supplement/supplement.pdf"), pdf_pages(ROOT / "paper/mssp/supplement/supplement.pdf"))

    def test_cover_letter_is_one_page_and_names_the_manuscript(self):
        self.assertEqual(pdf_pages(PKG / "cover_letter/cover_letter.pdf"), 1)
        title = re.search(r"^# (.+)$", DRAFT.read_text(encoding="utf-8"), flags=re.M).group(1).strip()
        self.assertIn(title, (PKG / "cover_letter/cover_letter.txt").read_text(encoding="utf-8"))

    def test_upload_bundle_manifest_and_copies(self):
        bundle = PKG / "submission_bundle"
        lines = (bundle / "UPLOAD_MANIFEST.txt").read_text(encoding="utf-8").splitlines()
        self.assertGreaterEqual(len(lines), 15)
        for line in lines:
            digest, name = line.split("  ", 1)
            self.assertEqual(sha256(bundle / name), digest, name)
        for built, copy in (("latex/main.pdf", "manuscript.pdf"), ("supplement/supplement.pdf", "supplementary_material.pdf"),
                            ("cover_letter/cover_letter.pdf", "cover_letter.pdf")):
            self.assertEqual(sha256(PKG / built), sha256(bundle / copy), copy)


def pdf_text(path, first=None, last=None):
    command = ["pdftotext", "-layout"] + (["-f", str(first)] if first else []) + (["-l", str(last)] if last else [])
    return subprocess.run(command + [str(path), "-"], capture_output=True, text=True, check=True).stdout


def draft_title():
    return re.search(r"^# (.+)$", DRAFT.read_text(encoding="utf-8"), flags=re.M).group(1).strip()


def flat(text):
    return " ".join(text.split())


MAIN_TEX, MAIN_PDF = PKG / "latex/main.tex", PKG / "latex/main.pdf"
SUPP_TEX, SUPP_PDF = PKG / "supplement/supplement.tex", PKG / "supplement/supplement.pdf"
COVER_TXT, COVER_PDF = PKG / "cover_letter/cover_letter.txt", PKG / "cover_letter/cover_letter.pdf"
RELEASE_NOTES, ZENODO, CITATION = ROOT / "docs/release/v1.1.0/RELEASE_NOTES.md", ROOT / ".zenodo.json", ROOT / "CITATION.cff"
CHECKLIST, FILES_DOC = PKG / "FINAL_SUBMISSION_CHECKLIST.md", PKG / "SUBMISSION_FILES.md"
AMBIGUOUS = ("noise floor", "noise-floor", "self-calibration floor", "cross-fitted floor", "noise references")


class LimitsAndWording(unittest.TestCase):
    def test_limits(self):
        text = DRAFT.read_text(encoding="utf-8")
        abstract = text.split("## Abstract", 1)[1].split("**Keywords:**", 1)[0]
        self.assertLessEqual(len(abstract.split()), 250)
        keywords = [k for k in text.split("**Keywords:**", 1)[1].splitlines()[0].split(";") if k.strip()]
        self.assertLessEqual(len(keywords), 6, "MSSP: a maximum of 6 keywords")
        highlights = (PKG / "latex/highlights.txt").read_text(encoding="utf-8").splitlines()
        self.assertTrue(3 <= len(highlights) <= 5)
        self.assertTrue(all(len(h) <= 85 for h in highlights))

    def test_highlights_word_file_matches_text(self):
        import zipfile
        with zipfile.ZipFile(PKG / "latex/Highlights.docx") as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        for line in (PKG / "latex/highlights.txt").read_text(encoding="utf-8").splitlines():
            self.assertIn(line.replace("&", "&amp;"), xml)

    def test_final_uncertainty_terminology(self):
        draft = re.sub(r"<!--.*?-->", "", DRAFT.read_text(encoding="utf-8"), flags=re.S).lower()
        supplement_a = flat(pdf_text(SUPP_PDF)).lower().split("part b. supplement of the pre-extension study", 1)[0]
        for document, name in ((draft, "draft"), (flat(pdf_text(MAIN_PDF)).lower(), "PDF"), (supplement_a, "supplement A"),
                               (COVER_TXT.read_text(encoding="utf-8").lower(), "cover letter")):
            for term in AMBIGUOUS:
                self.assertNotIn(term, document, f"{term!r} in {name}")
        self.assertIn("cross-fitted self-calibration reference", draft)
        self.assertIn("engine-specific sampling and self-calibration references", draft)

    def test_stale_wording_absent_from_pdf(self):
        text = flat(pdf_text(MAIN_PDF)).lower().rsplit("references", 1)[0]
        for phrase in ("pre-registered", "causal lstm", "fault sensitivity", "mitigation", "limiting factor", "stabiliz",
                       "reliability engineering & system safety"):
            self.assertNotIn(phrase, text, phrase)


class References(unittest.TestCase):
    def setUp(self):
        self.bb = load("build_bibliography")
        self.cited = self.bb.cited_keys(DRAFT.read_text(encoding="utf-8"))

    def test_cited_keys_equal_bibliography_and_spec(self):
        spec = set(json.loads((PKG / "references_spec.json").read_text(encoding="utf-8")))
        entries = set(re.findall(r"^@\w+\{([^,]+),", (PKG / "latex/references_mssp.bib").read_text(encoding="utf-8"), flags=re.M))
        self.assertEqual(self.cited, spec, "no orphan or unverified references")
        self.assertEqual(self.cited, entries)

    def test_doi_syntax_and_crossref_cache(self):
        spec = json.loads((PKG / "references_spec.json").read_text(encoding="utf-8"))
        for key, item in spec.items():
            if "doi" in item:
                self.assertRegex(item["doi"], self.bb.DOI_PATTERN, key)
                self.assertTrue(self.bb.cache_path(item["doi"]).exists(), f"{key}: Crossref record not cached")
            else:
                self.assertIn("url", item["manual"]["fields"], f"{key}: manual entry needs a URL")
        bib = (PKG / "latex/references_mssp.bib").read_text(encoding="utf-8")
        self.assertNotIn("doi.org/https", bib)

    def test_bibliography_check_report_is_clean(self):
        report = (PKG / "literature_evidence/bibliography_check.csv").read_text(encoding="utf-8")
        statuses = [line.rsplit(",", 1)[-1] for line in report.splitlines()[1:]]
        self.assertTrue(statuses and all(s in ("ok", "manual") for s in statuses), statuses)

    def test_reference_audit_covers_every_cited_reference(self):
        audit = (PKG / "reference_audit.csv").read_text(encoding="utf-8")
        for key in self.cited:
            label = f"[{key[3:]}]" if key.startswith("ref") else f"[{key}]"
            self.assertIn(label, audit, f"{label} missing from reference_audit.csv")


class LayoutAndRendering(unittest.TestCase):
    def test_no_raw_markdown_or_placeholders(self):
        body = MAIN_TEX.read_text(encoding="utf-8").split(r"\begin{document}", 1)[1]
        for token in ("**", "[N", "## ", "[Author", "TODO"):
            self.assertNotIn(token, body, token)
        self.assertIsNone(re.search(r"\{\{[A-Z_]+\}\}", body), "unfilled placeholder")
        text = pdf_text(MAIN_PDF)
        for token in ("**", "{{", "[N", "\\cite", "\\textbf", "??", "[Author", "TODO", "\ufffd"):
            self.assertNotIn(token, text, token)

    def test_figures_and_tables_included_once(self):
        builder = load("build_latex")
        tex = MAIN_TEX.read_text(encoding="utf-8")
        for name in builder.FIGURES.values():
            self.assertEqual(tex.count(f"../figures/{name}.pdf"), 1, name)
        for name in builder.TABLES.values():
            self.assertEqual(tex.count(f"../tables/{name}.tex"), 1, name)

    def test_every_bibliography_entry_printed_once(self):
        references = pdf_text(MAIN_PDF).rsplit("References", 1)[1]
        numbers = re.findall(r"^\s*(?:\d+\s+)?\[(\d+)\]", references, flags=re.M)
        cited = load("build_bibliography").cited_keys(DRAFT.read_text(encoding="utf-8"))
        self.assertEqual(len(set(numbers)), len(cited))

    def test_heading_numbers_match_markdown(self):
        text = flat(pdf_text(MAIN_PDF))
        headings = re.findall(r"^#{2,4} (\d+(?:\.\d+)*)\.? (.+)$", DRAFT.read_text(encoding="utf-8"), flags=re.M)
        self.assertGreater(len(headings), 30)
        for number, title in headings:
            self.assertIn(f"{number}. {title.strip()}", text, f"heading {number} {title}")

    def test_symbols_render(self):
        text = pdf_text(MAIN_PDF)
        for symbol in ("α", "κ", "hs = 0", "%", "−"):
            self.assertIn(symbol, text, symbol)

    def test_layout_log_is_clean(self):
        log = (PKG / "latex/main.log").read_text(encoding="utf-8", errors="replace")
        self.assertNotIn("Float(s) lost", log)
        self.assertNotRegex(log, r"(Citation|Reference) `[^']+' on page \d+ undefined")
        widths = [float(w) for w in re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\)", log)]
        self.assertTrue(all(w < 15 for w in widths), widths)

    def test_figure_pdfs_are_vector_with_embedded_fonts(self):
        for pdf in sorted((PKG / "figures").glob("*.pdf")):
            fonts = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True, check=True).stdout.splitlines()[2:]
            self.assertTrue(fonts, pdf.name)
            self.assertTrue(all(" yes " in f.split("  ", 1)[1] for f in fonts), f"{pdf.name}: font not embedded")

    def test_supplement_tables_cited_and_numbered(self):
        draft = DRAFT.read_text(encoding="utf-8")
        part_a = SUPP_TEX.read_text(encoding="utf-8").split(r"\section*{Part B", 1)[0]
        n_tables = part_a.count(r"\begin{longtable}")
        self.assertEqual(part_a.count(r"\caption{"), n_tables)
        self.assertIn(r"\renewcommand{\thetable}{S\arabic{table}}", part_a)
        self.assertIn(f"Tables S1–S{n_tables}", draft)
        text = pdf_text(SUPP_PDF)
        self.assertIn(f"Table S{n_tables}:", text)


class Consistency(unittest.TestCase):
    def test_title_consistent_across_documents(self):
        title = draft_title()
        for path in (MAIN_TEX, SUPP_TEX, COVER_TXT, RELEASE_NOTES, CHECKLIST, FILES_DOC):
            self.assertIn(title, flat(path.read_text(encoding="utf-8")), path.name)

    def test_author_metadata_consistent(self):
        author = load("build_latex").AUTHOR
        for path in (MAIN_TEX, COVER_TXT):
            text = path.read_text(encoding="utf-8")
            for field in ("name", "email", "orcid"):
                self.assertIn(author[field], text, f"{path.name}: {field}")
        self.assertIn(f"https://orcid.org/{author['orcid']}", CITATION.read_text(encoding="utf-8"))
        zenodo = json.loads(ZENODO.read_text(encoding="utf-8"))
        self.assertEqual(zenodo["creators"][0]["orcid"], author["orcid"])

    def test_cover_letter_is_one_page_without_declarations(self):
        self.assertEqual(pdf_pages(COVER_PDF), 1)
        text = COVER_TXT.read_text(encoding="utf-8").lower()
        for forbidden in ("grant", "funding", "competing interest", "suggested reviewer"):
            self.assertNotIn(forbidden, text)
        self.assertIn("not under consideration elsewhere", text)

    def test_declarations_exported_from_the_draft(self):
        draft = DRAFT.read_text(encoding="utf-8")
        builder = load("build_latex")
        for heading, name in builder.DECLARATIONS.items():
            section = draft.split("## " + heading + "\n", 1)[1].split("\n## ", 1)[0].strip()
            section = re.sub(r"\*\*([^*]+)\*\*", r"\1", section)
            exported = (PKG / "declarations" / name).read_text(encoding="utf-8")
            self.assertEqual(exported, heading + "\n\n" + section + "\n", name)
        ai = draft.split("## Declaration of generative AI", 1)[1]
        self.assertIn("takes full responsibility", ai)
        self.assertIn("Claude Opus 5.5", ai)

    def test_release_metadata_prepared_not_published(self):
        notes = RELEASE_NOTES.read_text(encoding="utf-8")
        self.assertIn("prepared, not published", notes.lower())
        self.assertIn("version: 1.1.0", CITATION.read_text(encoding="utf-8"))
        zenodo = json.loads(ZENODO.read_text(encoding="utf-8"))
        for field in ("title", "upload_type", "description", "creators", "license", "version", "keywords"):
            self.assertIn(field, zenodo, field)
        self.assertEqual(zenodo["version"], "1.1.0")
        tags = subprocess.run(["git", "tag", "--list", "v1.1.0"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        self.assertEqual(tags, "", "v1.1.0 must not be tagged before the author approves the release")

    def test_upload_bundle_matches_the_documented_file_list(self):
        documented = set(re.findall(r"`(submission_bundle/[^`]+)`", FILES_DOC.read_text(encoding="utf-8")))
        manifest = {"submission_bundle/" + line.split("  ", 1)[1]
                    for line in (PKG / "submission_bundle/UPLOAD_MANIFEST.txt").read_text(encoding="utf-8").splitlines()}
        top_level = {m for m in manifest if "/" not in m[len("submission_bundle/"):]}
        self.assertTrue(top_level <= documented, sorted(top_level - documented))


class FrozenBoundaries(unittest.TestCase):
    def test_frozen_tags_exist(self):
        tags = set(git("tag", "--list").stdout.split())
        for tag in FROZEN_TAGS:
            self.assertIn(tag, tags)

    def test_frozen_baseline_manifest_verifies(self):
        result = subprocess.run(["sha256sum", "-c", "--quiet", "docs/mssp/frozen_baseline.sha256"], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pre_extension_packages_are_unchanged(self):
        # paper/mssp literature records (reference audit, novelty positioning, full-text quotes) received one additive
        # extension commit (e6b6a85); the pre-extension manuscript sources and every built output are unchanged.
        for path in ("paper/mssp/manuscript_mssp_draft.md", "paper/mssp/latex", "paper/mssp/supplement",
                     "paper/mssp/submission_bundle", "paper/mssp/figures", "paper/mssp/tables", "paper/mssp/cover_letter",
                     "paper/mssp/declarations", "paper/ress", "paper/submission", "results/final_validation",
                     "results/confirmation_ds03", "results/mssp_mitigation", "results/mssp_adversarial"):
            result = git("diff", "--quiet", "mssp-pre-extension-2026-09-28", "HEAD", "--", path)
            self.assertEqual(result.returncode, 0, f"{path} differs from the pre-extension tag")
            self.assertEqual(git("diff", "--quiet", "--", path).returncode, 0, f"{path} has uncommitted changes")


if __name__ == "__main__":
    unittest.main()
