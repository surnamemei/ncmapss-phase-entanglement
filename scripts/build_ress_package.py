"""Layout-only conversion of the frozen clean manuscript to elsarticle.

This script never reads experimental data or regenerates numerical exhibits.
It retains the verified manual reference text in main.tex; references.bib is an
editable, structured companion for a later publisher production workflow.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "paper/latex_clean/main.tex"
SOURCE_DIR = SOURCE.parent
OUTPUT = ROOT / "paper/ress"


def replace_once(value: str, old: str, new: str) -> str:
    count = value.count(old)
    if count != 1:
        raise ValueError(f"Expected one occurrence, found {count}: {old[:85]}")
    return value.replace(old, new)


def replace_expected(value: str, old: str, new: str, expected: int) -> str:
    count = value.count(old)
    if count != expected:
        raise ValueError(f"Expected {expected} occurrences, found {count}: {old[:85]}")
    return value.replace(old, new)


def extract_blocks(value: str, kind: str, expected: int) -> tuple[str, list[str]]:
    pattern = rf"\\begin\{{{kind}\*?\}}\[t\].*?\\end\{{{kind}\*?\}}\n?"
    blocks = re.findall(pattern, value, flags=re.S)
    if len(blocks) != expected:
        raise ValueError(f"Expected {expected} {kind} blocks; found {len(blocks)}")
    for block in blocks:
        value = replace_once(value, block, "")
    converted = [
        block.replace(f"\\begin{{{kind}*}}[t]", f"\\begin{{{kind}}}[!htbp]")
             .replace(f"\\end{{{kind}*}}", f"\\end{{{kind}}}")
        for block in blocks
    ]
    return value, converted


def reflow_ds03_table(source: str) -> str:
    """Combine each contrast and its interval in one readable cell, preserving data."""
    source = replace_once(
        source,
        r"\resizebox{\textwidth}{!}{\begin{tabular}{lrrrrrrr}",
        r"\fontsize{8.3}{10}\selectfont" + "\n" +
        r"\setlength{\tabcolsep}{1.5pt}" + "\n" +
        r"\renewcommand{\arraystretch}{1.24}" + "\n" +
        r"\begin{tabular}{>{\raggedright\arraybackslash}p{0.22\linewidth}*{3}{>{\centering\arraybackslash}p{0.10\linewidth}}*{2}{>{\centering\arraybackslash}p{0.21\linewidth}}}",
    )
    source = replace_once(source, r"\end{tabular}}", r"\end{tabular}")
    result: list[str] = []
    data_rows = 0
    for line in source.splitlines():
        if line.startswith("Detector & "):
            cells = line.removesuffix(r" \\").split(" & ")
            if len(cells) != 8:
                raise ValueError("DS03 source header changed")
            result.append(
                r"Detector & Climb FPR (\%) & Cruise FPR (\%) & Descent FPR (\%) & "
                r"Descent $-$ climb (pp); run-level 95\% CI & "
                r"Descent $-$ cruise (pp); run-level 95\% CI \\"
            )
        elif line.startswith(("PCA & ", "Isolation Forest (seed mean) & ", "Causal LSTM reconstruction (seed mean) & ")):
            cells = line.removesuffix(r" \\").split(" & ")
            if len(cells) != 8:
                raise ValueError("DS03 source row changed")
            result.append(
                " & ".join((cells[0], cells[1], cells[2], cells[3],
                            cells[4] + r"\newline " + cells[5],
                            cells[6] + r"\newline " + cells[7])) + r" \\"
            )
            data_rows += 1
        else:
            result.append(line)
    if data_rows != 3:
        raise ValueError("DS03 table lacks a detector row")
    return "\n".join(result) + "\n"


def build() -> Path:
    text = SOURCE.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "unchanged. {[}2{]}, {[}10{]}.",
        "unchanged {[}2{]}, {[}10{]}.",
    )
    text = replace_once(
        text,
        "phase-wise FPR, conditional calibration, and cross-phase threshold transfer expose",
        "phase-wise FPR, phase-conditional false-alarm behaviour, and cross-phase threshold transfer expose",
    )
    # The clean Markdown links are correct, but the earlier Markdown-to-LaTeX
    # converter stopped at parentheses inside two DOI URLs and left these tails
    # after citation tokens. They are not bibliography content.
    text = replace_expected(
        text, "{[}6{]}AS.1943-5525.0001483)", "{[}6{]}", 2
    )
    text = replace_expected(text, "{[}12{]}00060-7)", "{[}12{]}", 1)

    title = re.search(r"(?m)^\\title\{([^\n]+)\}$", text)
    abstract = re.search(r"(?s)\\begin\{abstract\}\n(.*?)\n\\end\{abstract\}", text)
    keywords = re.search(r"(?s)\\textbf\{Keywords---\}\s*\n(.*?)\n\n", text)
    if not (title and abstract and keywords):
        raise ValueError("Clean title, abstract, or keywords were not found")

    body = text[text.index(r"\section{Introduction}"):]
    body, figures = extract_blocks(body, "figure", 4)
    body, tables = extract_blocks(body, "table", 3)
    figures[2] = replace_once(
        figures[2],
        r"\includegraphics[width=0.94\textwidth]",
        r"\includegraphics[width=0.72\textwidth]",
    )
    tables[0] = replace_once(
        tables[0],
        r"\begin{tabular}{p{0.20\textwidth}p{0.36\textwidth}p{0.36\textwidth}}",
        r"\setlength{\tabcolsep}{3pt}" + "\n" +
        r"\renewcommand{\arraystretch}{1.12}" + "\n" +
        r"\begin{tabular}{>{\raggedright\arraybackslash}p{0.23\textwidth}>{\raggedright\arraybackslash}p{0.33\textwidth}>{\raggedright\arraybackslash}p{0.33\textwidth}}",
    )
    for index in (1,):
        tables[index] = replace_once(
            tables[index],
            r"\resizebox{\textwidth}{!}{\begin{tabular}{lrrrrrrr}",
            r"\fontsize{8.3}{10}\selectfont" + "\n" +
            r"\setlength{\tabcolsep}{2pt}" + "\n" +
            r"\renewcommand{\arraystretch}{1.24}" + "\n" +
            r"\begin{tabular}{>{\raggedright\arraybackslash}p{0.20\linewidth}*{7}{>{\centering\arraybackslash}p{0.10\linewidth}}}",
        )
        tables[index] = replace_once(tables[index], r"\end{tabular}}", r"\end{tabular}")
    tables[2] = reflow_ds03_table(tables[2])
    bibliography = re.search(r"(?s)\\begin\{thebibliography\}\{12\}.*?\\end\{thebibliography\}\n?", body)
    if not bibliography or len(re.findall(r"\\bibitem\{ref\d+\}", bibliography.group())) != 12:
        raise ValueError("Expected the 12 frozen verified bibliography entries")
    bib_block = bibliography.group()
    body = replace_once(body, bib_block, "")
    bib_block = replace_once(
        bib_block,
        r"\begin{thebibliography}{12}",
        r"\begin{thebibliography}{12}" + "\n" +
        r"\small\setlength{\itemsep}{0pt}",
    )
    body = replace_once(body, "\\end{document}", "")

    def after_heading(heading: str, block: str) -> None:
        nonlocal body
        body = replace_once(body, heading, heading + "\n" + block + "\n")

    after_heading(
        r"\subsection{Dataset and Discovery--Confirmation Design}\label{dataset-and-discoveryconfirmation-design}",
        figures[0],
    )
    after_heading(
        r"\subsection{Data Partitioning and Leakage Controls}\label{data-partitioning-and-leakage-controls}",
        tables[0],
    )
    after_heading(
        r"\subsection{Discovery of Phase-Dependent Healthy False Alarms on DS02}\label{discovery-of-phase-dependent-healthy-false-alarms-on-ds02}",
        figures[1] + "\n" + tables[1],
    )
    after_heading(
        r"\subsection{Cross-Phase Threshold Transfer}\label{cross-phase-threshold-transfer}",
        figures[2],
    )
    after_heading(
        r"\subsection{Frozen DS03 Confirmation}\label{frozen-ds03-confirmation}",
        figures[3] + "\n" + tables[2],
    )
    body, citation_count = re.subn(r"\{\[\}(\d+)\{\]\}", lambda m: rf"\cite{{ref{m.group(1)}}}", body)
    if citation_count < 12 or any(f"\\cite{{ref{i}}}" not in body for i in range(1, 13)):
        raise ValueError("Not all 12 in-text citations were converted")
    stray = re.findall(r"\\cite\{ref\d+\}[A-Za-z0-9]", body)
    if stray:
        raise ValueError(f"Citation followed by stray DOI or text: {stray}")
    if body.count(r"\begin{figure}") != 4 or body.count(r"\begin{table}") != 3:
        raise ValueError("Exhibit count changed during conversion")

    declaration_text = (ROOT / "paper/submission/generative_ai_declaration.md").read_text(encoding="utf-8")
    declaration_parts = declaration_text.strip().split("\n\n")
    if len(declaration_parts) != 2 or not declaration_parts[1].startswith("During the preparation of this work,"):
        raise ValueError("Expected one finalized AI declaration paragraph")
    ai_declaration = (
        r"\section*{Declaration of generative AI and AI-assisted technologies in the manuscript preparation process}"
        + "\n" + declaration_parts[1] + "\n"
    )

    head = rf"""\documentclass[preprint,12pt]{{elsarticle}}
\usepackage{{graphicx,amsmath,amssymb,array,booktabs,url,hyperref}}
\hypersetup{{hidelinks}}
\providecommand{{\tightlist}}{{}}
\emergencystretch=3em
\biboptions{{numbers,sort&compress}}
\journal{{Reliability Engineering \& System Safety}}
\makeatletter
\let\ps@pprintTitle\ps@plain
\makeatother

\begin{{document}}
\begin{{frontmatter}}
\title{{{title.group(1)}}}
\author[usyd]{{Jinghang Mei\corref{{cor1}}}}
\cortext[cor1]{{Corresponding author}}
\ead{{surnamemei05@gmail.com}}
\address[usyd]{{School of Electrical and Computer Engineering, The University of Sydney, Sydney, Australia}}
\begin{{abstract}}
{abstract.group(1).replace('/', r'/\allowbreak ')}
\end{{abstract}}
\begin{{keyword}}
{keywords.group(1).strip()}
\end{{keyword}}
\end{{frontmatter}}
\thispagestyle{{plain}}

"""
    result = head + body.strip() + "\n\n" + ai_declaration + "\n" + bib_block.strip() + "\n\n\\end{document}\n"
    for forbidden in ("Email: [to be added]", "draft 1", "draft 2", "Publisher.", "Author manuscript."):
        if forbidden in result:
            raise ValueError(f"Draft artifact in converted source: {forbidden}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "main.tex").write_text(result, encoding="utf-8")
    shutil.copy2(SOURCE_DIR / "references.bib", OUTPUT / "references.bib")
    for folder in ("figures", "tables"):
        destination = OUTPUT / folder
        destination.mkdir(exist_ok=True)
        for source in (SOURCE_DIR / folder).iterdir():
            if source.is_file():
                shutil.copy2(source, destination / source.name)
    return OUTPUT / "main.tex"


if __name__ == "__main__":
    print(build())
