"""Convert the MSSP Markdown draft into an elsarticle LaTeX manuscript and compile it.

Input: paper/mssp/manuscript_mssp_draft.md (the single source of truth for the text),
paper/mssp/figures/*.pdf and paper/mssp/tables/*.tex (built by build_mssp_figures_tables.py), and
paper/mssp/latex/references_mssp.bib (verified bibliography).
Output: paper/mssp/latex/main.tex, highlights.txt, and main.pdf (via latexmk with pdflatex/BibTeX).
The converter handles the Markdown subset used by the draft: headings, paragraphs, bold,
italic, inline code, inline and display math, nested bullet and numbered lists, and numeric
citations [n] / [N#] with ranges.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "paper/mssp"
DRAFT = PKG / "manuscript_mssp_draft.md"
OUT = PKG / "latex"
AUTHOR = {"name": "Jinghang Mei", "email": "surnamemei05@gmail.com", "orcid": "0009-0007-2901-3285",
          "affiliation": "School of Electrical and Computer Engineering, The University of Sydney, Sydney, Australia"}
AUTHOR_BLOCK = rf"""\author[usyd]{{{AUTHOR['name']}\corref{{cor1}}}}
\cortext[cor1]{{Corresponding author. ORCID: \url{{https://orcid.org/{AUTHOR['orcid']}}}}}
\ead{{{AUTHOR['email']}}}
\address[usyd]{{{AUTHOR['affiliation']}}}"""
UNICODE = {"2032": r"\ensuremath{'}", "2212": r"\ensuremath{-}", "03B1": r"\ensuremath{\alpha}",
           "03BA": r"\ensuremath{\kappa}", "00D7": r"\ensuremath{\times}", "2265": r"\ensuremath{\geq}",
           "2264": r"\ensuremath{\leq}", "2192": r"\ensuremath{\rightarrow}", "03C6": r"\ensuremath{\phi}",
           "00B1": r"\ensuremath{\pm}", "2248": r"\ensuremath{\approx}", "03C0": r"\ensuremath{\pi}",
           "03C4": r"\ensuremath{\tau}", "03C1": r"\ensuremath{\rho}", "0394": r"\ensuremath{\Delta}"}
FIGURES = {1: "fig1_study_timeline", 2: "fig2_frozen_pooled_phase_fpr", 3: "fig3_disparity_and_nominal_calibration",
           4: "fig4_matched_false_flag_tradeoff", 5: "fig5_engine_transport", 6: "fig6_operating_context_and_support"}
TABLES = {1: "table1_design", 2: "table2_frozen_pooled_calibration", 3: "table3_calibration_quality",
          4: "table4_matched_false_flag_delay", 5: "table5_engine_transport"}
NO_RESIZE = {1}


def cite_key(token):
    return token if token.startswith("N") else f"ref{token}"


def citations(text):
    def expand(match):
        a, b, prefix = int(match.group(2)), int(match.group(4)), match.group(1)
        return ", ".join(f"[{prefix}{k}]" for k in range(a, b + 1))
    text = re.sub(r"\[(N?)(\d+)\]–\[(N?)(\d+)\]", expand, text)
    text = re.sub(r"\[(N?\d{1,2})\]", lambda m: r"\cite{" + cite_key(m.group(1)) + "}", text)
    while True:
        merged = re.sub(r"\\cite\{([^}]*)\},\s*\\cite\{([^}]*)\}", r"\\cite{\1,\2}", text)
        if merged == text:
            return text
        text = merged


def escape(text):
    out, i = [], 0
    for part in re.split(r"(\$\$.*?\$\$|\$[^$]+\$|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("$$"):
            out.append(r"\[" + part[2:-2] + r"\]")
        elif part.startswith("$"):
            out.append(part)
        elif part.startswith("`"):
            inner = part[1:-1].replace("\\", r"\textbackslash{}").replace("_", r"\_").replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")
            out.append(r"\texttt{" + inner + "}")
        else:
            s = part.replace("\\", r"\textbackslash{}")
            for a, b in (("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_"), ("~", r"\textasciitilde{}")):
                s = s.replace(a, b)
            s = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", s)
            s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\\emph{\1}", s)
            s = s.replace("\u201c", "``").replace("\u201d", "''")
            s = re.sub(r'"([^"]+)"', r"``\1''", s)
            s = citations(s)
            out.append(s)
        i += 1
    return "".join(out)


def list_block(lines):
    """Nested itemize/enumerate from indented '- ' and '1. ' lines (with continuation lines)."""
    items = []
    for raw in lines:
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", raw)
        if m:
            items.append([len(m.group(1)), "enumerate" if m.group(2)[0].isdigit() else "itemize", m.group(3)])
        elif items and raw.strip():
            items[-1][2] += " " + raw.strip()
    out, stack = [], []
    for indent, kind, text in items:
        while stack and indent < stack[-1][0]:
            out.append(r"\end{" + stack.pop()[1] + "}")
        if not stack or indent > stack[-1][0]:
            out.append(r"\begin{" + kind + "}")
            stack.append((indent, kind))
        out.append(r"\item " + escape(text))
    while stack:
        out.append(r"\end{" + stack.pop()[1] + "}")
    return out


def blocks(body):
    """Split Markdown body into (kind, lines) blocks."""
    result, current, kind = [], [], None
    for line in body.splitlines():
        is_list = bool(re.match(r"^\s*([-*]|\d+\.)\s+", line))
        if not line.strip():
            if kind == "list":
                current.append(line)
                continue
            if current:
                result.append((kind, current))
            current, kind = [], None
            continue
        if line.startswith("#"):
            if current:
                result.append((kind, current))
            result.append(("heading", [line]))
            current, kind = [], None
            continue
        if kind == "list" and not is_list and not line.startswith(" ") and current and not current[-1].strip():
            result.append((kind, current))
            current, kind = [], None
        if kind is None:
            kind = "list" if is_list else "para"
        elif kind == "para" and is_list:
            result.append((kind, current))
            current, kind = [], "list"
        current.append(line)
    if current:
        result.append((kind, current))
    return result


def figure_env(number, caption):
    return [r"\begin{figure}[htbp]", r"\centering",
            r"\includegraphics[width=\textwidth]{../figures/" + FIGURES[number] + ".pdf}",
            r"\caption{" + escape(caption) + "}", r"\label{fig:" + str(number) + "}", r"\end{figure}"]


def table_env(number, caption):
    body = [r"\input{../tables/" + TABLES[number] + ".tex}"]
    if number not in NO_RESIZE:
        body = [r"\begin{adjustbox}{max width=\textwidth}"] + body + [r"\end{adjustbox}"]
    return [r"\begin{table}[htbp]", r"\centering", r"\small", r"\caption{" + escape(caption) + "}",
            r"\label{tab:" + str(number) + "}"] + body + [r"\end{table}"]


def convert(markdown):
    markdown = re.sub(r"<!--.*?-->", "", markdown, flags=re.S)
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", markdown)
    if leftover:
        raise SystemExit(f"unfilled placeholders in the draft: {leftover}")
    title = re.search(r"^# (.+)$", markdown, flags=re.M).group(1).strip()
    abstract = markdown.split("## Abstract", 1)[1].split("**Keywords:**", 1)[0].strip()
    keywords = markdown.split("**Keywords:**", 1)[1].splitlines()[0].strip()
    highlights = [l[2:].strip() for l in markdown.split("**Highlights", 1)[1].split("## 1.", 1)[0].splitlines()
                  if l.startswith("- ")]
    body = "## 1." + markdown.split("## 1.", 1)[1]
    body, _, tail = body.partition("## Figures (captions)")
    fig_caps = dict((int(n), c.strip()) for n, c in re.findall(r"\*\*Fig\. (\d+)\.\*\* (.+?)(?=\n\*\*Fig\. |\n## |\Z)", tail, flags=re.S))
    tab_caps = dict((int(n), c.strip()) for n, c in re.findall(r"\*\*Table (\d+)\.\*\* (.+)", tail))
    fig_caps = {n: " ".join(c.replace("\n- ", " ").split()) for n, c in fig_caps.items()}
    placed_f, placed_t, lines = set(), set(), []
    for kind, block in blocks(body):
        if kind == "heading":
            level, text = block[0].split(" ", 1)
            numbered = bool(re.match(r"^\d+(\.\d+)*\.?\s+", text.strip()))
            text = re.sub(r"^\d+(\.\d+)*\.?\s+", "", text.strip())
            command = {"##": "section", "###": "subsection", "####": "subsubsection"}[level]
            lines += ["", "\\" + command + ("" if numbered else "*") + "{" + escape(text) + "}"]
            continue
        if kind == "list":
            lines += list_block(block)
        else:
            text = " ".join(l.strip() for l in block)
            if text.startswith(">"):
                lines += [r"\begin{quote}", escape(text.lstrip("> ")), r"\end{quote}"]
            else:
                lines += ["", escape(text)]
        joined = " ".join(block)
        # Floats are emitted in numeric order so that LaTeX's automatic numbering matches the text:
        # a first mention of item n also places every lower-numbered item not yet placed.
        mentioned = [int(x) for x in re.findall(r"Figs?\. (\d+)", joined)]
        for n in sorted(k for k in FIGURES if mentioned and k <= max(mentioned) and k not in placed_f and k in fig_caps):
            lines += figure_env(n, fig_caps[n])
            placed_f.add(n)
        mentioned = [int(x) for x in re.findall(r"Tables? (\d+)", joined)]
        for n in sorted(k for k in TABLES if mentioned and k <= max(mentioned) and k not in placed_t and k in tab_caps):
            lines += table_env(n, tab_caps[n])
            placed_t.add(n)
    for n in sorted(set(FIGURES) - placed_f):
        if n in fig_caps:
            lines += figure_env(n, fig_caps[n])
    for n in sorted(set(TABLES) - placed_t):
        if n in tab_caps:
            lines += table_env(n, tab_caps[n])
    declarations = []
    unicode = "\n".join(r"\DeclareUnicodeCharacter{" + k + "}{" + v + "}" for k, v in UNICODE.items())
    document = rf"""\documentclass[preprint,11pt,a4paper]{{elsarticle}}
\usepackage[a4paper,margin=2.5cm]{{geometry}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{graphicx,amsmath,amssymb,array,booktabs,xurl,adjustbox,makecell,hyperref}}
\renewcommand{{\cellalign}}{{bl}}\renewcommand{{\theadalign}}{{bl}}
\usepackage[switch]{{lineno}}
\usepackage{{enumitem}}
\setlist{{nosep,leftmargin=*}}
\hypersetup{{hidelinks}}
{unicode}
\emergencystretch=3em
\renewcommand{{\topfraction}}{{0.9}}\renewcommand{{\bottomfraction}}{{0.8}}
\renewcommand{{\textfraction}}{{0.07}}\renewcommand{{\floatpagefraction}}{{0.8}}
\setcounter{{topnumber}}{{3}}\setcounter{{bottomnumber}}{{2}}\setcounter{{totalnumber}}{{5}}
\biboptions{{numbers,sort&compress}}
\AtBeginDocument{{\setlength{{\bibsep}}{{1pt plus 0.3pt}}}}
\journal{{Mechanical Systems and Signal Processing}}
\makeatletter
\let\ps@pprintTitle\ps@plain
\makeatother

\begin{{document}}
\begin{{frontmatter}}
\title{{{escape(title)}}}
{AUTHOR_BLOCK}
\begin{{abstract}}
{escape(" ".join(abstract.split()))}
\end{{abstract}}
\begin{{keyword}}
{" \\sep ".join(escape(k.strip()) for k in keywords.split(";"))}
\end{{keyword}}
\end{{frontmatter}}
\linenumbers
{chr(10).join(lines)}
{chr(10).join(declarations)}

\bibliographystyle{{elsarticle-num}}
\bibliography{{references_mssp}}
\end{{document}}
"""
    return document, highlights


DECLARATIONS = {"Data availability": "data_availability.txt", "Code availability": "code_availability.txt",
                "Declaration of competing interest": "competing_interests.txt", "Funding": "funding.txt",
                "CRediT authorship contribution statement": "credit_author_statement.txt",
                "Declaration of generative AI and AI-assisted technologies in the manuscript preparation process":
                    "generative_ai_declaration.txt"}


def export_declarations(markdown):
    """Write each declaration section of the draft to paper/mssp/declarations/ for the submission system."""
    folder = PKG / "declarations"
    folder.mkdir(exist_ok=True)
    for heading, name in DECLARATIONS.items():
        text = markdown.split("## " + heading + "\n", 1)[1].split("\n## ", 1)[0].strip()
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        (folder / name).write_text(heading + "\n\n" + text + "\n", encoding="utf-8")
    metadata = (f"Author: {AUTHOR['name']}\nAffiliation: {AUTHOR['affiliation']}\n"
                f"Postal address: The University of Sydney, NSW 2006, Australia\n"
                f"Corresponding-author e-mail: {AUTHOR['email']}\nORCID: https://orcid.org/{AUTHOR['orcid']}\n")
    (folder / "author_metadata.txt").write_text(metadata, encoding="utf-8")


def write_docx(path, title, paragraphs):
    """Write a minimal Word (OOXML) document with a bold title and one paragraph per item."""
    import zipfile
    from xml.sax.saxutils import escape as xml_escape

    def para(text, bold=False):
        run = "<w:rPr><w:b/></w:rPr>" if bold else ""
        return f'<w:p><w:r>{run}<w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r></w:p>'
    body = para(title, bold=True) + "".join(para(p) for p in paragraphs)
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f"<w:body>{body}<w:sectPr/></w:body></w:document>")
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" ContentType="application/'
                     'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'officeDocument" Target="word/document.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in (("[Content_Types].xml", content_types), ("_rels/.rels", rels),
                           ("word/document.xml", document)):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            archive.writestr(info, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-compile", action="store_true")
    args = parser.parse_args()
    markdown = DRAFT.read_text(encoding="utf-8")
    document, highlights = convert(markdown)
    export_declarations(markdown)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "main.tex").write_text(document, encoding="utf-8")
    (OUT / "highlights.txt").write_text("\n".join(highlights) + "\n", encoding="utf-8")
    write_docx(OUT / "Highlights.docx", "Highlights", highlights)
    print(f"wrote {OUT / 'main.tex'} and highlights.txt ({len(highlights)} highlights)")
    if args.no_compile:
        return
    result = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                            cwd=OUT, capture_output=True, text=True, errors="replace")
    log = (OUT / "main.log").read_text(encoding="utf-8", errors="replace") if (OUT / "main.log").exists() else ""
    undefined = sorted(set(re.findall(r"Citation `([^']+)' on page", log)))
    print(f"latexmk exit {result.returncode}; undefined citations: {undefined or 'none'}")
    if result.returncode != 0:
        print(result.stdout[-3000:])
        sys.exit(1)


if __name__ == "__main__":
    main()
