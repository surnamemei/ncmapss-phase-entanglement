"""Create a neutral, clean manuscript PDF from the frozen submission package.

Only specified editorial replacements, bibliography display, and page composition
are changed. The existing main figures, tables, and numerical text are reused.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import build_pdf_draft as base
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    BaseDocTemplate, Frame, FrameBreak, KeepTogether, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from pypdf import PdfReader


ROOT = base.ROOT
PAPER = base.PAPER
SOURCE = PAPER / "manuscript_submission.md"
CLEAN_MD = PAPER / "manuscript_clean.md"
CLEAN_LATEX = PAPER / "latex_clean"
PDF = PAPER / "output/NCMAPSS_Flight_Phase_Manuscript_Clean.pdf"
LOG = PAPER / "output/NCMAPSS_Flight_Phase_Manuscript_Clean.log"
DOI_LABEL = "doi: "
REF_TYPES = {
    1: ("article", "Data"),
    2: ("article", "International Journal of Rotating Machinery"),
    3: ("article", "Aerospace Science and Technology"),
    4: ("inproceedings", "Vertical Flight Society Forum 62"),
    5: ("article", "Aerospace"),
    6: ("article", "Journal of Aerospace Engineering"),
    7: ("article", "International Journal of Prognostics and Health Management"),
    8: ("article", "Mechanical Systems and Signal Processing"),
    9: ("article", "Mathematics"),
    10: ("misc", "arXiv preprint"),
    11: ("inproceedings", "PHM Society European Conference"),
    12: ("article", "Safety Science"),
}


def once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"Expected exactly one editorial target ({count}): {old[:90]}")
    return text.replace(old, new)


def reference_link(line: str, number: int) -> tuple[str, str]:
    label = "[Author manuscript](" if number == 10 else "[Publisher]("
    index = line.rfind(label)
    if index < 0 or not line.endswith(")."):
        raise ValueError(f"Unexpected approved reference link: [{number}]")
    return line[:index].rstrip(), line[index + len(label):-2]


def clean_references(text: str) -> tuple[str, list[dict[str, str]]]:
    records: list[dict[str, str]] = []
    lines: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^\[(\d+)\] (.*)$", line)
        if not match:
            lines.append(line)
            continue
        number = int(match.group(1))
        if number != len(records) + 1 or number not in REF_TYPES:
            raise ValueError("Reference numbering is not consecutive 1–12")
        prefix, url = reference_link(line, number)
        if number == 10:
            if url != "https://arxiv.org/abs/2607.19380" or "preprint" not in prefix:
                raise ValueError("Preprint reference changed unexpectedly")
            final = prefix + " arXiv: [2607.19380](" + url + ")."
            identifier = "2607.19380"
        else:
            if not url.startswith("https://doi.org/"):
                raise ValueError(f"Reference [{number}] lacks verified DOI URL")
            identifier = url.removeprefix("https://doi.org/")
            final = prefix + " " + DOI_LABEL + "[" + identifier + "](" + url + ")."
        title_match = re.search(r"“([^”]+)”", line)
        if not title_match:
            raise ValueError(f"Reference [{number}] title missing")
        records.append({
            "number": str(number), "original": line, "clean": final,
            "url": url, "identifier": identifier,
            "title": title_match.group(1).rstrip(","),
            "author": line[len(f"[{number}] "):title_match.start()].rstrip(" ,"),
            "year": re.findall(r"\b(?:19|20)\d{2}\b", prefix)[-1],
            "entry_type": REF_TYPES[number][0], "venue": REF_TYPES[number][1],
        })
        lines.append(final)
    if len(records) != 12:
        raise ValueError("Expected 12 verified references")
    return "\n".join(lines) + "\n", records


def clean_manuscript() -> tuple[str, list[dict[str, str]], list[str]]:
    original = SOURCE.read_text(encoding="utf-8")
    text = original
    changes: list[str] = []
    replacements = [
        (
            "Variation with operating context can therefore alter healthy anomaly scores even when health state is unchanged",
            "Variation with operating context may therefore alter healthy anomaly scores even when health state is unchanged.",
            "Changed 'can therefore alter' to the requested empirical 'may therefore alter'.",
        ),
        (
            "However, the representative work above rarely makes the stability of nominal pooled healthy FPR calibration across normal full-flight phases its direct, held-out audit target.",
            "However, the representative work above does not make phase stability of a nominal pooled healthy-FPR calibration its primary held-out evaluation target.",
            "Narrowed the related-work gap wording to a primary held-out evaluation target.",
        ),
        ("### C. Cross-Detector Replication", "### C. Consistency Across Three Detector Implementations", "Renamed Results IV-C."),
        ("### B. Why Operating-Condition Correction Was Insufficient", "### B. Sensitivity to Operating-Condition Correction", "Renamed Discussion V-B."),
        (
            "the phase-wise row FPRs differed on DS02 and DS03",
            "the phase-wise healthy row-level FPRs differed on DS02 and DS03",
            "Standardized the Discussion's healthy row-level FPR terminology.",
        ),
    ]
    for old, new, description in replacements:
        text = once(text, old, new)
        changes.append(description)
    text = once(
        text,
        "The aggregate may satisfy its nominal target while climb, cruise, and descent have materially different healthy false-positive rates (FPRs), interpreted here as healthy false-alarm rates.",
        "The aggregate may satisfy its nominal target while climb, cruise, and descent have materially different healthy false-positive rates. Healthy false-positive rate (FPR) is interpreted here as the healthy false-alarm rate.",
    )
    changes.append("Defined healthy false-positive rate (FPR) once as the healthy false-alarm rate.")
    # The added period precedes two intact supporting citations.
    text = once(text, "unchanged. [2]", "unchanged [2]")
    text = once(
        text,
        "unchanged [2](https://doi.org/10.1155/2011/942576), [10](https://arxiv.org/abs/2607.19380).",
        "unchanged. [2](https://doi.org/10.1155/2011/942576), [10](https://arxiv.org/abs/2607.19380).",
    )
    text, records = clean_references(text)
    changes.append("Replaced generic bibliography link labels with the 11 verified DOIs and the verified arXiv identifier; bibliographic fields otherwise retained.")
    old_captions = re.findall(r"(?m)^\*\*Fig\. \d+\..*$", text)
    if len(old_captions) != 4:
        raise ValueError("Expected four existing main figure captions")
    new_captions = [
        "**Fig. 1. Discovery-to-confirmation study design.** DS02 discovery and exploratory robustness analyses preceded protocol freeze; DS03 is an independent confirmatory subset evaluated once after freeze. No DS03 official-test access occurred before freeze.",
        "**Fig. 2. DS02 exploratory healthy row-level FPR at the nominal 1% pooled calibration target.** PCA is a single run; Isolation Forest and the causal LSTM sequence-reconstruction network are arithmetic three-seed means. Bars show pooled-threshold phase FPR, not cross-phase transfer FPR. Figures 2 and 4 use the same vertical scale to support direct visual comparison.",
        "**Fig. 3. DS02 exploratory PCA cross-phase threshold transfer at the nominal 1% target.** Calibration phase is shown vertically and healthy audit phase horizontally. Each cell is the held-out transfer FPR after phase-specific calibration, not pooled phase FPR. Diagonal cells are same-phase audit FPRs and are not constrained to exactly 1%.",
        "**Fig. 4. DS03 frozen confirmatory healthy row-level FPR at the nominal 1% pooled calibration target.** PCA is a single run; Isolation Forest and the causal LSTM sequence-reconstruction network are arithmetic three-seed means. Bars show pooled-threshold phase FPR, not cross-phase transfer FPR. The vertical scale matches Fig. 2; no seed-mean confidence interval was executed.",
    ]
    for old, new in zip(old_captions, new_captions):
        text = once(text, old, new)
    changes.append("Shortened all four captions while retaining dataset status, threshold type, seed aggregation, equal scale, and the Fig. 3 diagonal-cell qualification.")
    text = once(
        text,
        "*Note:* 3/42 per-engine detector/seed directional rows were exceptions, all from LSTM seed 2. All three individual LSTM descent-minus-cruise bootstrap intervals include zero. Individual-seed interval tables belong in the supplement; an arithmetic seed-mean interval was not executed. Cross-phase transfer FPR is not tabulated here.",
        "*Note:* 3 of 42 per-engine detector/seed directional rows were exceptions, all associated with LSTM seed 2. All three individual LSTM descent-minus-cruise bootstrap intervals include zero. No confidence interval is reported for arithmetic seed means because no seed-mean bootstrap interval was executed. Individual-seed interval tables belong in the supplement; cross-phase transfer FPR is not tabulated here.",
    )
    changes.append("Expanded the Table III caveat to state explicitly that no seed-mean bootstrap interval was executed; retained the 3-of-42 and zero-containing LSTM interval findings.")
    body = text.split("## References\n", 1)[0]
    cited = {int(x) for x in re.findall(r"\[(\d+)\]\(https?://", body)}
    if cited != set(range(1, 13)):
        raise ValueError(f"Cited-reference set differs from bibliography: {sorted(cited)}")
    if "The detectors are unsupervised with respect to fault labels; supplied health-state annotations are used only to select healthy samples for retrospective fitting, calibration, and evaluation." not in text:
        raise ValueError("Required early unsupervised clarification missing")
    for token in ("600-epoch ceiling", "simulated", "retrospective", "fault recall", "detection delay"):
        if token not in text:
            raise ValueError(f"Required scientific qualification missing: {token}")
    CLEAN_MD.write_text(text, encoding="utf-8")
    return text, records, changes


def clean_parts(text: str) -> tuple[str, str, list[str], list[str]]:
    main, exhibits = text.split("## Main Figures\n", 1)
    match = re.search(r"(?ms)^## Abstract\n\n(.*?)\n\n## I\. Introduction", main)
    if not match:
        raise ValueError("Abstract boundary missing")
    abstract = match.group(1)
    body = main[main.index("## I. Introduction"):]
    captions = re.findall(r"(?m)^\*\*Fig\. \d+\..*$", exhibits)
    tables = [(PAPER / "tables" / name).read_text(encoding="utf-8") for name in base.TABLE_NAMES]
    # The numerical table files remain authoritative; only the Table III note is editorially expanded.
    tables[2] = tables[2].replace(
        "*Note:* 3/42 per-engine detector/seed directional rows were exceptions, all from LSTM seed 2. All three individual LSTM descent-minus-cruise bootstrap intervals include zero. Individual-seed interval tables belong in the supplement; an arithmetic seed-mean interval was not executed. Cross-phase transfer FPR is not tabulated here.",
        "*Note:* 3 of 42 per-engine detector/seed directional rows were exceptions, all associated with LSTM seed 2. All three individual LSTM descent-minus-cruise bootstrap intervals include zero. No confidence interval is reported for arithmetic seed means because no seed-mean bootstrap interval was executed. Individual-seed interval tables belong in the supplement; cross-phase transfer FPR is not tabulated here.",
    )
    if len(captions) != 4 or "3 of 42" not in tables[2]:
        raise ValueError("Clean figure/table presentation did not materialize")
    return abstract, body, captions, tables


def bibtex(records: list[dict[str, str]]) -> str:
    entries = []
    for record in records:
        author = record["author"].replace("*et al.*", "and others")
        author = author.replace(", and ", " and ").replace(", ", " and ")
        fields = [
            ("author", author),
            ("title", record["title"]),
            ("year", record["year"]),
        ]
        kind = record["entry_type"]
        if kind == "article":
            fields.append(("journal", record["venue"]))
        elif kind == "inproceedings":
            fields.append(("booktitle", record["venue"]))
        else:
            fields.append(("note", "Preprint; arXiv:2607.19380"))
        if kind != "misc":
            fields.append(("doi", record["identifier"]))
        fields.append(("url", record["url"]))
        lines = [f"@{kind}{{ref{record['number']},"]
        for field, value in fields:
            escaped = value.replace("&", r"\&").replace("%", r"\%")
            lines.append(f"  {field} = {{{escaped}}},")
        lines[-1] = lines[-1].rstrip(",")
        entries.append("\n".join(lines + ["}"]))
    return "\n\n".join(entries) + "\n"


def clean_latex(abstract: str, body: str, captions: list[str], tables: list[str], records: list[dict[str, str]]) -> None:
    base.LATEX = CLEAN_LATEX
    base.create_latex(abstract, body, captions, tables)
    tex_path = CLEAN_LATEX / "main.tex"
    tex = tex_path.read_text(encoding="utf-8")
    tex = tex.replace(
        r"\documentclass[10pt,conference]{IEEEtran}",
        r"\documentclass[10pt,twocolumn]{article}" + "\n" +
        r"\usepackage[letterpaper,left=0.68in,right=0.68in,top=0.72in,bottom=0.72in,columnsep=0.20in]{geometry}",
    )
    tex, author_count = re.subn(
        r"(?m)^\\author\{.*$",
        lambda _: r"\author{Jinghang Mei\\School of Electrical and Computer Engineering\\The University of Sydney\\Sydney, Australia}" + "\n" + r"\date{}",
        tex,
        count=1,
    )
    if author_count != 1:
        raise ValueError("Expected exactly one LaTeX author block")
    tex = tex.replace(r"\begin{IEEEkeywords}", r"\par\smallskip\noindent\textbf{Keywords---} ")
    tex = tex.replace(r"\end{IEEEkeywords}", "")
    figures = re.findall(r"\\begin\{figure\*\}\[t\].*?\\end\{figure\*\}", tex, flags=re.S)
    if len(figures) != 4:
        raise ValueError("LaTeX source lacks exactly four figures")
    for figure in figures:
        tex = tex.replace(figure, "", 1)
    targets = (
        r"\subsection{Healthy-State and Flight-Phase Definitions}\label{healthy-state-and-flight-phase-definitions}",
        r"\subsection{Cluster-Aware Uncertainty and Heterogeneity}\label{cluster-aware-uncertainty-and-heterogeneity}",
        r"\section{Discussion}\label{discussion}",
        r"\subsection{Implications for Anomaly-Detector Evaluation}\label{implications-for-anomaly-detector-evaluation}",
    )
    for target, figure in zip(targets, figures):
        tex = once(tex, target, target + "\n" + figure)
    if "Email: [to be added]" in tex or "IEEEauthor" in tex or "IEEEkeywords" in tex:
        raise ValueError("Neutral LaTeX source retains a placeholder or IEEE template macro")
    tex_path.write_text(tex, encoding="utf-8")
    (CLEAN_LATEX / "references.bib").write_text(bibtex(records), encoding="utf-8")


class NeutralDoc(BaseDocTemplate):
    def __init__(self, filename: Path):
        super().__init__(str(filename), pagesize=letter, leftMargin=40, rightMargin=40,
                         topMargin=42, bottomMargin=39, title=base.TITLE,
                         author="Jinghang Mei", pageCompression=1, allowSplitting=1)
        page_w, page_h = letter
        usable_w = page_w - 80
        gap = 17
        column_w = (usable_w - gap) / 2

        def columns(upper: float, prefix: str) -> list[Frame]:
            height = page_h - 42 - 39 - upper
            return [
                Frame(40, 39, column_w, height, id=prefix + "_left", leftPadding=0, rightPadding=4, topPadding=0, bottomPadding=0),
                Frame(40 + column_w + gap, 39, column_w, height, id=prefix + "_right", leftPadding=4, rightPadding=0, topPadding=0, bottomPadding=0),
            ]

        title_h = 278
        title = Frame(40, page_h - 42 - title_h, usable_w, title_h, id="title", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        templates = [PageTemplate(id="first", frames=[title, *columns(title_h, "first")], onPage=self.decorate)]
        templates.append(PageTemplate(id="body", frames=columns(0, "body"), onPage=self.decorate))
        figure_heights = (235, 356, 424, 356)
        for n, height in enumerate(figure_heights, 1):
            figure = Frame(40, page_h - 42 - height, usable_w, height, id=f"figure{n}", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
            templates.append(PageTemplate(id=f"figure{n}", frames=[figure, *columns(height, f"figure{n}")], onPage=self.decorate))
        wide = Frame(40, 39, usable_w, page_h - 42 - 39, id="wide", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        templates.append(PageTemplate(id="tables", frames=[wide], onPage=self.decorate))
        self.addPageTemplates(templates)

    def decorate(self, canv, doc) -> None:
        canv.saveState()
        canv.setFont("DVS", 7)
        canv.setFillColor(colors.HexColor("#444B55"))
        canv.drawCentredString(letter[0] / 2, 22, str(doc.page))
        canv.restoreState()


def clean_table(content: str, index: int, sty: dict) -> list:
    caption, rows, note = base.split_table(content)
    if index == 0:
        widths = [110, 211, 211]
    elif index == 1:
        widths = [130, 50, 50, 50, 57, 62, 62, 71]
    else:
        widths = [130, 52, 52, 52, 58, 66, 58, 64]
    if index in (1, 2):
        for row in rows[1:]:
            if row[0] == "Causal LSTM reconstruction (seed mean)":
                row[0] = "Causal LSTM (seed mean)"
    cell_style = sty["cell"] if index == 0 else sty["cell_small"]
    cells = [[Paragraph(base.inline_pdf(cell), cell_style) for cell in row] for row in rows]
    table = Table(cells, colWidths=widths, repeatRows=1, hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EDF2")),
        ("LINEABOVE", (0, 0), (-1, 0), 0.65, colors.HexColor("#4C5865")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.65, colors.HexColor("#4C5865")),
        ("LINEBELOW", (0, -1), (-1, -1), 0.65, colors.HexColor("#4C5865")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFB")]),
    ]))
    result = [Paragraph(base.inline_pdf(caption), sty["table_caption"]), table]
    if note:
        result.append(Paragraph(base.inline_pdf(note), sty["note"]))
    return result


def clean_pdf(abstract: str, body: str, captions: list[str], tables: list[str]) -> None:
    base.register_fonts()
    sty = base.styles()
    sty["body"].alignment = TA_LEFT
    sty["ref"].leading = 8.15
    sty["ref"].spaceAfter = 2.5
    sty["cell_small"].fontSize = 6.6
    sty["cell_small"].leading = 8.6
    before_refs, refs = base.references_from_body(body)
    story: list = [
        NextPageTemplate("body"),
        Paragraph(html.escape(base.TITLE), sty["title"]),
        Paragraph("<br/>".join(html.escape(line) for line in base.AUTHOR if not line.startswith("Email:")), sty["author"]),
        Paragraph("<b>Abstract—</b> " + base.inline_pdf(abstract), sty["abstract"]),
        Paragraph("<b>Keywords—</b> " + html.escape(base.KEYWORDS), sty["keywords"]),
        FrameBreak(),
    ]
    hooks = {
        "### C. Healthy-State and Flight-Phase Definitions": 0,
        "### E. Cluster-Aware Uncertainty and Heterogeneity": 1,
        "## V. Discussion": 2,
        "### C. Implications for Anomaly-Detector Evaluation": 3,
    }
    used_hooks: set[int] = set()
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            story.append(Paragraph(base.inline_pdf(" ".join(paragraph)), sty["body"]))
            paragraph.clear()

    for line in before_refs.splitlines():
        if line in hooks:
            flush()
            index = hooks[line]
            if index in used_hooks:
                raise ValueError("Figure placement hook duplicated")
            used_hooks.add(index)
            story.extend([NextPageTemplate(f"figure{index + 1}"), PageBreak()])
            width = (520, 520, 400, 520)[index]
            image = base.scaled_image(PAPER / "figures" / f"{base.FIGURE_STEMS[index]}.png", width)
            story.extend([image, Paragraph(base.inline_pdf(captions[index]), sty["caption"]), FrameBreak(), NextPageTemplate("body")])
        if line.startswith("## "):
            flush()
            story.append(Paragraph(html.escape(line[3:]), sty["section"]))
        elif line.startswith("### "):
            flush()
            story.append(Paragraph(html.escape(line[4:]), sty["subsection"]))
        elif re.match(r"^\d+\. ", line):
            flush()
            story.append(Paragraph(base.inline_pdf(line), sty["body"]))
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.strip())
    flush()
    if used_hooks != set(range(4)):
        raise ValueError("Not all four figures were placed")
    story.append(Paragraph("References", sty["section"]))
    for line in refs:
        story.append(Paragraph(base.inline_pdf(line), sty["ref"]))
    story.extend([NextPageTemplate("tables"), PageBreak()])
    for index, content in enumerate(tables):
        story.append(KeepTogether(clean_table(content, index, sty)))
        if index < len(tables) - 1:
            story.append(Spacer(1, 16))
    PDF.parent.mkdir(parents=True, exist_ok=True)
    NeutralDoc(PDF).build(story)


def main() -> None:
    text, records, changes = clean_manuscript()
    abstract, body, captions, tables = clean_parts(text)
    clean_latex(abstract, body, captions, tables, records)
    clean_pdf(abstract, body, captions, tables)
    pages = len(PdfReader(str(PDF)).pages)
    LOG.write_text(json.dumps({
        "source": "paper/manuscript_submission.md",
        "clean_manuscript": "paper/manuscript_clean.md",
        "latex_source": "paper/latex_clean/main.tex",
        "bibliography": "paper/latex_clean/references.bib",
        "pdf": "paper/output/NCMAPSS_Flight_Phase_Manuscript_Clean.pdf",
        "renderer": "ReportLab fallback; no local TeX engine on PATH",
        "latex_compiled": False,
        "pages": pages,
        "editorial_changes": changes,
        "reference_entries_changed": [int(r["number"]) for r in records],
        "scientific_content_or_numeric_results_changed": False,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Built {PDF} ({pages} pages)")


if __name__ == "__main__":
    main()
