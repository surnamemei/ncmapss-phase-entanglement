"""Manuscript and submission-package QA for the MSSP paper (paper/mssp/).

No N-CMAPSS data are read. The tests check the committed manuscript sources, the built PDFs, the
bibliography, the supplement, the cover letter and the frozen-evidence boundaries.
"""

import hashlib
import json
import re
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "paper/mssp"
sys.path.insert(0, str(PKG))

import build_bibliography as bb  # noqa: E402
import build_latex as bl  # noqa: E402
import verify_draft_numbers as vd  # noqa: E402

DRAFT = PKG / "manuscript_mssp_draft.md"
MAIN_TEX, MAIN_PDF = PKG / "latex/main.tex", PKG / "latex/main.pdf"
BIB = PKG / "latex/references_mssp.bib"
SUPP_TEX, SUPP_PDF = PKG / "supplement/supplement.tex", PKG / "supplement/supplement.pdf"
COVER_TXT, COVER_PDF = PKG / "cover_letter/cover_letter.txt", PKG / "cover_letter/cover_letter.pdf"
PAGE_LIMIT = 25
RESS_TAG = "ress-submission-2026-09-25"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pdf_text(path):
    return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout


def pdf_pages(path):
    info = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", info).group(1))


def draft_title():
    return re.search(r"^# (.+)$", DRAFT.read_text(encoding="utf-8"), flags=re.M).group(1).strip()


class NumbersAndWording(unittest.TestCase):
    def test_every_cited_value_rederives_and_wording_rules_hold(self):
        result = subprocess.run([sys.executable, str(PKG / "verify_draft_numbers.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
        self.assertIn("text checks passed", result.stdout)

    def test_limits(self):
        text = DRAFT.read_text(encoding="utf-8")
        abstract = vd.section(text, "## Abstract", "**Keywords:**")
        self.assertLessEqual(len(abstract.split()), 245)
        keywords = [k for k in vd.section(text, "**Keywords:**").splitlines()[0].split(";") if k.strip()]
        self.assertLessEqual(len(keywords), 6, "MSSP: a maximum of 6 keywords")
        highlights = (PKG / "latex/highlights.txt").read_text(encoding="utf-8").splitlines()
        self.assertTrue(3 <= len(highlights) <= 5)
        self.assertTrue(all(len(h) <= 85 for h in highlights))

    def test_highlights_word_file_matches_text(self):
        with zipfile.ZipFile(PKG / "latex/Highlights.docx") as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        for line in (PKG / "latex/highlights.txt").read_text(encoding="utf-8").splitlines():
            self.assertIn(line.replace("&", "&amp;"), xml)


class References(unittest.TestCase):
    def test_cited_keys_equal_bibliography_and_spec(self):
        cited = bb.cited_keys(DRAFT.read_text(encoding="utf-8"))
        spec = set(json.loads((PKG / "references_spec.json").read_text(encoding="utf-8")))
        entries = set(re.findall(r"^@\w+\{([^,]+),", BIB.read_text(encoding="utf-8"), flags=re.M))
        self.assertEqual(cited, spec, "no orphan or unverified references")
        self.assertEqual(cited, entries)

    def test_doi_syntax_and_crossref_cache(self):
        spec = json.loads((PKG / "references_spec.json").read_text(encoding="utf-8"))
        for key, item in spec.items():
            if "doi" in item:
                self.assertRegex(item["doi"], bb.DOI_PATTERN, key)
                self.assertTrue(bb.cache_path(item["doi"]).exists(), f"{key}: Crossref record not cached")
            else:
                self.assertIn("url", item["manual"]["fields"], f"{key}: manual entry needs a URL")
        bib = BIB.read_text(encoding="utf-8")
        self.assertNotIn("doi.org/https", bib)
        for doi in re.findall(r"doi = \{([^}]*)\}", bib):
            self.assertRegex(doi, bb.DOI_PATTERN)

    def test_bibliography_check_report_is_clean(self):
        report = (PKG / "literature_evidence/bibliography_check.csv").read_text(encoding="utf-8")
        statuses = [line.rsplit(",", 1)[-1] for line in report.splitlines()[1:]]
        self.assertTrue(all(s in ("ok", "manual") for s in statuses), statuses)

    def test_reference_audit_covers_every_cited_reference(self):
        audit = (PKG / "reference_audit.csv").read_text(encoding="utf-8")
        for key in bb.cited_keys(DRAFT.read_text(encoding="utf-8")):
            label = f"[{key[3:]}]" if key.startswith("ref") else f"[{key}]"
            self.assertIn(label, audit, f"{label} missing from reference_audit.csv")


class BuiltManuscript(unittest.TestCase):
    def test_latex_matches_markdown_source(self):
        document, highlights = bl.convert(DRAFT.read_text(encoding="utf-8"))
        self.assertEqual(document, MAIN_TEX.read_text(encoding="utf-8"), "main.tex is stale; rerun build_latex.py")

    def test_no_raw_markdown_or_placeholders(self):
        tex = MAIN_TEX.read_text(encoding="utf-8")
        body = tex.split(r"\begin{document}", 1)[1]
        for token in ("**", "[N", "## ", "[Author", "TODO"):
            self.assertNotIn(token, body, token)
        self.assertIsNone(re.search(r"\{\{[A-Z_]+\}\}", body), "unfilled placeholder")
        self.assertIsNone(re.search(r"(?<!`)`[^`'\n]+`(?!`)", body), "markdown code span left in LaTeX")
        text = pdf_text(MAIN_PDF)
        for token in ("**", "{{", "[N", "\\cite", "\\textbf", "??", "[Author", "TODO"):
            self.assertNotIn(token, text, token)

    def test_figures_and_tables_included_once(self):
        tex = MAIN_TEX.read_text(encoding="utf-8")
        for name in bl.FIGURES.values():
            self.assertEqual(tex.count(f"../figures/{name}.pdf"), 1, name)
            self.assertTrue((PKG / "figures" / f"{name}.pdf").exists(), name)
        for name in bl.TABLES.values():
            self.assertEqual(tex.count(f"../tables/{name}.tex"), 1, name)

    def test_citations_resolve_and_page_limit(self):
        log_path = PKG / "latex/main.log"
        if log_path.exists():
            log = log_path.read_text(encoding="utf-8", errors="replace")
            self.assertNotRegex(log, r"Citation `[^']+' on page \d+ undefined")
            self.assertNotRegex(log, r"Reference `[^']+' on page \d+ undefined")
        references = pdf_text(MAIN_PDF).rsplit("References", 1)[1]
        numbers = re.findall(r"^\s*(?:\d+\s+)?\[(\d+)\]", references, flags=re.M)  # even pages carry line numbers on the left
        cited = bb.cited_keys(DRAFT.read_text(encoding="utf-8"))
        self.assertEqual(len(set(numbers)), len(cited), "every bibliography entry is printed once")
        self.assertLessEqual(pdf_pages(MAIN_PDF), PAGE_LIMIT, "MSSP standard research article: 25 A4 pages")

    def test_heading_numbers_match_markdown(self):
        """Numbered Markdown headings must appear with the same numbers in the PDF (cross-references rely on it)."""
        text = " ".join(pdf_text(MAIN_PDF).split())
        headings = re.findall(r"^#{2,4} (\d+(?:\.\d+)*)\.? (.+)$", DRAFT.read_text(encoding="utf-8"), flags=re.M)
        self.assertGreater(len(headings), 30)
        for number, title in headings:
            self.assertIn(f"{number}. {title.strip()}", text, f"heading {number} {title}")

    def test_symbols_render(self):
        text = pdf_text(MAIN_PDF)
        for symbol in ("α", "κ", "C′", "hs = 0", "%"):
            self.assertIn(symbol, text, symbol)
        self.assertNotIn("\ufffd", text)

    def test_stale_wording_absent_from_pdf(self):
        text = " ".join(pdf_text(MAIN_PDF).split()).lower()
        text = text.rsplit("references", 1)[0]
        for phrase in ("pre-registered", "causal lstm", "fault sensitivity", "reliability engineering & system safety",
                       "mitigation", "limiting factor", "stabiliz"):
            self.assertNotIn(phrase, text, phrase)


class Consistency(unittest.TestCase):
    def test_title_consistent_across_documents(self):
        title = draft_title()
        flat = lambda s: " ".join(s.split())  # noqa: E731
        self.assertIn(title, flat(MAIN_TEX.read_text(encoding="utf-8")))
        self.assertIn(title, flat(SUPP_TEX.read_text(encoding="utf-8")))
        self.assertIn(title, flat(COVER_TXT.read_text(encoding="utf-8")))
        for path in (ROOT / "docs/mssp/FINAL_SUBMISSION_READINESS.md", ROOT / "docs/release/v1.1.0/RELEASE_NOTES.md"):
            if path.exists():
                self.assertIn(title, flat(path.read_text(encoding="utf-8")), path.name)

    def test_author_email_and_orcid_consistent(self):
        author = bl.AUTHOR
        tex = MAIN_TEX.read_text(encoding="utf-8")
        cover = COVER_TXT.read_text(encoding="utf-8")
        cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        for document in (tex, cover):
            self.assertIn(author["name"], document)
            self.assertIn(author["email"], document)
            self.assertIn(author["orcid"], document)
        self.assertIn(f"https://orcid.org/{author['orcid']}", cff)
        self.assertIn("family-names: Mei", cff)

    def test_supplement_numbering_consistent(self):
        tex = SUPP_TEX.read_text(encoding="utf-8")
        tables = len(re.findall(r"\\input\{tables/s\d+_", tex))
        figures = len(re.findall(r"\\begin\{figure\}", tex))
        draft = DRAFT.read_text(encoding="utf-8")
        self.assertIn(f"Tables S1–S{tables} and Figures S1–S{figures}", draft)
        for kind, number in re.findall(r"(Tables?|Figs?\.) (S\d+)", draft):
            limit = tables if kind.startswith("Table") else figures
            self.assertLessEqual(int(number[1:]), limit, f"{kind} {number}")
        for kind, a, b in re.findall(r"(Tables?|Figs?\.) S(\d+)–S(\d+)", draft):
            self.assertLessEqual(int(b), tables if kind.startswith("Table") else figures)

    def test_cover_letter_is_one_page_without_declarations(self):
        self.assertEqual(pdf_pages(COVER_PDF), 1)
        text = COVER_TXT.read_text(encoding="utf-8").lower()
        for forbidden in ("grant", "funding", "competing interest", "suggested reviewer"):
            self.assertNotIn(forbidden, text)
        self.assertIn("not under consideration elsewhere", text)


class Provenance(unittest.TestCase):
    def test_frozen_baseline_unchanged(self):
        for line in (ROOT / "docs/mssp/frozen_baseline.sha256").read_text().splitlines():
            digest, path = line.split(maxsplit=1)
            self.assertEqual(sha256(ROOT / path), digest, path)

    def test_ress_package_unchanged(self):
        result = subprocess.run(["git", "diff", "--quiet", RESS_TAG, "--", "paper/ress", "paper/submission"], cwd=ROOT)
        self.assertEqual(result.returncode, 0, "paper/ress or paper/submission differs from the RESS tag")

    def test_derived_artefacts_are_current(self):
        sidecars = list((PKG / "figures").glob("*.provenance.json")) + list((PKG / "tables").glob("*.provenance.json"))
        sidecars.append(PKG / "supplement/supplement.provenance.json")
        for sidecar in sidecars:
            record = json.loads(sidecar.read_text(encoding="utf-8"))
            for path, digest in record["inputs"].items():
                self.assertEqual(sha256(ROOT / path), digest, f"{sidecar.name}: input {path} changed")
            for path, digest in record["outputs"].items():
                self.assertEqual(sha256(ROOT / path), digest, f"{sidecar.name}: output {path} changed")

    def test_evidence_manifest(self):
        for line in (PKG / "evidence/SHA256SUMS").read_text().splitlines():
            digest, name = line.split(maxsplit=1)
            self.assertEqual(sha256(PKG / "evidence" / name), digest, name)


if __name__ == "__main__":
    unittest.main()
