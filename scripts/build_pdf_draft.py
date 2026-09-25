"""Build a two-column review PDF and an editable LaTeX tree from the frozen paper.

Presentation only: reads the approved submission Markdown, figures, tables, and
reference audit. No analysis CSV, model, threshold, or scientific endpoint is run.
The local PDF renderer is ReportLab because this host has no TeX engine.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, FrameBreak, Image, KeepTogether, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
LATEX = PAPER / "latex"
OUTPUT = PAPER / "output"
PDF = OUTPUT / "NCMAPSS_Flight_Phase_Manuscript_Draft.pdf"
LOG = OUTPUT / "NCMAPSS_Flight_Phase_Manuscript_Draft.log"
SOURCE = PAPER / "manuscript_submission.md"
REFERENCE_AUDIT = PAPER / "reference_audit.md"
TITLE = "Auditing Flight-Phase Dependence in Unsupervised Aero-Engine Anomaly Detection: A Discovery-and-Confirmation Study on N-CMAPSS"
AUTHOR = [
    "Jinghang Mei",
    "School of Electrical and Computer Engineering",
    "The University of Sydney",
    "Sydney, Australia",
    "Email: [to be added]",
]
KEYWORDS = "Aero-engine anomaly detection; N-CMAPSS; false-alarm calibration; flight phases; threshold transfer."
FIGURE_STEMS = (
    "figure_1_study_design",
    "figure_2_ds02_phase_fpr",
    "figure_3_cross_phase_transfer",
    "figure_4_ds03_phase_fpr",
)
TABLE_NAMES = (
    "table_i_dataset_protocol.md",
    "table_ii_ds02_canonical.md",
    "table_iii_ds03_confirmation.md",
)
FIG3_REQUIRED = "Diagonal cells are held-out same-phase audit FPRs and are not constrained to exactly 1%. Values are cross-phase transfer FPRs, not pooled phase FPRs."


def read_inputs() -> tuple[str, str, str, list[str], list[str]]:
    source = SOURCE.read_text(encoding="utf-8")
    audit = REFERENCE_AUDIT.read_text(encoding="utf-8")
    if source.count(TITLE) != 1:
        raise ValueError("Approved working title is missing or duplicated")
    required = (
        "The detectors are unsupervised with respect to fault labels; supplied health-state annotations are used only to select healthy samples for retrospective fitting, calibration, and evaluation.",
        "the pre-specified pooled directional pattern was reproduced.",
        "These results motivate explicit phase-stability auditing alongside aggregate anomaly-detection evaluation under nonstationary operating conditions.",
        "Future work should test the calibration-audit question on real or independently sourced full-flight data and evaluate whether context-aware calibration can reduce phase dependence without compromising fault sensitivity.",
    )
    for sentence in required:
        if sentence not in source:
            raise ValueError(f"Approved wording missing: {sentence[:70]}")
    if "No reference was invented or renumbered" not in audit:
        raise ValueError("Reference audit has not been verified")
    for n in range(1, 13):
        if f"[{n}]" not in audit:
            raise ValueError(f"Reference {n} absent from reference audit")
    main, exhibits = source.split("## Main Figures\n", 1)
    abstract = re.search(r"(?ms)^## Abstract\n\n(.*?)\n\n## I\. Introduction", main)
    if not abstract:
        raise ValueError("Abstract boundary missing")
    body = main[main.index("## I. Introduction"):]
    captions = re.findall(r"(?m)^\*\*Fig\. \d+\..*$", exhibits)
    if len(captions) != 4:
        raise ValueError("Expected exactly four approved figure captions")
    captions[2] += " " + FIG3_REQUIRED
    tables = [(PAPER / "tables" / name).read_text(encoding="utf-8") for name in TABLE_NAMES]
    for text in tables:
        if "<!-- evidence:" not in text:
            raise ValueError("Generated table provenance marker missing")
    return source, abstract.group(1), body, captions, tables


def strip_markdown(text: str) -> str:
    return re.sub(r"\*\*|(?<!\*)\*(?!\*)|`", "", text).strip()


def pandoc_latex(fragment: str) -> str:
    result = subprocess.run(
        ["pandoc", "--from=markdown+tex_math_single_backslash", "--to=latex", "--wrap=none"],
        input=fragment, text=True, capture_output=True, check=True, encoding="utf-8"
    )
    return result.stdout.strip()


def latex_inline(markdown: str) -> str:
    return pandoc_latex(markdown).replace("\n", " ")


def split_table(text: str) -> tuple[str, list[list[str]], str]:
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("<!--")]
    caption = lines[0]
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines if line.startswith("|") and not re.match(r"^\|[ :|\-]+\|$", line)]
    if not rows or len({len(row) for row in rows}) != 1:
        raise ValueError("Malformed approved table")
    note = " ".join(line for line in lines[1:] if not line.startswith("|") and not line.startswith("<!--"))
    return caption, rows, note


def references_from_body(body: str) -> tuple[str, list[str]]:
    before, refs = body.split("## References\n", 1)
    lines = [line for line in refs.splitlines() if line.strip()]
    if len(lines) != 12:
        raise ValueError(f"Expected 12 approved references, found {len(lines)}")
    for n, line in enumerate(lines, 1):
        if not line.startswith(f"[{n}] "):
            raise ValueError("Reference numbering differs from approved manuscript")
    return before, lines


def bib_entry(number: int, line: str) -> str:
    # A lossless draft BibTeX record, not a speculative completion of fields.
    match = re.search(r"\]\((https?://.*)\)\.$", line)
    if not match:
        raise ValueError(f"Approved reference {number} lacks its URL")
    url = match.group(1)
    note = line[len(f"[{number}] "):match.start()].rstrip()
    note = strip_markdown(note).replace("&", r"\&").replace("%", r"\%")
    return f"@misc{{ref{number},\n  note = {{{note}}},\n  url = {{{url}}}\n}}"


def create_latex(abstract: str, body: str, captions: list[str], tables: list[str]) -> None:
    (LATEX / "figures").mkdir(parents=True, exist_ok=True)
    (LATEX / "tables").mkdir(parents=True, exist_ok=True)
    for stem in FIGURE_STEMS:
        for suffix in ("svg", "png"):
            shutil.copyfile(PAPER / "figures" / f"{stem}.{suffix}", LATEX / "figures" / f"{stem}.{suffix}")
    for name, content in zip(TABLE_NAMES, tables):
        (LATEX / "tables" / name).write_text(content, encoding="utf-8")
    body_md, refs = references_from_body(body)
    # The source contains manually numbered headings; IEEEtran will number them.
    clean_md = re.sub(r"(?m)^## [IVX]+\. ", "# ", body_md)
    clean_md = re.sub(r"(?m)^### [A-Z]\. ", "## ", clean_md)
    clean_md = re.sub(r"\[([0-9]+)\]\(https?://[^\s)]+(?:\([^)]*\)[^\s)]*)?\)", r"[\1]", clean_md)
    body_tex = pandoc_latex(clean_md)
    bib = "\n\n".join(bib_entry(n, line) for n, line in enumerate(refs, 1)) + "\n"
    (LATEX / "references.bib").write_text(bib, encoding="utf-8")
    ref_tex = []
    for n, line in enumerate(refs, 1):
        ref_tex.append(f"\\bibitem{{ref{n}}} {latex_inline(line[len(f'[{n}] '):])}")
    figure_tex = []
    for stem, caption in zip(FIGURE_STEMS, captions):
        # The copied SVG is the vector master; PNG is the pdflatex-compatible fallback.
        caption_without_label = re.sub(r"^\*\*Fig\. \d+\. (.*?)\*\*", r"\1", caption)
        figure_tex.append(
            "\\begin{figure*}[t]\n\\centering\n"
            f"\\includegraphics[width=0.94\\textwidth]{{figures/{stem}.png}}\n"
            f"\\caption{{{latex_inline(caption_without_label)}}}\n\\end{{figure*}}"
        )
    table_tex = []
    for index, content in enumerate(tables):
        caption, rows, note = split_table(content)
        if index == 2:
            note = note.replace("3/42", "3 of 42")
        title = re.sub(r"^\*\*Table [IVX]+\. (.*?)\*\*", r"\1", caption)
        title = latex_inline(title)
        headers, data = rows[0], rows[1:]
        if index == 0:
            colspec = r"p{0.20\textwidth}p{0.36\textwidth}p{0.36\textwidth}"
        else:
            colspec = "l" + "r" * (len(headers) - 1)
        render_rows = []
        for cells in [headers, *data]:
            render_rows.append(" & ".join(latex_inline(cell) for cell in cells) + r" \\")
        tabular = "\n".join([r"\hline", render_rows[0], r"\hline", *render_rows[1:], r"\hline"])
        if index == 0:
            inner = f"\\begin{{tabular}}{{{colspec}}}\n{tabular}\n\\end{{tabular}}"
        else:
            inner = f"\\resizebox{{\\textwidth}}{{!}}{{\\begin{{tabular}}{{{colspec}}}\n{tabular}\n\\end{{tabular}}}}"
        table_tex.append(
            "\\begin{table*}[t]\n\\centering\n\\footnotesize\n"
            f"\\caption{{{title}}}\n{inner}\n"
            + (f"\\par\\vspace{{3pt}}\\footnotesize {latex_inline(note)}\n" if note else "")
            + "\\end{table*}"
        )
    preamble = r"""\documentclass[10pt,conference]{IEEEtran}
\usepackage[utf8]{inputenc}
\DeclareUnicodeCharacter{2212}{\ensuremath{-}}
\usepackage{graphicx,amsmath,amssymb,array,booktabs,url,hyperref}
\hypersetup{hidelinks}
\title{TITLE_TOKEN}
\author{\IEEEauthorblockN{Jinghang Mei}\IEEEauthorblockA{School of Electrical and Computer Engineering\\The University of Sydney\\Sydney, Australia\\Email: [to be added]}}
\begin{document}
\maketitle
\begin{abstract}
ABSTRACT_TOKEN
\end{abstract}
\begin{IEEEkeywords}
KEYWORDS_TOKEN
\end{IEEEkeywords}
"""
    preamble = preamble.replace("TITLE_TOKEN", latex_inline(TITLE)).replace("ABSTRACT_TOKEN", latex_inline(abstract)).replace("KEYWORDS_TOKEN", latex_inline(KEYWORDS))
    main_tex = (
        preamble + "\n" + body_tex + "\n\\begin{thebibliography}{12}\n"
        + "\n".join(ref_tex) + "\n\\end{thebibliography}\n"
        + "\n".join(figure_tex) + "\n" + "\n".join(table_tex) + "\n\\end{document}\n"
    )
    (LATEX / "main.tex").write_text(main_tex, encoding="utf-8")


def register_fonts() -> None:
    candidates = [
        Path("D:/ANACONDA/Lib/site-packages/matplotlib/mpl-data/fonts/ttf"),
        Path("C:/Windows/Fonts"),
    ]
    for base in candidates:
        regular, bold, italic, bolditalic = (base / name for name in ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSerif-Italic.ttf", "DejaVuSerif-BoldItalic.ttf"))
        if all(path.is_file() for path in (regular, bold, italic, bolditalic)):
            for name, path in (("DVS", regular), ("DVS-Bold", bold), ("DVS-Italic", italic), ("DVS-BoldItalic", bolditalic)):
                pdfmetrics.registerFont(TTFont(name, str(path)))
            pdfmetrics.registerFontFamily("DVS", normal="DVS", bold="DVS-Bold", italic="DVS-Italic", boldItalic="DVS-BoldItalic")
            return
    raise FileNotFoundError("DejaVu Serif fonts not available for Unicode PDF text")


def styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName="DVS", textColor=colors.HexColor("#171C22"), allowWidows=0, allowOrphans=0)
    return {
        "title": ParagraphStyle("paper_title", fontName="DVS-Bold", fontSize=13.4, leading=16.7, alignment=TA_CENTER, spaceAfter=10, **{k: v for k, v in base.items() if k != "fontName"}),
        "author": ParagraphStyle("paper_author", fontSize=8.5, leading=11.4, alignment=TA_CENTER, spaceAfter=7, **base),
        "abstract": ParagraphStyle("paper_abstract", fontSize=7.9, leading=10, alignment=TA_LEFT, spaceAfter=5, **base),
        "keywords": ParagraphStyle("paper_keywords", fontSize=7.7, leading=9.6, alignment=TA_LEFT, spaceAfter=1, **base),
        "section": ParagraphStyle("paper_section", fontName="DVS-Bold", fontSize=9.4, leading=11.1, spaceBefore=9, spaceAfter=4, alignment=TA_CENTER, keepWithNext=1, **{k: v for k, v in base.items() if k != "fontName"}),
        "subsection": ParagraphStyle("paper_subsection", fontName="DVS-Bold", fontSize=8.45, leading=10.3, spaceBefore=7, spaceAfter=3, keepWithNext=1, **{k: v for k, v in base.items() if k != "fontName"}),
        "body": ParagraphStyle("paper_body", fontSize=8.05, leading=10.15, alignment=TA_LEFT, spaceAfter=5.1, splitLongWords=0, **base),
        "ref": ParagraphStyle("paper_ref", fontSize=7.0, leading=8.7, leftIndent=14, firstLineIndent=-14, spaceAfter=3, splitLongWords=1, **base),
        "caption": ParagraphStyle("paper_caption", fontSize=8.0, leading=10.5, spaceBefore=5, spaceAfter=14, **base),
        "table_caption": ParagraphStyle("paper_table_caption", fontSize=8.0, leading=10.5, spaceAfter=9, **base),
        "cell": ParagraphStyle("paper_cell", fontSize=6.8, leading=8.7, **base),
        "cell_small": ParagraphStyle("paper_cell_small", fontSize=6.3, leading=8.3, **base),
        "note": ParagraphStyle("paper_note", fontSize=7.3, leading=9.6, spaceBefore=5, spaceAfter=10, **base),
    }


def inline_pdf(markdown: str) -> str:
    # ReportLab Paragraph markup; preserve DOI links and numbered citation labels.
    # Markdown URLs can contain balanced parentheses (notably the ASCE DOI).
    links: list[tuple[str, str]] = []
    linkless: list[str] = []
    i = 0
    while i < len(markdown):
        if markdown[i] == "[":
            close = markdown.find("]", i + 1)
            if close != -1 and markdown[close:close + 2] == "](":
                cursor = close + 2
                depth = 1
                while cursor < len(markdown) and depth:
                    if markdown[cursor] == "(":
                        depth += 1
                    elif markdown[cursor] == ")":
                        depth -= 1
                    cursor += 1
                if depth == 0:
                    label = markdown[i + 1:close]
                    url = markdown[close + 2:cursor - 1]
                    if url.startswith(("https://", "http://")):
                        token = f"ZZLINKTOKEN{len(links)}ZZ"
                        links.append((label, url))
                        linkless.append(token)
                        i = cursor
                        continue
        linkless.append(markdown[i])
        i += 1
    markdown = "".join(linkless)
    pieces: list[str] = []
    pattern = re.compile(r"\\\((.+?)\\\)|\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`")
    cursor = 0
    for match in pattern.finditer(markdown):
        pieces.append(html.escape(markdown[cursor:match.start()]))
        math, bold, italic, code = match.groups()
        if math is not None:
            math = math.replace(r"\mathrm{alarm}", "alarm").replace(r"\mathrm{healthy}", "healthy").replace(r"\mathrm{phase}", "phase")
            math = math.replace(r"\mid", " | ").replace(r"\epsilon", "ε")
            math = math.replace("_t", "ₜ")
            pieces.append(html.escape(math))
        elif bold is not None:
            pieces.append(f"<b>{html.escape(bold)}</b>")
        elif italic is not None:
            pieces.append(f"<i>{html.escape(italic)}</i>")
        else:
            pieces.append(html.escape(code))
        cursor = match.end()
    pieces.append(html.escape(markdown[cursor:]))
    rendered = "".join(pieces)
    for index, (label, url) in enumerate(links):
        visible = f"[{label}]" if label.isdigit() else label
        rendered = rendered.replace(
            f"ZZLINKTOKEN{index}ZZ",
            f'<link href="{html.escape(url, quote=True)}" color="#174A75">{html.escape(visible)}</link>',
        )
    return rendered


def body_flowables(before_refs: str, refs: list[str], sty: dict[str, ParagraphStyle]) -> list:
    story: list = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            story.append(Paragraph(inline_pdf(" ".join(paragraph)), sty["body"]))
            paragraph.clear()

    for line in before_refs.splitlines():
        if line.startswith("## "):
            flush()
            story.append(Paragraph(html.escape(line[3:]), sty["section"]))
        elif line.startswith("### "):
            flush()
            story.append(Paragraph(html.escape(line[4:]), sty["subsection"]))
        elif re.match(r"^\d+\. ", line):
            flush()
            story.append(Paragraph(inline_pdf(line), sty["body"]))
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.strip())
    flush()
    story.append(Paragraph("References", sty["section"]))
    for line in refs:
        story.append(Paragraph(inline_pdf(line), sty["ref"]))
    return story


class TwoColumnDraft(BaseDocTemplate):
    def __init__(self, filename: Path):
        super().__init__(str(filename), pagesize=letter, leftMargin=40, rightMargin=40, topMargin=42, bottomMargin=39,
                         title=TITLE, author="Jinghang Mei", pageCompression=1, allowSplitting=1)
        page_w, page_h = letter
        usable_w = page_w - 80
        gap = 17
        column_w = (usable_w - gap) / 2
        title_h = 285
        first_body_h = page_h - 42 - 39 - title_h
        title = Frame(40, page_h - 42 - title_h, usable_w, title_h, id="title", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        first_left = Frame(40, 39, column_w, first_body_h, id="first_left", leftPadding=0, rightPadding=4, topPadding=0, bottomPadding=0)
        first_right = Frame(40 + column_w + gap, 39, column_w, first_body_h, id="first_right", leftPadding=4, rightPadding=0, topPadding=0, bottomPadding=0)
        body_h = page_h - 42 - 39
        left = Frame(40, 39, column_w, body_h, id="left", leftPadding=0, rightPadding=4, topPadding=0, bottomPadding=0)
        right = Frame(40 + column_w + gap, 39, column_w, body_h, id="right", leftPadding=4, rightPadding=0, topPadding=0, bottomPadding=0)
        wide = Frame(40, 39, usable_w, body_h, id="wide", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id="first", frames=[title, first_left, first_right], onPage=self.decorate),
            PageTemplate(id="body", frames=[left, right], onPage=self.decorate),
            PageTemplate(id="exhibits", frames=[wide], onPage=self.decorate),
        ])

    def decorate(self, canv, doc) -> None:
        canv.saveState()
        canv.setStrokeColor(colors.HexColor("#B7BEC5"))
        canv.setLineWidth(0.35)
        canv.line(40, 32, letter[0] - 40, 32)
        canv.setFont("DVS", 7)
        canv.setFillColor(colors.HexColor("#505962"))
        canv.drawString(40, 22, "N-CMAPSS flight-phase calibration audit | draft")
        canv.drawRightString(letter[0] - 40, 22, str(doc.page))
        canv.restoreState()


def scaled_image(path: Path, max_w: float, max_h: float | None = None) -> Image:
    with PILImage.open(path) as image:
        w, h = image.size
    ratio = min(max_w / w, (max_h / h if max_h else max_w / w))
    return Image(str(path), width=w * ratio, height=h * ratio)


def make_table(content: str, index: int, sty: dict[str, ParagraphStyle]) -> list:
    caption, rows, note = split_table(content)
    widths = ([110, 211, 211] if index == 0 else [116, 58, 58, 58, 61, 61, 61, 59])
    if index == 2:
        widths = [116, 58, 58, 58, 59, 65, 59, 59]
    if sum(widths) > 532:
        factor = 532 / sum(widths)
        widths = [w * factor for w in widths]
    cellstyle = sty["cell"] if index == 0 else sty["cell_small"]
    table_rows = [[Paragraph(inline_pdf(cell), cellstyle) for cell in row] for row in rows]
    table = Table(table_rows, colWidths=widths, repeatRows=1, hAlign="CENTER")
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
    result = [Paragraph(inline_pdf(caption), sty["table_caption"]), table]
    if note:
        if index == 2:
            note = note.replace("3/42", "3 of 42")
        result.append(Paragraph(inline_pdf(note), sty["note"]))
    return result


def create_pdf(abstract: str, body: str, captions: list[str], tables: list[str]) -> None:
    register_fonts()
    sty = styles()
    before_refs, refs = references_from_body(body)
    story: list = [
        NextPageTemplate("body"),
        Paragraph(html.escape(TITLE), sty["title"]),
        Paragraph("<br/>".join(html.escape(line) for line in AUTHOR), sty["author"]),
        Paragraph("<b>Abstract—</b> " + inline_pdf(abstract), sty["abstract"]),
        Paragraph("<b>Keywords—</b> " + html.escape(KEYWORDS), sty["keywords"]),
        FrameBreak(),
        *body_flowables(before_refs, refs, sty),
        NextPageTemplate("exhibits"),
        PageBreak(),
    ]
    for index, (stem, caption) in enumerate(zip(FIGURE_STEMS, captions)):
        max_width = 520 if index != 2 else 400
        image = scaled_image(PAPER / "figures" / f"{stem}.png", max_width)
        story.append(KeepTogether([image, Paragraph(inline_pdf(caption), sty["caption"])]))
        if index == 1 or index == 3:
            story.append(PageBreak())
    for index, content in enumerate(tables):
        block = make_table(content, index, sty)
        story.append(KeepTogether(block))
        story.append(Spacer(1, 16))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    TwoColumnDraft(PDF).build(story)


def main() -> None:
    _, abstract, body, captions, tables = read_inputs()
    create_latex(abstract, body, captions, tables)
    create_pdf(abstract, body, captions, tables)
    from pypdf import PdfReader
    pages = len(PdfReader(str(PDF)).pages)
    log = {
        "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "latex_source": "paper/latex/main.tex",
        "bibliography": "paper/latex/references.bib",
        "pdf": "paper/output/NCMAPSS_Flight_Phase_Manuscript_Draft.pdf",
        "renderer": "ReportLab fallback: no pdflatex, xelatex, lualatex, or tectonic on local PATH",
        "latex_compiled": False,
        "pandoc_for_latex_source": subprocess.run(["pandoc", "--version"], text=True, capture_output=True, check=True).stdout.splitlines()[0],
        "pages": pages,
        "scientific_content_changes": "none; Figure 3 caption clarification, author placeholder, and keywords are presentation additions",
    }
    LOG.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    print(f"Built {PDF} ({pages} pages); LaTeX source at {LATEX / 'main.tex'}")


if __name__ == "__main__":
    main()
